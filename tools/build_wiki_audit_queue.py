#!/usr/bin/env python3
"""Build the deterministic #1273 external-reference investigation queue.

The queue is a discovery aid. It never upgrades wiki leads into accepted game truth,
and it only reports gaps explicitly recorded in queue-targets.tsv. Source silence is
therefore neither a contradiction nor evidence of absence.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
COVERAGE_VALUES = {"covered", "partial", "uncovered"}
GAP_KINDS = {
    "alternate_routes",
    "ap_override_scope",
    "check_binding",
    "check_partition",
    "coverage",
    "prerequisite_chain",
}


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _split(value: str) -> list[str]:
    return [part for part in value.split(",") if part]


def _check_ids(lead: dict[str, str]) -> list[str]:
    if lead["subject_kind"] == "check":
        return [lead["subject_id"]]
    value = json.loads(lead["normalized_value"])
    return [str(ap_id) for ap_id in value.get("ap_ids", [])]


def build(repo: Path) -> dict[str, Any]:
    root = repo / "greenfield" / "evidence" / "wiki-audit"
    leads = _read_tsv(root / "leads.tsv")
    targets = _read_tsv(root / "queue-targets.tsv")
    contradiction_rows = _read_tsv(root / "contradictions.tsv")
    dispositions = _read_tsv(
        repo / "greenfield" / "evidence" / "v060-current" / "access_dispositions.tsv")

    lead_by_id = {row["lead_id"]: row for row in leads}
    assert len(lead_by_id) == len(leads), "duplicate lead_id"
    known_checks = {row["check_id"] for row in dispositions}

    linked: list[dict[str, Any]] = []
    unbound: list[dict[str, str]] = []
    for lead in sorted(leads, key=lambda row: row["lead_id"]):
        assert lead["disposition"] == "lead_only", lead["lead_id"]
        check_ids = _check_ids(lead)
        if check_ids:
            assert set(check_ids) <= known_checks, f"unknown AP check in {lead['lead_id']}"
            linked.append({
                "lead_id": lead["lead_id"],
                "check_ids": sorted(check_ids, key=int),
                "claim_kind": lead["claim_kind"],
                "game_version": lead["game_version"],
                "disposition": "lead_only",
            })
        else:
            unbound.append({
                "lead_id": lead["lead_id"],
                "subject_kind": lead["subject_kind"],
                "subject_id": lead["subject_id"],
                "claim_kind": lead["claim_kind"],
                "game_version": lead["game_version"],
                "disposition": "lead_only",
            })

    target_ids: set[str] = set()
    normalized_targets: list[dict[str, Any]] = []
    for row in targets:
        target_id = row["target_id"]
        assert target_id not in target_ids, f"duplicate target_id: {target_id}"
        target_ids.add(target_id)
        assert row["priority"] in PRIORITY_ORDER, target_id
        assert row["coverage"] in COVERAGE_VALUES, target_id
        assert row["gap_kind"] in GAP_KINDS, target_id
        lead_ids = _split(row["lead_ids"])
        check_ids = _split(row["expected_check_ids"])
        assert set(lead_ids) <= set(lead_by_id), f"unknown lead in {target_id}"
        assert set(check_ids) <= known_checks, f"unknown check in {target_id}"
        if row["coverage"] == "uncovered":
            assert not lead_ids, f"uncovered target {target_id} has leads"
        else:
            assert lead_ids, f"{row['coverage']} target {target_id} needs leads"
        assert row["gap_summary"] and row["next_evidence"], target_id
        normalized_targets.append({
            "target_id": target_id,
            "priority": row["priority"],
            "regression_class": row["regression_class"],
            "coverage": row["coverage"],
            "lead_ids": sorted(lead_ids),
            "expected_check_ids": sorted(check_ids, key=int),
            "gap": {
                "kind": row["gap_kind"],
                "summary": row["gap_summary"],
                "next_evidence": row["next_evidence"],
            },
        })

    normalized_targets.sort(
        key=lambda row: (PRIORITY_ORDER[row["priority"]], row["target_id"]))
    gaps = [
        {"target_id": row["target_id"], "priority": row["priority"], **row["gap"]}
        for row in normalized_targets
    ]
    uncovered = [
        row["target_id"] for row in normalized_targets if row["coverage"] == "uncovered"
    ]

    contradictions: list[dict[str, Any]] = []
    finding_ids: set[str] = set()
    for row in contradiction_rows:
        finding_id = row["finding_id"]
        assert finding_id not in finding_ids, f"duplicate finding_id: {finding_id}"
        finding_ids.add(finding_id)
        assert row["priority"] in PRIORITY_ORDER, finding_id
        lead_ids = _split(row["lead_ids"])
        assert len(lead_ids) >= 2, f"contradiction {finding_id} needs at least two leads"
        assert set(lead_ids) <= set(lead_by_id), f"unknown lead in {finding_id}"
        values = {lead_by_id[lead_id]["normalized_value"] for lead_id in lead_ids}
        assert len(values) >= 2, f"contradiction {finding_id} has identical values"
        assert row["summary"] and row["next_evidence"], finding_id
        contradictions.append({
            "finding_id": finding_id,
            "priority": row["priority"],
            "lead_ids": sorted(lead_ids),
            "summary": row["summary"],
            "next_evidence": row["next_evidence"],
        })
    contradictions.sort(
        key=lambda row: (PRIORITY_ORDER[row["priority"]], row["finding_id"]))
    counts = Counter(row["coverage"] for row in normalized_targets)
    return {
        "schema_version": 1,
        "policy": {
            "external_disposition": "lead_only",
            "silence_is_evidence": False,
            "contradictions_require_explicit_record": True,
        },
        "counts": {
            "leads": len(leads),
            "exact_check_linked_leads": len(linked),
            "unbound_leads": len(unbound),
            "targets": len(normalized_targets),
            "covered_targets": counts["covered"],
            "partial_targets": counts["partial"],
            "uncovered_targets": counts["uncovered"],
            "contradictions": len(contradictions),
            "gaps": len(gaps),
        },
        "exact_check_linked_leads": linked,
        "unbound_leads": unbound,
        "uncovered_high_risk_targets": uncovered,
        "contradictions": contradictions,
        "gaps": gaps,
        "targets": normalized_targets,
    }


def render(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parent.parent
    output = args.output or (
        repo / "greenfield" / "evidence" / "wiki-audit" / "queue.json")
    rendered = render(build(repo))
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != rendered:
            raise SystemExit(f"wiki audit queue drift: run {Path(__file__).name}")
        print(f"wiki audit queue: OK -- {output.relative_to(repo)}")
        return 0
    output.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"wrote {output.relative_to(repo)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
