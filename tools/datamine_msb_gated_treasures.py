#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""datamine_msb_gated_treasures.py -- treasures that DO NOT EXIST at map load (StartDisabled=1).

WHY
---
The long-running "checks gated behind something else" hunt looked in two places and found nothing:
  * EMEVD -- flag 67050 and its lot appear NOWHERE in all 589 decompiled files, and only 32 of 1824
    corpse flags (1.8%) appear anywhere in the EMEVD at all. It is the least script-visible pickup
    class in the game (chests 11.5%, all msb_flag_region 15.2%).
  * ESD -- the NPC-state flag vocabulary (esd_flags.tsv) is DISJOINT from pickup acquisition flags:
    0 of 2803 msb_flag_region, 0 of 1824 corpse.
Both were dead ends because the answer was never in a script. It is a FIELD ON THE MSB RECORD.

`MSB Event/Treasure` carries `<StartDisabled>`. When it is 1 the pickup is not in the world at load.
The hypothesis was that something must therefore ENABLE it later, making this the "regioned correctly
but cannot exist yet" class -- a missing ACCESS RULE invisible to every region oracle.

🛑 THE HYPOTHESIS IS DISPROVEN. Do not re-inherit it; the number below is the reason.
MEASURED 2026-07-25, whole corpus, this tool's own `--probe` output:

    InChest=0  StartDisabled=0 : 3112      InChest=0  StartDisabled=1 :   1
    InChest=1  StartDisabled=0 :  117      InChest=1  StartDisabled=1 : 141
    InChest=2  StartDisabled=0 :  502      InChest=2  StartDisabled=1 :  21

162 of the 163 StartDisabled=1 records are InChest>=1. Of the 3113 pickups NOT in a container,
exactly ONE is StartDisabled -- 0.03%. StartDisabled tracks the CONTAINER, not access: an item in a
closed chest is not in the world until the lid opens, which is the ordinary chest, not a gate.

The structural confirmation is in the `asset_entity_id` column this tool now emits. EnableAssetTreasure
is addressed by an ENTITY ID, and 54 of the 136 distinct live checks here have NO entity id at all --
Treasure EntityID 0 AND Part/Asset EntityID 0 -- so no EMEVD instruction can ever name them. They are
nonetheless ordinary loot: Stormveil's Godslayer's Seal and Curved Sword Talisman, Leyndell's Blessed
Dew Talisman, five Farum Azula chests, Roundtable Hold's Assassin's Prayerbook. A field whose only
proposed meaning is "an event must enable this" cannot mean that on 54 checks no event can address.

tools/datamine_treasure_enablers.py does the enabler join anyway and lands 18 of 136 with any enabler
at all, of which 13 are in-place ("break the pot", "open the carriage") and exactly ONE is a genuine
cross-region prerequisite. THIS TABLE IS NOT A RISK LIST. It is the candidate set that produced that
answer, and it is kept because the columns are the join keys, not because the rows are suspects.

MEASURED (all 1347 *-msb-dcx dirs, 2026-07-25): 3894 Treasure records, 163 StartDisabled=1 (4.2%).
Those 163 ROWS carry only 148 DISTINCT flags -- several treasure records share one lot -- of which
140 are LIVE AP checks (13 corpses). Rows and checks are different numbers; the tool prints both.

🛑 THE EXEMPLAR THAT STARTED THE HUNT IS NOT IN THIS SET. f67050 has StartDisabled=0, its asset is
`NeverDisable` with no condition, and both Fextralife and Game8 place it on "a dead man sitting" at
the collapsed bridge to Stormveil with NO Roderika involvement and no gate. The handoff's "the
cookbook Roderika leaves at Stormhill Shack ... does not exist until you rest at a Liurnia grace" was
never sourced and looks like a conflation of two different things. Do not re-inherit it.

WHAT THIS TABLE IS NOT
----------------------
`StartDisabled=1` says a pickup starts absent. It does NOT say what enables it, and it does NOT by
itself mean the check is misregioned or unwinnable -- some are enabled immediately by their map's own
setup. It is a CANDIDATE SET for access-rule review, not a verdict. Treating a row here as a proven
bug is the same error as treating the EMEVD's silence as proof of no gating.

OUTPUT: greenfield/msb_gated_treasures.tsv
    map_id, treasure_name, item_lot_id, treasure_part, entity_id, flag, is_live_check, is_corpse

USAGE:
    python tools/datamine_msb_gated_treasures.py --root elden_ring_artifacts/mapstudio --probe
    python tools/datamine_msb_gated_treasures.py --root elden_ring_artifacts/mapstudio
⚠️ --state PATH checkpoints progress and resumes. That exists because the agent sandbox reads this
tree over a MOUNT and a full walk exceeds the harness's hard 45s command cap; on a local disk the
whole scan is one pass and the flag is unnecessary.
"""
import argparse
import collections
import csv
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

import artifacts_root                          # noqa: E402  -- THE --path argument, not a copy

ROOT_DEFAULT = os.path.join(artifacts_root.default_root(REPO), "mapstudio")
OUT = os.path.join(REPO, "greenfield", "msb_gated_treasures.tsv")
CORPSE = "宝死体"          # 宝死体 -- "treasure corpse"

# Floor on the TOTAL treasure population, not on the gated subset. Measured 3894; a run that sees far
# fewer has a broken walk or a moved layout. The gated count is the FINDING and must never be floored
# -- flooring an output you are trying to measure is how a rebaseline launders a regression.
_TREASURE_FLOOR = 3000

_F = {k: re.compile(r"<%s>([^<]*)</%s>" % (k, k)) for k in
      ("Name", "EntityID", "ItemLotID", "TreasurePartName", "StartDisabled", "InChest",
       "ModelName")}

# Where a TreasurePartName can live. Part/Asset is the live instance; Part/DummyAsset is a
# placeholder part. MEASURED 2026-07-25: 8 of the 160 distinct gated (map, part) pairs resolve only
# in DummyAsset, so an Asset-only lookup would have silently dropped 5%% of the join. Both are tried
# and the winning directory is recorded in `part_dir` rather than flattened away.
_PART_DIRS = ("Asset", "DummyAsset")


def _get(text, key):
    m = _F[key].search(text)
    return m.group(1).strip() if m else ""


def load_tsv(name):
    fp = os.path.join(REPO, "greenfield", name)
    if not os.path.exists(fp):
        return None
    rows = [l for l in open(fp, encoding="utf-8") if not l.startswith("#")]
    return list(csv.DictReader(rows, delimiter="\t"))


def _asset(root, mapdir, part):
    """TreasurePartName -> (asset EntityID, ModelName, which Part/ subdir it came from).

    🛑 THIS IS THE JOIN KEY THE FIRST VERSION OF THIS TOOL GOT WRONG. The `EntityID` on the
    Event/Treasure record is 0 on 161 of the 163 gated rows, so a column built from it joins to
    nothing. `EnableAssetTreasure` is addressed by an ENTITY ID, and MEASURED against the corpus it
    accepts EITHER space:
      * the Part/Asset EntityID  -- m15_00 `EnableAssetTreasure(15001810)` == asset AEG099_990_9000
      * the Treasure EVENT EntityID -- m60_39_53 `EnableAssetTreasure(1039533501)`, where the asset
        is a different id (1039531480) and is enabled separately by `EnableAsset`.
    Both are emitted; the consumer must try both keys or it will miss the second family.
    """
    for sub in _PART_DIRS:
        fp = os.path.join(root, mapdir, "Part", sub, part + ".xml")
        if os.path.exists(fp):
            t = open(fp, encoding="utf-8-sig", errors="replace").read()
            return _get(t, "EntityID"), _get(t, "ModelName"), sub
    return "", "", ""


def scan(root, state_path):
    dirs = sorted(d for d in os.listdir(root) if d.endswith("-msb-dcx"))
    if not dirs:
        sys.exit("FATAL: no *-msb-dcx directories under %s. This tool reads WITCHY-UNPACKED MSBs, not "
                 "packed .msb.dcx. Nothing scanned, nothing written." % root)
    # `xtab` is the whole-corpus (InChest, StartDisabled) cross-tabulation. It is not decoration: it
    # is the control that tells you whether StartDisabled means "an event must enable this" or is
    # simply a property of the CONTAINER. See the module docstring.
    st = {"i": 0, "tot": 0, "rows": [], "no_lot": 0, "unparsed": 0, "xtab": {}, "no_part": 0}
    if state_path and os.path.exists(state_path):
        st = json.load(open(state_path))
    t0 = time.time()
    while st["i"] < len(dirs):
        d = dirs[st["i"]]
        st["i"] += 1
        td = os.path.join(root, d, "Event", "Treasure")
        if os.path.isdir(td):
            for fn in sorted(os.listdir(td)):
                if not fn.endswith(".xml"):
                    continue
                try:
                    t = open(os.path.join(td, fn), encoding="utf-8-sig", errors="replace").read()
                except OSError:
                    st["unparsed"] += 1
                    continue
                st["tot"] += 1
                sd = _get(t, "StartDisabled")
                ic = _get(t, "InChest")
                # Cross-tab EVERY record, gated or not. Counting only the gated rows would make the
                # "StartDisabled is a container property" question unanswerable from this output.
                k = "%s|%s" % (ic or "?", sd or "?")
                st["xtab"][k] = st["xtab"].get(k, 0) + 1
                if sd == "":
                    st["unparsed"] += 1          # tallied: a missing field is not a 0
                    continue
                if sd != "1":
                    continue
                lot = _get(t, "ItemLotID")
                if not lot or lot == "-1":
                    st["no_lot"] += 1            # gated, but awards nothing joinable
                    continue
                part = _get(t, "TreasurePartName")
                aent, amdl, adir = _asset(root, d, part) if part else ("", "", "")
                if part and not adir:
                    st["no_part"] += 1       # TALLIED: part named but resolvable in no Part/ subdir
                st["rows"].append([d.replace("-msb-dcx", ""), _get(t, "Name"), lot, part,
                                   _get(t, "EntityID"), aent, amdl, adir, _get(t, "InChest")])
        if state_path and time.time() - t0 > 35:
            json.dump(st, open(state_path, "w"))
            print("checkpoint: %d/%d dirs, %d treasures, %d gated -- rerun to continue"
                  % (st["i"], len(dirs), st["tot"], len(st["rows"])))
            return None, st, len(dirs)
    if state_path:
        json.dump(st, open(state_path, "w"))
    return dirs, st, len(dirs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None,
                    help="the witchy-unpacked MSB directory itself (default: <--path>/mapstudio). "
                         "--root is the narrower flag and WINS over --path when both are given.")
    artifacts_root.add_path_argument(
        ap, artifacts_alias=False,
        extra_help="this tool reads mapstudio/ under it, so --path DIR means --root DIR/mapstudio")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--state", help="checkpoint file (sandbox/mount use only; see docstring)")
    ap.add_argument("--probe", action="store_true")
    a = ap.parse_args()
    _root = artifacts_root.resolve(a.path)
    if not a.root:
        a.root = os.path.join(_root, "mapstudio") if _root else ROOT_DEFAULT

    if not os.path.isdir(a.root):
        sys.exit("FATAL: %s not found. Point --root at the witchy-unpacked mapstudio dir." % a.root)

    done, st, ndirs = scan(a.root, a.state)
    if done is None:
        return 0                                  # checkpointed mid-walk; not an error, not a result

    print("msb dirs %d | Treasure records %d | StartDisabled=1 with a lot %d"
          % (ndirs, st["tot"], len(st["rows"])))
    print("  gated but ItemLotID missing/-1 : %d   (tallied, not silently dropped)" % st["no_lot"])
    print("  unreadable / no StartDisabled  : %d" % st["unparsed"])
    print("  TreasurePartName in no Part/   : %d   (tallied)" % st["no_part"])
    print("\n  WHOLE-CORPUS (InChest, StartDisabled) cross-tab -- the control for 'is StartDisabled")
    print("  an access gate or a property of the CONTAINER?':")
    for k in sorted(st["xtab"]):
        ic, sd = k.split("|")
        print("    InChest=%-2s StartDisabled=%-2s : %5d" % (ic, sd, st["xtab"][k]))
    _ic0 = sum(v for k, v in st["xtab"].items() if k.startswith("0|"))
    _ic0d = st["xtab"].get("0|1", 0)
    if _ic0:
        print("    -> of %d NOT-in-a-container records, %d are StartDisabled (%.2f%%)"
              % (_ic0, _ic0d, 100.0 * _ic0d / _ic0))

    if st["tot"] < _TREASURE_FLOOR:
        sys.exit("FATAL: only %d Treasure records (floor %d) -- broken walk or moved layout, not a "
                 "smaller corpus. Nothing written." % (st["tot"], _TREASURE_FLOOR))
    if not st["rows"]:
        sys.exit("FATAL: zero StartDisabled=1 rows out of %d treasures. StartDisabled parsed on every "
                 "record, so zero means the FIELD moved, not that nothing is gated. Nothing written."
                 % st["tot"])

    # --- joins, each one tallied ---
    lot2flag = collections.defaultdict(set)
    fl = load_tsv("flag_lots.tsv")
    for x in (fl or []):
        if x["lot"].isdigit():
            lot2flag[x["lot"]].add(x["flag"])
    msb = {x["flag"]: x for x in (load_tsv("msb_flag_region.tsv") or [])}
    data_py = os.path.join(REPO, "greenfield", "eldenring", "data.py")
    live = set(re.findall(r"\[f(\d+)\]", open(data_py, encoding="utf-8").read())) \
        if os.path.exists(data_py) else set()
    if fl is None or not live:
        sys.exit("FATAL: flag_lots.tsv and/or data.py unavailable -- the lot->flag and live-check "
                 "joins CANNOT RUN, and the table's whole value is those columns. Nothing written.")

    out, nflag, nlive = [], 0, 0
    for mp, name, lot, part, ent, aent, amdl, adir, ic in st["rows"]:
        flags = sorted(lot2flag.get(lot, ()))
        f = flags[0] if flags else ""
        if f:
            nflag += 1
        islive = "1" if f in live else "0"
        if islive == "1":
            nlive += 1
        corpse = "1" if CORPSE in (msb.get(f, {}).get("treasure_name") or name or "") else "0"
        out.append((mp, name, lot, part, ent, aent, amdl, adir, ic, f, islive, corpse))
    # 🛑 DISTINCT, not totals. The first version of this print counted ROWS and called them "checks",
    # which is verbatim the CONTRIBUTING bug where resolved.len() counted locations and was read as
    # flags for three messages straight: 163 rows carry only 148 distinct flags, because several
    # treasure records share a lot. Both numbers are printed so neither can be misread for the other.
    dflag = {r[9] for r in out if r[9]}
    dlive = {r[9] for r in out if r[10] == "1"}
    dcorpse = {r[9] for r in out if r[10] == "1" and r[11] == "1"}
    print("  lot -> flag resolved            : %d rows / %d DISTINCT flags (of %d rows)"
          % (nflag, len(dflag), len(st["rows"])))
    print("  LIVE AP checks                  : %d rows / %d DISTINCT checks (corpses: %d distinct)"
          % (nlive, len(dlive), len(dcorpse)))

    if nflag == 0:
        sys.exit("FATAL: zero lots resolved to a flag -- the lot id space does not match flag_lots. A "
                 "join that matches nothing is a FAILURE, not a clean run. Nothing written.")

    if a.probe:
        print("\n--probe: nothing written.")
        return 0

    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# AUTO-GENERATED by tools/datamine_msb_gated_treasures.py -- DO NOT EDIT, re-emit.\n")
        fh.write("# MSB Event/Treasure records with StartDisabled=1: the item is not in the world\n")
        fh.write("# at map load. 🛑 THIS IS NOT A RISK LIST, and the cross-tab below is why.\n")
        for k in sorted(st["xtab"]):
            ic, sd = k.split("|")
            fh.write("#   InChest=%-2s StartDisabled=%-2s : %5d\n" % (ic, sd, st["xtab"][k]))
        _a = sum(v for k, v in st["xtab"].items() if k.startswith("0|"))
        fh.write("# %d of %d StartDisabled=1 records are InChest>=1; of the %d pickups NOT in a\n"
                 % (len(st["rows"]) - st["xtab"].get("0|1", 0), len(st["rows"]), _a))
        fh.write("#   container only %d is StartDisabled. The field tracks the CONTAINER, not access:\n"
                 % st["xtab"].get("0|1", 0))
        fh.write("#   an item in a closed chest is not in the world until the lid opens.\n")
        fh.write("# See tools/datamine_treasure_enablers.py + greenfield/treasure_enablers.tsv for the\n")
        fh.write("#   enabler join: 18 of 136 have any enabler, 13 of those are in-place, ONE is a\n")
        fh.write("#   genuine cross-region prerequisite (f580600 waits on 9146, Messmer, m21_01).\n")
        fh.write("# MEASURED THIS RUN: %d treasure records, %d gated w/ lot, %d resolved to a flag,\n"
                 % (st["tot"], len(st["rows"]), nflag))
        fh.write("#   %d rows = %d DISTINCT live AP checks (rows > checks: treasure records share\n"
                 % (nlive, len(dlive)))
        fh.write("#   lots). Gated-but-no-lot: %d. Unreadable: %d.\n" % (st["no_lot"], st["unparsed"]))
        fh.write("# ENTITY KEYS: `entity_id` is the Treasure EVENT's EntityID, `asset_entity_id` is\n")
        fh.write("#   the Part/Asset EntityID. EnableAssetTreasure is MEASURED to accept EITHER, so a\n")
        fh.write("#   consumer must try BOTH or it misses a family. Both are 0/empty on many rows --\n")
        fh.write("#   those treasures have NO entity handle and can never be script-enabled.\n")
        fh.write("# in_chest: 0 = loose pickup, 1 = inside a chest, 2 = item-glow/container.\n")
        fh.write("map_id\ttreasure_name\titem_lot_id\ttreasure_part\tentity_id\tasset_entity_id\t"
                 "asset_model\tpart_dir\tin_chest\tflag\tis_live_check\tis_corpse\n")
        for r in sorted(out):
            fh.write("\t".join(r) + "\n")
    print("\nwrote %s (%d rows)" % (a.out, len(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
