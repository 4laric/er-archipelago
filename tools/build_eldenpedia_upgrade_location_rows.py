#!/usr/bin/env python3
"""Bind repeated upgrade materials through one pinned Acquisition row and linked place."""
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from io import StringIO
import json
from pathlib import Path
import re

import build_eldenpedia_upgrade_material_leads as upgrades
import build_eldenpedia_repeated_pickup_leads as repeated

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield/evidence/wiki-audit"
OUT = AUDIT / "eldenpedia-upgrade-location-row-check-leads.tsv"
REPORT = AUDIT / "eldenpedia-upgrade-location-row-coverage.json"
FIELDS = ("lead_id", "subject_kind", "subject_id", "claim_kind", "normalized_value",
          "source_ids", "independence_families", "disposition", "game_version",
          "exact_citations", "summary", "limitations")


def acquisition_rows(text: str) -> list[str]:
    return [line for line in upgrades.acquisition(text).splitlines()
            if line.lstrip().startswith("*")]


def links(row: str) -> list[tuple[str, str]]:
    found = []
    for target, shown in re.findall(
            r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]", row):
        found.append((target.strip(), (shown or target).strip()))
    return found


def read_sources() -> dict[str, dict[str, str]]:
    sources = {}
    for name in ("eldenpedia-item-acquisition-pages.tsv",
                 "eldenpedia-upgrade-material-pages.tsv"):
        with (AUDIT / name).open(encoding="utf-8", newline="") as handle:
            sources.update((row["source_id"], row) for row in csv.DictReader(handle, delimiter="\t"))
    return sources


def covered_subjects() -> set[int]:
    covered = set()
    for path in AUDIT.glob("*-check-leads.tsv"):
        if path == OUT:
            continue
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                if row.get("subject_kind") == "check" and row.get("subject_id", "").isdigit():
                    covered.add(int(row["subject_id"]))
    return covered


def build(capture: dict) -> tuple[list[dict[str, str]], dict]:
    data = upgrades.module("_upgrade_row_data", ROOT / "greenfield/eldenring/data.py")
    detections = repeated.detection_claims()
    candidates = defaultdict(list)
    for region, entries in data.LOCATIONS.items():
        for location, ap_id, flag in entries:
            item = upgrades.norm(upgrades.item_name(location))
            if upgrades.is_upgrade_material(item):
                candidates[item].append((ap_id, flag, region, location))
    with (AUDIT / "eldenpedia-location-pages.tsv").open(encoding="utf-8", newline="") as handle:
        location_titles = {upgrades.norm(row["title"])
                           for row in csv.DictReader(handle, delimiter="\t")}
    vague = {upgrades.norm(region) for region in data.LOCATIONS} | {
        "altus plateau", "liurnia of the lakes", "weeping peninsula", "realm of shadow",
        "crumbling farum azula",
    }
    known_sources = read_sources()
    prior = covered_subjects()
    raw_matches = []
    stats = Counter(source_rows=0, refused_no_unique_check=0, refused_non_map_lot=0,
                    refused_duplicate_rows=0, already_covered_checks=0,
                    new_union_checks=0)
    for page in capture["pages"]:
        title = upgrades.norm(page["title"])
        if title not in candidates or not upgrades.is_upgrade_material(title):
            continue
        revision = page["revisions"][0]
        source_id = f"wiki:eldenpedia:page-{page['pageid']}:revision-{revision['revid']}"
        source = known_sources.get(source_id)
        if not source:
            continue
        if source["revision_sha1"] != revision["sha1"]:
            raise ValueError(f"upgrade item revision hash mismatch: {source_id}")
        for ordinal, row in enumerate(acquisition_rows(revision["slots"]["main"]["content"]), 1):
            stats["source_rows"] += 1
            matches = []
            for target, label in links(row):
                phrase = upgrades.norm(label)
                if (phrase not in location_titles or phrase in vague or len(phrase.split()) < 2):
                    continue
                for ap_id, flag, region, location in candidates[title]:
                    acquisition = location.split(", may be sweep-granted", 1)[0]
                    if re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])",
                                 upgrades.norm(acquisition)):
                        matches.append((ap_id, flag, region, target, label, phrase))
            check_ids = {match[0] for match in matches}
            places = {(match[3], match[4]) for match in matches}
            if len(check_ids) != 1 or len(places) != 1:
                stats["refused_no_unique_check"] += 1
                continue
            ap_id, flag, region, target, label, phrase = matches[0]
            detection = detections.get(ap_id)
            if not detection or detection[:2] != (flag, repeated.MAP_LOT):
                stats["refused_non_map_lot"] += 1
                continue
            raw_matches.append((ap_id, flag, region, page, revision, source_id,
                                ordinal, target, label, phrase))
    counts = Counter(match[0] for match in raw_matches)
    stats["refused_duplicate_rows"] = sum(count for count in counts.values() if count > 1)
    unique = [match for match in raw_matches if counts[match[0]] == 1]
    stats["already_covered_checks"] = sum(match[0] in prior for match in unique)
    rows = []
    for ap_id, flag, region, page, revision, source_id, ordinal, target, label, phrase in unique:
        if ap_id in prior:
            continue
        page_id, revision_id = int(page["pageid"]), int(revision["revid"])
        value = {"acquisition_row": ordinal, "flag": flag, "item_name": page["title"],
                 "place": label, "place_target": target, "region": region}
        rows.append({
            "lead_id": f"eldenpedia-upgrade-row-page-{page_id}-revision-{revision_id}-row-{ordinal}-check-{ap_id}",
            "subject_kind": "check", "subject_id": str(ap_id),
            "claim_kind": "identity_region",
            "normalized_value": json.dumps(value, ensure_ascii=False, sort_keys=True,
                                           separators=(",", ":")),
            "source_ids": source_id, "independence_families": "gameplay-wiki:eldenpedia",
            "disposition": "lead_only", "game_version": "unknown",
            "exact_citations": (f"eldenpedia:pageid-{page_id}:revision-{revision_id}:"
                                f"#Acquisition:row-{ordinal}:place-{label};"
                                f"project:{detections[ap_id][2]};flag-{flag}"),
            "summary": (f"Eldenpedia revision {revision_id} links {label} in one acquisition row "
                        f"for {page['title']}; that place selects one AP map-lot flag ({flag}) in {region}."),
            "limitations": ("Community-wiki acquisition-row lead using one linked place and matching "
                            "v1.17 map-lot evidence. It does not prove access, route order, "
                            "coordinates, completeness, event timing, or alternate-acquisition absence."),
        })
    rows.sort(key=lambda row: row["lead_id"])
    stats["new_union_checks"] = len(rows)
    return rows, dict(sorted(stats.items()))


def render(rows: list[dict[str, str]]) -> str:
    out = StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    return out.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("capture", type=Path); args = parser.parse_args()
    rows, stats = build(json.loads(args.capture.read_text(encoding="utf-8")))
    OUT.write_text(render(rows), encoding="utf-8")
    REPORT.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(stats, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
