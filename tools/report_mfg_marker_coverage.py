#!/usr/bin/env python3
"""Compare source-generated marker identities with AP candidates, not live coverage."""
import argparse
from collections import defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path

from build_mfg_check_registry import ROOT, build


def report(manifest, marker_csv):
    """Consume the native export's numeric lot namespace (0 unknown, 1 map, 2 enemy)."""
    reader = csv.DictReader(io.StringIO(marker_csv.decode("utf-8-sig")))
    if reader.fieldnames != ["marker_row_id", "lot_table", "lot_row"]:
        raise ValueError("Expected marker_row_id,lot_table,lot_row CSV header")
    markers = []
    seen = set()
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ValueError("Malformed marker CSV row")
        try:
            marker_id, table, lot = (int(row[key]) for key in reader.fieldnames)
        except ValueError as error:
            raise ValueError("Marker fields must be integers") from error
        if not 0 < marker_id < 2**64 or marker_id in seen:
            raise ValueError("Invalid or duplicate marker_row_id")
        if table not in (0, 1, 2) or not 0 <= lot < 2**32 or ((table == 0) != (lot == 0)):
            raise ValueError("Invalid lot identity; unknown must be paired 0,0")
        seen.add(marker_id)
        markers.append((marker_id, table, lot))
    if not markers:
        raise ValueError("Empty marker inventory")
    # Inverted index retains every check in each acquisition-flag group.
    candidates = defaultdict(lambda: defaultdict(set))
    all_checks = set()
    for check in manifest["checks"]:
        ap_id = check["ap_id"]
        all_checks.add(ap_id)
        for lot in check["source_identity"]["item_lots"]:
            candidates[(lot["table"], lot["row_id"])][
                check["original_acquisition_flag"]].add(ap_id)
    matched_checks = set()
    counts = defaultdict(int)
    mappings = []
    for marker_id, table, lot in sorted(markers):
        groups = candidates.get(({1: "map", 2: "enemy"}.get(table), lot), {})
        ids = set().union(*groups.values()) if groups else set()
        if table == 0:
            status = "unknown_identity"
        elif not ids:
            status = "unmatched"
        elif len(ids) == 1:
            status = "single_check_candidate"
        elif len(groups) == 1:
            status = "shared_flag_candidates"
        else:
            status = "multiple_flag_candidates"
        counts[status] += 1
        matched_checks.update(ids)
        mappings.append({
            "marker_row_id": marker_id, "lot_table": table, "lot_row": lot,
            "status": status,
            "groups": [{"original_acquisition_flag": flag, "ap_ids": sorted(ap_ids)}
                       for flag, ap_ids in sorted(groups.items())],
        })
    return {
        "schema_version": 1,
        "evidence_kind": "static_baked_marker_candidates_not_live_or_corroborated",
        "marker_csv_sha256": hashlib.sha256(marker_csv).hexdigest(),
        "registry_sources_sha256": manifest["sources_sha256"],
        "total_checks": len(all_checks),
        "checks_with_candidate_markers": sorted(matched_checks),
        "checks_without_candidate_markers": sorted(all_checks - matched_checks),
        "total_markers": len(markers),
        "marker_status_counts": dict(sorted(counts.items())),
        "markers": mappings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("marker_csv", type=Path)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = report(build(args.repo), args.marker_csv.read_bytes())
    except ValueError as error:
        parser.error(str(error))
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "checks_with_candidate_markers": len(result["checks_with_candidate_markers"]),
        "checks_without_candidate_markers": len(result["checks_without_candidate_markers"]),
        "marker_status_counts": result["marker_status_counts"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
