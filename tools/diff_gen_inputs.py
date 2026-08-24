#!/usr/bin/env python3
"""Diff two `gen_inputs.db` bundles — what a game patch actually changed in the params.

WHY
---
`gen_inputs.db` is a SNAPSHOT of the vanilla regulation (239 param CSVs, zlib blobs). When
FromSoftware patches the game we re-dump it from Smithbox and recompile the bundle — and then we
need to know what moved, because several of our features are pinned to facts about the OLD dump
that nothing re-checks on its own:

  * We REPURPOSE vanilla `SpEffectParam` rows at runtime (`no_equip_load` 20012080,
    `no_fall_damage` 20010827, `scadu_blessing` 20012081, `traps::no_flask` 20012082 -- the live
    registry is `er-logic/src/safe_speffect_rows.rs::CLAIMED`). Each was claimed on the strength of
    "occurs exactly once across all 239 param tables — as its own row". A patch that adds a
    reference to one of those rows makes us silently rewrite something the game reads, and the
    symptom is a BALANCE bug in one area weeks later, not a crash.
  * We index off ladders whose base id we read at runtime (`baseScaduBlessingSpEffectId`
    20000100..20000120, the DLC enemy-scaling ladder 20007000+10i). A patch that extends or
    re-points those changes what our arithmetic means.

`tools/verify_safe_speffect_row.py` answers "is this ONE row still safe" precisely. This answers
the broader "what changed, and did anything move into territory we depend on".

USAGE
-----
    # the OLD bundle comes out of git; the NEW one is the freshly recompiled file
    git show <rev>:gen_inputs.db > /tmp/old_gen_inputs.db
    python tools/diff_gen_inputs.py /tmp/old_gen_inputs.db gen_inputs.db

    python tools/diff_gen_inputs.py old.db new.db --only SpEffectParam --only EquipParamProtector
    python tools/diff_gen_inputs.py old.db new.db --watch-only     # skip the row diff, just the
                                                                   # id-range guard (fast)

Exit code 1 if anything landed in a WATCHED id range — i.e. "a human must look at this before
shipping". Row additions elsewhere are informational and exit 0. Read-only.
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sqlite3
import sys
import zlib
from collections import Counter
from pathlib import Path

PARAM_LIKE = "vanilla_er/vanilla_er/%.csv"

# ---------------------------------------------------------------------------------------------
# THE WATCH LIST. Ids we have built behaviour on top of. A NEW reference to any of these, from any
# param table, is the thing this tool exists to catch.
#
# Keep this in step with `er-logic/src/safe_speffect_rows.rs` (the repurposed rows) and with
# whatever reads a base id out of GameSystemCommonParam.
# ---------------------------------------------------------------------------------------------
WATCHED = [
    ("no_equip_load clone row", range(20012080, 20012081)),
    ("no_fall_damage clone row", range(20010827, 20010828)),
    ("scadu_blessing clone row", range(20012081, 20012082)),
    # Claimed 2026-08-10 by `traps::NoFlask` and MISSING from this list until 2026-08-24. The row is
    # rewritten at runtime exactly like the three above, so it carries the same silent-write hazard;
    # the drift test below now derives the claimed set from the registry instead of re-typing it.
    ("traps::no_flask clone row", range(20012082, 20012083)),
    ("Scadutree blessing ladder", range(20000100, 20000121)),
    ("Revered spirit-ash ladder", range(20000200, 20000231)),
    ("Revered Torrent ladder", range(20000300, 20000311)),
    ("DLC enemy-scaling ladder", range(20007000, 20007351)),
    # `er_logic::scaling` reads and CLEARS the DLC band family as well as the ladder
    # (`scaling.rs`: "20007400..20007750 is the band (haveSoulRate 2)", `BAND_TIERS`), and its own
    # declared window is `DLC_SCALING_ID_RANGE = 20007000..20008000`. Watch the band too.
    ("DLC enemy-scaling band", range(20007400, 20007751)),
]

# 🛑 NOT WATCHABLE BY THIS INSTRUMENT: the base-game scaling ladder/band
# (`er_logic::scaling::SCALING_ID_RANGE = 7000..8000`). The scan tokenises integers and tests
# membership, so four-digit ids collide with ordinary cell VALUES (counts, rates, ids of other
# kinds) in every one of the 239 tables -- a watch entry there would fire on essentially every
# patch and train the reader to ignore the guard. Those rows are covered by the informational row
# diff instead: `--only SpEffectParam` and read the changed-row list by hand.


def load(db: sqlite3.Connection, path: str) -> str:
    row = db.execute("SELECT blob FROM files WHERE path=?", (path,)).fetchone()
    return zlib.decompress(row[0]).decode("utf-8-sig", "replace") if row else ""


def param_paths(db: sqlite3.Connection) -> list[str]:
    return [p for (p,) in db.execute(
        "SELECT path FROM files WHERE path LIKE ? ORDER BY path", (PARAM_LIKE,))]


def rows_of(text: str):
    """(header, {id: row}). Returns (None, {}) for anything that doesn't parse as a param CSV."""
    if not text:
        return None, {}
    r = list(csv.reader(io.StringIO(text)))
    if not r:
        return None, {}
    return r[0], {row[0]: row for row in r[1:] if row}


def diff_table(old_txt: str, new_txt: str):
    oh, old = rows_of(old_txt)
    nh, new = rows_of(new_txt)
    added = sorted(set(new) - set(old), key=lambda s: int(s) if s.lstrip("-").isdigit() else 0)
    removed = sorted(set(old) - set(new), key=lambda s: int(s) if s.lstrip("-").isdigit() else 0)
    changed = []
    if oh == nh:
        for rid in set(old) & set(new):
            if old[rid] != new[rid]:
                cols = [nh[i] for i in range(min(len(oh), len(new[rid])))
                        if i < len(old[rid]) and old[rid][i] != new[rid][i]]
                changed.append((rid, cols))
    header_changed = (oh is not None and nh is not None and oh != nh)
    changed.sort(key=lambda t: int(t[0]) if t[0].lstrip("-").isdigit() else 0)
    return added, removed, changed, header_changed


# One compiled scan for ALL watched ids. The first version ran a separate regex per id -- ~415 ids
# x 2 texts x 9 MB per table -- and did not finish a single table inside 40s. Tokenise once and look
# up membership instead: one pass per text, and the cost stops depending on how many ids we watch.
WATCHED_IDS = {str(w): label for label, rng in WATCHED for w in rng}
_INT_TOKEN = re.compile(r"(?<![0-9])[0-9]+(?![0-9])")


def count_watched(text: str) -> Counter:
    c: Counter = Counter()
    for m in _INT_TOKEN.finditer(text):
        tok = m.group()
        if tok in WATCHED_IDS:
            c[tok] += 1
    return c


def watch_scan(old_txt: str, new_txt: str, table: str):
    """Every watched id whose OCCURRENCE COUNT rose in this table.

    Counting rather than presence is the point: a repurposed row already occurs once (as its own
    row), so presence alone would fire on every table that contains it. A COUNT that rises is a
    genuinely new reference -- which is the thing that would make us rewrite a row the game reads.
    """
    before, after = count_watched(old_txt), count_watched(new_txt)
    hits = []
    for tok, n_after in after.items():
        n_before = before.get(tok, 0)
        if n_after > n_before:
            hits.append((WATCHED_IDS[tok], int(tok), table, n_before, n_after))
    return sorted(hits, key=lambda h: h[1])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old", type=Path, help="the previous gen_inputs.db (git show <rev>:gen_inputs.db)")
    ap.add_argument("new", type=Path, help="the freshly recompiled gen_inputs.db")
    ap.add_argument("--only", action="append", default=[],
                    help="limit to param tables whose name contains this (repeatable)")
    ap.add_argument("--watch-only", action="store_true",
                    help="skip the row diff; only run the watched-id-range guard")
    ap.add_argument("--max-rows", type=int, default=12,
                    help="how many example row ids to print per table (default 12)")
    args = ap.parse_args()

    for p in (args.old, args.new):
        if not p.exists():
            sys.exit(f"{p} not found")
    o = sqlite3.connect(str(args.old))
    n = sqlite3.connect(str(args.new))

    op, np_ = param_paths(o), param_paths(n)
    if not np_:
        sys.exit("the NEW bundle has no param CSVs — wrong file?")
    names = sorted(set(op) | set(np_))
    if args.only:
        names = [p for p in names if any(f.lower() in p.lower() for f in args.only)]

    print(f"old: {args.old}  ({len(op)} param tables)")
    print(f"new: {args.new}  ({len(np_)} param tables)")
    if set(op) ^ set(np_):
        for p in sorted(set(np_) - set(op)):
            print(f"  + NEW TABLE  {p.split('/')[-1]}")
        for p in sorted(set(op) - set(np_)):
            print(f"  - GONE       {p.split('/')[-1]}")
    print(f"comparing {len(names)} table(s)\n")

    watch_hits, touched = [], 0
    for path in names:
        table = path.split("/")[-1]
        old_txt, new_txt = load(o, path), load(n, path)
        if old_txt == new_txt:
            continue
        touched += 1
        watch_hits += watch_scan(old_txt, new_txt, table)
        if args.watch_only:
            print(f"~ {table}")
            continue
        added, removed, changed, header_changed = diff_table(old_txt, new_txt)
        print(f"~ {table}")
        if header_changed:
            print("    !! COLUMN LAYOUT CHANGED — row-level comparison skipped for this table.")
            print("       Every downstream ordinal/offset assumption needs re-checking.")
        if added:
            print(f"    + {len(added)} new row(s): {', '.join(added[:args.max_rows])}"
                  + (" ..." if len(added) > args.max_rows else ""))
        if removed:
            print(f"    - {len(removed)} removed row(s): {', '.join(removed[:args.max_rows])}"
                  + (" ..." if len(removed) > args.max_rows else ""))
        if changed:
            print(f"    ~ {len(changed)} changed row(s)")
            for rid, cols in changed[:args.max_rows]:
                shown = ", ".join(cols[:6]) + (" ..." if len(cols) > 6 else "")
                print(f"        {rid}: {shown}")
            if len(changed) > args.max_rows:
                print(f"        ... and {len(changed) - args.max_rows} more")

    print(f"\n{touched} of {len(names)} table(s) differ.")
    print("=" * 88)
    if watch_hits:
        print("!! WATCHED ID RANGES GAINED REFERENCES — DO NOT SHIP UNTIL A HUMAN HAS LOOKED\n")
        for label, wid, table, before, after in watch_hits:
            print(f"  {wid}  ({label})  in {table}: {before} -> {after} occurrence(s)")
        print("\nWhat this means: an id we build behaviour on is now referenced somewhere it was")
        print("not before. If it is one of the repurposed clone rows, we would be rewriting a row")
        print("the game reads — a SILENT balance bug, not a crash. Re-run")
        print("`tools/verify_safe_speffect_row.py <id>` and claim a different row if it fails.")
        return 1
    print("ok  no watched id gained a reference. The repurposed rows and the ladders we index")
    print("    off are as unreferenced as they were before the patch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
