#!/usr/bin/env python3
"""strip_param_names.py -- blank the Name column of a Smithbox param CSV export.

WHY (2026-09-08, Elden Ring 2.7.1.0 patch day). Smithbox 2.2.5 exports row NAMES into the second
column. The dumps `gen_inputs.db` was built from had that column EMPTY (or the literal `null` in a
few system tables), so `tools/diff_gen_inputs.py` against a named export reports every row in every
table as changed -- and then crashes on `FaceParam`, because names carry commas, unbalanced quotes
(`23720,"368: Maleigh Marais,...`) and, in `TalkParam`, embedded newlines. Two hours of "what did the
patch change" were spent on an export option. Run this FIRST, then `gen_inputs.py --build`.

HOW. Rows are re-joined on "next line starts with <digits>," so a multi-line name is one row. Per
table the modal field count of plain rows gives R = fields after Name; every row keeps its ID, an
empty Name, and its LAST R fields, so a name with commas cannot shift the numeric columns. Nothing
else is rewritten: values, order and line endings are untouched.

    python tools/strip_param_names.py <export dir> elden_ring_artifacts/vanilla_er/vanilla_er
"""
from __future__ import annotations

import collections
import glob
import os
import re
import sys

ROW_START = re.compile(r"^-?\d+,")


def strip_file(src: str, dst: str) -> tuple[int, int]:
    txt = open(src, "rb").read().decode("utf-8")
    nl = "\r\n" if "\r\n" in txt else "\n"
    raw = txt.split(nl)
    hdr = raw[0]
    if hdr.split(",")[1:2] != ["Name"]:
        raise SystemExit(f"{src}: second column is not Name -- not a Smithbox param export")
    rows: list[str] = []
    joined = 0
    for line in raw[1:]:
        if ROW_START.match(line):
            rows.append(line)
        elif line == "" and (not rows or rows[-1] == ""):
            continue
        elif rows:
            rows[-1] += "\n" + line
            joined += 1
    rows = [r for r in rows if r != ""]
    counts = collections.Counter(
        len(r.split(",")) for r in rows if '"' not in r.split(",")[1] and "\n" not in r
    )
    mode = counts.most_common(1)[0][0] if counts else len(hdr.split(",")) - 1
    keep = mode - 2
    out = [hdr] + [r.split(",")[0] + ",," + ",".join(r.split(",")[-keep:]) for r in rows] + [""]
    open(dst, "wb").write(nl.join(out).encode("utf-8"))
    return len(rows), joined


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    src_dir, dst_dir = argv[1], argv[2]
    os.makedirs(dst_dir, exist_ok=True)
    total = joined = files = 0
    for path in sorted(glob.glob(os.path.join(src_dir, "*.csv"))):
        n, j = strip_file(path, os.path.join(dst_dir, os.path.basename(path)))
        total += n
        joined += j
        files += 1
    print(f"{files} table(s), {total} row(s), {joined} continuation line(s) re-joined -> {dst_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
