#!/usr/bin/env python3
"""Repo-only integrity tests for the #1273 gameplay-wiki intake pilot."""
from __future__ import annotations

import csv
import importlib.util
import json
import os
import unittest
from pathlib import Path

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON


_REPO = find_repo_root(__file__, marker="tools/check_wiki_audit.py")
REPO = Path(_REPO) if _REPO is not None else None


def load_repo_tool(name: str):
    if REPO is None:
        return None
    spec = importlib.util.spec_from_file_location(name, Path(REPO) / "tools" / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AUDIT = load_repo_tool("check_wiki_audit")

WALKTHROUGH_AUDIT = load_repo_tool("check_walkthrough_check_leads")
GAME8_AUDIT = load_repo_tool("check_game8_check_leads")
ELDENPEDIA_AUDIT = load_repo_tool("check_eldenpedia_location_leads")
POWERPYX_AUDIT = load_repo_tool("check_powerpyx_check_leads")
FEXTRALIFE_AUDIT = load_repo_tool("check_fextralife_item_leads")


@unittest.skipUnless(REPO is not None, REPO_ONLY_REASON)
class WikiAuditTest(unittest.TestCase):
    def test_registry_and_normalized_leads_validate(self):
        self.assertEqual(AUDIT.validate(REPO), (24, 16))

    def test_broad_walkthrough_check_leads_validate(self):
        path = REPO / "greenfield" / "evidence" / "wiki-audit" / "walkthrough-check-leads.tsv"
        with path.open(encoding="utf-8", newline="") as handle:
            self.assertGreaterEqual(len(list(csv.DictReader(handle, delimiter="\t"))), 800)
        self.assertEqual(WALKTHROUGH_AUDIT.main(), 0)

    def test_game8_check_leads_validate(self):
        path = REPO / "greenfield" / "evidence" / "wiki-audit" / "game8-check-leads.tsv"
        with path.open(encoding="utf-8", newline="") as handle:
            self.assertGreaterEqual(len(list(csv.DictReader(handle, delimiter="\t"))), 30)
        self.assertEqual(GAME8_AUDIT.main(), 0)

    def test_eldenpedia_location_check_leads_validate(self):
        path = (REPO / "greenfield" / "evidence" / "wiki-audit" /
                "eldenpedia-location-check-leads.tsv")
        with path.open(encoding="utf-8", newline="") as handle:
            self.assertGreaterEqual(len(list(csv.DictReader(handle, delimiter="\t"))), 315)
        self.assertEqual(ELDENPEDIA_AUDIT.main(), 0)

    def test_eldenpedia_location_leads_never_claim_access(self):
        path = (REPO / "greenfield" / "evidence" / "wiki-audit" /
                "eldenpedia-location-check-leads.tsv")
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertGreaterEqual(len(rows), 315)
        self.assertTrue(all(row["claim_kind"] == "identity_region" for row in rows))
        self.assertTrue(all(row["disposition"] == "lead_only" for row in rows))
        self.assertTrue(all("does not prove access" in row["limitations"] for row in rows))

    def test_powerpyx_regional_check_leads_validate(self):
        path = REPO / "greenfield" / "evidence" / "wiki-audit" / "powerpyx-check-leads.tsv"
        with path.open(encoding="utf-8", newline="") as handle:
            self.assertGreaterEqual(len(list(csv.DictReader(handle, delimiter="\t"))), 20)
        self.assertEqual(POWERPYX_AUDIT.main(), 0)

    def test_fextralife_item_check_leads_validate(self):
        path = (REPO / "greenfield" / "evidence" / "wiki-audit" /
                "fextralife-item-check-leads.tsv")
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertGreaterEqual(len(rows), 290)
        self.assertTrue(all(row["claim_kind"] == "identity_region" for row in rows))
        self.assertTrue(all(row["disposition"] == "lead_only" for row in rows))
        self.assertTrue(all("does not prove access" in row["limitations"] for row in rows))
        self.assertEqual(FEXTRALIFE_AUDIT.main(), 0)

    def test_generated_queue_prioritizes_external_coverage_without_promoting_it(self):
        path = REPO / "greenfield" / "evidence" / "wiki-audit" / "queue.json"
        queue = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(queue["policy"], {
            "contradictions_require_explicit_record": True,
            "external_disposition": "lead_only",
            "silence_is_evidence": False,
        })
        self.assertEqual(queue["counts"]["leads"], 16)
        self.assertEqual(queue["counts"]["exact_check_linked_leads"], 10)
        self.assertEqual(queue["counts"]["unbound_leads"], 6)
        self.assertEqual(queue["uncovered_high_risk_targets"], [])
        self.assertEqual(queue["contradictions"], [])
        self.assertTrue(all(
            row["disposition"] == "lead_only"
            for row in queue["exact_check_linked_leads"] + queue["unbound_leads"]
        ))

    def test_queue_keeps_carian_partition_check_linked_and_radahn_routes_unbound(self):
        queue = json.loads((REPO / "greenfield" / "evidence" / "wiki-audit" /
                            "queue.json").read_text(encoding="utf-8"))
        linked = {row["lead_id"]: row for row in queue["exact_check_linked_leads"]}
        unbound = {row["lead_id"]: row for row in queue["unbound_leads"]}
        self.assertEqual(len(linked["carian-study-hall-standard-route"]["check_ids"]), 5)
        self.assertEqual(len(linked["carian-study-hall-inverted-route"]["check_ids"]), 10)
        self.assertEqual(linked["chapel-anticipation-return-route"]["check_ids"],
                         ["7770913", "7770914", "7773786", "7900113"])
        self.assertIn("radahn-festival-altus-route", unbound)
        self.assertIn("radahn-festival-ranni-route", unbound)

    def test_lamenter_pilot_preserves_lead_only_scope(self):
        path = REPO / "greenfield" / "evidence" / "wiki-audit" / "leads.tsv"
        with path.open(encoding="utf-8", newline="") as handle:
            leads = {row["lead_id"]: row for row in csv.DictReader(handle, delimiter="\t")}
        self.assertEqual(leads["lamenters-gaol-upper-key-access"]["normalized_value"],
                         '{"type":"region_only"}')
        self.assertIn("Gaol Upper Level Key",
                      leads["lamenters-gaol-lower-key-access"]["normalized_value"])
        self.assertIn("Gaol Lower Level Key",
                      leads["lamenter-boss-access"]["normalized_value"])
        self.assertTrue(all(row["disposition"] == "lead_only" for row in leads.values()))
        self.assertTrue(all(row["game_version"] == "unknown" for row in leads.values()))

    def test_patches_pilot_keeps_routes_disjunctive_and_lead_only(self):
        path = REPO / "greenfield" / "evidence" / "wiki-audit" / "leads.tsv"
        with path.open(encoding="utf-8", newline="") as handle:
            leads = {row["lead_id"]: row for row in csv.DictReader(handle, delimiter="\t")}
        murkwater = leads["patches-murkwater-margits-shackle"]
        scenic = leads["patches-scenic-isle-margits-shackle"]
        self.assertEqual((murkwater["subject_id"], scenic["subject_id"]),
                         ("7770235", "7770235"))
        self.assertEqual((murkwater["claim_kind"], scenic["claim_kind"]),
                         ("alternate_acquisition", "alternate_acquisition"))
        self.assertIn("spared_after_surrender", murkwater["normalized_value"])
        self.assertIn('"name":"Liurnia"', scenic["normalized_value"])
        self.assertIn("shared Thiollier row", murkwater["limitations"])
        self.assertIn("alternate route", scenic["limitations"])
        self.assertTrue(all(row["disposition"] == "lead_only" for row in (murkwater, scenic)))

    def test_patches_report_comparison_still_matches_current_world_inputs(self):
        rows_test = (REPO / "greenfield" / "eldenring" / "tests" /
                     "test_gf_hub_collapsed_merchant_rows.py").read_text(encoding="utf-8")
        generated = (REPO / "greenfield" / "eldenring" / "data.py").read_text(encoding="utf-8")
        self.assertIn('PATCHES_REGIONS = ("Limgrave", "Mt. Gelmir", "Cerulean")', rows_test)
        self.assertIn("Margit's Shackle - from Patches or Thiollier", generated)
        self.assertIn("7770235, 110000", generated)

    def test_sellen_jerren_pilot_keeps_terminal_choices_distinct(self):
        path = REPO / "greenfield" / "evidence" / "wiki-audit" / "leads.tsv"
        with path.open(encoding="utf-8", newline="") as handle:
            leads = {row["lead_id"]: row for row in csv.DictReader(handle, delimiter="\t")}
        sellen = leads["sellen-ending-eccentrics-hood"]
        jerren = leads["jerren-ending-ancient-dragon-stone"]
        self.assertEqual((sellen["subject_id"], jerren["subject_id"]),
                         ("7770618", "7773737"))
        self.assertIn('"choice":"aid_Sellen_against_Jerren"', sellen["normalized_value"])
        self.assertIn('"choice":"aid_Jerren_against_Sellen"', jerren["normalized_value"])
        self.assertIn("speak_to_Jerren_after_battle", jerren["normalized_value"])
        self.assertNotEqual(sellen["normalized_value"], jerren["normalized_value"])
        self.assertTrue(all(row["disposition"] == "lead_only" for row in (sellen, jerren)))

    def test_sellen_jerren_report_comparison_still_matches_current_world_inputs(self):
        generated = (REPO / "greenfield" / "eldenring" / "data.py").read_text(encoding="utf-8")
        questline = (REPO / "greenfield" / "questline_dag.tsv").read_text(encoding="utf-8")
        self.assertIn("Raya Lucaria Academy :: Eccentric's Hood", generated)
        self.assertIn("Caelid :: Ancient Dragon Smithing Stone - around Smoldering Church", generated)
        self.assertIn("3371\t400400\tset\ttalk 312001400", questline)

    def test_sellian_sealbreaker_pilot_keeps_acquisition_and_use_separate(self):
        path = REPO / "greenfield" / "evidence" / "wiki-audit" / "leads.tsv"
        with path.open(encoding="utf-8", newline="") as handle:
            leads = {row["lead_id"]: row for row in csv.DictReader(handle, delimiter="\t")}
        acquisition = leads["sellian-sealbreaker-acquisition"]
        use = leads["sellian-sealbreaker-use"]
        self.assertEqual((acquisition["subject_kind"], acquisition["subject_id"]),
                         ("game_item", "goods:8169"))
        self.assertEqual((acquisition["claim_kind"], use["claim_kind"]),
                         ("acquisition", "use"))
        self.assertIn('"name":"Comet Azur"', acquisition["normalized_value"])
        self.assertIn('"name":"Sellia Hideaway"', use["normalized_value"])
        self.assertIn("GameSpot calls the item Sellian Spellbreaker", acquisition["limitations"])

    def test_sellian_sealbreaker_report_comparison_still_matches_current_inputs(self):
        gifts = (REPO / "greenfield" / "esd_gifts.tsv").read_text(encoding="utf-8")
        lots = (REPO / "greenfield" / "flag_lots.tsv").read_text(encoding="utf-8")
        regions = (REPO / "greenfield" / "region_map.csv").read_text(encoding="utf-8")
        generated = (REPO / "greenfield" / "eldenring" / "data.py").read_text(encoding="utf-8")
        self.assertIn("316006000\t1044369218\t1\t101020", gifts)
        self.assertIn("400102\tmap\t101020\t1\t1\t8169\t1\t1", lots)
        self.assertIn("7000879,400102,map_lot,Sellian Sealbreaker,PENDING", regions)
        self.assertNotIn("Sellian Sealbreaker", generated)

    def test_radahn_pilot_keeps_vanilla_routes_disjunctive_and_lead_only(self):
        path = REPO / "greenfield" / "evidence" / "wiki-audit" / "leads.tsv"
        with path.open(encoding="utf-8", newline="") as handle:
            leads = {row["lead_id"]: row for row in csv.DictReader(handle, delimiter="\t")}
        altus = leads["radahn-festival-altus-route"]
        ranni = leads["radahn-festival-ranni-route"]
        self.assertEqual((altus["subject_kind"], altus["subject_id"]),
                         ("boss", "1051360800"))
        self.assertEqual((altus["claim_kind"], ranni["claim_kind"]),
                         ("vanilla_access_route", "vanilla_access_route"))
        self.assertIn("activate_Altus_site_of_grace", altus["normalized_value"])
        self.assertIn("Ranni_questline_festival_information", ranni["normalized_value"])
        self.assertNotEqual(altus["normalized_value"], ranni["normalized_value"])
        self.assertTrue(all(row["disposition"] == "lead_only" for row in (altus, ranni)))

    def test_radahn_report_preserves_ap_region_sufficient_override(self):
        start_grace = (REPO / "greenfield" / "eldenring" / "features" /
                       "start_grace.py").read_text(encoding="utf-8")
        dispositions = (REPO / "greenfield" / "evidence" / "v060-current" /
                        "access_dispositions.tsv").read_text(encoding="utf-8")
        claims = (REPO / "greenfield" / "evidence" / "v060-current" /
                  "claims.tsv").read_text(encoding="utf-8")
        self.assertIn("_RADAHN_FESTIVAL = 9410", start_grace)
        self.assertIn("graces.append(_RADAHN_FESTIVAL)", start_grace)
        self.assertIn("7770002\tcheck:7770002/access\tregion_sufficient", dispositions)
        self.assertIn("7770665\tcheck:7770665/access\tregion_sufficient", dispositions)
        self.assertIn('""runtime_bypass"":{""flag"":9410', claims)

    def test_carian_pilot_partitions_standard_and_inverted_routes(self):
        path = REPO / "greenfield" / "evidence" / "wiki-audit" / "leads.tsv"
        with path.open(encoding="utf-8", newline="") as handle:
            leads = {row["lead_id"]: row for row in csv.DictReader(handle, delimiter="\t")}
        standard = leads["carian-study-hall-standard-route"]
        inverted = leads["carian-study-hall-inverted-route"]
        standard_value = json.loads(standard["normalized_value"])
        inverted_value = json.loads(inverted["normalized_value"])

        self.assertEqual(standard_value["layout"], "standard")
        self.assertFalse(standard_value["requires_carian_inverted_statue"])
        self.assertEqual(inverted_value["layout"], "inverted_bridge_tower")
        self.assertIn("Carian Inverted Statue", inverted["normalized_value"])
        self.assertTrue(set(standard_value["ap_ids"]).isdisjoint(inverted_value["ap_ids"]))
        self.assertEqual(len(standard_value["ap_ids"]), 5)
        self.assertEqual(len(inverted_value["ap_ids"]), 10)
        self.assertTrue(all(row["game_version"] == "unknown" for row in (standard, inverted)))
        self.assertTrue(all(row["disposition"] == "lead_only" for row in (standard, inverted)))

    def test_carian_leads_match_current_project_partition_without_becoming_proof(self):
        path = REPO / "greenfield" / "evidence" / "wiki-audit" / "leads.tsv"
        with path.open(encoding="utf-8", newline="") as handle:
            leads = {row["lead_id"]: row for row in csv.DictReader(handle, delimiter="\t")}
        inverted = json.loads(leads["carian-study-hall-inverted-route"]["normalized_value"])
        standard = json.loads(leads["carian-study-hall-standard-route"]["normalized_value"])
        feature = (REPO / "greenfield" / "eldenring" / "features" /
                   "legacy_key_gates.py").read_text(encoding="utf-8")
        generated = (REPO / "greenfield" / "eldenring" / "data.py").read_text(encoding="utf-8")

        for ap_id in inverted["ap_ids"] + standard["ap_ids"]:
            self.assertIn(f", {ap_id}, 341", generated)
        self.assertIn('"Carian Inverted Statue": frozenset({', feature)
        self.assertIn("# Standard side stays open:", feature)
        self.assertIn("comparison, not circular evidence", (
            REPO / "greenfield" / "evidence" / "wiki-audit" /
            "carian-study-hall.md").read_text(encoding="utf-8"))

    def test_chapel_return_lead_keeps_warp_requirements_together(self):
        path = REPO / "greenfield" / "evidence" / "wiki-audit" / "leads.tsv"
        with path.open(encoding="utf-8", newline="") as handle:
            leads = {row["lead_id"]: row for row in csv.DictReader(handle, delimiter="\t")}
        lead = leads["chapel-anticipation-return-route"]
        value = json.loads(lead["normalized_value"])

        self.assertEqual(value["type"], "all")
        self.assertEqual(value["ap_ids"], [7770913, 7770914, 7773786, 7900113])
        self.assertIn({"name": "Liurnia", "type": "region"}, value["requirements"])
        self.assertIn({"name": "Imbued Sword Key", "type": "item"}, value["requirements"])
        self.assertIn("Precipice of Anticipation", lead["normalized_value"])
        self.assertEqual(lead["disposition"], "lead_only")
        self.assertEqual(lead["game_version"], "unknown")

    def test_chapel_report_records_the_adjudicated_access_bucket(self):
        generated = (REPO / "greenfield" / "eldenring" / "data.py").read_text(encoding="utf-8")
        report = (REPO / "greenfield" / "evidence" / "wiki-audit" /
                  "chapel-anticipation-return.md").read_text(encoding="utf-8")

        self.assertIn("Liurnia :: Ornamental Straight Sword - m10_01", generated)
        self.assertIn("Liurnia :: Golden Beast Crest Shield - m10_01", generated)
        self.assertIn("Liurnia :: The Stormhawk King - m10_01", generated)
        self.assertIn("Liurnia :: Stormhawk Deenh - m10_01", generated)
        self.assertIn("v1.17 EMEVD", report)
        self.assertIn("adjudicated as Liurnia", report)


if __name__ == "__main__":
    unittest.main()
