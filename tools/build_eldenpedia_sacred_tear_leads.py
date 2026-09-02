#!/usr/bin/env python3
"""Bind the pinned Eldenpedia Sacred Tear church list to current AP checks."""
from __future__ import annotations

import argparse, csv, importlib.util, json, re
from io import StringIO
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield" / "evidence" / "wiki-audit"
DEFAULT_MANIFEST = AUDIT / "eldenpedia-sacred-tear-pages.tsv"
DEFAULT_LEADS = AUDIT / "eldenpedia-sacred-tear-check-leads.tsv"
API = "https://eldenring.wiki.gg/api.php"
USER_AGENT = "er-archipelago-v060-evidence-audit/1.0"
PAGE_ID, REVISION_ID = 13254, 99877
REVISION_SHA1 = "c7a13f72bb1579728cba9811dfbdddf1a97de308"
SOURCE_ID = f"wiki:eldenpedia:page-{PAGE_ID}:revision-{REVISION_ID}"
TITLE = "Sacred Tear"
PAGE_FIELDS = ("source_id", "page_id", "revision_id", "revision_timestamp", "revision_sha1",
               "title", "canonical_url", "revision_url", "acquisition_rows", "disposition")
LEAD_FIELDS = ("lead_id", "subject_kind", "subject_id", "claim_kind", "normalized_value",
               "source_ids", "independence_families", "disposition", "game_version",
               "exact_citations", "summary", "limitations")

# AP id, flag, source area, exact linked church. The thirteenth AP Sacred Tear, at
# Ruin-Strewn Precipice, is deliberately not bound because this revision does not list it.
BINDINGS = (
    (7772958, 1046387100, "Limgrave", "Third Church of Marika"),
    (7772917, 1044337100, "Limgrave", "Callu Baptismal Church"),
    (7772786, 1041337200, "Limgrave", "Fourth Church of Marika"),
    (7772881, 1043357100, "Limgrave", "Church of Pilgrimage"),
    (7772710, 1039397000, "Liurnia of the Lakes", "Church of Irith"),
    (7772585, 1036497000, "Liurnia of the Lakes", "Bellum Church"),
    (7772627, 1037497100, "Liurnia of the Lakes", "Church of Inhibition"),
    (7773077, 1050387020, "Caelid", "Church of the Plague"),
    (7772744, 1039527400, "Altus Plateau", "Second Church of Marika"),
    (7772767, 1040517400, "Altus Plateau", "Stormcaller Church"),
    (7773134, 1051537800, "Mountaintops of the Giants", "Church of Repose"),
    (7773205, 1054557800, "Mountaintops of the Giants", "First Church of Marika"),
)


def fetch_revision() -> dict:
    params = {"action": "query", "format": "json", "formatversion": "2",
              "revids": str(REVISION_ID), "prop": "revisions",
              "rvprop": "ids|timestamp|sha1|content", "rvslots": "main"}
    req = Request(API + "?" + urlencode(params), headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=60) as response:
        return json.load(response)["query"]["pages"][0]


def acquisition_rows(text: str) -> list[tuple[int, str, str]]:
    match = re.search(r"(?ims)^==[^\n]*Acquisition[^\n]*==\s*(.*?)(?=^==[^=]|\Z)", text)
    if not match:
        raise ValueError("pinned page has no Acquisition section")
    area = ""
    rows = []
    for line in match.group(1).splitlines():
        links = re.findall(r"\[\[([^\]|#]+)", line)
        if line.startswith("**") and links:
            rows.append((len(rows) + 1, area, links[0].strip()))
        elif line.startswith("*") and links:
            area = links[0].strip()
    return rows


def load_locations() -> dict[int, tuple[str, str, int]]:
    path = ROOT / "greenfield" / "eldenring" / "data.py"
    spec = importlib.util.spec_from_file_location("_eldenpedia_sacred_tear_data", path)
    module = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(module)
    return {ap_id: (region, name, flag) for region, checks in module.LOCATIONS.items()
            for name, ap_id, flag in checks}


def lot_identities() -> set[tuple[int, str]]:
    with (ROOT / "greenfield" / "flag_lots.tsv").open(encoding="utf-8", newline="") as handle:
        return {(int(row["flag"]), row["name"]) for row in csv.DictReader(handle, delimiter="\t")}


def build(page: dict) -> tuple[list[dict], list[dict]]:
    revision = page["revisions"][0]
    if (int(page["pageid"]), page["title"], int(revision["revid"]), revision["sha1"]) != (
            PAGE_ID, TITLE, REVISION_ID, REVISION_SHA1):
        raise ValueError("refusing an unregistered Eldenpedia Sacred Tear revision")
    rows = acquisition_rows(revision["slots"]["main"]["content"])
    if len(rows) != len(BINDINGS):
        raise ValueError(f"expected {len(BINDINGS)} acquisition rows, found {len(rows)}")
    current, lots, leads = load_locations(), lot_identities(), []
    for ap_id, expected_flag, source_area, church in BINDINGS:
        candidates = [(ordinal, area) for ordinal, area, anchor in rows if anchor == church]
        if candidates != [(next(o for o, a, c in rows if c == church), source_area)]:
            raise ValueError(f"{church!r} is not one unique acquisition row in {source_area}")
        ordinal, _ = candidates[0]
        project_region, location, flag = current[ap_id]
        if flag != expected_flag or ":: Sacred Tear -" not in location:
            raise ValueError(f"AP id {ap_id} no longer identifies expected flag {expected_flag}")
        if (flag, "Sacred Tear") not in lots:
            raise ValueError(f"flag_lots no longer identifies {flag} as a Sacred Tear award")
        leads.append({
            "lead_id": f"eldenpedia-sacred-tear-revision-{REVISION_ID}-check-{ap_id}",
            "subject_kind": "check", "subject_id": str(ap_id),
            "claim_kind": "acquisition_identity",
            "normalized_value": json.dumps({"anchor": church, "flag": flag,
                                             "item_name": "Sacred Tear",
                                             "project_region": project_region,
                                             "source_area": source_area},
                                            sort_keys=True, separators=(",", ":")),
            "source_ids": SOURCE_ID, "independence_families": "gameplay-wiki:eldenpedia",
            "disposition": "lead_only", "game_version": "unknown",
            "exact_citations": f"eldenpedia:pageid-{PAGE_ID}:revision-{REVISION_ID}:#Acquisition:{ordinal}",
            "summary": f"Eldenpedia revision {REVISION_ID} lists a Sacred Tear at {church}; the unique linked church and committed ItemLot identity select one AP check.",
            "limitations": "Community-wiki acquisition lead cross-checked against committed lot data. It does not prove v1.17 behavior, AP region boundaries, access logic, route order, or completeness; the AP Ruin-Strewn Precipice Sacred Tear is not listed in this revision.",
        })
    leads.sort(key=lambda row: row["lead_id"])
    manifest = [{"source_id": SOURCE_ID, "page_id": str(PAGE_ID),
                 "revision_id": str(REVISION_ID), "revision_timestamp": revision["timestamp"],
                 "revision_sha1": revision["sha1"], "title": TITLE,
                 "canonical_url": "https://eldenring.wiki.gg/wiki/Sacred_Tear",
                 "revision_url": f"https://eldenring.wiki.gg/w/index.php?oldid={REVISION_ID}",
                 "acquisition_rows": str(len(rows)), "disposition": "lead_only"}]
    return manifest, leads


def render(rows: list[dict], fields: tuple[str, ...]) -> str:
    out = StringIO(newline=""); writer = csv.DictWriter(out, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader(); writer.writerows(rows); return out.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--capture", type=Path)
    parser.add_argument("--write-capture", type=Path); parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--leads", type=Path, default=DEFAULT_LEADS); args = parser.parse_args()
    page = json.loads(args.capture.read_text(encoding="utf-8")) if args.capture else fetch_revision()
    if args.write_capture:
        args.write_capture.write_text(json.dumps(page, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    manifest, leads = build(page); args.manifest.write_text(render(manifest, PAGE_FIELDS), encoding="utf-8")
    args.leads.write_text(render(leads, LEAD_FIELDS), encoding="utf-8")
    print(json.dumps({"acquisition_rows": len(BINDINGS), "matched_checks": len(leads), "unmatched_ap_checks": 1}, sort_keys=True)); return 0


if __name__ == "__main__": raise SystemExit(main())
