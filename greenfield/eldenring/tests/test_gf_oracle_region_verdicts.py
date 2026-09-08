"""The oracle region review queue's HUMAN half: how a verdict is recorded and how it gets back.

The queue itself (which rows are in it, and the licence boundary on what may be written) is gated
by test_gf_matt_oracle.py. This suite covers the two pieces a reviewer touches:

  A. THE ROUND TRIP -- tools/apply_oracle_region_verdicts.py folds the player review notebook's own
     backup file into greenfield/evidence/oracle-region-queue.tsv. There is deliberately NO server:
     the notebook has always shared work as a downloaded JSON file, and a second submission path
     would be a second way to lose a reviewer's work. So the tool must accept exactly the shapes
     that page can produce, and must REFUSE the ones that would quietly corrupt the queue --
     an unattributed verdict (two people work this queue), a verdict for a check that is not in it,
     and two reviewers who disagree.
  B. THE EVIDENCE JOIN -- build_evidence_browser.attach_oracle_region_queue puts OUR OWN evidence
     beside each queued row so a reviewer can rule without the second source's sheet. The
     nearest-grace candidate is the interesting part: it must exclude the queued rows from their
     own vote (or it just restates the assignment under review) and must stay SILENT when the
     checks around a grace do not agree.

🛑 Everything here is synthetic. No third-party row, name or area appears in this file.

Run:  python -m pytest greenfield/eldenring/tests/test_gf_oracle_region_verdicts.py
"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest

try:                       # package-relative under pytest; plain path when run directly
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
_FOUND = find_repo_root(HERE)
RUNNING_FROM_REPO = _FOUND is not None
REPO = _FOUND or os.path.dirname(os.path.dirname(HERE))
TOOLS = os.path.join(REPO, "tools")

QUEUE = """\
# synthetic queue header written for this test
flag\tap_id\tour_region\tbasis\tstatus\treviewer\tnote
1\t11\tLimgrave\tsecond-source-region-disagrees\topen\t\t
2\t12\tCaelid\tsecond-source-region-disagrees\topen\t\t
3\t13\tRoundtable Hold\tsecond-source-dlc-membership-disagrees\topen\t\t
"""


def _load(name):
    path = os.path.join(TOOLS, name + ".py")
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    spec = importlib.util.spec_from_file_location("_under_test_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def notebook(*reviews):
    return {"schema": "er-player-notebook-v1",
            "reviews": [{"check_id": cid, "form": form} for cid, form in reviews]}


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class VerdictRoundTrip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.T = _load("apply_oracle_region_verdicts")

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "queue.tsv")
        with open(self.path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(QUEUE)

    def run_tool(self, payload, *extra):
        nb = os.path.join(self.dir.name, "nb.json")
        with open(nb, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        code = self.T.main([nb, "--queue", self.path, *extra])
        _c, _cols, rows = self.T.read_queue(self.path)
        return code, {int(r["ap_id"]): r for r in rows}

    # --- A. the round trip -----------------------------------------------
    def test_A_verdict_reviewer_and_note_land_in_the_tsv(self):
        code, rows = self.run_tool(notebook(
            (11, {"OracleVerdict": "confirmed-ours", "Reviewer": "alaric",
                  "Finding": "Correct", "RawNotes": "walked it\nfrom the north grace"}),
            (13, {"OracleVerdict": "moved", "Reviewer": "second", "LockRegion": "Gravesite"}),
        ))
        self.assertEqual(code, 0)
        self.assertEqual(rows[11]["status"], "confirmed-ours")
        self.assertEqual(rows[11]["reviewer"], "alaric")
        # The note is ONE LINE: an embedded newline or tab would break the row and silently eat
        # every column after it, which is how a queue quietly loses its verdicts.
        self.assertEqual(rows[11]["note"], "Correct — walked it from the north grace")
        self.assertEqual(rows[13]["status"], "moved")
        self.assertEqual(rows[13]["note"], "Gravesite")
        self.assertEqual(rows[12]["status"], "open")     # untouched rows stay open

    def test_A_recording_a_verdict_does_not_move_anything(self):
        # 🛑 The queue is a REVIEW record. `moved` says a human ruled the region wrong; the fix
        # goes through the derivation ladder in a separate change. Nothing but the three verdict
        # columns may change, or the queue would be a second, competing region source.
        _code, rows = self.run_tool(notebook(
            (11, {"OracleVerdict": "moved", "Reviewer": "alaric", "LockRegion": "Caelid"})))
        self.assertEqual(rows[11]["our_region"], "Limgrave")
        self.assertEqual(rows[11]["basis"], "second-source-region-disagrees")
        self.assertEqual(rows[11]["flag"], "1")

    def test_A_blank_verdicts_are_skipped_not_written(self):
        # Most notebook entries are ordinary location notes with no ruling at all. They must not
        # blank out a verdict, and must not count as work.
        code, rows = self.run_tool(notebook(
            (11, {"OracleVerdict": "", "Reviewer": "alaric", "RawNotes": "just a note"})))
        self.assertEqual(code, 0)
        self.assertEqual(rows[11]["status"], "open")
        self.assertEqual(rows[11]["note"], "")

    def test_A_unattributed_verdict_is_refused(self):
        code, rows = self.run_tool(notebook((11, {"OracleVerdict": "confirmed-ours"})))
        self.assertEqual(code, 1)
        self.assertEqual(rows[11]["status"], "open")

    def test_A_unknown_check_and_unknown_verdict_are_refused(self):
        code, rows = self.run_tool(notebook(
            (999, {"OracleVerdict": "moved", "Reviewer": "alaric"}),
            (12, {"OracleVerdict": "probably", "Reviewer": "alaric"})))
        self.assertEqual(code, 1)
        self.assertEqual(rows[12]["status"], "open")

    def test_A_two_reviewers_agreeing_records_both(self):
        self.run_tool(notebook((11, {"OracleVerdict": "moved", "Reviewer": "alaric"})))
        code, rows = self.run_tool(notebook((11, {"OracleVerdict": "moved", "Reviewer": "second"})))
        self.assertEqual(code, 0)
        self.assertEqual(rows[11]["reviewer"], "alaric, second")

    def test_A_two_reviewers_disagreeing_is_refused_until_forced(self):
        # Two reviewers disagreeing IS the finding. Silently taking whichever file was imported
        # last would destroy the only evidence that the row is genuinely ambiguous.
        self.run_tool(notebook((11, {"OracleVerdict": "moved", "Reviewer": "alaric"})))
        code, rows = self.run_tool(
            notebook((11, {"OracleVerdict": "confirmed-ours", "Reviewer": "second"})))
        self.assertEqual(code, 1)
        self.assertEqual(rows[11]["status"], "moved")
        self.assertEqual(rows[11]["reviewer"], "alaric")
        code, rows = self.run_tool(
            notebook((11, {"OracleVerdict": "confirmed-ours", "Reviewer": "second"})), "--force")
        self.assertEqual(code, 0)
        self.assertEqual(rows[11]["status"], "confirmed-ours")
        self.assertIn("overrides alaric: moved", rows[11]["note"])

    def test_A_dry_run_writes_nothing(self):
        before = open(self.path, encoding="utf-8").read()
        self.run_tool(notebook((11, {"OracleVerdict": "moved", "Reviewer": "alaric"})),
                      "--dry-run")
        self.assertEqual(open(self.path, encoding="utf-8").read(), before)

    def test_A_legacy_single_report_shape_is_accepted(self):
        # The page's "Download this note" button still writes the older single-report file. A
        # reviewer should not have to know which of the two buttons they pressed.
        code, rows = self.run_tool({"schema": "er-player-review-v1", "check_id": 12,
                                    "oracle_verdict": "confirmed-ours", "reviewer": "alaric",
                                    "finding": "Correct"})
        self.assertEqual(code, 0)
        self.assertEqual(rows[12]["status"], "confirmed-ours")

    def test_A_header_comments_and_line_endings_survive(self):
        self.run_tool(notebook((11, {"OracleVerdict": "moved", "Reviewer": "alaric"})))
        with open(self.path, "rb") as fh:
            body = fh.read()
        self.assertNotIn(b"\r\n", body)     # the committed file is diff-gated in CI
        self.assertTrue(body.startswith(b"# synthetic queue header"))

    def test_A_a_foreign_schema_is_refused_rather_than_half_read(self):
        with self.assertRaises(SystemExit):
            self.T.forms_from({"schema": "something-else", "reviews": []})


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class EvidenceJoin(unittest.TestCase):
    """attach_oracle_region_queue against a synthetic queue and synthetic checks."""

    @classmethod
    def setUpClass(cls):
        cls.B = _load("build_evidence_browser")

    def _repo(self, queue_rows):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        gf = os.path.join(d.name, "greenfield")
        os.makedirs(os.path.join(gf, "evidence"))
        with open(os.path.join(gf, "evidence", "oracle-region-queue.tsv"),
                  "w", encoding="utf-8", newline="\n") as fh:
            fh.write("flag\tap_id\tour_region\tbasis\tstatus\treviewer\tnote\n")
            fh.writelines(r + "\n" for r in queue_rows)
        # The other three joins are optional evidence: an absent file must mean "no evidence",
        # never a crash, because this build runs in CI without the second-source checkout.
        return d.name

    @staticmethod
    def _check(check_id, region, grace, flag):
        return {"check_id": check_id,
                "player": {"region": region, "nearby_grace": grace, "acquisition_flag": flag}}

    def test_B_queued_rows_get_our_own_evidence_and_others_get_nothing(self):
        root = self._repo(["1\t11\tLimgrave\tsecond-source-region-disagrees\topen\tal\twhy"])
        checks = [self._check(11, "Limgrave", "North Grace", 1),
                  self._check(12, "Caelid", "North Grace", 2)]
        summary = self.B.attach_oracle_region_queue(checks, repo=root)
        self.assertEqual(summary["queued"], 1)
        self.assertIn("oracle_region", checks[0]["player"])
        self.assertNotIn("oracle_region", checks[1]["player"])
        self.assertEqual(checks[0]["player"]["oracle_region"]["reviewer"], "al")

    def test_B_grace_candidate_excludes_the_row_under_review(self):
        # 11 is queued and sits in Limgrave; every OTHER check on its grace sits in Caelid. The
        # candidate must be Caelid -- if the queued row voted for itself, a lone outlier would
        # always "confirm" its own region and the signal would be worthless.
        root = self._repo(["1\t11\tLimgrave\tsecond-source-region-disagrees\topen\t\t"])
        checks = [self._check(11, "Limgrave", "North Grace", 1),
                  self._check(12, "Caelid", "North Grace", 2),
                  self._check(13, "Caelid", "North Grace", 3)]
        summary = self.B.attach_oracle_region_queue(checks, repo=root)
        q = checks[0]["player"]["oracle_region"]
        self.assertEqual(q["grace_region"], "Caelid")
        self.assertEqual(q["candidate_region"], "Caelid")
        self.assertEqual(summary["grace_candidate"], 1)

    def test_B_agreeing_grace_is_not_a_candidate(self):
        root = self._repo(["1\t11\tCaelid\tsecond-source-region-disagrees\topen\t\t"])
        checks = [self._check(11, "Caelid", "North Grace", 1),
                  self._check(12, "Caelid", "North Grace", 2)]
        summary = self.B.attach_oracle_region_queue(checks, repo=root)
        q = checks[0]["player"]["oracle_region"]
        self.assertEqual(q["grace_region"], "Caelid")
        # It corroborates nothing: the vote is made of the same nearest-neighbour geometry that
        # produced the assignment. So it is recorded, and it is NOT offered as a candidate.
        self.assertEqual(q["candidate_region"], "")
        self.assertEqual(summary["grace_candidate"], 0)

    def test_B_a_split_grace_yields_silence_not_a_guess(self):
        root = self._repo(["1\t11\tLimgrave\tsecond-source-region-disagrees\topen\t\t"])
        checks = [self._check(11, "Limgrave", "North Grace", 1),
                  self._check(12, "Caelid", "North Grace", 2),
                  self._check(13, "Altus", "North Grace", 3)]
        self.B.attach_oracle_region_queue(checks, repo=root)
        q = checks[0]["player"]["oracle_region"]
        self.assertEqual(q["grace_region"], "")
        self.assertEqual(q["candidate_region"], "")

    def test_B_an_empty_queue_is_a_zero_summary_not_a_crash(self):
        root = self._repo([])
        checks = [self._check(11, "Limgrave", "North Grace", 1)]
        self.assertEqual(self.B.attach_oracle_region_queue(checks, repo=root),
                         {"queued": 0, "grace_candidate": 0})
        self.assertNotIn("oracle_region", checks[0]["player"])


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class NotebookField(unittest.TestCase):
    def test_notebook_carries_the_verdict_field(self):
        # The verdict rides the notebook's EXISTING record, so it round-trips through the existing
        # backup file. If this field is ever dropped from the JS, the round trip loses its input
        # silently -- the tsv would just stop gaining verdicts.
        js = open(os.path.join(TOOLS, "player_review_notebook.js"), encoding="utf-8").read()
        self.assertIn("'OracleVerdict'", js)
        self.assertIn("oracle_verdict:'OracleVerdict'", js)

    def test_the_page_offers_only_the_documented_verdicts(self):
        M = _load("apply_oracle_region_verdicts")
        html = open(os.path.join(TOOLS, "player_review_template.html"), encoding="utf-8").read()
        self.assertIn('id="pOracleVerdict"', html)
        for verdict in M.VERDICTS:
            self.assertIn('value="%s"' % verdict, html)


if __name__ == "__main__":
    unittest.main()
