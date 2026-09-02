#!/usr/bin/env python3
"""Bind Redmaw's immutable completion checklists to globally unique AP checks.

The upstream repository has no reuse licence, so this tool does not copy checklist prose. It
retains only a sheet name, checkbox id, factual game-item label, immutable commit identity, and the
single current AP check identified by that label. Ambiguous item names are refused. These are
discovery leads from one source family, never accepted access or region logic.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from html.parser import HTMLParser
import importlib.util
from io import StringIO
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "greenfield" / "eldenring" / "data.py"
DEFAULT_OUT = ROOT / "greenfield" / "evidence" / "wiki-audit" / "redmaw-checklist-check-leads.tsv"
DEFAULT_REPORT = ROOT / "greenfield" / "evidence" / "wiki-audit" / "redmaw-checklist-coverage.json"

SOURCE_ID = "wiki:redmaw:checklists:7281cb6f"
COMMIT = "7281cb6f7f067e71856f12d5e7083b97ad081bb1"
MANIFEST_SHA256 = "047bae3a1974396120b4b8108590b630f2484b9f13b9beb8c7b1bf1156fc6ec2"
SHEET_HASHES = {
    "achievements.html": "b81b006e997bc6a042d5fa9c9540405387417c2f49c537f8b01482ef209cfc94",
    "armor.html": "e2d91df1cc88f94d8a78ea063f9387d983cdeaa51dbb04a6301973d60b063a14",
    "ashes.html": "2811f45fadbb9353c026c626e083fc991083ed6bde6a410e1350988481558b01",
    "key-items.html": "59d0b44bf043dc21c967a04e19410a90d083c0ef0abe0350c344f543f72f4194",
    "merchants.html": "b7e762dd3fc090a7bfdc0dba22f0de256422c110b597b088e194b651250ad2b0",
    "miscellaneous-items.html": "84930105d6ed80a5f55fbd84d2e7f2a24d43490e1f49245985bb88b996189d52",
    "new-game-plus.html": "4760b87f13393957e0b2a0ab48a27515cee9f9407fe575951ba6519c99b031a5",
    "npc-walkthrough.html": "15c04296f01e86c2a731a254dc8f66ec091a55182d3c69483167265d75b7aadd",
    "spells.html": "498392fcfda7835a7bfda11a20b759b0d9f88004bb2c8bb845d1fba375f83f7e",
    "talismans.html": "3ba843a576d89b92413cb02cd272fbe786d870083097623edd2419e4e7dcf0af",
    "weapons.html": "ccfbcdb5f8d8f1994739c795c7aa504134a780c2e53a2b2a297829fc7bc09e68",
}


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = text.casefold().replace("&", " and ")
    return " ".join(re.findall(r"[a-z0-9]+", text))


def ap_item_name(location: str) -> str:
    value = location.split(" :: ", 1)[-1]
    value = re.sub(r"\s*\[f\d+\]\s*$", "", value)
    value = value.split(", may be sweep-granted", 1)[0]
    value = value.split(" - ", 1)[0]
    value = re.sub(r"^\[(?:Incantation|Sorcery)\]\s*", "", value)
    return value.strip()


class ChecklistParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_label = False
        self.checkbox_id = ""
        self.section_id = ""
        self.link_href = ""
        self.captured_link = False
        self.link_depth = 0
        self.link_text: list[str] = []
        self.rows: list[tuple[str, str, str, str]] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "label":
            self.in_label = True
            self.checkbox_id = ""
            self.captured_link = False
        elif self.in_label and tag == "input" and attrs.get("type") == "checkbox":
            self.checkbox_id = attrs.get("id", "")
        elif tag in {"h2", "h3", "h4"} and attrs.get("id"):
            self.section_id = attrs["id"]
        elif self.in_label and self.checkbox_id and not self.captured_link and tag == "a":
            self.link_depth = 1
            self.link_text = []
            self.link_href = attrs.get("href", "")
        elif self.link_depth:
            self.link_depth += 1

    def handle_data(self, data):
        if self.link_depth:
            self.link_text.append(data)

    def handle_endtag(self, tag):
        if self.link_depth:
            self.link_depth -= 1
            if self.link_depth == 0:
                label = " ".join("".join(self.link_text).split())
                if label and self.checkbox_id:
                    self.rows.append((self.checkbox_id, self.section_id, self.link_href, label))
                    self.captured_link = True
                self.link_text = []
                self.link_href = ""
        if tag == "label":
            self.in_label = False
            self.checkbox_id = ""


def load_locations():
    spec = importlib.util.spec_from_file_location("_redmaw_checklist_data", DATA)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module.LOCATIONS


def verify_snapshot(sheets: Path) -> None:
    actual = {path.name for path in sheets.glob("*.html") if path.name in SHEET_HASHES}
    if actual != set(SHEET_HASHES):
        raise ValueError(f"checklist snapshot files differ: expected={sorted(SHEET_HASHES)} actual={sorted(actual)}")
    for name, expected in SHEET_HASHES.items():
        digest = hashlib.sha256((sheets / name).read_bytes()).hexdigest()
        if digest != expected:
            raise ValueError(f"refusing unknown Redmaw sheet {name}: sha256 {digest}")
    manifest = "".join(f"{digest}  sheets/{name}\n" for name, digest in sorted(SHEET_HASHES.items()))
    if hashlib.sha256(manifest.encode()).hexdigest() != MANIFEST_SHA256:
        raise AssertionError("pinned Redmaw sheet manifest does not match the source registry")


def build(sheets: Path):
    verify_snapshot(sheets)
    index: dict[str, list[tuple[str, int, str]]] = {}
    for region, locations in load_locations().items():
        for location, ap_id, _flag in locations:
            index.setdefault(norm(ap_item_name(location)), []).append((region, ap_id, location))

    emitted: dict[int, dict[str, str]] = {}
    labels = exact = ambiguous = unmatched = 0
    by_sheet: dict[str, dict[str, int]] = {}
    for name in sorted(SHEET_HASHES):
        parser = ChecklistParser()
        parser.feed((sheets / name).read_text(encoding="utf-8"))
        sheet = name.removesuffix(".html")
        sheet_stats = {"labels": 0, "exact": 0, "ambiguous": 0, "unmatched": 0}
        for checkbox_id, section_id, wiki_url, label in parser.rows:
            labels += 1
            sheet_stats["labels"] += 1
            candidates = index.get(norm(label), ())
            if len(candidates) != 1:
                ambiguous += bool(candidates)
                unmatched += not candidates
                sheet_stats["ambiguous" if candidates else "unmatched"] += 1
                continue
            region, ap_id, _location = candidates[0]
            exact += 1
            sheet_stats["exact"] += 1
            anchor = f"{section_id}/{checkbox_id}" if section_id else checkbox_id
            emitted.setdefault(ap_id, {
                "lead_id": f"redmaw-checklist-{sheet}-{checkbox_id}-check-{ap_id}",
                "subject_kind": "check", "subject_id": str(ap_id), "claim_kind": "identity",
                "normalized_value": json.dumps({"item_name": label, "wiki_url": wiki_url}, ensure_ascii=False,
                                               sort_keys=True, separators=(",", ":")),
                "source_ids": SOURCE_ID,
                "independence_families": "gameplay-guide:redmaw",
                "disposition": "lead_only", "game_version": "unknown",
                "exact_citations": f"redmaw-checklists:{name}#{anchor};wiki.gg:{wiki_url}",
                "summary": f"Redmaw lists {label}; that exact game-item name identifies one current AP check.",
                "limitations": "One unlicensed community checklist family, retaining only a factual game-item label and immutable anchor. It does not prove region, v1.17 behavior, access logic, event predicates, route order, or absence of alternate acquisition.",
            })
        by_sheet[name] = sheet_stats
    return sorted(emitted.values(), key=lambda row: row["lead_id"]), {
        "labels": labels, "exact_labels": exact, "matched_checks": len(emitted),
        "duplicate_exact_labels": exact - len(emitted),
        "ambiguous_labels": ambiguous, "unmatched_labels": unmatched,
        "by_sheet": by_sheet,
    }


def render(rows: list[dict[str, str]]) -> str:
    fields = list(rows[0]) if rows else []
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sheets", type=Path, help=f"sheets/ at immutable Redmaw commit {COMMIT}")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    try:
        rows, stats = build(args.sheets)
    except ValueError as error:
        raise SystemExit(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(rows), encoding="utf-8")
    args.report.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(stats, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
