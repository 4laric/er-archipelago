#!/usr/bin/env python3
r"""datamine_sweep_trigger_npcs.py -- the missing half of the #713 join: SWEEP TRIGGER FLAG -> the
`npc_param` ids the client's boss-fight probe prints.

WHY THIS EXISTS. `sweep_watch.rs` logs a FLAG (`sweep-watch: trigger flag 1034500800 -> SET`);
`boss_fight_probe.rs` logs an NPC PARAM (`boss-fight END: npc_param 45010040 outcome=BOSS DOWN`).
Both facts are on the same timeline and nothing joins them, which is why #697 -- a sweep that fired
with no boss fight anywhere near it -- had to be found by a human reading two line kinds side by
side. `tools/check_sweep_kill_correlation.py` is the correlator; this is the table it reads.

🛑 THE OBVIOUS JOIN DOES NOT EXIST AND IS NOT COMING. An MSB `Parts/Enemy` row carries EntityID and
NPCParamID on the SAME record, which would make this a one-hop lookup. `tools/gen_inputs.py` says
outright that the bundle carries what gen_data READS, "not the MSBs", and `datamine_boss_arenas.py`
already ran into the same wall on #363. So this table takes the two-hop route through data that IS
committed -- params + NpcName FMG -- and is honest about what that costs.

  UPDATE (#1000): the one-hop join now EXISTS, as a LOCAL-INPUT tool --
  `tools/gen_enemy_drop_entities.py` takes the WitchyBND-unpacked vanilla MSBs as an external
  argument and does exactly this lookup. Nothing above is wrong: the MSBs still are not in the
  bundle and never will be, so that tool cannot run in CI or on a fresh clone and this table stays
  the committed-data route. But if you have the MSBs on disk, do not re-derive the two-hop
  workaround -- read that tool first.

THE TWO HOPS

  1. flag -> chr, via the healthbar's `nameId`. `DisplayBossHealthBar(Enabled, ent, slot, nameId)`
     and ER encodes a boss name text id as `900000000 + chrId*1000 + variant`, so
     `chr = (nameId - 900000000) // 1000`. Measured: 214 of the 222 flags with a high nameId decode
     to a chr that exists in ChrModelParam.
     🛑 The nameId is NOT in `boss_healthbars.py` -- `_write` emits `(map, tile, class, name)` only.
     We therefore import `datamine_boss_healthbars.datamine()` and read `nameId` off the live dict
     rather than reversing the NAME STRING back through the FMG. That reversal was measured at
     210/244 exact and 13 ambiguous, and a join on a name is what this codebase forbids twice over
     (`flag_lots.tsv` on `name`; *an id that resolves is not a table match*).

  2. chr -> npc_param, via `NpcParam.isSoulGetByBoss`. 315 of 7039 rows are marked game-side as
     "this row's runes come from the boss award", which is the boss-row filter. Row ids encode the
     chr as `(ID // 10000) % 10000` -- the `% 10000` is load-bearing, 764 rows are 9 digits
     (`523090000` is chr 2309, not chr 52309).

  🛑 `nameId` ON THE BOSS ROW IS 0. `NpcParam 45010040` (Decaying Ekzykes) carries `nameId=0`: the
  name is passed by the EVENT, not held on the row, which is why the tempting
  `healthbar.nameId == NpcParam.nameId` join lands only 5 of 244. It survives here only as the
  THIRD fallback, for human NPCs whose healthbar nameId is a low id (Leda, Dane, Freyja, Patches).

⭐ THE RESULT IS A CANDIDATE SET, NOT AN ID, AND THAT IS THE POINT. A chr family routinely holds
several npc_param rows (one flag resolves to 10 of them), and several flags routinely share a chr
(Adula and Smarag are both chr 4502 on m60_34). The correlator asks "did a kill of ANY row in this
trigger's family land near the sweep?", so a wide set is LENIENT: it can miss a real defect, it
cannot invent one. A correlator that cried wolf would be turned off in a week; one that under-reports
still catches #697, where no boss fight was logged at all.

COVERAGE, measured 2026-08-16 over all 244 healthbar keys:
    chr_boss   208   chr decoded, isSoulGetByBoss rows found      -- the good case
    nameid      16   low nameId matched NpcParam.nameId           -- human NPCs
    chr_all     11   chr decoded but NO isSoulGetByBoss row; fall back to the whole chr family
    UNRESOLVED   9   emitted with an empty npc_params and a reason
The 9 are enumerable and 4 of them are the unnamed triggers `contract._UNNAMED_TRIGGER_REASON`
already skips. 🛑 An UNRESOLVED row is emitted rather than dropped: the correlator must be able to
say "this sweep cannot be adjudicated", which is a different answer from "this sweep is fine", and a
missing row would read as the latter.

TIER 2 (AGENTS §5a): needs `elden_ring_artifacts/` (event js + msg FMG + vanilla params). Run by
hand, commit the tsv, and only then does anything downstream see it.

    python3 tools/datamine_sweep_trigger_npcs.py            # emit greenfield/sweep_trigger_npcs.tsv
    python3 tools/datamine_sweep_trigger_npcs.py --list     # print the table, write nothing
"""
import argparse
import collections
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.dirname(HERE)
sys.path.insert(0, HERE)

AR = os.path.join(REPO, "elden_ring_artifacts")
NPC_PARAM = os.path.join(AR, "vanilla_er", "vanilla_er", "NpcParam.csv")
OUT = os.path.join(REPO, "greenfield", "sweep_trigger_npcs.tsv")

HEADER = ["trigger_flag", "map", "tile", "class", "name", "chr_id", "method", "n_candidates",
          "npc_params"]
MIN_TRIGGERS = 244
MIN_RESOLVED_TRIGGERS = 235


def validate_census(resolved):
    resolved_count = sum(r["method"] != "UNRESOLVED" for r in resolved.values())
    short = []
    if len(resolved) < MIN_TRIGGERS:
        short.append("triggers=%d (floor %d)" % (len(resolved), MIN_TRIGGERS))
    if resolved_count < MIN_RESOLVED_TRIGGERS:
        short.append("resolved=%d (floor %d)" % (resolved_count, MIN_RESOLVED_TRIGGERS))
    if short:
        raise SystemExit("datamine_sweep_trigger_npcs: REFUSED incomplete census: %s. Nothing "
                         "written." % ", ".join(short))


def _chr_from_name_id(name_id):
    """`900000000 + chr*1000 + variant` -> chr, or None when the id is not in that space.

    The low-id space (`132900` Lionel, `141800` Leda) is ordinary NPC text and carries no chr at
    all; it is handled by the nameId fallback, not here.
    """
    if name_id and name_id >= 900_000_000:
        return (name_id - 900_000_000) // 1000
    return None


def load_npc_param():
    """Three indices over NpcParam: boss rows by chr, ALL rows by chr, and rows by their own nameId.

    Returns `(by_chr_boss, by_chr_all, by_name_id)`, each `{key: [npc_param_id, ...]}` sorted.
    """
    by_chr_boss = collections.defaultdict(list)
    by_chr_all = collections.defaultdict(list)
    by_name_id = collections.defaultdict(list)
    with open(NPC_PARAM, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                pid = int(row["ID"])
            except (KeyError, TypeError, ValueError):
                continue
            chr_id = (pid // 10000) % 10000
            by_chr_all[chr_id].append(pid)
            if row.get("isSoulGetByBoss") == "1":
                by_chr_boss[chr_id].append(pid)
            name_id = (row.get("nameId") or "").strip()
            if name_id and name_id not in ("0", "-1"):
                by_name_id[int(name_id)].append(pid)
    for idx in (by_chr_boss, by_chr_all, by_name_id):
        for k in idx:
            idx[k].sort()
    return by_chr_boss, by_chr_all, by_name_id


def resolve(bosses, by_chr_boss, by_chr_all, by_name_id):
    """{trigger flag: dict} with `chr_id`, `method` and the candidate `npc_params` filled in.

    The fallback ORDER is the confidence order, and it is not arbitrary: a chr that has rows the
    game itself marks as boss rows is the strongest evidence available without MSBs; the whole chr
    family is weaker but still a real constraint; a nameId match is last because it is the one that
    lands 5/244 on bosses and only works at all for human NPCs.
    """
    out = {}
    for flag, b in sorted(bosses.items()):
        name_id = b.get("nameId")
        chr_id = _chr_from_name_id(name_id)
        if chr_id is not None and by_chr_boss.get(chr_id):
            method, params = "chr_boss", by_chr_boss[chr_id]
        elif chr_id is not None and by_chr_all.get(chr_id):
            method, params = "chr_all", by_chr_all[chr_id]
        elif name_id and by_name_id.get(name_id):
            method, params = "nameid", by_name_id[name_id]
        else:
            method, params = "UNRESOLVED", []
        out[flag] = {
            "map": b.get("map", ""),
            "tile": b.get("tile", ""),
            "class": b.get("class", ""),
            "name": b.get("name", ""),
            "chr_id": chr_id,
            "method": method,
            "npc_params": params,
        }
    return out


def _rows(resolved):
    for flag, r in sorted(resolved.items()):
        yield [
            str(flag),
            r["map"],
            r["tile"],
            r["class"],
            r["name"],
            "" if r["chr_id"] is None else str(r["chr_id"]),
            r["method"],
            str(len(r["npc_params"])),
            ";".join(str(p) for p in r["npc_params"]),
        ]


def _write(resolved):
    counts = collections.Counter(r["method"] for r in resolved.values())
    with open(OUT, "w", newline="\n", encoding="utf-8") as f:
        f.write("# AUTO-GENERATED by tools/datamine_sweep_trigger_npcs.py -- DO NOT EDIT, re-emit.\n")
        f.write("# Sweep trigger flag -> the npc_param ids `boss-fight` probe lines can carry for\n")
        f.write("# that trigger's boss. Read by tools/check_sweep_kill_correlation.py (#713).\n")
        f.write("#\n")
        f.write("# method=chr_boss   nameId -> chr -> NpcParam rows with isSoulGetByBoss=1. Strongest.\n")
        f.write("# method=chr_all    chr decoded but no boss-marked row; the whole chr family. Weaker.\n")
        f.write("# method=nameid     healthbar nameId matched NpcParam.nameId. Human NPCs only.\n")
        f.write("# method=UNRESOLVED no candidate set. 🛑 NOT a pass -- the correlator must report\n")
        f.write("#                   these as UNJUDGED, never fold them into the clean count.\n")
        f.write("#\n")
        f.write("# 🛑 npc_params is a CANDIDATE SET, not an identity. Several flags share a chr\n")
        f.write("#    (Adula and Smarag are both 4502 on m60_34) and one chr holds up to 10 rows.\n")
        f.write("#    A wide set makes the correlator LENIENT: it can miss a defect, not invent one.\n")
        f.write("#\n")
        f.write("# method counts: %s\n" % ", ".join(
            "%s=%d" % (k, counts[k]) for k in ("chr_boss", "chr_all", "nameid", "UNRESOLVED")))
        f.write("\t".join(HEADER) + "\n")
        for row in _rows(resolved):
            f.write("\t".join(row) + "\n")
    return counts


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true",
                    help="print the table and the unresolved roll-call, write nothing")
    args = ap.parse_args()

    if not os.path.isdir(AR):
        raise SystemExit(
            "elden_ring_artifacts/ is absent -- this is a Tier-2 datamine (AGENTS §5a) and needs "
            "the event js + msg FMG + vanilla params. Run it on the box and commit the tsv.")

    import datamine_boss_healthbars as hb
    bosses = hb.datamine()
    resolved = resolve(bosses, *load_npc_param())
    validate_census(resolved)
    counts = collections.Counter(r["method"] for r in resolved.values())

    if args.list:
        print("\t".join(HEADER))
        for row in _rows(resolved):
            print("\t".join(row))
    else:
        _write(resolved)
        print("[sweep_trigger_npcs] wrote %s (%d triggers)" % (OUT, len(resolved)))

    print("[sweep_trigger_npcs] method: " + ", ".join(
        "%s=%d" % (k, counts[k]) for k in ("chr_boss", "chr_all", "nameid", "UNRESOLVED")))
    # The roll-call is printed EVERY run, not only on --list. An unresolved count that grows is a
    # thing to notice at emit time; discovering it later, from a correlator that quietly judged
    # nothing, is how an instrument rots.
    for flag, r in sorted(resolved.items()):
        if r["method"] == "UNRESOLVED":
            print("[sweep_trigger_npcs] UNRESOLVED %d (%s, %s): %s" % (
                flag, r["class"], r["map"], r["name"] or "no healthbar name"))


if __name__ == "__main__":
    main()
