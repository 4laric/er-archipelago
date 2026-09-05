"""Candidate matching must preserve ambiguity and never count as corroboration."""
import json
import sys
import unittest
from pathlib import Path
try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    from _util import find_repo_root, REPO_ONLY_REASON
ROOT = find_repo_root(__file__)
if ROOT:
    sys.path.insert(0, str(Path(ROOT) / "tools"))
    import build_bulk_check_review as bulk
    from player_check_review import player_check

@unittest.skipUnless(ROOT, REPO_ONLY_REASON)
class BulkReviewTests(unittest.TestCase):
    def test_stack_quantities_are_not_part_of_item_identity(self):
        self.assertEqual(bulk.item_mention("Smithing Stone [7] x2"),
                         ("Smithing Stone [7]", 2))
        self.assertEqual(bulk.item_mention("Rune Arc × 3"), ("Rune Arc", 3))
        self.assertEqual(bulk.item_mention("Golden Rune [5]"), ("Golden Rune [5]", None))

    def test_section_aliases_preserve_disagreements(self):
        self.assertEqual(bulk.REGIONS["ainsel"], ("Ainsel River",))
        self.assertEqual(set(bulk.REGIONS["belurat"]), {"Belurat", "Gravesite"})

    def test_ordinal_siblings_remain_ambiguous(self):
        candidates = [{"check_id": n, "region": "Limgrave",
                       "anchor": bulk.anchor(f"Limgrave :: Rune - near Gatefront ({n}) [f123]")}
                      for n in (1, 2)]
        out = bulk.match_observation(
            {"regions": ["Limgrave"], "context_labels": ["Gatefront"]}, candidates)
        self.assertEqual(out["candidate_ids"], [1, 2])
        self.assertEqual(out["reason"], "shared_landmark")
        self.assertEqual(out["status"], "needs_review")

    def test_no_region_match_preserves_all_alternatives(self):
        candidates = [{"check_id": n, "region": "Limgrave", "anchor": "gatefront"}
                      for n in (1, 2)]
        for regions, reason in (([], "source_area_unmapped"),
                                (["Liurnia"], "region_disagreement")):
            out = bulk.match_observation(
                {"regions": regions, "context_labels": ["Gatefront"]}, candidates)
            self.assertEqual(out["candidate_ids"], [1, 2])
            self.assertEqual(out["reason"], reason)
            self.assertEqual(out["matched_on"], ["item_name"])

    def test_unique_suggestion_is_still_only_a_lead(self):
        out = bulk.match_observation(
            {"regions": ["Limgrave"], "context_labels": ["Gatefront"]},
            [{"check_id": 1, "region": "Limgrave", "anchor": "gatefront"},
             {"check_id": 2, "region": "Liurnia", "anchor": "other"}])
        self.assertEqual(out["candidate_ids"], [1])
        self.assertEqual(out["all_candidate_ids"], [1, 2])
        self.assertEqual(out["status"], "needs_review")
        self.assertIn("exact_acquisition", out["missing_evidence"])

    def test_flags_sweeps_and_ordinals_are_not_landmarks(self):
        for tail in ("(1) [f123]", "m10_00_00_00 [f123]",
                     "(2), may be sweep-granted by Godrick (m10_00_00_00) [f123]"):
            self.assertEqual(bulk.anchor("Limgrave :: Rune - " + tail), "")

    def test_snapshot_registration_rejects_unknown_revision(self):
        snapshot = json.loads(bulk.SNAPSHOT.read_text())
        snapshot["revision"] = "unregistered"
        with self.assertRaisesRegex(ValueError, "registered"):
            bulk.build(snapshot)

    def test_committed_queue_is_reproducible_and_not_a_promotion(self):
        data, report = bulk.build()
        self.assertEqual(data, json.loads(Path(bulk.OUT).read_text()))
        self.assertEqual(report, json.loads(bulk.REPORT.read_text()))
        self.assertEqual(report["trusted_promotions"], 0)
        ids = set()
        for row in data["observations"]:
            self.assertNotIn(row["observation_id"], ids)
            ids.add(row["observation_id"])
            self.assertEqual(row["family"], "gameplay-guide:redmaw")
            self.assertEqual(row["status"], "needs_review")
            self.assertLessEqual(set(row["new_family_candidate_ids"]), set(row["candidate_ids"]))
            self.assertLessEqual(set(row["candidate_ids"]), set(row["all_candidate_ids"]))
            self.assertLessEqual(set(row["second_family_candidate_ids"]),
                                 set(row["new_family_candidate_ids"]))

@unittest.skipUnless(ROOT, REPO_ONLY_REASON)
class PlayerProjectionTests(unittest.TestCase):
    def check(self):
        return {"name": "Limgrave :: Rune - near Gatefront, may be sweep-granted by Boss [f123]",
                "tags": [], "claims": [{"claim_kind": "region", "value": {"region": "Limgrave"},
                                      "status": "supported"}], "access_dispositions": []}

    def test_plain_label_does_not_imply_access_review(self):
        view = player_check(self.check(), {"external_family_count": 2,
                                         "confidence": "trusted_identity_region"})
        self.assertEqual(view["item"], "Rune")
        self.assertEqual(view["place"], "near Gatefront")
        self.assertEqual(view["need"], "confirmed")
        self.assertFalse(view["access_reviewed"])

    def test_conflicts_take_precedence_over_identity_count(self):
        check = self.check()
        check["claims"][0]["status"] = "conflicted"
        view = player_check(check, {"external_family_count": 2,
                                  "confidence": "trusted_identity_region"})
        self.assertEqual(view["need"], "conflict")


if __name__ == "__main__":
    unittest.main()
