#!/usr/bin/env python3
"""Disambiguate repeated checks with pinned Eldenpedia Acquisition text and map-lot flags."""
from __future__ import annotations
import argparse, csv, importlib.util, json, re
from collections import Counter, defaultdict
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield/evidence/wiki-audit"
CLAIMS = ROOT / "greenfield/evidence/v060-current/claims.tsv"
LEADS = AUDIT / "eldenpedia-item-acquisition-check-leads.tsv"
MANIFEST = AUDIT / "eldenpedia-item-acquisition-pages.tsv"
REPORT = AUDIT / "eldenpedia-item-acquisition-coverage.json"
FIELDS = ("lead_id", "subject_kind", "subject_id", "claim_kind", "normalized_value",
          "source_ids", "independence_families", "disposition", "game_version",
          "exact_citations", "summary", "limitations")
MANIFEST_FIELDS = ("source_id", "page_id", "revision_id", "revision_timestamp",
                   "revision_sha1", "title", "canonical_url", "revision_url",
                   "acquisition_rows", "disposition")
MAP_LOT = "ItemLotParam_map.getItemFlagId"
UPGRADE_PREFIXES = ("smithing stone ", "somber smithing stone ",
                    "ancient dragon smithing stone", "somber ancient dragon smithing stone")

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path); result = importlib.util.module_from_spec(spec)
    assert spec.loader; spec.loader.exec_module(result); return result

def norm(value): return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

def item_name(location):
    value = location.split(" :: ", 1)[1].split(" - ", 1)[0]
    return re.sub(r"^\[[^]]+\]\s*", "", value).replace("[", "").replace("]", "")

def anchor(location):
    if " - " not in location: return ""
    value = location.split(" - ", 1)[1]
    value = re.split(r", may be sweep| \[f", value)[0]
    value = re.sub(r"\s*\(region unconfirmed\)|\s*\(\d+\)$", "", value)
    value = re.sub(r"^(near|around|at|in|from|outside|behind|below|above)\s+", "", value,
                   flags=re.I)
    return norm(value)

def acquisition(content):
    match = re.search(r"(?ims)^==\s*Acquisition\s*==\s*(.*?)(?=^==[^=]|\Z)", content)
    return match.group(1) if match else ""

def render(rows, fields):
    out = StringIO(newline=""); writer = csv.DictWriter(out, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader(); writer.writerows(rows); return out.getvalue()

def build(capture):
    data = module("_data", ROOT / "greenfield/eldenring/data.py")
    detections = {}
    with CLAIMS.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["claim_kind"] == "detection" and row["active"] == "true":
                value = json.loads(row["value"])
                if isinstance(value, dict): detections[int(row["subject_id"])] = value
    checks = defaultdict(list)
    vague = {norm(region) for region in data.LOCATIONS} | {
        "altus plateau", "liurnia of the lakes", "weeping peninsula", "volcano manor",
        "consecrated snowfield", "crumbling farum azula", "realm of shadow", "lands between",
    }
    for region, entries in data.LOCATIONS.items():
        for location, ap_id, flag in entries:
            checks[norm(item_name(location))].append((ap_id, flag, region, location, anchor(location)))
    emitted, used = {}, {}
    stats = Counter(requested_titles=len(capture.get("requested_titles", [])),
                    resolved_pages=len(capture["pages"]), missing_pages=len(capture.get("missing_titles", [])))
    for page in capture["pages"]:
        candidates = checks.get(norm(page["title"]), [])
        if not candidates: stats["refused_no_exact_item"] += 1; continue
        if norm(page["title"]).startswith(UPGRADE_PREFIXES):
            stats["refused_upgrade_material_lane"] += len(candidates); continue
        revision = page["revisions"][0]; text = acquisition(revision["slots"]["main"]["content"])
        if not text: stats["refused_no_acquisition_section"] += len(candidates); continue
        normalized_text = norm(text); matches = []
        for candidate in candidates:
            ap_id, flag, _region, _location, phrase = candidate
            detection = detections.get(ap_id, {})
            if (phrase in vague or len(phrase) < 6 or len(phrase.split()) < 2 or
                    detection.get("flag") != flag or detection.get("mechanism") != MAP_LOT):
                stats["refused_weak_anchor_or_detection"] += 1; continue
            if re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", normalized_text):
                matches.append(candidate)
            else: stats["refused_anchor_absent"] += 1
        counts = Counter(candidate[4] for candidate in matches)
        for ap_id, flag, region, _location, phrase in matches:
            if counts[phrase] != 1:
                stats["refused_ambiguous_anchor"] += 1; continue
            page_id, revision_id = int(page["pageid"]), int(revision["revid"])
            source_id = f"wiki:eldenpedia:page-{page_id}:revision-{revision_id}"
            used[source_id] = {
                "source_id": source_id, "page_id": str(page_id), "revision_id": str(revision_id),
                "revision_timestamp": revision["timestamp"], "revision_sha1": revision["sha1"],
                "title": page["title"], "canonical_url": "https://eldenring.wiki.gg/wiki/" + page["title"].replace(" ", "_"),
                "revision_url": f"https://eldenring.wiki.gg/w/index.php?oldid={revision_id}",
                "acquisition_rows": str(sum(1 for line in text.splitlines() if line.lstrip().startswith("*"))),
                "disposition": "lead_only",
            }
            value = {"acquisition_anchor": phrase, "flag": flag, "item_name": page["title"], "region": region}
            emitted[ap_id] = {
                "lead_id": f"eldenpedia-acquisition-page-{page_id}-revision-{revision_id}-check-{ap_id}",
                "subject_kind": "check", "subject_id": str(ap_id), "claim_kind": "identity_region",
                "normalized_value": json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                "source_ids": source_id, "independence_families": "gameplay-wiki:eldenpedia",
                "disposition": "lead_only", "game_version": "unknown",
                "exact_citations": f"eldenpedia:pageid-{page_id}:revision-{revision_id}:#Acquisition:{phrase};project:check:{ap_id}/detection;flag-{flag}",
                "summary": f"Eldenpedia revision {revision_id} places {page['title']} at {phrase}; that exact anchor selects one current AP map-lot flag ({flag}) in {region}.",
                "limitations": "Community-wiki acquisition lead disambiguated by an exact multiword anchor and matching v1.17 map-lot flag evidence. It does not prove access, route order, coordinates, completeness, event timing, or absence of another acquisition.",
            }
    rows = sorted(emitted.values(), key=lambda row: row["lead_id"])
    manifests = sorted(used.values(), key=lambda row: row["source_id"])
    stats["matched_checks"] = len(rows); stats["pinned_pages"] = len(manifests)
    return rows, manifests, dict(sorted(stats.items()))

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("capture", type=Path); args = parser.parse_args()
    rows, manifests, stats = build(json.loads(args.capture.read_text(encoding="utf-8")))
    LEADS.write_text(render(rows, FIELDS), encoding="utf-8"); MANIFEST.write_text(render(manifests, MANIFEST_FIELDS), encoding="utf-8")
    REPORT.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(stats, sort_keys=True)); return 0

if __name__ == "__main__": raise SystemExit(main())
