"""Phase-1 evidence browser contract and deterministic offline artifact (#1212)."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import re
import tempfile
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

ROOT = find_repo_root(__file__)
RUNNING_FROM_REPO = ROOT is not None
ROOT = ROOT or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILDER = None
if RUNNING_FROM_REPO:
    spec = importlib.util.spec_from_file_location(
        "evidence_browser_builder", os.path.join(ROOT, "tools", "build_evidence_browser.py"))
    BUILDER = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(BUILDER)


def payload(html: str) -> dict:
    match = re.search(
        r'<script id="evidence-payload" type="application/json">(.*?)</script>', html, re.S)
    if not match:
        raise AssertionError("offline page has no embedded evidence payload")
    return json.loads(match.group(1).replace("<\\/", "</"))


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class FixtureContractTests(unittest.TestCase):
    def test_fixture_uses_normalized_headers_and_identity_values(self):
        tables = BUILDER.normalized_tables(BUILDER.FIXTURE)
        self.assertEqual(set(tables), set(BUILDER.HEADERS))
        for table, rows in tables.items():
            if rows:
                self.assertEqual(tuple(rows[0]), BUILDER.HEADERS[table])

        data = BUILDER.load_fixture()
        for check in data["checks"]:
            identity = next(c for c in check["claims"] if c["claim_kind"] == "identity")
            self.assertEqual(set(identity["value"]), {"ap_id", "flag", "namespace", "id"})
            self.assertEqual(identity["value"]["ap_id"], check["check_id"])
            self.assertIn(identity["value"]["namespace"],
                          {"item", "lot", "shop", "entity", "flag"})

    def test_fixture_has_exactly_identity_and_region_claims(self):
        data = BUILDER.load_fixture()
        self.assertGreaterEqual(len(data["checks"]), 2, "fixture must exercise more than one check")
        for check in data["checks"]:
            self.assertEqual({c["claim_kind"] for c in check["claims"]}, {"identity", "region"})

    def test_dependent_outputs_are_one_family_not_two_votes(self):
        data = BUILDER.load_fixture()
        claim = next(c for x in data["checks"] for c in x["claims"]
                     if c["claim_id"] == "check:7770100/identity")
        self.assertEqual(len(claim["evidence"]), 2, "witness: the dependent pair disappeared")
        self.assertEqual({e["family_id"] for e in claim["evidence"]},
                         {"game:param:ItemLotParam_map"})
        self.assertTrue(any("not an independent vote" in e["lineage"]
                            for e in claim["evidence"]))

    def test_transform_rejects_dangling_evidence_and_blank_citations(self):
        tables = copy.deepcopy(BUILDER.normalized_tables(BUILDER.FIXTURE))
        tables["claims.tsv"][0]["evidence_ids"] += ",evidence:missing"
        with self.assertRaisesRegex(ValueError, "evidence_ids do not match"):
            BUILDER.transform(tables)

        tables = copy.deepcopy(BUILDER.normalized_tables(BUILDER.FIXTURE))
        tables["evidence.tsv"][0]["citation"] = ""
        with self.assertRaisesRegex(ValueError, "exact citation"):
            BUILDER.transform(tables)

    def test_external_leads_cannot_promote_core_claims(self):
        tables = BUILDER.normalized_tables(BUILDER.FIXTURE)
        sources, leads = BUILDER.wiki_tables()
        bad = copy.deepcopy(leads[:1])
        bad[0]["disposition"] = "corroborated"
        with self.assertRaisesRegex(ValueError, "lead-only boundary"):
            BUILDER.transform(tables, external_sources=sources, external_leads=bad)

        bad = copy.deepcopy(leads[:1])
        bad[0]["source_ids"] = "wiki:missing"
        with self.assertRaisesRegex(ValueError, "dangling sources"):
            BUILDER.transform(tables, external_sources=sources, external_leads=bad)

    def test_external_leads_accept_semicolon_separated_sources_and_families(self):
        tables = BUILDER.normalized_tables(BUILDER.FIXTURE)
        sources, leads = BUILDER.wiki_tables()
        source_ids = [row["source_id"] for row in sources[:2]]
        lead = copy.deepcopy(leads[0])
        lead["lead_id"] = "fixture-semicolon-check-7770100"
        lead["subject_id"] = "7770100"
        lead["source_ids"] = ";".join(source_ids)
        lead["independence_families"] = "gameplay-guide:first;gameplay-guide:second"
        data = BUILDER.transform(tables, external_sources=sources, external_leads=[lead])
        rendered = next(
            candidate for check in data["checks"] for candidate in check["external_leads"]
            if candidate["lead_id"] == lead["lead_id"]
        )
        self.assertEqual([source["source_id"] for source in rendered["sources"]], source_ids)
        self.assertEqual(rendered["families"],
                         ["gameplay-guide:first", "gameplay-guide:second"])


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class OfflineArtifactTests(unittest.TestCase):
    def test_wiki_leads_are_total_and_partitioned_without_changing_core_status(self):
        baseline = BUILDER.transform(
            BUILDER.normalized_tables(BUILDER.CURRENT),
            BUILDER.validate_access_dispositions(
                BUILDER.Path(BUILDER.CURRENT),
                BUILDER.Path(BUILDER.CURRENT, BUILDER.ACCESS_FILE),
            ),
        )
        data = BUILDER.load_ledger()
        _sources, registry = BUILDER.wiki_tables()
        linked = [lead for check in data["checks"] for lead in check["external_leads"]]
        unbound = data["unbound_external_leads"]
        self.assertEqual(
            sorted(lead["lead_id"] for lead in linked + unbound),
            sorted(row["lead_id"] for row in registry),
        )
        self.assertEqual(len(linked), sum(row["subject_kind"] == "check" for row in registry))
        self.assertEqual(len(unbound), sum(row["subject_kind"] != "check" for row in registry))
        self.assertTrue(all(lead["disposition"] == "lead_only" for lead in linked + unbound))
        self.assertTrue(all(lead["game_version"] == "unknown" for lead in linked + unbound))
        self.assertEqual(
            [(c["claim_id"], c["status"], c["value"])
             for check in baseline["checks"] for c in check["claims"]],
            [(c["claim_id"], c["status"], c["value"])
             for check in data["checks"] for c in check["claims"]],
        )

    def test_wiki_registries_participate_in_the_content_hash(self):
        self.assertEqual(BUILDER.wiki_lead_files(),
                         ["dlc-blessing-collectible-check-leads.tsv",
                          "dlc-sparse-region-check-leads.tsv",
                          "eldenpedia-boss-reward-check-leads.tsv",
                          "eldenpedia-crystal-tear-check-leads.tsv",
                          "eldenpedia-deathroot-check-leads.tsv",
                          "eldenpedia-golden-seed-check-leads.tsv",
                          "eldenpedia-item-acquisition-check-leads.tsv",
                          "eldenpedia-location-check-leads.tsv",
                          "eldenpedia-memory-stone-check-leads.tsv",
                          "eldenpedia-repeated-pickup-check-leads.tsv",
                          "eldenpedia-sacred-tear-check-leads.tsv",
                          "eldenpedia-seedbed-curse-check-leads.tsv",
                          "eldenpedia-shabriri-grape-check-leads.tsv",
                          "eldenpedia-upgrade-location-row-check-leads.tsv",
                          "eldenpedia-upgrade-material-check-leads.tsv",
                          "eldenpedia-whetblade-check-leads.tsv",
                          "fextralife-acquisition-check-leads.tsv",
                          "fextralife-item-check-leads.tsv",
                          "fextralife-linked-place-check-leads.tsv",
                          "fextralife-redmaw-corroboration-check-leads.tsv",
                          "game8-check-leads.tsv",
                          "game8-dlc-anchor-check-leads.tsv",
                          "game8-dlc-floor-check-leads.tsv", "leads.tsv",
                          "powerpyx-check-leads.tsv",
                          "redmaw-checklist-check-leads.tsv",
                          "redmaw-embedded-ash-check-leads.tsv",
                          "redmaw-location-anchor-check-leads.tsv",
                          "redmaw-merchant-check-leads.tsv",
                          "small-guide-tail-corroboration-check-leads.tsv",
                          "walkthrough-check-leads.tsv"])
        self.assertEqual(BUILDER.load_ledger()["inputs_hash"],
                         BUILDER.ledger_hash(BUILDER.CURRENT, BUILDER.WIKI_AUDIT))
        self.assertNotEqual(BUILDER.ledger_hash(BUILDER.CURRENT),
                            BUILDER.ledger_hash(BUILDER.CURRENT, BUILDER.WIKI_AUDIT))

    def test_committed_page_uses_the_full_current_corpus(self):
        data = BUILDER.load_ledger()
        claims = BUILDER.normalized_tables(BUILDER.CURRENT)["claims.tsv"]
        subjects = {int(row["subject_id"]) for row in claims if row["active"] == "true"}
        self.assertEqual(data["dataset"], "greenfield/evidence/v060-current")
        self.assertGreater(len(subjects), 4000, "production browser fell back to the tiny fixture")
        self.assertEqual(len(data["checks"]), len(subjects))
        self.assertEqual(sum(len(check["claims"]) for check in data["checks"]), len(claims))
        self.assertEqual(
            {row["claim_kind"] for row in claims},
            {"identity", "region", "detection", "access"})
        self.assertEqual(
            sorted(row["status"] for row in claims),
            sorted(claim["status"] for check in data["checks"] for claim in check["claims"]))
        self.assertEqual(len(data["checks"]), data["access_summary"]["checks_total"])
        self.assertEqual(
            sum(check["release_blocker"] for check in data["checks"]),
            data["access_summary"]["release_blockers"],
        )
        self.assertTrue(all(check["access_dispositions"] for check in data["checks"]))
        self.assertTrue(all(not check["name"].startswith("Check ") for check in data["checks"]))
        self.assertEqual(
            next(check["tags"] for check in data["checks"] if check["check_id"] == 7770002),
            ["Boss", "GreatRune", "MajorBoss"],
        )
        review = [check for check in data["checks"] if check["needs_review"]]
        self.assertGreater(len(review), 1000)
        self.assertLess(len(review), 1500, "targeted review regressed to the full unresolved queue")
        self.assertTrue(all(check["review_reasons"] for check in review))
        self.assertTrue(any(
            "one external family" in reason
            for check in review for reason in check["review_reasons"]
        ))
        self.assertIn("Dark Moon Ring", next(
            check["name"] for check in data["checks"] if check["check_id"] == 7770000))

    def test_production_browser_uses_validated_disposition_review_metadata(self):
        data = BUILDER.load_ledger()
        radahn = next(check for check in data["checks"] if check["check_id"] == 7770002)
        self.assertFalse(radahn["release_blocker"])
        self.assertEqual(
            {row["disposition"] for row in radahn["access_dispositions"]},
            {"region_sufficient"},
        )
        row = radahn["access_dispositions"][0]
        self.assertEqual(row["option_set"], "all")
        self.assertEqual(row["review_issue"], "#1271")
        self.assertIn("festival flag 9410", row["reason"])

    def test_small_fixture_still_exercises_conflicts_and_family_deduplication(self):
        data = BUILDER.load_fixture()
        self.assertEqual(data["dataset"], "greenfield/evidence/browser_fixture")
        self.assertEqual(len(data["checks"]), 2)
        self.assertTrue(any(claim["status"] == "conflicted"
                            for check in data["checks"] for claim in check["claims"]))

    def test_build_is_byte_deterministic_and_committed_page_is_current(self):
        first = BUILDER.build()
        second = BUILDER.build()
        self.assertEqual(first, second)
        with open(BUILDER.OUT_HTML, "rb") as fh:
            self.assertEqual(first, fh.read(),
                             "evidence browser is stale; run tools/build_evidence_browser.py")

    def test_fixture_stamp_is_content_hash_not_a_git_commit(self):
        contract = BUILDER.load_fixture()
        stamp = contract["inputs_hash"]
        self.assertEqual(stamp, BUILDER.ledger_hash(BUILDER.FIXTURE))
        html = BUILDER.build(ledger_path=BUILDER.FIXTURE).decode("utf-8")
        self.assertIn(f'<meta name="evidence-inputs-hash" content="{stamp}">', html)
        self.assertEqual(payload(html)["inputs_hash"], stamp)

    def test_page_exposes_facets_conflicts_citations_and_the_four_questions(self):
        html = BUILDER.build().decode("utf-8")
        for facet in (
            'id="status"', 'id="risk"', 'id="kind"', 'id="family"',
            'id="tag"', 'id="review"', 'id="disposition"', 'id="external"', 'id="blocker"',
        ):
            self.assertIn(facet, html)
        for question in (
            "1. Why is this check here?",
            "2. What says the player can reach and collect it?",
            "3. What disagrees with that answer?",
            "4. What evidence would graduate it?",
        ):
            self.assertIn(question, html)
        data = payload(BUILDER.build(ledger_path=BUILDER.FIXTURE).decode("utf-8"))
        claims = [c for x in data["checks"] for c in x["claims"]]
        conflicted = [c for c in claims if c["status"] == "conflicted"]
        self.assertTrue(conflicted, "witness: fixture no longer exercises an active conflict")
        self.assertTrue(any(check["needs_review"] for check in data["checks"]))
        self.assertTrue(any(e["stance"] == "contradicts" for c in conflicted for e in c["evidence"]))
        self.assertTrue(all(e["citation"].strip() for c in claims for e in c["evidence"]))
        fixture_html = BUILDER.build(ledger_path=BUILDER.FIXTURE).decode("utf-8")
        self.assertIn("Conflict is active.", fixture_html)
        self.assertIn("Evidence by independent family", fixture_html)
        self.assertIn("No access evidence exists for this check", html)
        self.assertIn("Access claim:", html)
        self.assertIn("ownership is not proof that the player can reach or collect it", html)
        self.assertIn("Access disposition", html)
        self.assertIn("v0.6 release blocker.", html)
        self.assertIn("${blockers} release blockers", html)
        self.assertIn("External wiki leads", html)
        self.assertIn("Unbound external leads", html)
        self.assertIn("Lead only: external agreement does not alter", html)
        self.assertIn("Immutable citations:", html)
        self.assertIn('id="playerQueue"', html)
        self.assertIn('id="copyReview"', html)
        self.assertIn("Can you confirm where this is and everything required to collect it?", html)
        self.assertIn("els.review.value='yes'", html)
        self.assertIn("Human review requested.", html)

    def test_permalink_serialises_every_facet_and_selected_claim(self):
        html = BUILDER.build().decode("utf-8")
        self.assertIn("new URLSearchParams(location.hash.slice(1))", html)
        self.assertIn("history.replaceState(null,'','#'+hashParams(selected).toString())", html)
        for key in ("q", "status", "risk", "kind", "family", "disposition", "external", "blocker"):
            self.assertIn(f"'{key}'", html)
        self.assertIn("p.set('claim',selected)", html)
        self.assertIn("new URL(location.href)", html)
        self.assertIn("hashParams(c.claim_id)", html)
        self.assertIn("This permalink names a claim that is absent from this build.", html)

    def test_export_uses_filtered_risk_order_and_safe_stable_columns(self):
        html = BUILDER.build().decode("utf-8")
        self.assertIn("downloadQueue(filtered())", html)
        self.assertIn("riskRank[a.risk]-riskRank[b.risk]", html)
        self.assertIn("statusRank[a.status]-statusRank[b.status]", html)
        self.assertIn("a.check_id-b.check_id||a.claim_kind.localeCompare(b.claim_kind)", html)
        self.assertIn("'access_dispositions','option_sets','release_blocker'", html)
        self.assertIn("'disposition_reasons','disposition_review_issues','permalink'", html)
        self.assertIn("'external_lead_count','external_lead_ids','external_claim_kinds'", html)
        self.assertIn("'external_families','external_game_versions','external_dispositions'", html)
        self.assertIn("new Set(c.evidence.map(e=>e.family_id)).size", html)
        self.assertIn("String(value??'').replace(/[\\t\\r\\n]+/g,' ')", html)
        self.assertIn("if(/^[=+\\-@]/.test(s))s=\"'\"+s", html)
        self.assertIn("text/tab-separated-values;charset=utf-8", html)

    def test_check_mode_detects_stale_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "page.html")
            with open(path, "wb") as fh:
                fh.write(b"stale")
            with open(path, "rb") as fh:
                stale = fh.read()
            self.assertNotEqual(stale, BUILDER.build(path))


if __name__ == "__main__":
    unittest.main()
