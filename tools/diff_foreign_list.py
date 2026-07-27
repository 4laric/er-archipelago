#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diff_foreign_list.py -- where is OUR derivation short? Measured against a list you already have.

Reads another randomizer's location list FROM YOUR OWN DISK, compares it to our corpus, and
reports where our derivation has gaps. It writes nothing, commits nothing, and cannot print a
foreign identifier. See PROVENANCE.md.

    python3 tools/diff_foreign_list.py PATH_TO_THEIR_LIST

WHY THIS SHAPE
--------------
Reading a foreign list to cross-check is fine; ingesting it is not. The distinction is not a
formality -- it is the difference between two very different acts:

    "they have 173 flags we lack, here they are, paste them in"   <- ingesting their curation
    "our derivation is short in Liurnia; go re-run our datamine"  <- finding OUR bug

Only the second is allowed here, and this tool is built so the first is not expressible: it holds
foreign flags in memory only long enough to bucket them, and there is NO option to print them.
The escape hatch is deliberately absent -- an --emit-flags flag would become the default way to
use the tool within a week.

That is also the right call independently of anyone's licence. A flag copied from a foreign list
is a hand entry we cannot regenerate, cannot stamp with an inputs_hash, and cannot defend under
CONTRIBUTING.md's "derive the datum" rule. Let the other project be the BUG REPORT; keep our own
datamine as the SOURCE.

WHAT IT TELLS YOU
-----------------
For every foreign entry we do not already have, the tool asks OUR OWN tables where that flag
lives (flag_lots / check_maps / msb_flag_region / shop_rows). The answer splits the gap in two,
and the split is the whole point:

  * OUR TABLES CAN PLACE IT  -> our datamine already SAW this flag and our pipeline dropped it.
                                This is a derivation bug, reachable with data we already have.
                                Re-run the relevant generator scoped to the named region.
  * OUR TABLES KNOW NOTHING  -> outside what our datamine currently reads. A tooling gap, not a
                                copying opportunity: extend the datamine, don't import the row.

INPUT FORMAT: structured first, scrape second, and it SAYS WHICH.
A location key of the shape `<id>,<n>:<flag>::` has the acquisition flag in field 1; the leading
field is a shop/lot id, NOT a flag. Blind scraping counts both and roughly doubles the apparent
gap -- measured on a synthetic list, 3240 keys scraped as 6469 "flags" and inflated the
unexplained bucket from 240 to 3300. So: if that grammar is present the tool parses it and takes
only the flag field; otherwise it falls back to scraping and LABELS the result as an upper bound
containing noise. A number this tool cannot stand behind is one it must not present as a finding.
"""
import argparse
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_check_browser import load_module_consts, read_tsv  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Elden Ring event flags are 4-10 digits. Below 1000 is almost always an index/count in these
# files, so the floor cuts noise without needing to know the foreign schema.
FLAG_RE = re.compile(r"\b(\d{4,10})\b")
FLAG_MIN = 1000
# `<shop-or-lot-id>,<n>:<10-digit acquisition flag>::` -- field 1 is the flag, field 0 is NOT.
KEYED_RE = re.compile(r"\b\d{4,7},\d+:(\d{10})::")


def extract_flags(path):
    """(flags, how) -- 'keyed' when the location-key grammar was found and parsed, 'scraped'
    when we fell back to pulling every plausible integer. The caller must report `how`: a
    scraped set contains ids that are not flags and its gap count is an UPPER BOUND."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    keyed = {int(m) for m in KEYED_RE.findall(text)}
    if keyed:
        return keyed, "keyed"
    return {int(m) for m in FLAG_RE.findall(text) if int(m) >= FLAG_MIN}, "scraped"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("foreign", help="path to the other project's list, ON YOUR DISK")
    ap.add_argument("--repo", default=REPO)
    args = ap.parse_args()

    gf = os.path.join(args.repo, "greenfield")
    er = os.path.join(gf, "eldenring")

    LOCATIONS = load_module_consts(os.path.join(er, "data.py"), {"LOCATIONS"})["LOCATIONS"]
    # A handful of flags carry TWO ap_ids (the co-check band), so location COUNT != flag COUNT.
    # Keying a dict on flag silently loses those; report both numbers rather than one wrong one.
    n_locations = sum(len(v) for v in LOCATIONS.values())
    ours = defaultdict(set)
    for region, v in LOCATIONS.items():
        for (_n, _a, f) in v:
            ours[f].add(region)

    foreign, how = extract_flags(args.foreign)
    if not foreign:
        print("No plausible event flags found in that file. Is it the right list?")
        return 1

    # --- where do OUR OWN tables think an unmatched flag lives? -----------------------
    # Order matters: the first table to claim a flag wins, so the most locator-rich table
    # is asked first. Everything here is OUR data -- the foreign file contributes only the
    # question "is this flag interesting", never an answer.
    placed = {}           # flag -> (our table that knows it, a locator string)
    for name, key, loc in (("flag_lots", "flag", "table"),
                           ("check_maps", "flag", "map_id"),
                           ("msb_flag_region", "flag", None),
                           ("shop_rows", "stock_flag", "region")):
        p = os.path.join(gf, name + ".tsv")
        if not os.path.exists(p):
            continue
        for row in read_tsv(p):
            try:
                f = int(row[key])
            except (KeyError, ValueError):
                continue
            if f in ours or f not in foreign or f in placed:
                continue
            where = ""
            if loc and row.get(loc):
                where = row[loc]
            else:
                for cand in ("region", "map_id", "map", "ap_region"):
                    if row.get(cand):
                        where = row[cand]
                        break
            placed[f] = (name, where or "(no locator column)")

    both = sorted(f for f in foreign if f in ours)
    theirs_only = sorted(f for f in foreign if f not in ours)
    ours_only = sorted(f for f in ours if f not in foreign)

    reachable = {f: placed[f] for f in theirs_only if f in placed}
    unreachable = [f for f in theirs_only if f not in placed]

    # ---------------------------------------------------------------------------------
    w = sys.stdout.write
    w("\n=== foreign list vs our corpus =================================================\n")
    w(f"  file                      {os.path.basename(args.foreign)}\n")
    if how == "keyed":
        w(f"  parsed                    location-key grammar (flag field only)\n")
        w(f"  distinct flags in it      {len(foreign)}\n")
    else:
        w(f"  parsed                    NO key grammar found -- SCRAPED every plausible integer\n")
        w(f"  candidate flags in it     {len(foreign)}   ⚠ UPPER BOUND: includes ids that are\n")
        w( "                                not event flags, so every 'not in ours' count below\n")
        w( "                                is inflated. Treat as a direction, not a number.\n")
    w(f"  our live checks           {n_locations}"
      + (f"   ({len(ours)} distinct flags; {n_locations - len(ours)} share a flag)\n"
         if n_locations != len(ours) else "\n"))
    w(f"  present in BOTH           {len(both)}\n")
    w(f"  in theirs, not in ours    {len(theirs_only)}\n")
    w(f"  in ours, not in theirs    {len(ours_only)}\n")

    w("\n--- the half that is OUR BUG ---------------------------------------------------\n")
    w(f"  {len(reachable)} of those {len(theirs_only)} are flags OUR OWN tables can already place.\n")
    w("  Our datamine saw them; our pipeline dropped them. Re-run the generator for these\n")
    w("  areas and the check should appear from vanilla data, with a stamp.\n\n")
    if reachable:
        by_table = Counter(t for t, _ in reachable.values())
        w("  which of our tables knows them:\n")
        for t, n in by_table.most_common():
            w(f"      {n:5d}  {t}.tsv\n")
        by_where = Counter(loc for _, loc in reachable.values())
        w("\n  where our tables say they are (top 20):\n")
        for loc, n in by_where.most_common(20):
            w(f"      {n:5d}  {loc}\n")
    else:
        w("      (none -- every gap is outside what our datamine currently reads)\n")

    w("\n--- the half that is a TOOLING GAP ---------------------------------------------\n")
    w(f"  {len(unreachable)} flags appear in neither our checks nor any of our datamine tables.\n")
    w("  Extend the datamine to reach them. Do NOT import the rows.\n")
    if how == "scraped":
        w("  ⚠ This bucket absorbs the scrape noise described above and is an UPPER BOUND.\n")

    w("\n--- where we are AHEAD ---------------------------------------------------------\n")
    w(f"  {len(ours_only)} live checks of ours are absent from their list.\n")
    if ours_only:
        by_region = Counter(r for f in ours_only for r in ours[f])
        for reg, n in by_region.most_common(10):
            w(f"      {n:5d}  {reg}\n")

    w("\n" + "=" * 80 + "\n")
    w("NO foreign identifier is printed above, by design -- see PROVENANCE.md. Act on a gap by\n")
    w("re-running OUR datamine for the area named, never by copying a row. tools/check_integrity.py\n")
    w("will refuse to commit a foreign list if one ends up staged.\n\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
