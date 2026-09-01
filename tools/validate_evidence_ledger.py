#!/usr/bin/env python3
import argparse
from pathlib import Path
from evidence_ledger import LedgerError, summary

def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("directory",type=Path)
    args=parser.parse_args()
    try: result=summary(args.directory)
    except (LedgerError,OSError) as exc:
        print(f"evidence ledger INVALID: {exc}"); return 1
    print("evidence ledger OK: " + __import__("json").dumps(result, sort_keys=True)); return 0
if __name__ == "__main__": raise SystemExit(main())
