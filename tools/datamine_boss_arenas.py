#!/usr/bin/env python3
"""Which healthbar heads share ONE fight? -- derived from the EMEVD defeat banner.

Emits greenfield/boss_arena_pairs.tsv: `secondary -> primary`, one row per healthbar entity whose
fight is REPORTED BY ANOTHER ENTITY on the same map.

WHY THIS TABLE EXISTS (#363)
----------------------------
gen_data's dungeon sweep keys its member list on the MAP and assigns it per ENTITY, so a map with
several healthbar heads handed every one of them the SAME list and the sweep paid out the whole
dungeon when ANY head flipped. bobler, 2026-08-04: seven Altus Tunnel checks granted 69 seconds
before the fight ended, after which the Crystalian he actually killed dropped nothing.

#364 suppressed the heads GameAreaParam covers (`game_areas.defeat_flag`), which is 3 of them. It
could not reach the rest, because `game_areas.tsv` is -- by its own header -- "A PARTITION, not
every boss": m34_14's second Fell Twin (34140851) has no row at all, and you cannot read an answer
off a row that does not exist.

THE DISCRIMINATOR: the defeat banner, not spawn geometry
--------------------------------------------------------
The handoff on #363 proposed MSB spawn distance (two heads in one room = one fight). That cannot be
computed where it has to run: `tools/gen_inputs.py --ensure` materialises 1452 files and NOT ONE of
them is an MSB -- `gen_inputs`'s own docstring says so ("the bundle carries what gen_data READS, not
the MSBs"). A discriminator that only works on a box with the full artifacts cannot gate CI.

The EMEVD ships in the bundle (589 files) and answers the question directly, with no threshold to
tune. `HandleBossDefeatAndDisplayBanner(P, EnemyFelled)` is the game declaring "this fight is over
and P is what reports it". So:

    m32_05  WaitFor(HPValue(32050800) <= 0 && HPValue(32050801) <= 0)
            HandleBossDefeatAndDisplayBanner(32050800)      -> ONE fight, 32050800 reports it
    m31_19  WaitFor(CharacterDead(31190800)); Banner(31190800)
            WaitFor(CharacterDead(31190850)); Banner(31190850)   -> TWO fights, keep both triggers

That is a SEMANTIC statement from the game's own script, not a proximity guess, and it decides the
control case (m31_19 Sage's Cave, Black Knife Assassin + Necromancer Garris) correctly by
construction rather than by a distance that happens to land right.

TWO EVIDENCE SHAPES
-------------------
`conjunct`    -- the secondary appears in the death condition guarding the primary's banner. The
                 game will not call the fight over until this head is dead too. (12 rows.)
`subordinate` -- the secondary carries a healthbar but its death is NOT required; a block guarded by
                 `EventFlag(primary)` force-kills it. m31_22 Spiritcaller Cave: the snail (31220800)
                 SUMMONS the Godskin Apostle and Noble, killing the snail ends the fight, and the
                 boss-appears event force-kills both summons when the snail's flag is set. (2 rows.)

🛑 THE THREE GUARDS, and what each one cost to learn
-----------------------------------------------------
1. The secondary must NOT be a banner primary anywhere on the map. This is the whole negative
   control: m31_19's two heads each fire their own banner, so neither can ever be a secondary. It
   also protects m30_05, m31_00 and m30_13 for free.
2. The primary must EXIST as a healthbar head ON THE SAME MAP -- the m30_20 regression (#364).
   Stray Mimic Tear is its map's only head; suppressing it cost m30_20 its entire sweep (aps
   7772247/7772248). A suppression may never take a map's last reporter.
3. `subordinate` requires the guarding flag to be a DIFFERENT head's. The idiom
   `if (EventFlag(X)) { ForceCharacterDeath(X) }` is the ordinary "boss already dead at map load"
   cleanup and appears on EVERY boss including both m31_19 heads; only a cleanup keyed on ANOTHER
   head's flag says anything about who reports the fight.

🛑 ABSENCE IS NEVER AN ANSWER. A map with no EMEVD, or with no banner at all, emits NO rows and is
   listed in the `unadjudicated_maps:` header line so gen_data can tell "the derivation says these
   heads are independent" apart from "the derivation could not look". Same discipline as
   arena_graces.tsv's `adjudicated_tiles:`.

Run:  python tools/gen_inputs.py --ensure elden_ring_artifacts
      python tools/datamine_boss_arenas.py [--inputs elden_ring_artifacts] [--report]
"""
import argparse
import importlib.util
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GF = os.path.join(ROOT, "greenfield")

# `$Event(id, Restart, function() { ... \n});` -- the generated JS puts the closing `});` of an event
# at column 0, which is what makes this non-greedy match safe against nested braces.
EVENT_RE = re.compile(r"\$Event\((\d+),\s*\w+,\s*function\(\)\s*\{(.*?)\n\}\);", re.S)
BANNER_RE = re.compile(r"HandleBossDefeatAndDisplayBanner\((\d+)\s*,")
# The conditions that mean "this character is dead". HPRatio is deliberately NOT here: it is used for
# phase transitions (`HPRatio(x) <= 0.6`), which is not a death.
DEATH_RE = re.compile(r"(?:CharacterHPValue|CharacterDead)\((\d+)\)")
FLAG_GUARD_RE = re.compile(r"if\s*\(EventFlag\((\d+)\)\)\s*\{")
FORCE_DEATH_RE = re.compile(r"ForceCharacterDeath\((\d+)\s*,")


def _load_healthbars():
    """BOSS_HEALTHBARS without importing the eldenring package (which needs Archipelago on sys.path)."""
    path = os.path.join(GF, "eldenring", "boss_healthbars.py")
    spec = importlib.util.spec_from_file_location("_bh", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.BOSS_HEALTHBARS


def _guarded_block(body, start):
    """Text of the `{...}` opened at `start` (index of the `{`), brace-matched."""
    depth = 0
    for i in range(start, len(body)):
        if body[i] == "{":
            depth += 1
        elif body[i] == "}":
            depth -= 1
            if depth == 0:
                return body[start:i]
    return body[start:]


# Sweep classes that key their member list on the MAP, which is the whole defect. FIELD bosses are
# deliberately out of scope: their members come from the NEIGHBORHOOD pass, which assigns every
# overworld filler check to exactly one nearest boss (test_field_sweeps_are_disjoint), so two field
# heads cannot share a list and there is nothing here to adjudicate. Their EMEVD is per-TILE
# (m60_XX_YY) rather than per-map anyway, so including them would report 22 maps as "no emevd" and
# bury the legacy heads that genuinely could not be resolved.
_SWEPT_BY_MAP = {"catacomb", "cave", "tunnel", "dungeon", "legacy"}


def adjudicate(event_dir, healthbars):
    """-> (rows, unadjudicated_maps, stats). rows = [(secondary, primary, bmap, event, evidence)]."""
    heads_by_map = defaultdict(set)
    for ent, info in healthbars.items():
        if info[2] in _SWEPT_BY_MAP:
            heads_by_map[info[0]].add(ent)

    rows, unadjudicated, stats = [], [], Counter()
    for bmap in sorted(heads_by_map):
        heads = heads_by_map[bmap]
        if len(heads) < 2:
            continue                                   # a lone head cannot duplicate a member list
        stats["multi_head_maps"] += 1
        path = os.path.join(event_dir, bmap + "_00_00.emevd.dcx.js")
        if not os.path.isfile(path):
            unadjudicated.append((bmap, "no emevd"))
            continue
        text = open(path, encoding="utf-8", errors="replace").read()

        # GUARD 1: every head that fires its OWN banner is a fight in its own right, forever.
        banner_primaries = {int(x) for x in BANNER_RE.findall(text)}
        # GUARD 2: ...and it must also be a head on this map, or suppression could point at a
        # reporter that carries no sweep and the map loses its coverage (the m30_20 regression).
        reporters = banner_primaries & heads
        if not reporters:
            unadjudicated.append((bmap, "no banner names a head of this map"))
            continue

        found = {}                                     # secondary -> (primary, event, evidence)
        for ev, body in EVENT_RE.findall(text):
            primaries = [int(x) for x in BANNER_RE.findall(body)]
            if primaries:
                # `conjunct`: the banner's own event will not fire until these heads are dead.
                primary = primaries[0]
                if primary in reporters:
                    for h in sorted((set(int(x) for x in DEATH_RE.findall(body)) & heads)
                                    - banner_primaries):
                        found.setdefault(h, (primary, int(ev), "conjunct"))
            # `subordinate`: a cleanup keyed on ANOTHER head's flag (GUARD 3).
            for m in FLAG_GUARD_RE.finditer(body):
                guard = int(m.group(1))
                if guard not in reporters:
                    continue
                block = _guarded_block(body, m.end() - 1)
                for h in sorted({int(x) for x in FORCE_DEATH_RE.findall(block)}
                                & heads - banner_primaries - {guard}):
                    found.setdefault(h, (guard, int(ev), "subordinate"))

        for h in sorted(found):
            primary, ev, evidence = found[h]
            rows.append((h, primary, bmap, ev, evidence))
            stats[evidence] += 1
        orphans = sorted(heads - banner_primaries - set(found))
        if orphans:
            unadjudicated.append((bmap, "heads with no banner and no link: %s"
                                  % ",".join(str(o) for o in orphans)))
    return rows, unadjudicated, stats


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inputs", default=os.path.join(ROOT, "elden_ring_artifacts"),
                    help="unpacked artifacts dir (default: ./elden_ring_artifacts)")
    ap.add_argument("--out", help="output path (default: greenfield/boss_arena_pairs.tsv)")
    ap.add_argument("--report", action="store_true", help="print the adjudication, write nothing")
    args = ap.parse_args()

    event_dir = os.path.join(args.inputs, "event")
    if not os.path.isdir(event_dir):
        sys.exit("FATAL: %s missing -- run `python tools/gen_inputs.py --ensure %s` first."
                 % (event_dir, args.inputs))

    healthbars = _load_healthbars()
    rows, unadjudicated, stats = adjudicate(event_dir, healthbars)

    if args.report:
        for sec, pri, bmap, ev, evidence in rows:
            print("  %-10d -> %-10d  %-8s ev%-9d %-12s %s"
                  % (sec, pri, bmap, ev, evidence, healthbars[sec][3] or "?"))
        for bmap, why in unadjudicated:
            print("  UNADJUDICATED %-8s %s" % (bmap, why))
        return 0

    # REFUSE TO EMIT A TABLE THAT WOULD SILENTLY SHRINK. Same discipline as arena_graces.tsv: this
    # set is a lower bound on a shipped fix, and an empty or collapsed emit hands every multi-head
    # arena back its duplicate sweep without anything going red.
    #
    # The floor is on the DUNGEON classes specifically, because those are the ones gen_data consults
    # -- a legacy row could legitimately move without any sweep changing, but losing a dungeon row
    # puts 111 checks back in reach of the wrong boss.
    dungeon = [r for r in rows if healthbars[r[0]][2] != "legacy"]
    if len(dungeon) < 15:
        sys.exit("FATAL: adjudicated only %d dungeon-class secondary head(s), floor 15. The EMEVD "
                 "has carried at least these since 2026-08-04 (m32_05 Crystalians through m34_14 "
                 "Fell Twins). Something moved in the event dump or in boss_healthbars.py -- do "
                 "not emit a shrunken table." % len(dungeon))

    out_path = args.out or os.path.join(GF, "boss_arena_pairs.tsv")
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# AUTO-GENERATED by tools/datamine_boss_arenas.py -- DO NOT EDIT, re-emit.\n")
        fh.write("# Healthbar heads whose fight is REPORTED BY ANOTHER HEAD on the same map (#363).\n")
        fh.write("# source: EMEVD HandleBossDefeatAndDisplayBanner + its death condition.\n")
        fh.write("#\n")
        fh.write("# evidence=conjunct    the primary's banner event waits on this head's death too\n")
        fh.write("#                      -- one fight, several bars (m32_05 Crystalian duo).\n")
        fh.write("# evidence=subordinate this head's death is not required; a block guarded by the\n")
        fh.write("#                      PRIMARY's flag force-kills it (m31_22: the Spiritcaller\n")
        fh.write("#                      Snail summons the Godskins, killing the snail ends it).\n")
        fh.write("#\n")
        fh.write("# 🛑 A head that fires its OWN banner is NEVER listed here, however close it\n")
        fh.write("#    stands: m31_19 Sage's Cave is Black Knife Assassin AND Necromancer Garris,\n")
        fh.write("#    two banners, two fights, and it must keep BOTH sweep triggers.\n")
        fh.write("# 🛑 LEGACY rows are ADJUDICATED BUT NOT CONSUMED. gen_data suppresses only the\n")
        fh.write("#    dungeon classes: legacy bosses take the round-robin DIVVY, which partitions a\n")
        fh.write("#    region's filler, so they never shared a member list and narrowing one out\n")
        fh.write("#    would reshape shares that are correct today. They are emitted because the\n")
        fh.write("#    region-capstone model has to count ARENAS, not healthbar entities.\n")
        fh.write("# 🛑 ABSENCE IS NOT AN ANSWER. A map that could not be adjudicated emits no rows\n")
        fh.write("#    and is named below; do not read its silence as 'independent heads'.\n")
        fh.write("# unadjudicated_maps: %s\n"
                 % (";".join("%s=%s" % (m, w) for m, w in unadjudicated) or "(none)"))
        fh.write("secondary\tprimary\tboss_map\tevent\tevidence\n")
        for sec, pri, bmap, ev, evidence in rows:
            fh.write("%d\t%d\t%s\t%d\t%s\n" % (sec, pri, bmap, ev, evidence))

    print("wrote %s  (%d secondary head(s), %d of them dungeon-class)" % (out_path, len(rows),
                                                                          len(dungeon)))
    print("  conjunct    : %d" % stats["conjunct"])
    print("  subordinate : %d" % stats["subordinate"])
    print("  multi-head maps seen: %d; unadjudicated: %d"
          % (stats["multi_head_maps"], len(unadjudicated)))
    for bmap, why in unadjudicated:
        print("    %-8s %s" % (bmap, why))
    return 0


if __name__ == "__main__":
    sys.exit(main())
