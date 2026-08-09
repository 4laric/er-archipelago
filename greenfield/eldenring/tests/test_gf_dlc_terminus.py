"""A dlc_only seed ENDS ON PROMISED CONSORT RADAHN -- not on whatever the draw happened to keep.

THE MOTIVATING CASE (CONTRIBUTING rule 11), and it is a player-support cost, not a crash.
bobler finished a `dlc_only` run on 2026-08-07 and reported that "the ending didn't work". His
slot_data: `goalLocations = [7770775]` -- Romina, Saint of the Bud -- over six kept regions, none of
them Enir Ilim. Nothing had malfunctioned. Romina carries a Remembrance, so `_is_terminus` says yes,
and she was the deepest terminus his draw kept. The ladder ran exactly as written.

The defect was one layer up, and it is an ASYMMETRY between the two terminus regions:

    |                 | base game                   | DLC                                 |
    | terminus        | Ashen Capital (Elden Beast) | Enir Ilim (Promised Consort Radahn) |
    | in REGIONS?     | NO -- never rollable        | YES -- one of the thirteen          |
    | auto ends there | ALWAYS                      | only if the draw kept it            |

SPEC-ashen-capital-lock guaranteed the base-game terminus by making it a region you cannot roll.
The DLC never got the equivalent, so Radahn was the ending by lottery. These tests are that
guarantee: Enir Ilim is barred from the draw, force-kept, named outright by the goal ladder, and
never allowed to open the run.
"""
import random

import pytest

pytest.importorskip("worlds.eldenring")
from worlds.eldenring.region_spine import (SPINE, compute_kept, base_regions,  # noqa: E402
                                           dlc_regions, REGION_PARENT)
from worlds.eldenring.data import LOCATIONS  # noqa: E402
from worlds.eldenring.features.goal_locations import (  # noqa: E402
    DLC_TERMINUS_REGION, auto_forced_regions, dlc_terminus_active, terminal_goal_ids,
    _major_boss_ids)
from worlds.eldenring.features.start_grace import pick_anchor_regions  # noqa: E402

DLC_POOL = sorted(dlc_regions())
BASE_POOL = sorted(base_regions())
PCR_IDS = set(_major_boss_ids(DLC_TERMINUS_REGION))
# Romina. The id bobler's client actually reported, hard-coded so this test names the seed it came
# from rather than re-deriving whatever the current data happens to call the Ancient Ruins' major.
ROMINA = 7770775

CHECK_COUNTS = {r: len(LOCATIONS.get(r, ())) for r in SPINE}


def _kept(n, seed, pool=DLC_POOL):
    """compute_kept exactly as core calls it: forced and barred come from the same resolved pool."""
    forced = auto_forced_regions(pool)
    return compute_kept(n, random.Random(seed), pool, forced=forced, bar_from_draw=forced)


class TestTheGuarantee:
    def test_the_romina_seed_can_no_longer_happen(self):
        """His exact shape -- dlc_only, six regions, `goal: auto` -- over 200 draws."""
        for seed in range(200):
            kept = _kept(6, seed)
            assert DLC_TERMINUS_REGION in kept, f"seed {seed} kept {sorted(kept)}"
            region, ids = terminal_goal_ids(kept, "auto", finale_built=False, dlc_terminus=True)
            assert region == DLC_TERMINUS_REGION
            assert set(ids) == PCR_IDS
            assert ROMINA not in ids, "the run must not end on Romina any more"

    def test_the_ending_is_promised_consort_radahn_at_every_draw_size(self):
        # 1 is the interesting one (see below); 13 and 20 run the full-pool branch, where the bar
        # must NOT have deleted the terminus.
        for n in (0, 1, 2, 3, 6, 13, 20):
            for seed in range(25):
                kept = _kept(n, seed)
                assert DLC_TERMINUS_REGION in kept, f"n={n} seed={seed}: {sorted(kept)}"
                region, _ = terminal_goal_ids(kept, "auto", finale_built=False, dlc_terminus=True)
                assert region == DLC_TERMINUS_REGION, f"n={n} seed={seed}"

    def test_num_regions_one_means_one_region_to_play_PLUS_the_ending(self):
        """The point of barring the draw rather than only forcing the keep.

        Force-keeping alone, with Enir Ilim still in the pool, lets the draw spend the player's one
        region ON the region the run ends in -- a seed with nothing to play. Barred first, `n == 1`
        always yields a real region and the terminus, which is what the Ashen Capital gives a
        base-game seed by not being rollable at all."""
        for seed in range(100):
            kept = _kept(1, seed)
            assert DLC_TERMINUS_REGION in kept
            playable = [r for r in kept if r != DLC_TERMINUS_REGION]
            assert playable, f"seed {seed}: the terminus is the ONLY kept region"

    def test_a_shattering_still_contains_the_terminus(self):
        """`num_regions: 0` means the whole eligible map. The draw bar must not remove a region
        from the SEED -- only from the sample -- or a Shattering would be missing its own ending."""
        kept = _kept(0, 1337)
        assert set(kept) == set(DLC_POOL)


class TestItNeverOpensTheRun:
    def test_enir_ilim_is_never_the_opening_region(self):
        for seed in range(300):
            kept = _kept(4, seed)
            picks, rules, _ = pick_anchor_regions(
                kept, random.Random(seed + 9000), CHECK_COUNTS, set(dlc_regions()), n=1,
                gated=frozenset(REGION_PARENT),
                never_anchor=frozenset({DLC_TERMINUS_REGION}))
            assert picks[0] != DLC_TERMINUS_REGION, f"seed {seed}: opened on the ending"
            assert "degraded" not in rules[0], (
                f"seed {seed}: the bar emptied the pool, so the force-keep upstream failed")

    def test_it_is_not_an_extra_start_region_either(self):
        for seed in range(100):
            kept = _kept(6, seed)
            picks, _, _ = pick_anchor_regions(
                kept, random.Random(seed + 4200), CHECK_COUNTS, set(dlc_regions()), n=3,
                gated=frozenset(REGION_PARENT),
                never_anchor=frozenset({DLC_TERMINUS_REGION}))
            assert DLC_TERMINUS_REGION not in picks

    def test_the_bar_degrades_and_says_so_rather_than_raising(self):
        """A kept set of nothing BUT the terminus cannot come out of core -- the force-keep is
        additive -- but a bar that raised would turn a hypothetical into a crash, and the rule
        string is how a degraded pick announces itself (CONTRIBUTING: runtime visibility)."""
        picks, rules, _ = pick_anchor_regions(
            [DLC_TERMINUS_REGION], random.Random(1), CHECK_COUNTS, set(dlc_regions()), n=1,
            never_anchor=frozenset({DLC_TERMINUS_REGION}))
        assert picks == [DLC_TERMINUS_REGION]
        assert "degraded" in rules[0] and "goal region" in rules[0]


class TestANamedGoalIsCoveredByTheSameRule:
    """`goal: promised_consort` force-kept Enir Ilim and then let it OPEN the run.

    The bar core applies is the seed's forced set, not a hardcoded region, so the named goal and
    `auto` are covered by one rule. MEASURED on main before the fix, 20k draws per row:
    num_regions=1 -> 59.6% of seeds opened on Enir Ilim, 3 -> 28.5%, 6 -> 14.7%, 10 -> 8.8%.
    `never_extra` did not catch it (that set is GOAL_REGION, i.e. Leyndell) and neither did
    `gated` (Enir Ilim is not a REGION_PARENT child)."""

    def test_promised_consort_cannot_open_on_its_own_goal(self):
        forced = ("Enir Ilim",)
        for seed in range(300):
            kept = compute_kept(3, random.Random(seed), DLC_POOL, forced=forced,
                                bar_from_draw=forced)
            picks, _, _ = pick_anchor_regions(
                kept, random.Random(seed + 77), CHECK_COUNTS, set(dlc_regions()), n=1,
                gated=frozenset(REGION_PARENT), never_anchor=frozenset(forced))
            assert picks[0] != DLC_TERMINUS_REGION, f"seed {seed}: opened on the named goal"


class TestBaseGameSeedsAreUntouched:
    def test_the_base_game_forces_nothing_and_bars_nothing(self):
        """The emptiness is load-bearing: SPEC-ashen-capital-lock deleted the old GOAL_REGION
        force-keep so that `num_regions: 1` really keeps one region. This must not put one back."""
        assert auto_forced_regions(BASE_POOL) == ()
        assert not dlc_terminus_active(BASE_POOL)

    def test_a_base_and_dlc_seed_is_not_a_dlc_terminus_seed(self):
        """Tier 0b must be mutually exclusive with tier 0. The finale owns any seed with the base
        game in play, even one whose draw happened to take only DLC regions."""
        assert not dlc_terminus_active(BASE_POOL + DLC_POOL)
        assert auto_forced_regions(BASE_POOL + DLC_POOL) == ()

    def test_the_rng_stream_does_not_move_for_a_base_game_seed(self):
        """Byte-identical: an empty bar must take the same path through rng.sample as no bar at
        all, or every base seed already rolled re-rolls differently."""
        for n in (1, 3, 8):
            for seed in range(40):
                before = compute_kept(n, random.Random(seed), BASE_POOL)
                after = compute_kept(n, random.Random(seed), BASE_POOL,
                                     forced=auto_forced_regions(BASE_POOL),
                                     bar_from_draw=auto_forced_regions(BASE_POOL))
                assert before == after, f"n={n} seed={seed}"
