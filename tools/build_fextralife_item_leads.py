#!/usr/bin/env python3
"""Bind immutable Fextralife item revisions to current AP checks.

The source wiki exposes structured ``locationN`` template fields.  A binding is emitted only when
the AP item name identifies one check globally and its current AP region appears literally in one
of those fields.  These are discovery leads, not access evidence.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
import importlib.util
import json
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield" / "evidence" / "wiki-audit"
DEFAULT_MANIFEST = AUDIT / "fextralife-item-pages.tsv"
DEFAULT_LEADS = AUDIT / "fextralife-item-check-leads.tsv"
API = "https://eldenring.wiki.fextralife.com/api.php?"
USER_AGENT = "er-archipelago evidence audit/1.0 (+https://github.com/4laric/er-archipelago)"
PAGE_FIELDS = (
    "source_id", "page_id", "revision_id", "revision_timestamp", "revision_sha1", "title",
    "canonical_url", "revision_url", "ap_item_name", "template_fields", "ap_region",
    "disposition",
)
LEAD_FIELDS = (
    "lead_id", "subject_kind", "subject_id", "claim_kind", "normalized_value", "source_ids",
    "independence_families", "disposition", "game_version", "exact_citations", "summary",
    "limitations",
)


def ap_item_name(location: str) -> str:
    value = location.split(" :: ", 1)[-1]
    value = re.sub(r"\s*\[f\d+\]\s*$", "", value)
    value = value.split(", may be sweep-granted", 1)[0]
    value = value.split(" - ", 1)[0]
    value = re.sub(r"^\[(?:Incantation|Sorcery)\]\s*", "", value)
    return value.strip()


def load_unique_checks() -> dict[str, tuple[str, int]]:
    spec = importlib.util.spec_from_file_location(
        "_fextralife_data", ROOT / "greenfield" / "eldenring" / "data.py")
    mod = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)
    by_name: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for region, checks in mod.LOCATIONS.items():
        for location, ap_id, _flag in checks:
            by_name[ap_item_name(location)].append((region, ap_id))
    return {name: rows[0] for name, rows in by_name.items()
            if len(rows) == 1 and len(name) >= 4}


def fetch(names: list[str], cache_dir: Path | None) -> list[dict]:
    """Fetch in API-sized batches, reusing byte-for-byte local responses when requested."""
    batches = []
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
    for offset in range(0, len(names), 40):
        path = cache_dir / f"{offset // 40:03}.json" if cache_dir else None
        if path and path.exists():
            body = path.read_bytes()
        else:
            query = {
                "action": "query", "format": "json", "formatversion": "2", "redirects": "1",
                "titles": "|".join(names[offset:offset + 40]), "prop": "revisions",
                "rvprop": "ids|timestamp|sha1|content", "rvslots": "main",
            }
            request = urllib.request.Request(
                API + urllib.parse.urlencode(query), headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=60) as response:
                body = response.read()
            if path:
                path.write_bytes(body)
            # Be a quiet API client even though the endpoint permits much larger batches.
            time.sleep(1)
        batches.append(json.loads(body))
    return batches


def clean_field(value: str) -> str:
    value = re.sub(r"<!--.*?-->", " ", value, flags=re.DOTALL)
    value = re.sub(r"\[\[(?:[^]|]+\|)?([^]]+)\]\]", r"\1", value)
    value = re.sub(r"\{\{[^{}]*\}\}", " ", value)
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(value.split())


def location_fields(content: str) -> list[tuple[str, str]]:
    rows = []
    for match in re.finditer(r"^\|\s*(location\d*|obtained\w*|found\w*)\s*=\s*(.*)$",
                             content, flags=re.MULTILINE | re.IGNORECASE):
        value = clean_field(match.group(2))
        if value:
            rows.append((match.group(1).lower(), value))
    return rows


def template_item_name(content: str) -> str:
    match = re.search(r"^\|\s*name\s*=\s*(.*)$", content,
                      flags=re.MULTILINE | re.IGNORECASE)
    return clean_field(match.group(1)) if match else ""


def norm(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold().replace("&", " and ")))


def resolve_pages(batches: list[dict]) -> tuple[dict[str, dict], dict[str, str]]:
    pages, aliases = {}, {}
    for batch in batches:
        query = batch.get("query", {})
        for row in query.get("normalized", []):
            aliases[row["from"]] = row["to"]
        for row in query.get("redirects", []):
            aliases[row["from"]] = row["to"]
        for page in query.get("pages", []):
            if "missing" not in page and page.get("revisions"):
                pages[page["title"]] = page
    return pages, aliases


def resolved(name: str, pages: dict[str, dict], aliases: dict[str, str]) -> dict | None:
    seen = set()
    while name in aliases and name not in seen:
        seen.add(name); name = aliases[name]
    return pages.get(name)


def build(batches: list[dict]) -> tuple[list[dict], list[dict], dict]:
    checks = load_unique_checks()
    pages, aliases = resolve_pages(batches)
    manifest, leads = [], []
    stats = {"unique_check_names": len(checks), "resolved_pages": 0,
             "pages_with_exact_template_name": 0, "pages_with_structured_location": 0,
             "identity_checks": 0, "identity_region_checks": 0, "matched_checks": 0}
    for item_name in sorted(checks):
        page = resolved(item_name, pages, aliases)
        if not page:
            continue
        stats["resolved_pages"] += 1
        revision = page["revisions"][0]
        content = revision["slots"]["main"]["content"]
        if norm(template_item_name(content)) != norm(item_name):
            continue
        stats["pages_with_exact_template_name"] += 1
        fields = location_fields(content)
        stats["pages_with_structured_location"] += bool(fields)
        region, ap_id = checks[item_name]
        matched = [(field, value) for field, value in fields
                   if region.casefold() in value.casefold()]
        page_id, revision_id = int(page["pageid"]), int(revision["revid"])
        source_id = f"wiki:fextralife:page-{page_id}:revision-{revision_id}"
        title_slug = page["title"].replace(" ", "_")
        manifest.append({
            "source_id": source_id, "page_id": page_id, "revision_id": revision_id,
            "revision_timestamp": revision["timestamp"], "revision_sha1": revision["sha1"],
            "title": page["title"],
            "canonical_url": "https://eldenring.wiki.fextralife.com/" + title_slug,
            "revision_url": ("https://eldenring.wiki.fextralife.com/" + title_slug
                             + f"?oldid={revision_id}"),
            "ap_item_name": item_name,
            "template_fields": ",".join(field for field, _value in matched),
            "ap_region": region if matched else "", "disposition": "lead_only",
        })
        citations = [f"fextralife:pageid-{page_id}:revision-{revision_id}:template-name"]
        citations.extend(f"fextralife:pageid-{page_id}:revision-{revision_id}:template-{field}"
                         for field, _value in matched)
        claim_kind = "identity_region" if matched else "identity"
        value = {"item_name": item_name}
        if matched:
            value["region"] = region
        stats["identity_region_checks" if matched else "identity_checks"] += 1
        leads.append({
            "lead_id": f"fextralife-page-{page_id}-revision-{revision_id}-check-{ap_id}",
            "subject_kind": "check", "subject_id": str(ap_id), "claim_kind": claim_kind,
            "normalized_value": json.dumps(value, ensure_ascii=False, sort_keys=True,
                                           separators=(",", ":")),
            "source_ids": source_id, "independence_families": "gameplay-wiki:fextralife",
            "disposition": "lead_only", "game_version": "unknown",
            "exact_citations": ",".join(citations),
            "summary": ((f"Fextralife revision {revision_id} names {item_name} and files it under "
                         f"a structured location field naming {region}; that item name identifies "
                         "one AP check.") if matched else
                        (f"Fextralife revision {revision_id} uses {item_name} as its structured item "
                         "name; that exact name identifies one current AP check.")),
            "limitations": (("Community-wiki item-page lead matched by a globally unique AP item "
                             "name and a literal AP-region occurrence in a structured template field. "
                             "It does not prove access, a v1.17 event predicate, route order, "
                             "completeness, exact coordinates, or absence of another source.")
                            if matched else
                            ("Community-wiki item-page lead matched only by a globally unique AP item "
                             "name and the page's structured name field. It does not prove region. "
                             "It does not prove access, v1.17 behavior, event predicates, route "
                             "order, coordinates, completeness, or absence of another source.")),
        })
    manifest.sort(key=lambda row: row["source_id"])
    leads.sort(key=lambda row: row["lead_id"])
    stats["matched_checks"] = len(leads)
    return manifest, leads, stats


def render(rows: list[dict], fields: tuple[str, ...]) -> str:
    from io import StringIO
    out = StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    return out.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path,
                        help="JSON list of cached API batch responses; omit to fetch")
    parser.add_argument("--write-capture", type=Path)
    parser.add_argument("--cache-dir", type=Path,
                        help="reuse/store one response per 40-title API batch")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--leads", type=Path, default=DEFAULT_LEADS)
    args = parser.parse_args()
    names = sorted(load_unique_checks())
    batches = (json.loads(args.capture.read_text(encoding="utf-8")) if args.capture
               else fetch(names, args.cache_dir))
    if args.write_capture:
        args.write_capture.write_text(json.dumps(batches, ensure_ascii=False, sort_keys=True),
                                      encoding="utf-8")
    manifest, leads, stats = build(batches)
    args.manifest.write_text(render(manifest, PAGE_FIELDS), encoding="utf-8")
    args.leads.write_text(render(leads, LEAD_FIELDS), encoding="utf-8")
    print(json.dumps(stats, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
