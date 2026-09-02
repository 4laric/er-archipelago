#!/usr/bin/env python3
"""Resolve repeated Eldenpedia loot names with exact location and map-lot evidence.

This is deliberately narrower than a fuzzy place matcher.  A lead requires one immutable
Eldenpedia location page, an exact Notable Loot link, one current same-region AP candidate whose
description contains that page title as a whole phrase, and a matching v1.17 map-lot flag claim.
The result remains external discovery evidence and never becomes access logic.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
import importlib.util
from io import StringIO
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TOOLS = str(ROOT / "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
from build_eldenpedia_location_leads import (  # noqa: E402
    REGIONS, ap_item_name, links, load_locations, norm, page_region, section,
)

AUDIT = ROOT / "greenfield" / "evidence" / "wiki-audit"
MANIFEST = AUDIT / "eldenpedia-location-pages.tsv"
CLAIMS = ROOT / "greenfield" / "evidence" / "v060-current" / "claims.tsv"
DEFAULT_OUT = AUDIT / "eldenpedia-repeated-pickup-check-leads.tsv"
DEFAULT_REPORT = AUDIT / "eldenpedia-repeated-pickup-coverage.json"
FIELDS = (
    "lead_id", "subject_kind", "subject_id", "claim_kind", "normalized_value", "source_ids",
    "independence_families", "disposition", "game_version", "exact_citations", "summary",
    "limitations",
)
MAP_LOT = "ItemLotParam_map.getItemFlagId"


def title_phrase(title: str) -> str:
    """Drop a disambiguating final parenthetical, but retain the named location itself."""
    return norm(re.sub(r"\s*\([^)]*\)\s*$", "", title))


def detection_claims() -> dict[int, tuple[int, str, str]]:
    rows = {}
    with CLAIMS.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["claim_kind"] != "detection" or row["active"] != "true":
                continue
            value = json.loads(row["value"])
            if isinstance(value, dict) and "flag" in value and "mechanism" in value:
                rows[int(row["subject_id"])] = (
                    int(value["flag"]), value["mechanism"], row["claim_id"])
    return rows


def manifests() -> dict[str, dict[str, str]]:
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        return {row["source_id"]: row for row in csv.DictReader(handle, delimiter="\t")}


def build(pages: list[dict]) -> tuple[list[dict[str, str]], dict]:
    index: dict[tuple[str, str], list[tuple[int, int, str]]] = defaultdict(list)
    for region, checks in load_locations().items():
        for location, ap_id, flag in checks:
            index[(region, norm(ap_item_name(location)))].append((ap_id, flag, location))
    detections = detection_claims()
    known_sources = manifests()
    emitted: dict[int, dict[str, str]] = {}
    stats = defaultdict(int)
    stats["location_pages"] = len(pages)
    for page in pages:
        revision = page["revisions"][0]
        content = revision["slots"]["main"]["*"]
        page_id, revision_id = int(page["pageid"]), int(revision["revid"])
        source_id = f"wiki:eldenpedia:page-{page_id}:revision-{revision_id}"
        source = known_sources.get(source_id)
        if not source or source["revision_sha1"] != revision["sha1"]:
            raise ValueError(f"capture revision is not pinned by manifest: {source_id}")
        regions = REGIONS.get(page_region(content), ())
        phrase = title_phrase(page["title"])
        if not regions or len(phrase) < 5:
            continue
        for item in links(section(content, "Notable Loot")):
            candidates = [(region, *candidate) for region in regions
                          for candidate in index.get((region, norm(item)), ())]
            if len(candidates) <= 1:
                continue
            stats["ambiguous_loot_links"] += 1
            title_matches = [candidate for candidate in candidates
                             if re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])",
                                          norm(candidate[3]))]
            if len(title_matches) != 1:
                stats["refused_title_match"] += 1
                continue
            region, ap_id, flag, location = title_matches[0]
            detection = detections.get(ap_id)
            if not detection or detection[:2] != (flag, MAP_LOT):
                stats["refused_non_map_lot"] += 1
                continue
            _claim_flag, _mechanism, claim_id = detection
            value = {"flag": flag, "item_name": item, "location_page": page["title"],
                     "region": region}
            emitted[ap_id] = {
                "lead_id": f"eldenpedia-repeated-page-{page_id}-revision-{revision_id}-check-{ap_id}",
                "subject_kind": "check", "subject_id": str(ap_id),
                "claim_kind": "identity_region",
                "normalized_value": json.dumps(value, ensure_ascii=False, sort_keys=True,
                                               separators=(",", ":")),
                "source_ids": source_id,
                "independence_families": "gameplay-wiki:eldenpedia",
                "disposition": "lead_only", "game_version": "unknown",
                "exact_citations": (f"eldenpedia:pageid-{page_id}:revision-{revision_id}:"
                                    f"#Notable_Loot:{item};project:{claim_id};flag-{flag}"),
                "summary": (f"Eldenpedia revision {revision_id} lists {item} on {page['title']}; "
                            f"that exact page title selects one of the repeated {region} checks, "
                            f"whose current v1.17 map-lot flag is {flag}."),
                "limitations": ("Community-wiki location lead disambiguated by an exact page-title "
                                "phrase in the current AP description and matching v1.17 map-lot "
                                "flag evidence. It does not prove access, route order, coordinates, "
                                "completeness, event timing, or absence of another acquisition."),
            }
    rows = sorted(emitted.values(), key=lambda row: row["lead_id"])
    stats["matched_checks"] = len(rows)
    return rows, dict(sorted(stats.items()))


def render(rows: list[dict[str, str]]) -> str:
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path, help="same-run Eldenpedia Category:Locations capture")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    pages = json.loads(args.capture.read_text(encoding="utf-8"))
    rows, stats = build(pages)
    args.output.write_text(render(rows), encoding="utf-8")
    args.report.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(stats, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
