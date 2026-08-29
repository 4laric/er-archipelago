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

     🛑 Including the one that used to be a pure NEGATIVE. f510110 (Fortissax) was asserted ABSENT
     because every corpus feeding this graph read an AWARD SITE, and what Fia's questline gates is
     whether the FIGHT EXISTS. The instruction attached to that assertion was: if a future widening
     makes it appear, READ the new edge, do not delete the assertion. #1085 is that widening -- the
     questline-condition extractor resolves the award's own guard cone, per branch, through the
     setters -- so the assertion was REWRITTEN to hold BOTH halves:
        (a) f510110 is STILL absent from the three award-site corpora. The blind spot is unchanged
            and is still what stops "the graph is populated" being read as "the class is covered".
        (b) f510110 IS present via `questline_conditions`, with its derived ancestry asserted by
            name (Deeproot map access, Champions f12030800, the Cursemark goods-8191 chain).
     The premise changed deliberately, and this is the motivating case standing as the acceptance
     test (CONTRIBUTING rule 11): the test below FAILS on main, because on main there is no
     extractor corpus and half (b) has nothing to find.

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
    that bar for the lot_gates corpus and holds it at zero. This table adds three corpora that
    screen has never read, and they surface candidates whose polarity/geometry a HUMAN has to rule
    on --
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
import tempfile
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
#
# 🛑 IT IS HELD ON A POPULATION, AND THE POPULATION IS THE THREE AWARD-SITE CORPORA -- unchanged by
# #1085. The extractor corpus added in #1085 has a different reach (it resolves the guard cone of
# EVERY award site, not only the ones an NPC hands over), so blending it in would move this ratio
# for a reason that has nothing to do with the joins the ratchet watches, and "the number changed
# because the population changed" is not a measurement. The extractor's own corroboration is
# REPORTED separately below and floored separately, lower and on purpose: 10% measured 2026-08-27.
AWARD_SITE_TOOLS = ("lot_gates", "esd_gifts", "treasure_enablers")
CORROBORATION_FLOOR_PCT = 50
EXTRACTOR_CORROBORATION_FLOOR_PCT = 5
# Same argument, opposite direction: a graph that shrinks has gone blind. 283 edges / 154 targets
# on 2026-07-28 (award-site corpora); 1513 edges / 441 targets on 2026-08-27 (extractor corpus).
# Per corpus, because a total would let one corpus go dark while another grew.
MIN_EDGES = 200
MIN_TARGETS = 120
MIN_EXTRACTOR_EDGES = 1000
MIN_EXTRACTOR_TARGETS = 300


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
        # An empty result is a FAILURE, not a clean run (CONTRIBUTING rule 2). Floored PER CORPUS:
        # a total floor stays green while one producer goes dark and another grows past it.
        award = [r for r in self.rows if r["tool"] in AWARD_SITE_TOOLS]
        self.assertGreaterEqual(
            len(award), MIN_EDGES,
            "the AWARD-SITE corpora hold %d edges; %d were derived on 2026-07-28. A SHRINK means a "
            "producer went blind -- find out which corpus stopped joining before touching this "
            "number." % (len(award), MIN_EDGES))
        targets = {r["target_flag"] for r in award}
        self.assertGreaterEqual(len(targets), MIN_TARGETS,
                                "only %d distinct award-site target checks" % len(targets))
        ext = [r for r in self.rows if r["tool"] == "questline_conditions"]
        self.assertGreaterEqual(
            len(ext), MIN_EXTRACTOR_EDGES,
            "the #1085 extractor corpus contributes %d edges; 1513 were derived 2026-08-27. If "
            "greenfield/questline_conditions.tsv went missing this is where you find out -- the "
            "table is a HAND EMIT (licensing-restricted artifacts, absent from CI), so an empty "
            "one reads as a clean tier-1 run unless something floors it." % len(ext))
        self.assertGreaterEqual(len({r["target_flag"] for r in ext}), MIN_EXTRACTOR_TARGETS,
                                "only %d distinct extractor target checks"
                                % len({r["target_flag"] for r in ext}))

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
        """The ratchet, on the population it was measured over: the three AWARD-SITE corpora.

        #1085 added a fourth corpus. Its targets are NOT added to this ratio -- see the note on
        CORROBORATION_FLOOR_PCT. Its own ratio is asserted immediately below, against its own
        floor, so the new corpus is measured rather than hidden behind the old one's number.
        """
        world = self.notes["world"]
        award = [r for r in self.rows if r["tool"] in AWARD_SITE_TOOLS]
        self.assertTrue(award, "no award-site rows at all -- the ratchet would run BLIND")
        targets = {int(r["target_flag"]) for r in award}
        tagged = {f for f in targets if world.flag_ap.get(f) in world.missable}
        pct = round(100.0 * len(tagged) / max(1, len(targets)))
        self.assertGreaterEqual(
            pct, CORROBORATION_FLOOR_PCT,
            "only %d%% (%d/%d) of the AWARD-SITE corpora's target checks are already "
            "missable-tagged; %d%% is the "
            "floor and 64%% was measured on 2026-07-28. The overlap with a year of hand audits is "
            "the ONLY evidence these edges are real rather than a corpus dumped into a tsv -- a "
            "collapse here means the flag/lot joins broke, not that the game changed."
            % (pct, len(tagged), len(targets), CORROBORATION_FLOOR_PCT))
        warnings.warn("[questline-dag] award-site corroboration %d%% (%d/%d targets already "
                      "missable-tagged); %d edges, senses set/clear/unknown = %d/%d/%d"
                      % (pct, len(tagged), len(targets), len(award),
                         sum(1 for r in award if r["sense"] == "set"),
                         sum(1 for r in award if r["sense"] == "clear"),
                         sum(1 for r in award if r["sense"] == "unknown")), stacklevel=2)

    def test_the_extractor_corpus_corroborates_separately_and_says_by_how_much(self):
        """#1085's corpus, measured on its own terms. A LOWER floor, argued rather than inherited.

        The extractor resolves the guard cone of EVERY award site in the EMEVD/ESD corpus, so its
        targets are mostly ordinary chest/enemy checks whose cone happens to be readable -- not the
        NPC handovers a missable audit concentrates on. Expecting the award-site corpora's 54%%
        here would be expecting a different population to behave like this one; expecting NOTHING
        would let a broken flag/lot join through unnoticed. So: floored low, and REPORTED, which is
        what makes a movement in it visible to a human.
        """
        world = self.notes["world"]
        ext = [r for r in self.rows if r["tool"] == "questline_conditions"]
        self.assertTrue(ext, "greenfield/questline_conditions.tsv contributed NO edges -- the "
                             "corpus is absent or stopped joining; an absent hand-emitted table "
                             "must not read as a clean run.")
        targets = {int(r["target_flag"]) for r in ext}
        tagged = {f for f in targets if world.flag_ap.get(f) in world.missable}
        pct = round(100.0 * len(tagged) / max(1, len(targets)))
        self.assertGreaterEqual(
            pct, EXTRACTOR_CORROBORATION_FLOOR_PCT,
            "the #1085 extractor corpus corroborates only %d%% (%d/%d) of its target checks against "
            "the missable tag set; %d%% is the floor and 10%% was measured 2026-08-27. A collapse "
            "here is a broken lot->flag join in the extractor, not a discovery."
            % (pct, len(tagged), len(targets), EXTRACTOR_CORROBORATION_FLOOR_PCT))
        warnings.warn("[questline-dag] #1085 extractor corpus: %d edges over %d targets, "
                      "corroboration %d%% (%d already missable-tagged); source placed for %d of "
                      "them (%d unplaced)"
                      % (len(ext), len(targets), pct, len(tagged),
                         sum(1 for r in ext if r["source_locator"]),
                         sum(1 for r in ext if not r["source_locator"])), stacklevel=2)

    # -- C. the acceptance cases, from the COMMITTED table ------------------
    def test_acceptance_cases_survive_the_whole_pipeline(self):
        """SPEC §7, asserted on what was COMMITTED -- a hand-edit is invisible to a tool-only check."""
        for ok, label, detail in self.tool._acceptance(
                [{k: (int(v) if k in ("source_flag", "target_flag") and v.lstrip("-").isdigit()
                      else v) for k, v in r.items()} for r in self.rows]):
            self.assertTrue(ok, "ACCEPTANCE LOST: %s -- %s\nThe pipeline no longer reports a case it "
                                "was built for. Fix the derivation, never the fixture." % (label, detail))

    def test_fortissax_is_absent_from_the_award_site_corpora_and_present_via_the_extractor(self):
        """The fixture that WAS `assertNotIn(510110)`, rewritten when the widening arrived.

        This is the motivating case of #1085 standing as its acceptance test (CONTRIBUTING rule
        11), and it is the test that would FAIL without the change: on main, half (b) finds nothing.
        Both halves are asserted, because deleting half (a) would quietly convert a documented blind
        spot into a covered one -- the exact misreading SPEC §5 and §9a were written to prevent.
        """
        fort = [r for r in self.rows if r["target_flag"] == "510110"]
        # (a) THE BLIND SPOT IS UNCHANGED. An award-site corpus pairs a flag test with an award in
        #     the same event; a gate on whether the FIGHT EXISTS leaves it no trace. If one of the
        #     three ever starts claiming to see this, that is a defect in that corpus, not progress.
        self.assertFalse(
            [r for r in fort if r["tool"] in AWARD_SITE_TOOLS],
            "an AWARD-SITE corpus has started emitting f510110 (Fortissax). It cannot see an "
            "arena-existence gate (SPEC §5), so this is a cross-product artefact leaking through, "
            "not a discovery: %s" % [(r["tool"], r["source_flag"], r["basis"]) for r in fort
                                     if r["tool"] in AWARD_SITE_TOOLS])
        # (b) AND THE WIDENING IS REAL. The #1085 cone extractor is not an award-site pairing: it
        #     resolves the remembrance award's own guard cone. The ancestry is asserted BY NAME so
        #     that a collapse of the cone walk (a budget exhausted in the wrong subtree, the
        #     talk-list menu gate going back to a per-file OR) fails HERE instead of silently
        #     restoring the old, comfortable absence.
        sources = {r["source_flag"] for r in fort if r["tool"] == "questline_conditions"}
        for want, why in (("map:m12_03", "Deeproot Depths must be REACHABLE -- the arena is in it"),
                          ("12030800", "Champions defeat: the band edge 4127 && 12030800 -> 4128 "
                                       "(common.emevd.dcx.js $Event(4139))"),
                          ("goods:8191", "the Cursemark of Death chain: t322001203_x41:914 sets "
                                         "f12039161 right after consuming goods 8191 at :913")):
            self.assertIn(want, sources,
                          "f510110's derived ancestry lost %s -- %s. The cone walk has gone "
                          "shallow; read the extractor's report before touching this list. "
                          "sources seen: %d" % (want, why, len(sources)))

    def test_the_phase1_self_gate_retractions_stay_retracted(self):
        """The path-scoped consumption rule, asserted where it can actually fail.

        Phase 1 of the extractor minted three prerequisites that phase 2 RETRACTED, each because
        the sharper slicing showed the root was a SELF-GATE -- a flag the awarding branch sets
        ITSELF, which is bookkeeping ("not already taken"), never a requirement:

          f400042 (Glowstone, `talk/.../t800001100.py` machines `_x68` -> `_x69`) carried
            DIALOGUE_STEP(f11009307), set BY the awarding branch at :1361. What survives is goods
            1210, consumed in `_x68` at :1319 on the path that calls `_x69` -- and it survives only
            because consumption is PATH-scoped (the consumption's guard stack must be contained in
            the statement's).
          f400041 (Perfume Bottle, `t800906000.py` `_x99`) carried DIALOGUE_STEP(f1043379223), a
            flag that occurs ONLY negated (`... and not GetEventFlag(1043379223)` at :1415) and is
            set at :1434, one line above the award at :1436.

        A DENYLIST would make this test pass while the rule that produced the retraction rotted --
        it would assert the symptom. So there is no denylist: the rule is ported (it lives in
        `path_consumes`/`consume_reqs` and in the per-branch `else` negation in `esd_ast.py`), and
        this asserts the rule's OUTPUT on the corpus, where a regression in the slicer shows up.
        """
        path = os.path.join(GREENFIELD, "questline_conditions.tsv")
        if not os.path.isfile(path):
            self.skipTest("greenfield/questline_conditions.tsv absent (hand emit)")
        with open(path, encoding="utf-8-sig", newline="") as fh:
            corpus = list(csv.DictReader(
                (ln for ln in fh if not ln.lstrip().startswith("#")), delimiter="\t"))
        self.assertTrue(corpus, "the extractor corpus parsed to ZERO rows")
        for target, bad, why in (("400042", "11009307", "set by the awarding branch at :1361"),
                                 ("400041", "1043379223", "occurs only NEGATED at :1415, set at "
                                                          ":1434, one line above the award")):
            hits = [r for r in corpus
                    if r["target_flag"] == target and r["source_id"] == bad
                    and r["source_kind"] == "flag"]
            self.assertFalse(hits, "f%s has regrown the phase-1 self-gate root f%s (%s). The "
                                   "per-branch slicing or the path-scoped consumption rule has "
                                   "regressed -- fix the slicer, do not filter the row."
                                   % (target, bad, why))
        # ...and the requirement the retraction was careful to KEEP must still be there, or this
        # test would pass just as well against an extractor that had gone blind entirely.
        self.assertTrue([r for r in corpus if r["target_flag"] == "400042"
                         and r["source_kind"] == "goods" and r["source_id"] == "1210"],
                        "f400042 lost ITEM_POSSESSION(goods 1210) -- the retraction dropped the "
                        "self-gates and KEPT the consumption; losing both is not the same result.")

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
                if r["tool"] in ("esd_gifts", "treasure_enablers") and r["cross_region"] == "yes"
                and r["sense"] == "set"
                and world.flag_ap.get(int(r["target_flag"])) not in world.missable]
        # ADJUDICATED 2026-07-28 by the live-game oracle (Alaric), which is the only thing that can
        # tell these apart. Both verdicts are now WIRED, not just recorded:
        #   f580600 <- f9146   REAL. "message from leda requires defeating messmer" -> tagged via
        #                      gen_data._ENABLER_CROSS_REGION; keeper test_gf_enabler_cross_region.
        #   f1039537050/60     NOT a gate. "a classic rise puzzle where you have to interact with
        #                      three objects near the rise to open the door" -- the AND-group is
        #                      real, but all three objects are AT the rise; the cross-region reading
        #                      is the Gelmir/Altus TILE BORDER. Adjudicated in that same keeper.
        # The warning below stays anyway: it reports the POPULATION, and its job is to be loud when
        # a NEW member appears. A screen that goes quiet once its known members are handled is a
        # screen that has stopped screening.
        if news:
            warnings.warn(
                "[questline-dag] %d unprotected cross-region PREREQUISITE candidate(s) from corpora "
                "the lot_gates screen does not read. f580600 and the f10395370xx pair were "
                "adjudicated 2026-07-28 (see test_gf_enabler_cross_region); ANY OTHER member is "
                "unruled -- a tile-straddle border and a real gate are indistinguishable here:\n  %s"
                % (len(news), "\n  ".join(
                    "f%s [%s] <- f%s [%s] via %s (%s)"
                    % (r["target_flag"], r["target_region"], r["source_flag"],
                       r["source_region"], r["tool"], r["basis"]) for r in news)), stacklevel=2)
        # #1085's corpus is reported as a POPULATION, not row by row: it contributes hundreds of
        # such candidates, and a 300-line warning is a wall nobody reads, which is the same as no
        # warning. It is also INERT by construction -- every extractor group carries
        # `group_semantics=unknown`, and this table's rule is that a consumer may act on `any`/`all`
        # only -- so no candidate here can become a rule without a human first proving the grouping.
        # What IS actionable is the shape of the population, so it is bucketed by target region.
        ext = [r for r in self.rows
               if r["tool"] == "questline_conditions" and r["cross_region"] == "yes"
               and r["sense"] == "set"
               and world.flag_ap.get(int(r["target_flag"])) not in world.missable]
        if ext:
            buckets = collections.Counter(r["target_region"] or "(unplaced)" for r in ext)
            warnings.warn(
                "[questline-dag] #1085 extractor corpus: %d unprotected cross-region PREREQUISITE "
                "candidate(s) over %d target check(s). NONE is a verdict -- a cone unions the arms "
                "of a disjunction, so these are an OVER-approximation, and every one of them "
                "carries group_semantics=unknown. By target region: %s"
                % (len(ext), len({r["target_flag"] for r in ext}),
                   ", ".join("%s %d" % kv for kv in sorted(buckets.items()))), stacklevel=2)

        # The lot_gates half stays at zero -- that bar is already held by the other screen, and a
        # regression there must fail HERE too rather than depend on which suite ran.
        old = [r for r in self.rows
               if r["tool"] == "lot_gates" and r["cross_region"] == "yes" and r["sense"] == "set"
               and world.flag_ap.get(int(r["target_flag"])) not in world.missable]
        self.assertFalse(old, "%d lot_gates cross-region PREREQUISITE edge(s) whose target is not "
                              "missable-tagged: %s" % (len(old), [r["target_flag"] for r in old]))

    # -- F. freshness + determinism ----------------------------------------
    def test_output_replace_does_not_open_existing_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = os.path.join(directory, "questline_dag.tsv")
            with open(destination, "w", encoding="utf-8") as fh:
                fh.write("old")

            self.tool._write_atomic(destination, "new\n")

            with open(destination, encoding="utf-8", newline="") as fh:
                self.assertEqual(fh.read(), "new\n")
            self.assertEqual(os.listdir(directory), ["questline_dag.tsv"])

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
