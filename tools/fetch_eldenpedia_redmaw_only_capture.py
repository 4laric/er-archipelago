#!/usr/bin/env python3
"""Fetch Eldenpedia revisions for the Redmaw-only progression-host queue."""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIDENCE = ROOT / "greenfield/evidence/v060-current/progression_host_confidence.tsv"
MANIFEST = ROOT / "greenfield/evidence/wiki-audit/eldenpedia-item-acquisition-pages.tsv"
API = "https://eldenring.wiki.gg/api.php"
USER_AGENT = "er-archipelago-evidence-audit/0.6 (https://github.com/4laric/er-archipelago)"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def item_name(location: str) -> str:
    value = location.split(" :: ", 1)[1].split(" - ", 1)[0]
    return re.sub(r"^\[[^]]+\]\s*", "", value).replace("[", "").replace("]", "")


def requested_titles() -> list[str]:
    with CONFIDENCE.open(encoding="utf-8", newline="") as handle:
        redmaw_only = {
            int(row["check_id"])
            for row in csv.DictReader(handle, delimiter="\t")
            if row["external_family_count"] == "1"
            and row["external_families"] == "gameplay-guide:redmaw"
        }
    data = load_module("_eldenring_data", ROOT / "greenfield/eldenring/data.py")
    titles = {
        item_name(location)
        for entries in data.LOCATIONS.values()
        for location, ap_id, _flag in entries
        if ap_id in redmaw_only
    }
    # Keep the previous acquisition corpus in a focused refresh.
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        titles.update(row["title"] for row in csv.DictReader(handle, delimiter="\t"))
    return sorted(titles, key=str.casefold)


def fetch(titles: list[str]) -> dict[str, object]:
    pages: list[dict[str, object]] = []
    missing: list[str] = []
    for offset in range(0, len(titles), 40):
        batch = titles[offset : offset + 40]
        query = urllib.parse.urlencode({
            "action": "query", "format": "json", "formatversion": "2",
            "prop": "revisions", "redirects": "1",
            "rvprop": "ids|timestamp|sha1|content", "rvslots": "main",
            "titles": "|".join(batch),
        })
        request = urllib.request.Request(f"{API}?{query}", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.load(response)
        for page in payload["query"]["pages"]:
            if page.get("missing"):
                missing.append(page["title"])
            else:
                pages.append(page)
        if offset + 40 < len(titles):
            time.sleep(0.25)
    return {
        "requested_titles": titles,
        "missing_titles": sorted(missing, key=str.casefold),
        "pages": sorted(pages, key=lambda page: (str(page["title"]).casefold(), int(page["pageid"]))),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    titles = requested_titles()
    capture = fetch(titles)
    args.output.write_text(json.dumps(capture, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"Eldenpedia capture: {len(titles)} requested, "
        f"{len(capture['pages'])} resolved, {len(capture['missing_titles'])} missing"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
