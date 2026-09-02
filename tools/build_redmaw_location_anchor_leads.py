#!/usr/bin/env python3
"""Bind repeated walkthrough pickups using same-step named-location anchors and map-lot flags."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
import hashlib
from html.parser import HTMLParser
from io import StringIO
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield/evidence/wiki-audit"
CLAIMS = ROOT / "greenfield/evidence/v060-current/claims.tsv"
DEFAULT_OUT = AUDIT / "redmaw-location-anchor-check-leads.tsv"
DEFAULT_REPORT = AUDIT / "redmaw-location-anchor-coverage.json"
SOURCE_ID = "wiki:redmaw:walkthroughs:7281cb6f"
HASHES = {
    "dlc-walkthrough.html": "4c453ba6143b1cdabc8b2d04f7448ff297aedb5eb490ec308771e33bef5277c7",
    "walkthrough.html": "186c282b5f1cd113e5d25bb6bc5305fad9e0042306cac05db1768dbaaaa8fd8c",
}
MANIFEST_SHA256 = "a6da765f9abc673d7c10855fbbac0aa9e3d2406513f6727b8b61d8053584c6e0"
REGIONS = {
    "tutorial": ("Limgrave",), "first-steps": ("Limgrave",),
    "early-liurnia": ("Liurnia", "Caelid"), "west-limgrave": ("Limgrave",),
    "north-limgrave": ("Limgrave",), "weeping-peninsula": ("Weeping",),
    "castle-morne": ("Weeping",), "stormveil-castle": ("Stormveil",),
    "fringefolk": ("Limgrave",), "south-liurnia": ("Liurnia",),
    "west-liurnia": ("Liurnia",), "central-liurnia": ("Liurnia",),
    "east-liurnia": ("Liurnia",), "academy": ("Raya Lucaria Academy",),
    "caria-manor": ("Liurnia",), "ruin-strewn": ("Liurnia", "Altus"),
    "ainsel-river": ("Ainsel River",), "nokstella": ("Ainsel River",),
    "lake-of-rot": ("Ainsel River",), "siofra-river": ("Siofra River",),
    "nokron": ("Siofra River",), "caelid": ("Caelid",), "sellia": ("Caelid",),
    "redmane-castle": ("Caelid",), "dragonbarrow": ("Caelid",),
    "carian-study-hall": ("Liurnia",), "deeproot-depths": ("Deeproot Depths",),
    "moonlight-altar": ("Liurnia",), "west-altus": ("Altus",),
    "shaded-castle": ("Altus",), "central-altus": ("Altus",),
    "east-altus": ("Altus",), "mt-gelmir": ("Mt. Gelmir",),
    "volcano-manor": ("Mt. Gelmir",), "capital-outskirts": ("Altus",),
    "leyndell": ("Leyndell",), "shunning-grounds": ("Sewer",),
    "forbidden-lands": ("Mountaintops of the Giants",),
    "west-mountaintops": ("Mountaintops of the Giants",),
    "castle-sol": ("Mountaintops of the Giants",),
    "east-mountaintops": ("Mountaintops of the Giants",),
    "consecrated-snowfield": ("Consecrated Snowfield",), "mohgwyn-palace": ("Mohgwyn",),
    "miquellas-haligtree": ("Haligtree",), "elphael": ("Haligtree",),
    "farum-azula": ("Farum Azula",), "ashen-capital": ("Ashen Capital",),
    "west-gravesite": ("Gravesite",), "east-gravesite": ("Gravesite",),
    "belurat": ("Belurat",), "ellac-river": ("Cerulean",),
    "cerulean-coast": ("Cerulean",), "charos-grave": ("Cerulean",),
    "castle-ensis": ("Ensis",), "scadu-west": ("Scadu Altus",),
    "rauh-base": ("Rauh Base",), "scadu-east": ("Scadu Altus",),
    "fissure": ("Cerulean",), "shadow-keep": ("Shadow Keep",),
    "church-district": ("Shadow Keep",), "scaduview": ("Scaduview",),
    "recluses-river": ("Abyssal",), "abyssal-woods": ("Abyssal",),
    "midras-manse": ("Abyssal",), "jagged-peak": ("Jagged Peak",),
    "rauh-ruins": ("Ancient Ruins",), "enir-ilim": ("Enir Ilim",),
}


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.section = ""; self.step = ""; self.href = ""; self.text = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h3" and attrs.get("id"):
            self.section = attrs["id"]
        elif tag == "input" and re.fullmatch(r"[wd]\d+-\d+", attrs.get("id", "")):
            self.step = attrs["id"]
        elif tag == "a" and self.step and attrs.get("href"):
            self.href = attrs["href"]; self.text = []

    def handle_data(self, data):
        if self.href:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href:
            label = " ".join("".join(self.text).split())
            if label:
                self.links.append((self.section, self.step, self.href, label))
            self.href = ""; self.text = []
        elif tag == "li":
            self.step = ""


def verify(sheets: Path):
    for name, expected in HASHES.items():
        actual = hashlib.sha256((sheets / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"refusing unknown Redmaw {name}: sha256 {actual}")
    manifest = "".join(f"{digest}  sheets/{name}\n" for name, digest in sorted(HASHES.items()))
    if hashlib.sha256(manifest.encode()).hexdigest() != MANIFEST_SHA256:
        raise AssertionError("pinned walkthrough manifest does not match the source registry")


def build(sheets: Path):
    verify(sheets)
    base = load("_redmaw_walkthrough_base", ROOT / "tools/build_walkthrough_check_leads.py")
    repeated = load("_redmaw_detection", ROOT / "tools/build_eldenpedia_repeated_pickup_leads.py")
    index = defaultdict(list)
    for region, locations in base.load_locations().items():
        for location, ap_id, flag in locations:
            index[(region, base.norm(base.ap_item_name(location)))].append((ap_id, flag, location))
    detection = repeated.detection_claims()
    grouped = defaultdict(list)
    for name in sorted(HASHES):
        parser = Parser(); parser.feed((sheets / name).read_text(encoding="utf-8"))
        for section_name, step, url, label in parser.links:
            grouped[(name, section_name, step)].append((url, label))

    emitted = {}
    stats = defaultdict(int)
    for (sheet, section_name, step), links in grouped.items():
        anchors = [label for url, label in links if "mapgenie.io/elden-ring/" in url]
        if not anchors:
            continue
        stats["steps_with_named_location"] += 1
        for url, raw_label in links:
            if not url.startswith("https://eldenring.wiki.gg/wiki/"):
                continue
            label = re.sub(r"\s+x?\d+$", "", raw_label, flags=re.IGNORECASE).strip()
            candidates = [(region, *candidate) for region in REGIONS.get(section_name, ())
                          for candidate in index.get((region, base.norm(label)), ())]
            if len(candidates) <= 1:
                continue
            stats["repeated_item_links"] += 1
            matches = [candidate for candidate in candidates if any(
                re.search(rf"(?<![a-z0-9]){re.escape(base.norm(anchor))}(?![a-z0-9])",
                          base.norm(candidate[3])) for anchor in anchors
            )]
            if len(matches) != 1:
                stats["refused_location_match"] += 1
                continue
            region, ap_id, flag, _location = matches[0]
            claim = detection.get(ap_id)
            if not claim or claim[:2] != (flag, repeated.MAP_LOT):
                stats["refused_non_map_lot"] += 1
                continue
            if ap_id in emitted:
                stats["refused_duplicate_check"] += 1
                emitted.pop(ap_id, None)
                continue
            source_anchor = anchors[0]
            emitted[ap_id] = {
                "lead_id": f"redmaw-location-{sheet.removesuffix('.html')}-{step}-check-{ap_id}",
                "subject_kind": "check", "subject_id": str(ap_id),
                "claim_kind": "identity_region",
                "normalized_value": json.dumps(
                    {"flag": flag, "item_name": label, "location_anchor": source_anchor,
                     "region": region, "wiki_url": url}, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":")),
                "source_ids": SOURCE_ID,
                "independence_families": "gameplay-guide:redmaw",
                "disposition": "lead_only", "game_version": "unknown",
                "exact_citations": (f"redmaw:{sheet}#{section_name}/{step}:"
                                    f"location-{source_anchor};project:{claim[2]};flag-{flag}"),
                "summary": (f"Redmaw step {step} links {label} and {source_anchor}; that exact "
                            f"same-step anchor selects one repeated {region} map-lot check at flag {flag}."),
                "limitations": ("One unlicensed walkthrough family, retaining only factual link labels "
                                "and immutable anchors. The v1.17 flag mechanism is project evidence. "
                                "This does not prove access, route order, coordinates, completeness, "
                                "event timing, or absence of another acquisition."),
            }
    rows = sorted(emitted.values(), key=lambda row: row["lead_id"])
    stats["matched_checks"] = len(rows)
    return rows, dict(sorted(stats.items()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sheets", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    rows, stats = build(args.sheets)
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    args.output.write_text(output.getvalue(), encoding="utf-8")
    args.report.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(stats, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
