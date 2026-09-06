#!/usr/bin/env python3
"""Resolve copied native identities against static source data, never live flags."""
import argparse
import json
from export_mfg_check_registry import build


def resolve(manifest, original_flag=0, lot_table=None, lot_row=None):
    """Return every matching AP sibling, refusing contradictory supplied identities.

    Zero means native source does not know the original acquisition flag. A verified
    baked lot identity can still identify candidate flag groups. Runtime handles,
    current loot flags, item names and icon coordinates are not matching evidence.
    """
    if original_flag < 0:
        raise ValueError("original_flag must be zero (unknown) or positive")
    if (lot_table is None) != (lot_row is None):
        raise ValueError("lot_table and lot_row must be supplied together")
    if lot_table is not None and (lot_table not in ("map", "enemy") or lot_row < 0):
        raise ValueError("Invalid original lot identity")
    groups = {}
    if original_flag or lot_table is not None:
        for check in manifest["checks"]:
            flag = check["original_acquisition_flag"]
            if original_flag and flag != original_flag:
                continue
            if lot_table is not None and not any(
                lot["table"] == lot_table and lot["row_id"] == lot_row
                for lot in check["source_identity"]["item_lots"]
            ):
                continue
            groups.setdefault(flag, []).append(check["ap_id"])
    result = [{"original_acquisition_flag": flag, "ap_ids": sorted(ids)}
              for flag, ids in sorted(groups.items())]
    count = sum(len(group["ap_ids"]) for group in result)
    return {
        "status": "unmatched" if count == 0 else
                  "single_candidate" if count == 1 else "ambiguous_candidates",
        "groups": result,
        "evidence_kind": "static_source_identity_not_live_verified",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-flag", type=int, default=0)
    parser.add_argument("--lot-table", choices=("map", "enemy"))
    parser.add_argument("--lot-row", type=int)
    args = parser.parse_args()
    try:
        result = resolve(build(), args.original_flag, args.lot_table, args.lot_row)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
