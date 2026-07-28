"""Questline-DAG gate (tier A) -- tools/build_questline_dag.py + greenfield/questline_dag.tsv.

TIER 1 of SPEC-questline-dag-20260728 is "emit the graph, assert nothing" -- so the world reads
nothing here and this gate cannot be about world behaviour. What it CAN be about is the two ways a
derived corpus lies:

  A. CORROBORATION -- does the graph re-find what a year of hand audits already found? The spec's
     own tier 2 puts it plainly: "if the graph does not RE-FIND most of what a year of hand audits
     found, the graph is wrong". Measured as a ratio against MISSABLE_LOCATIONS, floored, and the
     floor is a RATCHET you are made to justify -- not a number that only fires when it gets worse.
  B. THE ACCEPTANCE CASES, END TO END, BY NAME (CONTRIBUTING rule 11). We have shipped a finding
     that was produced, stored, and then silently dropped by its own consumer while the suite went
     green. So every case in SPEC §7 that this tier can reach is asserted against the COMMITTED
     TABLE -- not against the tool's in-memory output, because a hand-edited tsv is exactly the
     failure a tool-only assertion cannot see.

     🛑 Including the NEGATIVE one. f510110 (Fortissax) MUST BE ABSENT. Every corpus feeding this
     graph reads an AWARD SITE, and what Fia's questline gates is whether the FIGHT EXISTS -- so
     the case the whole spec was written from is invisible here by construction. Asserting the
     absence is how "the graph is populated" stops being read as "the class is covered". If a
     future widening makes it appear, this test goes red and the right response is to READ the new
     edge, not to delete the assertion.

  C. NO DRIFT between this table's region column and the OTHER copy of the region resolver, in
     test_gf_lot_gates_cross_region. Two implementations of one join is a smell; two
     implementations with a cross-check is a design. This is the cross-check.

  D. FRESHNESS + DETERMINISM, same shape as the check-browser gate: a fresh build equals the
     committed file, byte for byte.

WHAT THIS GATE DELIBERATELY DOES NOT ASSERT
  * It does NOT demand that every graph target be missable-tagged. 64% of them are; the rest are
    same-region gates that the region lock already covers, and demanding 100% would force tags
    that buy nothing.
  * It does NOT demand zero unprotected cross-region edges. `test_gf_lot_gates_cross_region` owns
    that bar for the lot_gates corpus and holds it at zero. This table adds two corpora that screen
    has never read, and they surface candidates whose polarity/geometry a HUMAN has to rule on --
    see `test_new_corpora_candidates_are_reported_not_silently_passed`, which makes them loud on a
    green run instead of asserting a verdict nobody has earned yet.

AP-FREE: the tool executes the generated modules as plain literal data and reads committed tsvs.
No Archipelago on sys.path, so this runs in the bare sandbox.

Run:  python -m pytest greenfield/eldenring/tests/test_gf_questline_dag.py
  or: python greenfield/eldenring/tests/test_gf_questline_dag.py
"""
import collections
import csv
import importlib.util
import os
import sys
import unittest
import warnings

try:                       # package-relative under pytest; plain path when run directly
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
_FOUND = find_repo_root(HERE)
RUNNING_FROM_REPO = _FOUND is not None
# Derive from the FOUND root, never positionally: in CI the AP checkout sits inside the repo, so a
# positional GREENFIELD resolves to `_ap/worlds/` and every tsv read misses (the 2026-07-27 path bug).
REPO = _FOUND or os.path.dirname(os.path.dirname(HERE))
GREENFIELD = os.path.join(REPO, "greenfield") if _FOUND else os.path.dirname(os.path.dirname(HERE))
TOOL = os.path.join(REPO, "tools", "build_questline_dag.py")
TABLE = os.path.join(GREENFIELD, "questline_dag.tsv")

# MEASURED 2026-07-28 on the committed corpora: 99 of 154 target checks (64%) already carry the
# missable tag. The floor sits below that with room for honest movement, and it is a RATCHET: a run
# that comes in under it means the graph has stopped agreeing with the hand audits, which is a
# broken join, not a discovery. Raising it is fine; LOWERING it needs the reason written down.
CORROBORATION_FLOOR_PCT = 50
# Same argument, opposite direction: a graph that shrinks has gone blind. 283 edges / 154 targets
# on 2026-07-28.
MIN_EDGES = 200
MIN_TARGETS = 120


def _load_tool():
    spec = importlib.util.spec_from_file_location("_build_questline_dag", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _committed_rows():
    with open(TABLE, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(
            (ln for ln in fh if not ln.lstrip().startswith("#")), delimiter="\t"))


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class QuestlineDagGate(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(TABLE):
            raise unittest.SkipTest(
                "greenfield/questline_dag.tsv is absent -- run `python tools/build_questline_dag.py`. "
                "This gate would otherwise pass by having nothing to look at.")
        cls.tool = _load_tool()
        cls.rows = _committed_rows()
        cls.edges, cls.tally, cls.notes = cls.tool.build()

    # -- A. the table is a table -------------------------------------------
    def test_committed_table_is_not_empty(self):
        # An empty result is a FAILURE, not a clean run (CONTRIBUTING rule 2).
        self.assertGreaterEqual(
            len(self.rows), MIN_EDGES,
            "questline_dag.tsv holds %d edges; %d were derived on 2026-07-28. A SHRINK means a "
            "producer went blind -- find out which corpus stopped joining before touching this "
            "number." % (len(self.rows), MIN_EDGES))
        targets = {r["target_flag"] for r in self.rows}
        self.assertGreaterEqual(len(targets), MIN_TARGETS,
                                "only %d distinct target checks" % len(targets))

    def test_every_sense_is_one_of_the_three_and_unknown_carries_a_basis(self):
        senses = {r["sense"] for r in self.rows}
        self.assertTrue(senses <= {"set", "clear", "unknown"},
                        "unexpected sense value(s): %s" % sorted(senses - {"set", "clear", "unknown"}))
        for r in self.rows:
            self.assertTrue(r["basis"].strip(),
                            "edge %s->%s has no `basis` -- a polarity with no stated rule is a guess"
                            % (r["source_flag"], r["target_flag"]))
        # A run where nothing in the EMEVD half is unknown means _CONTEXT_SENSE has grown a
        # catch-all default, which is precisely how a false prerequisite gets minted. Scoped to
        # lot_gates on purpose: the other producers have their own reasons to emit `unknown`
        # (esd-paths-disagree, enabler-alternation), so an all-corpora check would stay green while
        # the polarity table quietly started answering every question.
        self.assertTrue(
            any(r["sense"] == "unknown" for r in self.rows if r["tool"] == "lot_gates"),
            "not one lot_gates edge is `unknown`. That corpus provably contains constructs whose "
            "polarity is NOT encoded -- treasure-verb cross products (the same (check, gate) pair "
            "under both Enable and Disable) and accumulator forms. If none survive, _CONTEXT_SENSE "
            "has acquired a default and every one of those is now a coin-flip prerequisite.")

    def test_the_enabler_alternation_guard_actually_fires(self):
        """The guard `_enabler_sense` documents must EXIST, not merely be written down.

        It did not. The clause regex was `\\(([^()]*\\|\\|[^()]*)\\)`, and `EventFlag(` contains
        parentheses, so it could never match `WaitFor(EventFlag(a) || EventFlag(b))` -- the
        refusal was dead code, and the basis string "conjunctive" was being minted for disjunctive
        input. Nothing caught it: every fixture asserted an OUTCOME the fall-through happened to
        produce. So this calls the function directly on the shape the guard is FOR, which is the
        only kind of test that can tell a live guard from a decorative one (CONTRIBUTING rule 8:
        "what would make this pass while the bug is present?").
        """
        sense, basis = self.tool._enabler_sense(
            111, 999, "WaitFor(EventFlag(111) || EventFlag(222));")
        self.assertEqual((sense, basis), ("unknown", "enabler-alternation-not-a-requirement"),
                         "a flag OR'd with an unrelated flag is a SECOND WAY IN, not a requirement, "
                         "and must not be minted as `set`. Got %r/%r." % (sense, basis))
        # ...and the documented EXCEPTION must still work: an alternation with the check's OWN
        # acquisition flag is "already taken", so the other operand IS a requirement (f580600<-9146).
        sense, basis = self.tool._enabler_sense(
            9146, 580600, "WaitFor(EventFlag(580600) || EventFlag(9146));")
        self.assertEqual(sense, "set",
                         "the own-flag alternation exception stopped working; f580600 <- 9146 "
                         "depends on it. Got %r/%r." % (sense, basis))
        # A condition BELOW the enable call is not a precondition of it.
        sense, _b = self.tool._enabler_sense(
            15002805, 15007990, "if (EventFlag(15000800)) { ;; > WaitFor(EventFlag(15002805));")
        self.assertEqual(sense, "unknown",
                         "text after the `> ` marker sits BELOW the enable call and cannot be a "
                         "prerequisite; reading it as one invents a requirement.")

    def test_group_semantics_never_claims_more_than_the_data(self):
        """`any` and `all` are verdicts; `unknown` is the default and must stay the majority.

        The first version of this table documented EVERY alt_group as "alternatives -- need any
        one". A `treasure_enablers` group whose members are the `&&` conjuncts of one WaitFor read
        that way is an UNDER-constrained rule. So: no group may claim a semantics while its members
        disagree about sense, and the claiming groups must stay a minority of the multi-edge ones.
        """
        groups = collections.defaultdict(list)
        for r in self.rows:
            groups[r["alt_group"]].append(r)
        for key, members in groups.items():
            sem = {m["group_semantics"] for m in members}
            self.assertEqual(len(sem), 1, "group %s carries mixed semantics %s" % (key, sorted(sem)))
            sem = sem.pop()
            self.assertIn(sem, ("any", "all", "single", "unknown"), "group %s: %r" % (key, sem))
            if sem in ("any", "all"):
                senses = {m["sense"] for m in members}
                self.assertEqual(
                    len(senses), 1, "group %s claims semantics=%s while mixing senses %s. 'Any one "
                    "of these' and 'all of these' are both incoherent over a group holding a "
                    "prerequisite AND an exclusion." % (key, sem, sorted(senses)))
                self.assertNotIn("unknown", senses,
                                 "group %s claims semantics=%s with an unknown-sense member" % (key, sem))
        multi = {k: v for k, v in groups.items() if len(v) > 1}
        claiming = {k for k, v in multi.items() if v[0]["group_semantics"] in ("any", "all")}
        self.assertTrue(claiming, "NO multi-edge group claims a semantics -- f400191 (any) and "
                                  "f1039537050 (all) are both supposed to. The resolver has gone "
                                  "blind, not conservative.")
        self.assertLess(len(claiming), len(multi),
                        "EVERY multi-edge group claims a semantics. That is what the original bug "
                        "looked like: a default dressed as a verdict.")

    def test_group_downgrade_rule_is_exercised_directly(self):
        """The downgrade rule, fed the groups the corpus does not currently contain.

        Mutation-tested 2026-07-28: disabling the rule outright -- every group keeps its producer's
        hint, which is the original blocker restored -- left the ENTIRE suite green, because no
        group in today's data mixes senses or hints. A rule the data does not reach is a rule that
        rots, and asserting it only through the emitted table is asserting it not at all. So it is
        called here with synthetic groups.
        """
        def group(*pairs):
            return [{"group_semantics": h, "sense": s} for h, s in pairs]

        cases = [
            (group(("any", "set")), "single", "a one-member group is not a group"),
            (group(("any", "set"), ("any", "set")), "any", "uniform hint + uniform known sense"),
            (group(("all", "set"), ("all", "set")), "all", "same, for a conjunction"),
            (group(("any", "set"), ("any", "clear")), "unknown",
             "MIXED SENSES: 'any one of these' is incoherent when one member is a prerequisite and "
             "the other an exclusion"),
            (group(("any", "set"), ("any", "unknown")), "unknown",
             "a member with no known polarity cannot be part of a claimed group"),
            (group(("any", "set"), ("all", "set")), "unknown",
             "producers disagree about what the grouping IS"),
            (group(("unknown", "set"), ("unknown", "set")), "unknown",
             "no producer claimed anything, so neither does the group"),
        ]
        for members, expected, why in cases:
            got, _downgraded = self.tool._resolve_group_semantics(members)
            self.assertEqual(got, expected,
                             "group %s resolved to %r, expected %r -- %s"
                             % ([(m["group_semantics"], m["sense"]) for m in members],
                                got, expected, why))
        # The downgrade must also REPORT itself: a silent one is invisible in the emit header.
        _sem, downgraded = self.tool._resolve_group_semantics(group(("any", "set"), ("any", "clear")))
        self.assertTrue(downgraded, "a hint was discarded and the tool did not count it")
        _sem, downgraded = self.tool._resolve_group_semantics(
            group(("unknown", "set"), ("unknown", "set")))
        self.assertFalse(downgraded, "nothing was claimed, so nothing was downgraded")

    # -- B. corroboration (SPEC §6 tier 2) ---------------------------------
    def test_the_graph_refinds_what_the_hand_audits_found(self):
        world = self.notes["world"]
        targets = {int(r["target_flag"]) for r in self.rows}
        tagged = {f for f in targets if world.flag_ap.get(f) in world.missable}
        pct = round(100.0 * len(tagged) / max(1, len(targets)))
        self.assertGreaterEqual(
            pct, CORROBORATION_FLOOR_PCT,
            "only %d%% (%d/%d) of the graph's target checks are already missable-tagged; %d%% is the "
            "floor and 64%% was measured on 2026-07-28. The overlap with a year of hand audits is "
            "the ONLY evidence these edges are real rather than a corpus dumped into a tsv -- a "
            "collapse here means the flag/lot joins broke, not that the game changed."
            % (pct, len(tagged), len(targets), CORROBORATION_FLOOR_PCT))
        warnings.warn("[questline-dag] corroboration %d%% (%d/%d targets already missable-tagged); "
                      "%d edges, senses set/clear/unknown = %d/%d/%d"
                      % (pct, len(tagged), len(targets), len(self.rows),
                         sum(1 for r in self.rows if r["sense"] == "set"),
                         sum(1 for r in self.rows if r["sense"] == "clear"),
                         sum(1 for r in self.rows if r["sense"] == "unknown")), stacklevel=2)

    # -- C. the acceptance cases, from the COMMITTED table ------------------
    def test_acceptance_cases_survive_the_whole_pipeline(self):
        """SPEC §7, asserted on what was COMMITTED -- a hand-edit is invisible to a tool-only check."""
        for ok, label, detail in self.tool._acceptance(
                [{k: (int(v) if k in ("source_flag", "target_flag") and v.lstrip("-").isdigit()
                      else v) for k, v in r.items()} for r in self.rows]):
            self.assertTrue(ok, "ACCEPTANCE LOST: %s -- %s\nThe pipeline no longer reports a case it "
                                "was built for. Fix the derivation, never the fixture." % (label, detail))

    def test_fortissax_is_absent_and_that_absence_is_the_point(self):
        """The negative fixture, spelled out because it is the easiest one to delete by accident."""
        self.assertNotIn(
            "510110", {r["target_flag"] for r in self.rows},
            "f510110 (Fortissax) has APPEARED in questline_dag.tsv. That is a real finding, not a "
            "failure to paper over: an award-site corpus is not supposed to be able to see an "
            "arena-existence gate (SPEC §5). READ the new edge and its evidence, decide whether the "
            "widening is sound, and only then move this assertion.")

    # -- D. no drift with the other copy of the region resolver -------------
    def test_interior_source_regions_agree_with_the_independent_grace_oracle(self):
        """The region column, checked against an oracle that shares NO provenance with it.

        `tools/map_region_oracle.py` arbitrates map_id -> region through the GRACE JOIN
        (BonfireWarpParam warp -> mapTile, warp -> play_region, play_region -> gf region). This
        table's interior decode goes through `dungeon_regions.tsv`. Two different routes to the
        same answer, so a disagreement is a real defect in one of them rather than a copy drifting
        from its twin -- which is why this one runs unconditionally and the twin-copy check below
        is allowed to skip.
        """
        sys.path.insert(0, os.path.join(REPO, "tools"))
        import map_region_oracle                                    # noqa: PLC0415
        truth, meta = map_region_oracle.load_map_truth()
        if truth is None:
            self.skipTest("grace tables absent (%s) -- the oracle would run BLIND" % meta)
        checked = 0
        for r in self.rows:
            flag = str(r["source_flag"])
            # only the interior `MMSS7NNN` shape decodes to a single map; overworld tiles
            # legitimately straddle regions and are out of this arbiter's scope by design.
            if r["source_locator"] != "flag_decode" or len(flag) != 8 or flag[4] != "7":
                continue
            expected = truth.get("m%s_%s" % (flag[0:2], flag[2:4]))
            if not expected or not r["source_region"]:
                continue
            checked += 1
            self.assertIn(
                r["source_region"], expected,
                "source flag %s decodes to region %r in questline_dag.tsv, but the independent "
                "grace oracle says map m%s_%s is %s. One of the two joins is wrong -- find out "
                "which before shipping an edge that names a region."
                % (flag, r["source_region"], flag[0:2], flag[2:4], sorted(expected)))
        warnings.warn("[questline-dag] independent grace oracle agreed on %d interior source "
                      "region(s)" % checked, stacklevel=2)

    def test_region_column_agrees_with_the_cross_region_screen(self):
        """The two resolvers are separate COPIES; this is what stops them drifting silently.

        Skips where the screen cannot be imported (it needs pytest and an installed AP world), so
        it is live in the world-unit job and quiet in the AP-free generators job. That is why the
        independent-oracle check above exists and does not skip: a check that only runs in one job
        gates nothing in the other.
        """
        try:
            from . import test_gf_lot_gates_cross_region as screen
        except ImportError:
            sys.path.insert(0, HERE)
            try:
                import test_gf_lot_gates_cross_region as screen
            except BaseException as exc:              # noqa: BLE001 - pytest.skip raises BaseException
                self.skipTest("cross-region screen not importable here (%s)" % exc)
        try:
            resolve = screen._gate_region_resolver()
        except BaseException as exc:                  # noqa: BLE001 - the screen skips without its tsvs
            self.skipTest("the cross-region screen's resolver is unavailable here (%s); the drift "
                          "check needs both copies" % exc)
        checked = disagreed = 0
        for r in self.rows:
            if r["tool"] != "lot_gates" or r["source_locator"] != "flag_decode":
                continue
            checked += 1
            theirs = resolve(int(r["source_flag"]))
            if theirs and theirs != r["source_region"]:
                disagreed += 1
                self.fail("region DRIFT on source flag %s: questline_dag says %r, "
                          "test_gf_lot_gates_cross_region's resolver says %r. Two copies of one "
                          "join have diverged -- reconcile them, do not pick a winner."
                          % (r["source_flag"], r["source_region"], theirs))
        self.assertGreater(checked, 0,
                           "no flag_decode-located lot_gates rows to compare -- the drift check ran "
                           "BLIND, which is not the same as agreeing.")
        warnings.warn("[questline-dag] region resolver cross-check: %d row(s) compared, %d "
                      "disagreement(s)" % (checked, disagreed), stacklevel=2)

    # -- E. the candidates the older screen cannot see ----------------------
    def test_new_corpora_candidates_are_reported_not_silently_passed(self):
        """Loud on a GREEN run. A self-reported coverage number is not a safeguard unless something
        ACTS on it, and the thing acting here is a human reading the warning.

        `test_gf_lot_gates_cross_region` reads ONLY lot_gates.tsv and holds unprotected cross-region
        gates at zero there. This table adds esd_gifts and treasure_enablers, which that screen has
        never read -- so any unprotected cross-region edge from those two is a CANDIDATE nobody has
        ruled on. It is not asserted away and it is not asserted ON: a tile-straddle artifact and a
        real prerequisite look identical from here, and only the live-game oracle separates them.
        """
        world = self.notes["world"]
        news = [r for r in self.rows
                if r["tool"] != "lot_gates" and r["cross_region"] == "yes"
                and r["sense"] == "set"
                and world.flag_ap.get(int(r["target_flag"])) not in world.missable]
        if news:
            warnings.warn(
                "[questline-dag] %d unprotected cross-region PREREQUISITE candidate(s) from corpora "
                "the lot_gates screen does not read. Each needs a human verdict -- a tile-straddle "
                "border and a real gate are indistinguishable here:\n  %s"
                % (len(news), "\n  ".join(
                    "f%s [%s] <- f%s [%s] via %s (%s)"
                    % (r["target_flag"], r["target_region"], r["source_flag"],
                       r["source_region"], r["tool"], r["basis"]) for r in news)), stacklevel=2)
        # The lot_gates half stays at zero -- that bar is already held by the other screen, and a
        # regression there must fail HERE too rather than depend on which suite ran.
        old = [r for r in self.rows
               if r["tool"] == "lot_gates" and r["cross_region"] == "yes" and r["sense"] == "set"
               and world.flag_ap.get(int(r["target_flag"])) not in world.missable]
        self.assertFalse(old, "%d lot_gates cross-region PREREQUISITE edge(s) whose target is not "
                              "missable-tagged: %s" % (len(old), [r["target_flag"] for r in old]))

    # -- F. freshness + determinism ----------------------------------------
    def test_committed_table_is_not_stale(self):
        fresh = self.tool.emit(self.edges, self.tally, self.notes, path=None)
        with open(TABLE, encoding="utf-8", newline="") as fh:
            shipped = fh.read()
        self.assertEqual(shipped.replace("\r\n", "\n"), fresh,
                         "greenfield/questline_dag.tsv is STALE or hand-edited -- "
                         "run: python tools/build_questline_dag.py")

    def test_build_is_deterministic(self):
        again_edges, again_tally, again_notes = self.tool.build()
        self.assertEqual(self.tool.emit(again_edges, again_tally, again_notes, path=None),
                         self.tool.emit(self.edges, self.tally, self.notes, path=None),
                         "two builds from the same inputs differ -- the CI diff gate would be "
                         "permanently red (dict order? a timestamp? CRLF?)")


if __name__ == "__main__":
    unittest.main()
