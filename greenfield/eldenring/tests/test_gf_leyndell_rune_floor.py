"""The armed Leyndell rune wall is never WEAKER than the vanilla capital gate.

MOTIVATING CASE (2026-08-01, from a player report on 0.2.18 -- "I had 2 great runes, but couldn't
enter leyndell itself to make progress"). Triaging that turned up a soundness hole one step away
from it: `features/leyndell_gate.generate_early` used to do

    want = min(want, len(world._available_runes()))

on the theory that lowering the requirement is always safe. It is not. Our N is data-driven; the
game's capital main gate is a FIXED two-Great-Rune possession wall that does not clamp with us. And
while our wall is ARMED, `features/graces.WALL_ARMED["Leyndell"]` withholds the capital grace
bundle, so the physical gate is the ONLY way in. At N=1:

    logic says   "one Great Rune opens Leyndell"   ->  fill may put a region Lock in the capital
    the game says "two, or the gate stays shut"    ->  the player cannot open it. Stranded.

Two ways to land on N=1 with no warning: `num_regions` (default 6) keeping exactly one Great-Rune
region, or the player simply writing `leyndell_runes_required: 1` in their yaml -- it is a
Range(0, 6) and 1 is selectable.

THE RULE THIS FILE GUARDS. `gf_leyndell_runes` is either EMPTY or holds AT LEAST
`VANILLA_CAPITAL_GATE_RUNES`. Never one. There is no third state.

🛑 WHAT "EMPTY" IS ALLOWED TO MEAN CHANGED ON 2026-08-12 (#589). The last sentence here used to read
"the disarmed state is the only safe response to a pool that cannot supply two runes." That was
wrong, and it was wrong in the direction that costs a run: disarming OUR wall does not disarm the
GAME'S, so a seed whose kept regions held one rune sealed Leyndell, the Sewer and Ashen Capital
behind a fixed two-rune gate nothing could open. LordChungle's 7-player seed 26505919849221796677
is the case -- unfinishable, with 42 other players' items stranded inside the sealed regions.

So a SHORT POOL IS NOW REPAIRED, NOT DISARMED: generate_early injects the missing Great Runes and
arms at the floor. Empty now means only what the player asked for -- `leyndell_runes_required: 0`,
item_shuffle off, or a sealed goal region.

NB the guard is deliberately stated over the ARMED SET, not over the option value: it is the set
`set_rules` and `graces.WALL_ARMED` both read, so it holds however a future caller arrives at it.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.features.leyndell_gate import (  # noqa: E402
    GOAL_REGION, GREAT_RUNES, VANILLA_CAPITAL_GATE_RUNES, _gated_region_names)
from worlds.eldenring.features.graces import WALL_ARMED  # noqa: E402

GAME = "Elden Ring"
UNBORN = "Great Rune of the Unborn"


def _assert_never_armed_below_vanilla(world):
    """The invariant, in one place: empty, or >= the vanilla constant."""
    runes = list(getattr(world, "gf_leyndell_runes", []))
    assert len(runes) != 1 or VANILLA_CAPITAL_GATE_RUNES <= 1, (
        f"Leyndell wall ARMED at {len(runes)} rune(s) ({runes}) but the vanilla capital gate is a "
        f"fixed {VANILLA_CAPITAL_GATE_RUNES}-rune wall and the capital graces are withheld while "
        f"armed -- logic would believe a door open that the game keeps shut")
    assert not runes or len(runes) >= VANILLA_CAPITAL_GATE_RUNES, (
        f"armed rune wall {runes} is below the vanilla floor {VANILLA_CAPITAL_GATE_RUNES}")
    # And the arming predicate graces.py reads must agree with what we just checked.
    assert WALL_ARMED["Leyndell"](world) == bool(runes)


class TestFlooredAtVanilla(WorldTestBase):
    """A yaml asking for ONE rune must not produce a one-rune wall."""
    game = GAME
    options = {"num_regions": 0, "leyndell_runes_required": 1}

    def test_asking_for_one_arms_at_vanilla_or_not_at_all(self):
        _assert_never_armed_below_vanilla(self.world)

    def test_all_base_regions_kept_means_it_arms_rather_than_disarms(self):
        # num_regions 0 keeps everything, so the pool has all six Great Runes and there is no
        # excuse to disarm -- the floor must ARM at 2, not silently drop the gate.
        assert len(GREAT_RUNES) >= VANILLA_CAPITAL_GATE_RUNES, "fixture assumes runes exist"
        assert len(self.world.gf_leyndell_runes) == VANILLA_CAPITAL_GATE_RUNES


class TestDefaultIsUnchanged(WorldTestBase):
    """The floor is a no-op on the shipped default -- this is a fix, not a difficulty change."""
    game = GAME
    options = {"num_regions": 0}

    def test_default_still_arms_at_two(self):
        _assert_never_armed_below_vanilla(self.world)
        assert len(self.world.gf_leyndell_runes) == VANILLA_CAPITAL_GATE_RUNES


class TestDisarmedStaysDisarmed(WorldTestBase):
    """0 still means 0 -- the floor must not resurrect a gate the player turned off."""
    game = GAME
    options = {"num_regions": 0, "leyndell_runes_required": 0}

    def test_zero_is_not_floored_up(self):
        assert self.world.gf_leyndell_runes == []
        assert WALL_ARMED["Leyndell"](self.world) is False


class TestAboveTheFloorIsUntouched(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "leyndell_runes_required": 4}

    def test_four_stays_four(self):
        _assert_never_armed_below_vanilla(self.world)
        assert len(self.world.gf_leyndell_runes) == 4


class TestScarceRunePoolIsRepairedNotDisarmed(WorldTestBase):
    """A kept capital with a short rune pool must be TOPPED UP -- never disarmed, never armed low.

    🛑 This class used to be `TestScarceRunePoolDisarmsRatherThanArmsLow` and asserted the OPPOSITE:
    that a short pool must leave the wall empty. It was green while the seeds it describes were
    unwinnable. A test can encode the defect, and this one did.

    🛑 It also asserted it VACUOUSLY. Its fixture was `num_regions: 2`, and Leyndell is not kept on
    a two-region draw, so `generate_early` bailed at the sealed-goal check on almost every seed and
    the assertion was reading a wall that was correctly absent. The two states look identical from
    `gf_leyndell_runes == []` and are not the same thing. The fixture below is the SHIPPED DEFAULT
    (`num_regions: 6`), the spread is filtered to seeds that actually keep the capital, and the
    class refuses to pass if the spread never produced a short pool.
    """
    game = GAME
    options = {"num_regions": 6}
    auto_construct = False
    SEEDS = range(16)

    def _goal_kept_seeds(self):
        """(seed, available runes) for every seed in the spread that actually keeps the capital."""
        out = []
        for seed in self.SEEDS:
            self.world_setup(seed)
            if GOAL_REGION in self.world._kept() and self.world._shuffle_on():
                out.append((seed, list(self.world._available_runes())))
        return out

    def test_the_pool_is_never_short_and_the_wall_arms(self):
        """🛑 REWRITTEN 2026-08-16 (#764): THE SHORT POOL THIS CLASS WAS BUILT ON CANNOT HAPPEN NOW.

        It used to require the spread to contain a seed with fewer than two runes on kept
        locations, drive the repair through `leyndell_gate`, and FAIL if no such seed turned up --
        `"the repair path never ran and this test is vacuous"`. That refusal was right, and it is
        what fired the moment all seven runes started being injected on every seed: there is no
        short pool left to find.

        The repair did not disappear, it MOVED and became unconditional (`features/great_runes`),
        for the reason the old one could not cover: it only ran when Leyndell was in the draw, so a
        seed without the capital got no top-up at all (bobler, seed 75791261719639771134 -- three
        regions, one rune in the whole multiworld).

        So this asserts the INVARIANT the seeds must satisfy rather than the mechanism that used to
        supply it -- the same correction #737 made to the region-major test. The wall's own rule
        (empty, or at least the vanilla floor -- never one) is unchanged and still checked here.
        """
        kept = 0
        for seed, avail in self._goal_kept_seeds():
            self.world_setup(seed)
            w = self.world
            kept += 1
            _assert_never_armed_below_vanilla(w)
            armed = list(w.gf_leyndell_runes)
            assert armed, (
                f"seed {seed}: the capital is kept, so the wall must be ARMED. Disarming it does "
                f"not disarm the game's fixed {VANILLA_CAPITAL_GATE_RUNES}-rune gate -- it just "
                f"seals Leyndell, the Sewer and Ashen Capital behind a door nothing opens (#589)")
            assert len(armed) >= VANILLA_CAPITAL_GATE_RUNES
            assert len(set(armed)) == len(armed), f"seed {seed}: duplicates in {armed}"
            # THE NEW INVARIANT: the supply no longer depends on the draw, so the pool is never
            # short and every armed rune is one fill can place without any repair at all.
            assert len(avail) == len(GREAT_RUNES), (
                f"seed {seed}: the pool holds {len(avail)} Great Rune(s), expected all "
                f"{len(GREAT_RUNES)} -- features/great_runes did not inject (#764)")
            assert set(armed) <= set(avail), (
                f"seed {seed}: armed {armed} names runes that are not in the pool")
            # The gate must no longer mint anything itself; that is great_runes' job now.
            assert not getattr(w, "gf_leyndell_injected", []), (
                f"seed {seed}: leyndell_gate injected {w.gf_leyndell_injected} -- the top-up moved "
                f"to features/great_runes and the wall must only READ the supply")
        assert kept, "no seed in the spread kept the capital -- this fixture proves nothing"

    def test_every_seed_holds_all_seven_capital_or_not(self):
        """The half the class above cannot see: a seed with NO capital.

        That is precisely the hole the old arrangement had -- the top-up lived in the capital's own
        feature, so a draw without Leyndell got none. This walks the whole spread, unfiltered."""
        checked = 0
        for seed in self.SEEDS:
            self.world_setup(seed)
            if not self.world._shuffle_on():
                continue
            checked += 1
            avail = list(self.world._available_runes())
            assert len(avail) == len(GREAT_RUNES), (
                f"seed {seed} (capital kept: {GOAL_REGION in self.world._kept()}): pool holds "
                f"{len(avail)} Great Rune(s), expected {len(GREAT_RUNES)}")
        assert checked, "no shuffle-on seed in the spread -- this test proves nothing"


class TestTheCapitalIsReachableOnAShortPool(WorldTestBase):
    """ACCEPTANCE (Rule 11) -- LordChungle's seed, as a test.

    Seed 26505919849221796677 (v0.3.9, 7 players) kept the capital with one countable Great Rune in
    the whole multiworld. Our wall disarmed; the game's did not. Leyndell -> Sewer -> Ashen Capital
    were unreachable, the run was unfinishable, and 42 other players' items were stranded inside.

    We cannot replay a foreign multiworld's draw, so the acceptance is the SHAPE, found on the
    SHIPPED DEFAULT (`num_regions: 6`) -- which is the part that matters: this was never an exotic
    configuration. Seeds 7 and 13 of this spread keep the capital with one available rune.

    Red before #589: `gf_leyndell_runes == []`, and the single Great Rune sits in the pool as
    filler. Per the five-runs rule, run the suite five times before calling this green.
    """
    game = GAME
    options = {"num_regions": 6}
    auto_construct = False

    def _short_supply_seed(self):
        """🛑 THE QUALIFIER CHANGED 2026-08-16 (#764) AND THE CLASS NAME IS NOW HISTORY.

        This used to demand `len(_available_runes()) < VANILLA_CAPITAL_GATE_RUNES` -- a seed whose
        kept regions could not supply the capital's two. All seven runes are injected on every seed
        now, so no such seed exists and this helper returned `None` on all sixteen, failing four
        acceptance tests with *"no default-settings seed in the spread keeps the capital on a short
        rune pool"*.

        The right response is NOT to widen the range (nothing wider will find one) and NOT to delete
        the tests: what they assert -- an armed rune exists as progression, is never placed behind
        the wall it opens, and the pool stays count-exact -- is the winnability property LordChungle's
        seed violated, and it must hold on EVERY capital seed, not just a scarce one. Scarcity was
        the trigger for the bug, never the subject of the assertion.

        So the qualifier is now simply "the capital is kept". The class keeps its name and this note
        so the #589 lineage stays findable.
        """
        for seed in range(16):
            self.world_setup(seed)
            w = self.world
            if GOAL_REGION in w._kept() and w._shuffle_on():
                return seed
        return None

    def _setup_short(self):
        seed = self._short_supply_seed()
        assert seed is not None, (
            "no default-settings seed in the spread keeps the capital at all, so this acceptance "
            "test would assert nothing -- widen the range rather than skipping")
        self.world_setup(seed)
        return seed

    @staticmethod
    def _my_items(w):
        """Every item that exists for this player: the unfilled pool PLUS everything already placed.

        🛑 `world_setup` runs a full generation, so by the time a test looks, progression items are
        ON LOCATIONS and `itempool` no longer holds them. Reading `itempool` alone says "the rune is
        not in the pool" about a rune that is placed and perfectly reachable -- which is how the
        first draft of this test failed against a working fix.
        """
        items = [i for i in w.multiworld.itempool if i.player == w.player]
        items += [l.item for l in w.multiworld.get_locations(w.player)
                  if l.item is not None and l.item.player == w.player]
        return items

    def test_the_wall_arms_and_every_armed_rune_exists_as_progression(self):
        seed = self._setup_short()
        w = self.world
        armed = list(w.gf_leyndell_runes)
        assert len(armed) >= VANILLA_CAPITAL_GATE_RUNES, (
            f"seed {seed}: wall is {armed} -- this is the #589 strand")
        assert WALL_ARMED["Leyndell"](w) is True
        by_name = {}
        for item in self._my_items(w):
            by_name.setdefault(item.name, item)
        for rune in armed:
            assert rune in by_name, (
                f"seed {seed}: armed rune {rune} exists nowhere in this player's items -- an armed "
                f"wall naming a rune fill never placed is the same unreachability in a new hat")
            assert by_name[rune].advancement, (
                f"seed {seed}: {rune} gates the capital but is not progression, so fill is free to "
                f"strand it behind the wall it opens")

    def test_no_armed_rune_is_placed_behind_the_wall_it_opens(self):
        """The winnability property itself, not a proxy for it.

        `set_rules` bars every GREAT_RUNE from the gated subtree via item_rule, which is the one
        rule `can_fill` honours unconditionally. This asserts the outcome rather than the guard --
        a rune sitting inside Leyndell or the Sewer is exactly the seed #589 describes, arrived at
        from the other direction.
        """
        seed = self._setup_short()
        w = self.world
        gated = _gated_region_names(w)
        armed = set(w.gf_leyndell_runes)
        for loc in w.multiworld.get_locations(w.player):
            region = getattr(getattr(loc, "parent_region", None), "name", None)
            if region in gated and loc.item is not None and loc.item.name in armed:
                raise AssertionError(
                    f"seed {seed}: {loc.item.name} opens the capital and was placed at "
                    f"{loc.name} inside {region}, which is behind it")

    def test_the_repair_is_count_neutral(self):
        """Injected runes ride core.create_items' filler tail, so items == locations still holds.

        Counted over everything that exists for the player (pool + placed) against every location
        the player owns -- AP's own fill would have blown up otherwise, but assert it here where
        the cause is legible instead of as a FillError three layers down.
        """
        seed = self._setup_short()
        w = self.world
        items = self._my_items(w)
        locations = w.multiworld.get_locations(w.player)
        assert len(items) == len(locations), (
            f"seed {seed}: {len(items)} items for {len(locations)} locations -- the injection was "
            f"not count-neutral")

    def test_the_unborn_rune_is_a_capital_rune_like_any_other(self):
        """🛑 DELETED CLAIM, 2026-08-16. This test used to assert the Unborn rune is never injected,
        on the stated ground that *"Great Rune of the Unborn is not a capital-gate rune; the game
        does not count it toward its two."* **That claim had no source and is probably false.**

        Alaric: *"what vanilla gate doesn't count Unborn? i believe they all do"* -- and the EMEVD
        agrees. `common.emevd $Event(6905)` maps every remembrance flag to a contiguous held-rune
        slot, `510010->171 ... 510200->176`, and `197->177`: SEVEN slots, one per Great Rune, the
        Unborn rune among them. A game that did not count it would not give it a slot in that block.
        (Nothing in the corpus READS 171-177, so the gate's count is engine-side and not decidable
        from the artifacts -- which is exactly why an uncited exclusion was the wrong response.)

        The old assertion was also about to become false on its own terms: all seven runes are
        injected on every seed now (#764), so "never injected" is simply not true of any of them.

        What is asserted instead is the invariant that survives: the Unborn rune is an ordinary
        member of the pool and of the armed set. Kept as a named test so the retracted claim leaves
        a trail rather than quietly vanishing from the suite."""
        self._setup_short()
        w = self.world
        assert UNBORN in w._available_runes(), (
            "the Unborn rune must be in the pool like the other six (#764)")
        armed = list(getattr(w, "gf_leyndell_runes", []))
        assert set(armed) <= set(w._available_runes()), (
            f"armed set {armed} names a rune that is not in the pool")
