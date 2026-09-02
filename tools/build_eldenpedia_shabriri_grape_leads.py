#!/usr/bin/env python3
"""Bind a pinned Eldenpedia Shabriri Grape list to the three current AP checks."""
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
DEFAULT_MANIFEST = AUDIT / "eldenpedia-shabriri-grape-pages.tsv"
DEFAULT_LEADS = AUDIT / "eldenpedia-shabriri-grape-check-leads.tsv"
API = "https://eldenring.wiki.gg/api.php"
USER_AGENT = "er-archipelago-v060-evidence-audit/1.0"

PAGE_ID = 13775
REVISION_ID = 51506
REVISION_SHA1 = "3cbde246b8fc0f5071784f614dbf948d9ab7f23c"
SOURCE_ID = f"wiki:eldenpedia:page-{PAGE_ID}:revision-{REVISION_ID}"
TITLE = "Shabriri Grape"

PAGE_FIELDS = ("source_id", "page_id", "revision_id", "revision_timestamp", "revision_sha1",
               "title", "canonical_url", "revision_url", "acquisition_rows", "disposition")
LEAD_FIELDS = ("lead_id", "subject_kind", "subject_id", "claim_kind", "normalized_value",
               "source_ids", "independence_families", "disposition", "game_version",
               "exact_citations", "summary", "limitations")

# Each selector is source-local and unique.  The expected flag is then checked against the current
# AP corpus and against the committed ItemLot table before a binding is emitted.
BINDINGS = (
    (7770896, 10007850, "Limgrave", "room past Godrick's throne", "",
     ("Limgrave", "Liurnia of the Lakes")),
    (7772713, 1039417200, "Liurnia of the Lakes", "Purified Ruins", "",
     ("Purified Ruins", "Two Fingers Heirloom")),
    (7770562, 400061, "Liunia of the Lakes", "Revenger's Shack",
     "Edgar received Irina's Letter and witnessed her death at the Bridge of Sacrifice",
     ("Revenger's Shack", "Castellan Edgar", "Irina's Letter", "Bridge of Sacrifice")),
)


def fetch_revision() -> dict:
    params = {"action": "query", "format": "json", "formatversion": "2",
              "revids": str(REVISION_ID), "prop": "revisions",
              "rvprop": "ids|timestamp|sha1|content", "rvslots": "main"}
    request = Request(API + "?" + urlencode(params), headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=60) as response:
        return json.load(response)["query"]["pages"][0]


def acquisition_rows(text: str) -> list[tuple[int, set[str]]]:
    match = re.search(r"(?ims)^==\s*Acquisition\s*==\s*(.*?)(?=^==[^=]|\Z)", text)
    if not match:
        raise ValueError("pinned page has no Acquisition section")
    blocks = re.findall(r"(?ms)^\*([^\n]+)(.*?)(?=^\*|\Z)", match.group(1))
    rows = []
    for ordinal, (heading, body) in enumerate(blocks, 1):
        links = {target.strip() for target in re.findall(r"\[\[([^\]|#]+)", heading + body)}
        rows.append((ordinal, links))
    return rows


def load_locations() -> dict[int, tuple[str, str, int]]:
    path = ROOT / "greenfield" / "eldenring" / "data.py"
    spec = importlib.util.spec_from_file_location("_eldenpedia_shabriri_data", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return {ap_id: (region, name, flag) for region, checks in module.LOCATIONS.items()
            for name, ap_id, flag in checks}


def lot_identities() -> set[tuple[int, str]]:
    with (ROOT / "greenfield" / "flag_lots.tsv").open(encoding="utf-8", newline="") as handle:
        return {(int(row["flag"]), row["name"]) for row in csv.DictReader(handle, delimiter="\t")}


def build(page: dict) -> tuple[list[dict], list[dict]]:
    revision = page["revisions"][0]
    if (int(page["pageid"]), page["title"], int(revision["revid"]), revision["sha1"]) != (
            PAGE_ID, TITLE, REVISION_ID, REVISION_SHA1):
        raise ValueError("refusing an unregistered Eldenpedia Shabriri Grape revision")
    rows = acquisition_rows(revision["slots"]["main"]["content"])
    if len(rows) != len(BINDINGS):
        raise ValueError(f"expected {len(BINDINGS)} acquisition rows, found {len(rows)}")

    current = load_locations()
    lots = lot_identities()
    leads = []
    for ap_id, expected_flag, source_area, anchor, quest_context, required_links in BINDINGS:
        candidates = [(ordinal, links) for ordinal, links in rows if set(required_links) <= links]
        if len(candidates) != 1:
            raise ValueError(f"{anchor!r} identifies {len(candidates)} acquisition rows")
        ordinal, _ = candidates[0]
        project_region, location, flag = current[ap_id]
        if flag != expected_flag or ":: Shabriri Grape -" not in location:
            raise ValueError(f"AP id {ap_id} no longer identifies expected flag {expected_flag}")
        if (flag, "Shabriri Grape") not in lots:
            raise ValueError(f"flag_lots no longer identifies {flag} as a Shabriri Grape award")
        leads.append({
            "lead_id": f"eldenpedia-shabriri-grape-revision-{REVISION_ID}-check-{ap_id}",
            "subject_kind": "check", "subject_id": str(ap_id),
            "claim_kind": "acquisition_identity",
            "normalized_value": json.dumps({"anchor": anchor, "flag": flag,
                                              "item_name": "Shabriri Grape",
                                              "project_region": project_region,
                                              "quest_context": quest_context,
                                              "source_area": source_area},
                                             sort_keys=True, separators=(",", ":")),
            "source_ids": SOURCE_ID,
            "independence_families": "gameplay-wiki:eldenpedia",
            "disposition": "lead_only", "game_version": "unknown",
            "exact_citations": (f"eldenpedia:pageid-{PAGE_ID}:revision-{REVISION_ID}:"
                                f"#Acquisition:{ordinal}"),
            "summary": (f"Eldenpedia revision {REVISION_ID} lists a Shabriri Grape at {anchor}; "
                        "unique linked anchors and the committed ItemLot identity select one AP check."),
            "limitations": ("Community-wiki acquisition lead cross-checked against committed lot data. "
                            "It does not prove v1.17 behavior, AP region boundaries, access logic, "
                            "quest predicates, route order, or absence of another acquisition."),
        })
    leads.sort(key=lambda row: row["lead_id"])
    manifest = [{
        "source_id": SOURCE_ID, "page_id": str(PAGE_ID), "revision_id": str(REVISION_ID),
        "revision_timestamp": revision["timestamp"], "revision_sha1": revision["sha1"],
        "title": TITLE, "canonical_url": "https://eldenring.wiki.gg/wiki/Shabriri_Grape",
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
