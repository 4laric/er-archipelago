#!/usr/bin/env python3
"""datamine_spawn_traps.py -- every enemy a SPAWN TRAP can drop on top of the player.

WHY THIS EXISTS
---------------
A spawn trap needs THREE ids, not one. `WorldChrMan::spawn_debug_character` takes a chr model, an
`NpcParam` row (the body: hp, damage, drops) and an `NpcThinkParam` row (the brain -- without a live
one the creature stands there and does nothing). A yaml that names `c4150` therefore cannot be
handed to the client as-is; something has to resolve it, and that something is generation time,
here, off committed data, rather than the client guessing at runtime.

The Runebear (the first spawn trap, client PR #114) had its three ids derived BY HAND from
`msg/item-msgbnd-dcx/NpcName.fmg.xml`. 🛑 That route does not generalise: NpcName holds 532 rows
covering only **76 distinct models**, essentially bosses and named NPCs. The basilisk -- the
motivating case for this table -- is not in it, and neither are most enemies. A miss there is the
normal case, not evidence the creature does not exist.

THE DERIVATION
--------------
For every id in `ChrModelParam` (the authoritative list of character models):

    npc rows    = NpcParam rows whose ID // 10000 == chr
    think rows  = NpcThinkParam rows whose ID // 10000 == chr

A model is SPAWNABLE when all four hold:

    1. it has an NpcParam row at exactly `<chr>0000`   -- the family template
    2. it has an NpcThinkParam row at exactly `<chr>0000`
    3. not every one of its NpcParam rows has `hp == 0` -- those are props, not creatures
       (c4450 Walking Mausoleum, c4492 Greatjar, c5350 Basilisk Eyes, c8120 Merciless Chariot)
    4. `<chr>0000` is not the only thing we can say about it -- see the row choice below

390 of 416 real models qualify. The 26 that do not are enumerable rather than mysterious: 17 have
no think row at all (c2131 dead-Morgott, c4751 Godrick's corpse, c8101 wheeled ballista and so on),
and the rest are the props. 🛑 Refusing them HERE, at generation, is the whole point: the
alternative is a yaml that gens clean and mints an item which does nothing in-game forever.

WHICH NpcParam ROW
------------------
Prefer the row with the LOWEST POSITIVE `getSoul`, ties broken by lowest id, and fall back to the
`<chr>0000` template when no row in the family pays at all.

⭐ `getSoul` rather than the row id, because it is the one committed column that ORDERS a family by
strength. Every row shares one `hp`; the difficulty spread is the `spEffectID3` area-tier ladder
(basilisk: 7050 -> 130 souls, 7090 -> 357, 7130 -> 819), and `getSoul` rises with it. So the lowest
positive `getSoul` is the MILDEST paying variant -- which is what a trap wants, since a trap is
meant to be an inconvenience rather than a boss dropped on your head.

🛑 THE CONTROL, and the reason this rule is not just asserted: it independently reproduces the ONE
row that was derived by hand. The Runebear was hand-pinned to `46300010` in client PR #114 after a
person read the family; this rule picks `46300010` out of 21 rows without being told. A rule that
disagreed with the only known-good answer would be the wrong rule. `test_gf_spawn_traps` pins it.
(Sorting by row id instead also reproduces the bear -- but it picks `41500031` for the basilisk,
the 7090 rung, over the milder 7050 at `41500060`. The bear alone cannot discriminate the two
rules; the basilisk can, which is why both are pinned.)

⭐ That fallback is not free and the column says so. The template pays `getSoul 0`, so killing a
template-spawned creature earns nothing -- which is exactly why the Runebear was hand-pinned to
`46300010` rather than `46300000`. 303 of the 390 have a paying row; 87 do not and cannot.

The difficulty spread does NOT live in this choice. Every row in a family shares one `hp` (basilisk
338, runebear 2585); the spread is the `spEffectID3` area-tier ladder. So picking the paying row
changes what the kill pays, not how hard it is.

LABELS AND COUNTS
-----------------
`CURATED` is the only hand-written thing in this file, and it is deliberately tiny. An entry gives a
model a yaml key, a readable label and a horde size. Everything else gets the label `c<chr>` and a
count of 1, and is reachable only by raw id through the `spawn_traps` option.

🛑 A `yaml_key` is a PUBLIC OPTION VALUE. Adding one later is safe; REMOVING one is a compat break
that fails an old yaml (issue #114 rule 4). Never curate a name you might withdraw.
🛑 `LABEL_CAP` is a CROSS-REPO CONTRACT with `er_logic::traps::LABEL_CAP`. The client retains the
label inline so its `SpawnSpec` can stay `Copy`, and REFUSES a longer one rather than truncating --
a truncated label would silently rename the creature in the one line the player ever reads. This
tool must never emit one the client would refuse, so it asserts rather than trusting.

USAGE
-----
    python tools/datamine_spawn_traps.py            # regenerate greenfield/spawn_traps.tsv
    python tools/datamine_spawn_traps.py --check    # drift gate: exit 1 if the tsv is stale

Artifacts: reads `elden_ring_artifacts/vanilla_er/vanilla_er/` under the repo, the same staging
every other datamine tool uses. `--check` needs them too; it re-derives and compares.
"""
import argparse
import csv
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARAMS = os.path.join(REPO, "elden_ring_artifacts", "vanilla_er", "vanilla_er")
OUT = os.path.join(REPO, "greenfield", "spawn_traps.tsv")

#: Cross-repo contract with `er_logic::traps::LABEL_CAP`. See the module docstring.
LABEL_CAP = 24

#: chr_id -> (yaml_key, label, count). The ONLY hand-written data in this file.
#:
#: basilisk: c4150, the motivating case (issue #114). Three of them, because bobler's ask was
#: "enemy horde on your head" and one basilisk at zero range is trivially killable -- the threat is
#: the Death Blight mist, and mist wants numbers.
#: aging_untouchable: c5280, the Abyssal Woods madness enemy. One is already a serious trap: it is
#: invulnerable until parried, so a horde would turn an inconvenience into an arbitrary run-killer.
#: malenia: c2120, Malenia's phase-one model/body/brain. Her phase transition is driven by arena
#: EMEVD; a debug spawn of this template remains phase one, which is the trap promised by the yaml.
#: 🛑 c4630 (Runebear) is deliberately NOT curated: it already ships as the fixed item name
#: `Trap: Runebear`, which may never be withdrawn. It stays reachable here by raw id, and the two
#: names coexist rather than one shadowing the other.
CURATED = {
    2120: ("malenia", "Malenia (Phase 1)", 1),
    4150: ("basilisk", "Basilisk", 3),
    5280: ("aging_untouchable", "Aging Untouchable", 1),
}

HEADER = ["chr_id", "npc_param_id", "think_param_id", "count", "label", "yaml_key",
          "hp", "get_soul", "row_pays"]


def _rows(name):
    path = os.path.join(PARAMS, name)
    if not os.path.isfile(path):
        raise SystemExit(
            "FATAL: %s missing -- this tool needs elden_ring_artifacts staged.\n"
            "Run: python tools/gen_inputs.py --extract elden_ring_artifacts" % path)
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        rd = csv.DictReader(fh)
        for col in ("ID",):
            if col not in (rd.fieldnames or ()):
                raise SystemExit("FATAL: %s lacks column %r -- header is %r. A renamed column must "
                                 "fail loudly, not silently derive an empty table."
                                 % (name, col, rd.fieldnames))
        return list(rd)


def _num(row, col):
    try:
        return float(row[col])
    except (KeyError, TypeError, ValueError):
        return 0.0


def derive():
    """-> list of dict rows, sorted by chr_id. Pure: no I/O beyond the param reads."""
    models = sorted({int(r["ID"]) for r in _rows("ChrModelParam.csv")})
    npc, think = {}, {}
    for r in _rows("NpcParam.csv"):
        npc.setdefault(int(r["ID"]) // 10000, []).append(r)
    for r in _rows("NpcThinkParam.csv"):
        think.setdefault(int(r["ID"]) // 10000, set()).add(int(r["ID"]))

    out = []
    for chr_id in models:
        family = npc.get(chr_id, [])
        template = chr_id * 10000
        if not family:
            continue
        if not any(int(r["ID"]) == template for r in family):
            continue
        if template not in think.get(chr_id, set()):
            continue
        if all(_num(r, "hp") == 0 for r in family):
            continue  # a prop, not a creature

        # (getSoul, id) so the ORDER is by strength and the tie-break is deterministic.
        paying = sorted((_num(r, "getSoul"), int(r["ID"])) for r in family
                        if _num(r, "getSoul") > 0)
        npc_id = paying[0][1] if paying else template
        chosen = next(r for r in family if int(r["ID"]) == npc_id)

        key, label, count = CURATED.get(chr_id, ("", "c%d" % chr_id, 1))
        if len(label.encode("ascii", "strict")) > LABEL_CAP:
            raise SystemExit("FATAL: label %r for c%d is %d bytes; the client REFUSES anything over "
                             "LABEL_CAP=%d and would drop the trap silently."
                             % (label, chr_id, len(label), LABEL_CAP))
        out.append({
            "chr_id": chr_id,
            "npc_param_id": npc_id,
            "think_param_id": template,
            "count": count,
            "label": label,
            "yaml_key": key,
            "hp": int(_num(chosen, "hp")),
            "get_soul": int(_num(chosen, "getSoul")),
            # 🛑 A '0' here is not a defect, it is the honest state of 87 families: no row in the
            # family pays, so the kill cannot pay. Recorded so nobody re-derives it hopefully.
            "row_pays": 1 if paying else 0,
        })
    return out


def render(rows):
    lines = ["\t".join(HEADER)]
    for r in rows:
        lines.append("\t".join(str(r[c]) for c in HEADER))
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="drift gate: exit 1 if the committed tsv differs from a fresh datamine")
    args = ap.parse_args()

    rows = derive()
    text = render(rows)
    curated = sum(1 for r in rows if r["yaml_key"])
    pays = sum(r["row_pays"] for r in rows)

    if args.check:
        if not os.path.isfile(OUT):
            print("STALE: %s does not exist. Run: python tools/datamine_spawn_traps.py" % OUT,
                  file=sys.stderr)
            return 1
        with open(OUT, encoding="utf-8") as fh:
            if fh.read() != text:
                print("STALE: spawn_traps.tsv differs from a fresh datamine. "
                      "Run: python tools/datamine_spawn_traps.py", file=sys.stderr)
                return 1
        print("spawn_traps.tsv up to date (%d spawnable models, %d curated, %d with a paying row)"
              % (len(rows), curated, pays))
        return 0

    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("wrote %s -- %d spawnable models, %d curated, %d with a paying row"
          % (os.path.relpath(OUT, REPO), len(rows), curated, pays))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
