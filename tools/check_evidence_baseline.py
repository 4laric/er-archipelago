#!/usr/bin/env python3
"""Validate and compare v0.6 evidence-ledger summary manifests.

This is deliberately narrower than the ledger validator.  The ledger owns whether individual
sources, evidence and claims are well-formed; this tool owns the reviewed aggregate baseline that
lets CI say whether the audit population changed.  Keeping those jobs separate means a new adapter
cannot make its own smaller output look valid by quietly redefining the expected totals.

The initial gate is exact drift, not a confidence score.  An improvement is expected to change the
manifest, fail ``--check``, and be re-baselined in the same reviewed commit with ``--update``.
Later no-regression policy can compare claim-level manifests without changing this file format.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Mapping


SCHEMA_VERSION = 1
STATUSES = (
    "proven",
    "corroborated",
    "single_source",
    "conflicted",
    "inferred",
    "unverified",
)
RISKS = ("critical", "high", "medium", "low")
REQUIRED = (
    "schema_version",
    "claims_total",
    "by_status",
    "by_kind",
    "by_risk",
    "active_conflicts",
    "content_hash",
)


class BaselineError(ValueError):
    """The summary is malformed or internally inconsistent."""


def _canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


def summary_hash(claim_payload: object) -> str:
    """Return the ledger-owned content hash algorithm for canonical active records."""

    return hashlib.sha256(_canonical_bytes(claim_payload)).hexdigest()


def _non_negative_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BaselineError(f"{field} must be a non-negative integer, got {value!r}")
    return value


def _status_counts(value: object, field: str) -> dict[str, int]:
    if not isinstance(value, Mapping):
        raise BaselineError(f"{field} must be an object")
    unknown = sorted(set(value) - set(STATUSES))
    missing = sorted(set(STATUSES) - set(value))
    if unknown or missing:
        raise BaselineError(f"{field} status keys differ: missing={missing}, unknown={unknown}")
    return {status: _non_negative_int(value[status], f"{field}.{status}") for status in STATUSES}


def validate_summary(raw: object) -> dict[str, object]:
    """Validate and normalize one aggregate summary.

    Exact status keys are required even when a count is zero.  Omitting an empty state would make
    independently produced summaries serialize differently and would hide vocabulary drift.
    """

    if not isinstance(raw, Mapping):
        raise BaselineError("summary root must be an object")
    missing = sorted(set(REQUIRED) - set(raw))
    unknown = sorted(set(raw) - set(REQUIRED))
    if missing or unknown:
        raise BaselineError(f"summary fields differ: missing={missing}, unknown={unknown}")

    version = _non_negative_int(raw["schema_version"], "schema_version")
    if version != SCHEMA_VERSION:
        raise BaselineError(f"schema_version must be {SCHEMA_VERSION}, got {version}")

    total = _non_negative_int(raw["claims_total"], "claims_total")
    by_status = _status_counts(raw["by_status"], "by_status")
    if sum(by_status.values()) != total:
        raise BaselineError(
            f"by_status sums to {sum(by_status.values())}, claims_total is {total}"
        )

    by_kind_raw = raw["by_kind"]
    if not isinstance(by_kind_raw, Mapping) or not by_kind_raw:
        raise BaselineError("by_kind must be a non-empty object")
    by_kind = {
        str(kind): _status_counts(counts, f"by_kind.{kind}")
        for kind, counts in sorted(by_kind_raw.items())
    }
    if any(not kind for kind in by_kind):
        raise BaselineError("by_kind keys must be non-empty strings")
    if sum(sum(counts.values()) for counts in by_kind.values()) != total:
        raise BaselineError("by_kind totals do not sum to claims_total")
    folded_status = {
        status: sum(counts[status] for counts in by_kind.values()) for status in STATUSES
    }
    if folded_status != by_status:
        raise BaselineError("by_kind status totals do not agree with by_status")

    by_risk_raw = raw["by_risk"]
    if not isinstance(by_risk_raw, Mapping):
        raise BaselineError("by_risk must be an object")
    missing_risks = sorted(set(RISKS) - set(by_risk_raw))
    unknown_risks = sorted(set(by_risk_raw) - set(RISKS))
    if missing_risks or unknown_risks:
        raise BaselineError(
            f"by_risk keys differ: missing={missing_risks}, unknown={unknown_risks}"
        )
    by_risk = {risk: _status_counts(by_risk_raw[risk], f"by_risk.{risk}") for risk in RISKS}
    if sum(sum(counts.values()) for counts in by_risk.values()) != total:
        raise BaselineError("by_risk totals do not sum to claims_total")
    folded_risk_status = {
        status: sum(counts[status] for counts in by_risk.values()) for status in STATUSES
    }
    if folded_risk_status != by_status:
        raise BaselineError("by_risk status totals do not agree with by_status")

    conflicts_raw = raw["active_conflicts"]
    if not isinstance(conflicts_raw, list) or not all(
        isinstance(claim_id, str) and claim_id for claim_id in conflicts_raw
    ):
        raise BaselineError("active_conflicts must be a list of non-empty claim ids")
    conflicts = sorted(set(conflicts_raw))
    if conflicts != conflicts_raw:
        raise BaselineError("active_conflicts must be sorted and unique")
    if len(conflicts) != by_status["conflicted"]:
        raise BaselineError("active_conflicts count must equal by_status.conflicted")

    content_hash = raw["content_hash"]
    if not isinstance(content_hash, str) or len(content_hash) != 64:
        raise BaselineError("content_hash must be a lowercase SHA-256 hex digest")
    try:
        int(content_hash, 16)
    except ValueError as exc:
        raise BaselineError("content_hash must be a lowercase SHA-256 hex digest") from exc
    if content_hash != content_hash.lower():
        raise BaselineError("content_hash must be lowercase")

    return {
        "schema_version": version,
        "claims_total": total,
        "by_status": by_status,
        "by_kind": by_kind,
        "by_risk": by_risk,
        "active_conflicts": conflicts,
        "content_hash": content_hash,
    }


def load_summary(path: str) -> dict[str, object]:
    try:
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise BaselineError(f"cannot read {path}: {exc}") from exc
    return validate_summary(raw)


def render_summary(summary: Mapping[str, object]) -> str:
    return json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def compare(current: Mapping[str, object], baseline: Mapping[str, object]) -> list[str]:
    """Return stable, review-friendly differences between two validated summaries."""

    differences = []
    for field in REQUIRED:
        if current[field] != baseline[field]:
            differences.append(
                f"{field}: baseline={json.dumps(baseline[field], sort_keys=True)} "
                f"current={json.dumps(current[field], sort_keys=True)}"
            )
    return differences


def atomic_write(path: str, text: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--current", required=True, help="fresh generated summary JSON")
    parser.add_argument("--baseline", required=True, help="reviewed baseline JSON")
    parser.add_argument(
        "--update",
        action="store_true",
        help="replace the baseline with the validated current summary",
    )
    args = parser.parse_args(argv)

    try:
        current = load_summary(args.current)
        if args.update:
            atomic_write(args.baseline, render_summary(current))
            print(f"evidence baseline: updated {args.baseline}")
            return 0
        baseline = load_summary(args.baseline)
        differences = compare(current, baseline)
    except BaselineError as exc:
        print(f"evidence baseline: INVALID: {exc}", file=sys.stderr)
        return 2

    if differences:
        print("evidence baseline: DRIFT -- review the census and run --update in this commit")
        for difference in differences:
            print(f"  {difference}")
        return 1

    print(
        "evidence baseline: OK -- "
        f"{current['claims_total']} claims, {len(current['active_conflicts'])} active conflicts"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
