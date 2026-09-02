#!/usr/bin/env python3
"""Bind uniquely anchored Golden Seed rows from a pinned Eldenpedia revision."""
from __future__ import annotations

import argparse, csv, importlib.util, json, re
from io import StringIO
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield" / "evidence" / "wiki-audit"
MANIFEST = AUDIT / "eldenpedia-golden-seed-pages.tsv"
LEADS = AUDIT / "eldenpedia-golden-seed-check-leads.tsv"
COVERAGE = AUDIT / "eldenpedia-golden-seed-coverage.json"
API = "https://eldenring.wiki.gg/api.php"
PAGE_ID, REVISION_ID = 8969, 99538
SHA1 = "b3afda3a6fffbe96085e7a5be21d87427129fdc1"
SOURCE_ID = f"wiki:eldenpedia:page-{PAGE_ID}:revision-{REVISION_ID}"
PAGE_FIELDS = ("source_id", "page_id", "revision_id", "revision_timestamp", "revision_sha1", "title", "canonical_url", "revision_url", "acquisition_rows", "disposition")
LEAD_FIELDS = ("lead_id", "subject_kind", "subject_id", "claim_kind", "normalized_value", "source_ids", "independence_families", "disposition", "game_version", "exact_citations", "summary", "limitations")

# AP id, flag, source heading, unique normalized source-row selector.
BINDINGS = (
    (7771049, 12017100, "Ainsel River", "western side of nokstella eternal city"),
    (7771145, 12017997, "Ainsel River", "putrid tree spirit in the grand cloister"),
    (7772688, 1038517400, "Altus Plateau", "erdtree gazing hill"),
    (7772743, 1039517400, "Altus Plateau", "altus highway junction"),
    (7772845, 1042507020, "Altus Plateau", "ulcerated tree spirit south of outer wall phantom tree"),
    (7772850, 1042547400, "Altus Plateau", "dominula windmill village"),
    (7774314, 1041547400, "Altus Plateau", "minor erdtree altus plateau"),
    (7773050, 1049377020, "Caelid", "road to redmane castle"),
    (7773087, 1050397100, "Caelid", "sellia town of sorcery"),
    (7774512, 1051437020, "Caelid", "path to the bestial sanctum"),
    (7900003, 520160, "Caelid", "putrid tree spirit in war dead catacombs"),
    (7774481, 1049557800, "Consecrated Snowfield", "north east of the consecrated snowfield"),
    (7771485, 13007980, "Crumbling Farum Azula", "dragon temple rooftop"),
    (7771486, 13007990, "Crumbling Farum Azula", "dragon temple site of grace"),
    (7771027, 11007993, "Altus Plateau", "ulcerated tree spirit in leyndell royal capital"),
    (7773927, 11007990, "Altus Plateau", "valiant gargoyle south of the west capital rampart"),
    (7770583, 400191, "Limgrave", "roderika has moved to roundtable hold"),
    (7772953, 1046367100, "Limgrave", "entrance to fort haight"),
    (7772631, 1037507100, "Liurnia of the Lakes", "southwest of the ravine veiled village"),
    (7774164, 1035507300, "Liurnia of the Lakes", "caria manor past the room containing the manor upper level"),
    (7771553, 14007990, "Liurnia of the Lakes", "academy of raya lucaria west of the courtyard"),
    (7773063, 1049527800, "Mountaintops of the Giants", "forbidden lands near the black blade kindred"),
    (7773183, 1052537800, "Mountaintops of the Giants", "south of the giant s gravepost"),
    (7773820, 520180, "Mountaintops of the Giants", "giants mountaintop catacombs"),
    (7771149, 12027040, "Siofra River", "worshipper s woods"),
    (7770832, 10007195, "Limgrave", "uncerated tree spirit in the lower area of the castle"),
    (7770885, 10007730, "Limgrave", "secluded cell site of grace"),
    (7772906, 1044327020, "Limgrave", "weeping peninsula near the path to castle morne"),
)
REFUSED = {
    "7772847": "one 2x source row cannot select AP slot 1",
    "7772848": "one 2x source row cannot select AP slot 2",
    "7772897": "no distinct source row selects this second two-seed lot",
    "7772898": "no distinct source row selects this second two-seed lot",
    "7773716": "the source does not distinguish this Roderika/Lake-Facing Cliffs check",
}


def normalize(text: str) -> str:
    text = re.sub(r"\[\[([^]|#]+)(?:\|([^]]+))?\]\]", lambda m: m.group(2) or m.group(1), text)
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def fetch() -> dict:
    params = {"action": "query", "format": "json", "formatversion": "2", "revids": str(REVISION_ID), "prop": "revisions", "rvprop": "ids|timestamp|sha1|content", "rvslots": "main"}
    req = Request(API + "?" + urlencode(params), headers={"User-Agent": "er-archipelago-v060-evidence-audit/1.0"})
    with urlopen(req, timeout=60) as response:
        return json.load(response)["query"]["pages"][0]


def rows(text: str) -> list[tuple[int, str, str]]:
    section = re.search(r"(?ims)^==Acquisition==\s*(.*?)(?=^==[^=]|\Z)", text)
    if not section: raise ValueError("pinned page has no Acquisition section")
    area, result = "", []
    for line in section.group(1).splitlines():
        if line.startswith("**"):
            result.append((len(result) + 1, area, normalize(line[2:])))
        elif line.startswith("*"):
            links = re.findall(r"\[\[([^]|#]+)", line)
            area = links[0] if links else normalize(line[1:])
    return result


def locations() -> dict[int, tuple[str, str, int]]:
    spec = importlib.util.spec_from_file_location("_golden_seed_data", ROOT / "greenfield" / "eldenring" / "data.py")
    module = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(module)
    return {ap_id: (region, name, flag) for region, checks in module.LOCATIONS.items() for name, ap_id, flag in checks}


def lots() -> dict[int, set[tuple[int, str]]]:
    with (ROOT / "greenfield" / "flag_lots.tsv").open(encoding="utf-8", newline="") as handle:
        result: dict[int, set[tuple[int, str]]] = {}
        for row in csv.DictReader(handle, delimiter="\t"):
            result.setdefault(int(row["flag"]), set()).add((int(row["item_id"]), row["name"]))
        return result


def build(page: dict) -> tuple[list[dict], list[dict], dict]:
    revision = page["revisions"][0]
    if (page["pageid"], page["title"], revision["revid"], revision["sha1"]) != (PAGE_ID, "Golden Seed", REVISION_ID, SHA1):
        raise ValueError("refusing an unregistered Golden Seed revision")
    source_rows, current, lot_rows, leads = rows(revision["slots"]["main"]["content"]), locations(), lots(), []
    for ap_id, expected_flag, source_area, selector in BINDINGS:
        matches = [(ordinal, area) for ordinal, area, text in source_rows if selector in text]
        if len(matches) != 1 or matches[0][1] != source_area:
            raise ValueError(f"selector {selector!r} found {matches}")
        ordinal, _ = matches[0]; project_region, location, flag = current[ap_id]
        golden_rows = [(item_id, name) for item_id, name in lot_rows[flag] if item_id == 10010]
        if (flag != expected_flag or ":: Golden Seed -" not in location or
                golden_rows != [(10010, "Golden Seed")]):
            raise ValueError(f"AP/ItemLot identity drift for {ap_id}")
        leads.append({"lead_id": f"eldenpedia-golden-seed-revision-{REVISION_ID}-check-{ap_id}", "subject_kind": "check", "subject_id": str(ap_id), "claim_kind": "acquisition_identity", "normalized_value": json.dumps({"flag": flag, "item_name": "Golden Seed", "project_region": project_region, "source_area": source_area, "source_selector": selector}, sort_keys=True, separators=(",", ":")), "source_ids": SOURCE_ID, "independence_families": "gameplay-wiki:eldenpedia", "disposition": "lead_only", "game_version": "unknown", "exact_citations": f"eldenpedia:pageid-{PAGE_ID}:revision-{REVISION_ID}:#Acquisition:{ordinal}", "summary": f"Eldenpedia revision {REVISION_ID} identifies a Golden Seed by {selector}; that unique acquisition row and committed ItemLot id select one AP check.", "limitations": "Community-wiki acquisition lead cross-checked against committed lot data. It does not prove v1.17 behavior, AP region boundaries, access logic, route order, coordinates, or completeness."})
    leads.sort(key=lambda row: row["lead_id"])
    manifest = [{"source_id": SOURCE_ID, "page_id": str(PAGE_ID), "revision_id": str(REVISION_ID), "revision_timestamp": revision["timestamp"], "revision_sha1": SHA1, "title": "Golden Seed", "canonical_url": "https://eldenring.wiki.gg/wiki/Golden_Seed", "revision_url": f"https://eldenring.wiki.gg/w/index.php?oldid={REVISION_ID}", "acquisition_rows": str(len(source_rows)), "disposition": "lead_only"}]
    coverage = {"ap_checks": 43, "prior_union_checks": 10, "new_exact_bindings": len(leads), "union_after": 10 + len(leads), "remaining_unbound": len(REFUSED), "refused_ap_checks": REFUSED}
    return manifest, leads, coverage


def render(data: list[dict], fields: tuple[str, ...]) -> str:
    out = StringIO(newline=""); writer = csv.DictWriter(out, fieldnames=fields, delimiter="\t", lineterminator="\n"); writer.writeheader(); writer.writerows(data); return out.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--capture", type=Path); args = parser.parse_args()
    page = json.loads(args.capture.read_text(encoding="utf-8")) if args.capture else fetch()
    if "query" in page: page = page["query"]["pages"][0]
    manifest, leads, coverage = build(page)
    MANIFEST.write_text(render(manifest, PAGE_FIELDS), encoding="utf-8"); LEADS.write_text(render(leads, LEAD_FIELDS), encoding="utf-8")
    COVERAGE.write_text(json.dumps(coverage, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(coverage, sort_keys=True)); return 0


if __name__ == "__main__": raise SystemExit(main())
