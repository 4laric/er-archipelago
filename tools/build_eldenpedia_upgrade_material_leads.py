#!/usr/bin/env python3
"""Bind repeated upgrade materials through pinned acquisition anchors and map-lot flags."""
from __future__ import annotations

import argparse
import csv
import importlib.util
from io import StringIO
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield/evidence/wiki-audit"
CLAIMS = ROOT / "greenfield/evidence/v060-current/claims.tsv"
LEADS = AUDIT / "eldenpedia-upgrade-material-check-leads.tsv"
MANIFEST = AUDIT / "eldenpedia-upgrade-material-pages.tsv"
REPORT = AUDIT / "eldenpedia-upgrade-material-coverage.json"
FIELDS = ("lead_id", "subject_kind", "subject_id", "claim_kind", "normalized_value",
          "source_ids", "independence_families", "disposition", "game_version",
          "exact_citations", "summary", "limitations")
MANIFEST_FIELDS = ("source_id", "page_id", "revision_id", "revision_timestamp",
                   "revision_sha1", "title", "canonical_url", "revision_url",
                   "acquisition_rows", "disposition")
MAP_LOT = "ItemLotParam_map.getItemFlagId"


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(result)
    return result


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def is_upgrade_material(value: str) -> bool:
    value = norm(value)
    return bool(re.fullmatch(
        r"(?:(?:somber )?(?:ancient dragon )?smithing stone(?: [1-9])?|"
        r"(?:great )?(?:grave|ghost) glovewort(?: [1-9])?|"
        r"scadutree fragment|revered spirit ash)", value))


def item_name(location: str) -> str:
    value = location.split(" :: ", 1)[1].split(" - ", 1)[0]
    return re.sub(r"^\[[^]]+\]\s*", "", value).replace("[", "").replace("]", "")


def anchor(location: str) -> str:
    if " - " not in location:
        return ""
    value = location.split(" - ", 1)[1]
    value = re.split(r", may be sweep| \[f", value)[0]
    value = re.sub(r"\s*\(region unconfirmed\)|\s*\(\d+\)$", "", value)
    value = re.sub(r"^(near|around|at|in|from|outside|behind|below|above)\s+", "", value,
                   flags=re.I)
    return norm(value)


def acquisition(content: str) -> str:
    match = re.search(r"(?ims)^==\s*Acquisition\s*==\s*(.*?)(?=^==[^=]|\Z)", content)
    return match.group(1) if match else ""


def render(rows: list[dict[str, str]], fields: tuple[str, ...]) -> str:
    out = StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def covered_subjects() -> set[int]:
    covered = set()
    for path in AUDIT.glob("*-check-leads.tsv"):
        if path == LEADS:
            continue
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                if row.get("subject_kind") == "check" and row.get("subject_id", "").isdigit():
                    covered.add(int(row["subject_id"]))
    return covered


def build(capture: dict) -> tuple[list[dict[str, str]], list[dict[str, str]], dict]:
    data = module("_upgrade_material_data", ROOT / "greenfield/eldenring/data.py")
    detections = {}
    with CLAIMS.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["claim_kind"] == "detection" and row["active"] == "true":
                value = json.loads(row["value"])
                if isinstance(value, dict):
                    detections[int(row["subject_id"])] = value
    checks = {}
    for region, entries in data.LOCATIONS.items():
        for location, ap_id, flag in entries:
            name = norm(item_name(location))
            if is_upgrade_material(name):
                checks.setdefault(name, []).append((ap_id, flag, region, location, anchor(location)))

    vague = {norm(region) for region in data.LOCATIONS} | {
        "altus plateau", "liurnia of the lakes", "weeping peninsula", "volcano manor",
        "consecrated snowfield", "crumbling farum azula", "realm of shadow", "lands between",
    }
    prior = covered_subjects()
    emitted, used = {}, {}
    stats = {
        "requested_titles": len(capture.get("requested_titles", [])),
        "resolved_pages": len(capture["pages"]),
        "missing_pages": len(capture.get("missing_titles", [])),
        "upgrade_pages": 0, "candidate_checks": sum(map(len, checks.values())),
        "refused_no_acquisition_section": 0, "refused_weak_anchor_or_detection": 0,
        "refused_anchor_absent": 0, "refused_ambiguous_anchor": 0,
        "already_covered_checks": 0, "new_union_checks": 0, "pinned_pages": 0,
    }
    accepted = {}
    for page in capture["pages"]:
        title = norm(page["title"])
        if not is_upgrade_material(title) or title not in checks:
            continue
        stats["upgrade_pages"] += 1
        revision = page["revisions"][0]
        text = acquisition(revision["slots"]["main"]["content"])
        if not text:
            stats["refused_no_acquisition_section"] += len(checks[title])
            continue
        normalized_text = norm(text)
        matches = []
        for candidate in checks[title]:
            ap_id, flag, _region, _location, phrase = candidate
            detection = detections.get(ap_id, {})
            if (phrase in vague or len(phrase) < 6 or len(phrase.split()) < 2 or
                    detection.get("flag") != flag or detection.get("mechanism") != MAP_LOT):
                stats["refused_weak_anchor_or_detection"] += 1
                continue
            if re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", normalized_text):
                matches.append(candidate)
            else:
                stats["refused_anchor_absent"] += 1
        phrase_counts = {phrase: sum(row[4] == phrase for row in matches)
                         for *_head, phrase in matches}
        for ap_id, flag, region, _location, phrase in matches:
            if phrase_counts[phrase] != 1:
                stats["refused_ambiguous_anchor"] += 1
                continue
            accepted[ap_id] = (page, revision, flag, region, phrase)

    stats["already_covered_checks"] = sum(ap_id in prior for ap_id in accepted)
    for ap_id, (page, revision, flag, region, phrase) in accepted.items():
        if ap_id in prior:
            continue
        page_id, revision_id = int(page["pageid"]), int(revision["revid"])
        source_id = f"wiki:eldenpedia:page-{page_id}:revision-{revision_id}"
        text = acquisition(revision["slots"]["main"]["content"])
        used[source_id] = {
            "source_id": source_id, "page_id": str(page_id), "revision_id": str(revision_id),
            "revision_timestamp": revision["timestamp"], "revision_sha1": revision["sha1"],
            "title": page["title"],
            "canonical_url": "https://eldenring.wiki.gg/wiki/" + page["title"].replace(" ", "_"),
            "revision_url": f"https://eldenring.wiki.gg/w/index.php?oldid={revision_id}",
            "acquisition_rows": str(sum(line.lstrip().startswith("*") for line in text.splitlines())),
            "disposition": "lead_only",
        }
        value = {"acquisition_anchor": phrase, "flag": flag, "item_name": page["title"],
                 "region": region}
        emitted[ap_id] = {
            "lead_id": f"eldenpedia-upgrade-page-{page_id}-revision-{revision_id}-check-{ap_id}",
            "subject_kind": "check", "subject_id": str(ap_id),
            "claim_kind": "identity_region",
            "normalized_value": json.dumps(value, ensure_ascii=False, sort_keys=True,
                                           separators=(",", ":")),
            "source_ids": source_id, "independence_families": "gameplay-wiki:eldenpedia",
            "disposition": "lead_only", "game_version": "unknown",
            "exact_citations": (f"eldenpedia:pageid-{page_id}:revision-{revision_id}:"
                                f"#Acquisition:{phrase};project:check:{ap_id}/detection;flag-{flag}"),
            "summary": (f"Eldenpedia revision {revision_id} places {page['title']} at {phrase}; "
                        f"that exact anchor selects one current AP map-lot flag ({flag}) in {region}."),
            "limitations": ("Community-wiki acquisition lead disambiguated by an exact multiword "
                            "anchor and matching v1.17 map-lot flag evidence. It does not prove "
                            "access, route order, coordinates, completeness, event timing, or "
                            "absence of another acquisition."),
        }
    rows = sorted(emitted.values(), key=lambda row: row["lead_id"])
    manifests = sorted(used.values(), key=lambda row: row["source_id"])
    stats["new_union_checks"] = len(rows)
    stats["pinned_pages"] = len(manifests)
    return rows, manifests, stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    rows, manifests, stats = build(json.loads(args.capture.read_text(encoding="utf-8")))
    LEADS.write_text(render(rows, FIELDS), encoding="utf-8")
    MANIFEST.write_text(render(manifests, MANIFEST_FIELDS), encoding="utf-8")
    REPORT.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(stats, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
