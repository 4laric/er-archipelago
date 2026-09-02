#!/usr/bin/env python3
"""Pin the wiki.gg targets used by Redmaw merchant leads to immutable revisions."""

from __future__ import annotations

import csv
import argparse
import importlib.util
import json
from pathlib import Path
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "greenfield/evidence/wiki-audit/redmaw-merchant-wikigg-revisions.tsv"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sheets", type=Path)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location(
        "_redmaw_checklists", ROOT / "tools/build_redmaw_checklist_leads.py"
    )
    base = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(base)
    base.verify_snapshot(args.sheets)
    merchant_parser = base.ChecklistParser()
    merchant_parser.feed((args.sheets / "merchants.html").read_text(encoding="utf-8"))
    urls = sorted({url for _checkbox, _section, url, _label in merchant_parser.rows
                   if url.startswith("https://eldenring.wiki.gg/wiki/")})
    titles = {
        urllib.parse.unquote(urllib.parse.urlparse(url).path.removeprefix("/wiki/")).replace("_", " "): url
        for url in urls
    }
    revisions = {}
    title_list = sorted(titles)
    for offset in range(0, len(title_list), 50):
        params = urllib.parse.urlencode({
            "action": "query", "format": "json", "formatversion": 2,
            "prop": "revisions", "rvprop": "ids|timestamp", "redirects": 1,
            "titles": "|".join(title_list[offset:offset + 50]),
        })
        request = urllib.request.Request(
            "https://eldenring.wiki.gg/api.php?" + params,
            headers={"User-Agent": "er-archipelago-evidence-audit/0.1"},
        )
        payload = json.load(urllib.request.urlopen(request))
        for page in payload["query"]["pages"]:
            assert "missing" not in page and len(page["revisions"]) == 1
            revision = page["revisions"][0]
            canonical = "https://eldenring.wiki.gg/wiki/" + urllib.parse.quote(
                page["title"].replace(" ", "_"), safe="_()'"
            )
            revisions[canonical] = {
                "canonical_url": canonical,
                "revision_url": canonical + f"?oldid={revision['revid']}",
                "page_id": str(page["pageid"]),
                "revision_id": str(revision["revid"]),
                "revision_timestamp": revision["timestamp"],
            }
    # Resolve redirects by normalized title if the canonical URL differs from Redmaw's target.
    normalized = {urllib.parse.unquote(urllib.parse.urlparse(url).path).casefold(): row
                  for url, row in revisions.items()}
    rows = []
    for url in urls:
        key = urllib.parse.unquote(urllib.parse.urlparse(url).path).casefold()
        row = normalized.get(key)
        if row is None:
            title = urllib.parse.unquote(urllib.parse.urlparse(url).path.removeprefix("/wiki/")).replace("_", " ")
            matches = [candidate for candidate in revisions.values()
                       if urllib.parse.unquote(urllib.parse.urlparse(candidate["canonical_url"]).path.removeprefix("/wiki/")).replace("_", " ").casefold() == title.casefold()]
            assert len(matches) == 1, f"cannot bind wiki.gg redirect for {url}"
            row = matches[0]
        rows.append({"redmaw_url": url, **row})
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} immutable wiki.gg revisions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
