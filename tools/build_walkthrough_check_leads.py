#!/usr/bin/env python3
"""Bind Redmaw's pinned base and DLC walkthroughs to exact AP checks.

The source is Redmaw's base-game and DLC 100% walkthrough pair. Its HTML has stable section and step
ids and item links. We retain only those ids, link labels (game item names), and immutable commit
identity. A binding is emitted only when an exact item name identifies one AP check inside the
walkthrough section's declared AP region(s), optionally after one complete AP place suffix occurs
in the same step. Repeated stones/runes otherwise remain ambiguous; this tool does not turn route
order or fuzzy prose into a fact.

This is broad external *coverage*, not accepted access logic.  Rows are leads from one independent
walkthrough family and must not be promoted to proven/corroborated by this tool.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "greenfield" / "eldenring" / "data.py"
DEFAULT_OUT = ROOT / "greenfield" / "evidence" / "wiki-audit" / "walkthrough-check-leads.tsv"

REDMAW_SOURCE_ID = "wiki:redmaw:walkthroughs:7281cb6f"
REDMAW_COMMIT = "7281cb6f7f067e71856f12d5e7083b97ad081bb1"
REDMAW_HASHES = {
    "walkthrough.html": "186c282b5f1cd113e5d25bb6bc5305fad9e0042306cac05db1768dbaaaa8fd8c",
    "dlc-walkthrough.html": "4c453ba6143b1cdabc8b2d04f7448ff297aedb5eb490ec308771e33bef5277c7",
}

# Walkthrough sections are more precise than AP's intentionally coarse region buckets.  Multi-area
# sections name every possible bucket explicitly; no name-based guessing happens at emit time.
REDMAW_REGIONS = {
    "tutorial": ("Limgrave",),
    "first-steps": ("Limgrave",),
    "early-liurnia": ("Liurnia", "Caelid"),
    "west-limgrave": ("Limgrave",), "north-limgrave": ("Limgrave",),
    "weeping-peninsula": ("Weeping",), "castle-morne": ("Weeping",),
    "stormveil-castle": ("Stormveil",), "fringefolk": ("Limgrave",),
    "south-liurnia": ("Liurnia",), "west-liurnia": ("Liurnia",),
    "central-liurnia": ("Liurnia",), "east-liurnia": ("Liurnia",),
    "academy": ("Raya Lucaria Academy",), "caria-manor": ("Liurnia",),
    "precipice": ("Liurnia", "Altus"),
    "ainsel": ("Ainsel River",), "nokstella": ("Ainsel River",),
    "lake-of-rot": ("Ainsel River",), "siofra-river": ("Siofra River",),
    "nokron": ("Siofra River",), "caelid": ("Caelid",), "sellia": ("Caelid",),
    "redmane-castle": ("Caelid",), "dragonbarrow": ("Caelid",),
    "study-hall": ("Liurnia",), "deeproot-depths": ("Deeproot Depths",),
    "moonlight-altar": ("Liurnia",), "west-altus": ("Altus",),
    "shaded-castle": ("Altus",), "central-altus": ("Altus",),
    "east-altus": ("Altus",), "mt-gelmir": ("Mt. Gelmir",),
    "volcano-manor": ("Mt. Gelmir",), "capital-outskirts": ("Altus",),
    "leyndell": ("Leyndell",), "shunning-grounds": ("Sewer",),
    "forbidden-lands": ("Mountaintops of the Giants",),
    "west-mountaintops": ("Mountaintops of the Giants",),
    "castle-sol": ("Mountaintops of the Giants",),
    "east-mountaintops": ("Mountaintops of the Giants",),
    "snowfield": ("Consecrated Snowfield",),
    "mohgwyn-palace": ("Mohgwyn",), "haligtree": ("Haligtree",),
    "elphael": ("Haligtree",), "farum-azula": ("Farum Azula",),
    "ashen-leyndell": ("Ashen Capital",),
    "west-gravesite": ("Gravesite",), "east-gravesite": ("Gravesite",),
    "belurat": ("Gravesite",), "ellac-river": ("Gravesite",),
    "cerulean-coast": ("Cerulean",), "charos-grave": ("Cerulean",),
    "castle-ensis": ("Ensis",), "scadu-west": ("Scadu Altus",),
    "rauh-base": ("Rauh Base",), "scadu-east": ("Scadu Altus",),
    "fissure": ("Cerulean",), "shadow-keep": ("Shadow Keep",),
    "church-district": ("Shadow Keep",), "scaduview": ("Shadow Keep",),
    "recluses-river": ("Scadu Altus",), "abyssal-woods": ("Abyssal",),
    "midras-manse": ("Abyssal",), "jagged-peak": ("Jagged Peak",),
    "rauh-ruins": ("Ancient Ruins",), "enir-ilim": ("Enir Ilim",),
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


class WalkthroughParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.section = None
        self.step = None
        self.link = None
        self.link_text: list[str] = []
        self.step_text: list[str] = []
        self.step_row_start = 0
        self.rows: list[dict[str, str]] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h3" and attrs.get("id"):
            self.section = attrs["id"]
        elif tag == "input" and self.section and re.fullmatch(r"[wd]\d+-\d+", attrs.get("id", "")):
            self.step = attrs["id"]
            self.step_text = []
            self.step_row_start = len(self.rows)
        elif tag == "a" and self.step and attrs.get("href"):
            self.link = attrs["href"]
            self.link_text = []

    def handle_data(self, data):
        if self.step:
            self.step_text.append(data)
        if self.link is not None:
            self.link_text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.link is not None:
            label = " ".join("".join(self.link_text).split())
            if label:
                self.rows.append({"section": self.section or "", "step": self.step or "",
                                  "label": label, "url": self.link})
            self.link = None
            self.link_text = []
        elif tag == "li":
            text = " ".join("".join(self.step_text).split())
            for row in self.rows[self.step_row_start:]:
                row["step_text"] = text
            self.step = None
            self.step_text = []


def place_hint(location: str) -> str:
    """Return AP's explicit place suffix, never a guessed token subset."""
    item = location.split(" :: ", 1)[-1]
    match = re.search(r" - (?:near|around) (.*?)(?:, may be sweep-granted| \[f\d+\]$)", item)
    return norm(match.group(1)) if match else ""


def load_locations():
    spec = importlib.util.spec_from_file_location("_walkthrough_data", DATA)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod.LOCATIONS


def build(sheets: Path):
    locations = load_locations()
    index: dict[tuple[str, str], list[tuple[int, str]]] = {}
    for region, rows in locations.items():
        for location, ap_id, _flag in rows:
            index.setdefault((region, norm(ap_item_name(location))), []).append((ap_id, location))

    emitted = {}
    ambiguous = 0
    unmatched = 0
    links = 0
    for filename, expected_hash in REDMAW_HASHES.items():
        body = (sheets / filename).read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        if digest != expected_hash:
            raise ValueError(f"refusing unknown Redmaw {filename}: sha256 {digest}")
        parser = WalkthroughParser()
        parser.feed(body.decode("utf-8"))
        links += len(parser.rows)
        for link in parser.rows:
            regions = REDMAW_REGIONS.get(link["section"])
            if not regions:
                continue
            candidates = []
            for region in regions:
                candidates.extend((region, ap_id, name)
                                  for ap_id, name in index.get((region, norm(link["label"])), ()))
            if len(candidates) > 1:
                step_text = norm(link.get("step_text", ""))
                exact_context = [candidate for candidate in candidates
                                 if place_hint(candidate[2])
                                 and place_hint(candidate[2]) in step_text]
                # Repeated AP descriptions can share a place label. Context is accepted only when
                # the whole stored place suffix selects exactly one current check.
                if len(exact_context) == 1:
                    candidates = exact_context
            if len(candidates) != 1:
                ambiguous += bool(candidates)
                unmatched += not candidates
                continue
            region, ap_id, name = candidates[0]
            # One external source may mention the same unique item more than once. A check is one
            # row; keep the first stable step id rather than pretending repeats corroborate it.
            emitted.setdefault(ap_id, {
            "lead_id": f"redmaw-{link['step']}-check-{ap_id}",
            "subject_kind": "check", "subject_id": str(ap_id), "claim_kind": "identity_region",
            "normalized_value": json.dumps({"item_name": link["label"], "region": region},
                                           ensure_ascii=False, sort_keys=True,
                                           separators=(",", ":")),
            "source_ids": REDMAW_SOURCE_ID,
            "independence_families": "gameplay-guide:redmaw",
            "disposition": "lead_only", "game_version": "unknown",
            "exact_citations": f"redmaw:#{link['section']}:{link['step']}",
            "summary": f"The walkthrough records {link['label']} in its {link['section']} segment; "
                       f"that item name identifies one current AP check in {region}.",
            "limitations": "One independently authored walkthrough lead, matched by exact item name "
                           "inside a declared region bucket. It does not prove a v1.17 event "
                           "predicate, access requirement, absence of alternate acquisition, or "
                           "the accuracy of AP's descriptive location suffix.",
            })
    return sorted(emitted.values(), key=lambda row: row["lead_id"]), {
        "links": links, "matched_checks": len(emitted),
        "ambiguous_links": ambiguous, "unmatched_links": unmatched,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sheets", type=Path, help=f"sheets/ at immutable Redmaw commit {REDMAW_COMMIT}")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    try:
        rows, stats = build(args.sheets)
    except ValueError as error:
        raise SystemExit(str(error))
    fields = list(rows[0]) if rows else []
    from io import StringIO
    out = StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    rendered = out.getvalue()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(json.dumps(stats, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
