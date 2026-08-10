#!/usr/bin/env python3
r"""build_boss_region_worksheet.py -- the 83 bosses that stand between us and 395 ambiguous checks.

WHY A BOSS TABLE AND NOT A CHECK TABLE
--------------------------------------
`check_region_triage.tsv` (#524) lists 436 overworld checks whose region is a NEAREST-NEIGHBOUR
GUESS -- no grace on the tile, no PlayRegionParam row. Adjudicating them one by one is 436 research
tasks ("where is Smithing Stone [3] - near Ancient Ruins Base?").

395 of them are sweep members of just **83 bosses** -- 4.8 checks per decision, and the top 40
bosses cover 80%. "Where is Tibia Mariner" is a question a human can answer instantly.

⭐ THE REAL ARGUMENT IS NOT LABOUR, IT IS CIRCULARITY. A boss's region today is DERIVED from the
same tile machinery that regions the checks, so using it as evidence is circular exactly when it
would help. Measured over the 436:

    boss tile HAS a grace -> independent answer .... 166
    boss tile also graceless -> still a guess ...... 154
    boss on the SAME tile as the check (circular) ... 75
    no sweep boss at all ........................... 41

ASSERTING a boss's region breaks that dependency, so the 229 circular cases become answerable.
Deriving it harder never can.

🛑 A BOSS'S REGION IS NOT ALWAYS ITS CHECKS' REGION. That is #523: the Tree Sentinel stands on
Shadow Keep's measured ground (69300) while its 28 members are labelled Scadu Altus. So the column
you are filling is "the region that OWNS THIS BOSS'S CHECKS", NOT "where the boss stands". The
`arena_region` column shows where it stands, when that is even known -- where the two disagree,
say so in the reason.

COLUMNS
  ambiguous_checks   how many of the 436 ride this boss (the reason it is on the list)
  sweep_members      its whole sweep group, for scale
  derived_region     what ships TODAY (SWEEP_REGION)
  arena_region       BOSS_AREA_REGION, or ABSENT = unaudited, the #523 blind spot
  claimed_regions    the distinct regions its ambiguous checks currently claim; >1 = a straddle
  tile_has_grace     whether the boss's own tile carries first-hand evidence
  verdict            EMPTY -- for a human. Leave blank to accept derived_region.
  reason             EMPTY -- required when verdict differs; it is what the oracle reads.

🛑 EMITS A WORKSHEET, CONSUMES NOTHING. Nothing in gen reads it yet, deliberately: see the PR for
the two candidate consumption paths, which are NOT equivalent and want a decision first.

Run:  python3 tools/build_boss_region_worksheet.py [--emit]
"""
import argparse
import csv
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GF = os.path.join(ROOT, "greenfield")
OUT = os.path.join(GF, "boss_region_worksheet.tsv")


def _tile_from_entity(ent):
    """Tile decoded from the trigger id, for entries boss_healthbars does not key.

    10XXYY.... -> m60_XX_YY, 20XXYY.... -> m61_XX_YY, and 12XXYY.... -> m60_XX_YY: the 12-prefix
    ARENA form, whose fight lives in a dungeon while the trigger sits on an overworld tile. Decoding
    it is what a previous pass missed and lost an arena over. A worksheet row with no tile is a row
    a human cannot identify, so fill it even when the name is unknown.
    """
    s = str(ent)
    if len(s) == 10 and s[:2] in ("10", "12", "20"):
        return "m6%s_%s_%s" % ("1" if s[:2] == "20" else "0", s[2:4], s[4:6])
    return "?"


def _names_from_bundle():
    """{entity: name} via the EMEVD's own DisplayBossHealthBar nameId -> NpcName.fmg.xml.

    Reads gen_inputs.db DIRECTLY (plain sqlite, committed at the repo root) so this works with no
    artifacts extracted. boss_healthbars is keyed by DEFEAT FLAG, so duo partners and extra
    healthbar slots have no entry there -- and a worksheet that asks a human to rule on '?' is a
    worksheet that gets a wrong ruling.
    """
    db = os.path.join(ROOT, "gen_inputs.db")
    if not os.path.isfile(db):
        return {}
    import sqlite3, zlib
    con = sqlite3.connect(db)
    ids, txt = {}, {}
    for path, blob in con.execute("select path, blob from files where path like 'event/%'"):
        if os.path.basename(path).startswith("common"):
            continue
        t = zlib.decompress(blob).decode("utf-8", errors="replace")
        for m in re.finditer(r"DisplayBossHealthBar\(\s*(?:Enabled|1)\s*,\s*(\d+)\s*,\s*\d+\s*,\s*(\d+)", t):
            ids.setdefault(int(m.group(1)), int(m.group(2)))
    for path, blob in con.execute("select path, blob from files where path like '%NpcName%.fmg.xml'"):
        t = zlib.decompress(blob).decode("utf-8", errors="replace")
        for m in re.finditer(r'<text id="(\d+)"[^>]*>(.*?)</text>', t, re.S):
            v = m.group(2).strip()
            if v and v not in ("%null%", "[ERROR]"):
                txt.setdefault(int(m.group(1)), v)
    return {e: txt[n] for e, n in ids.items() if n in txt}


def _tbl(src, name):
    i = src.index(name + " = {")
    j = src.index("\n}", i)
    return {int(k): v for k, v in re.findall(r"(\d+):\s*'([^']*)'", src[i:j])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", action="store_true")
    args = ap.parse_args()

    tri_p = os.path.join(GF, "check_region_triage.tsv")
    if not os.path.isfile(tri_p):
        raise SystemExit("FATAL: %s missing -- run tools/triage_check_region_ambiguity.py --emit "
                         "first. An empty worksheet would look like 'no bosses need a ruling'."
                         % tri_p)
    tri = [r for r in csv.DictReader((l for l in open(tri_p, encoding="utf-8")
                                      if not l.startswith("#")), delimiter="\t")]

    sw = open(os.path.join(GF, "eldenring", "boss_sweeps.py"), encoding="utf-8").read()
    i, j = sw.index("DUNGEON_SWEEPS = {"), sw.index("\n}", sw.index("DUNGEON_SWEEPS = {"))
    trig, members = {}, Counter()
    for m in re.finditer(r"(\d+):\s*\[([^\]]*)\]", sw[i:j]):
        aps = [int(x) for x in m.group(2).replace("\n", "").split(",") if x.strip()]
        members[int(m.group(1))] = len(aps)
        for a in aps:
            trig[a] = int(m.group(1))
    SR, SAR = _tbl(sw, "SWEEP_REGION"), _tbl(sw, "SWEEP_ARENA_REGION")

    hb = open(os.path.join(GF, "eldenring", "boss_healthbars.py"), encoding="utf-8").read()
    META = {int(e): (t, c, n) for e, _g, t, c, n in re.findall(
        r"(\d+):\s*\('([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)'\)", hb)}
    graced = {l.split("\t")[1] for l in open(os.path.join(GF, "grace_flags.tsv"), encoding="utf-8")
              if l[:1].isdigit()}

    BUNDLE_NAME = _names_from_bundle()

    cover, claims = Counter(), defaultdict(set)
    orphan = 0
    for r in tri:
        b = trig.get(int(r["ap_id"]))
        if b is None:
            orphan += 1
            continue
        cover[b] += 1
        claims[b].add(r["region"])

    rows = []
    for b, n in cover.most_common():
        tile, cls, name = META.get(b, ("?", "?", "?"))
        name = BUNDLE_NAME.get(b) or name or "?"
        if tile == "?":
            tile = _tile_from_entity(b)
        arena = SAR.get(b, "ABSENT")
        overworld = tile[:3] in ("m60", "m61")
        # 🛑 ABSENT here is INFORMATION, not ignorance (Alaric, 2026-08-10): a boss with no fogwall
        # and no sealed arena has no PlayRegionParam boss-area overlay to derive one FROM. So the
        # arena audit's "112 of 219" is roughly the count of bosses that HAVE arenas, not a coverage
        # figure to chase. has_arena distinguishes the two readings.
        #   overworld + arena present  = the EXCEPTION: evergaols, castle/manor fog gates, set-piece
        #                                arenas. 22 of them, 16 in this sheet.
        #   overworld + ABSENT         = fogwall-less. The verdict is a GEOGRAPHY call.
        has_arena = "no" if arena == "ABSENT" else "yes"
        mismatch = "" if arena == "ABSENT" else ("MISMATCH" if arena != SR.get(b) else "ok")
        rows.append((b, name, tile, cls, n, members.get(b, 0),
                     SR.get(b, "?"), arena, has_arena, mismatch,
                     ";".join(sorted(claims[b])), "yes" if tile in graced else "no", "", ""))

    tot = sum(cover.values())
    print("boss region worksheet: %d boss(es) cover %d of %d ambiguous checks (%.1f per decision)"
          % (len(rows), tot, len(tri), tot / max(len(rows), 1)))
    print("  %d check(s) have NO sweep boss and stay per-check whatever you decide" % orphan)
    _noarena = sum(1 for r in rows if r[8] == "no")
    print("  %d boss(es) have NO ARENA (fogwall-less) -- their verdict is a GEOGRAPHY call" % _noarena)
    print("  %d have a real arena (evergaol / fog gate / set-piece); of those %d have arena != members"
          % (len(rows) - _noarena, sum(1 for r in rows if r[9] == "MISMATCH")))
    print("  %d boss(es) whose ambiguous checks claim MORE THAN ONE region (a straddle)"
          % sum(1 for r in rows if ";" in r[10]))
    cum = 0
    for k, r in enumerate(rows, 1):
        cum += r[4]
        if k in (10, 20, 40):
            print("    top %2d bosses cover %d checks (%.0f%%)" % (k, cum, 100 * cum / tot))
    print("\n  %-11s %-27s %-12s %4s %-14s %-14s %s"
          % ("boss", "name", "tile", "amb", "derived", "arena", "claimed"))
    for r in rows[:15]:
        print("  %-11d %-27s %-12s %4d %-14s %-14s %s"
              % (r[0], r[1][:27], r[2], r[4], r[6][:14], r[7][:14], r[9]))

    if args.emit:
        with open(OUT, "w", encoding="utf-8", newline="\n") as f:
            f.write("# WORKSHEET -- hand-fill `verdict` and `reason`. Nothing in gen reads this yet.\n")
            f.write("# verdict = the region that OWNS THIS BOSS'S CHECKS, which is NOT always where\n")
            f.write("#   the boss stands (#523: Tree Sentinel stands in Shadow Keep, its 28 members\n")
            f.write("#   are Scadu Altus). Blank verdict = accept derived_region.\n")
            f.write("# arena_region ABSENT = unaudited, no boss_area_regions row.\n")
            f.write("# tile_has_grace no = the boss's own region is a guess too, so its derived value\n")
            f.write("#   is NOT independent evidence -- those are the rows where a human is load-bearing.\n")
            f.write("boss_entity\tboss_name\ttile\tclass\tambiguous_checks\tsweep_members\t"
                    "derived_region\tarena_region\thas_arena\tarena_vs_members\t"
                    "claimed_regions\ttile_has_grace\tverdict\treason\n")
            for r in rows:
                f.write("\t".join(str(x) for x in r) + "\n")
        print("\n-> %s (%d rows)" % (OUT, len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
