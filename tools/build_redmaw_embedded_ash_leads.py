#!/usr/bin/env python3
"""Bind Redmaw weapon labels to AP checks whose names also carry their innate Ash of War."""
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
import importlib.util
from io import StringIO
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield/evidence/wiki-audit"
OUT = AUDIT / "redmaw-embedded-ash-check-leads.tsv"
REPORT = AUDIT / "redmaw-embedded-ash-coverage.json"
SOURCE_ID = "wiki:redmaw:walkthroughs:7281cb6f"
FIELDS = ("lead_id", "subject_kind", "subject_id", "claim_kind", "normalized_value",
          "source_ids", "independence_families", "disposition", "game_version",
          "exact_citations", "summary", "limitations")
MARKER = " with ash of war "


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def build(sheets: Path) -> tuple[list[dict[str, str]], dict]:
    anchors = load("_redmaw_ash_anchors", ROOT / "tools/build_redmaw_location_anchor_leads.py")
    base = load("_redmaw_ash_base", ROOT / "tools/build_walkthrough_check_leads.py")
    repeated = load("_redmaw_ash_detection", ROOT / "tools/build_eldenpedia_repeated_pickup_leads.py")
    anchors.verify(sheets)
    index = defaultdict(list)
    for region, locations in base.load_locations().items():
        for location, ap_id, flag in locations:
            display_item = base.ap_item_name(location)
            item = base.norm(display_item)
            if MARKER in item:
                index[(region, item.split(MARKER, 1)[0])].append(
                    (ap_id, flag, location, display_item))
    aliases = {alias for _region, alias in index}
    detections = repeated.detection_claims()
    stats = Counter(source_item_links=0, refused_no_alias_candidate=0,
                    refused_ambiguous_candidate=0, refused_non_map_lot=0,
                    refused_duplicate_check=0, matched_checks=0)
    emitted = {}
    for sheet in sorted(anchors.HASHES):
        parser = anchors.Parser()
        parser.feed((sheets / sheet).read_text(encoding="utf-8"))
        for section, step, url, label in parser.links:
            if not url.startswith("https://eldenring.wiki.gg/wiki/"):
                continue
            if base.norm(label) not in aliases:
                continue
            stats["source_item_links"] += 1
            candidates = [(region, *candidate) for region in anchors.REGIONS.get(section, ())
                          for candidate in index.get((region, base.norm(label)), ())]
            if not candidates:
                stats["refused_no_alias_candidate"] += 1
                continue
            if len(candidates) != 1:
                stats["refused_ambiguous_candidate"] += 1
                continue
            region, ap_id, flag, _location, ap_item = candidates[0]
            detection = detections.get(ap_id)
            if not detection or detection[:2] != (flag, repeated.MAP_LOT):
                stats["refused_non_map_lot"] += 1
                continue
            if ap_id in emitted:
                stats["refused_duplicate_check"] += 1
                emitted.pop(ap_id, None)
                continue
            value = {"ap_item_name": ap_item, "flag": flag, "region": region,
                     "source_item_name": label, "wiki_url": url}
            emitted[ap_id] = {
                "lead_id": f"redmaw-embedded-ash-{sheet.removesuffix('.html')}-{step}-check-{ap_id}",
                "subject_kind": "check", "subject_id": str(ap_id),
                "claim_kind": "identity_region",
                "normalized_value": json.dumps(value, ensure_ascii=False, sort_keys=True,
                                               separators=(",", ":")),
                "source_ids": SOURCE_ID,
                "independence_families": "gameplay-guide:redmaw",
                "disposition": "lead_only", "game_version": "unknown",
                "exact_citations": (f"redmaw:{sheet}#{section}/{step}:item-{label};"
                                    f"wiki.gg:{url};project:{detection[2]};flag-{flag}"),
                "summary": (f"Redmaw step {step} links {label} in {region}; the exact base weapon "
                            f"name selects one current AP check whose label appends its innate Ash "
                            f"of War and whose map-lot flag is {flag}."),
                "limitations": ("One unlicensed walkthrough family, retaining only a factual item "
                                "link and immutable step anchor. AP's appended Ash-of-War text and "
                                "the v1.17 map-lot flag are project evidence. This does not prove "
                                "access, route order, completeness, or alternate-acquisition absence."),
            }
    rows = sorted(emitted.values(), key=lambda row: row["lead_id"])
    stats["matched_checks"] = len(rows)
    return rows, dict(sorted(stats.items()))


def render(rows: list[dict[str, str]]) -> str:
    out = StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    return out.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sheets", type=Path)
    args = parser.parse_args()
    rows, stats = build(args.sheets)
    OUT.write_text(render(rows), encoding="utf-8")
    REPORT.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(stats, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
