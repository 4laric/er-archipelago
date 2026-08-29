#!/usr/bin/env python3
"""Generate release/latest.json from the channel and contract ledgers."""
import argparse
import json
import os
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANNELS = os.path.join(ROOT, "release", "CHANNELS.tsv")
CONTRACTS = os.path.join(ROOT, "release", "CONTRACT-VERSIONS.tsv")
OUT = os.path.join(ROOT, "release", "latest.json")


def _rows(path):
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            if line.strip() and not line.lstrip().startswith("#"):
                yield [part.strip() for part in line.rstrip("\n").split("\t")]


def render():
    stable = None
    for row in _rows(CHANNELS):
        if len(row) >= 2 and row[0] == "stable":
            stable = row[1]
    if not stable or not stable.startswith("v"):
        raise SystemExit("release/CHANNELS.tsv has no tagged stable channel")

    version = stable[1:]
    contracts = {row[0]: row[1] for row in _rows(CONTRACTS) if len(row) >= 2}
    contract = contracts.get(version)
    if not contract:
        raise SystemExit("release/CONTRACT-VERSIONS.tsv has no row for %s" % version)

    payload = {
        "version": version,
        "contract": contract,
        "url": "https://github.com/4laric/er-archipelago/releases/tag/%s" % stable,
    }
    return json.dumps(payload, separators=(", ", ": ")) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    text = render()

    if args.check:
        current = open(OUT, encoding="utf-8").read() if os.path.isfile(OUT) else None
        if current != text:
            print("DRIFT: release/latest.json is stale; run python tools/gen_latest_json.py")
            return 1
        print("--check: release/latest.json matches the channel and contract ledgers")
        return 0

    fd, temporary = tempfile.mkstemp(dir=os.path.dirname(OUT), prefix=".latest.json.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(temporary, OUT)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    print("wrote release/latest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
