#!/usr/bin/env python3
"""Bind a pinned Eldenpedia Deathroot acquisition list to nine current AP checks.

Repeated item names cannot identify these checks globally.  Each binding therefore requires a
unique set of linked acquisition anchors (boss, dungeon, or nearby site) from one immutable wiki
revision.  The checked-in result keeps only those factual anchors and remains ``lead_only``.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
from io import StringIO
import json
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield" / "evidence" / "wiki-audit"
DEFAULT_MANIFEST = AUDIT / "eldenpedia-deathroot-pages.tsv"
DEFAULT_LEADS = AUDIT / "eldenpedia-deathroot-check-leads.tsv"
API = "https://eldenring.wiki.gg/api.php"
USER_AGENT = "er-archipelago-v060-evidence-audit/1.0"

PAGE_ID = 10213
REVISION_ID = 38369
REVISION_SHA1 = "fbb08b39a5771a04b4be611d843434541801dfcf"
SOURCE_ID = f"wiki:eldenpedia:page-{PAGE_ID}:revision-{REVISION_ID}"
TITLE = "Deathroot"

PAGE_FIELDS = ("source_id", "page_id", "revision_id", "revision_timestamp", "revision_sha1",
               "title", "canonical_url", "revision_url", "acquisition_rows", "disposition")
LEAD_FIELDS = ("lead_id", "subject_kind", "subject_id", "claim_kind", "normalized_value",
               "source_ids", "independence_families", "disposition", "game_version",
               "exact_citations", "summary", "limitations")

# Required link targets are an exact, revision-local selector.  They are not inferred from current
# AP text.  The source_area records the page's own coarse geography, including the useful Altus /
# current-Mt.-Gelmir disagreement at Wyndham Catacombs.
BINDINGS = (
    (7770696, "Limgrave", "Summonwater Village", ("Tibia Mariner", "Summonwater Village"), ""),
    (7772077, "Limgrave", "Deathtouched Catacombs",
     ("Deathtouched Catacombs", "Black Knife Assassin"), ""),
    (7770699, "Liurnia of the Lakes", "eastern Liurnia", ("Liurnia of the Lakes",),
     "eastern"),
    (7772041, "Liurnia of the Lakes", "Black Knife Catacombs",
     ("Black Knife Catacombs", "Cemetery Shade"), ""),
    (7770712, "Altus Plateau", "Wyndham Catacombs", ("Wyndham Catacombs",), ""),
    (7772061, "Mt. Gelmir", "Gelmir Hero's Grave", ("Gelmir Hero's Grave", "Mt. Gelmir"), ""),
    (7772104, "Mountaintops of the Giants", "Giants' Mountaintop Catacombs",
     ("Giants' Mountaintop Catacombs", "Ulcerated Tree Spirit"), ""),
    (7900276, "Mountaintops of the Giants", "Castle Sol", ("Castle Sol",), ""),
    (7772111, "Forbidden Lands", "Hidden Path to the Haligtree",
     ("Hidden Path to the Haligtree", "Stray Mimic Tear"), ""),
)


def fetch_revision() -> dict:
    params = {"action": "query", "format": "json", "formatversion": "2",
              "revids": str(REVISION_ID), "prop": "revisions",
              "rvprop": "ids|timestamp|sha1|content", "rvslots": "main"}
    request = Request(API + "?" + urlencode(params), headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=60) as response:
        return json.load(response)["query"]["pages"][0]


def acquisition_rows(text: str) -> list[tuple[int, set[str], str]]:
    match = re.search(r"(?ims)^==\s*Acquisition\s*==\s*(.*?)(?=^==[^=]|\Z)", text)
    if not match:
        raise ValueError("pinned page has no Acquisition section")
    rows = []
    for ordinal, line in enumerate(re.findall(r"(?m)^#\s+(.+)$", match.group(1)), 1):
        links = {target.strip() for target in re.findall(r"\[\[([^\]|#]+)", line)}
        rows.append((ordinal, links, " ".join(line.casefold().split())))
    return rows


def load_locations():
    path = ROOT / "greenfield" / "eldenring" / "data.py"
    spec = importlib.util.spec_from_file_location("_eldenpedia_deathroot_data", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module.LOCATIONS


def build(page: dict) -> tuple[list[dict], list[dict]]:
    revision = page["revisions"][0]
    if (int(page["pageid"]), page["title"], int(revision["revid"]), revision["sha1"]) != (
            PAGE_ID, TITLE, REVISION_ID, REVISION_SHA1):
        raise ValueError("refusing an unregistered Eldenpedia Deathroot revision")
    rows = acquisition_rows(revision["slots"]["main"]["content"])
    if len(rows) != len(BINDINGS):
        raise ValueError(f"expected {len(BINDINGS)} acquisition rows, found {len(rows)}")

    current = {ap_id: (region, name) for region, checks in load_locations().items()
               for name, ap_id, _flag in checks}
    leads = []
    for ap_id, source_area, anchor, required_links, required_text in BINDINGS:
        candidates = [
            (ordinal, links) for ordinal, links, raw in rows
            if set(required_links) <= links and required_text in raw
        ]
        if len(candidates) != 1:
            raise ValueError(f"{anchor!r} identifies {len(candidates)} acquisition rows")
        ordinal, _ = candidates[0]
        project_region, location = current[ap_id]
        if ":: Deathroot -" not in location:
            raise ValueError(f"AP id {ap_id} is no longer a Deathroot check")
        leads.append({
            "lead_id": f"eldenpedia-deathroot-revision-{REVISION_ID}-check-{ap_id}",
            "subject_kind": "check", "subject_id": str(ap_id),
            "claim_kind": "acquisition_identity",
            "normalized_value": json.dumps({"anchor": anchor, "item_name": "Deathroot",
                                             "project_region": project_region,
                                             "source_area": source_area},
                                            sort_keys=True, separators=(",", ":")),
            "source_ids": SOURCE_ID,
            "independence_families": "gameplay-wiki:eldenpedia",
            "disposition": "lead_only", "game_version": "unknown",
            "exact_citations": (f"eldenpedia:pageid-{PAGE_ID}:revision-{REVISION_ID}:"
                                f"#Acquisition:{ordinal}"),
            "summary": (f"Eldenpedia revision {REVISION_ID} lists a Deathroot acquisition at "
                        f"{anchor}; its linked anchors identify one current AP Deathroot check."),
            "limitations": ("Community-wiki acquisition lead selected by exact linked anchors. "
                            "It does not prove v1.17 behavior, AP region boundaries, access logic, "
                            "event predicates, route order, or absence of another acquisition."),
        })
    leads.sort(key=lambda row: row["lead_id"])
    manifest = [{
        "source_id": SOURCE_ID, "page_id": str(PAGE_ID), "revision_id": str(REVISION_ID),
        "revision_timestamp": revision["timestamp"], "revision_sha1": revision["sha1"],
        "title": TITLE, "canonical_url": "https://eldenring.wiki.gg/wiki/Deathroot",
        "revision_url": f"https://eldenring.wiki.gg/w/index.php?oldid={REVISION_ID}",
        "acquisition_rows": str(len(rows)), "disposition": "lead_only",
    }]
    return manifest, leads


def render(rows: list[dict], fields: tuple[str, ...]) -> str:
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--write-capture", type=Path)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--leads", type=Path, default=DEFAULT_LEADS)
    args = parser.parse_args()
    page = json.loads(args.capture.read_text(encoding="utf-8")) if args.capture else fetch_revision()
    if args.write_capture:
        args.write_capture.write_text(json.dumps(page, ensure_ascii=False, sort_keys=True),
                                      encoding="utf-8")
    manifest, leads = build(page)
    args.manifest.write_text(render(manifest, PAGE_FIELDS), encoding="utf-8")
    args.leads.write_text(render(leads, LEAD_FIELDS), encoding="utf-8")
    print(json.dumps({"acquisition_rows": len(BINDINGS), "matched_checks": len(leads)},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
