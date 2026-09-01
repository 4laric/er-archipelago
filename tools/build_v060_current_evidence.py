#!/usr/bin/env python3
"""Emit the v0.6 phase-1 identity/region census from the current generated corpus.

This is an adapter, not a new source of truth. It snapshots data.LOCATIONS and preserves
the lineage of an applicable region_overrides.tsv ruling. The generated location and its
override evidence deliberately share one family: data.py consumes that table, so their
agreement is not independent corroboration.

The record dictionaries intentionally use the field names in
SPEC-check-evidence-ledger-v060.md. Until #1210 lands, the four checked-in files are the
adapter's local interchange fixture. No runtime module consumes them.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Iterable, Mapping

import evidence_ledger

REVIEW_DATE = "2026-08-31"
GAME_VERSION = "1.17"


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _load_generated_locations(data_path: Path) -> tuple[list[dict], dict]:
    spec = importlib.util.spec_from_file_location("_v060_current_data", data_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load generated locations from {data_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    stamp = dict(module._GEN_STAMP)
    rows = []
    for region, locations in module.LOCATIONS.items():
        for name, ap_id, flag in locations:
            rows.append({
                "ap_id": int(ap_id), "flag": int(flag), "name": str(name), "region": str(region),
            })
    rows.sort(key=lambda row: row["ap_id"])
    ap_ids = [row["ap_id"] for row in rows]
    if not rows:
        raise RuntimeError("generated location corpus is empty")
    if len(ap_ids) != len(set(ap_ids)):
        duplicates = sorted(ap for ap, count in Counter(ap_ids).items() if count > 1)
        raise RuntimeError(f"duplicate AP location ids in generated corpus: {duplicates[:10]}")
    return rows, stamp


def _load_flag_region_overrides(path: Path) -> tuple[dict[int, dict], int]:
    """Return flag-scoped rulings and the number of non-flag rows deliberately out of scope."""
    overrides: dict[int, dict] = {}
    non_flag = 0
    with path.open(encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(
            (line for line in handle if line.strip() and not line.startswith("#")), delimiter="\t")
        for line_number, row in enumerate(rows, start=2):
            if row["key_kind"] != "flag":
                non_flag += 1
                continue
            flag = int(row["key"])
            if flag in overrides:
                raise RuntimeError(f"duplicate active flag ruling for {flag} in {path}")
            overrides[flag] = {
                "region": row["region"], "reason": row["reason"], "line": line_number,
            }
    return overrides, non_flag


def _load_map_lot_detection(path: Path) -> dict[int, list[dict]]:
    """Load exact ItemLotParam_map citations, grouped by their acquisition event flag."""
    by_flag: dict[int, list[dict]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle, delimiter="\t")
        for line_number, row in enumerate(rows, start=2):
            if row["table"] != "map":
                continue
            flag = int(row["flag"])
            lot = int(row["lot"])
            existing_lots = {entry["lot"] for entry in by_flag.setdefault(flag, [])}
            if lot not in existing_lots:
                by_flag[flag].append({"lot": lot, "line": line_number})
    for rows in by_flag.values():
        rows.sort(key=lambda row: (row["lot"], row["line"]))
    return by_flag


def _load_stormhill_access(path: Path) -> list[dict[str, object]]:
    """Load the exact f400191 WaitFor sites without treating their join as detection evidence."""
    matches = []
    with path.open(encoding="utf-8", newline="") as handle:
        header = ""
        for line_number, line in enumerate(handle, start=1):
            if not line.strip() or line.startswith("#"):
                continue
            if not header:
                header = line
                continue
            row = next(csv.DictReader([header, line], delimiter="\t"))
            if row["check_flag"] != "400191" or row["context"] != "commonarg/WaitFor":
                continue
            matches.append({
                "line": line_number, "gate_flag": int(row["gate_flag"]),
                "context": row["context"], "event_id": int(row["event_id"]),
                "source": row["source"], "evidence": row["evidence"],
                "gate_map": row["gate_map"], "gate_test_map": row["gate_test_map"],
            })
    matches.sort(key=lambda row: int(row["gate_flag"]))
    if [row["gate_flag"] for row in matches] != [3708, 3709, 1041389414]:
        raise RuntimeError(f"f400191 WaitFor corpus changed: {matches!r}")
    if {row["event_id"] for row in matches} != {90005750}:
        raise RuntimeError(f"f400191 WaitFor event changed: {matches!r}")
    return matches


def _load_perfect_order_access(path: Path) -> dict[str, object]:
    """Load the one exact f9500 WaitFor site; its param join is not a detection witness."""
    matches = []
    with path.open(encoding="utf-8", newline="") as handle:
        header = ""
        for line_number, line in enumerate(handle, start=1):
            if not line.strip() or line.startswith("#"):
                continue
            if not header:
                header = line
                continue
            row = next(csv.DictReader([header, line], delimiter="\t"))
            if row["check_flag"] != "9500" or row["context"] != "commonarg/WaitFor":
                continue
            matches.append({
                "line": line_number, "gate_flag": int(row["gate_flag"]),
                "context": row["context"], "event_id": int(row["event_id"]),
                "source": row["source"], "evidence": row["evidence"],
                "gate_map": row["gate_map"],
            })
    if len(matches) != 1 or matches[0]["gate_flag"] != 11059206:
        raise RuntimeError(f"f9500 WaitFor corpus changed: {matches!r}")
    if matches[0]["event_id"] != 90005750:
        raise RuntimeError(f"f9500 WaitFor event changed: {matches!r}")
    return matches[0]


def _source_records(
        repo: Path, data_path: Path, override_path: Path, lot_path: Path,
        stamp: Mapping[str, str]):
    body_hash = str(stamp["body_sha256"])
    family_id = f"project:current-locations:{body_hash.removeprefix('sha256:')}"
    generated_id = f"project:data.py:{body_hash.removeprefix('sha256:')}"
    override_hash = _sha256(override_path)
    override_id = f"project:region-overrides:{override_hash.removeprefix('sha256:')}"
    lot_hash = _sha256(lot_path)
    lot_id = f"game:param:ItemLotParam_map:{lot_hash.removeprefix('sha256:')}"
    data_display = data_path.relative_to(repo).as_posix()
    override_display = override_path.relative_to(repo).as_posix()
    lot_display = lot_path.relative_to(repo).as_posix()
    sources = [
        {
            "source_id": generated_id, "source_kind": "project_derivation",
            "family_id": family_id, "title": "Current generated Elden Ring locations",
            "game_version": GAME_VERSION, "retrieved_at": REVIEW_DATE, "revision": body_hash,
            "url_or_path": data_display, "license": "project-derived",
            "environment_id": "", "supersedes": "",
        },
        {
            "source_id": lot_id, "source_kind": "game_data",
            "family_id": "game:param:ItemLotParam_map",
            "title": "ItemLotParam_map acquisition flags",
            "game_version": GAME_VERSION, "retrieved_at": REVIEW_DATE,
            "revision": lot_hash, "url_or_path": lot_display,
            "license": "private-evidence", "environment_id": "", "supersedes": "",
        },
        {
            "source_id": override_id, "source_kind": "ruling",
            # Same family on purpose: data.py consumes this table.
            "family_id": family_id, "title": "Current project region rulings",
            "game_version": GAME_VERSION, "retrieved_at": REVIEW_DATE,
            "revision": override_hash,
            "url_or_path": override_display, "license": "project-derived",
            "environment_id": "", "supersedes": "",
        },
    ]
    sources.sort(key=lambda row: row["source_id"])
    return sources, {
        "family_id": family_id, "generated_id": generated_id, "override_id": override_id,
        "lot_id": lot_id, "body_hash": body_hash, "override_hash": override_hash,
        "lot_hash": lot_hash,
    }


def build_records(repo: Path) -> dict:
    data_path = repo / "greenfield" / "eldenring" / "data.py"
    override_path = repo / "greenfield" / "region_overrides.tsv"
    lot_path = repo / "greenfield" / "flag_lots.tsv"
    lot_gates_path = repo / "greenfield" / "lot_gates.tsv"
    locations, stamp = _load_generated_locations(data_path)
    overrides, non_flag_overrides = _load_flag_region_overrides(override_path)
    map_lots = _load_map_lot_detection(lot_path)
    stormhill_access = _load_stormhill_access(lot_gates_path)
    perfect_order_access = _load_perfect_order_access(lot_gates_path)
    sources, source = _source_records(repo, data_path, override_path, lot_path, stamp)
    lot_gates_hash = _sha256(lot_gates_path)
    lot_gates_source_id = (
        f"game:emevd-lot-gates:m60_41_38_00:{lot_gates_hash.removeprefix('sha256:')}")
    sources.append({
        "source_id": lot_gates_source_id, "source_kind": "game_data",
        "family_id": "game:emevd:m60_41_38_00:90005750",
        "title": "Stormhill Shack f400191 WaitFor call sites",
        "game_version": GAME_VERSION, "retrieved_at": REVIEW_DATE,
        "revision": lot_gates_hash, "url_or_path": "greenfield/lot_gates.tsv",
        "license": "private-evidence", "environment_id": "", "supersedes": "",
    })
    perfect_order_source_id = (
        f"game:emevd-lot-gates:m11_05_00_00:{lot_gates_hash.removeprefix('sha256:')}")
    sources.append({
        "source_id": perfect_order_source_id, "source_kind": "game_data",
        "family_id": "game:emevd:m11_05_00_00:90005750",
        "title": "Mending Rune of Perfect Order f9500 WaitFor call site",
        "game_version": GAME_VERSION, "retrieved_at": REVIEW_DATE,
        "revision": lot_gates_hash, "url_or_path": "greenfield/lot_gates.tsv",
        "license": "private-evidence", "environment_id": "", "supersedes": "",
    })
    sources.sort(key=lambda row: row["source_id"])
    environments: list[dict] = []
    evidence: list[dict] = []
    claims: list[dict] = []
    matched_override_flags: set[int] = set()
    matched_map_lot_flags: set[int] = set()

    for location in locations:
        ap_id, flag = location["ap_id"], location["flag"]
        identity_claim_id = f"check:{ap_id}/identity"
        region_claim_id = f"check:{ap_id}/region"
        # data.LOCATIONS exposes the AP id and event flag, but not a normalized lot/shop id.
        # Preserve that legacy key without pretending a second derived table is independent.
        identity_value = {"ap_id": ap_id, "flag": flag, "namespace": "flag", "id": flag}
        identity_evidence_id = (
            f"project:data.py:{source['body_hash'].removeprefix('sha256:')}:"
            f"check-{ap_id}:identity")
        evidence.append({
            "evidence_id": identity_evidence_id, "claim_id": identity_claim_id,
            "source_id": source["generated_id"],
            "stance": "supports", "value": _json(identity_value),
            "citation": f"greenfield/eldenring/data.py:LOCATIONS ap_id={ap_id} flag={flag}",
            "method": "tools/build_v060_current_evidence.py:current_locations",
            "independence_notes":
                "Generated location snapshot; downstream views of data.py are this same family.",
            "valid_from": GAME_VERSION, "valid_to": "",
            "notes":
                "Legacy current-corpus key: data.py exposes an event flag, not a vanilla lot/shop id.",
        })
        claims.append({
            "claim_id": identity_claim_id, "subject_kind": "check", "subject_id": str(ap_id),
            "claim_kind": "identity", "game_version": GAME_VERSION,
            "value": _json(identity_value),
            "status": "single_source", "risk": "medium",
            "adjudication": "automatic", "evidence_ids": identity_evidence_id,
            "last_reviewed": REVIEW_DATE, "review_issue": "#1211", "active": "true",
            "supersedes": "",
        })

        lot_rows = map_lots.get(flag, [])
        if lot_rows:
            matched_map_lot_flags.add(flag)
            detection_claim_id = f"check:{ap_id}/detection"
            detection_value = {"mechanism": "ItemLotParam_map.getItemFlagId", "flag": flag}
            detection_evidence_ids = []
            for lot_row in lot_rows:
                evidence_id = (
                    f"game:param:ItemLotParam_map:{lot_row['lot']}:"
                    f"getItemFlagId:check-{ap_id}")
                detection_evidence_ids.append(evidence_id)
                evidence.append({
                    "evidence_id": evidence_id, "claim_id": detection_claim_id,
                    "source_id": source["lot_id"], "stance": "supports",
                    "value": _json(detection_value),
                    "citation": (
                        f"greenfield/flag_lots.tsv:{lot_row['line']} table=map "
                        f"lot={lot_row['lot']} getItemFlagId={flag}"),
                    "method": "tools/build_v060_current_evidence.py:map_lot_detection",
                    "independence_notes": (
                        "Rows from ItemLotParam_map share one game:param family; multiple lot "
                        "rows are one witness, not corroboration."),
                    "valid_from": GAME_VERSION, "valid_to": "",
                    "notes": "Exact map-lot acquisition flag from the committed param census.",
                })
            claims.append({
                "claim_id": detection_claim_id, "subject_kind": "check",
                "subject_id": str(ap_id), "claim_kind": "detection",
                "game_version": GAME_VERSION, "value": _json(detection_value),
                "status": "single_source", "risk": "high", "adjudication": "automatic",
                "evidence_ids": ",".join(sorted(detection_evidence_ids)),
                "last_reviewed": REVIEW_DATE, "review_issue": "#1220", "active": "true",
                "supersedes": "",
            })

        region_value = location["region"]
        generated_region_evidence_id = (
            f"project:data.py:{source['body_hash'].removeprefix('sha256:')}:"
            f"check-{ap_id}:region")
        region_evidence_ids = [generated_region_evidence_id]
        evidence.append({
            "evidence_id": generated_region_evidence_id, "claim_id": region_claim_id,
            "source_id": source["generated_id"],
            "stance": "supports", "value": _json(region_value),
            "citation":
                f"greenfield/eldenring/data.py:LOCATIONS[{location['region']!r}] ap_id={ap_id}",
            "method": "tools/build_v060_current_evidence.py:current_locations",
            "independence_notes":
                "Current region is generated; its provenance inputs are not independent witnesses.",
            "valid_from": GAME_VERSION, "valid_to": "",
            "notes": "Current runtime filing; this adapter does not promote it into generation.",
        })

        ruling = overrides.get(flag)
        contradictory = False
        if ruling is not None:
            matched_override_flags.add(flag)
            ruling_value = ruling["region"]
            contradictory = ruling["region"] != location["region"]
            ruling_evidence_id = (
                f"project:region-overrides:{source['override_hash'].removeprefix('sha256:')}:"
                f"line-{ruling['line']}:check-{ap_id}:region")
            region_evidence_ids.append(ruling_evidence_id)
            evidence.append({
                "evidence_id": ruling_evidence_id, "claim_id": region_claim_id,
                "source_id": source["override_id"],
                "stance": "contradicts" if contradictory else "supports",
                "value": _json(ruling_value),
                "citation": f"greenfield/region_overrides.tsv:{ruling['line']} flag={flag}",
                "method": "tools/build_v060_current_evidence.py:flag_region_rulings",
                "independence_notes":
                    "Not independent of data.py: gen_data consumes region_overrides.tsv; "
                    "both records share one family and count once.",
                "valid_from": GAME_VERSION, "valid_to": "", "notes": ruling["reason"],
            })
        claims.append({
            "claim_id": region_claim_id, "subject_kind": "check", "subject_id": str(ap_id),
            "claim_kind": "region", "game_version": GAME_VERSION,
            "value": _json(region_value),
            "status": "conflicted" if contradictory else "single_source", "risk": "high",
            "adjudication": "automatic",
            "evidence_ids": ",".join(sorted(region_evidence_ids)),
            "last_reviewed": REVIEW_DATE, "review_issue": "#1211", "active": "true",
            "supersedes": "",
        })

    stormhill = [row for row in locations if row["flag"] == 400191]
    if len(stormhill) != 1:
        raise RuntimeError(f"expected one current f400191 check, found {stormhill!r}")
    stormhill_ap_id = stormhill[0]["ap_id"]
    access_claim_id = f"check:{stormhill_ap_id}/access"
    access_value = {
        "type": "any",
        "conditions": [{"type": "flag", "flag": row["gate_flag"]}
                       for row in stormhill_access],
    }
    access_evidence_ids = []
    for row in stormhill_access:
        gate_flag = row["gate_flag"]
        evidence_id = (
            f"game:emevd:m60_41_38_00:90005750:f400191:gate-{gate_flag}:access")
        access_evidence_ids.append(evidence_id)
        locator = row["gate_map"] or row["gate_test_map"]
        evidence.append({
            "evidence_id": evidence_id, "claim_id": access_claim_id,
            "source_id": lot_gates_source_id, "stance": "supports",
            "value": _json(access_value),
            "citation": (
                f"greenfield/lot_gates.tsv:{row['line']} check_flag=400191 "
                f"gate_flag={gate_flag}; {row['source']} event={row['event_id']} "
                f"{row['context']} {row['evidence']} {locator}"
            ),
            "method": "tools/build_v060_current_evidence.py:stormhill_waitfor_access",
            "independence_notes": (
                "One of three OR arms in the same EMEVD common-event family; the f400191 "
                "association is joined through ItemLotParam/flag_lots and is not independent "
                "detection evidence."
            ),
            "valid_from": GAME_VERSION, "valid_to": "",
            "notes": "Positive WaitFor prerequisite; separate call sites form one any group.",
        })
    claims.append({
        "claim_id": access_claim_id, "subject_kind": "check",
        "subject_id": str(stormhill_ap_id), "claim_kind": "access",
        "game_version": GAME_VERSION, "value": _json(access_value),
        "status": "single_source", "risk": "critical", "adjudication": "automatic",
        "evidence_ids": ",".join(sorted(access_evidence_ids)),
        "last_reviewed": REVIEW_DATE, "review_issue": "#1226", "active": "true",
        "supersedes": "",
    })

    perfect_order = [row for row in locations if row["flag"] == 9500]
    if len(perfect_order) != 1:
        raise RuntimeError(f"expected one current f9500 check, found {perfect_order!r}")
    perfect_order_ap_id = perfect_order[0]["ap_id"]
    perfect_order_claim_id = f"check:{perfect_order_ap_id}/access"
    perfect_order_value = {"type": "flag", "flag": perfect_order_access["gate_flag"]}
    perfect_order_evidence_id = (
        "game:emevd:m11_05_00_00:90005750:f9500:gate-11059206:access")
    evidence.append({
        "evidence_id": perfect_order_evidence_id, "claim_id": perfect_order_claim_id,
        "source_id": perfect_order_source_id, "stance": "supports",
        "value": _json(perfect_order_value),
        "citation": (
            f"greenfield/lot_gates.tsv:{perfect_order_access['line']} check_flag=9500 "
            f"gate_flag=11059206; {perfect_order_access['source']} "
            f"event={perfect_order_access['event_id']} {perfect_order_access['context']} "
            f"{perfect_order_access['evidence']} {perfect_order_access['gate_map']}"
        ),
        "method": "tools/build_v060_current_evidence.py:perfect_order_waitfor_access",
        "independence_notes": (
            "The one WaitFor call is one EMEVD family; the f9500 association is joined through "
            "ItemLotParam/flag_lots and is not independent detection evidence."
        ),
        "valid_from": GAME_VERSION, "valid_to": "",
        "notes": "Positive WaitFor prerequisite; one call site has semantics=single.",
    })
    claims.append({
        "claim_id": perfect_order_claim_id, "subject_kind": "check",
        "subject_id": str(perfect_order_ap_id), "claim_kind": "access",
        "game_version": GAME_VERSION, "value": _json(perfect_order_value),
        "status": "single_source", "risk": "critical", "adjudication": "automatic",
        "evidence_ids": perfect_order_evidence_id,
        "last_reviewed": REVIEW_DATE, "review_issue": "#1232", "active": "true",
        "supersedes": "",
    })

    evidence.sort(key=lambda row: row["evidence_id"])
    claims.sort(key=lambda row: row["claim_id"])
    source_ids = {row["source_id"] for row in sources}
    claim_ids = {row["claim_id"] for row in claims}
    if len(claim_ids) != len(claims):
        raise RuntimeError("adapter emitted duplicate active claims")
    if any(row["source_id"] not in source_ids for row in evidence):
        raise RuntimeError("adapter emitted evidence with a dangling source")
    if any(row["claim_id"] not in claim_ids for row in evidence):
        raise RuntimeError("adapter emitted evidence with a dangling claim")

    content = {
        "sources": sources, "evidence": evidence, "claims": claims,
        "environments": environments,
    }
    return {
        **content,
        "diagnostics": {
            "locations": len(locations), "flag_overrides_total": len(overrides),
            "flag_overrides_matched": len(matched_override_flags),
            "flag_overrides_without_current_check": len(set(overrides) - matched_override_flags),
            "non_flag_overrides_out_of_scope": non_flag_overrides,
            "map_lot_rows": sum(len(rows) for rows in map_lots.values()),
            "map_lot_flags": len(map_lots),
            "map_lot_flags_matched": len(matched_map_lot_flags),
            "map_lot_flags_without_current_check": len(set(map_lots) - matched_map_lot_flags),
            "stormhill_access_claims": 1,
            "perfect_order_access_claims": 1,
        },
    }


def _write_tsv(path: Path, fields: Iterable[str], rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(fields)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(fields)
        for row in rows:
            values = [row.get(field, "") for field in fields]
            while values and values[-1] == "":
                values.pop()
            writer.writerow(values)


def write_bundle(repo: Path, out_dir: Path) -> dict:
    bundle = build_records(repo)
    table_rows = {
        "sources.tsv": bundle["sources"],
        "evidence.tsv": bundle["evidence"],
        "claims.tsv": bundle["claims"],
        "environments.tsv": bundle["environments"],
    }
    for name, rows in table_rows.items():
        _write_tsv(out_dir / name, evidence_ledger.HEADERS[name], rows)
    evidence_ledger.validate(out_dir)
    bundle["summary"] = evidence_ledger.summary(out_dir)
    (out_dir / "summary.json").write_text(
        json.dumps(bundle["summary"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out-dir", type=Path, default=Path("greenfield/evidence/v060-current"))
    args = parser.parse_args()
    repo = args.repo.resolve()
    out_dir = args.out_dir if args.out_dir.is_absolute() else repo / args.out_dir
    bundle = write_bundle(repo, out_dir)
    print(_json({**bundle["summary"], **bundle["diagnostics"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
