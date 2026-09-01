#!/usr/bin/env python3
"""Validate and census the v0.6 per-check access disposition ledger."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path, PurePosixPath

from evidence_ledger import LedgerError, _rows as evidence_rows, validate as validate_evidence

HEADERS = (
    "check_id", "access_claim_id", "disposition", "risk", "option_set", "reason",
    "review_issue", "owner", "review_by", "implementation_path", "implementation_symbol",
)
DISPOSITIONS = {"region_sufficient", "encoded", "excluded", "waived", "unresolved"}
RISKS = {"critical", "high", "medium", "low"}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SYMBOL = re.compile(r"[A-Za-z_][A-Za-z0-9_.:-]{0,255}")
REPO = Path(__file__).resolve().parents[1]


class AccessDispositionError(ValueError):
    pass


def _implementation_witness(row: dict[str, str]) -> None:
    check_id = row["check_id"]
    raw_path = row["implementation_path"]
    symbol = row["implementation_symbol"]
    relative = PurePosixPath(raw_path)
    if (
        not raw_path
        or raw_path != relative.as_posix()
        or relative.is_absolute()
        or ".." in relative.parts
    ):
        raise AccessDispositionError(f"{check_id}: invalid implementation_path")
    if not SYMBOL.fullmatch(symbol):
        raise AccessDispositionError(f"{check_id}: invalid implementation_symbol")
    target = REPO.joinpath(*relative.parts).resolve()
    if not target.is_relative_to(REPO) or not target.is_file():
        raise AccessDispositionError(f"{check_id}: implementation_path does not name a repo file")
    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise AccessDispositionError(f"{check_id}: implementation witness must be UTF-8 text") from exc
    token = rf"(?<![A-Za-z0-9_]){re.escape(symbol)}(?![A-Za-z0-9_])"
    if not re.search(token, content):
        raise AccessDispositionError(
            f"{check_id}: implementation_symbol is absent from {raw_path}"
        )


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
    options_by_check: dict[str, set[str]] = {}
    for row in rows:
        check_id = row["check_id"]
        if row["disposition"] not in DISPOSITIONS:
            raise AccessDispositionError(f"{check_id}: unknown disposition")
        if row["risk"] not in RISKS:
            raise AccessDispositionError(f"{check_id}: unknown risk")
        if not row["option_set"] or row["option_set"] != row["option_set"].strip():
            raise AccessDispositionError(f"{check_id}: option_set must be a canonical non-empty value")
        options_by_check.setdefault(check_id, set()).add(row["option_set"])
        expected_claim = access.get(check_id, {}).get("claim_id", "")
        if row["access_claim_id"] != expected_claim:
            raise AccessDispositionError(
                f"{check_id}: access_claim_id {row['access_claim_id']!r} != {expected_claim!r}"
            )
        if row["disposition"] in {"region_sufficient", "encoded"} and not expected_claim:
            raise AccessDispositionError(
                f"{check_id}: {row['disposition']} requires an active access claim"
            )
        if row["disposition"] in {"region_sufficient", "encoded"}:
            _implementation_witness(row)
        if row["disposition"] in {"excluded", "waived"}:
            required = ("reason", "review_issue", "owner", "review_by")
            if not all(row[field].strip() for field in required):
                raise AccessDispositionError(
                    f"{check_id}: {row['disposition']} requires review metadata"
                )
            if not DATE.fullmatch(row["review_by"]):
                raise AccessDispositionError(f"{check_id}: invalid review_by date")
    for check_id, options in options_by_check.items():
        if "all" in options and len(options) > 1:
            raise AccessDispositionError(
                f"{check_id}: option_set 'all' cannot coexist with specific option sets"
            )
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


def ratchet_snapshot(ledger_dir: Path, disposition_path: Path) -> dict:
    rows = validate(ledger_dir, disposition_path)
    current = summary(ledger_dir, disposition_path)
    return {
        "schema_version": 1,
        "checks_total": current["checks_total"],
        "release_blockers": current["release_blockers"],
        "unresolved": current["by_disposition"]["unresolved"],
        "without_access_claim": current["without_access_claim"],
        "linked_access_claim_ids": sorted(
            {row["access_claim_id"] for row in rows if row["access_claim_id"]}
        ),
        "resolved_dispositions": {
            f"{row['check_id']}|{row['option_set']}": row["disposition"]
            for row in rows
            if row["disposition"] != "unresolved"
        },
    }


def compare_ratchet(current: dict, baseline: dict) -> list[str]:
    expected = {
        "schema_version", "checks_total", "release_blockers", "unresolved",
        "without_access_claim", "linked_access_claim_ids", "resolved_dispositions",
    }
    if set(current) != expected or set(baseline) != expected:
        raise AccessDispositionError("access ratchet has unknown or missing fields")
    if current["schema_version"] != 1 or baseline["schema_version"] != 1:
        raise AccessDispositionError("unknown access ratchet schema_version")
    errors = []
    for field in ("checks_total", "release_blockers", "unresolved", "without_access_claim"):
        if type(current[field]) is not int or type(baseline[field]) is not int:
            raise AccessDispositionError(f"access ratchet {field} must be an integer")
    for name, value in (("current", current), ("baseline", baseline)):
        if not isinstance(value["linked_access_claim_ids"], list) or not all(
            isinstance(item, str) for item in value["linked_access_claim_ids"]
        ):
            raise AccessDispositionError(f"{name} linked_access_claim_ids must be a string list")
        if not isinstance(value["resolved_dispositions"], dict) or not all(
            isinstance(key, str) and disposition in DISPOSITIONS - {"unresolved"}
            for key, disposition in value["resolved_dispositions"].items()
        ):
            raise AccessDispositionError(f"{name} resolved_dispositions is malformed")
    if current["checks_total"] < baseline["checks_total"]:
        errors.append("checks_total decreased")
    for field in ("release_blockers", "unresolved", "without_access_claim"):
        if current[field] > baseline[field]:
            errors.append(f"{field} increased")
    old_links = set(baseline["linked_access_claim_ids"])
    new_links = set(current["linked_access_claim_ids"])
    if len(old_links) != len(baseline["linked_access_claim_ids"]):
        raise AccessDispositionError("baseline linked_access_claim_ids must be unique")
    lost = sorted(old_links - new_links)
    if lost:
        errors.append(f"linked access evidence disappeared: {lost!r}")
    allowed = {
        "encoded": {"encoded"},
        "region_sufficient": {"region_sufficient", "encoded"},
        "excluded": {"excluded", "region_sufficient", "encoded"},
        "waived": {"waived", "region_sufficient", "encoded"},
    }
    for key, old_disposition in baseline["resolved_dispositions"].items():
        new_disposition = current["resolved_dispositions"].get(key)
        if new_disposition not in allowed.get(old_disposition, set()):
            errors.append(
                f"resolved disposition regressed: {key} {old_disposition!r} -> {new_disposition!r}"
            )
    return errors


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
                "implementation_path": "",
                "implementation_symbol": "",
            }
            handle.write("\t".join(row[field] for field in HEADERS).rstrip("\t") + "\n")


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--dispositions", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--bootstrap", action="store_true")
    parser.add_argument("--update-summary", action="store_true")
    parser.add_argument("--update-baseline", action="store_true")
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
        if args.baseline:
            snapshot = ratchet_snapshot(args.ledger, args.dispositions)
            if args.update_baseline:
                _write_json(args.baseline, snapshot)
            else:
                baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
                regressions = compare_ratchet(snapshot, baseline)
                if regressions:
                    raise AccessDispositionError("; ".join(regressions))
    except (AccessDispositionError, LedgerError, OSError, json.JSONDecodeError) as exc:
        print(f"access dispositions INVALID: {exc}")
        return 1
    print("access dispositions OK: " + json.dumps(current, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
