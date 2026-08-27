"""SweepSlot may only nominate a member we are CONFIDENT is swept (er-archipelago#672).

SweepSlot's premise is that this world's progression only lands where a sweep trigger will hand it
over. A trigger that cannot fire turns that promise into a coincidence: the item sits on junk, the
player is told nothing, and there is no boss to go and kill.

MOTIVATING CASE (bobler, Discord 2026-08-14). Progression restricted to boss sweeps. He cleared
**19/19 Limgrave bosses** and finished at 235/332 with two progression checks still open:

    * Limgrave :: Mushroom - treasure - Murkwater Cave [f31007000]      swept by 31000850
    * Limgrave :: Warming Stone - near Limgrave Tower Bridge [f34107000] swept by 34100800

`34100800` is the Divine Tower of Limgrave: BOSS_HEALTHBARS records an EMPTY name, and
arena_graces.tsv's own header already lists it under `# unresolved_bosses`. `31000850` is Patches,
who yields rather than dying, so his defeat flag is never reached in normal play.

🛑 These assertions were written against the BROKEN behaviour first: with `skips={}` -- the
pre-fix expression -- both ap-ids ARE nominated, which is what `test_the_fix_is_load_bearing`
pins. Delete the gate and this file goes red rather than vacuous.

Run:  python greenfield/eldenring/tests/test_gf_sweep_slot_skips.py
"""
import importlib.util
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)


def _load(name):
    """Load a leaf data/contract module by path, so this runs with no AP install."""
    spec = importlib.util.spec_from_file_location(
        "gf_" + name + "_skipcheck", os.path.join(GF_PKG, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


CONTRACT = _load("contract")
_SWEEP_DATA = _load("boss_sweeps")
SWEEPS = _SWEEP_DATA.DUNGEON_SWEEPS
ARENA_REGIONS = _SWEEP_DATA.SWEEP_ARENA_REGION
MEMBER_REGIONS = _SWEEP_DATA.SWEEP_REGION
HEALTHBARS = _load("boss_healthbars").BOSS_HEALTHBARS

# bobler's two, resolved from data.py by FLAG rather than hard-coded ap-id: #249 renumbered the ap
# ids once already, and a test that pins the old number would pass for the wrong reason.
_TRIPLE = re.compile(r'\(\s*([\'"])(.*?)\1\s*,\s*(\d+)\s*,\s*(\d+)\s*\)')
with open(os.path.join(GF_PKG, "data.py"), encoding="utf-8", errors="replace") as fh:
    _AP_BY_FLAG = {t[3]: int(t[2]) for t in _TRIPLE.findall(fh.read())}

MUSHROOM_AP = _AP_BY_FLAG["31007000"]      # Murkwater Cave, swept by Patches
WARMING_STONE_AP = _AP_BY_FLAG["34107000"]  # Divine Tower of Limgrave, swept by nothing


class TestSweepSlotSkips(unittest.TestCase):

    def _surface_skips(self, arena_regions=ARENA_REGIONS):
        return CONTRACT.sweep_slot_skips(
            healthbars=HEALTHBARS, arena_regions=arena_regions, triggers=SWEEPS)

    def test_every_unaudited_trigger_is_withheld_from_the_surface(self):
        """#671 ruling: no authoritative arena row means no SweepSlot progression nomination."""
        unaudited = set(SWEEPS) - set(ARENA_REGIONS)
        # 2026-08-26 (#1066): 26 -> 24. Two of the residue were Demi-Human Queen Marigga
        # (2046400800) and the Jagged Peak Drake (2049410800), whose arenas Alaric had already
        # ruled in game on 2026-08-10; the rulings are now hand rows in boss_arena_rulings.tsv and
        # both triggers are AUDITED, so they leave this set and become eligible to nominate. That
        # is the census IMPROVING, which is the direction #671 wants; a rise means arena coverage
        # was lost and is to be diagnosed, not rebaselined.
        self.assertEqual(len(unaudited), 24,
                         "the audited-arena census changed; review the issue #671 residue")
        skips = self._surface_skips()
        self.assertTrue(unaudited <= set(skips),
                        "every unaudited trigger must fail closed for progression surface")
        for flag in unaudited:
            self.assertEqual(
                CONTRACT.nominate_sweep_slots({flag: SWEEPS[flag]}, skips=skips), set(),
                f"unaudited trigger {flag} contributed a SweepSlot surface entry")

    def test_adding_authoritative_arena_evidence_restores_eligibility(self):
        """The gate is audit-driven, not a permanent hand blacklist."""
        other_skips = CONTRACT.sweep_slot_skips(healthbars=HEALTHBARS)
        flag = min((set(SWEEPS) - set(ARENA_REGIONS)) - set(other_skips))
        before = self._surface_skips()
        audited = dict(ARENA_REGIONS)
        audited[flag] = "Limgrave"
        after = self._surface_skips(audited)
        self.assertIn(flag, before)
        self.assertNotIn(flag, after,
                         "an authoritative arena row must restore eligibility unless another skip applies")
        self.assertTrue(CONTRACT.nominate_sweep_slots({flag: SWEEPS[flag]}, skips=after))

    def test_missing_audit_table_fails_closed(self):
        """An empty-but-present audit table means every sweep is unaudited, not clean."""
        skips = self._surface_skips({})
        self.assertTrue(set(SWEEPS) <= set(skips))
        self.assertEqual(CONTRACT.nominate_sweep_slots(SWEEPS, skips=skips), set())

    def test_boblers_two_checks_are_not_nominated(self):
        """THE MOTIVATING CASE. Neither check may be a SweepSlot surface entry.

        Healthbars are passed explicitly, exactly as `progression_surface.sweep_slot_aps` passes
        them: `sweep_slot_skips()`'s own lazy import is package-relative and CANNOT resolve under
        `spec_from_file_location`, so a test that relied on the default would assert the degraded
        path and call it a pass -- see `test_the_lazy_default_degrades_SAFELY`."""
        nominated = CONTRACT.nominate_sweep_slots(
            SWEEPS, skips=CONTRACT.sweep_slot_skips(healthbars=HEALTHBARS))
        self.assertNotIn(MUSHROOM_AP, nominated,
                         "Murkwater Cave mushroom is swept by Patches, who never dies")
        self.assertNotIn(WARMING_STONE_AP, nominated,
                         "Divine Tower warming stone is swept by a trigger with no boss")

    # ---- #703: slots scale with the FOREIGN PLAYER COUNT ---------------------------------------

    def test_many_player_seeds_are_byte_unchanged(self):
        """⭐ THE CONTROL #703 ASKS FOR, asserted structurally rather than by diffing two seeds.

        `f(n) == 1` for every n at or above MAX_SLOTS_PER_SWEEP, and `slots=1` takes the identical
        branch the shipped code took -- so an 8-player seed cannot move. A fix that quietly reshaped
        many-player seeds is a different feature, and this is the assertion that says it did not."""
        skips = CONTRACT.sweep_slot_skips(healthbars=HEALTHBARS)
        shipped = CONTRACT.nominate_sweep_slots(SWEEPS, skips=skips)
        for n in range(CONTRACT.MAX_SLOTS_PER_SWEEP, CONTRACT.MAX_SLOTS_PER_SWEEP + 4):
            self.assertEqual(CONTRACT.slots_per_sweep(n), 1, f"{n} foreign players must stay at 1")
            self.assertEqual(
                CONTRACT.nominate_sweep_slots(SWEEPS, skips=skips,
                                              slots=CONTRACT.slots_per_sweep(n)),
                shipped,
                f"{n} foreign players must nominate exactly what today's build nominates")

    def test_solo_is_one_slot(self):
        """🛑 A solo seed has nowhere to send anything, so widening buys nothing -- and 0 partners
        must not reach the division."""
        self.assertEqual(CONTRACT.slots_per_sweep(0), 1)
        self.assertEqual(CONTRACT.slots_per_sweep(-1), 1, "a negative count is still solo")

    def test_the_shape_of_f_is_the_ruling(self):
        """The ruled shape: clamp(8 // n, 1, 8). Pinned because it is a JUDGEMENT, not a measured
        optimum -- the curve had no plateau by N=8 -- so a later change to it should be a decision
        someone makes on purpose and not a refactor."""
        self.assertEqual(
            [CONTRACT.slots_per_sweep(n) for n in range(1, 10)],
            [8, 4, 2, 2, 1, 1, 1, 1, 1])

    def test_more_slots_nominate_strictly_more(self):
        """The knob does something, and it only ever ADDS: a wider nomination is a superset, so no
        check that was on the surface at one slot falls off it at eight."""
        skips = CONTRACT.sweep_slot_skips(healthbars=HEALTHBARS)
        one = CONTRACT.nominate_sweep_slots(SWEEPS, skips=skips, slots=1)
        many = CONTRACT.nominate_sweep_slots(SWEEPS, skips=skips,
                                             slots=CONTRACT.MAX_SLOTS_PER_SWEEP)
        self.assertTrue(one, "witness: the one-slot nomination is not empty")
        self.assertGreater(len(many), len(one), "eight slots must nominate more than one")
        self.assertTrue(one <= many, "widening must never drop a check off the surface")

    def test_skips_still_nominate_nothing_at_every_width(self):
        """🛑 THE #672 GATE SURVIVES THE KNOB. A sweep that cannot fire must not put a check on the
        surface -- at ANY slot count. This is the constraint most likely to be lost by a widening,
        because the skip filter and the pick both live in the same loop."""
        skips = CONTRACT.sweep_slot_skips(healthbars=HEALTHBARS)
        for slots in (1, 2, 4, CONTRACT.MAX_SLOTS_PER_SWEEP):
            nominated = CONTRACT.nominate_sweep_slots(SWEEPS, skips=skips, slots=slots)
            self.assertNotIn(MUSHROOM_AP, nominated, f"slots={slots} reopened #672")
            self.assertNotIn(WARMING_STONE_AP, nominated, f"slots={slots} reopened #672")

    def test_the_pick_is_deterministic_and_draws_nothing(self):
        """🛑 PURE. `nominate_sweep_slots`'s docstring forbids drawing here -- `world.random` is
        consumed a different number of times depending on how hard fill works, so a draw would move
        the seed for everything downstream, and the census must reproduce the pick outside a
        generation at all. Repeated calls must be identical."""
        skips = CONTRACT.sweep_slot_skips(healthbars=HEALTHBARS)
        runs = [CONTRACT.nominate_sweep_slots(SWEEPS, skips=skips, slots=4) for _ in range(5)]
        self.assertEqual(len(set(runs)), 1, "the pick moved between identical calls")

    def test_the_fix_is_load_bearing(self):
        """🛑 The same call WITHOUT the gate nominates both -- so the assertions above are a real
        witness of the defect, not a restatement of whatever the code happens to do."""
        unguarded = CONTRACT.nominate_sweep_slots(SWEEPS, skips={})
        self.assertIn(MUSHROOM_AP, unguarded)
        self.assertIn(WARMING_STONE_AP, unguarded)

    def test_every_unnamed_trigger_is_skipped(self):
        """The derived half: a trigger BOSS_HEALTHBARS cannot name cannot be vouched for."""
        skips = CONTRACT.sweep_slot_skips(healthbars=HEALTHBARS)
        unnamed = [f for f, info in HEALTHBARS.items()
                   if not str((info[3] if len(info) > 3 else "") or "").strip()]
        self.assertTrue(unnamed, "fixture check: expected at least one unnamed trigger")
        for flag in unnamed:
            self.assertIn(flag, skips, f"unnamed trigger {flag} must be skipped")

    def test_patches_is_skipped_though_he_IS_named(self):
        """The declared half, and why it cannot be derived.

        Patches has a NAME in BOSS_HEALTHBARS, so no join over the shipped tables can exclude him --
        bobler's tracker even read "Patches ✅", because that is the check his ENCOUNTER grants, not
        the sweep's defeat flag."""
        skips = CONTRACT.sweep_slot_skips(healthbars=HEALTHBARS)
        for flag in (31000800, 31000850):
            self.assertIn(flag, skips)
            self.assertTrue(str(HEALTHBARS[flag][3]).strip(),
                            "fixture check: Patches is NAMED, so the derived half cannot catch him")

    def test_runtime_skips_are_the_declared_unfireable_subset_only(self):
        runtime = CONTRACT.runtime_sweep_skips()
        surface = CONTRACT.sweep_slot_skips(
            healthbars=HEALTHBARS, arena_regions=ARENA_REGIONS, triggers=SWEEPS)
        self.assertEqual(set(runtime), {31000800, 31000850})
        self.assertTrue(set(runtime) < set(surface),
                        "runtime fireability was conflated with the wider progression-safety bar")
        self.assertNotIn(34100800, runtime,
                         "an unnamed trigger is unaudited, not positively known unfireable")

    def test_every_skip_carries_a_reason(self):
        """ShopSlot's SHOP_SLOT_SKIPS shape: keyed by what is excluded, valued by WHY. A silent
        filter is how an exclusion outlives the reason for it."""
        for flag, reason in CONTRACT.sweep_slot_skips(healthbars=HEALTHBARS).items():
            self.assertIsInstance(reason, str)
            self.assertGreater(len(reason.strip()), 20, f"{flag} needs a real reason")

    def test_the_gate_only_removes(self):
        """It must never ADD a nomination -- the surface may shrink (the feasibility ladder widens
        to cover it), but a gate that grows the surface is a different feature."""
        guarded = CONTRACT.nominate_sweep_slots(
            SWEEPS, skips=CONTRACT.sweep_slot_skips(healthbars=HEALTHBARS))
        unguarded = CONTRACT.nominate_sweep_slots(SWEEPS, skips={})
        self.assertTrue(guarded.issubset(unguarded))
        self.assertLess(len(guarded), len(unguarded), "fixture check: the gate should bite")

    def test_the_lazy_default_degrades_SAFELY(self):
        """🛑 `sweep_slot_skips()` with no argument resolves BOSS_HEALTHBARS through a
        package-relative import. When that cannot resolve -- which is the case here, and would be
        the case for any caller loading contract.py by path -- it must fall back to the DECLARED
        set and never to 'skip everything' or 'skip nothing but crash'.

        This is why `progression_surface.sweep_slot_aps` passes the table explicitly instead of
        trusting the default: silently dropping the derived half would put the unfireable triggers
        straight back on the surface with no error anywhere."""
        self.assertEqual(set(CONTRACT.sweep_slot_skips()), {31000800, 31000850})

    def test_missing_healthbars_does_not_empty_the_surface(self):
        """🛑 If the healthbar table were unavailable, skipping on absence would silently disable
        SweepSlot everywhere and the ladder would widen with nobody the wiser. Only the DECLARED
        set survives that case."""
        skips = CONTRACT.sweep_slot_skips(healthbars={})
        self.assertEqual(set(skips), {31000800, 31000850})
        still = CONTRACT.nominate_sweep_slots(SWEEPS, skips=skips)
        self.assertGreater(len(still), len(SWEEPS) - 10)


def _split_triggers():
    """Triggers whose arena region and members' region are both known and DISAGREE (#523)."""
    return {t for t in SWEEPS
            if t in ARENA_REGIONS and t in MEMBER_REGIONS
            and ARENA_REGIONS[t] != MEMBER_REGIONS[t]}


class TestArenaMembersSplitSkip(unittest.TestCase):
    """#523: a SweepSlot candidate must co-region with the boss that triggers its sweep."""

    def _skips(self, member_regions=MEMBER_REGIONS):
        return CONTRACT.sweep_slot_skips(
            healthbars=HEALTHBARS, arena_regions=ARENA_REGIONS,
            member_regions=member_regions, triggers=SWEEPS)

    # 🛑 THE LIVE CORPUS NO LONGER CONTAINS A SPLIT (#1059, 2026-08-26), so these tests are driven
    # by a SYNTHETIC one instead of by whichever defect happened to be in the data.
    #
    # They used to assert `len(_split_triggers()) > 0` and use Jori (2052430800) as the named
    # fixture -- and that was the right shape while a split existed, because a skip rule with
    # nothing to skip is not tested. #1059 fixed the split at the source (the measured arena now
    # outranks the tile decode when a legacy boss picks its host region, and boss_area_regions.tsv
    # is re-folded through the live bucket spine), so Jori is no longer a split and the corpus is
    # at zero -- which is now asserted, in test_the_corpus_has_no_split_left below.
    #
    # Retiring the class was the other option and it is the wrong one: `sweep_slot_skips`' SPLIT
    # branch is live code that must keep working, and a branch whose only test needed a defect in
    # the data to fire is a branch that goes dark the moment the data is fixed. The fixture below
    # exercises it unconditionally and is stronger than what it replaces.
    SYNTH_TRIGGER = 999999800          # not a real defeat flag; never present in SWEEPS
    SYNTH_MEMBERS = [7770041, 7770047]

    def _synth(self):
        """A trigger whose arena region and members' region disagree, and nothing else does."""
        # NB dict(x, **{int: ...}) is a TypeError -- these tables are keyed by INT flags.
        triggers, arena = dict(SWEEPS), dict(ARENA_REGIONS)
        members, healthbars = dict(MEMBER_REGIONS), dict(HEALTHBARS)
        triggers[self.SYNTH_TRIGGER] = list(self.SYNTH_MEMBERS)
        arena[self.SYNTH_TRIGGER] = "Caelid"
        members[self.SYNTH_TRIGGER] = "Limgrave"
        healthbars[self.SYNTH_TRIGGER] = HEALTHBARS[10000800]
        return triggers, arena, members, healthbars

    def test_the_corpus_has_no_split_left(self):
        """#1059's ruling, at the surface this class guards: a boss may only grant checks in the
        region it is fought in. gen_data refuses to emit a split at all, so a non-empty set here is
        a regression, not a number to rebaseline."""
        # WITNESS: [] must mean "checked every trigger and none split", not "the tables are empty".
        self.assertGreater(
            len(ARENA_REGIONS), 150,
            "only %d trigger(s) carry an arena region -- _split_triggers() cannot see the corpus, "
            "so an empty result proves nothing" % len(ARENA_REGIONS))
        self.assertEqual(
            sorted(_split_triggers()), [],
            "an arena/members split is back (#1059). gen_data is supposed to refuse to emit one.")

    def test_no_split_trigger_nominates_a_sweep_slot(self):
        triggers, arena, members, healthbars = self._synth()
        skips = CONTRACT.sweep_slot_skips(
            healthbars=healthbars, arena_regions=arena, member_regions=members, triggers=triggers)
        self.assertIn(
            self.SYNTH_TRIGGER, skips,
            "a split trigger (Limgrave members / Caelid arena) is not withheld -- a SweepSlot here "
            "places progression behind a boss the seed's region selection may exclude (#523)")
        self.assertEqual(
            CONTRACT.nominate_sweep_slots(
                {self.SYNTH_TRIGGER: triggers[self.SYNTH_TRIGGER]}, skips=skips), set(),
            "the split trigger still contributed a SweepSlot nomination")

    def test_the_split_skip_is_load_bearing(self):
        """RED-FIRST: without member_regions the split slips past every other source; supplying it
        is what catches it. Delete the SPLIT block in contract.py and this reds."""
        triggers, arena, members, healthbars = self._synth()
        without = CONTRACT.sweep_slot_skips(
            healthbars=healthbars, arena_regions=arena, triggers=triggers)
        self.assertNotIn(
            self.SYNTH_TRIGGER, without,
            "the fixture is caught even without member_regions -- the SPLIT source is not "
            "load-bearing here, so this differential proves nothing")
        with_regions = CONTRACT.sweep_slot_skips(
            healthbars=healthbars, arena_regions=arena, member_regions=members, triggers=triggers)
        self.assertIn(self.SYNTH_TRIGGER, with_regions,
                      "the fixture is not caught with member_regions -- the SPLIT source did not fire")

    def test_margit_co_regions_and_keeps_its_slot(self):
        # #523 regression fixture: _ARENA_REGION_CURATED put Margit's arena onto his members' region,
        # so he is NOT a split and his sweep still hosts a (Stormveil) SweepSlot.
        margit = 10000850
        self.assertEqual(
            ARENA_REGIONS.get(margit), MEMBER_REGIONS.get(margit),
            "Margit's arena and members no longer agree -- gen_data._ARENA_REGION_CURATED[10000850] regressed")
        self.assertEqual(ARENA_REGIONS.get(margit), "Stormveil",
                         "Margit did not co-region onto Stormveil")
        skips = self._skips()
        self.assertNotIn(
            margit, skips,
            "Margit is withheld from SweepSlot -- the override was meant to make his slot VALID, not skip it")
        self.assertTrue(
            CONTRACT.nominate_sweep_slots({margit: SWEEPS[margit]}, skips=skips),
            "Margit's sweep nominates no SweepSlot despite co-regioning -- his slot was lost")



if __name__ == "__main__":
    unittest.main()
