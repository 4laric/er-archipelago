#!/usr/bin/env python3
"""Bind only uniquely resolvable Seedbed Curse acquisitions from a pinned wiki revision."""
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
DEFAULT_MANIFEST = AUDIT / "eldenpedia-seedbed-curse-pages.tsv"
DEFAULT_LEADS = AUDIT / "eldenpedia-seedbed-curse-check-leads.tsv"
API = "https://eldenring.wiki.gg/api.php"
USER_AGENT = "er-archipelago-v060-evidence-audit/1.0"
PAGE_ID = 3879
REVISION_ID = 100628
REVISION_SHA1 = "2472387a6d4b9b62f475bae74e1ef9b539e7d21a"
SOURCE_ID = f"wiki:eldenpedia:page-{PAGE_ID}:revision-{REVISION_ID}"
TITLE = "Seedbed Curse"

PAGE_FIELDS = ("source_id", "page_id", "revision_id", "revision_timestamp", "revision_sha1",
               "title", "canonical_url", "revision_url", "acquisition_rows", "disposition")
LEAD_FIELDS = ("lead_id", "subject_kind", "subject_id", "claim_kind", "normalized_value",
               "source_ids", "independence_families", "disposition", "game_version",
               "exact_citations", "summary", "limitations")

# Rows 3 and 4 are the only source areas with exactly one current AP Seedbed Curse check.  The
# duplicate Leyndell and Haligtree rows deliberately remain unbound: ItemLot identity alone cannot
# tell which same-region physical pickup is which.
ROWS = (
    ("East Capital Rampart", "cracked ceiling", None, None, "Leyndell, Royal Capital"),
    ("West Capital Rampart", "Fortified Manor", None, None, "Leyndell, Royal Capital"),
    ("Capital Outskirts", "Big Boggart", 7770596, 400308, "Capital Outskirts"),
    ("Mt. Gelmir", "Audience Pathway", 7771716, 16007700, "Mt. Gelmir"),
    ("Miquella's Haligtree", "balcony on the western wall", None, None, "Miquella's Haligtree"),
    ("Miquella's Haligtree", "dark room directly below", None, None, "Miquella's Haligtree"),
)


def fetch_revision() -> dict:
    params = {"action": "query", "format": "json", "formatversion": "2",
              "revids": str(REVISION_ID), "prop": "revisions",
              "rvprop": "ids|timestamp|sha1|content", "rvslots": "main"}
    request = Request(API + "?" + urlencode(params), headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=60) as response:
        return json.load(response)["query"]["pages"][0]


def acquisition_rows(text: str) -> list[tuple[int, str, str, set[str]]]:
    match = re.search(r"(?ims)^==\s*Acquisition\s*==\s*(.*?)(?=^==[^=]|\Z)", text)
    if not match:
        raise ValueError("pinned page has no Acquisition section")
    current_heading = ""
    rows = []
    for raw in match.group(1).splitlines():
        line = raw.strip()
        if not line:
            continue
        if not line.startswith("*"):
            current_heading = line
            continue
        links = {target.strip() for target in re.findall(r"\[\[([^\]|#]+)",
                                                         current_heading + " " + line)}
        rows.append((len(rows) + 1, current_heading, line[1:].strip(), links))
    return rows


def load_locations() -> dict[int, tuple[str, str, int]]:
    spec = importlib.util.spec_from_file_location(
        "_eldenpedia_seedbed_data", ROOT / "greenfield" / "eldenring" / "data.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return {ap_id: (region, name, flag) for region, checks in module.LOCATIONS.items()
            for name, ap_id, flag in checks}


def lot_identities() -> set[tuple[int, str]]:
    with (ROOT / "greenfield" / "flag_lots.tsv").open(encoding="utf-8", newline="") as handle:
        return {(int(row["flag"]), row["name"]) for row in csv.DictReader(handle, delimiter="\t")}


def verify_big_boggart_evidence() -> None:
    conditions_path = ROOT / "greenfield" / "questline_conditions.tsv"
    lines = [line for line in conditions_path.read_text(encoding="utf-8").splitlines()
             if not line.startswith("#")]
    conditions = list(csv.DictReader(lines, delimiter="\t"))
    if not any(row["target_flag"] == "400308" and row["target_lot"] == "113010"
               and row["root_class"] == "BOSS_KILL" and row["source_id"] == "4143"
               for row in conditions):
        raise ValueError("questline conditions no longer connect flag 400308 to NPC death flag 4143")
    name_lines = [line for line in (ROOT / "greenfield" / "flag_names.tsv").read_text(
        encoding="utf-8").splitlines() if not line.startswith("#")]
    names = {row["flag"]: row["name_en"] for row in csv.DictReader(name_lines, delimiter="\t")}
    if "Rogue_Killed by a shit eater" not in names.get("4143", ""):
        raise ValueError("flag 4143 no longer identifies the Dung Eater killing the rogue")


def build(page: dict) -> tuple[list[dict], list[dict]]:
    revision = page["revisions"][0]
    if (int(page["pageid"]), page["title"], int(revision["revid"]), revision["sha1"]) != (
            PAGE_ID, TITLE, REVISION_ID, REVISION_SHA1):
        raise ValueError("refusing an unregistered Eldenpedia Seedbed Curse revision")
    parsed = acquisition_rows(revision["slots"]["main"]["content"])
    if len(parsed) != len(ROWS):
        raise ValueError(f"expected {len(ROWS)} acquisition rows, found {len(parsed)}")
    current = load_locations()
    seedbeds = {ap_id: value for ap_id, value in current.items() if ":: Seedbed Curse -" in value[1]}
    lots = lot_identities()
    verify_big_boggart_evidence()
    if len(seedbeds) != 6:
        raise ValueError(f"expected six current Seedbed Curse checks, found {len(seedbeds)}")

    leads = []
    for parsed_row, expected in zip(parsed, ROWS):
        ordinal, heading, bullet, links = parsed_row
        heading_token, bullet_token, ap_id, expected_flag, source_area = expected
        source_text = heading + " " + bullet
        if heading_token not in heading or bullet_token.casefold() not in source_text.casefold():
            raise ValueError(f"Seedbed Curse acquisition row {ordinal} changed selector")
        if ap_id is None:
            subject_kind = "acquisition_row"
            subject_id = f"{SOURCE_ID}:Acquisition:{ordinal}"
            value = {"anchor": bullet_token, "item_name": TITLE, "source_area": source_area,
                     "refusal_reason": "same-region duplicate lacks a stable source-to-flag join"}
            summary = (f"Eldenpedia revision {REVISION_ID} lists a Seedbed Curse at {bullet_token}; "
                       "the row remains unbound because committed lot data has a same-region duplicate.")
        else:
            project_region, location, flag = seedbeds[ap_id]
            if flag != expected_flag or (flag, TITLE) not in lots:
                raise ValueError(f"AP id {ap_id} no longer has expected Seedbed Curse lot identity")
            # The source area selects exactly one current project region for this item family.
            same_region = [candidate for candidate, (region, _name, _flag) in seedbeds.items()
                           if region == project_region]
            if len(same_region) != 1 or same_region[0] != ap_id:
                raise ValueError(f"AP region {project_region} no longer uniquely selects {ap_id}")
            subject_kind, subject_id = "check", str(ap_id)
            value = {"anchor": bullet_token, "flag": flag, "item_name": TITLE,
                     "project_region": project_region, "source_area": source_area}
            if flag == 400308:
                value["game_data_anchor"] = "questline_conditions:400308:lot-113010:BOSS_KILL-4143"
            summary = (f"Eldenpedia revision {REVISION_ID} lists a Seedbed Curse at {bullet_token}; "
                       "the source area and committed ItemLot identity select one current AP check.")
        leads.append({
            "lead_id": f"eldenpedia-seedbed-curse-revision-{REVISION_ID}-row-{ordinal}",
            "subject_kind": subject_kind, "subject_id": subject_id,
            "claim_kind": "acquisition_identity",
            "normalized_value": json.dumps(value, sort_keys=True, separators=(",", ":")),
            "source_ids": SOURCE_ID, "independence_families": "gameplay-wiki:eldenpedia",
            "disposition": "lead_only", "game_version": "unknown",
            "exact_citations": (f"eldenpedia:pageid-{PAGE_ID}:revision-{REVISION_ID}:"
                                f"#Acquisition:{ordinal}"),
            "summary": summary,
            "limitations": ("Community-wiki acquisition lead cross-checked against committed lot data. "
                            "It does not prove v1.17 behavior, AP region boundaries, access logic, "
                            "quest predicates, route order, or absence of another acquisition."),
        })
    manifest = [{
        "source_id": SOURCE_ID, "page_id": str(PAGE_ID), "revision_id": str(REVISION_ID),
        "revision_timestamp": revision["timestamp"], "revision_sha1": revision["sha1"],
        "title": TITLE, "canonical_url": "https://eldenring.wiki.gg/wiki/Seedbed_Curse",
        "revision_url": f"https://eldenring.wiki.gg/w/index.php?oldid={REVISION_ID}",
        "acquisition_rows": str(len(parsed)), "disposition": "lead_only",
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
    print(json.dumps({"acquisition_rows": 6, "matched_checks": 2, "refused_rows": 4},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
