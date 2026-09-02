#!/usr/bin/env python3
"""Validate the normalized, non-redistributive gameplay-wiki audit registry."""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path


def validate(repo: Path) -> tuple[int, int]:
    root = repo / "greenfield" / "evidence" / "wiki-audit"
    with (root / "sources.tsv").open(encoding="utf-8", newline="") as handle:
        sources = list(csv.DictReader(handle, delimiter="\t"))
    with (root / "leads.tsv").open(encoding="utf-8", newline="") as handle:
        leads = list(csv.DictReader(handle, delimiter="\t"))

    assert len(sources) >= 2, "pilot must compare at least two sources"
    source_ids = {row["source_id"] for row in sources}
    assert len(source_ids) == len(sources), "duplicate source_id"
    for row in sources:
        revision = row["revision_url"]
        is_archive = revision.startswith("https://web.archive.org/web/")
        is_pinned_github_tree = bool(re.fullmatch(
            r"https://github\.com/[^/]+/[^/]+/tree/[0-9a-f]{40}/.+", revision
        ))
        assert is_archive or is_pinned_github_tree, "revision must be an immutable archive or commit"
        assert row["body_sha256"].startswith("sha256:") and len(row["body_sha256"]) == 71
        assert row["published_at"] and row["last_modified"] and row["archived_at"]
        assert row["patch_applicability"], "every source needs an explicit version disposition"
        assert row["disposition"] == "lead_only"

    lead_ids = {row["lead_id"] for row in leads}
    assert len(lead_ids) == len(leads), "duplicate lead_id"
    for row in leads:
        json.loads(row["normalized_value"])
        claimed_sources = row["source_ids"].split(",")
        families = row["independence_families"].split(",")
        assert len(claimed_sources) >= 2 and set(claimed_sources) <= source_ids
        assert len(families) == len(set(families)) == len(claimed_sources)
        assert row["disposition"] == "lead_only" and row["game_version"] == "unknown"
        assert row["exact_citations"] and row["summary"] and row["limitations"]
    subprocess.run(
        [sys.executable, str(repo / "tools" / "build_wiki_audit_queue.py"), "--check"],
        cwd=repo,
        check=True,
    )
    return len(sources), len(leads)


if __name__ == "__main__":
    repo = Path(__file__).resolve().parent.parent
    source_count, lead_count = validate(repo)
    print(f"wiki audit: OK -- {source_count} sources, {lead_count} normalized leads")
