#!/usr/bin/env python3
"""Bind immutable PowerPyx regional walkthrough captures to current AP checks.

Only an exact item-name occurrence in one article block, and a name that identifies exactly one
check in the page's declared AP region, can emit a row.  The result is discovery evidence only:
regional walkthrough prose cannot establish an event predicate or an access requirement.
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
DEFAULT_OUT = ROOT / "greenfield" / "evidence" / "wiki-audit" / "powerpyx-check-leads.tsv"

CAPTURES = {
    "elden-ring-limgrave-walkthrough.html": {
        "source_id": "wiki:powerpyx:limgrave:20260519062715",
        "sha256": "565cafd649ec6e842a167eaf33935c4364d5d3a655ac883e992ca2e7795b9521",
        "region": "Limgrave",
    },
    "elden-ring-liurnia-of-the-lakes-walkthrough.html": {
        "source_id": "wiki:powerpyx:liurnia:20260612104900",
        "sha256": "54da515f275b1246ac5cc13fc72c4851b3450c8174cccb739f0fdb8e43cdbe45",
        "region": "Liurnia",
    },
    "elden-ring-academy-of-raya-lucaria-walkthrough.html": {
        "source_id": "wiki:powerpyx:academy:20260609174003",
        "sha256": "699859e6a28fb72220335c036a51282665e283c97936b89bb5c487b4317e06d1",
        "region": "Raya Lucaria Academy",
    },
}


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold().replace("&", " and ")))


def slug(text: str) -> str:
    return "-".join(re.findall(r"[a-z0-9]+", norm(text))) or "article"


def ap_item_name(location: str) -> str:
    value = location.split(" :: ", 1)[-1]
    value = re.sub(r"\s*\[f\d+\]\s*$", "", value)
    value = value.split(", may be sweep-granted", 1)[0]
    value = value.split(" - ", 1)[0]
    value = re.sub(r"^\[(?:Incantation|Sorcery)\]\s*", "", value)
    return value.strip()


class ArticleParser(HTMLParser):
    BLOCKS = {"p", "li", "h2", "h3", "h4"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.article_depth = 0
        self.block_tag: str | None = None
        self.text: list[str] = []
        self.heading = "article"
        self.blocks: list[tuple[str, int, str]] = []
        self.ordinal = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()
        if tag == "div" and "entry-content" in classes:
            self.article_depth = 1
            return
        if self.article_depth and tag == "div":
            self.article_depth += 1
        if self.article_depth and tag in self.BLOCKS and self.block_tag is None:
            self.block_tag = tag
            self.text = []

    def handle_data(self, data):
        if self.article_depth and self.block_tag:
            self.text.append(data)

    def handle_endtag(self, tag):
        if self.article_depth and tag == self.block_tag:
            text = " ".join("".join(self.text).split())
            if text:
                if self.block_tag.startswith("h"):
                    self.heading = slug(text)
                    self.ordinal = 0
                else:
                    self.ordinal += 1
                    self.blocks.append((self.heading, self.ordinal, text))
            self.block_tag = None
            self.text = []
        if self.article_depth and tag == "div":
            self.article_depth -= 1


def load_locations():
    spec = importlib.util.spec_from_file_location("_powerpyx_data", DATA)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod.LOCATIONS


def build(capture_dir: Path):
    locations = load_locations()
    emitted: dict[int, dict[str, str]] = {}
    stats = {"captures": 0, "blocks": 0, "matched_checks": 0, "ambiguous_mentions": 0}
    for filename, capture in CAPTURES.items():
        body = (capture_dir / filename).read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        if digest != capture["sha256"]:
            raise SystemExit(f"refusing unknown capture {filename}: sha256 {digest}")
        parser = ArticleParser()
        parser.feed(body.decode("utf-8"))
        stats["captures"] += 1
        stats["blocks"] += len(parser.blocks)
        region = capture["region"]
        by_name: dict[str, list[tuple[int, str]]] = {}
        for location, ap_id, _flag in locations[region]:
            name = ap_item_name(location)
            by_name.setdefault(norm(name), []).append((ap_id, name))
        for key, candidates in by_name.items():
            if len(candidates) != 1 or len(key) < 5:
                continue
            hits = [(heading, ordinal, text) for heading, ordinal, text in parser.blocks
                    if re.search(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])", norm(text))]
            if len(hits) != 1:
                stats["ambiguous_mentions"] += bool(hits)
                continue
            ap_id, name = candidates[0]
            heading, ordinal, text = hits[0]
            block_digest = hashlib.sha256(text.encode()).hexdigest()[:16]
            citation = f"powerpyx:#{heading}:block-{ordinal}:sha256-{block_digest}"
            emitted[ap_id] = {
                "lead_id": f"powerpyx-{slug(region)}-check-{ap_id}",
                "subject_kind": "check", "subject_id": str(ap_id),
                "claim_kind": "identity_region",
                "normalized_value": json.dumps({"item_name": name, "region": region},
                                               ensure_ascii=False, sort_keys=True,
                                               separators=(",", ":")),
                "source_ids": capture["source_id"],
                "independence_families": "gameplay-guide:powerpyx",
                "disposition": "lead_only", "game_version": "unknown",
                "exact_citations": citation,
                "summary": f"The regional walkthrough names {name}; that exact item name identifies one current AP check in {region}.",
                "limitations": "One independently authored regional walkthrough lead, bound by exact item name inside its declared AP region. It does not prove a v1.17 event predicate, access requirement, absence of alternate acquisition, route order, or the accuracy of AP's descriptive location suffix.",
            }
    rows = sorted(emitted.values(), key=lambda row: row["lead_id"])
    stats["matched_checks"] = len(rows)
    return rows, stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("capture_dir", type=Path)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    rows, stats = build(args.capture_dir)
    if not rows:
        raise SystemExit("no exact PowerPyx bindings")
    from io import StringIO
    out = StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    rendered = out.getvalue()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(json.dumps(stats, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
