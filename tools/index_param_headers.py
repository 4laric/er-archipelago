#!/usr/bin/env python3
"""Index the COLUMN NAMES of a Smithbox param CSV dump -- and nothing else.

WHY
---
Agents cannot see the param schema from the sandbox, so field names get GUESSED, and a guessed
field name is the exact failure this repo keeps paying for (AGENTS.md S4: three build round-trips
on wrong crate symbols; CONTRIBUTING "Data integrity -- no invented IDs"). A committed index of
which columns exist on which param answers "what is the per-slot category field on ITEMLOT_PARAM_ST"
by LOOKUP instead of by vibe.

GAME-DATA-FREE BY CONSTRUCTION
------------------------------
This reads **only the first line** of each CSV -- the header. No row is ever parsed, so no item id,
name, flag or stat can reach the output. That is what makes the result committable under the repo's
"never commit game data" rule. (Eyeball the output before you commit it anyway.)

Column TYPES are not in a CSV. If you point --paramdex at Smithbox's paramdef XML directory, each
column is annotated with its real declared type (s32/u8/f32/dummy8/...) from the def. Without it the
type column says UNKNOWN -- it does not guess (CONTRIBUTING: refusing to answer beats answering
confidently wrong).

USAGE (PowerShell)
------------------
    python tools\\index_param_headers.py $env:USERPROFILE\\Smithbox\\csv -o greenfield\\param_headers
    python tools\\index_param_headers.py C:\\dump\\csv --paramdex C:\\Smithbox\\Assets\\Paramdex\\ER\\Defs

OUTPUTS (3 files, under -o)
    param_columns.tsv     param, ordinal, column, type    -- the flat table
    param_index.json      {param: [column, ...]}          -- machine lookup
    column_to_params.tsv  column, n_params, params        -- REVERSE index: grep a name, find the param
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Smithbox writes ';' by default; other tools write ','. Sniffed per file, never assumed.
DELIMS = (";", ",", "\t", "|")


def sniff_header(path: Path):
    """Return (columns, delimiter). Reads ONE line. Raises on anything it cannot honestly parse."""
    with path.open("r", encoding="utf-8-sig", errors="strict", newline="") as fh:
        line = fh.readline()
    if not line.strip():
        raise ValueError("empty first line")
    delim = max(DELIMS, key=line.count)
    if line.count(delim) == 0:
        raise ValueError("no recognised delimiter in the header")
    cols = next(csv.reader([line], delimiter=delim))
    cols = [c.strip() for c in cols]
    if not any(cols):
        raise ValueError("header parsed to all-empty fields")
    return cols, delim


def load_paramdex(root: Path):
    """param name -> {field name: declared type}, from Smithbox's paramdef XML. Missing dir = {}."""
    types: dict[str, dict[str, str]] = {}
    files = sorted(root.rglob("*.xml"))
    if not files:
        sys.exit(f"--paramdex {root}: no .xml defs found -- refusing to run with a blind type source")
    for xml in files:
        try:
            tree = ET.parse(xml)
        except ET.ParseError as e:
            print(f"  [paramdex] SKIP {xml.name}: {e}", file=sys.stderr)
            continue
        fields = {}
        for f in tree.iter("Field"):
            decl = (f.findtext("Def") or f.get("Def") or "").strip()
            if not decl:
                continue
            # "s32 lotItemId01" / "dummy8 pad[3]" / "f32 weight = 1"
            head = decl.split("=")[0].strip().split()
            if len(head) < 2:
                continue
            vartype, name = head[0], head[1].split("[")[0].split(":")[0]
            fields[name] = vartype
        if fields:
            types[xml.stem] = fields
    return types


def main() -> int:
    ap = argparse.ArgumentParser(description="Index param CSV column names (headers only).")
    ap.add_argument("csv_dir", type=Path, help="directory of Smithbox-dumped param .csv files")
    ap.add_argument("-o", "--out", type=Path, default=Path("param_headers"), help="output directory")
    ap.add_argument("--paramdex", type=Path, default=None, help="Smithbox paramdef XML dir (for types)")
    ap.add_argument("--recursive", action="store_true", help="recurse into subdirectories")
    args = ap.parse_args()

    if not args.csv_dir.is_dir():
        sys.exit(f"{args.csv_dir}: not a directory")
    files = sorted((args.csv_dir.rglob if args.recursive else args.csv_dir.glob)("*.csv"))
    if not files:
        sys.exit(f"{args.csv_dir}: no .csv files found -- an empty input is a FAILURE, not a clean run")

    types = load_paramdex(args.paramdex) if args.paramdex else {}
    if args.paramdex:
        print(f"[paramdex] {len(types)} defs, {sum(len(v) for v in types.values())} typed fields")

    index: dict[str, list[str]] = {}
    reverse: dict[str, list[str]] = collections.defaultdict(list)
    rows: list[tuple[str, int, str, str]] = []
    skipped: list[tuple[str, str]] = []
    dupes: list[tuple[str, str, int]] = []
    untyped = 0

    for path in files:
        param = path.stem
        try:
            cols, delim = sniff_header(path)
        except (ValueError, UnicodeDecodeError, OSError) as e:
            skipped.append((path.name, str(e)))          # COUNTED, never silent
            continue
        seen = collections.Counter(cols)
        for name, n in seen.items():
            if n > 1 and name:
                dupes.append((param, name, n))
        index[param] = cols
        for i, col in enumerate(cols):
            vartype = types.get(param, {}).get(col, "UNKNOWN")
            if vartype == "UNKNOWN":
                untyped += 1
            rows.append((param, i, col, vartype))
            reverse[col].append(param)

    if not rows:
        sys.exit("every input file was skipped -- 0 columns indexed. That is a failure, not a result.")

    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "param_columns.tsv").open("w", encoding="utf-8", newline="") as fh:
        fh.write("param\tordinal\tcolumn\ttype\n")
        for r in rows:
            fh.write("%s\t%d\t%s\t%s\n" % r)
    (args.out / "param_index.json").write_text(
        json.dumps(index, indent=1, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    with (args.out / "column_to_params.tsv").open("w", encoding="utf-8", newline="") as fh:
        fh.write("column\tn_params\tparams\n")
        for col in sorted(reverse):
            ps = sorted(set(reverse[col]))
            fh.write("%s\t%d\t%s\n" % (col, len(ps), ",".join(ps)))

    # TALLY -- including what was dropped and why (CONTRIBUTING: a filter with no tally is a lie).
    print(f"[index] params {len(index)} | columns {len(rows)} | distinct column names {len(reverse)}")
    print(f"[index] typed {len(rows) - untyped} | UNKNOWN type {untyped}"
          + ("" if args.paramdex else "  (pass --paramdex to resolve)"))
    if dupes:
        print(f"[index] duplicate column names within a param: {len(dupes)} "
              f"(e.g. {dupes[:3]}) -- usually padding fields")
    if skipped:
        print(f"[index] SKIPPED {len(skipped)} of {len(files)} file(s):")
        for name, why in skipped:
            print(f"          {name}: {why}")
    print(f"[index] wrote -> {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
