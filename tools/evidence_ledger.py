"""Normalized v0.6 check-evidence ledger validation and adjudication.

This module is deliberately AP-free and corpus-free. It validates normalized TSV rows and derives
claim status; adapters and runtime promotion belong to later slices (world#1210).
"""
from __future__ import annotations

import csv
import json
import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

CLAIM_KINDS = {"identity", "region", "access", "detection", "suppression", "sweep_owner", "alternate_acquisition", "description"}
IDENTITY_NAMESPACES = {"item", "lot", "shop", "entity", "flag"}
LIVE_EXACT_BUILD_FIELDS = ("game_version", "dlc_version", "apworld_version", "client_version")
SOURCE_KINDS = {"game_data", "external_reference", "live_testimony", "project_derivation", "ruling"}
STANCES = {"supports", "contradicts", "silent", "ambiguous"}
STATUSES = {"proven", "corroborated", "single_source", "conflicted", "inferred", "unverified"}
RISKS = {"critical", "high", "medium", "low"}
FAMILY_PREFIXES = ("game:param:", "game:emevd:", "game:esd:", "game:msb:", "game:runtime:", "reference:", "testimony:", "project:")
FAMILY_SOURCE_KINDS = {
    "game:": {"game_data"},
    "reference:": {"external_reference"},
    "testimony:": {"live_testimony"},
    "project:": {"project_derivation", "ruling"},
}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})?)?$")
GAME_VERSION = re.compile(r"^\d+(?:\.\d+)*$")

HEADERS = {
    "sources.tsv": ("source_id", "source_kind", "family_id", "title", "game_version", "retrieved_at", "revision", "url_or_path", "license", "environment_id", "supersedes"),
    "evidence.tsv": ("evidence_id", "claim_id", "source_id", "stance", "value", "citation", "method", "independence_notes", "valid_from", "valid_to", "notes"),
    "claims.tsv": ("claim_id", "subject_kind", "subject_id", "claim_kind", "game_version", "value", "status", "risk", "adjudication", "evidence_ids", "last_reviewed", "review_issue", "active", "supersedes"),
    "environments.tsv": ("environment_id", "game_version", "dlc_version", "apworld_version", "client_version", "seed_id", "yaml_options", "launcher", "mods", "regulation", "save_provenance", "reproduction_steps", "result", "artifact_hashes", "artifact_location"),
}

class LedgerError(ValueError):
    pass

def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        expected = HEADERS[path.name]
        if tuple(reader.fieldnames or ()) != expected:
            raise LedgerError(f"{path.name}: header must be {expected!r}")
        # Trailing optional TSV cells may be physically omitted to keep git's whitespace gate
        # meaningful; DictReader represents those as None, canonically normalize them to empty.
        rows = [{key: (value or "") for key, value in row.items()} for row in reader]
    keys = [row[expected[0]] for row in rows]
    if keys != sorted(keys) or len(keys) != len(set(keys)):
        raise LedgerError(f"{path.name}: rows must have unique, deterministic sorted keys")
    return rows

def _json(raw: str, where: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LedgerError(f"{where}: invalid JSON: {exc.msg}") from exc

def _version(raw: str, where: str, *, allow_unknown: bool = False) -> tuple[int, ...] | None:
    if allow_unknown and raw == "unknown":
        return None
    if not GAME_VERSION.match(raw):
        raise LedgerError(f"{where}: invalid game version {raw!r}")
    return tuple(int(part) for part in raw.split("."))

def _evidence_applies(
    claim: dict[str, str], evidence: dict[str, str], source: dict[str, str]
) -> bool:
    claim_version = _version(claim["game_version"], claim["claim_id"])
    source_version = _version(source["game_version"], source["source_id"], allow_unknown=True)
    if source_version is None or source_version != claim_version:
        return False
    if evidence["valid_from"] and claim_version < _version(
        evidence["valid_from"], evidence["evidence_id"]
    ):
        return False
    if evidence["valid_to"] and claim_version > _version(
        evidence["valid_to"], evidence["evidence_id"]
    ):
        return False
    return True

def _typed_value(kind: str, value, where: str) -> None:
    if kind == "region":
        if not isinstance(value, str) or not value.strip(): raise LedgerError(f"{where}: region must be a non-empty string")
    elif kind == "identity":
        if not isinstance(value, dict) or not isinstance(value.get("ap_id"), int) or not isinstance(value.get("flag"), int) or value.get("namespace") not in IDENTITY_NAMESPACES or not isinstance(value.get("id"), int): raise LedgerError(f"{where}: invalid identity value")
    elif kind == "access":
        if not isinstance(value, dict) or value.get("type") not in {"unknown", "all", "any", "flag", "item", "region", "event"}: raise LedgerError(f"{where}: invalid access expression")
    elif kind == "detection":
        if not isinstance(value, dict) or not isinstance(value.get("mechanism"), str) or not isinstance(value.get("flag"), int): raise LedgerError(f"{where}: invalid detection value")
    elif kind == "suppression":
        if not isinstance(value, dict) or value.get("target_type") not in {"lot", "shop", "gesture", "award"} or not isinstance(value.get("target_id"), int): raise LedgerError(f"{where}: invalid suppression value")
    elif kind == "sweep_owner":
        if not isinstance(value, dict) or not isinstance(value.get("trigger_id"), int) or not isinstance(value.get("owner_region"), str): raise LedgerError(f"{where}: invalid sweep_owner value")
    elif kind == "alternate_acquisition":
        if not isinstance(value, dict) or not isinstance(value.get("equivalence_group"), str) or not isinstance(value.get("members"), list) or not value["members"]: raise LedgerError(f"{where}: invalid alternate_acquisition value")
    elif kind == "description":
        if not isinstance(value, dict) or not isinstance(value.get("text"), str) or value.get("precision") not in {"exact", "approximate", "region_only", "unknown"}: raise LedgerError(f"{where}: invalid description value")

def _canon(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

def _citation_names_revision(citation: str, revision: str) -> bool:
    pattern = rf"(?<![A-Za-z0-9]){re.escape(revision)}(?![A-Za-z0-9])"
    return re.search(pattern, citation) is not None

def _requires_environment(source: dict[str, str]) -> bool:
    return (
        source["source_kind"] == "live_testimony"
        or source["family_id"].startswith("game:runtime:")
    )

def _family_matches_source_kind(source: dict[str, str]) -> bool:
    return any(
        source["family_id"].startswith(prefix) and source["source_kind"] in kinds
        for prefix, kinds in FAMILY_SOURCE_KINDS.items()
    )

def _complete_environment(row: dict[str, str]) -> bool:
    required = ("game_version", "dlc_version", "apworld_version", "client_version", "seed_id", "yaml_options", "launcher", "mods", "regulation", "save_provenance", "reproduction_steps", "result", "artifact_hashes", "artifact_location")
    if not all(row[key].strip() for key in required):
        return False
    return all(row[key].strip().lower() != "unknown" for key in LIVE_EXACT_BUILD_FIELDS)

@dataclass(frozen=True)
class Result:
    statuses: dict[str, str]
    counts: dict[str, int]

def summary(directory: Path) -> dict:
    """Public deterministic Phase-A report contract; no baseline/CI policy lives here."""
    result = validate(directory)
    claims = [r for r in _rows(directory / "claims.tsv") if r["active"] == "true"]
    active_ids = {r["claim_id"] for r in claims}
    evidence = [r for r in _rows(directory / "evidence.tsv") if r["claim_id"] in active_ids]
    by_kind: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_risk: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for claim in claims:
        status = result.statuses[claim["claim_id"]]
        by_kind[claim["claim_kind"]][status] += 1
        by_risk[claim["risk"]][status] += 1
    canonical = json.dumps(
        {"claims": claims, "evidence": evidence},
        sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()
    return {
        "schema_version": 1,
        "claims_total": len(claims),
        "by_status": {s: result.counts.get(s, 0) for s in sorted(STATUSES)},
        "by_kind": {k: {s: by_kind[k].get(s, 0) for s in sorted(STATUSES)} for k in sorted(CLAIM_KINDS)},
        "by_risk": {k: {s: by_risk[k].get(s, 0) for s in sorted(STATUSES)} for k in sorted(RISKS)},
        "active_conflicts": sorted(cid for cid, status in result.statuses.items() if status == "conflicted"),
        "content_hash": hashlib.sha256(canonical).hexdigest(),
    }

def derive_status(claim: dict[str, str], evidence: list[dict[str, str]], sources: dict[str, dict[str, str]], environments: dict[str, dict[str, str]]) -> str:
    if not claim["value"]: return "unverified"
    selected = _canon(_json(claim["value"], claim["claim_id"]))
    by_family = defaultdict(list)
    for row in evidence:
        source = sources[row["source_id"]]
        if not _evidence_applies(claim, row, source):
            continue
        if _requires_environment(source) and (
            not source["environment_id"]
            or not _complete_environment(environments[source["environment_id"]])
        ):
            continue
        if row["stance"] in {"supports", "contradicts"}:
            value = _canon(_json(row["value"], row["evidence_id"]))
            by_family[source["family_id"]].append((row["stance"], value, source))
    coherent = []
    for family, positions in by_family.items():
        unique = {(stance, value) for stance, value, _ in positions}
        if len(unique) != 1:
            continue
        stance, value = next(iter(unique))
        coherent.append((family, stance, value, positions[0][2]))
    if any(stance == "contradicts" for _, stance, _, _ in coherent): return "conflicted"
    supported_values = {value for _, stance, value, _ in coherent if stance == "supports"}
    if any(value != selected for value in supported_values): return "conflicted"
    if claim["adjudication"] == "design_ruling": return "proven"
    families = {family for family, stance, value, _ in coherent if stance == "supports" and value == selected}
    if claim["adjudication"] in {"heuristic", "model"}: return "inferred" if families else "unverified"
    if not families: return "unverified"
    direct = any(source["source_kind"] == "game_data" for _, stance, value, source in coherent if stance == "supports" and value == selected)
    if direct and (len(families) >= 2 or claim["risk"] not in {"critical", "high"}): return "proven"
    if len(families) >= 2: return "corroborated"
    return "single_source"

def validate(directory: Path) -> Result:
    tables = {name: _rows(directory / name) for name in HEADERS}
    sources = {r["source_id"]: r for r in tables["sources.tsv"]}; envs = {r["environment_id"]: r for r in tables["environments.tsv"]}
    for sid, row in sources.items():
        if not sid or not row["title"] or not row["game_version"] or not row["revision"] or not row["url_or_path"] or not row["license"]: raise LedgerError(f"{sid or '<blank>'}: incomplete source snapshot")
        _version(row["game_version"], sid, allow_unknown=True)
        if row["retrieved_at"] and not DATE.match(row["retrieved_at"]): raise LedgerError(f"{sid}: invalid retrieved_at")
        if row["source_kind"] not in SOURCE_KINDS: raise LedgerError(f"{sid}: unknown source_kind")
        if not row["family_id"].startswith(FAMILY_PREFIXES): raise LedgerError(f"{sid}: unknown family_id")
        if not _family_matches_source_kind(row):
            raise LedgerError(f"{sid}: source_kind does not match family_id")
        if _requires_environment(row):
            if row["environment_id"] not in envs:
                raise LedgerError(f"{sid}: live/runtime evidence needs a referenced environment")
            environment = envs[row["environment_id"]]
            if row["game_version"] != environment["game_version"]:
                raise LedgerError(f"{sid}: live/runtime game_version must match its environment")
        if row["supersedes"] and row["supersedes"] not in sources: raise LedgerError(f"{sid}: dangling supersedes")
    # Source supersession is a dependency graph; cycles would make 'current' unknowable.
    for sid in sources:
        seen=set(); cur=sid
        while sources[cur]["supersedes"]:
            if cur in seen: raise LedgerError(f"{sid}: source supersedes cycle")
            seen.add(cur); cur=sources[cur]["supersedes"]
    claims = tables["claims.tsv"]; active_keys=set(); claims_by_id={r["claim_id"]:r for r in claims}
    for row in claims:
        cid=row["claim_id"]
        _version(row["game_version"], cid)
        if row["claim_kind"] not in CLAIM_KINDS or row["risk"] not in RISKS or row["status"] not in STATUSES: raise LedgerError(f"{cid}: unknown claim vocabulary")
        if row["active"] not in {"true", "false"}: raise LedgerError(f"{cid}: active must be true or false")
        if row["value"]: _typed_value(row["claim_kind"], _json(row["value"], cid), cid)
        if row["active"] == "true":
            key=(row["subject_kind"],row["subject_id"],row["claim_kind"],row["game_version"])
            if key in active_keys: raise LedgerError(f"{cid}: duplicate active claim")
            active_keys.add(key)
        if row["supersedes"] and row["supersedes"] not in claims_by_id: raise LedgerError(f"{cid}: dangling claim supersedes")
        if row["last_reviewed"] and not DATE.match(row["last_reviewed"]): raise LedgerError(f"{cid}: invalid last_reviewed")
        if row["evidence_ids"] != ",".join(sorted(filter(None,row["evidence_ids"].split(",")))): raise LedgerError(f"{cid}: evidence_ids must be sorted")
    evidence_by_claim=defaultdict(list); evidence_ids=set()
    for row in tables["evidence.tsv"]:
        eid=row["evidence_id"]
        if eid in evidence_ids: raise LedgerError(f"{eid}: duplicate evidence_id")
        evidence_ids.add(eid)
        if row["claim_id"] not in claims_by_id or row["source_id"] not in sources: raise LedgerError(f"{eid}: dangling claim/source")
        if row["stance"] not in STANCES or not row["citation"].strip() or not row["method"].strip(): raise LedgerError(f"{eid}: invalid stance/citation/method")
        valid_from = _version(row["valid_from"], eid) if row["valid_from"] else None
        valid_to = _version(row["valid_to"], eid) if row["valid_to"] else None
        if valid_from and valid_to and valid_from > valid_to:
            raise LedgerError(f"{eid}: valid_from is after valid_to")
        source = sources[row["source_id"]]
        if _requires_environment(source) and not _citation_names_revision(
            row["citation"], source["revision"]
        ):
            raise LedgerError(f"{eid}: live/runtime citation must name source revision")
        if row["stance"] in {"supports", "contradicts"} and not row["value"]: raise LedgerError(f"{eid}: {row['stance']} evidence requires a value")
        if row["value"]: _typed_value(claims_by_id[row["claim_id"]]["claim_kind"], _json(row["value"], eid), eid)
        evidence_by_claim[row["claim_id"]].append(row)
    for cid in claims_by_id:
        seen=set(); cur=cid
        while claims_by_id[cur]["supersedes"]:
            if cur in seen: raise LedgerError(f"{cid}: claim supersedes cycle")
            seen.add(cur); cur=claims_by_id[cur]["supersedes"]
    for row in claims:
        if not row["supersedes"]:
            continue
        predecessor = claims_by_id[row["supersedes"]]
        identity = ("subject_kind", "subject_id", "claim_kind")
        if any(row[field] != predecessor[field] for field in identity):
            raise LedgerError(f"{row['claim_id']}: supersedes a different claim identity")
        if predecessor["active"] != "false":
            raise LedgerError(f"{row['claim_id']}: superseded predecessor must be inactive")
    statuses={}; counts=defaultdict(int)
    for row in claims:
        if row["active"] != "true": continue
        expected_ids=sorted(e["evidence_id"] for e in evidence_by_claim[row["claim_id"]])
        if list(filter(None,row["evidence_ids"].split(","))) != expected_ids: raise LedgerError(f"{row['claim_id']}: evidence_ids do not match rows")
        status=derive_status(row,evidence_by_claim[row["claim_id"]],sources,envs)
        if row["status"] != status: raise LedgerError(f"{row['claim_id']}: status {row['status']} != derived {status}")
        statuses[row["claim_id"]]=status; counts[status]+=1
    return Result(statuses,dict(sorted(counts.items())))
