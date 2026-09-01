#!/usr/bin/env python3
"""Validate and census the v0.6 per-check access disposition ledger."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from evidence_ledger import LedgerError, _rows as evidence_rows, validate as validate_evidence

HEADERS = (
    "check_id", "access_claim_id", "disposition", "risk", "option_set", "reason",
    "review_issue", "owner", "review_by",
)
DISPOSITIONS = {"region_sufficient", "encoded", "excluded", "waived", "unresolved"}
RISKS = {"critical", "high", "medium", "low"}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class AccessDispositionError(ValueError):
    pass


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if tuple(reader.fieldnames or ()) != HEADERS:
            raise AccessDispositionError(f"header must be {HEADERS!r}")
        rows = []
        for line_number, row in enumerate(reader, 2):
            if None in row:
                raise AccessDispositionError(f"line {line_number}: row width differs from header")
            # Reviewer metadata is optional except on exclusions/waivers. Physically omitted
            # trailing cells normalize to empty so tracked TSV rows do not carry trailing tabs.
            rows.append({key: (value or "") for key, value in row.items()})
    keys = [(row["check_id"], row["option_set"]) for row in rows]
    if keys != sorted(keys) or len(keys) != len(set(keys)):
        raise AccessDispositionError("rows must have unique, deterministic check/option keys")
    return rows


def _current_claims(ledger_dir: Path):
    validate_evidence(ledger_dir)
    claims = evidence_rows(ledger_dir / "claims.tsv")
    regions = {
        row["subject_id"]: row
        for row in claims
        if row["active"] == "true"
        and row["subject_kind"] == "check"
        and row["claim_kind"] == "region"
    }
    access = {
        row["subject_id"]: row
        for row in claims
        if row["active"] == "true"
        and row["subject_kind"] == "check"
        and row["claim_kind"] == "access"
    }
    if len(regions) != sum(
        row["active"] == "true"
        and row["subject_kind"] == "check"
        and row["claim_kind"] == "region"
        for row in claims
    ):
        raise AccessDispositionError("active region claims do not identify unique checks")
    if set(access) - set(regions):
        raise AccessDispositionError("active access claim has no active region-check subject")
    return regions, access


def validate(ledger_dir: Path, disposition_path: Path) -> list[dict[str, str]]:
    regions, access = _current_claims(ledger_dir)
    rows = _read(disposition_path)
    represented = {row["check_id"] for row in rows}
    if represented != set(regions):
        missing = sorted(set(regions) - represented)
        extra = sorted(represented - set(regions))
        raise AccessDispositionError(
            f"disposition population differs from active checks: missing={missing[:5]!r}, extra={extra[:5]!r}"
        )
    for row in rows:
        check_id = row["check_id"]
        if row["disposition"] not in DISPOSITIONS:
            raise AccessDispositionError(f"{check_id}: unknown disposition")
        if row["risk"] not in RISKS:
            raise AccessDispositionError(f"{check_id}: unknown risk")
        if not row["option_set"] or row["option_set"] != row["option_set"].strip():
            raise AccessDispositionError(f"{check_id}: option_set must be a canonical non-empty value")
        expected_claim = access.get(check_id, {}).get("claim_id", "")
        if row["access_claim_id"] != expected_claim:
            raise AccessDispositionError(
                f"{check_id}: access_claim_id {row['access_claim_id']!r} != {expected_claim!r}"
            )
        if row["disposition"] in {"region_sufficient", "encoded"} and not expected_claim:
            raise AccessDispositionError(
                f"{check_id}: {row['disposition']} requires an active access claim"
            )
        if row["disposition"] in {"excluded", "waived"}:
            required = ("reason", "review_issue", "owner", "review_by")
            if not all(row[field].strip() for field in required):
                raise AccessDispositionError(
                    f"{check_id}: {row['disposition']} requires review metadata"
                )
            if not DATE.fullmatch(row["review_by"]):
                raise AccessDispositionError(f"{check_id}: invalid review_by date")
    return rows


def summary(ledger_dir: Path, disposition_path: Path) -> dict:
    rows = validate(ledger_dir, disposition_path)
    counts = Counter(row["disposition"] for row in rows)
    by_risk = {
        risk: Counter(row["disposition"] for row in rows if row["risk"] == risk)
        for risk in sorted(RISKS)
    }
    by_option = {
        option: Counter(row["disposition"] for row in rows if row["option_set"] == option)
        for option in sorted({row["option_set"] for row in rows})
    }
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    checks = {row["check_id"] for row in rows}
    return {
        "schema_version": 1,
        "checks_total": len(checks),
        "dispositions_total": len(rows),
        "by_disposition": {key: counts.get(key, 0) for key in sorted(DISPOSITIONS)},
        "by_risk": {
            risk: {key: by_risk[risk].get(key, 0) for key in sorted(DISPOSITIONS)}
            for risk in sorted(RISKS)
        },
        "by_option_set": {
            option: {key: by_option[option].get(key, 0) for key in sorted(DISPOSITIONS)}
            for option in sorted(by_option)
        },
        "with_access_claim": sum(bool(row["access_claim_id"]) for row in rows),
        "without_access_claim": sum(not row["access_claim_id"] for row in rows),
        "release_blockers": sum(
            row["disposition"] == "unresolved" and row["risk"] in {"critical", "high"}
            for row in rows
        ),
        "content_hash": hashlib.sha256(canonical).hexdigest(),
    }


def bootstrap(ledger_dir: Path, destination: Path) -> None:
    if destination.exists():
        raise AccessDispositionError(f"refusing to overwrite existing {destination}")
    regions, access = _current_claims(ledger_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        handle.write("\t".join(HEADERS) + "\n")
        for check_id in sorted(regions):
            row = {
                "check_id": check_id,
                "access_claim_id": access.get(check_id, {}).get("claim_id", ""),
                "disposition": "unresolved",
                "risk": access.get(check_id, {}).get("risk", "critical"),
                "option_set": "all",
                "reason": "",
                "review_issue": "",
                "owner": "",
                "review_by": "",
            }
            handle.write("\t".join(row[field] for field in HEADERS).rstrip("\t") + "\n")


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--dispositions", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--bootstrap", action="store_true")
    parser.add_argument("--update-summary", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.bootstrap:
            bootstrap(args.ledger, args.dispositions)
        current = summary(args.ledger, args.dispositions)
        if args.summary:
            if args.update_summary:
                _write_json(args.summary, current)
            else:
                committed = json.loads(args.summary.read_text(encoding="utf-8"))
                if committed != current:
                    raise AccessDispositionError("committed summary differs from current census")
    except (AccessDispositionError, LedgerError, OSError, json.JSONDecodeError) as exc:
        print(f"access dispositions INVALID: {exc}")
        return 1
    print("access dispositions OK: " + json.dumps(current, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
