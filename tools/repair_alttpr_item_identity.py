"""Repair the verified ALttPR 1.5.0 item-identity bug without modifying Elden Ring.

Reads a user-supplied package, verifies the affected source hash, and writes a NEW
package. Does not download or distribute ALttPR code. See issue #1541 and the report.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from zipfile import ZipFile

MEMBER = "alttpr/Items.py"
SOURCE_SHA256 = "2c6f5b56c20d65d6f36edb52a99f73421acc01367ca4162faa70e438ef5c2bf6"


def repaired_source(source: bytes) -> bytes:
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError("Unrecognized ALttPR Items.py; only the verified 1.5.0 source is supported. "
                         "Already-repaired packages are also refused.")
    text = source.decode("utf-8")
    old = "filleritempool.remove(item)"
    if text.count(old) != 2:
        raise ValueError("Expected exactly two filler-removal sites")
    text = text.replace(old, "filleritempool.pop(next(i for i, candidate in "
                       "enumerate(filleritempool) if candidate is item))")
    old_progression = "if progitempool[i] == item and progitempool[i].location:"
    if text.count(old_progression) != 1:
        raise ValueError("Expected exactly one progression-removal site")
    text = text.replace(old_progression, "if progitempool[i] is item:")
    compile(text, MEMBER, "exec")
    return text.encode("utf-8")


def repair(source: Path, output: Path) -> str:
    if source.resolve() == output.resolve():
        raise ValueError("Output must differ from the original package")
    with ZipFile(source) as archive:
        entries = [(info, archive.read(info.filename)) for info in archive.infolist()]
        comment = archive.comment
    matching = [data for info, data in entries if info.filename == MEMBER]
    if len(matching) != 1:
        raise ValueError("Expected exactly one alttpr/Items.py member")
    fixed = repaired_source(matching[0])
    # Exclusive creation preserves an existing output and keeps the input untouched.
    with ZipFile(output, "x") as archive:
        archive.comment = comment
        for info, data in entries:
            archive.writestr(info, fixed if info.filename == MEMBER else data)
    with ZipFile(output) as archive:
        assert archive.testzip() is None
        for info, data in entries:
            assert archive.read(info.filename) == (fixed if info.filename == MEMBER else data)
    return hashlib.sha256(output.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Original alttpr.apworld")
    parser.add_argument("--output", type=Path, required=True, help="New repaired package path")
    args = parser.parse_args()
    digest = repair(args.source, args.output)
    print(f"Wrote {args.output}; sha256:{digest}")
    print("Only alttpr/Items.py changed. Keep the original as a backup outside custom_worlds; "
          "replace its installed copy with this file named alttpr.apworld.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
