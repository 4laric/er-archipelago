#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""datamine_unplaced_globals.py -- give the UNPLACED common-event rows a tile, where the data can.

THE DEFECT (issue #249, reported in game: Thops still drops the vanilla Academy Glintstone Staff).
`region_map.csv` files a row as `Global / Common-event (unplaced)` when nothing decoded a tile for
its flag. gen_data then emits no location for it, `check_lots` never blanks the vanilla lot, and the
player gets the vanilla item. Nothing errors: the item simply is not a check.

This tool is the DERIVATION half. It does NOT hand-pin anything -- that is `GLOBAL_RECOVER`, which
exists for what no data can reach, and which this is meant to shrink rather than grow.

EVIDENCE, in precedence order (strongest first):
  1. `msb_flag_region.tsv` / `check_maps.tsv` -- an OBSERVED map for the flag.
  2. the lot -> talk-ESD join: `flag_lots.tsv` gives the flag's item lots, and the decompiled talk
     ESD is bucketed by map (`elden_ring_artifacts/talk/<map>-only/`), so an ESD that names the lot
     names the map its award fires in.

🛑 IT REFUSES, LOUDLY, IN TWO CASES, and the refusals are the point:
  * MORE THAN ONE map. NPCs relocate, so the ESD names every site they award from -- Dancer's
    Castanets is named in m16_00, m31_00 and m60_00. Picking one would be a confident wrong answer
    of exactly the kind CONTRIBUTING rule 1 is about, and a wrong region is worse than none: it
    asserts a reachability we do not have (see DEFAULTED_REGION_APS).
  * NO evidence at all. Measured 2026-08-04: 45 of 101 candidates, INCLUDING f400361, the Thops
    staff that motivated the issue. Its lots 103601/113601 are named by no talk ESD and no map
    EMEVD. This tool does not close #249; it reduces it, and prints what it could not reach.

Run:
    python3 tools/datamine_unplaced_globals.py            # report only
    python3 tools/datamine_unplaced_globals.py --emit     # write greenfield/unplaced_global_tiles.tsv
"""
import argparse
import ast
import collections
import csv
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GF = os.path.join(ROOT, "greenfield")
OUT = os.path.join(GF, "unplaced_global_tiles.tsv")
TALK = os.path.join(ROOT, "elden_ring_artifacts", "talk")
_COMMON_BUCKETS = {"m60_00_00_00", "m61_00_00_00", "m00_00_00_00"}


def _tsv(name, cols=2):
    out = collections.defaultdict(set)
    p = os.path.join(GF, name)
    if not os.path.isfile(p):
        return out, False
    for ln in open(p, encoding="utf-8"):
        if ln.startswith("#") or not ln.strip():
            continue
        c = ln.rstrip("\n").split("\t")
        if c and c[0].isdigit() and len(c) >= cols and c[1].strip():
            out[c[0]].add(c[1].strip())
    return out, True


def _gen_data_excludes():
    """Flags gen_data DELIBERATELY refuses, read textually out of gen_data.py (this tool is AP-free
    and must not import the world).

    Producer coverage and consumer coverage are different numbers, and this is where they diverged:
    the first emit placed 30207900 (Silver Scarab), which gen_data lists in `_UNREACHABLE_DEAD` --
    it sits behind an imp-statue door at the end of the Hidden Path to the Haligtree and is not
    obtainable. The table gained a row, the world gained no location, and only the end-to-end test
    noticed. Refuse it HERE too, so the two sides agree by construction rather than by luck."""
    txt = open(os.path.join(GF, "gen_data.py"), encoding="utf-8").read()
    # 🛑 EVERY named refusal set, not just the first. 2026-08-07: this read only _UNREACHABLE_DEAD,
    # so re-keying the de-dup onto lots proposed f1033477020 -- the PHANTOM 4th "Imbued Sword Key",
    # which gen_data drops via _RECOVER_PHANTOM_DUPES to keep a singleton key singular. Exactly the
    # Silver Scarab divergence this docstring already describes, one set over. Add new gen_data
    # refusal sets HERE when they appear.
    out, missing = set(), []
    for _name in ("_UNREACHABLE_DEAD", "_RECOVER_PHANTOM_DUPES", "_SHEET_DROPS",
                  "_UNPLACEABLE_DLC_COOKBOOKS"):
        m = re.search(_name + r"\s*=\s*frozenset\(\{([^}]*)\}\)", txt, re.S)
        if m:
            out |= {int(x) for x in re.findall(r"\d+", m.group(1))}
        else:
            missing.append(_name)
    if missing:
        print(f"  WARNING: could not read {', '.join(missing)} out of gen_data.py -- those "
              f"exclusions are NOT being honoured here, so this emit may contain rows the world "
              f"will drop.")
    return out


def _flag_lots():
    """flag(str) -> {(table, lot)} from greenfield/flag_lots.tsv -- the STRUCTURAL identity of an
    award row. Two flags sharing a (table, lot) pair are the same in-game award; two flags on
    different lots are separately collectable no matter how alike their item names look."""
    out = collections.defaultdict(set)
    p = os.path.join(GF, "flag_lots.tsv")
    if not os.path.isfile(p):
        return out
    with open(p, encoding="utf-8") as fh:
        rd = csv.DictReader(fh, delimiter="\t")
        for row in rd:
            f = (row.get("flag") or "").strip()
            t = (row.get("table") or "").strip()
            lot = (row.get("lot") or "").strip()
            if f.isdigit() and t and lot:
                out[f].add((t, lot))
    return out


def _existing_table():
    """Rows of the table as it stands, so candidates() can subtract its own previous output."""
    if not os.path.isfile(OUT):
        return []
    out = []
    for ln in open(OUT, encoding="utf-8"):
        if ln.startswith("#") or not ln.strip() or ln.startswith("flag\t"):
            continue
        c = ln.rstrip("\n").split("\t")
        if c and c[0].isdigit():
            out.append(c)
    return out


def candidates():
    """Unplaced rows that are not a check AND do not re-award an EXISTING check's ItemLotParam row.

    Both filters matter and both are counted by the caller.

    🛑 THE DE-DUP KEY IS THE LOT, NOT THE ITEM NAME (changed 2026-08-07). It used to drop any row
    whose `item_name` already appeared as a check under some other flag -- 62 rows, on the stated
    grounds that placing them "would DOUBLE-COUNT a single in-game pickup". That premise was false:
    of those 62, **61 sit on ItemLotParam rows DISTINCT from every name-twin and 0 share a lot**, so
    the rule was discarding real, separately-collectable checks whenever two sites happen to award
    the same common item (Golden Rune [1], Glowstone, Smithing Stone [1], Dragon Heart, ...).

    MOTIVATING CASE (rule 11): boblerrr, 2026-08-07, client 0.3.7. `Blessing of Marika` is awarded by
    lot 30950 (flag 530950, a real check) and lot 30935 (flag 530935, dropped by the name rule). He
    collected BOTH on one character -- `!flag` reads `true` for each -- and got a check from the
    first and the vanilla item from the second. One item name, two award rows, two pickups.

    A NAME match is not a SITE match. Two different lots are two different award events, so the only
    thing that proves "this is the same pickup" is sharing a lot. Where flag_lots.tsv knows no lot
    for a row we cannot prove distinctness, so those fall back to the old name rule and are counted
    separately -- conservative exactly where the evidence runs out."""
    rows = list(csv.DictReader(open(os.path.join(GF, "region_map.csv"), encoding="utf-8")))
    data = open(os.path.join(GF, "eldenring", "data.py"), encoding="utf-8").read()
    loc = ast.literal_eval(re.search(r"^LOCATIONS\s*=\s*(\{.*?\n\})", data, re.S | re.M).group(1))
    in_world = {str(f) for _r, v in loc.items() for (_n, _a, f) in v}
    # 🛑 SELF-EXCLUSION, or this tool ERASES ITS OWN TABLE.
    # A flag placed by the LAST emit is a check in data.py now, so the `in_world` filter below drops
    # it from the candidate set, and the next --emit writes a table without it. Measured the hard
    # way: the second run resolved "0 of 64" and wrote a 0-row file, silently reverting 36 checks to
    # dropping their vanilla item. A derivation whose input contains its own output must subtract
    # that output first, and `test_the_emit_is_idempotent` pins it.
    in_world -= {c[0] for c in _existing_table()}
    # BOTH self-exclusions, for the same reason: after an emit + regen, the flags this table placed
    # are checks in data.py, so they look like "already a check" (by flag) AND like "this item is
    # already a check under another flag" (by name -- their own). Subtract them from both or the
    # next --emit erases the table. The item-name one is the subtler half: it removed 36 rows on the
    # second run while `in_world` was already handled, and the run reported "0 of 64" as if the
    # corpora had moved.
    _mine = {c[0] for c in _existing_table()}
    item_seen = collections.Counter()
    for _r, v in loc.items():
        for (nm, _a, _f) in v:
            if str(_f) in _mine:
                continue
            body = nm.split(" :: ", 1)[1] if " :: " in nm else nm
            item_seen[re.sub(r"\s*\[f\d+\]$", "", body.split(" - ")[0]).strip()] += 1

    # flag -> {(table, lot)}: the STRUCTURAL identity of an award. Same subtraction of `_mine` as
    # item_seen above, and for the same self-erasure reason.
    lot_of = _flag_lots()
    claimed_lots = set()
    for _r, v in loc.items():
        for (_nm, _a, _f) in v:
            if str(_f) in _mine:
                continue
            claimed_lots |= lot_of.get(str(_f), set())
    _EXCLUDED = _gen_data_excludes()
    tally = collections.Counter()
    out = []
    for r in rows:
        if "unplaced" not in r["region"]:
            continue
        tally["unplaced rows"] += 1
        if r["flag"] in in_world:
            tally["  already a check"] += 1
            continue
        if not r["item_name"]:
            tally["  no item name on the row"] += 1
            continue
        _mylots = lot_of.get(r["flag"], set())
        if _mylots:
            if _mylots & claimed_lots:
                tally["  SAME ItemLotParam row as an existing check (genuinely one pickup)"] += 1
                continue
        elif item_seen.get(r["item_name"]):
            # No lot data either side -> distinctness is unprovable, so keep the old, more
            # conservative name rule for this row and COUNT it, so the blind spot stays visible.
            tally["  no lot data; item name already a check (name-rule fallback)"] += 1
            continue
        if int(r["flag"]) in _EXCLUDED:
            tally["  gen_data refuses it (named exclusion set) -- dead or a phantom dupe"] += 1
            continue
        tally["  CANDIDATE"] += 1
        out.append(r)
    return out, tally


def talk_index():
    """{lot id -> {map bucket}}, built once. Empty (and said so) when the artifacts are absent."""
    idx = collections.defaultdict(set)
    files = glob.glob(os.path.join(TALK, "*", "*.py"))
    if not files:
        return idx, 0
    num = re.compile(r"\b\d{4,10}\b")
    for p in files:
        bucket = os.path.basename(os.path.dirname(p)).replace("-only", "")
        try:
            txt = open(p, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        for n in set(num.findall(txt)):
            idx[n].add(bucket)
    return idx, len(files)


def resolve(cands):
    obs_msb, _ = _tsv("msb_flag_region.tsv")
    obs_cm, _ = _tsv("check_maps.tsv")
    lots, _have_lots = _tsv("flag_lots.tsv", cols=3)
    lots = collections.defaultdict(set)
    for ln in open(os.path.join(GF, "flag_lots.tsv"), encoding="utf-8"):
        c = ln.rstrip("\n").split("\t")
        if c and c[0].isdigit() and len(c) > 2:
            lots[c[0]].add(c[2])
    talk, n_talk = talk_index()
    rows, refused = [], collections.Counter()
    for r in cands:
        f = r["flag"]
        maps = set(obs_msb.get(f, ())) | set(obs_cm.get(f, ()))
        src = "observed"
        if not maps and n_talk:
            for lot in lots.get(f, ()):
                maps |= talk.get(lot, set())
            # 🛑 THE COMMON BUCKETS ARE NOT PLACES. `m60_00_00_00` / `m61_00_00_00` / `m00_00_00_00`
            # are where the talk ESD files an award that fires anywhere in that world, and they
            # exist in NO other corpus -- zero rows in check_maps.tsv, zero in msb_flag_region.tsv,
            # absent from map_names.tsv. Tile (00,00) is not a tile. Before this filter the emit
            # placed 8 checks at "m60_00_00_00", which reads like a location and is not one; the
            # count looked like a 43-row win. Drop them here, LOUDLY, rather than relying on a
            # downstream tile-prefix check to swallow them silently.
            maps -= _COMMON_BUCKETS
            src = "talk_esd"
        if not maps:
            if n_talk and any(talk.get(lot, set()) & _COMMON_BUCKETS for lot in lots.get(f, ())):
                refused["talk ESD names ONLY a common bucket (not a place)"] += 1
            else:
                refused["no evidence in ANY corpus"] += 1
            continue
        if len(maps) > 1:
            refused["ambiguous: %d maps (an NPC that relocates) -- REFUSED, not guessed" % len(maps)] += 1
            continue
        rows.append((f, next(iter(maps)), src, r["item_name"]))
    return rows, refused, n_talk


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", action="store_true", help="write greenfield/unplaced_global_tiles.tsv")
    args = ap.parse_args(argv)

    cands, tally = candidates()
    for k, v in tally.items():
        print("%-64s %d" % (k, v))
    if not cands:
        print("no candidates -- either everything is placed, or the filters collapsed. REFUSING to "
              "write an empty table (rule 2: an empty result is a failure, not a clean run).")
        return 1

    rows, refused, n_talk = resolve(cands)
    print("\ntalk ESD files indexed: %d%s" % (n_talk, "" if n_talk else
          "   <- ABSENT: run tools/gen_inputs.py --ensure elden_ring_artifacts, or the ESD half is BLIND"))
    print("resolved %d of %d candidate(s)" % (len(rows), len(cands)))
    by_src = collections.Counter(s for _f, _m, s, _n in rows)
    for k, v in sorted(by_src.items()):
        print("   %-10s %d" % (k, v))
    print("REFUSED %d:" % sum(refused.values()))
    for k, v in refused.most_common():
        print("   %-62s %d" % (k, v))

    if not args.emit:
        print("\n(report only -- pass --emit to write %s)" % os.path.relpath(OUT, ROOT))
        return 0
    if not rows:
        print("\nREFUSING to write an empty table (rule 2: an empty result is a failure, not a clean "
              "run). %d candidate(s) all refused -- if that is real, the corpora moved; if it is not, "
              "this tool just tried to erase %d existing row(s)."
              % (len(cands), len(_existing_table())))
        return 1
    rows.sort(key=lambda t: int(t[0]))
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# unplaced_global_tiles.tsv -- AUTO-GENERATED by tools/datamine_unplaced_globals.py.\n")
        fh.write("# DO NOT hand-edit: a hand pin belongs in gen_data.GLOBAL_RECOVER, where it is visible\n")
        fh.write("# as one. Rows here are DERIVED -- `source` says from what.\n")
        fh.write("#   observed = an MSB/check_maps map for the flag\n")
        fh.write("#   talk_esd = the flag's item lot is named by exactly ONE map's talk ESD\n")
        fh.write("# A flag whose evidence names MORE THAN ONE map is absent on purpose (NPCs relocate;\n")
        fh.write("# picking one would assert a reachability we do not have). So is a flag with no\n")
        fh.write("# evidence at all -- 45 of them, including f400361, the Thops staff of issue #249.\n")
        fh.write("flag\tmap_id\tsource\titem_name\n")
        for f, m, s, n in rows:
            fh.write("%s\t%s\t%s\t%s\n" % (f, m, s, n))
    print("\nwrote %s: %d row(s)" % (os.path.relpath(OUT, ROOT), len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
