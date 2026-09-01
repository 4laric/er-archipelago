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


SCHEMA_VERSION = "v0.6-phase1-adapter-1"
REVIEW_DATE = "2026-08-31"
SOURCE_FIELDS = (
    "source_id", "source_kind", "family_id", "title", "game_version", "retrieved_at",
    "revision", "url_or_path", "license", "environment_id", "supersedes", "lineage",
)
EVIDENCE_FIELDS = (
    "evidence_id", "claim_id", "source_id", "family_id", "stance", "value", "citation",
    "method", "independence_notes", "valid_from", "valid_to", "notes", "lineage",
)
CLAIM_FIELDS = (
    "claim_id", "subject_kind", "subject_id", "claim_kind", "value", "status", "risk",
    "adjudication", "evidence_ids", "last_reviewed", "review_issue",
)


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


def _source_records(repo: Path, data_path: Path, override_path: Path, stamp: Mapping[str, str]):
    inputs_hash = str(stamp["inputs_hash"])
    body_hash = str(stamp["body_sha256"])
    family_id = f"project:current-locations:{inputs_hash.removeprefix('sha256:')}"
    generated_id = f"project:data.py:{body_hash.removeprefix('sha256:')}"
    override_hash = _sha256(override_path)
    override_id = f"project:region-overrides:{override_hash.removeprefix('sha256:')}"
    common_lineage = [f"greenfield/gen_inputs.db@{inputs_hash}", "greenfield/gen_data.py"]
    data_display = data_path.relative_to(repo).as_posix()
    override_display = override_path.relative_to(repo).as_posix()
    sources = [
        {
            "source_id": generated_id, "source_kind": "project_derivation",
            "family_id": family_id, "title": "Current generated Elden Ring locations",
            "game_version": "current-corpus", "retrieved_at": "", "revision": body_hash,
            "url_or_path": data_display, "license": "project-derived",
            "environment_id": "", "supersedes": "",
            "lineage": _json(common_lineage + [data_display]),
        },
        {
            "source_id": override_id, "source_kind": "ruling",
            # Same family on purpose: data.py consumes this table.
            "family_id": family_id, "title": "Current project region rulings",
            "game_version": "current-corpus", "retrieved_at": "", "revision": override_hash,
            "url_or_path": override_display, "license": "project-derived",
            "environment_id": "", "supersedes": "",
            "lineage": _json(common_lineage + [override_display, data_display]),
        },
    ]
    sources.sort(key=lambda row: row["source_id"])
    return sources, {
        "family_id": family_id, "generated_id": generated_id, "override_id": override_id,
        "inputs_hash": inputs_hash, "body_hash": body_hash, "override_hash": override_hash,
    }


def build_records(repo: Path) -> dict:
    data_path = repo / "greenfield" / "eldenring" / "data.py"
    override_path = repo / "greenfield" / "region_overrides.tsv"
    locations, stamp = _load_generated_locations(data_path)
    overrides, non_flag_overrides = _load_flag_region_overrides(override_path)
    sources, source = _source_records(repo, data_path, override_path, stamp)
    evidence: list[dict] = []
    claims: list[dict] = []
    matched_override_flags: set[int] = set()

    for location in locations:
        ap_id, flag = location["ap_id"], location["flag"]
        identity_claim_id = f"check:{ap_id}/identity"
        region_claim_id = f"check:{ap_id}/region"
        generated_lineage = _json([
            f"greenfield/gen_inputs.db@{source['inputs_hash']}", "greenfield/gen_data.py",
            f"greenfield/eldenring/data.py@{source['body_hash']}",
        ])
        identity_value = {
            "ap_id": ap_id, "name": location["name"],
            "acquisition": {"namespace": "event_flag", "id": flag},
        }
        identity_evidence_id = (
            f"project:data.py:{source['body_hash'].removeprefix('sha256:')}:"
            f"check-{ap_id}:identity")
        evidence.append({
            "evidence_id": identity_evidence_id, "claim_id": identity_claim_id,
            "source_id": source["generated_id"], "family_id": source["family_id"],
            "stance": "supports", "value": _json(identity_value),
            "citation": f"greenfield/eldenring/data.py:LOCATIONS ap_id={ap_id} flag={flag}",
            "method": "tools/build_v060_current_evidence.py:current_locations",
            "independence_notes":
                "Generated location snapshot; downstream views of data.py are this same family.",
            "valid_from": "current-corpus", "valid_to": "",
            "notes":
                "Current-corpus identity only; this does not independently prove the vanilla acquisition.",
            "lineage": generated_lineage,
        })
        claims.append({
            "claim_id": identity_claim_id, "subject_kind": "check", "subject_id": str(ap_id),
            "claim_kind": "identity", "value": _json(identity_value),
            "status": "single_source", "risk": "medium",
            "adjudication": "current_generated_location",
            "evidence_ids": _json([identity_evidence_id]), "last_reviewed": REVIEW_DATE,
            "review_issue": "#1211",
        })

        region_value = {"region": location["region"]}
        generated_region_evidence_id = (
            f"project:data.py:{source['body_hash'].removeprefix('sha256:')}:"
            f"check-{ap_id}:region")
        region_evidence_ids = [generated_region_evidence_id]
        evidence.append({
            "evidence_id": generated_region_evidence_id, "claim_id": region_claim_id,
            "source_id": source["generated_id"], "family_id": source["family_id"],
            "stance": "supports", "value": _json(region_value),
            "citation":
                f"greenfield/eldenring/data.py:LOCATIONS[{location['region']!r}] ap_id={ap_id}",
            "method": "tools/build_v060_current_evidence.py:current_locations",
            "independence_notes":
                "Current region is generated; its provenance inputs are not independent witnesses.",
            "valid_from": "current-corpus", "valid_to": "",
            "notes": "Current runtime filing, captured as inferred project output.",
            "lineage": generated_lineage,
        })

        ruling = overrides.get(flag)
        contradictory = False
        if ruling is not None:
            matched_override_flags.add(flag)
            ruling_value = {"region": ruling["region"]}
            contradictory = ruling["region"] != location["region"]
            ruling_evidence_id = (
                f"project:region-overrides:{source['override_hash'].removeprefix('sha256:')}:"
                f"line-{ruling['line']}:check-{ap_id}:region")
            region_evidence_ids.append(ruling_evidence_id)
            evidence.append({
                "evidence_id": ruling_evidence_id, "claim_id": region_claim_id,
                "source_id": source["override_id"], "family_id": source["family_id"],
                "stance": "contradicts" if contradictory else "supports",
                "value": _json(ruling_value),
                "citation": f"greenfield/region_overrides.tsv:{ruling['line']} flag={flag}",
                "method": "tools/build_v060_current_evidence.py:flag_region_rulings",
                "independence_notes":
                    "Not independent of data.py: gen_data consumes region_overrides.tsv; "
                    "both records share one family and count once.",
                "valid_from": "current-corpus", "valid_to": "", "notes": ruling["reason"],
                "lineage": _json([
                    f"greenfield/region_overrides.tsv@{source['override_hash']}",
                    "greenfield/gen_data.py",
                    f"greenfield/eldenring/data.py@{source['body_hash']}",
                ]),
            })
        claims.append({
            "claim_id": region_claim_id, "subject_kind": "check", "subject_id": str(ap_id),
            "claim_kind": "region", "value": _json(region_value),
            "status": "conflicted" if contradictory else "inferred", "risk": "high",
            "adjudication": "current_generated_location",
            "evidence_ids": _json(sorted(region_evidence_ids)),
            "last_reviewed": REVIEW_DATE, "review_issue": "#1211",
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

    content = {"sources": sources, "evidence": evidence, "claims": claims}
    content_hash = "sha256:" + hashlib.sha256(_json(content).encode("utf-8")).hexdigest()
    summary = {
        "schema_version": SCHEMA_VERSION, "claims_total": len(claims),
        "by_status": dict(sorted(Counter(row["status"] for row in claims).items())),
        "by_kind": dict(sorted(Counter(row["claim_kind"] for row in claims).items())),
        "by_risk": dict(sorted(Counter(row["risk"] for row in claims).items())),
        "active_conflicts": sum(row["status"] == "conflicted" for row in claims),
        "content_hash": content_hash,
    }
    return {
        **content, "summary": summary,
        "diagnostics": {
            "locations": len(locations), "flag_overrides_total": len(overrides),
            "flag_overrides_matched": len(matched_override_flags),
            "flag_overrides_without_current_check": len(set(overrides) - matched_override_flags),
            "non_flag_overrides_out_of_scope": non_flag_overrides,
        },
    }


def _write_tsv(path: Path, fields: Iterable[str], rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(fields), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_bundle(repo: Path, out_dir: Path) -> dict:
    bundle = build_records(repo)
    _write_tsv(out_dir / "sources.tsv", SOURCE_FIELDS, bundle["sources"])
    _write_tsv(out_dir / "evidence.tsv", EVIDENCE_FIELDS, bundle["evidence"])
    _write_tsv(out_dir / "claims.tsv", CLAIM_FIELDS, bundle["claims"])
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
