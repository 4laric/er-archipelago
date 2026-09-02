#!/usr/bin/env python3
"""Resolve Redmaw merchant-sheet ambiguities against explicit AP shop evidence.

This is deliberately narrower than name matching: a repeated item label is emitted only when the
pinned sheet's merchant section and current AP description or physical-shop datamine leave exactly
one candidate. If two sheet contexts resolve to the same AP check, both are refused.
The source still does not prove AP's region label or any access rule, so every row remains an
identity-only discovery lead.
"""

from __future__ import annotations

import argparse
import csv
from io import StringIO
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "greenfield/evidence/wiki-audit/redmaw-merchant-check-leads.tsv"
DEFAULT_REPORT = ROOT / "greenfield/evidence/wiki-audit/redmaw-merchant-coverage.json"
WIKIGG_REVISIONS = ROOT / "greenfield/evidence/wiki-audit/redmaw-merchant-wikigg-revisions.tsv"
MERCHANT_SHOPS = ROOT / "greenfield/merchant_shops.tsv"


def load_builder():
    path = ROOT / "tools/build_redmaw_checklist_leads.py"
    spec = importlib.util.spec_from_file_location("_redmaw_checklists", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def load_repo_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


# Section ids are immutable anchors in the pinned merchant sheet. Region is used only to narrow
# same-named merchant classes; it is not emitted as an external region claim.
MERCHANT_CONTEXT = {
    "kale": ("Limgrave", ("Merchant Kalé",)),
    "sellen": (None, ("Sorceress Sellen",)),
    "patches": (None, ("Patches",)),
    "bernahl": (None, ("Knight Bernahl",)),
    "gostoc": ("Stormveil", ("Gatekeeper Gostoc",)),
    "rogier": (None, ("Sorcerer Rogier",)),
    "darian": (None, ("D, Hunter of the Dead",)),
    "corhyn": (None, ("Brother Corhyn", "Scribe Corhyn")),
    "twin-maiden-husks": ("Roundtable Hold", ("Twin Maiden Husks",)),
    "enia": ("Roundtable Hold", ("Finger Reader Enia",)),
    "thops": ("Liurnia", ("Sorcerer Thops",)),
    "blackguard": (None, ("Blackguard Big Boggart",)),
    "iji": ("Liurnia", ("Smithing Master Iji",)),
    "seluvis": ("Liurnia", ("Preceptor Seluvis",)),
    "pidia": ("Liurnia", ("Pidia",)),
    "miriel": ("Liurnia", ("Miriel",)),
    "gowry": ("Caelid", ("Sage Gowry",)),
    "dragon-communion": (None, ("Dragon Communion",)),
    "nomadic-west-limgrave": ("Limgrave", ("Nomadic Merchant",)),
    "nomadic-east-limgrave": ("Limgrave", ("Nomadic Merchant",)),
    "nomadic-north-limgrave": ("Limgrave", ("Nomadic Merchant",)),
    "nomadic-weeping-peninsula": ("Weeping", ("Nomadic Merchant",)),
    "isolated-weeping-peninsula": ("Weeping", ("Isolated Merchant",)),
    "nomadic-south-liurnia": ("Liurnia", ("Nomadic Merchant",)),
    "nomadic-north-liurnia": ("Liurnia", ("Nomadic Merchant",)),
    "isolated-raya-lucaria": ("Raya Lucaria Academy", ("Isolated Merchant",)),
    "nomadic-north-caelid": ("Caelid", ("Nomadic Merchant",)),
    "nomadic-south-caelid": ("Caelid", ("Nomadic Merchant",)),
    "isolated-dragonbarrow": ("Caelid", ("Isolated Merchant",)),
    "nomadic-altus-plateau": ("Altus", ("Nomadic Merchant",)),
    "nomadic-mt-gelmir": ("Mt. Gelmir", ("Nomadic Merchant",)),
    "hermit-capital-outskirts": ("Altus", ("Hermit Merchant",)),
    "hermit-mountaintops": ("Mountaintops of the Giants", ("Hermit Merchant",)),
    "hermit-ainsel-river": ("Ainsel River", ("Hermit Merchant",)),
    "abandoned-merchant": ("Siofra River", ("Abandoned Merchant",)),
    "imprisoned-merchant": ("Mohgwyn", ("Imprisoned Merchant",)),
    # Moore's generated AP checks intentionally use the hub/defaulted fallback, so his immutable
    # merchant identity, not that fallback region, is the narrowing evidence.
    "moore": (None, ("Moore",)),
    "thiollier": (None, ("Thiollier",)),
    "ymir": ("Scadu Altus", ("Count Ymir",)),
}


def build(sheets: Path):
    base = load_builder()
    base.verify_snapshot(sheets)
    index: dict[str, list[tuple[str, int, str, int]]] = {}
    for region, locations in base.load_locations().items():
        for location, ap_id, flag in locations:
            index.setdefault(base.norm(base.ap_item_name(location)), []).append(
                (region, ap_id, location, flag)
            )

    shop_data = load_repo_module("_redmaw_shop_data", ROOT / "greenfield/eldenring/shop_data.py")
    physical_merchants: dict[int, list[str]] = {}
    with MERCHANT_SHOPS.open(encoding="utf-8", newline="") as handle:
        rows = (line for line in handle if not line.startswith("#"))
        for row in csv.DictReader(rows, delimiter="\t"):
            if row["merchant_name"]:
                physical_merchants.setdefault(int(row["row_id"]), []).append(row["merchant_name"])

    parser = base.ChecklistParser()
    parser.feed((sheets / "merchants.html").read_text(encoding="utf-8"))
    with WIKIGG_REVISIONS.open(encoding="utf-8", newline="") as handle:
        wiki_revisions = {row["redmaw_url"]: row for row in csv.DictReader(handle, delimiter="\t")}
    provisional = []
    ambiguous = matched = refused = 0
    by_section: dict[str, dict[str, int]] = {}
    for checkbox_id, section_id, wiki_url, raw_label in parser.rows:
        label = raw_label.removesuffix(":").strip()
        candidates = index.get(base.norm(label), ())
        if len(candidates) <= 1:
            continue
        ambiguous += 1
        section = by_section.setdefault(
            section_id, {"ambiguous": 0, "matched": 0, "duplicate": 0, "refused": 0}
        )
        section["ambiguous"] += 1
        region, merchant_names = MERCHANT_CONTEXT.get(section_id, (None, ()))
        def physical_names(candidate):
            row_ids = shop_data.SHOP_ROW_IDS.get(str(candidate[1]), ())
            return [name for row_id in row_ids for name in physical_merchants.get(row_id, ())]

        def context_matches(candidate):
            names = [candidate[2], *physical_names(candidate)]
            return any(expected.casefold() in actual.casefold()
                       for expected in merchant_names for actual in names)

        matches = [candidate for candidate in candidates
                   if (region is None or candidate[0] == region) and context_matches(candidate)]
        if len(matches) != 1:
            refused += 1
            section["refused"] += 1
            continue
        ap_region, ap_id, _location, ap_flag = matches[0]
        wiki_revision = wiki_revisions[wiki_url]
        matched += 1
        section["matched"] += 1
        shop_row_ids = sorted(shop_data.SHOP_ROW_IDS.get(str(ap_id), ()))
        provisional.append({
            "lead_id": f"redmaw-merchant-{section_id}-{checkbox_id}-check-{ap_id}",
            "subject_kind": "check",
            "subject_id": str(ap_id),
            "claim_kind": "identity",
            "normalized_value": json.dumps(
                {"ap_flag": ap_flag, "item_name": label, "merchant_anchor": section_id,
                 "shop_row_ids": shop_row_ids, "wiki_url": wiki_url},
                ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            ),
            "source_ids": base.SOURCE_ID,
            "independence_families": "gameplay-guide:redmaw",
            "disposition": "lead_only",
            "game_version": "unknown",
            "exact_citations": (
                f"redmaw-checklists:merchants.html#{section_id}/{checkbox_id};"
                f"wiki.gg:{wiki_revision['revision_url']}"
            ),
            "summary": f"Redmaw lists {label} under merchant section {section_id}; that context identifies current AP shop flag {ap_flag}.",
            "limitations": (
                f"The identity is narrowed by Redmaw's merchant anchor and AP's current flag, shop-row, and physical-merchant evidence ({ap_region}). "
                "It does not independently prove AP's region, v1.17 behavior, access logic, stock predicates, or shop availability."
            ),
        })
    subject_counts: dict[str, int] = {}
    for row in provisional:
        subject_counts[row["subject_id"]] = subject_counts.get(row["subject_id"], 0) + 1
    rows = []
    duplicate_labels = 0
    for row in provisional:
        if subject_counts[row["subject_id"]] != 1:
            duplicate_labels += 1
            anchor = json.loads(row["normalized_value"])["merchant_anchor"]
            by_section[anchor]["duplicate"] += 1
            continue
        rows.append(row)
    rows.sort(key=lambda row: row["lead_id"])
    return rows, {
        "ambiguous_merchant_labels": ambiguous,
        "matched_labels": matched,
        "duplicate_labels": duplicate_labels,
        "resolved_checks": len(rows),
        "refused_labels": refused + duplicate_labels,
        "by_section": by_section,
    }


def render(rows):
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sheets", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    rows, report = build(args.sheets)
    args.output.write_text(render(rows), encoding="utf-8")
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
