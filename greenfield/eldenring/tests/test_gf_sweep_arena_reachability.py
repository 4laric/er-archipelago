"""A sweep group's TRIGGER must be reachable in the seed that ships the group -- issue #445.

THE MOTIVATING CASE (CONTRIBUTING rule 11), and it is a fixture below, by name.

    boblerrr, 2026-08-07, F6 tracker: `Shadow Keep 124/270`, "all bosses dead except hippo which
    i can't fight". His seed kept Ancient Ruins, Belurat, Cerulean, Charo's, Jagged Peak and Shadow
    Keep. The Golden Hippopotamus's 104-member sweep is a SHADOW KEEP group, but the arena you
    stand in to kill it is PlayRegionParam bucket 69000 = m61_48_45 = SCADU ALTUS, which his seed
    did not keep. `er_logic::region_lock::kick_decision` ejects him before the fight, so the trigger
    could never fire and the group was dead on arrival -- while the client cheerfully rendered
    "Shadow Keep -- 0/104 checks [flag 21000850] -- waiting on the boss".

The July 2026 fix (greenfield/region_overrides.tsv) re-homed the Hippo's DROP to Scadu Altus and
explicitly left the filler SWEEP in Shadow Keep. Re-homing the reward was right. Leaving the sweep
was the unexamined half: a kept region shipped 38% of its checks behind a trigger in a region the
roll may not have kept, and nothing forbade the combination.

WHAT THIS IS NOT. The members are NOT stranded and never were -- measured 2026-08-07:

  * all 201 members of the 6 mismatched groups are ordinary rows in `data.LOCATIONS`, so each one
    is in `locationFlags` for its kept region and is collected by walking to it;
  * 0 of the 201 carry ANY location tag, so none is on any progression surface and
    `confine_foreign_progression` (a share, 100 by default) already refuses another player's advancement
    there -- the same measurement the gesture bar records in gen_data.py;
  * all 87 coordinate-bearing Hippo members sit in m21_00 = bucket 21000 = Shadow Keep ground, and
    all 53 coordinate-bearing Margit members in m10_00/m10_01 = Stormveil ground, so none of them
    stands on the arena's ground either.

So the defect is a LOST CONVENIENCE plus a tracker row that promises something the seed cannot
deliver. That is worth fixing and it is not worth over-fixing: dropping the group is right, deleting
the checks would not be.

Run:  python3 greenfield/eldenring/tests/test_gf_sweep_arena_reachability.py
"""
import importlib.util
import os
import sys
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF = os.path.dirname(HERE)                      # .../eldenring
GREENFIELD = os.path.dirname(GF)                # .../greenfield


def _install_ap_stubs():
    """Stub the AP modules `features/boss_locks.py` imports at module scope, so this suite runs in
    the AP-FREE tier too (same idiom as test_gf_progression_surface)."""
    if "Options" not in sys.modules:
        opt = types.ModuleType("Options")

        class _Base:
            def __init__(self, *a, **k):
                pass

        class _Visibility:
            spoiler = 0
            none = 1
            all = 2

        for _n in ("OptionList", "Choice", "Toggle", "DefaultOnToggle", "Range"):
            setattr(opt, _n, type(_n, (_Base,), {}))
        opt.Visibility = _Visibility
        sys.modules["Options"] = opt
    if "BaseClasses" not in sys.modules:
        bc = types.ModuleType("BaseClasses")

        class _IC:
            filler = 0
            progression = 1
            useful = 2

        bc.ItemClassification = _IC
        sys.modules["BaseClasses"] = bc


def _load(modname, relpath):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(GF, relpath))
    m = importlib.util.module_from_spec(spec)
    sys.modules[modname] = m
    spec.loader.exec_module(m)
    return m


_install_ap_stubs()
if "eldenring" not in sys.modules:
    _pkg = types.ModuleType("eldenring"); _pkg.__path__ = [GF]; sys.modules["eldenring"] = _pkg
    _fpkg = types.ModuleType("eldenring.features")
    _fpkg.__path__ = [os.path.join(GF, "features")]; sys.modules["eldenring.features"] = _fpkg

_load("eldenring.contract", "contract.py")
_load("eldenring.registry", "registry.py")
_load("eldenring.data", "data.py")
_load("eldenring.region_spine", "region_spine.py")
_load("eldenring.boss_data", "boss_data.py")
_load("eldenring.boss_sweeps", "boss_sweeps.py")
_load("eldenring.boss_healthbars", "boss_healthbars.py")
_load("eldenring.features.legible_keys", "features/legible_keys.py")
bl = _load("eldenring.features.boss_locks", "features/boss_locks.py")
sw = sys.modules["eldenring.boss_sweeps"]
data = sys.modules["eldenring.data"]

DS = sw.DUNGEON_SWEEPS
SR = sw.SWEEP_REGION
AR = getattr(sw, "SWEEP_ARENA_REGION", None)

# The trigger, the region its 104 members live in, and the region its arena stands in. Named
# constants rather than a literal in one assertion, because rule 11 wants the exemplar to survive a
# regen that renumbers everything around it.
HIPPO = 21000850
# ⭐ #885 (2026-08-19): the Hippo GRADUATED from the split set. His members' region is now the
# arena's own -- Alaric ruled the Hippo presents as Scadu Altus everywhere, and
# gen_data.DUNGEON_REGION_CURATED["m21_00_00_00"] moved the granted checks onto that ruling -- so
# the group agrees with itself and #445's screen has nothing to drop. The bobler test below asserts
# the NEW shape of the motivating case; test_gf_hippo_region_ruling.py owns the ruling itself.
HIPPO_MEMBERS_REGION = "Scadu Altus"
HIPPO_ARENA_REGION = "Scadu Altus"
# boblerrr's seed, verbatim (2026-08-07). The acceptance test is HIS kept set, not a synthetic one.
# "Charo's" dropped 2026-08-10: it merged INTO Cerulean, which is already in his set, so the
# kept GROUND is unchanged -- only the name it goes by.
BOBLERRR_KEPT = frozenset({"Ancient Ruins", "Belurat", "Cerulean", "Jagged Peak",
                           "Shadow Keep"})

# Ratchet for the AUDIT, not for the defect. The predicate is permissive about an unknown arena on
# purpose (refusing them would delete member links on missing evidence). This floor is what stops
# that permissiveness from quietly widening: a regen that drops arena rows fails here instead of
# silently arming more unverifiable groups. RAISE it whenever coverage improves; never lower it
# without saying which rows went away and why.
#
# 2026-08-15: 112 -> 170. Not a new datamine -- boss_area_regions.tsv is unchanged. 58 triggers were
# filled from boss_arena_rulings.tsv, Alaric's own arena_region rulings from 2026-08-10 (commit
# 41e8fe7), which until now were consumed ONLY to re-region ambiguous checks and never for the
# arena question they literally answer. Coverage improving is exactly the case this comment says to
# raise for -- leaving the floor at 112 would let all 58 silently disappear again.
# 2026-08-15: 170 -> 192, in two steps. First 170 -> 190. Again not a new datamine. 20 triggers whose ARENA
# MAP carries a first-hand region of its own (dungeon_regions.tsv, source grace/connect) are now
# derived, ranked below both PlayRegionParam and the human rulings.
# 🛑 ALL 20 AGREE with their members' region -- zero new #445 screens, so this is coverage without a
# behaviour change. And tile decode is deliberately excluded: an overworld arena would be regioned by
# the same nearest-neighbour machinery as its members, so the two would agree BY CONSTRUCTION and
# this floor would be measuring a tautology.
# Then 190 -> 192: Alaric ruled the last two by name (Ancestor Spirit m12_08 and Regal
# Ancestor Spirit m12_09, both Siofra River). ALL 26 that remain are the circular
# overworld case -- so this floor is now one short of everything we are willing to claim.
# 2026-08-19 (#877): 192 -> 185 because seven legacy participant/activation triggers ceased to be
# sweeps at all (Deeproot 12030810..13, Gelmir 16000861, Enir Ilim 20010851/52). Their arena
# regions did not become unknown; the bogus triggers were removed and their members redistributed
# among the same fights' terminal flags. The denominator moved 218 -> 211 by the same seven.
ARENA_COVERAGE_FLOOR = 185


class SweepArenaTable(unittest.TestCase):
    """The generated table itself."""

    def test_the_arena_table_is_generated_at_all(self):
        self.assertIsNotNone(
            AR, "boss_sweeps.SWEEP_ARENA_REGION is missing -- gen_data.py no longer emits the arena "
                "join, so features/boss_locks falls back to 'every arena is reachable' and #445 is "
                "silently un-fixed. Regenerate (python greenfield/gen_data.py).")

    def test_sweep_arena_coverage_floor(self):
        """A self-reported coverage number is not a safeguard unless something ACTS on it."""
        self.assertGreaterEqual(
            len(AR), ARENA_COVERAGE_FLOOR,
            "arena-region coverage FELL to %d of %d triggers (floor %d). The predicate in "
            "boss_locks.sweep_trigger_reachable treats an unknown arena as reachable, so every row "
            "lost here becomes a group nothing can screen. Re-emit "
            "tools/datamine_boss_area_regions.py --emit, or justify the drop in this constant."
            % (len(AR), len(DS), ARENA_COVERAGE_FLOOR))

    def test_every_arena_value_is_a_real_region(self):
        """An arena naming a region that does not exist would be permanently unkept, i.e. it would
        drop its group in EVERY seed -- a silent deletion wearing a fix's clothes."""
        known = set(data.REGIONS) | set(SR.values())
        # WITNESS (test_gf_vacuous_pass): say out loud that the scan saw a table, so an empty
        # SWEEP_ARENA_REGION fails here instead of passing for the same reason a correct one does.
        self.assertGreater(len(AR), 100, "SWEEP_ARENA_REGION is empty or tiny -- this test would "
                                         "then pass by having looked at nothing")
        bad = {t: r for t, r in AR.items() if r not in known}
        self.assertEqual(bad, {}, "SWEEP_ARENA_REGION names unknown region(s): " + repr(bad))

    def test_the_arena_table_only_covers_live_triggers(self):
        self.assertTrue(set(AR) & set(DS), "WITNESS: no trigger is in both tables at all")
        self.assertEqual(sorted(set(AR) - set(DS)), [],
                         "SWEEP_ARENA_REGION has rows for triggers with no sweep group")


class SweepTriggerReachable(unittest.TestCase):
    """The predicate features/boss_locks actually calls."""

    def test_the_hippo_sweep_is_dead_in_boblerrrs_seed(self):
        """THE motivating case, end to end, by name (rule 11) -- IN ITS POST-#885 SHAPE.

        Before #885 this asserted the #445 screen dropped the group: bobler's seed keeps Shadow
        Keep without Scadu Altus, the members existed as Shadow Keep checks, and the unfireable
        trigger had to be screened out. #885 moved the members onto the arena's region (Scadu
        Altus), so in that same seed they are not created at all -- nothing is stranded and nothing
        on the tracker steers the player into the arena kick. The group is now ordinary
        out-of-scope filtering (the class test_a_group_whose_members_region_is_not_kept pins), and
        the drop-screen has nothing to do. Both halves asserted:"""
        self.assertIn(HIPPO, DS, "the Hippo's sweep group is gone from boss_sweeps")
        self.assertEqual(SR.get(HIPPO), HIPPO_MEMBERS_REGION,
                         "the Hippo's members' region left Scadu Altus -- the #885 ruling is "
                         "un-applied (see test_gf_hippo_region_ruling.py before touching this)")
        self.assertEqual(AR.get(HIPPO), HIPPO_ARENA_REGION,
                         "the Hippo's arena region is no longer Scadu Altus -- if boss_area_regions "
                         "changed, re-derive; if the join broke, #445 is back")
        self.assertNotIn(HIPPO_ARENA_REGION, BOBLERRR_KEPT)
        self.assertFalse(
            bl.sweep_trigger_reachable(HIPPO, BOBLERRR_KEPT),
            "boblerrr's seed does not keep Scadu Altus, so the Hippo's group is out of scope there")
        self.assertEqual(bl.unreachable_sweeps({HIPPO: DS[HIPPO]}, BOBLERRR_KEPT), {},
                         "the Hippo must be ORDINARY out-of-scope now, not a reported unfireable "
                         "group -- if he is back in the report, members and arena split again")

    def test_the_hippo_sweep_still_fires_when_scadu_altus_is_kept(self):
        """THE MIRROR (CONTRIBUTING rule 7's other half): prove the fix does not just delete the
        feature. A seed holding BOTH regions must keep the group exactly as before."""
        self.assertTrue(bl.sweep_trigger_reachable(
            HIPPO, BOBLERRR_KEPT | {HIPPO_ARENA_REGION}),
            "adding Scadu Altus to the kept set must restore the Hippo's sweep -- if it does not, "
            "the filter is deleting groups rather than screening them")

    def test_an_unknown_arena_is_permissive_and_that_is_deliberate(self):
        """48 triggers have no arena row (was 113 before the rulings landed). They stay armed, because refusing on missing evidence
        would delete 1686 member links. test_sweep_arena_coverage_floor is what keeps that honest."""
        unaudited = sorted(set(DS) - set(AR))
        self.assertTrue(unaudited, "no unaudited triggers left -- delete this test and the floor")
        t = unaudited[0]
        self.assertTrue(bl.sweep_trigger_reachable(t, {SR[t]}))

    def test_a_group_whose_members_region_is_not_kept_is_out_of_scope_not_a_defect(self):
        self.assertIn(HIPPO, DS, "WITNESS: the group being asked about must exist")
        self.assertFalse(bl.sweep_trigger_reachable(HIPPO, {"Limgrave"}))
        self.assertEqual(bl.unreachable_sweeps({HIPPO: DS[HIPPO]}, {"Limgrave"}), {},
                         "a group whose members' region is simply not kept is ordinary out-of-scope "
                         "filtering and must not be reported as an unfireable group")

    def test_the_predicate_is_pure_over_injected_tables(self):
        """Synthetic data, no globals -- so the rule can be reasoned about without a regen."""
        sr = {1: "A", 2: "A", 3: "B"}
        ar = {1: "B", 2: "A"}                      # 3 has no arena row -> unaudited
        self.assertFalse(bl.sweep_trigger_reachable(1, {"A"}, sr, ar))       # arena B not kept
        self.assertTrue(bl.sweep_trigger_reachable(1, {"A", "B"}, sr, ar))
        self.assertTrue(bl.sweep_trigger_reachable(2, {"A"}, sr, ar))        # arena == members
        self.assertTrue(bl.sweep_trigger_reachable(3, {"B"}, sr, ar))        # unknown -> permissive
        self.assertEqual(bl.unreachable_sweeps({1: [], 2: [], 3: []}, {"A"}, sr, ar),
                         {1: ("A", "B")})


class EveryMismatchedGroup(unittest.TestCase):
    """The whole corpus, not just the exemplar -- the coarsening that let #445 exist was that nobody
    ever asked the question over all 225 groups at once."""

    @classmethod
    def setUpClass(cls):
        cls.split = {t: (SR[t], AR[t]) for t in AR if AR[t] != SR.get(t)}

    def test_every_split_group_drops_without_its_arena_region(self):
        for t, (mem, arena) in sorted(self.split.items()):
            with self.subTest(trigger=t, members=mem, arena=arena):
                self.assertFalse(bl.sweep_trigger_reachable(t, {mem}),
                                 "group %d lives in %s but is fought in %s and must not be emitted "
                                 "into a seed that keeps %s alone" % (t, mem, arena, mem))
                self.assertTrue(bl.sweep_trigger_reachable(t, {mem, arena}))

    def test_no_matched_group_is_disturbed(self):
        """106 audited groups have arena == members. The fix must be a no-op for every one of them."""
        for t in sorted(set(AR) - set(self.split)):
            with self.subTest(trigger=t):
                self.assertTrue(bl.sweep_trigger_reachable(t, {SR[t]}))

    def test_the_split_set_is_the_measured_one(self):
        """Pinned so a regen that grows the mismatch set has to be explained rather than absorbed.
        Ashen Capital's two rows are inert -- that region is never rolled (#436) -- and are pinned
        anyway, because 'benign today' is a claim that rots (CONTRIBUTING rule 10).

        ⭐ SHRANK 6 -> 5 on 2026-08-09, and the INPUT got better rather than the predicate looser.
        2046450800 ("Gravesite" arena -> "Rauh Base" members, 24 member links) left because its 13
        members were on m61_46_45, a tile with no grace of its own that ANCHOR61 had hopped into
        Gravesite; play_region_buckets.tsv carries a Rauh Base row for that exact tile, and
        gen_data.TILE_ROW_REGION now reads it. The members moved onto the ground their arena is
        already on, so the group agrees with itself -- nothing about the arena, the trigger or this
        screen's predicate changed. See test_gf_tile_row_region.py.

        ⭐ GREW 5 -> 6 on 2026-08-17 by an explicit gameplay ruling, not a looser predicate.
        34100800 entered when m34_10 (Divine Tower of Limgrave) moved from Limgrave geography to
        Stormveil's runtime bucket for region locks (#202). Its arena remains grace-truth Limgrave,
        so the mismatch is real, intentional, and retained here as measured debt.

        ⭐ SHRANK 6 -> 5 on 2026-08-19 by ruling #885, the ASSIGNMENT moving rather than the
        predicate loosening: the Golden Hippopotamus (21000850, "Shadow Keep" -> "Scadu Altus",
        109 links, the group this screen was BUILT for in #445) left because his members now
        present as the arena's own region -- the group agrees with itself. The screen itself is
        unchanged and still holds the five below.

        ⭐ SHRANK 6 -> 4 on 2026-08-21 by ruling #523 (the ASSIGNMENT moving, not the predicate).
        Margit (10000850, "Stormveil" members -> "Limgrave" arena, 56 links) left: Alaric ruled
        "Margit belongs to Stormveil; the game data is decisive, superseding the 'Margit is outside'
        call on #202", so gen_data._ARENA_REGION_CURATED co-regions his arena onto his members. The
        region ID already agrees: his arena grace and the Castleward Tunnel are m10_00 (play bucket
        10000 = Stormveil). Only the Stormhill CLIFF you swing at him from (bucket 61010, m60_41_38)
        stays Limgrave -- it shares the tile with 8 early overworld checks -- see
        MargitArenaAndTunnelAreStormveil.

        ⭐ SHRANK 4 -> 0 on 2026-08-26 by #1059 -- an INPUT getting better, and the last four going
        at once. Alaric's ruling ("there shouldn't be any cross-region boss sweeps in general") made
        the split a forbidden state rather than measured debt, and both of its causes were fixable
        at the source:
          * 34100800, 11050800 and 11050850 were never real. boss_area_regions.tsv's `region`
            column is a generated SNAPSHOT of the bucket->region spine, and six of its 120 rows had
            not moved with it -- 11050 still filed under Leyndell after the Ashen Capital split,
            34100 still under Limgrave after #202, and two rows naming "Sewer", a region deleted by
            the 2026-08-20 Shunning-Grounds merge. gen_data now re-folds the BUCKET through
            region_groups.py, and all three agree with their members.
          * 2052430800 (Jori) was real, and is the one a player reported. A legacy boss's host
            region ranked the nearest-neighbour tile decode above its MEASURED arena, so the boss
            inherited its members' region by construction. The measured arena now wins; Jori hosts
            Scadu Altus and his five Abyssal checks were re-hosted onto Midra.

        🛑 THIS SCREEN IS NOT RETIRED. The drop machinery it guards is still live code, and the set
        being empty is now itself the assertion -- gen_data FAILS on a non-empty split
        (test_gf_sweep_region_containment). If a group ever appears here again, that is a
        regression to diagnose, not a number to rebaseline."""
        # WITNESS: {} must mean "every group agreed", not "no groups were examined".
        self.assertGreater(
            len(AR), 150,
            "only %d trigger(s) carry an arena region -- the split scan has stopped seeing the "
            "corpus, so an empty split set proves nothing" % len(AR))
        self.assertEqual(
            dict(self.split), {},
            "a sweep group's arena region differs from its members' region again (#1059). This is "
            "a REGRESSION, not a rebaseline: gen_data is supposed to refuse to emit one. Say which "
            "group appeared and whether boss_area_regions.tsv drifted from region_groups.py or a "
            "curated arena ruling moved a label without moving its members.")

    def test_the_split_groups_members_are_ordinary_reachable_checks(self):
        """The severity claim in the docstring, asserted rather than asserted-in-prose: every member
        of a dropped group is still a real location in its own region, so dropping the group costs
        convenience and not checks. If this ever fails, #445 IS a strand and the fix is not a drop."""
        if not self.split:
            # DELIBERATE, not accidental vacuity: #1059 drove the split set to zero at the source,
            # and the sibling test above asserts that emptiness. Keeping this loop alive (rather
            # than deleting the class) means the severity claim is re-checked the moment a split
            # ever comes back, instead of having to be rediscovered.
            self.skipTest("no arena/members splits remain (#1059 drove the set to 0); the empty "
                          "set is asserted by test_the_split_set_is_the_measured_one")
        by_ap = {ap: region for region, rows in data.LOCATIONS.items() for (_n, ap, _f) in rows}
        # WITNESS: the `missing`/`elsewhere` emptiness below must mean "looked and found none".
        # The old witness was `assertTrue(self.split)`, which #1059 retired along with the splits.
        self.assertGreater(len(by_ap), 4000,
                           "only %d location(s) loaded -- the membership join is broken and the "
                           "empty assertions below prove nothing" % len(by_ap))
        for t, (mem, _arena) in sorted(self.split.items()):
            missing = [a for a in DS[t] if a not in by_ap]
            self.assertEqual(missing, [], "group %d has member(s) absent from data.LOCATIONS: %r"
                             % (t, missing[:5]))
            elsewhere = sorted({by_ap[a] for a in DS[t]} - {mem})
            self.assertEqual(elsewhere, [],
                             "group %d (%s) has members living in %r" % (t, mem, elsewhere))


class LockGatesAgreeWithTheEmit(unittest.TestCase):
    """The two consumers must never disagree about which groups exist -- gating a member behind a
    boss key whose sweep is not emitted strands it behind a trigger that never fires, which is the
    exact bug `enabled_sweeps`'s docstring already warns about one level up."""

    def test_sweep_lock_gates_skips_an_unfireable_group(self):
        gates = bl._sweep_lock_gates(set(BOBLERRR_KEPT))
        self.assertNotIn(str(HIPPO), gates,
                         "sweepLockGates still routes the Hippo's dead group to a boss key -- the "
                         "client would render 'waiting on <lock>' for a fight the seed forbids")


class MargitArenaAndTunnelAreStormveil(unittest.TestCase):
    """#523: Margit is a Stormveil boss, and the region ID already agrees with that -- his arena
    grace (71001) and the Castleward Tunnel (grace 71002) are map m10_00, whose play-region bucket
    10000 belongs to Stormveil. This pins the natural model Alaric ruled to (2026-08-21): "the region
    ID maps onto Margit-as-Stormveil; the earlier 'Margit is outside' call on #202 was the exception,
    now reversed."

    The Stormhill CLIFF you physically stand on to swing at him is a DIFFERENT bucket -- 61010 =
    tile m60_41_38 -- and it stays Limgrave, because it shares the tile with 8 early Limgrave
    overworld checks (Stormhill Shack: Deathbird / Bell Bearing Hunter / Crucible Knight / Roderika's
    Golden Seed / the Warmaster's Shack approach). The kick is tile-bucket-coarse, so that ground
    cannot move without stranding them -- documented here so a future 'make Margit's ground Stormveil'
    change sees the cost before paying it."""

    @classmethod
    def setUpClass(cls):
        # REGION_PLAY_IDS is the SHIPPED kick-watch geometry (region -> measured PlayRegionParam
        # buckets), the table the kick actually reads -- and it is inside the eldenring package, so
        # it loads in the installed apworld. (region_groups.PLAY_REGION_GROUPS is a top-level
        # greenfield gen-input, NOT packaged, and is warp-menu ids anyway.)
        cls.play_ids = _load("eldenring.region_play_ids", "region_play_ids.py").REGION_PLAY_IDS

    def _owners(self, bucket):
        return [r for r, buckets in self.play_ids.items() if bucket in buckets]

    def test_the_tunnel_and_arena_bucket_counts_as_stormveil(self):
        # m10_00 -> bucket 10000: the Castleward Tunnel and Margit's arena grace both live here.
        owners = self._owners(10000)
        self.assertIn(
            "Stormveil", owners,
            "the Castleward Tunnel / Margit's arena bucket 10000 (m10_00) is not Stormveil -- "
            "owners=%r. Margit is a Stormveil boss and the region ID must agree (#523)." % (owners,))
        self.assertNotIn(
            "Limgrave", owners,
            "bucket 10000 (m10_00, Margit's arena / Castleward Tunnel) is Limgrave -- it must be "
            "Stormveil for the Margit-as-Stormveil model.")

    def test_the_stormhill_cliff_stays_limgrave(self):
        # 61010 = m60_41_38: the ground you stand on to fight Margit AND 8 early Limgrave overworld
        # checks. Moving it to Stormveil would strand those, so it stays Limgrave by design.
        owners = self._owners(61010)
        self.assertIn(
            "Limgrave", owners,
            "the Stormhill cliff bucket 61010 (m60_41_38) left Limgrave -- owners=%r. It shares the "
            "tile with 8 early overworld checks (Stormhill Shack); moving it strands them (#523)." % (owners,))



if __name__ == "__main__":
    unittest.main(verbosity=2)
