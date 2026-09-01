#!/usr/bin/env python3
"""Build conservative AP-check leads from Eldenpedia location pages.

Only three source facts survive ingestion: immutable MediaWiki revision metadata, the infobox
region link, and link targets in the ``Notable Loot`` section.  No prose is stored.  A loot link is
bound only when its exact normalized item name identifies one current AP check in the page's
explicitly mapped AP region set.  Everything else is counted as ambiguous or unmatched.

These are external ``lead_only`` identity/region cross-checks.  They are not access evidence and
must never be consumed by world logic.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield" / "evidence" / "wiki-audit"
DEFAULT_MANIFEST = AUDIT / "eldenpedia-location-pages.tsv"
DEFAULT_LEADS = AUDIT / "eldenpedia-location-check-leads.tsv"
API = "https://eldenring.wiki.gg/api.php"
USER_AGENT = "er-archipelago-v060-evidence-audit/1.0"

PAGE_FIELDS = ("source_id", "page_id", "revision_id", "revision_timestamp", "revision_sha1",
               "title", "canonical_url", "revision_url", "wiki_region", "ap_regions",
               "notable_loot_links", "disposition")
LEAD_FIELDS = ("lead_id", "subject_kind", "subject_id", "claim_kind", "normalized_value",
               "source_ids", "independence_families", "disposition", "game_version",
               "exact_citations", "summary", "limitations")

# Explicit vocabulary bridge, not a fuzzy place-name guess. Multiple AP buckets are allowed only
# where the wiki's top-level geography is coarser than this project's region model.
REGIONS = {
    "Limgrave": ("Limgrave", "Stormveil"),
    "Weeping Peninsula": ("Weeping",),
    "Liurnia of the Lakes": ("Liurnia", "Raya Lucaria Academy"),
    "Caelid": ("Caelid",), "Greyoll's Dragonbarrow": ("Caelid",),
    "Altus Plateau": ("Altus", "Leyndell"), "Mt. Gelmir": ("Mt. Gelmir",),
    "Capital Outskirts": ("Altus",),
    "Leyndell, Royal Capital": ("Leyndell", "Sewer"),
    "Leyndell, Ashen Capital": ("Ashen Capital",),
    "Mountaintops of the Giants": ("Mountaintops of the Giants",),
    "Flame Peak": ("Mountaintops of the Giants",),
    "Consecrated Snowfield": ("Consecrated Snowfield",),
    "Miquella's Haligtree": ("Haligtree",), "Crumbling Farum Azula": ("Farum Azula",),
    "Siofra River": ("Siofra River", "Mohgwyn"), "Ainsel River": ("Ainsel River",),
    "Nokron, Eternal City": ("Siofra River",), "Ainsel River Main": ("Ainsel River",),
    "Deeproot Depths": ("Deeproot Depths",),
    "Gravesite Plain": ("Gravesite", "Belurat"), "Scadu Altus": ("Scadu Altus", "Shadow Keep"),
    "Southern Shore": ("Cerulean",), "Rauh Base": ("Rauh Base",),
    "Ancient Ruins of Rauh": ("Rauh Ruins",), "Abyssal Woods": ("Abyssal",),
    "Enir-Ilim": ("Enir-Ilim",),
}


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold().replace("&", " and ")))


def ap_item_name(location: str) -> str:
    value = location.split(" :: ", 1)[-1]
    value = re.sub(r"\s*\[f\d+\]\s*$", "", value)
    value = value.split(", may be sweep-granted", 1)[0].split(" - ", 1)[0]
    return re.sub(r"^\[(?:Incantation|Sorcery)\]\s*", "", value).strip()


def api(params: dict[str, str]) -> dict:
    req = Request(API + "?" + urlencode(params), headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=60) as response:
        return json.load(response)


def category_pages() -> list[dict]:
    rows, cont = [], None
    while True:
        params = {"action": "query", "format": "json", "list": "categorymembers",
                  "cmtitle": "Category:Locations", "cmnamespace": "0", "cmlimit": "500"}
        if cont:
            params["cmcontinue"] = cont
        payload = api(params)
        rows.extend(payload["query"]["categorymembers"])
        cont = payload.get("continue", {}).get("cmcontinue")
        if not cont:
            return rows


def current_pages() -> list[dict]:
    members = category_pages()
    pages = []
    for offset in range(0, len(members), 50):
        ids = "|".join(str(row["pageid"]) for row in members[offset:offset + 50])
        payload = api({"action": "query", "format": "json", "pageids": ids,
                       "prop": "revisions", "rvprop": "ids|timestamp|sha1|content",
                       "rvslots": "main"})
        pages.extend(payload["query"]["pages"].values())
    return pages


def section(text: str, name: str) -> str:
    match = re.search(rf"(?ims)^==\s*{re.escape(name)}\s*==\s*(.*?)(?=^==[^=]|\Z)", text)
    return match.group(1) if match else ""


def links(text: str) -> list[str]:
    out = []
    for target in re.findall(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]", text):
        target = target.strip()
        if target and not target.startswith(("File:", "Category:")):
            out.append(target)
    return list(dict.fromkeys(out))


def page_region(text: str) -> str:
    infobox = text.split("}}", 1)[0]
    match = re.search(r"(?im)^\s*\|\s*region\s*=\s*\[\[([^\]|#]+)", infobox)
    return match.group(1).strip() if match else ""


def load_locations():
    path = ROOT / "greenfield" / "eldenring" / "data.py"
    spec = importlib.util.spec_from_file_location("_eldenpedia_data", path)
    mod = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)
    return mod.LOCATIONS


def build(pages: list[dict]) -> tuple[list[dict], list[dict], dict]:
    index = {}
    for region, checks in load_locations().items():
        for location, ap_id, _flag in checks:
            index.setdefault((region, norm(ap_item_name(location))), []).append((ap_id, location))
    manifest, emitted = [], []
    stats = {"category_pages": len(pages), "pages_with_mapped_region": 0,
             "pages_with_notable_loot": 0, "loot_links": 0, "matched_checks": 0,
             "ambiguous_links": 0, "unmatched_links": 0, "duplicate_check_mentions": 0}
    for page in sorted(pages, key=lambda row: int(row["pageid"])):
        revision = page["revisions"][0]
        text = revision["slots"]["main"]["*"]
        region = page_region(text)
        ap_regions = REGIONS.get(region, ())
        loot = links(section(text, "Notable Loot"))
        stats["pages_with_mapped_region"] += bool(ap_regions)
        stats["pages_with_notable_loot"] += bool(loot)
        stats["loot_links"] += len(loot)
        page_id, revision_id = int(page["pageid"]), int(revision["revid"])
        source_id = f"wiki:eldenpedia:page-{page_id}:revision-{revision_id}"
        manifest.append({
            "source_id": source_id, "page_id": page_id, "revision_id": revision_id,
            "revision_timestamp": revision["timestamp"], "revision_sha1": revision["sha1"],
            "title": page["title"],
            "canonical_url": "https://eldenring.wiki.gg/wiki/" + page["title"].replace(" ", "_"),
            "revision_url": f"https://eldenring.wiki.gg/w/index.php?oldid={revision_id}",
            "wiki_region": region, "ap_regions": ",".join(ap_regions),
            "notable_loot_links": str(len(loot)), "disposition": "lead_only",
        })
        if not ap_regions:
            continue
        for item in loot:
            candidates = []
            for ap_region in ap_regions:
                candidates.extend((ap_region, *row)
                                  for row in index.get((ap_region, norm(item)), ()))
            if len(candidates) != 1:
                stats["ambiguous_links" if candidates else "unmatched_links"] += 1
                continue
            ap_region, ap_id, _location = candidates[0]
            emitted.append({
                "lead_id": f"eldenpedia-page-{page_id}-revision-{revision_id}-check-{ap_id}",
                "subject_kind": "check", "subject_id": str(ap_id),
                "claim_kind": "identity_region",
                "normalized_value": json.dumps({"item_name": item, "region": ap_region},
                                               ensure_ascii=False, sort_keys=True,
                                               separators=(",", ":")),
                "source_ids": source_id, "independence_families": "gameplay-wiki:eldenpedia",
                "disposition": "lead_only", "game_version": "unknown",
                "exact_citations": f"eldenpedia:pageid-{page_id}:revision-{revision_id}:#Notable_Loot:{item}",
                "summary": f"Eldenpedia revision {revision_id} lists {item} as notable loot on "
                           f"{page['title']}; that exact name identifies one current AP check in {ap_region}.",
                "limitations": "Community-wiki location lead matched by exact item name inside an "
                               "explicit region mapping. It does not prove access, a v1.17 event "
                               "predicate, route order, completeness, or absence of another source.",
            })
    # A loot item can appear on nested and parent location pages. Refuse every such binding rather
    # than retaining whichever page happened to sort first; page uniqueness is part of the proof.
    mentions = {}
    for row in emitted:
        mentions[row["subject_id"]] = mentions.get(row["subject_id"], 0) + 1
    duplicate_subjects = {subject for subject, count in mentions.items() if count > 1}
    stats["duplicate_check_mentions"] = sum(mentions[s] for s in duplicate_subjects)
    emitted = [row for row in emitted if row["subject_id"] not in duplicate_subjects]
    emitted.sort(key=lambda row: row["lead_id"])
    stats["matched_checks"] = len(emitted)
    return manifest, emitted, stats


def render(rows: list[dict], fields: tuple[str, ...]) -> str:
    from io import StringIO
    out = StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    return out.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, help="JSON API capture; omit to fetch current pages")
    parser.add_argument("--write-capture", type=Path,
                        help="write fetched API records for same-run reproducibility")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--leads", type=Path, default=DEFAULT_LEADS)
    args = parser.parse_args()
    if args.capture:
        pages = json.loads(args.capture.read_text(encoding="utf-8"))
    else:
        pages = current_pages()
        if args.write_capture:
            args.write_capture.write_text(json.dumps(pages, ensure_ascii=False, sort_keys=True),
                                           encoding="utf-8")
    manifest, leads, stats = build(pages)
    args.manifest.write_text(render(manifest, PAGE_FIELDS), encoding="utf-8")
    args.leads.write_text(render(leads, LEAD_FIELDS), encoding="utf-8")
    print(json.dumps(stats, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
