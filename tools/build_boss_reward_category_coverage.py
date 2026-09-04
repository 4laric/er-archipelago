#!/usr/bin/env python3
"""Build the category-first boss-reward coverage inventory for v0.6 review."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "greenfield/eldenring"
CONFIDENCE = ROOT / "greenfield/evidence/v060-current/progression_host_confidence.tsv"
OUTPUT = ROOT / "greenfield/evidence/wiki-audit/boss-reward-category-coverage.json"


def load_module(name: str):
    path = WORLD / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_boss_coverage_{name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def build() -> dict:
    data = load_module("data")
    tags = load_module("location_tags").LOCATION_TAGS
    locations = {
        ap_id: {"check_id": ap_id, "name": name, "region": region}
        for region, rows in data.LOCATIONS.items()
        for name, ap_id, _flag in rows
    }
    with CONFIDENCE.open(encoding="utf-8", newline="") as stream:
        confidence = {
            int(row["check_id"]): row for row in csv.DictReader(stream, delimiter="\t")
        }
    remembrance = {ap for ap, values in tags.items() if "Remembrance" in values}
    great_rune = {ap for ap, values in tags.items() if "GreatRune" in values}
    all_boss = {ap for ap, values in tags.items() if "Boss" in values}
    categories = {
        "remembrance": remembrance,
        "great_rune": great_rune,
        "major_boss": {ap for ap, values in tags.items() if "MajorBoss" in values},
        "fixed_boss_drop": all_boss - remembrance - great_rune,
        "all_boss_reward_checks": all_boss,
    }
    rendered_categories = {}
    all_held = set()
    for label, aps in categories.items():
        held = sorted(ap for ap in aps if confidence[ap]["confidence"] == "hold")
        all_held.update(held)
        rendered_categories[label] = {
            "total": len(aps),
            "trusted_identity_region": len(aps) - len(held),
            "hold": len(held),
            "hold_by_external_family_count": dict(sorted(Counter(
                confidence[ap]["external_family_count"] for ap in held
            ).items(), key=lambda pair: int(pair[0]))),
            "remaining_check_ids": held,
        }
    return {
        "schema_version": 1,
        "scope": "v0.6 boss, remembrance, great-rune, and fixed boss-drop checks",
        "categories": rendered_categories,
        "remaining_checks": {
            str(ap): {
                **locations[ap],
                "external_family_count": int(confidence[ap]["external_family_count"]),
                "external_families": confidence[ap]["external_families"].split(";")
                if confidence[ap]["external_families"] else [],
            }
            for ap in sorted(all_held)
        },
        "limitations": [
            "Trusted means two independent external families corroborate identity and region only.",
            "No row in this report is proof of access, route order, event timing, progression-host safety, or exclusion.",
            "Finale lifecycle and disputed-region holds remain independent and authoritative.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    rendered = json.dumps(build(), indent=2, sort_keys=True) + "\n"
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != rendered:
            raise SystemExit(f"STALE: {OUTPUT}; run {Path(__file__).name}")
        print("boss reward category coverage: OK")
        return 0
    OUTPUT.write_text(rendered, encoding="utf-8")
    print("boss reward category coverage: updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
