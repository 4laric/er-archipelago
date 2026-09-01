import csv
import hashlib
import importlib.util
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO / "tools" / "build_v060_current_evidence.py"
SPEC = importlib.util.spec_from_file_location("build_v060_current_evidence", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def test_every_current_check_has_identity_and_region_claims():
    bundle = adapter.build_records(REPO)
    claims_by_subject: dict[str, set[str]] = {}
    for claim in bundle["claims"]:
        claims_by_subject.setdefault(claim["subject_id"], set()).add(claim["claim_kind"])

    assert len(claims_by_subject) == bundle["diagnostics"]["locations"]
    assert all(kinds == {"identity", "region"} for kinds in claims_by_subject.values())


def test_ruling_and_generated_region_are_one_source_family():
    bundle = adapter.build_records(REPO)
    claim = next(
        claim for claim in bundle["claims"]
        if claim["claim_kind"] == "region"
        and len(json.loads(claim["evidence_ids"])) == 2
    )
    evidence_by_id = {row["evidence_id"]: row for row in bundle["evidence"]}
    rows = [evidence_by_id[evidence_id] for evidence_id in json.loads(claim["evidence_ids"])]

    assert len({row["family_id"] for row in rows}) == 1
    assert claim["status"] == "inferred"
    assert any("Not independent" in row["independence_notes"] for row in rows)


def test_identity_names_the_acquisition_id_space_and_all_evidence_has_lineage():
    bundle = adapter.build_records(REPO)
    identity_claims = [row for row in bundle["claims"] if row["claim_kind"] == "identity"]

    assert identity_claims
    assert all(
        json.loads(row["value"])["acquisition"]["namespace"] == "event_flag"
        for row in identity_claims
    )
    assert all(row["citation"] and json.loads(row["lineage"]) for row in bundle["evidence"])


def test_summary_hash_and_references_are_integral():
    bundle = adapter.build_records(REPO)
    content = {key: bundle[key] for key in ("sources", "evidence", "claims")}
    expected_hash = "sha256:" + hashlib.sha256(_canonical(content).encode()).hexdigest()
    source_ids = {row["source_id"] for row in bundle["sources"]}
    claim_ids = {row["claim_id"] for row in bundle["claims"]}

    assert bundle["summary"]["content_hash"] == expected_hash
    assert bundle["summary"]["active_conflicts"] == 0
    assert all(row["source_id"] in source_ids for row in bundle["evidence"])
    assert all(row["claim_id"] in claim_ids for row in bundle["evidence"])


def test_checked_in_bundle_is_byte_deterministic(tmp_path: Path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    adapter.write_bundle(REPO, first)
    adapter.write_bundle(REPO, second)
    checked_in = REPO / "greenfield" / "evidence" / "v060-current"

    for name in ("sources.tsv", "evidence.tsv", "claims.tsv", "summary.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
        assert (first / name).read_bytes() == (checked_in / name).read_bytes()

    claims = _read_tsv(first / "claims.tsv")
    evidence = _read_tsv(first / "evidence.tsv")
    assert len(claims) == 2 * adapter.build_records(REPO)["diagnostics"]["locations"]
    assert len(evidence) >= len(claims)
