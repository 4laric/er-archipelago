#!/usr/bin/env python3
"""Bind pinned Eldenpedia Crystal Tear acquisitions to current AP checks."""
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
MANIFEST = AUDIT / "eldenpedia-crystal-tear-pages.tsv"
LEADS = AUDIT / "eldenpedia-crystal-tear-check-leads.tsv"
API = "https://eldenring.wiki.gg/api.php"
USER_AGENT = "er-archipelago-v060-evidence-audit/1.0"
PAGE_FIELDS = ("source_id", "page_id", "revision_id", "revision_timestamp", "revision_sha1",
               "title", "canonical_url", "revision_url", "acquisition_rows", "disposition")
LEAD_FIELDS = ("lead_id", "subject_kind", "subject_id", "claim_kind", "normalized_value",
               "source_ids", "independence_families", "disposition", "game_version",
               "exact_citations", "summary", "limitations")

# title: page id, revision id, MediaWiki SHA1
PAGES = {
    "Cerulean Crystal Tear": (4364, 96843, "56969237c8a4d662413416c4b7d480eba04e265a"),
    "Crimson Crystal Tear": (7290, 96842, "33beaab322e3c41359c8142e75f23742b7382ce4"),
    "Crimsonburst Crystal Tear": (623, 95373, "9f76b854e7e5de683dc2bf2e88bed1a12b3db8cd"),
    "Crimsonspill Crystal Tear": (134, 96812, "efcc31d7f49928f6f1572f8a00a61ee7fc787dd4"),
    "Dexterity-knot Crystal Tear": (982, 96821, "a2426d3a32fa463691c05eec5232857710ff8631"),
    "Faith-knot Crystal Tear": (10069, 96823, "32dd0a29af169bbc7d5485cc73d5603edceb660a"),
    "Glovewort Crystal Tear": (13099, 96904, "a6afa302b8c319507294286ac50c11fbf75edd33"),
    "Greenburst Crystal Tear": (9211, 99410, "51b284581c7be79a37fc2c817e20ad59a8c41135"),
    "Greenspill Crystal Tear": (12727, 96819, "ee6cc5bd77a5329c2bcc4430c763b9248175b1ca"),
    "Intelligence-knot Crystal Tear": (9460, 96822, "cb44217d0142f6089a4b90f85aa59d80424b8ee1"),
    "Purifying Crystal Tear": (5506, 96910, "19edaae6610d572d8d337ff47e27e12f37c00e46"),
    "Ruptured Crystal Tear": (10655, 96913, "fc14803e3759d9ad9c95a6cc5fb3a44d085f0998"),
    "Strength-knot Crystal Tear": (10644, 96820, "7baae6f9f4ab450db9076be66e4e70dd50abdce0"),
    "Windy Crystal Tear": (6576, 96845, "13f58d1859bde25d34ac9da48e8f1e2d44ba6300"),
    "Winged Crystal Tear": (13911, 96848, "8375d369cb59b8123e589f9e91cd91762f0d1c7a"),
}

# AP id, flag, title, source-local area/site link used to separate repeated item names.
BINDINGS = (
    (7770029, 65040, "Cerulean Crystal Tear", "Liurnia of the Lakes"),
    (7773666, 65050, "Cerulean Crystal Tear", "Mountaintops of the Giants"),
    (7773665, 65020, "Crimson Crystal Tear", "Third Church of Marika"),
    (7770028, 65030, "Crimson Crystal Tear", "Capital Outskirts"),
    (7770031, 65090, "Crimsonburst Crystal Tear", "Weeping Peninsula"),
    (7773663, 65000, "Crimsonspill Crystal Tear", "Wormface"),
    (7773675, 65220, "Dexterity-knot Crystal Tear", "Scenic Isle"),
    (7770038, 65240, "Faith-knot Crystal Tear", "Church of Pilgrimage"),
    (7773688, 65460, "Glovewort Crystal Tear", "Charo's Hidden Grave"),
    (7770032, 65100, "Greenburst Crystal Tear", "Putrid Avatar"),
    (7773664, 65010, "Greenspill Crystal Tear", "Mistwood"),
    (7773676, 65230, "Intelligence-knot Crystal Tear", "Caria Manor"),
    (7770039, 65270, "Purifying Crystal Tear", "Eleonora, Violet Bloody Finger"),
    (7773672, 65160, "Ruptured Crystal Tear", "Liurnia of the Lakes"),
    (7773673, 65170, "Ruptured Crystal Tear", "Consecrated Snowfield"),
    (7773674, 65210, "Strength-knot Crystal Tear", "Warmaster's Shack"),
    (7770034, 65150, "Windy Crystal Tear", "Southern Aeonia Swamp Bank"),
    (7770033, 65120, "Winged Crystal Tear", "Hermit Merchant's Shack"),
)

ITEM_IDS = {
    "Cerulean Crystal Tear": {11004, 11005}, "Crimson Crystal Tear": {11002, 11003},
    "Crimsonburst Crystal Tear": {11009}, "Crimsonspill Crystal Tear": {11000},
    "Dexterity-knot Crystal Tear": {11022}, "Faith-knot Crystal Tear": {11024},
    "Glovewort Crystal Tear": {2011060}, "Greenburst Crystal Tear": {11010},
    "Greenspill Crystal Tear": {11001}, "Intelligence-knot Crystal Tear": {11023},
    "Purifying Crystal Tear": {11027}, "Ruptured Crystal Tear": {11016, 11017},
    "Strength-knot Crystal Tear": {11021}, "Windy Crystal Tear": {11015},
    "Winged Crystal Tear": {11012},
}


def fetch_pages() -> list[dict]:
    params = {"action": "query", "format": "json", "formatversion": "2",
              "titles": "|".join(PAGES), "prop": "revisions",
              "rvprop": "ids|timestamp|sha1|content", "rvslots": "main"}
    req = Request(API + "?" + urlencode(params), headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=60) as response:
        return json.load(response)["query"]["pages"]


def acquisition(text: str) -> str:
    match = re.search(r"(?ims)^==[^\n]*Acquisition[^\n]*==\s*(.*?)(?=^==[^=]|\Z)", text)
    if not match:
        raise ValueError("pinned page has no Acquisition section")
    return match.group(1)


def load_locations() -> dict[int, tuple[str, str, int]]:
    spec = importlib.util.spec_from_file_location("_crystal_tear_data", ROOT / "greenfield" / "eldenring" / "data.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return {ap_id: (region, name, flag) for region, checks in module.LOCATIONS.items()
            for name, ap_id, flag in checks}


def lot_identities() -> dict[int, tuple[int, str]]:
    with (ROOT / "greenfield" / "flag_lots.tsv").open(encoding="utf-8", newline="") as handle:
        return {int(row["flag"]): (int(row["item_id"]), row["name"])
                for row in csv.DictReader(handle, delimiter="\t")}


def build(pages: list[dict]) -> tuple[list[dict], list[dict]]:
    by_title = {page["title"]: page for page in pages}
    if set(by_title) != set(PAGES):
        raise ValueError("pinned Crystal Tear page set changed")
    sections, manifests = {}, []
    for title, (page_id, revision_id, sha1) in PAGES.items():
        page = by_title[title]
        revision = page["revisions"][0]
        if (page["pageid"], revision["revid"], revision["sha1"]) != (page_id, revision_id, sha1):
            raise ValueError(f"refusing unregistered revision for {title}")
        sections[title] = acquisition(revision["slots"]["main"]["content"])
        source_id = f"wiki:eldenpedia:page-{page_id}:revision-{revision_id}"
        manifests.append({"source_id": source_id, "page_id": str(page_id),
                          "revision_id": str(revision_id), "revision_timestamp": revision["timestamp"],
                          "revision_sha1": sha1, "title": title,
                          "canonical_url": "https://eldenring.wiki.gg/wiki/" + title.replace(" ", "_"),
                          "revision_url": f"https://eldenring.wiki.gg/w/index.php?oldid={revision_id}",
                          "acquisition_rows": "1", "disposition": "lead_only"})
    current, lots, leads = load_locations(), lot_identities(), []
    for ap_id, expected_flag, title, anchor in BINDINGS:
        if f"[[{anchor}" not in sections[title]:
            raise ValueError(f"{title} acquisition no longer links {anchor!r}")
        project_region, location, flag = current[ap_id]
        item_id, lot_name = lots[flag]
        if (flag != expected_flag or f":: {title}" not in location or
                item_id not in ITEM_IDS[title] or (lot_name and lot_name != title)):
            raise ValueError(f"AP/ItemLot identity drift for {ap_id} ({title})")
        page_id, revision_id, _ = PAGES[title]
        source_id = f"wiki:eldenpedia:page-{page_id}:revision-{revision_id}"
        leads.append({
            "lead_id": f"eldenpedia-crystal-tear-page-{page_id}-revision-{revision_id}-check-{ap_id}",
            "subject_kind": "check", "subject_id": str(ap_id), "claim_kind": "acquisition_identity",
            "normalized_value": json.dumps({"anchor": anchor, "flag": flag, "item_name": title,
                                             "project_region": project_region},
                                            sort_keys=True, separators=(",", ":")),
            "source_ids": source_id, "independence_families": "gameplay-wiki:eldenpedia",
            "disposition": "lead_only", "game_version": "unknown",
            "exact_citations": f"eldenpedia:pageid-{page_id}:revision-{revision_id}:#Acquisition:{anchor}",
            "summary": f"Eldenpedia revision {revision_id} links {title} acquisition to {anchor}; the source-local anchor and committed ItemLot identity select one AP check.",
            "limitations": "Community-wiki acquisition lead cross-checked against committed lot data. It does not prove v1.17 behavior, AP region boundaries, access logic, route order, coordinates, or event predicates.",
        })
    manifests.sort(key=lambda row: int(row["page_id"]))
    leads.sort(key=lambda row: row["lead_id"])
    return manifests, leads


def render(rows: list[dict], fields: tuple[str, ...]) -> str:
    out = StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--write-capture", type=Path)
    args = parser.parse_args()
    pages = json.loads(args.capture.read_text(encoding="utf-8")) if args.capture else fetch_pages()
    if isinstance(pages, dict):
        pages = pages["query"]["pages"]
    if args.write_capture:
        args.write_capture.write_text(json.dumps(pages, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    manifests, leads = build(pages)
    MANIFEST.write_text(render(manifests, PAGE_FIELDS), encoding="utf-8")
    LEADS.write_text(render(leads, LEAD_FIELDS), encoding="utf-8")
    print(json.dumps({"matched_checks": len(leads), "pinned_pages": len(manifests)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
