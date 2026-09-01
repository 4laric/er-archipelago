#!/usr/bin/env python3
"""Repo-only integrity tests for the #1273 gameplay-wiki intake pilot."""
from __future__ import annotations

import csv
import importlib.util
import unittest
from pathlib import Path

REPO_ONLY_REASON = "wiki source registry and validator are repository evidence, not world files"


def find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "tools" / "check_wiki_audit.py").is_file():
            return candidate
    raise RuntimeError("repository root not found")


REPO = find_repo_root(Path(__file__).resolve())
SPEC = importlib.util.spec_from_file_location(
    "check_wiki_audit", REPO / "tools" / "check_wiki_audit.py")
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class WikiAuditTest(unittest.TestCase):
    def test_registry_and_normalized_leads_validate(self):
        self.assertEqual(AUDIT.validate(REPO), (10, 11))

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


if __name__ == "__main__":
    unittest.main()
