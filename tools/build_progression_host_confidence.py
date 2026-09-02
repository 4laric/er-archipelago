#!/usr/bin/env python3
"""Build conservative external-corroboration confidence for progression-host review."""
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from io import StringIO
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield/evidence/wiki-audit"
OUT = ROOT / "greenfield/evidence/v060-current/progression_host_confidence.tsv"
REPORT = ROOT / "greenfield/evidence/v060-current/progression_host_confidence_summary.json"
MODULE = ROOT / "greenfield/eldenring/evidence_progression_hosts.py"
FIELDS = ("check_id", "confidence", "access_status", "external_family_count",
          "external_families", "identity_region_lead_ids", "basis", "limitations")
TRUSTED = "trusted_identity_region"
HOLD = "hold"
EXTERNAL_PREFIXES = ("gameplay-guide:", "gameplay-wiki:")


def load_current_check_ids() -> list[int]:
    path = ROOT / "greenfield/eldenring/data.py"
    spec = importlib.util.spec_from_file_location("_host_confidence_data", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return sorted(ap_id for entries in module.LOCATIONS.values() for _name, ap_id, _flag in entries)


def read_external_leads(audit: Path = AUDIT) -> dict[int, dict[str, set[str]]]:
    found: dict[int, dict[str, set[str]]] = defaultdict(
        lambda: {"families": set(), "identity_region_lead_ids": set()})
    for path in sorted(audit.glob("*-check-leads.tsv")):
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                if row.get("subject_kind") != "check" or not row.get("subject_id", "").isdigit():
                    continue
                if row.get("claim_kind") != "identity_region":
                    continue
                if row.get("disposition") != "lead_only":
                    raise ValueError(f"{path.name}:{row.get('lead_id')}: external lead is not lead_only")
                families = {family for family in row.get("independence_families", "").split(";")
                            if family.startswith(EXTERNAL_PREFIXES)}
                if not families:
                    raise ValueError(f"{path.name}:{row.get('lead_id')}: no declared external family")
                check_id = int(row["subject_id"])
                found[check_id]["families"].update(families)
                found[check_id]["identity_region_lead_ids"].add(row["lead_id"])
    return found


def classify(check_ids: list[int], leads: dict[int, dict[str, set[str]]]) -> list[dict[str, str]]:
    if len(check_ids) != len(set(check_ids)):
        raise ValueError("current check ids are not unique")
    rows = []
    for check_id in sorted(check_ids):
        evidence = leads.get(check_id, {"families": set(), "identity_region_lead_ids": set()})
        families = sorted(evidence["families"])
        lead_ids = sorted(evidence["identity_region_lead_ids"])
        confidence = TRUSTED if len(families) >= 2 else HOLD
        if confidence == TRUSTED:
            basis = "identity_region leads from at least two declared external source families"
        elif families:
            basis = "fewer than two declared external families support identity_region"
        else:
            basis = "no external identity_region lead"
        rows.append({
            "check_id": str(check_id), "confidence": confidence,
            "access_status": "unknown", "external_family_count": str(len(families)),
            "external_families": ";".join(families),
            "identity_region_lead_ids": ";".join(lead_ids), "basis": basis,
            "limitations": ("External identity and region corroboration only. This does not prove "
                            "access, route order, progression-host safety, or exclusion."),
        })
    return rows


def render(rows: list[dict[str, str]]) -> str:
    out = StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def summary(rows: list[dict[str, str]], rendered: str) -> dict:
    by_confidence = Counter(row["confidence"] for row in rows)
    by_family_count = Counter(row["external_family_count"] for row in rows)
    return {
        "by_confidence": dict(sorted(by_confidence.items())),
        "by_external_family_count": dict(sorted(by_family_count.items(), key=lambda pair: int(pair[0]))),
        "checks_total": len(rows),
        "content_sha256": hashlib.sha256(rendered.encode()).hexdigest(),
        "input_files": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(AUDIT.glob("*-check-leads.tsv"))
        },
        "minimum_trusted_external_families": 2,
        "schema_version": 1,
    }


def render_module(rows: list[dict[str, str]]) -> str:
    trusted = [int(row["check_id"]) for row in rows if row["confidence"] == TRUSTED]
    held = [int(row["check_id"]) for row in rows if row["confidence"] == HOLD]
    def values(name: str, ids: list[int]) -> list[str]:
        lines = [f"{name} = frozenset(("]
        for start in range(0, len(ids), 12):
            lines.append("    " + ", ".join(map(str, ids[start:start + 12])) + ",")
        lines.append("))")
        return lines
    return "\n".join([
        '"""AUTO-GENERATED external identity/region confidence; not proof of access."""',
        "", "# HOLD means unknown. Neither set is an exclusion list.",
        *values("TRUSTED_PROGRESSION_HOST_APS", trusted), "",
        *values("HOLD_PROGRESSION_HOST_APS", held), "",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    rows = classify(load_current_check_ids(), read_external_leads())
    rendered = render(rows)
    module = render_module(rows)
    report = json.dumps(summary(rows, rendered), indent=2, sort_keys=True) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != rendered:
            raise SystemExit(f"STALE: {OUT}; run {Path(__file__).name}")
        if not REPORT.is_file() or REPORT.read_text(encoding="utf-8") != report:
            raise SystemExit(f"STALE: {REPORT}; run {Path(__file__).name}")
        if not MODULE.is_file() or MODULE.read_text(encoding="utf-8") != module:
            raise SystemExit(f"STALE: {MODULE}; run {Path(__file__).name}")
        print(f"progression host confidence: OK -- {len(rows)} checks")
        return 0
    OUT.write_text(rendered, encoding="utf-8")
    REPORT.write_text(report, encoding="utf-8")
    MODULE.write_text(module, encoding="utf-8")
    print(json.dumps(summary(rows, rendered), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
