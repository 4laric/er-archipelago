#!/usr/bin/env python3
"""Build the v0.6 Phase-1 evidence audit browser from the normalized current ledger.

This is deliberately a reader only. It does not adjudicate claims or change runtime tables. The
small checked-in fixture remains available to tests, while the committed page reads the normalized
current-corpus identity, region, detection, and access ledger.

Run: python3 tools/build_evidence_browser.py [--check] [--out PATH]
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

TOOLS = os.path.dirname(os.path.abspath(__file__))
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
from player_check_review import player_check
from access_dispositions import summary as access_summary
from access_dispositions import validate as validate_access_dispositions

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURRENT = os.path.join(REPO, "greenfield", "evidence", "v060-current")
FIXTURE = os.path.join(REPO, "greenfield", "evidence", "browser_fixture")
OUT_HTML = os.path.join(REPO, "er-archipelago-evidence-browser.html")
ACCESS_FILE = "access_dispositions.tsv"
WIKI_AUDIT = os.path.join(REPO, "greenfield", "evidence", "wiki-audit")
GENERATED_DATA = os.path.join(REPO, "greenfield", "eldenring", "data.py")
GENERATED_LOCATION_TAGS = os.path.join(
    REPO, "greenfield", "eldenring", "location_tags.py")
PROGRESSION_HOST_CONFIDENCE = os.path.join(
    CURRENT, "progression_host_confidence.tsv")
WIKI_SOURCE_HEADERS = (
    "source_id", "publisher", "author", "title", "canonical_url", "revision_url",
    "archived_at", "published_at", "last_modified", "body_sha256", "license",
    "provenance", "patch_applicability", "disposition",
)
WIKI_LEAD_HEADERS = (
    "lead_id", "subject_kind", "subject_id", "claim_kind", "normalized_value",
    "source_ids", "independence_families", "disposition", "game_version",
    "exact_citations", "summary", "limitations",
)
ELDENPEDIA_PAGE_HEADERS = (
    "source_id", "page_id", "revision_id", "revision_timestamp", "revision_sha1",
    "title", "canonical_url", "revision_url", "wiki_region", "ap_regions",
    "notable_loot_links", "disposition",
)
ELDENPEDIA_ACQUISITION_PAGE_HEADERS = (
    "source_id", "page_id", "revision_id", "revision_timestamp", "revision_sha1",
    "title", "canonical_url", "revision_url", "acquisition_rows", "disposition",
)
ELDENPEDIA_COMBATANT_PAGE_HEADERS = (
    "source_id", "page_id", "revision_id", "revision_timestamp", "revision_sha1",
    "title", "canonical_url", "revision_url", "combatant_category", "drop_links",
    "disposition",
)
FEXTRALIFE_PAGE_HEADERS = (
    "source_id", "page_id", "revision_id", "revision_timestamp", "revision_sha1",
    "title", "canonical_url", "revision_url", "ap_item_name", "template_fields", "ap_region",
    "disposition",
)
PROGRESSION_HOST_HEADERS = (
    "check_id", "confidence", "access_status", "external_family_count",
    "external_families", "identity_region_lead_ids", "basis", "limitations",
)
HIGH_VALUE_REVIEW_TAGS = {
    "GreatRune", "KeyItem", "MajorBoss", "Remembrance", "Fragment", "Revered", "Shop",
}

STATUSES = {"proven", "corroborated", "single_source", "conflicted", "inferred", "unverified"}
RISKS = {"critical", "high", "medium", "low"}
BROWSER_CLAIM_KINDS = {"identity", "region", "detection", "access"}
REQUIRED_CHECK_KINDS = {"identity", "region"}
STANCES = {"supports", "contradicts", "silent", "ambiguous"}
HEADERS = {
    "sources.tsv": ("source_id", "source_kind", "family_id", "title", "game_version",
                    "retrieved_at", "revision", "url_or_path", "license", "environment_id",
                    "supersedes"),
    "evidence.tsv": ("evidence_id", "claim_id", "source_id", "stance", "value", "citation",
                     "method", "independence_notes", "valid_from", "valid_to", "notes"),
    "claims.tsv": ("claim_id", "subject_kind", "subject_id", "claim_kind", "game_version",
                   "value", "status", "risk", "adjudication", "evidence_ids", "last_reviewed",
                   "review_issue", "active", "supersedes"),
    "environments.tsv": ("environment_id", "game_version", "dlc_version", "apworld_version",
                         "client_version", "seed_id", "yaml_options", "launcher", "mods",
                         "regulation", "save_provenance", "reproduction_steps", "result",
                         "artifact_hashes", "artifact_location"),
}


def canonical_bytes(contract: dict) -> bytes:
    return json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _rows(path: str, header: tuple[str, ...]) -> list[dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        if tuple(reader.fieldnames or ()) != header:
            raise ValueError(f"{os.path.basename(path)} does not match the normalized #1210 header")
        rows = [{key: (value or "") for key, value in row.items()} for row in reader]
    keys = [row[header[0]] for row in rows]
    if keys != sorted(keys) or len(keys) != len(set(keys)):
        raise ValueError(f"{os.path.basename(path)} keys must be unique and sorted")
    return rows


def normalized_tables(path: str = CURRENT) -> dict[str, list[dict[str, str]]]:
    return {name: _rows(os.path.join(path, name), header) for name, header in HEADERS.items()}


def wiki_lead_files(path: str = WIKI_AUDIT) -> list[str]:
    """Return every normalized external-lead registry in deterministic order."""
    names = {"leads.tsv"}
    names.update(candidate.name for candidate in Path(path).glob("*-check-leads.tsv"))
    return sorted(names)


def wiki_tables(path: str = WIKI_AUDIT) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Read the separately validated lead registry without promoting it into core evidence."""
    def read(name: str, header: tuple[str, ...]) -> list[dict[str, str]]:
        with open(os.path.join(path, name), encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh, delimiter="\t")
            if tuple(reader.fieldnames or ()) != header:
                raise ValueError(f"wiki-audit/{name} does not match its validated header")
            rows = [{key: (value or "") for key, value in row.items()} for row in reader]
        keys = [row[header[0]] for row in rows]
        if len(keys) != len(set(keys)):
            raise ValueError(f"wiki-audit/{name} has duplicate primary ids")
        return rows
    sources = read("sources.tsv", WIKI_SOURCE_HEADERS)
    merchant_revisions = os.path.join(path, "redmaw-merchant-wikigg-revisions.tsv")
    if os.path.exists(merchant_revisions):
        with open(merchant_revisions, encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                sources.append({
                    "source_id": "wiki:eldenpedia:merchant-item:revision-" + row["revision_id"],
                    "publisher": "Eldenpedia", "author": "Eldenpedia contributors",
                    "title": row["canonical_url"].rsplit("/", 1)[-1].replace("_", " "),
                    "canonical_url": row["canonical_url"], "revision_url": row["revision_url"],
                    "archived_at": row["revision_timestamp"], "published_at": "unknown",
                    "last_modified": row["revision_timestamp"],
                    "body_sha256": "mediawiki-revision:" + row["revision_id"],
                    "license": "CC BY-SA 4.0",
                    "provenance": "immutable MediaWiki item-page revision",
                    "patch_applicability": "No game patch stated; cannot establish v1.17 applicability",
                    "disposition": "lead_only",
                })
    eldenpedia_manifest = os.path.join(path, "eldenpedia-location-pages.tsv")
    if os.path.exists(eldenpedia_manifest):
        # The location corpus has page-level immutable revision records rather than pretending 341
        # revisions are independently authored sources.tsv entries. Adapt only the browser fields.
        for row in read("eldenpedia-location-pages.tsv", ELDENPEDIA_PAGE_HEADERS):
            sources.append({
                "source_id": row["source_id"], "publisher": "Eldenpedia",
                "author": "Eldenpedia contributors", "title": row["title"],
                "canonical_url": row["canonical_url"], "revision_url": row["revision_url"],
                "archived_at": row["revision_timestamp"], "published_at": "unknown",
                "last_modified": row["revision_timestamp"],
                "body_sha256": "mediawiki-sha1:" + row["revision_sha1"],
                "license": "CC BY-SA 4.0",
                "provenance": "immutable MediaWiki page revision",
                "patch_applicability": "No game patch stated; cannot establish v1.17 applicability",
                "disposition": row["disposition"],
            })
    acquisition_manifests = (
        "eldenpedia-crystal-tear-pages.tsv",
        "eldenpedia-deathroot-pages.tsv",
        "eldenpedia-golden-seed-pages.tsv",
        "eldenpedia-item-acquisition-pages.tsv",
        "eldenpedia-memory-stone-pages.tsv",
        "eldenpedia-upgrade-material-pages.tsv",
        "eldenpedia-whetblade-pages.tsv",
        "eldenpedia-sacred-tear-pages.tsv",
        "eldenpedia-seedbed-curse-pages.tsv",
        "eldenpedia-shabriri-grape-pages.tsv",
    )
    for manifest_name in acquisition_manifests:
        if not os.path.exists(os.path.join(path, manifest_name)):
            continue
        for row in read(manifest_name, ELDENPEDIA_ACQUISITION_PAGE_HEADERS):
            sources.append({
                "source_id": row["source_id"], "publisher": "Eldenpedia",
                "author": "Eldenpedia contributors", "title": row["title"],
                "canonical_url": row["canonical_url"], "revision_url": row["revision_url"],
                "archived_at": row["revision_timestamp"], "published_at": "unknown",
                "last_modified": row["revision_timestamp"],
                "body_sha256": "mediawiki-sha1:" + row["revision_sha1"],
                "license": "CC BY-SA 4.0",
                "provenance": "immutable MediaWiki item-page revision",
                "patch_applicability": "No game patch stated; cannot establish v1.17 applicability",
                "disposition": row["disposition"],
            })
    combatant_manifest = os.path.join(path, "eldenpedia-combatant-pages.tsv")
    if os.path.exists(combatant_manifest):
        for row in read("eldenpedia-combatant-pages.tsv", ELDENPEDIA_COMBATANT_PAGE_HEADERS):
            sources.append({
                "source_id": row["source_id"], "publisher": "Eldenpedia",
                "author": "Eldenpedia contributors", "title": row["title"],
                "canonical_url": row["canonical_url"], "revision_url": row["revision_url"],
                "archived_at": row["revision_timestamp"], "published_at": "unknown",
                "last_modified": row["revision_timestamp"],
                "body_sha256": "mediawiki-sha1:" + row["revision_sha1"],
                "license": "CC BY-SA 4.0",
                "provenance": "immutable MediaWiki combatant-page revision",
                "patch_applicability": "No game patch stated; cannot establish v1.17 applicability",
                "disposition": row["disposition"],
            })
    fextralife_manifest = os.path.join(path, "fextralife-item-pages.tsv")
    if os.path.exists(fextralife_manifest):
        # As above, one independently authored wiki remains one family even though each exact
        # binding pins its own immutable MediaWiki revision.
        for row in read("fextralife-item-pages.tsv", FEXTRALIFE_PAGE_HEADERS):
            sources.append({
                "source_id": row["source_id"], "publisher": "Fextralife",
                "author": "Fextralife wiki contributors", "title": row["title"],
                "canonical_url": row["canonical_url"], "revision_url": row["revision_url"],
                "archived_at": row["revision_timestamp"], "published_at": "unknown",
                "last_modified": row["revision_timestamp"],
                "body_sha256": "mediawiki-sha1:" + row["revision_sha1"],
                "license": "No content-reuse license asserted by this corpus",
                "provenance": "immutable MediaWiki page revision",
                "patch_applicability": "No game patch stated; cannot establish v1.17 applicability",
                "disposition": row["disposition"],
            })
    fextralife_acquisition = os.path.join(path, "fextralife-acquisition-pages.tsv")
    if os.path.exists(fextralife_acquisition):
        for row in read("fextralife-acquisition-pages.tsv", ELDENPEDIA_ACQUISITION_PAGE_HEADERS):
            sources.append({
                "source_id": row["source_id"], "publisher": "Fextralife",
                "author": "Fextralife wiki contributors", "title": row["title"],
                "canonical_url": row["canonical_url"], "revision_url": row["revision_url"],
                "archived_at": row["revision_timestamp"], "published_at": "unknown",
                "last_modified": row["revision_timestamp"],
                "body_sha256": "mediawiki-sha1:" + row["revision_sha1"],
                "license": "No content-reuse license asserted by this corpus",
                "provenance": "immutable MediaWiki acquisition-page revision",
                "patch_applicability": "No game patch stated; cannot establish v1.17 applicability",
                "disposition": row["disposition"],
            })
    leads = [row for name in wiki_lead_files(path)
             for row in read(name, WIKI_LEAD_HEADERS)]
    lead_ids = [row["lead_id"] for row in leads]
    if len(lead_ids) != len(set(lead_ids)):
        raise ValueError("wiki-audit lead registries have duplicate primary ids across files")
    return sources, leads


def graduation(status: str, risk: str) -> str:
    if status == "conflicted":
        return "Resolve the active contradiction with a reproducible source or explicit design ruling; do not hide the losing evidence."
    if status == "inferred":
        return "Add an exact first-party citation and an independent corroborating family; the heuristic cannot promote itself."
    if status == "single_source":
        return "Add a genuinely independent evidence family. A second projection of the same source does not count."
    if status == "unverified":
        return "Add the first usable, exactly cited source for this claim."
    if risk in {"critical", "high"} and status != "proven":
        return "Add the direct authority required for a high-risk claim and resolve every active contradiction."
    return "Retain the exact citations and family independence if this claim changes."


def location_names(path: str = GENERATED_DATA) -> dict[int, str]:
    """Read generated check names without importing the Archipelago world."""
    module = ast.parse(Path(path).read_text(encoding="utf-8"), filename=path)
    assignment = next(
        (node for node in module.body if isinstance(node, ast.Assign)
         and any(isinstance(target, ast.Name) and target.id == "LOCATIONS"
                 for target in node.targets)),
        None,
    )
    if assignment is None:
        raise ValueError("generated data has no LOCATIONS assignment")
    regions = ast.literal_eval(assignment.value)
    names: dict[int, str] = {}
    for rows in regions.values():
        for name, check_id, _flag in rows:
            if check_id in names and names[check_id] != name:
                raise ValueError(f"generated data has conflicting names for check {check_id}")
            names[check_id] = name
    return names


def location_tags(path: str = GENERATED_LOCATION_TAGS) -> dict[int, list[str]]:
    """Read generated check-family tags without importing the Archipelago world."""
    module = ast.parse(Path(path).read_text(encoding="utf-8"), filename=path)
    assignment = next(
        (node for node in module.body if isinstance(node, ast.Assign)
         and any(isinstance(target, ast.Name) and target.id == "LOCATION_TAGS"
                 for target in node.targets)),
        None,
    )
    if assignment is None:
        raise ValueError("generated location tags have no LOCATION_TAGS assignment")
    raw = ast.literal_eval(assignment.value)
    tags: dict[int, list[str]] = {}
    for check_id, values in raw.items():
        if not isinstance(check_id, int) or not isinstance(values, list) or not all(
            isinstance(value, str) and value for value in values
        ):
            raise ValueError("generated location tags have an invalid row")
        if len(values) != len(set(values)):
            raise ValueError(f"generated location tags repeat a tag for check {check_id}")
        tags[check_id] = sorted(values)
    return tags


def progression_host_confidence(path: str = PROGRESSION_HOST_CONFIDENCE) -> dict[int, dict]:
    """Read the generated host-confidence census used to target human review."""
    rows = _rows(path, PROGRESSION_HOST_HEADERS)
    result = {}
    for row in rows:
        check_id = int(row["check_id"])
        result[check_id] = {
            "confidence": row["confidence"],
            "external_family_count": int(row["external_family_count"]),
            "basis": row["basis"],
        }
    return result


def transform(
    tables: dict[str, list[dict[str, str]]],
    access_rows: list[dict[str, str]] | None = None,
    external_sources: list[dict[str, str]] | None = None,
    external_leads: list[dict[str, str]] | None = None,
    check_names: dict[int, str] | None = None,
    check_tags: dict[int, list[str]] | None = None,
    host_confidence: dict[int, dict] | None = None,
) -> dict:
    """Explicit normalized-TSV -> browser payload boundary; no status is derived here."""
    sources = {row["source_id"]: row for row in tables["sources.tsv"]}
    evidence_by_claim: dict[str, list[dict]] = {}
    seen_evidence = set()
    for row in tables["evidence.tsv"]:
        if row["evidence_id"] in seen_evidence or row["source_id"] not in sources:
            raise ValueError(f"duplicate or dangling evidence: {row['evidence_id']}")
        if row["stance"] not in STANCES or not row["citation"].strip():
            raise ValueError(f"evidence needs a valid stance and exact citation: {row['evidence_id']}")
        seen_evidence.add(row["evidence_id"])
        source = sources[row["source_id"]]
        evidence_by_claim.setdefault(row["claim_id"], []).append({
            "evidence_id": row["evidence_id"], "family_id": source["family_id"],
            "source_id": row["source_id"], "source_title": source["title"],
            "source_version": source["game_version"], "stance": row["stance"],
            "value": json.loads(row["value"]) if row["value"] else None,
            "citation": row["citation"], "method": row["method"],
            "lineage": row["independence_notes"],
        })
    by_check: dict[int, list[dict]] = {}
    seen_claims = set()
    for row in tables["claims.tsv"]:
        if row["active"] != "true":
            continue
        claim_id, kind = row["claim_id"], row["claim_kind"]
        if row["subject_kind"] != "check" or kind not in BROWSER_CLAIM_KINDS:
            raise ValueError(f"Phase 1 browser does not support this active claim: {claim_id}")
        check_id = int(row["subject_id"])
        if claim_id != f"check:{check_id}/{kind}" or claim_id in seen_claims:
            raise ValueError(f"unstable or duplicate claim_id: {claim_id}")
        if row["status"] not in STATUSES or row["risk"] not in RISKS:
            raise ValueError(f"closed vocabulary violation in {claim_id}")
        evidence = evidence_by_claim.get(claim_id, [])
        expected = ",".join(sorted(e["evidence_id"] for e in evidence))
        if row["evidence_ids"] != expected:
            raise ValueError(f"{claim_id}: evidence_ids do not match normalized evidence rows")
        seen_claims.add(claim_id)
        by_check.setdefault(check_id, []).append({
            "claim_id": claim_id, "claim_kind": kind, "value": json.loads(row["value"]),
            "status": row["status"], "risk": row["risk"],
            "last_reviewed": row["last_reviewed"], "review_issue": row["review_issue"],
            "graduation": graduation(row["status"], row["risk"]), "evidence": evidence,
        })
    dispositions_by_check: dict[int, list[dict[str, str]]] = {}
    for row in access_rows or []:
        dispositions_by_check.setdefault(int(row["check_id"]), []).append({
            key: row[key] for key in (
                "access_claim_id", "disposition", "risk", "option_set", "reason",
                "review_issue", "owner", "review_by",
            )
        })
    external_source_by_id = {row["source_id"]: row for row in external_sources or []}
    if any(row["disposition"] != "lead_only" for row in external_source_by_id.values()):
        raise ValueError("external source crossed the lead-only boundary")
    external_by_check: dict[int, list[dict]] = {}
    unbound_external = []
    for row in external_leads or []:
        # Check-lead tables use semicolons because citations and normalized values may contain
        # commas. Accept the original comma separator too so older audit fixtures remain readable.
        source_ids = [source_id.strip() for source_id in re.split(r"[;,]", row["source_ids"])
                      if source_id.strip()]
        if row["disposition"] != "lead_only" or row["game_version"] != "unknown":
            raise ValueError(f"external lead crossed the lead-only boundary: {row['lead_id']}")
        if not source_ids or not set(source_ids) <= set(external_source_by_id):
            raise ValueError(f"external lead has dangling sources: {row['lead_id']}")
        lead = {
            "lead_id": row["lead_id"], "subject_kind": row["subject_kind"],
            "subject_id": row["subject_id"], "claim_kind": row["claim_kind"],
            "value": json.loads(row["normalized_value"]),
            "disposition": row["disposition"], "game_version": row["game_version"],
            "families": [family.strip() for family in
                         re.split(r"[;,]", row["independence_families"])
                         if family.strip()],
            "citations": row["exact_citations"], "summary": row["summary"],
            "limitations": row["limitations"],
            "sources": [{key: external_source_by_id[source_id][key] for key in (
                "source_id", "publisher", "author", "title", "revision_url",
                "patch_applicability", "license",
            )} for source_id in source_ids],
        }
        if row["subject_kind"] == "check":
            try:
                external_by_check.setdefault(int(row["subject_id"]), []).append(lead)
            except ValueError as exc:
                raise ValueError(f"external check subject is not an AP id: {row['lead_id']}") from exc
        else:
            unbound_external.append(lead)
    if host_confidence is not None and set(host_confidence) != set(by_check):
        raise ValueError("progression host confidence population differs from active checks")
    checks = []
    for check_id, claims in sorted(by_check.items()):
        kinds = {c["claim_kind"] for c in claims}
        if len(kinds) != len(claims) or not REQUIRED_CHECK_KINDS <= kinds:
            raise ValueError(f"Phase 1 check {check_id} needs unique identity and region claims")
        dispositions = dispositions_by_check.get(check_id, [])
        tags = (check_tags or {}).get(check_id, [])
        confidence = (host_confidence or {}).get(check_id)
        review_reasons = []
        if any(claim["status"] == "conflicted" for claim in claims):
            review_reasons.append("active evidence conflict")
        if any(row["disposition"] == "unresolved" and row["access_claim_id"]
               for row in dispositions):
            review_reasons.append("access evidence exists but still needs a ruling")
        if confidence and confidence["confidence"] == "hold":
            family_count = confidence["external_family_count"]
            if family_count == 1:
                review_reasons.append("one external family; needs independent corroboration")
            elif family_count == 0 and HIGH_VALUE_REVIEW_TAGS.intersection(tags):
                review_reasons.append("high-value check class with no external corroboration")
        checks.append({
            "check_id": check_id,
            "name": (check_names or {}).get(check_id, f"Check {check_id}"),
            "tags": tags,
            "claims": sorted(claims, key=lambda c: c["claim_kind"]),
            "access_dispositions": dispositions,
            "external_leads": sorted(external_by_check.pop(check_id, []), key=lambda row: row["lead_id"]),
            "needs_review": bool(review_reasons),
            "review_reasons": review_reasons,
            "release_blocker": any(
                row["disposition"] == "unresolved" and row["risk"] in {"critical", "high"}
                for row in dispositions
            ),
        })
    if not checks:
        raise ValueError("normalized fixture has no active Phase 1 claims")
    if external_by_check:
        missing = ", ".join(map(str, sorted(external_by_check)))
        raise ValueError(f"external leads name checks absent from the current ledger: {missing}")
    return {
        "schema": "evidence-browser-payload-v1", "checks": checks,
        "unbound_external_leads": sorted(unbound_external, key=lambda row: row["lead_id"]),
    }


def ledger_hash(path: str = CURRENT, wiki_path: str | None = None) -> str:
    digest = hashlib.sha256()
    for name in sorted(HEADERS):
        digest.update(name.encode() + b"\0")
        with open(os.path.join(path, name), "rb") as fh:
            digest.update(fh.read())
    access_path = os.path.join(path, ACCESS_FILE)
    if os.path.exists(access_path):
        digest.update(ACCESS_FILE.encode() + b"\0")
        with open(access_path, "rb") as fh:
            digest.update(fh.read())
    if os.path.abspath(path) == os.path.abspath(CURRENT):
        for extra in ("greenfield/nearest_grace.tsv",
                      "greenfield/evidence/wiki-audit/bulk-check-review.json"):
            digest.update(extra.encode() + b"\0")
            digest.update((Path(REPO) / extra).read_bytes())
        digest.update(b"greenfield/eldenring/location_tags.py\0")
        with open(GENERATED_LOCATION_TAGS, "rb") as fh:
            digest.update(fh.read())
        digest.update(b"greenfield/evidence/v060-current/progression_host_confidence.tsv\0")
        with open(PROGRESSION_HOST_CONFIDENCE, "rb") as fh:
            digest.update(fh.read())
    if wiki_path:
        names = ["sources.tsv", *wiki_lead_files(wiki_path)]
        if os.path.exists(os.path.join(wiki_path, "eldenpedia-location-pages.tsv")):
            names.append("eldenpedia-location-pages.tsv")
        if os.path.exists(os.path.join(wiki_path, "eldenpedia-combatant-pages.tsv")):
            names.append("eldenpedia-combatant-pages.tsv")
        if os.path.exists(os.path.join(wiki_path, "fextralife-item-pages.tsv")):
            names.append("fextralife-item-pages.tsv")
        if os.path.exists(os.path.join(wiki_path, "fextralife-acquisition-pages.tsv")):
            names.append("fextralife-acquisition-pages.tsv")
        for name in sorted(names):
            digest.update(("wiki-audit/" + name).encode() + b"\0")
            with open(os.path.join(wiki_path, name), "rb") as fh:
                digest.update(fh.read())
    return "sha256:" + digest.hexdigest()


def load_ledger(path: str = CURRENT, wiki_path: str | None = None) -> dict:
    if wiki_path is None and os.path.abspath(path) == os.path.abspath(CURRENT):
        wiki_path = WIKI_AUDIT
    dispositions_path = os.path.join(path, ACCESS_FILE)
    dispositions = None
    census = None
    if os.path.exists(dispositions_path):
        dispositions = validate_access_dispositions(
            Path(path), Path(dispositions_path)
        )
        census = access_summary(
            Path(path), Path(dispositions_path)
        )
    external_sources = external_leads = None
    if wiki_path:
        external_sources, external_leads = wiki_tables(wiki_path)
    contract = transform(
        normalized_tables(path), dispositions, external_sources, external_leads,
        location_names() if os.path.abspath(path) == os.path.abspath(CURRENT) else None,
        location_tags() if os.path.abspath(path) == os.path.abspath(CURRENT) else None,
        progression_host_confidence()
        if os.path.abspath(path) == os.path.abspath(CURRENT) else None,
    )
    if os.path.abspath(path) == os.path.abspath(CURRENT):
        contract["bulk_review"] = json.loads(
            (Path(WIKI_AUDIT) / "bulk-check-review.json").read_text(encoding="utf-8"))
        with (Path(REPO) / "greenfield/nearest_grace.tsv").open(encoding="utf-8", newline="") as handle:
            graces = {int(row["flag"]): row["grace_name"] for row in csv.DictReader(
                (line for line in handle if not line.startswith("#")), delimiter="	")}
        confidence = progression_host_confidence()
    else:
        contract["bulk_review"] = {"observations": [], "summary": {}}
        graces, confidence = {}, {}
    for check in contract["checks"]:
        identity = next(c for c in check["claims"] if c["claim_kind"] == "identity")
        check["player"] = player_check(check, confidence.get(check["check_id"]),
                                       graces.get(identity["value"].get("flag"), ""))
    contract["access_summary"] = census
    contract["dataset"] = os.path.relpath(path, REPO).replace(os.sep, "/")
    contract["inputs_hash"] = ledger_hash(path, wiki_path)
    return contract


def load_fixture(path: str = FIXTURE) -> dict:
    """Load the deliberately small conflict/family fixture used by focused tests."""
    return load_ledger(path)


def render(contract: dict) -> str:
    payload = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")
    stamp = contract["inputs_hash"]
    html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="evidence-inputs-hash" content="{stamp}">
<title>ER Archipelago player reviews</title>
<style>
[hidden]{{display:none!important}}
:root{{--bg:#0b1118;--panel:#121b25;--panel2:#182431;--line:#2b3b4d;--text:#e8eef5;--muted:#9fb0c2;--gold:#e8bd62;--red:#ff786f;--green:#75d69c;--blue:#75baff}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 system-ui,sans-serif}}
header{{padding:24px clamp(18px,4vw,54px);border-bottom:1px solid var(--line);background:linear-gradient(120deg,#152537,#0b1118)}}
h1{{margin:0 0 6px;font-size:clamp(24px,4vw,38px)}} h2,h3{{margin:.4rem 0}} .muted{{color:var(--muted)}} code{{color:#b9d9ff}}
.layout{{display:grid;grid-template-columns:minmax(330px,42%) 1fr;min-height:calc(100vh - 126px)}}
.queue,.detail{{padding:20px;overflow:auto}} .queue{{border-right:1px solid var(--line)}}
.filters{{display:grid;grid-template-columns:2fr repeat(9,1fr);gap:8px;position:sticky;top:0;background:var(--bg);padding-bottom:14px;z-index:2}}
input,select,textarea,button{{width:100%;padding:9px;border:1px solid var(--line);border-radius:7px;background:var(--panel);color:var(--text)}} button{{cursor:pointer}}
.row{{display:grid;grid-template-columns:1fr auto;gap:8px;padding:12px;margin:7px 0;border:1px solid var(--line);border-radius:9px;background:var(--panel);cursor:pointer}}
.row:hover,.row.active{{border-color:var(--blue);background:var(--panel2)}} .badges{{display:flex;gap:5px;flex-wrap:wrap;margin-top:5px}}
.badge{{font-size:12px;padding:2px 7px;border-radius:20px;border:1px solid var(--line)}} .conflicted,.contradicts{{color:var(--red);border-color:#81433f}} .proven,.supports{{color:var(--green)}}
.high,.critical{{color:#ffb36b}} .questions{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:14px 0}}
.answer,.family{{padding:13px;border:1px solid var(--line);border-radius:9px;background:var(--panel)}} .answer h3{{font-size:14px;color:var(--gold)}}
.family{{margin:9px 0}} .evidence{{padding:10px 0;border-top:1px solid var(--line)}} .citation{{padding:7px;background:#0b141e;border-radius:5px;overflow-wrap:anywhere}}
.alert{{padding:10px;border:1px solid #81433f;background:#2a1718;color:#ffd2cf;border-radius:7px;margin:10px 0}}
.external{{border-color:#66562f;background:#211d14}} .external a{{color:var(--blue)}} .lead{{margin:9px 0;padding:12px;border:1px solid #66562f;border-radius:9px;background:#18170f}}
.toolbar{{display:flex;gap:8px;align-items:center}} .toolbar button{{width:auto}} .empty{{padding:20px;color:var(--muted)}}
.reviewform{{margin:14px 0;padding:14px;border:1px solid var(--gold);border-radius:9px;background:#19170f}}
.reviewgrid{{display:grid;grid-template-columns:1fr 1fr;gap:9px}} .reviewform label{{display:block;color:var(--muted);font-size:12px;margin-bottom:3px}}
.reviewform textarea{{min-height:76px;resize:vertical}} .reviewactions{{display:flex;gap:8px;margin-top:10px}} .reviewactions button{{width:auto}}
@media(max-width:900px){{.layout{{display:block}}.queue{{border-right:0;border-bottom:1px solid var(--line)}}.filters{{grid-template-columns:1fr 1fr}}.questions{{grid-template-columns:1fr}}}}
</style></head><body>
<div id="maintainerView" hidden><header><h1>Evidence audit · Phase 1</h1><div class="muted">Identity, region, detection, and access claims from <code>{contract['dataset']}</code> · reader only · <code>{stamp}</code></div></header>
<main class="layout"><section class="queue"><div class="filters">
<input id="q" aria-label="Search" placeholder="Search check, claim, value, citation">
<select id="status" aria-label="Status"><option value="">All statuses</option></select>
<select id="risk" aria-label="Risk"><option value="">All risks</option></select>
<select id="kind" aria-label="Claim kind"><option value="">All claim kinds</option></select>
<select id="tag" aria-label="Check class"><option value="">All check classes</option></select>
<select id="review" aria-label="Human review need"><option value="">All review states</option><option value="yes">Needs review</option><option value="no">No targeted review</option></select>
<select id="family" aria-label="Evidence family"><option value="">All families</option></select>
<select id="disposition" aria-label="Access disposition"><option value="">All dispositions</option></select>
<select id="external" aria-label="External leads"><option value="">All external coverage</option><option value="yes">Has external leads</option><option value="no">No external leads</option></select>
<select id="blocker" aria-label="Release blocker"><option value="">All blocker states</option><option value="yes">Release blockers</option><option value="no">Not blockers</option></select></div>
<div class="toolbar"><strong id="count"></strong><span class="muted">risk-ranked audit queue</span><button id="playerQueue">Player review queue</button><button id="exportQueue">Export filtered TSV</button></div><div id="rows"></div></section>
<section class="detail" id="detail"><p class="empty">Select a claim to inspect its evidence.</p></section></main>
<section class="detail" id="unbound"><h2>Unbound external leads</h2><p class="muted">Route, boss, and game-item leads stay here until an exact check mapping is justified. They are leads only and do not change claim status or runtime logic.</p><div id="unboundRows"></div></section>
</div>
<script id="evidence-payload" type="application/json">{payload}</script>
<script>
const DATA=JSON.parse(document.getElementById('evidence-payload').textContent);
const claims=DATA.checks.flatMap(c=>c.claims.map(x=>({{...x,check_id:c.check_id,check_name:c.name,tags:c.tags,needs_review:c.needs_review,review_reasons:c.review_reasons,access_dispositions:c.access_dispositions,external_leads:c.external_leads,release_blocker:c.release_blocker}})));
const riskRank={{critical:0,high:1,medium:2,low:3}}, statusRank={{conflicted:0,unverified:1,inferred:2,single_source:3,corroborated:4,proven:5}};
const els=Object.fromEntries(['q','status','risk','kind','tag','review','family','disposition','external','blocker','rows','count','detail','playerQueue','exportQueue','unboundRows'].map(x=>[x,document.getElementById(x)]));
function values(key){{return [...new Set(claims.flatMap(c=>key==='tag'?c.tags:key==='family'?c.evidence.map(e=>e.family_id):key==='disposition'?c.access_dispositions.map(d=>d.disposition):[c[key]]))].sort()}}
function options(el,vals){{for(const v of vals){{const o=document.createElement('option');o.value=v;o.textContent=v;el.append(o)}}}}
options(els.status,values('status'));options(els.risk,values('risk'));options(els.kind,values('claim_kind'));options(els.tag,values('tag'));options(els.family,values('family'));options(els.disposition,values('disposition'));
function readHash(){{const p=new URLSearchParams(location.hash.slice(1));for(const k of ['q','status','risk','kind','tag','review','family','disposition','external','blocker'])if(p.has(k))els[k].value=p.get(k);return p.get('claim')||''}}
function hashParams(selected){{const p=new URLSearchParams();p.set('mode','maintainer');for(const k of ['q','status','risk','kind','tag','review','family','disposition','external','blocker'])if(els[k].value)p.set(k,els[k].value);if(selected)p.set('claim',selected);return p}}
function writeHash(selected){{history.replaceState(null,'','#'+hashParams(selected).toString())}}
function claimPermalink(c){{const url=new URL(location.href);url.hash=hashParams(c.claim_id).toString();return url.toString()}}
function playerPrompt(c){{const access=claims.find(x=>x.check_id===c.check_id&&x.claim_kind==='access');const region=claims.find(x=>x.check_id===c.check_id&&x.claim_kind==='region');return `ER check review\n${{c.check_name}}\nCheck ID: ${{c.check_id}}\nCurrent region: ${{region?JSON.stringify(region.value):'unknown'}}\nCurrent access rule: ${{access?JSON.stringify(access.value):'unresolved'}}\n\nCan you confirm where this is and everything required to collect it? Please include required regions, bosses, keys, quests or NPC state; your game/AP version; and a screenshot or log if available.\n\n${{claimPermalink(c)}}`}}
function reviewAnswer(c){{
 const val=id=>(document.getElementById(id)?.value||'').trim();
 const region=claims.find(x=>x.check_id===c.check_id&&x.claim_kind==='region');
 const access=claims.find(x=>x.check_id===c.check_id&&x.claim_kind==='access');
 return `## Player evidence review\n\n**Check:** ${{c.check_name}}\n**Check ID:** ${{c.check_id}}\n**Claim:** ${{c.claim_id}}\n**Verdict:** ${{val('rvVerdict')||'not specified'}}\n**Game / AP version:** ${{val('rvVersion')||'not specified'}}\n\n### Player finding\n\n**Actual region:** ${{val('rvRegion')||'not specified'}}\n\n**Everything required to collect it:**\n${{val('rvAccess')||'not specified'}}\n\n**Evidence or reproduction:**\n${{val('rvEvidence')||'not specified'}}\n\n### Current catalog entry\n\n**Region:** ${{region?JSON.stringify(region.value):'unknown'}}\n**Access:** ${{access?JSON.stringify(access.value):'unresolved'}}\n**Why review was requested:** ${{c.review_reasons.join(' | ')||'manual review'}}\n\n${{claimPermalink(c)}}`;
}}
function tsvCell(value){{let s=String(value??'').replace(/[\\t\\r\\n]+/g,' ');if(/^[=+\\-@]/.test(s))s="'"+s;return s}}
function exportRows(rows){{const columns=['claim_id','check_id','check_classes','needs_review','review_reasons','claim_kind','status','risk','value','evidence_families','review_issue','access_dispositions','option_sets','release_blocker','external_lead_count','external_lead_ids','external_claim_kinds','external_families','external_game_versions','external_dispositions','disposition_reasons','disposition_review_issues','permalink'];const body=rows.map(c=>[c.claim_id,c.check_id,c.tags.join(','),c.needs_review,c.review_reasons.join(' | '),c.claim_kind,c.status,c.risk,JSON.stringify(c.value),new Set(c.evidence.map(e=>e.family_id)).size,c.review_issue,c.access_dispositions.map(d=>d.disposition).join(','),c.access_dispositions.map(d=>d.option_set).join(','),c.release_blocker,c.external_leads.length,c.external_leads.map(l=>l.lead_id).join(','),c.external_leads.map(l=>l.claim_kind).join(','),[...new Set(c.external_leads.flatMap(l=>l.families))].sort().join(','),[...new Set(c.external_leads.map(l=>l.game_version))].sort().join(','),[...new Set(c.external_leads.map(l=>l.disposition))].sort().join(','),c.access_dispositions.map(d=>d.reason).filter(Boolean).join(' | '),c.access_dispositions.map(d=>d.review_issue).filter(Boolean).join(','),claimPermalink(c)].map(tsvCell).join('\\t'));return [columns.join('\\t'),...body].join('\\n')+'\\n'}}
function downloadQueue(rows){{const blob=new Blob([exportRows(rows)],{{type:'text/tab-separated-values;charset=utf-8'}});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='er-evidence-audit.tsv';a.click();URL.revokeObjectURL(url)}}
function text(c){{return JSON.stringify(c).toLowerCase()}}
function filtered(){{const q=els.q.value.trim().toLowerCase();return claims.filter(c=>(!q||text(c).includes(q))&&(!els.status.value||c.status===els.status.value)&&(!els.risk.value||c.risk===els.risk.value)&&(!els.kind.value||c.claim_kind===els.kind.value)&&(!els.tag.value||c.tags.includes(els.tag.value))&&(!els.review.value||(c.needs_review?'yes':'no')===els.review.value)&&(!els.family.value||c.evidence.some(e=>e.family_id===els.family.value))&&(!els.disposition.value||c.access_dispositions.some(d=>d.disposition===els.disposition.value))&&(!els.external.value||(c.external_leads.length?'yes':'no')===els.external.value)&&(!els.blocker.value||(c.release_blocker?'yes':'no')===els.blocker.value)).sort((a,b)=>Number(b.needs_review)-Number(a.needs_review)||riskRank[a.risk]-riskRank[b.risk]||statusRank[a.status]-statusRank[b.status]||a.check_id-b.check_id||a.claim_kind.localeCompare(b.claim_kind))}}
function badge(s,extra=''){{return `<span class="badge ${{s}} ${{extra}}">${{escapeHtml(s)}}</span>`}}
function escapeHtml(s){{return String(s).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]))}}
function leadHtml(lead){{const sources=lead.sources.map(s=>`<li><a href="${{escapeHtml(s.revision_url)}}" rel="noreferrer">${{escapeHtml(s.title)}}</a> · ${{escapeHtml(s.publisher)}} · ${{escapeHtml(s.patch_applicability)}}<br><code>${{escapeHtml(s.source_id)}}</code></li>`).join('');return `<div class="lead external"><div class="badges">${{badge(lead.disposition)}}${{badge(lead.game_version)}}${{badge(lead.claim_kind)}}</div><strong>${{escapeHtml(lead.summary)}}</strong><div>Subject: <code>${{escapeHtml(lead.subject_kind+':'+lead.subject_id)}}</code> · value <code>${{escapeHtml(JSON.stringify(lead.value))}}</code></div><div>Independent source families: ${{escapeHtml(lead.families.join(', '))}}</div><div class="citation">Immutable citations: ${{escapeHtml(lead.citations)}}</div><div class="muted">Limitations: ${{escapeHtml(lead.limitations)}}<br><code>${{escapeHtml(lead.lead_id)}}</code></div><ul>${{sources}}</ul></div>`}}
function renderUnbound(){{els.unboundRows.innerHTML=DATA.unbound_external_leads.length?DATA.unbound_external_leads.map(leadHtml).join(''):'<p class="empty">No unbound external leads in this build.</p>'}}
function show(c){{
 const families=Map.groupBy?Map.groupBy(c.evidence,e=>e.family_id):c.evidence.reduce((m,e)=>(m.set(e.family_id,[...(m.get(e.family_id)||[]),e]),m),new Map());
 const contradictions=c.evidence.filter(e=>e.stance==='contradicts'||e.stance==='ambiguous');
 const identity=claims.find(x=>x.check_id===c.check_id&&x.claim_kind==='identity');
 const region=claims.find(x=>x.check_id===c.check_id&&x.claim_kind==='region');
 const why=identity?`Identity ${{escapeHtml(JSON.stringify(identity.value))}} · ${{identity.status}}`:'No identity claim in this phase.';
 const access=claims.find(x=>x.check_id===c.check_id&&x.claim_kind==='access');
 const reach=access?`Access claim: ${{escapeHtml(JSON.stringify(access.value))}} (${{escapeHtml(access.status)}}).`:region?`No access evidence exists for this check. The region claim files it in ${{escapeHtml(JSON.stringify(region.value))}}, but ownership is not proof that the player can reach or collect it.`:'No access evidence exists for this check.';
 const dispositionRows=c.access_dispositions.map(d=>`<div class="answer"><strong>${{escapeHtml(d.disposition)}}</strong> · option <code>${{escapeHtml(d.option_set)}}</code> · ${{escapeHtml(d.risk)}}${{d.reason?`<div>${{escapeHtml(d.reason)}}</div>`:''}}${{d.review_issue?`<div class="muted">review ${{escapeHtml(d.review_issue)}}${{d.owner?' · '+escapeHtml(d.owner):''}}${{d.review_by?' · by '+escapeHtml(d.review_by):''}}</div>`:''}}</div>`).join('');
 const disagree=contradictions.length?contradictions.map(e=>`${{e.family_id}}: ${{e.citation}}`).join(' · '):'No active contradiction is represented in this ledger.';
 let html=`<div class="toolbar"><div><h2>${{escapeHtml(c.check_name)}}</h2><div class="muted">${{c.claim_id}} · check ${{c.check_id}}</div></div><button id="copyReview">Copy player question</button><button id="copy">Copy permalink</button></div>`;
 html+=`<div class="badges">${{badge(c.claim_kind)}}${{badge(c.status)}}${{badge(c.risk)}}${{c.tags.map(x=>badge(x)).join('')}}${{c.needs_review?badge('needs review','critical'):''}}</div>`;
 if(c.needs_review)html+=`<div class="alert"><strong>Human review requested.</strong> ${{escapeHtml(c.review_reasons.join(' · '))}}</div>`;
 if(c.release_blocker)html+=`<div class="alert"><strong>v0.6 release blocker.</strong> This check still has an unresolved critical/high access disposition.</div>`;
 if(c.status==='conflicted')html+=`<div class="alert"><strong>Conflict is active.</strong> Contradicting evidence remains visible below; the current value does not erase it.</div>`;
 html+=`<div class="reviewform"><h3>Submit what you know</h3><p class="muted">A precise correction, route, or independent confirmation is useful. Nothing leaves your browser until you choose an action below.</p><div class="reviewgrid"><div><label for="rvVerdict">Does the catalog look right?</label><select id="rvVerdict"><option value="">Choose</option><option>Confirm</option><option>Correction needed</option><option>Unsure, but I can add route evidence</option></select></div><div><label for="rvVersion">Game / AP version</label><input id="rvVersion" placeholder="e.g. game 2.1.3, AP 0.5.7"></div><div><label for="rvRegion">Actual region</label><input id="rvRegion" placeholder="Confirm or correct the region"></div><div><label for="rvAccess">Required locks, bosses, keys, quests, or NPC state</label><textarea id="rvAccess" placeholder="List everything needed to collect this check"></textarea></div></div><label for="rvEvidence">Evidence or reproduction</label><textarea id="rvEvidence" placeholder="What you observed; wiki/walkthrough link; screenshot or log availability"></textarea><div class="reviewactions"><button id="copyAnswer">Copy answer for Discord</button><button id="openReview">Open prefilled GitHub issue</button></div><div id="reviewStatus" class="muted"></div></div>`;
 html+=`<div class="questions"><div class="answer"><h3>1. Why is this check here?</h3>${{why}}</div><div class="answer"><h3>2. What says the player can reach and collect it?</h3>${{reach}}</div><div class="answer"><h3>3. What disagrees with that answer?</h3>${{escapeHtml(disagree)}}</div><div class="answer"><h3>4. What evidence would graduate it?</h3>${{escapeHtml(c.graduation)}}</div></div><h3>Access disposition</h3>${{dispositionRows||'<p class="empty">No disposition ledger is available for this dataset.</p>'}}`;
 html+=`<h3>External wiki leads (${{c.external_leads.length}})</h3><p class="muted">Lead only: external agreement does not alter this claim's status or access disposition.</p>${{c.external_leads.length?c.external_leads.map(leadHtml).join(''):'<p class="empty">No exact check-linked external lead.</p>'}}`;
 html+=`<div class="answer"><h3>Current claim</h3><strong>${{escapeHtml(JSON.stringify(c.value))}}</strong><div class="muted">reviewed ${{c.last_reviewed}} · ${{escapeHtml(c.review_issue)}}</div></div><h3>Evidence by independent family (${{families.size}})</h3>`;
 for(const [family,rows] of [...families].sort((a,b)=>a[0].localeCompare(b[0]))){{html+=`<div class="family"><strong>${{escapeHtml(family)}}</strong><span class="muted"> · ${{rows.length}} row(s), one witness family</span>`;for(const e of rows)html+=`<div class="evidence"><div>${{badge(e.stance)}} <strong>${{escapeHtml(e.source_title)}}</strong> · version ${{escapeHtml(e.source_version)}}</div><div class="citation">${{escapeHtml(e.citation)}}</div><div class="muted">${{escapeHtml(e.method)}} · ${{escapeHtml(e.lineage)}}<br><code>${{escapeHtml(e.evidence_id)}}</code></div></div>`;html+='</div>'}}
 els.detail.innerHTML=html;document.getElementById('copy').onclick=()=>navigator.clipboard?.writeText(location.href);document.getElementById('copyReview').onclick=()=>navigator.clipboard?.writeText(playerPrompt(c));document.getElementById('copyAnswer').onclick=()=>navigator.clipboard?.writeText(reviewAnswer(c)).then(()=>document.getElementById('reviewStatus').textContent='Copied. Paste this into the Discord support thread.');document.getElementById('openReview').onclick=()=>{{const title=`[Evidence review] ${{c.check_name}}`;const url='https://github.com/4laric/er-archipelago/issues/new?labels=evidence&title='+encodeURIComponent(title)+'&body='+encodeURIComponent(reviewAnswer(c));window.open(url,'_blank','noopener')}};writeHash(c.claim_id);
}}
let selected=readHash();function render(){{const rows=filtered();const blockers=DATA.access_summary?DATA.access_summary.release_blockers:0;els.count.textContent=`${{rows.length}} / ${{claims.length}} claims · ${{blockers}} release blockers`;els.rows.innerHTML=rows.length?'':'<p class="empty">No claims match this permalink/filter.</p>';for(const c of rows.slice(0,200)){{const d=document.createElement('div');d.className='row'+(c.claim_id===selected?' active':'');d.innerHTML=`<div><strong>${{escapeHtml(c.check_name)}}</strong><div class="muted">${{c.claim_kind}} · ${{escapeHtml(JSON.stringify(c.value))}}</div><div class="badges">${{badge(c.status)}}${{badge(c.risk)}}${{c.needs_review?badge('needs review','critical'):''}}${{c.access_dispositions.map(x=>badge(x.disposition)).join('')}}${{c.external_leads.length?badge(c.external_leads.length+' external lead'+(c.external_leads.length===1?'':'s'),'external'):''}}${{c.release_blocker?badge('blocker','critical'):''}}${{c.evidence.some(e=>e.stance==='contradicts')?badge('conflict','contradicts'):''}}</div></div><code>${{c.check_id}}</code>`;d.onclick=()=>{{selected=c.claim_id;render();show(c)}};els.rows.append(d)}}if(rows.length>200)els.rows.insertAdjacentHTML('beforeend','<p class="empty">Showing the first 200 claims. Refine filters to see more.</p>');if(selected){{const c=claims.find(x=>x.claim_id===selected);if(c)show(c);else els.detail.innerHTML='<div class="alert">This permalink names a claim that is absent from this build.</div>'}}writeHash(selected)}}
for(const k of ['q','status','risk','kind','tag','review','family','disposition','external','blocker'])els[k].addEventListener(k==='q'?'input':'change',()=>{{selected='';render()}});els.playerQueue.addEventListener('click',()=>{{els.review.value='yes';els.kind.value='';els.disposition.value='';els.blocker.value='';selected='';render()}});els.exportQueue.addEventListener('click',()=>downloadQueue(filtered()));window.addEventListener('hashchange',()=>{{const p=new URLSearchParams(location.hash.slice(1));if(p.has('claim')||p.get('mode')==='maintainer'){{selected=readHash();render()}}}});if(new URLSearchParams(location.hash.slice(1)).has('claim')||new URLSearchParams(location.hash.slice(1)).get('mode')==='maintainer'){{renderUnbound();render();}}
</script></body></html>'''
    template = (Path(TOOLS) / "player_review_template.html").read_text(encoding="utf-8")
    return html.replace("</body>", template + chr(10) + "</body>")


def build(out_path: str = OUT_HTML, ledger_path: str = CURRENT) -> bytes:
    return render(load_ledger(ledger_path)).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=OUT_HTML)
    parser.add_argument("--ledger", default=CURRENT,
                        help="normalized ledger directory (default: v060-current)")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    blob = build(args.out, args.ledger)
    if args.check:
        try:
            with open(args.out, "rb") as fh:
                current = fh.read()
        except FileNotFoundError:
            current = b""
        if current != blob:
            print(f"STALE: {args.out}; run python3 tools/build_evidence_browser.py")
            return 1
        print(f"OK: {args.out} ({len(blob)} bytes)")
        return 0
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=".evidence-browser-", dir=os.path.dirname(os.path.abspath(args.out)))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(blob)
        os.replace(temp_path, args.out)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    print(f"wrote {args.out} ({len(blob)} bytes; {load_ledger(args.ledger)['inputs_hash']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
