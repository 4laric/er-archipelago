#!/usr/bin/env python3
"""Preserve whole-guide matching candidates without promoting evidence.

Capture retains link labels/targets and stable step ids, never walkthrough prose.
Matching is a review aid: even a unique suggestion is NOT an identity/region lead.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re

import build_walkthrough_check_leads as walkthrough
from build_redmaw_location_anchor_leads import REGIONS as ANCHOR_REGIONS

# Both established importers carry section mappings. Preserve their union when
# they disagree; never choose the smaller bucket to manufacture a unique match.
REGIONS = {key: tuple(sorted(set(ANCHOR_REGIONS.get(key, ()))
                            | set(walkthrough.REDMAW_REGIONS.get(key, ()))))
           for key in ANCHOR_REGIONS.keys() | walkthrough.REDMAW_REGIONS.keys()}

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield/evidence/wiki-audit"
SNAPSHOT = AUDIT / "walkthrough-review-observations.json"
OUT = AUDIT / "bulk-check-review.json"
REPORT = AUDIT / "bulk-check-review-summary.json"
FAMILY = "gameplay-guide:redmaw"


def render(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def capture(sheets: Path) -> dict:
    """Verify the already registered immutable pair before extracting link facts."""
    steps = {}
    for filename, expected in sorted(walkthrough.REDMAW_HASHES.items()):
        body = (sheets / filename).read_bytes()
        if hashlib.sha256(body).hexdigest() != expected:
            raise ValueError(f"unregistered walkthrough snapshot: {filename}")
        parser = walkthrough.WalkthroughParser()
        parser.feed(body.decode("utf-8"))
        for link in parser.rows:
            key = (filename, link["section"], link["step"])
            steps.setdefault(key, set()).add((link["label"], link["url"]))
    return {
        "schema_version": 1, "source_id": walkthrough.REDMAW_SOURCE_ID,
        "revision": walkthrough.REDMAW_COMMIT,
        "body_hashes": walkthrough.REDMAW_HASHES,
        "steps": [
            {"file": f, "section": section, "step": step,
             "links": [{"label": label, "url": url} for label, url in sorted(links)]}
            for (f, section, step), links in sorted(steps.items())
        ],
    }


def anchor(name: str) -> str:
    """An ordinal, map id or fallback region is not a source-visible landmark."""
    tail = name.split(" - ", 1)[1] if " - " in name else ""
    tail = tail.split(", may be sweep-granted", 1)[0]
    tail = re.sub(r"\s*\[f\d+\]\s*$", "", tail)
    tail = re.sub(r"\s*\(\d+\)\s*$", "", tail)
    tail = tail.replace("(region unconfirmed)", "").strip()
    tail = re.sub(r"^(?:near|around|treasure ·)\s+", "", tail)
    if re.fullmatch(r"m\d\d(?:_\d\d){1,3}", tail):
        return ""
    return walkthrough.norm(tail)


def match_observation(observation: dict, candidates: list[dict]) -> dict:
    """Return all candidates plus narrowing reasons, never a forced best match."""
    candidates = sorted(candidates, key=lambda c: c["check_id"])
    regions = set(observation["regions"])
    regional = [c for c in candidates if c["region"] in regions]
    context = {walkthrough.norm(s) for s in observation["context_labels"]}
    local = [c for c in regional if c["anchor"] and c["anchor"] in context]
    # Preserve candidates when a guide's region taxonomy does not match ours.
    pool = local or regional or candidates
    if not regions:
        reason = "source_area_unmapped"
    elif not regional:
        reason = "region_disagreement"
    elif local:
        reason = "one_landmark_candidate" if len(local) == 1 else "shared_landmark"
    else:
        reason = "area_only"
    return {
        **observation, "candidate_ids": [c["check_id"] for c in pool],
        "all_candidate_ids": [c["check_id"] for c in candidates],
        "reason": reason, "status": "needs_review",
        "matched_on": ["item_name"] + (["guide_area"] if regional else [])
                      + (["linked_landmark"] if local else []),
        "missing_evidence": (
            ["exact_acquisition", "quantity_or_position"]
            if reason == "one_landmark_candidate"
            else ["exact_landmark", "exact_acquisition", "quantity_or_position"]
        ),
    }


def build(snapshot: dict | None = None) -> tuple[dict, dict]:
    snapshot = snapshot if snapshot is not None else json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    if (snapshot["source_id"] != walkthrough.REDMAW_SOURCE_ID
            or snapshot["revision"] != walkthrough.REDMAW_COMMIT
            or snapshot["body_hashes"] != walkthrough.REDMAW_HASHES):
        raise ValueError("bulk review snapshot is not the registered walkthrough revision")
    index = defaultdict(list)
    for region, rows in walkthrough.load_locations().items():
        for name, ap_id, flag in rows:
            index[walkthrough.norm(walkthrough.ap_item_name(name))].append({
                "check_id": ap_id, "flag": flag, "region": region, "name": name,
                "anchor": anchor(name)})
    confidence = {}
    with (ROOT / "greenfield/evidence/v060-current/progression_host_confidence.tsv").open(
            encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            confidence[int(row["check_id"])] = row
    existing = set()
    for path in sorted(AUDIT.glob("*-check-leads.tsv")):
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                if (row["subject_kind"] == "check" and row["claim_kind"] == "identity_region"
                        and FAMILY in row["independence_families"].split(";")):
                    existing.add(int(row["subject_id"]))
    results = []
    seen = set()
    item_mentions = 0
    for step in snapshot["steps"]:
        labels = sorted({link["label"] for link in step["links"]})
        for item in sorted({walkthrough.norm(label) for label in labels} & index.keys()):
            item_mentions += 1
            key = (step["file"], step["step"], item)
            if key in seen:
                raise ValueError(f"duplicate source observation: {key}")
            seen.add(key)
            oid = "walkthrough:" + hashlib.sha256("|".join(key).encode()).hexdigest()[:20]
            observation = {
                "observation_id": oid, "source_id": snapshot["source_id"], "family": FAMILY,
                "revision": snapshot["revision"], "game_version": "unknown",
                "item_name": next(label for label in labels if walkthrough.norm(label) == item),
                "file": step["file"], "section": step["section"], "step": step["step"],
                "regions": list(REGIONS.get(step["section"], ())),
                "context_labels": labels,
                "source_url": "https://github.com/rdmaw/elden-ring-completion-sheets/blob/"
                              + snapshot["revision"] + "/sheets/" + step["file"],
                "guide_url": "https://eldenring.redmaw.dev/sheets/"
                             + step["file"].removesuffix(".html") + "#" + step["step"],
            }
            result = match_observation(observation, index[item])
            # Already-covered candidates are retained as alternatives. Otherwise an existing
            # match would be subtracted to manufacture a unique match for its neighbour.
            held = [ap for ap in result["candidate_ids"] if confidence[ap]["confidence"] == "hold"]
            missing = [ap for ap in held if ap not in existing]
            if not missing:
                continue
            result["new_family_candidate_ids"] = missing
            result["second_family_candidate_ids"] = [
                ap for ap in missing if confidence[ap]["external_family_count"] == "1"]
            results.append(result)
    by_candidate = Counter(ap for row in results for ap in row["candidate_ids"])
    for row in results:
        row["competing_observation_count"] = max(by_candidate[ap] for ap in row["candidate_ids"])
    results.sort(key=lambda r: (not bool(r["second_family_candidate_ids"]),
                                r["reason"] != "one_landmark_candidate", len(r["candidate_ids"]),
                                r["file"], r["section"], r["step"], r["observation_id"]))
    checks = {ap for row in results for ap in row["new_family_candidate_ids"]}
    summary = {
        "schema_version": 1, "source_steps": len(snapshot["steps"]),
        "item_mentions": item_mentions, "review_observations": len(results),
        "held_checks_with_new_family_candidates": len(checks),
        "one_source_checks_with_second_family_candidates": len({
            ap for row in results for ap in row["second_family_candidate_ids"]}),
        "by_reason": dict(sorted(Counter(row["reason"] for row in results).items())),
        "trusted_promotions": 0,
        "limitations": "Suggestions only. Linked items can be mentions, not acquisitions. "
                       "Guide area and catalog anchors are not independent proof of AP ownership. "
                       "No quantity, position, mechanism or access is inferred.",
    }
    return {"schema_version": 1, "observations": results, "summary": summary}, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, help="extract link facts from pinned Redmaw sheets")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.capture:
        if args.check:
            parser.error("--capture cannot be used with --check")
        SNAPSHOT.write_text(render(capture(args.capture)), encoding="utf-8")
    data, summary = build()
    for path, value in ((OUT, data), (REPORT, summary)):
        text = render(value)
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                raise SystemExit(f"STALE: {path}")
        else:
            path.write_text(text, encoding="utf-8")
    print(render(summary), end="")


if __name__ == "__main__":
    main()
