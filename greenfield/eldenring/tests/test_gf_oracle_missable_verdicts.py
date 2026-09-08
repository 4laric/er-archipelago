"""The oracle MISSABLE review queue's HUMAN half: how a verdict is recorded and how it gets back.

The queue's membership rule (which rows are in it, and the licence boundary on what may be
written) is gated by test_gf_matt_oracle.py. This suite is the sibling of
test_gf_oracle_region_verdicts.py and covers the two pieces a reviewer touches:

  A. THE ROUND TRIP -- tools/apply_oracle_verdicts.py --queue missable folds the player review
     notebook's own backup file into greenfield/evidence/oracle-missable-queue.tsv. It is the SAME
     tool and the SAME mechanism as the region queue, so what this suite has to prove is the
     part that ISN'T shared:
       * the missable verdict rides its OWN notebook field. A check can sit in both queues at once,
         and if the two shared a field a ruling about a check's region would silently be applied as
         a ruling about its missability -- which is exactly the kind of defect that looks green.
       * a `missable` verdict must name the MECHANISM, from a closed vocabulary. gen_data's
         MISSABLE_LOCATIONS values are a closed set of mechanism labels (deathroot, alt_currency:N,
         gesture_award, questline, questline_item), so a verdict that does not map onto one could
         never be applied downstream. Refusing it at the door is the difference between a verdict
         that is unapplicable and one that is silently lost.
       * `confirmed-not-missable` needs NO mechanism: it is the claim that none of them applies.
         Requiring one there would make the cheap, common, useful answer the hard one to record.

  B. THE EVIDENCE JOIN -- build_evidence_browser.attach_oracle_missable_queue puts OUR OWN evidence
     beside each queued row so a reviewer can rule without the second source's sheet: our current
     missable status, the questline_conditions rows and what each waits on, and the quest features
     that mention the flag.

🛑 Everything here is synthetic. No third-party row, name, tag or area appears in this file.

Run:  python -m pytest greenfield/eldenring/tests/test_gf_oracle_missable_verdicts.py
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

COLUMNS = "flag\tap_id\tour_name\tour_conditions\tbasis\tstatus\treviewer\tnote"
BASIS = "second-source-missable-disagrees"
QUEUE = """\
# synthetic queue header written for this test
%s
1\t11\tA place :: A thing [f1]\tDIALOGUE_STEP+NPC_STATE\t%s\topen\t\t
2\t12\tA place :: Another thing [f2]\tITEM_POSSESSION\t%s\topen\t\t
3\t13\tElsewhere :: A third thing [f3]\tDIALOGUE_STEP\t%s\topen\t\t
""" % (COLUMNS, BASIS, BASIS, BASIS)


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
class MissableVerdictRoundTrip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.T = _load("apply_oracle_verdicts")
        cls.SPEC = cls.T.QUEUES["missable"]

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
        code = self.T.main([nb, "--queue", "missable", "--path", self.path, *extra])
        _c, _cols, rows = self.T.read_queue(self.path)
        return code, {int(r["ap_id"]): r for r in rows}

    # --- A. the round trip -----------------------------------------------
    def test_A_verdict_reason_and_reviewer_land_in_the_tsv(self):
        code, rows = self.run_tool(notebook(
            (11, {"OracleMissableVerdict": "missable", "OracleMissableReason": "killable-npc",
                  "Reviewer": "alaric", "RawNotes": "the NPC who hands it over\ncan be killed"}),
            (12, {"OracleMissableVerdict": "confirmed-not-missable", "Reviewer": "second",
                  "Finding": "Correct"}),
        ))
        self.assertEqual(code, 0)
        self.assertEqual(rows[11]["status"], "missable")
        self.assertEqual(rows[11]["reviewer"], "alaric")
        # The mechanism leads the note: it is the part a later change has to map onto a gen_data
        # missable class, so it must be the first thing legible in the cell.
        self.assertTrue(rows[11]["note"].startswith("killable-npc"))
        # ONE LINE: an embedded newline or tab would break the row and silently eat every column
        # after it, which is how a queue quietly loses its verdicts.
        self.assertNotIn("\n", rows[11]["note"])
        self.assertEqual(rows[12]["status"], "confirmed-not-missable")
        self.assertEqual(rows[13]["status"], "open")     # untouched rows stay open

    def test_A_missable_without_a_mechanism_is_refused(self):
        # gen_data records missable checks BY MECHANISM. A verdict with no mechanism cannot be
        # turned into a MISSABLE_LOCATIONS entry at all, so accepting it would mean recording work
        # that can never be applied -- worse than refusing it, because it looks done.
        code, rows = self.run_tool(notebook(
            (11, {"OracleMissableVerdict": "missable", "Reviewer": "alaric"})))
        self.assertEqual(code, 1)
        self.assertEqual(rows[11]["status"], "open")

    def test_A_confirmed_not_missable_needs_no_mechanism(self):
        # The mirror of the rule above, and the reason it is scoped to one verdict:
        # "none of these mechanisms applies" is the whole claim, so demanding one would be
        # incoherent -- and it is the cheap, common answer this queue most needs to be easy.
        code, rows = self.run_tool(notebook(
            (11, {"OracleMissableVerdict": "confirmed-not-missable", "Reviewer": "alaric"})))
        self.assertEqual(code, 0)
        self.assertEqual(rows[11]["status"], "confirmed-not-missable")

    def test_A_a_mechanism_outside_the_vocabulary_is_refused(self):
        code, rows = self.run_tool(notebook(
            (11, {"OracleMissableVerdict": "missable", "OracleMissableReason": "vibes",
                  "Reviewer": "alaric"})))
        self.assertEqual(code, 1)
        self.assertEqual(rows[11]["status"], "open")

    def test_A_every_documented_mechanism_is_accepted(self):
        # WITNESS FIRST: assert the vocabulary is populated before asserting each member works,
        # or an accidentally-empty tuple would make this test vacuously pass.
        self.assertEqual(len(self.SPEC.reasons), 3)
        for reason in self.SPEC.reasons:
            code, rows = self.run_tool(notebook(
                (13, {"OracleMissableVerdict": "missable", "OracleMissableReason": reason,
                      "Reviewer": "alaric"})))
            self.assertEqual(code, 0, reason)
            self.assertEqual(rows[13]["status"], "missable")

    def test_A_the_region_verdict_field_does_not_rule_this_queue(self):
        # 🛑 THE FIELD-SEPARATION GUARD. A check can be in BOTH queues. If the two shared a verdict
        # field, a reviewer ruling on a check's REGION would silently also rule on its
        # MISSABILITY -- and `moved` is not even in this queue's vocabulary, so the failure would
        # arrive as a confusing refusal at best and a wrong tag at worst.
        code, rows = self.run_tool(notebook(
            (11, {"OracleVerdict": "moved", "Reviewer": "alaric"})))
        self.assertEqual(code, 0)                        # not an error: just not this queue's field
        self.assertEqual(rows[11]["status"], "open")

    def test_A_recording_a_verdict_does_not_tag_anything(self):
        # 🛑 The queue is a REVIEW record. `missable` says a human ruled it losable; the tag itself
        # is applied later through gen_data's normal missable derivation. Nothing but the three
        # verdict columns may change, or the queue would be a second, competing missable source.
        _code, rows = self.run_tool(notebook(
            (11, {"OracleMissableVerdict": "missable", "OracleMissableReason": "questline-progress",
                  "Reviewer": "alaric"})))
        self.assertEqual(rows[11]["flag"], "1")
        self.assertEqual(rows[11]["our_name"], "A place :: A thing [f1]")
        self.assertEqual(rows[11]["our_conditions"], "DIALOGUE_STEP+NPC_STATE")
        self.assertEqual(rows[11]["basis"], BASIS)

    def test_A_blank_verdicts_are_skipped_not_written(self):
        code, rows = self.run_tool(notebook(
            (11, {"OracleMissableVerdict": "", "Reviewer": "alaric", "RawNotes": "just a note"})))
        self.assertEqual(code, 0)
        self.assertEqual(rows[11]["status"], "open")
        self.assertEqual(rows[11]["note"], "")

    def test_A_unattributed_verdict_is_refused(self):
        code, rows = self.run_tool(notebook(
            (11, {"OracleMissableVerdict": "confirmed-not-missable"})))
        self.assertEqual(code, 1)
        self.assertEqual(rows[11]["status"], "open")

    def test_A_unknown_check_and_unknown_verdict_are_refused(self):
        code, rows = self.run_tool(notebook(
            (999, {"OracleMissableVerdict": "missable", "OracleMissableReason": "killable-npc",
                   "Reviewer": "alaric"}),
            (12, {"OracleMissableVerdict": "moved", "Reviewer": "alaric"})))
        self.assertEqual(code, 1)
        self.assertEqual(rows[12]["status"], "open")

    def test_A_two_reviewers_agreeing_records_both(self):
        self.run_tool(notebook(
            (11, {"OracleMissableVerdict": "confirmed-not-missable", "Reviewer": "alaric"})))
        code, rows = self.run_tool(notebook(
            (11, {"OracleMissableVerdict": "confirmed-not-missable", "Reviewer": "second"})))
        self.assertEqual(code, 0)
        self.assertEqual(rows[11]["reviewer"], "alaric, second")

    def test_A_two_reviewers_disagreeing_is_refused_until_forced(self):
        self.run_tool(notebook(
            (11, {"OracleMissableVerdict": "confirmed-not-missable", "Reviewer": "alaric"})))
        code, rows = self.run_tool(notebook(
            (11, {"OracleMissableVerdict": "missable", "OracleMissableReason": "limited-consumable",
                  "Reviewer": "second"})))
        self.assertEqual(code, 1)
        self.assertEqual(rows[11]["status"], "confirmed-not-missable")
        code, rows = self.run_tool(notebook(
            (11, {"OracleMissableVerdict": "missable", "OracleMissableReason": "limited-consumable",
                  "Reviewer": "second"})), "--force")
        self.assertEqual(code, 0)
        self.assertEqual(rows[11]["status"], "missable")
        self.assertIn("overrides alaric: confirmed-not-missable", rows[11]["note"])

    def test_A_dry_run_writes_nothing(self):
        before = open(self.path, encoding="utf-8").read()
        self.run_tool(notebook(
            (11, {"OracleMissableVerdict": "confirmed-not-missable", "Reviewer": "alaric"})),
            "--dry-run")
        self.assertEqual(open(self.path, encoding="utf-8").read(), before)

    def test_A_legacy_single_report_shape_is_accepted(self):
        code, rows = self.run_tool({"schema": "er-player-review-v1", "check_id": 12,
                                    "oracle_missable_verdict": "missable",
                                    "oracle_missable_reason": "limited-consumable",
                                    "reviewer": "alaric"})
        self.assertEqual(code, 0)
        self.assertEqual(rows[12]["status"], "missable")

    def test_A_header_comments_and_line_endings_survive(self):
        self.run_tool(notebook(
            (11, {"OracleMissableVerdict": "confirmed-not-missable", "Reviewer": "alaric"})))
        with open(self.path, "rb") as fh:
            body = fh.read()
        self.assertNotIn(b"\r\n", body)     # the committed file is diff-gated in CI
        self.assertTrue(body.startswith(b"# synthetic queue header"))


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class MissableEvidenceJoin(unittest.TestCase):
    """attach_oracle_missable_queue against a synthetic queue and synthetic tables."""

    @classmethod
    def setUpClass(cls):
        cls.B = _load("build_evidence_browser")

    def _repo(self, queue_rows, conditions=(), flag_names=(), feature=None):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        gf = os.path.join(d.name, "greenfield")
        os.makedirs(os.path.join(gf, "evidence"))
        os.makedirs(os.path.join(gf, "eldenring", "features"))
        with open(os.path.join(gf, "evidence", "oracle-missable-queue.tsv"),
                  "w", encoding="utf-8", newline="\n") as fh:
            fh.write(COLUMNS + "\n")
            fh.writelines(r + "\n" for r in queue_rows)
        cols = "target_flag\troot_class\tsource_id\tsource_kind\tcone_completeness"
        with open(os.path.join(gf, "questline_conditions.tsv"),
                  "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# synthetic\n" + cols + "\n")
            fh.writelines(r + "\n" for r in conditions)
        # The REAL flag_names.tsv column order, deliberately: the gloss lives in `name_en`, and a
        # fixture that invented a `name` column would let the join silently resolve nothing while
        # every assertion still passed on bare flag numbers.
        with open(os.path.join(gf, "flag_names.tsv"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write("flag\tname_ja\tname_en\tsource\tset_by_event\tmap_id\tsetters\n")
            fh.writelines(r + "\n" for r in flag_names)
        if feature:
            with open(os.path.join(gf, "eldenring", "features", feature[0] + ".py"),
                      "w", encoding="utf-8") as fh:
                fh.write(feature[1])
        return d.name

    @staticmethod
    def _check(check_id, region, flag):
        return {"check_id": check_id,
                "player": {"region": region, "nearby_grace": "", "acquisition_flag": flag}}

    def test_B_queued_rows_get_our_own_evidence_and_others_get_nothing(self):
        root = self._repo(
            ["1\t11\tA thing\tDIALOGUE_STEP\t%s\topen\tal\tkillable-npc" % BASIS],
            conditions=["1\tDIALOGUE_STEP\t500\tflag\tcomplete"],
            flag_names=["500	テスト	Someone's quest step	emevd_event	9	common	1"])
        checks = [self._check(11, "Limgrave", 1), self._check(12, "Caelid", 2)]
        summary = self.B.attach_oracle_missable_queue(checks, repo=root)
        self.assertEqual(summary, {"queued": 1, "with_conditions": 1})
        q = checks[0]["player"]["oracle_missable"]
        self.assertNotIn("oracle_missable", checks[1]["player"])
        self.assertEqual(q["reviewer"], "al")
        # The baseline the reviewer is being asked to change, said out loud rather than implied.
        self.assertEqual(q["our_status"], "not missable")
        self.assertEqual(q["condition_classes"], "DIALOGUE_STEP")
        self.assertEqual(len(q["conditions"]), 1)
        # Named with OUR flag_names, so the panel says who the gate is about rather than a number.
        self.assertEqual(q["conditions"][0]["depends_on"], "Someone's quest step")
        self.assertEqual(q["conditions"][0]["note"], "")

    def test_B_only_the_losable_condition_classes_are_shown(self):
        # A BOSS_KILL or REGION_ACCESS root is a gate that stays satisfiable, so it says nothing
        # about missability. Showing it would pad the panel with rows that cannot support either
        # verdict, which is how an evidence surface becomes noise a reviewer learns to skim past.
        root = self._repo(
            ["1\t11\tA thing\tNPC_STATE\t%s\topen\t\t" % BASIS],
            conditions=["1\tNPC_STATE\t500\tflag\tcomplete",
                        "1\tBOSS_KILL\t600\tflag\tcomplete",
                        "1\tREGION_ACCESS\t700\tflag\tcomplete"])
        checks = [self._check(11, "Limgrave", 1)]
        self.B.attach_oracle_missable_queue(checks, repo=root)
        labels = [r["label"] for r in checks[0]["player"]["oracle_missable"]["conditions"]]
        self.assertEqual(len(labels), 1)
        self.assertIn("NPC", labels[0])

    def test_B_duplicate_call_sites_collapse_to_distinct_dependencies(self):
        # questline_conditions is one row per (award site, cone root), so the same NPC arrives
        # several times. A reviewer wants the distinct dependencies, not the call-site census.
        root = self._repo(
            ["1\t11\tA thing\tDIALOGUE_STEP\t%s\topen\t\t" % BASIS],
            conditions=["1\tDIALOGUE_STEP\t500\tflag\tcomplete"] * 4,
            flag_names=["500	テスト	Someone's quest step	emevd_event	9	common	1"])
        checks = [self._check(11, "Limgrave", 1)]
        self.B.attach_oracle_missable_queue(checks, repo=root)
        self.assertEqual(len(checks[0]["player"]["oracle_missable"]["conditions"]), 1)

    def test_B_a_capped_cone_says_so(self):
        # 🛑 budget_capped / unreadable is the extractor's own confidence and it is load-bearing:
        # a capped cone can MISS a prerequisite, so "no more rows" is never "no more gates". A
        # reviewer who cannot see that would read a short list as a complete one.
        root = self._repo(
            ["1\t11\tA thing\tITEM_POSSESSION\t%s\topen\t\t" % BASIS],
            conditions=["1\tITEM_POSSESSION\t500\tflag\tbudget_capped"],
            flag_names=["500	テスト	A held item	emevd_event	9	common	1"])
        checks = [self._check(11, "Limgrave", 1)]
        self.B.attach_oracle_missable_queue(checks, repo=root)
        self.assertIn("budget_capped",
                      checks[0]["player"]["oracle_missable"]["conditions"][0]["note"])

    def test_B_quest_features_that_mention_the_flag_are_listed(self):
        root = self._repo(
            ["1234\t11\tA thing\tNPC_STATE\t%s\topen\t\t" % BASIS],
            feature=("some_quest", "FLAGS = {1234: 'a step'}\n"))
        checks = [self._check(11, "Limgrave", 1234)]
        self.B.attach_oracle_missable_queue(checks, repo=root)
        self.assertEqual(checks[0]["player"]["oracle_missable"]["features"], ["some_quest"])

    def test_B_a_flag_that_is_only_a_substring_is_not_a_mention(self):
        # 12345678 contains "1234". A naive substring match would claim quest logic references
        # this flag when it references a different one -- a false lead pointed at the reviewer.
        # WITNESS FIRST: the same scan over the same module DOES find the flag when it really
        # appears. Without it, "no features" would pass identically if the scan matched nothing at
        # all -- which is exactly the bug this test is meant to be able to see.
        row = ["1234\t11\tA thing\tNPC_STATE\t%s\topen\t\t" % BASIS]
        hit = self._repo(row, feature=("other_quest", "FLAGS = {1234: 'this step'}\n"))
        checks = [self._check(11, "Limgrave", 1234)]
        self.B.attach_oracle_missable_queue(checks, repo=hit)
        self.assertEqual(checks[0]["player"]["oracle_missable"]["features"], ["other_quest"])
        # ...and now the ONLY difference: the digits are a substring of a longer flag.
        root = self._repo(row, feature=("other_quest", "FLAGS = {12345678: 'a different step'}\n"))
        checks = [self._check(11, "Limgrave", 1234)]
        self.B.attach_oracle_missable_queue(checks, repo=root)
        found = checks[0]["player"]["oracle_missable"]["features"]
        self.assertEqual(found, [])

    def test_B_no_condition_rows_is_a_silence_not_a_crash(self):
        root = self._repo(["1\t11\tA thing\tDIALOGUE_STEP\t%s\topen\t\t" % BASIS])
        checks = [self._check(11, "Limgrave", 1)]
        summary = self.B.attach_oracle_missable_queue(checks, repo=root)
        # WITNESS: the row IS joined and carries its queue evidence, so the empty condition list
        # below is a real silence about this check rather than the join having skipped it.
        self.assertEqual(summary["queued"], 1)
        q = checks[0]["player"]["oracle_missable"]
        self.assertEqual(q["condition_classes"], "DIALOGUE_STEP")
        self.assertEqual(q["our_status"], "not missable")
        self.assertEqual(summary["with_conditions"], 0)
        self.assertEqual(q["conditions"], [])

    def test_B_an_empty_queue_is_a_zero_summary_not_a_crash(self):
        root = self._repo([])
        checks = [self._check(11, "Limgrave", 1)]
        self.assertEqual(self.B.attach_oracle_missable_queue(checks, repo=root),
                         {"queued": 0, "with_conditions": 0})
        self.assertNotIn("oracle_missable", checks[0]["player"])


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class NotebookFields(unittest.TestCase):
    def test_notebook_carries_both_missable_fields(self):
        # Both verdicts ride the notebook's EXISTING record, so they round-trip through the
        # existing backup file. If a field is ever dropped from the JS, the round trip loses its
        # input silently -- the tsv would just stop gaining verdicts.
        js = open(os.path.join(TOOLS, "player_review_notebook.js"), encoding="utf-8").read()
        for field in ("OracleMissableVerdict", "OracleMissableReason"):
            self.assertIn("'%s'" % field, js)
        self.assertIn("oracle_missable_verdict:'OracleMissableVerdict'", js)
        self.assertIn("oracle_missable_reason:'OracleMissableReason'", js)

    def test_the_page_offers_only_the_documented_verdicts_and_mechanisms(self):
        M = _load("apply_oracle_verdicts")
        spec = M.QUEUES["missable"]
        html = open(os.path.join(TOOLS, "player_review_template.html"), encoding="utf-8").read()
        self.assertIn('id="pOracleMissableVerdict"', html)
        self.assertIn('id="pOracleMissableReason"', html)
        for value in tuple(spec.verdicts) + tuple(spec.reasons):
            self.assertIn('value="%s"' % value, html)

    def test_the_two_queues_use_distinct_notebook_fields(self):
        # The separation asserted behaviourally above, asserted structurally here: if someone
        # collapses the two specs onto one field, this is the test that says why not.
        M = _load("apply_oracle_verdicts")
        fields = [q.verdict_field for q in M.QUEUES.values()]
        self.assertEqual(len(fields), len(set(fields)))
        self.assertFalse(set(M.QUEUES["region"].verdicts) & set(M.QUEUES["missable"].verdicts))


if __name__ == "__main__":
    unittest.main()
