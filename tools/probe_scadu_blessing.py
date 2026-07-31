#!/usr/bin/env python3
"""Resolve the Scadutree / Revered blessing SpEffect ladders straight out of gen_inputs.db.

WHY
---
`docs/specs/RECON-scadutree-blessing-speffect-20260729.md` established the CHAIN --
`SpEffect = GameSystemCommonParam[0].baseScaduBlessingSpEffectId + <level>` -- but left three
things UNKNOWN because the agent sandbox had no way to read regulation.bin:

  1. the numeric value of the three base ids,
  2. the STRIDE (base + level vs base + level*10),
  3. WHICH SpEffectParam fields the ladder rows actually move.

All three are answerable from the committed bundle: gen_inputs.db carries the full 239-param
Smithbox CSV dump as zlib blobs. No game install, no Smithbox, no regulation.bin needed.

HOW IT ANSWERS THE STRIDE
-------------------------
Level 0 is the identity row (1.000x dealt / 1.000x received -- see
elden_ring_artifacts/scadufrags_per_level.txt). So we diff each candidate row against the base row
and print only the columns that MOVED. If stride is 1 you get a dense contiguous run of ~20 changed
rows; if it is 10 you get changes at base+10, base+20, ... and identical rows in between. The
output distinguishes them without anyone having to guess.

    A run of consecutive changed rows  -> stride 1
    Changes only every 10th id        -> stride 10
    Nothing changed anywhere          -> the chain is wrong; say so, do not rationalise it

USAGE (PowerShell)
------------------
    python tools\\probe_scadu_blessing.py
    python tools\\probe_scadu_blessing.py --db gen_inputs.db --span 40

Read-only. Touches nothing but the DB.
"""
from __future__ import annotations

import argparse
import csv
import io
import sqlite3
import sys
import zlib
from pathlib import Path

DELIMS = (";", ",", "\t", "|")

# The three base-id fields, from param_headers/param_columns.tsv ordinals 342 / 343 / 355.
BASE_FIELDS = (
    "baseScaduBlessingSpEffectId",
    "baseReveredSpiritAshBlessingSpEffectId",
    "baseReveredSpiritTorrentBlessingSpEffectId",
)


def load_csv(con: sqlite3.Connection, needle: str):
    """Return (path, header, {row_id: {col: val}}) for the one params CSV whose name matches needle.

    Raises on 0 or >1 matches -- an ambiguous match is a wrong answer waiting to happen.
    """
    rows = con.execute(
        "SELECT path, blob FROM files WHERE lower(path) LIKE ?", (f"%{needle.lower()}%",)
    ).fetchall()
    rows = [r for r in rows if r[0].lower().endswith(".csv")]
    if not rows:
        raise SystemExit(f"no CSV in the bundle matching {needle!r}")
    if len(rows) > 1:
        raise SystemExit(
            f"{needle!r} matched {len(rows)} CSVs, refusing to guess: "
            + ", ".join(p for p, _ in rows)
        )
    path, blob = rows[0]
    text = zlib.decompress(blob).decode("utf-8-sig", errors="strict")
    first = text.split("\n", 1)[0]
    delim = max(DELIMS, key=first.count)
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    header = list(reader.fieldnames or [])
    id_col = header[0]  # ordinal 0 is the row id in every Smithbox export
    table = {}
    for rec in reader:
        raw = (rec.get(id_col) or "").strip()
        try:
            table[int(raw)] = rec
        except ValueError:
            continue
    return path, header, table


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="gen_inputs.db", help="path to gen_inputs.db (default: repo root)")
    ap.add_argument("--span", type=int, default=25, help="how many ids past the base to probe")
    ap.add_argument("--show", metavar="ROWS",
                    help="ABSOLUTE dump mode: comma-separated SpEffectParam row ids. Prints the "
                         "lifetime/refresh fields verbatim instead of diffing. Use this when the "
                         "question is 'what is this field set to', not 'what changed' -- a diff "
                         "hides every field the whole ladder shares.")
    ap.add_argument("--show-fields", default=(
        "effectEndurance,motionInterval,cycleOccurrenceSpEffectId,replaceSpEffectId,"
        "stateInfo,effectTargetSelf,effectTargetFriend,effectTargetEnemy,"
        "invocationConditionsStateChange1,invocationConditionsStateChange2,"
        "invocationConditionsStateChange3,vfxId,iconId,category,saveCategory"),
                    help="comma-separated column names for --show (default: the lifetime set)")
    args = ap.parse_args()

    db = Path(args.db)
    if not db.is_file():
        raise SystemExit(f"{db} not found -- run from the repo root or pass --db")
    con = sqlite3.connect(str(db))

    if args.show:
        sp_path, header, sp = load_csv(con, "SpEffectParam")
        print(f"== SpEffectParam  <- {sp_path}  ({len(sp)} rows)   ABSOLUTE VALUES")
        want = [f.strip() for f in args.show_fields.split(",") if f.strip()]
        missing = [f for f in want if f not in header]
        if missing:
            print(f"   (not columns on this param, skipped: {', '.join(missing)})")
            want = [f for f in want if f in header]
        for raw in args.show.split(","):
            raw = raw.strip()
            if not raw:
                continue
            try:
                rid = int(raw)
            except ValueError:
                print(f"   {raw!r} is not an id")
                continue
            row = sp.get(rid)
            print(f"\n---- {rid} ----")
            if row is None:
                print("   ROW DOES NOT EXIST")
                continue
            name = (row.get("Name") or "").strip()
            if name:
                print(f"   Name: {name}")
            for f in want:
                print(f"   {f:<38} = {row[f]}")
        return 0

    gsc_path, _, gsc = load_csv(con, "GameSystemCommon")
    print(f"== GameSystemCommonParam  <- {gsc_path}")
    if 0 not in gsc:
        raise SystemExit(f"GameSystemCommonParam has no row 0 (rows present: {sorted(gsc)[:5]})")
    cfg = gsc[0]

    bases = {}
    for f in BASE_FIELDS:
        if f not in cfg:
            print(f"   {f:<46} ABSENT FROM THIS DUMP")
            continue
        try:
            bases[f] = int(cfg[f])
        except ValueError:
            print(f"   {f:<46} unparseable: {cfg[f]!r}")
            continue
        print(f"   {f:<46} = {bases[f]}")

    if not bases:
        print("\nNone of the three base fields are in this dump. The param headers say they exist")
        print("(param_columns.tsv ordinals 342/343/355), so the dump is older than the headers.")
        return 1

    sp_path, _, sp = load_csv(con, "SpEffectParam")
    print(f"\n== SpEffectParam  <- {sp_path}  ({len(sp)} rows)")

    for field, base in bases.items():
        print(f"\n---- {field} = {base} ----")
        if base not in sp:
            print(f"   !! row {base} does not exist in SpEffectParam. The chain assumption is WRONG.")
            continue
        ref = sp[base]
        changed_ids = []
        for off in range(0, args.span + 1):
            rid = base + off
            row = sp.get(rid)
            if row is None:
                print(f"   {rid:>10}  (absent)")
                continue
            diff = {k: (ref.get(k), v) for k, v in row.items() if ref.get(k) != v and k != "Name"}
            if not diff:
                print(f"   {rid:>10}  identical to base")
                continue
            changed_ids.append(rid)
            name = (row.get("Name") or "").strip()
            print(f"   {rid:>10}  +{off:<3} {name}")
            for k, (a, b) in sorted(diff.items()):
                print(f"                    {k} : {a} -> {b}")

        if changed_ids:
            offs = [i - base for i in changed_ids]
            contiguous = offs == list(range(offs[0], offs[0] + len(offs)))
            verdict = "STRIDE 1 (contiguous run)" if contiguous else f"NON-CONTIGUOUS: offsets {offs}"
            print(f"   => {len(changed_ids)} rows differ from base. {verdict}")
        else:
            print("   => nothing in this span differs from the base row. Widen --span or the chain is wrong.")

    print("\nNote: these are game-data values. Do NOT commit the output -- quote it in the recon doc")
    print("or, better, have the client read base_scadu_blessing_sp_effect_id() at runtime.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
