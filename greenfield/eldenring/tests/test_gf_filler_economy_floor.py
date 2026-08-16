"""TIER-A semantic gate: the filler tail has ONE budget, and the upgrade economy is entitled to its
share of it.

WHY THIS TEST EXISTS
--------------------
A live playtest seed on current HEAD (num_regions=4, the shipped frozen defaults, the playtest
`curated_filler` recipe) put the player in fill-sphere 2 holding a +0 weapon. Nothing raised, nothing
warned, every per-pass unit test stayed green -- because the defect is NOT inside any one pass. It is
an INTERACTION between three passes that each own a slice of the same filler tail and have no
contract with each other:

  1. features/pool_builder  (PASS 1, additive)   -- frozen at scope=all_filler / intensity=max /
     juice_cap=0 (defaults.py FROZEN_OPTIONS), it converts essentially the WHOLE junk-consumable
     larder into `useful`-classified gear.
  2. features/filler_curation.curate  (PASS 2, in-place swap) -- runs AFTER, and selects its
     candidates with `_is_junk_consumable(name) and not (classification & (progression|useful))`.
     pool_builder just marked the larder `useful`. curate() therefore finds an empty larder and the
     recipe's `stones:`/`runes:` weights deliver ~nothing.
  3. core.post_fill stone_ramp  (post-fill relabel) -- measures its deficit against the stones
     already placed, decides supply is adequate, and no-ops.

Three locally-correct mechanisms; one silently broken upgrade economy. This file is the regression
that makes that unrepresentable. It deliberately tests the COMPOSED DEFAULT PIPELINE -- the frozen
options exactly as shipped -- because a pass tested in isolation cannot see this class of bug. (Six
test_gf_pool_builder_*.py files and a filler_curation suite were all green while the seed was broken.)

THE ORACLES ARE DERIVED, NOT PINNED
-----------------------------------
Nothing here hardcodes an observed count (that would pin the symptom rather than the datum):

  * ENTITLEMENT: the vanilla junk-consumable items across the seed's KEPT regions are the larder --
    computed straight from LOCATIONS + LOCATION_ITEM + the shipped `_is_junk_consumable` predicate,
    with no pipeline involvement. A recipe category weighted w/W is entitled to (w/W) of that larder.
    Whoever ends up owning the filler tail, that entitlement must survive.
  * AFFORDABILITY: the early-stone floor is derived from the game's own upgrade ladder under the
    frozen `flatten_regular_upgrades`, not from a magic number. The contract is stated in player
    terms: a player who has cleared a realistic FRACTION of what is open to them at shallow depth
    must be able to afford a modest weapon level. Anything else is not a randomizer, it is a walk.

Both oracles are re-derived per seed, so they follow num_regions / the recipe / the flatten setting
instead of drifting away from them.
"""
import math
import re
from collections import Counter, defaultdict

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring.data import LOCATIONS, HUB  # noqa: E402
from worlds.eldenring.item_ids import ITEM_CATALOG, LOCATION_ITEM  # noqa: E402
from worlds.eldenring.features import filler_curation as fc  # noqa: E402
from worlds.eldenring.features import filler_budget as fb  # noqa: E402

from ._util import world_pool_items  # noqa: E402

GAME = "Elden Ring"

# The playtest recipe (greenfield/playtest-yamls/Alaric_shattering.yaml) -- the seed that broke.
PLAYTEST_RECIPE = {
    "throwables": 25, "pots": 15, "greases": 10, "foods": 12, "boluses": 6,
    "perfumes": 8, "rare": 1, "stones": 20, "runes": 20,
}

# A category's delivered share may fall this far below its entitlement before we call it starvation.
# Generous on purpose: the pipeline legitimately rounds, DLC-filters members, and pays real vanilla
# items at most checks. This gate is not tuning -- it fires only when a pass has been eaten whole.
SHARE_FLOOR = 0.50


def _whole_items(share):
    """`share` as a count of WHOLE items -- floor, because you cannot deliver a third of a stone.

    🛑 COMPARING AN INT COUNT TO A FLOAT THRESHOLD SILENTLY RAISES THE BAR BY UP TO ONE ITEM. On
    2026-08-15 this gate demanded `66 >= 66.239` and reported "the recipe's `stones: 20` weight
    bought nothing" -- of a 52.478-item entitlement it had delivered 26 against a 50% floor of
    26.239, i.e. 99.1% of the stated bar. A gate that asks for 51% while its own comment promises
    50% will find a boundary eventually, and its failure text will describe a starvation that did
    not happen.
    """
    return math.floor(share)

# Fraction of the checks open to them that a player has actually cleared when they are "in sphere N".
# Fill spheres are a 100%-COLLECTION artifact: sphere 0 of a 4-region seed is ~40% of the entire seed.
# Nobody clears 693 checks before moving on. stone_ramp's supply model assumes they do, which is the
# precise reason it concludes there is no deficit while the player stands at +0. A quarter is already
# a thorough player.
# ...and both constants are PROD's, imported rather than restated. features/filler_budget sizes the
# stone reservation against them (early_stone_floor), so the spec and the code satisfying it cannot
# drift. If you want to argue with the bar, argue with it there -- in one place.
COLLECTION_RATE = fb.COLLECTION_RATE
EARLY_TARGET_LEVEL = fb.EARLY_TARGET_LEVEL

_STONE_RE = re.compile(r"Smithing Stone \[(\d+)\]$")
_SOMBER_RE = re.compile(r"Somber Smithing Stone \[(\d+)\]$")


def _stones_needed(level_target, flatten):
    """{tier: count} of REGULAR smithing stones to reach +level_target. This is the GAME's ladder --
    vanilla costs 2/4/6 per level within a tier; `flatten` (frozen at 2) caps each level's cost. The
    same rule the client applies, restated here so the test owns its oracle rather than importing the
    code under test."""
    need = defaultdict(int)
    for lvl in range(1, min(level_target, 24) + 1):
        tier = (lvl - 1) // 3 + 1
        vanilla = (2, 4, 6)[(lvl - 1) % 3]
        need[tier] += min(vanilla, flatten) if flatten > 0 else vanilla
    return need


def _junk_larder(world):
    """The seed's TRUE filler budget, derived with zero pipeline involvement: every VANILLA item on a
    kept region's (or the hub's) location that the shipped predicate calls junk-consumable. This is
    what pool_builder's juice and curated_filler's recipe are both drawing from -- the shared resource
    that currently has no single owner."""
    n = 0
    for rn in [HUB] + list(world._kept()):
        for (_name, ap_id, _flag) in LOCATIONS.get(rn, []):
            nm = LOCATION_ITEM.get(ap_id)
            if nm and fc._is_junk_consumable(nm):
                n += 1
    return n


def _delivered(counts, categories):
    return sum(counts[m] for c in categories for m in fc.CATEGORIES.get(c, ()))


# The early-economy sample. ONE seed cannot answer a question about fill DENSITY: measured across
# seeds 0xE1DE7..+8 the early Smithing Stone [1] count ranges 23..47 against a floor of 24, so a
# single-seed assertion is a coin flip dressed as a gate -- it was red on ~1 seed in 5 regardless of
# what the code did, and 0xE1DE7 happens to be the worst draw in the sample. That is the same "it
# genned on my one yaml" error CONTRIBUTING names, pointed at a test instead of a generation.
#
# So the claim is distributional, which is also what the claim MEANS: "a player who has cleared a
# realistic fraction of the early game can afford a +3 weapon" is a statement about seeds in general,
# not about one seed. A TYPICAL seed must clear the floor (median), and the tail must not be fat
# (most seeds clear it). The bug this was written for -- 2026-07-01, sphere 2, still +0 -- starves
# every seed, so it drives the median straight through both gates.
EARLY_SAMPLE_SEEDS = tuple(0xE1DE7 + i for i in range(9))
# At most this many seeds in the sample may sit under the floor. 2/9 -- the measured tail is 1/9 for
# both the playtest and the shipped default recipe, so this has exactly one seed of slack.
EARLY_SAMPLE_MAX_UNDER = 2


def _units_of(name):
    """Copies a pooled item hands over. A stacked name is `<base> x<n>`; anything else is one.
    Split from the RIGHT because base names contain spaces and the tail is minted from a digit."""
    head, _, tail = name.rpartition(" x")
    return int(tail) if head and tail.isdigit() else 1


def _early_stone_counts(test, seed):
    """{tier: UNITS of that Smithing Stone in spheres 0-1} for one seed, post-fill.

    🛑 UNITS, NOT PLACEMENTS (#624). The bar this file states is "can the player afford +N", which
    is denominated in stones, not in pickups. Since #624 a location whose vanilla lot grants several
    copies pays a STACKED item (`Smithing Stone [2] x3`, one AP id carrying itemCounts 3), and
    `_STONE_RE.match` happily matches that name -- so counting rows here would score a x3 as ONE and
    understate the early economy by exactly the copies #624 recovered. Same units-vs-placements trap
    scadu_supply.natural_fragments had in #616; the fix is the same shape, read the quantity rather
    than keep a second copy of the rule."""
    from Fill import distribute_items_restrictive

    test.world_setup(seed=seed)
    distribute_items_restrictive(test.multiworld)   # spheres only exist post-fill
    player = test.world.player
    sphere_of = {}
    for s, locs in enumerate(test.multiworld.get_spheres()):
        for loc in locs:
            sphere_of[loc] = s
    test.assertTrue(sphere_of, "no fill spheres -- cannot evaluate reachability")

    by_tier = defaultdict(int)
    own = 0
    early = 0
    for loc in test.multiworld.get_locations(player):
        if loc.item is None or loc.item.player != player:
            continue
        own += 1
        is_early = sphere_of.get(loc, 99) <= 1
        early += is_early
        m = _STONE_RE.match(loc.item.name)
        if m and is_early:
            by_tier[int(m.group(1))] += _units_of(loc.item.name)
    test.assertTrue(early, "no early own-world locations -- oracle is broken, not the code")
    return by_tier, early, own


def _assert_early_upgrade_affordable(test):
    """A player who has cleared a realistic fraction of the early game can afford a +3 weapon.

    This is the assertion the playtest failed in the most literal way available: sphere 2, +0.
    It is deliberately a DENSITY claim, not a total-supply claim. Supply-at-100%-collection is the
    model stone_ramp already uses, and it is the model that declared this seed healthy.

    Sampled across seeds -- see EARLY_SAMPLE_SEEDS for why one seed is not an answer here.
    """
    samples = {}          # tier -> [count per seed]
    shape = []            # (early, own) per seed, for the failure message
    for seed in EARLY_SAMPLE_SEEDS:
        by_tier, early, own = _early_stone_counts(test, seed)
        shape.append((early, own))
        for tier, n in by_tier.items():
            samples.setdefault(tier, [])
        for tier in list(samples):
            samples[tier].append(by_tier[tier])

    flatten = int(getattr(test.world.options, "flatten_regular_upgrades").value)
    need = _stones_needed(EARLY_TARGET_LEVEL, flatten)

    shortfalls = []
    for tier, required in sorted(need.items()):
        # They cleared COLLECTION_RATE of what was open, so the stones must be dense enough that
        # that fraction still covers the cost.
        floor = required / COLLECTION_RATE
        counts = sorted(samples.get(tier, [0] * len(EARLY_SAMPLE_SEEDS)))
        median = counts[len(counts) // 2]
        under = [c for c in counts if c < floor]
        detail = (f"Smithing Stone [{tier}]: need {required} to reach +{EARLY_TARGET_LEVEL} "
                  f"(flatten={flatten}); at a {COLLECTION_RATE:.0%} clear rate that requires "
                  f"{floor:.0f} placed across spheres 0-1. Sample over {len(counts)} seeds: "
                  f"{counts} (median {median}, {len(under)} under the floor)")
        if median < floor:
            shortfalls.append("TYPICAL SEED IS SHORT -- " + detail)
        elif len(under) > EARLY_SAMPLE_MAX_UNDER:
            shortfalls.append("TAIL IS TOO FAT -- " + detail)
    avg_early = sum(e for e, _ in shape) / len(shape)
    avg_own = sum(o for _, o in shape) / len(shape)
    test.assertFalse(
        shortfalls,
        "early upgrade economy is too sparse to afford +%d -- a player deep into the seed is still "
        "at +0:\n  %s\n(on average %.0f of this world's %.0f own checks live in spheres 0-1 = %.0f%%. "
        "filler_budget floors the POOL, so if the pool clears the floor and this does not, the gap "
        "is the early-sphere FRACTION, not the reservation. A single unlucky seed under the floor is "
        "EXPECTED and does not fail this -- see EARLY_SAMPLE_SEEDS.)"
        % (EARLY_TARGET_LEVEL, "\n  ".join(shortfalls), avg_early, avg_own,
           100.0 * avg_early / max(1.0, avg_own)))


class FillerEconomyFloor(WorldTestBase):
    """The seed that broke, reproduced under the shipped frozen defaults."""

    game = GAME
    options = {"num_regions": 4, "enable_dlc": True,
               "curated_filler": PLAYTEST_RECIPE}

    # 🛑 SAMPLED, NOT SINGLE-DRAWN. `num_regions: 4` draws WHICH four regions are kept, so the
    # larder, the vanilla-stone floor and the entitlement all move per seed -- and with no seed
    # pinned, this class asserted against one arbitrary draw. It flipped on an IDENTICAL TREE:
    # d44c50e (branch head) green, 22585d7c (its own merge, same tree) red. A gate that disagrees
    # with itself cannot tell "starved" from "unlucky".
    #
    # Fixed seeds, sampled: deterministic AND still exercising different draws, which is the shape
    # test_gf_region_diversity already uses. Every sampled draw must clear the floor -- this is a
    # starvation gate, so one starved draw is a finding, not noise.
    SEEDS = (1, 2, 7, 13, 101, 5551212)

    # ---- entitlement: the recipe must actually receive its share of the larder ------------------
    def test_curated_recipe_receives_its_share_of_the_filler_budget(self):
        for seed in self.SEEDS:
            with self.subTest(seed=seed):
                self.world_setup(seed=seed)
                counts = Counter(i.name for i in world_pool_items(self))
                larder = _junk_larder(self.world)
                self.assertGreater(larder, 0,
                                   "seed has no junk-consumable larder -- oracle is broken, not the code")
                total_w = sum(PLAYTEST_RECIPE.values())

                # The consumable roster is the recipe's most visible output and is drawn ONLY by
                # curate() -- no other pass creates a Fire Pot. If pool_builder has eaten the
                # larder, this is ~zero.
                roster_cats = ("throwables", "pots", "greases", "foods", "boluses", "perfumes")
                roster_w = sum(PLAYTEST_RECIPE[c] for c in roster_cats)
                entitled = larder * (roster_w / total_w)
                got = _delivered(counts, roster_cats)
                self.assertGreaterEqual(
                    got, _whole_items(SHARE_FLOOR * entitled),
                    f"seed {seed}: curated roster starved: recipe weights it {roster_w}/{total_w} of "
                    f"a {larder}-item junk larder (entitled ~{entitled:.0f}), delivered {got}. Some "
                    f"OTHER pass consumed the filler tail before curate() ran. The filler tail needs "
                    f"a single owner that takes the recipe as a reservation off the top.")

    def test_recipe_stones_reach_the_pool(self):
        for seed in self.SEEDS:
            with self.subTest(seed=seed):
                self.world_setup(seed=seed)
                counts = Counter(i.name for i in world_pool_items(self))
                larder = _junk_larder(self.world)
                total_w = sum(PLAYTEST_RECIPE.values())
                entitled = larder * (PLAYTEST_RECIPE["stones"] / total_w)

                # Vanilla stones are protected from displacement (_ECONOMY_SUBSTR), so they are a
                # FLOOR the recipe adds on top of -- the recipe's contribution is what we check.
                vanilla_stones = sum(
                    1 for rn in [HUB] + list(self.world._kept())
                    for (_n, ap_id, _f) in LOCATIONS.get(rn, [])
                    if (LOCATION_ITEM.get(ap_id) or "").startswith("Smithing Stone [")
                )
                got = sum(c for n, c in counts.items() if _STONE_RE.match(n))
                self.assertGreaterEqual(
                    got, vanilla_stones + _whole_items(SHARE_FLOOR * entitled),
                    f"seed {seed}: the recipe's `stones: {PLAYTEST_RECIPE['stones']}` weight bought "
                    f"nothing: entitled to ~{entitled:.0f} stones on top of the {vanilla_stones} "
                    f"vanilla ones, pool holds {got}.")

    # ---- affordability: the felt bug, stated in the player's terms ------------------------------
    def test_early_weapon_upgrade_is_affordable(self):
        _assert_early_upgrade_affordable(self)

    def test_low_somber_tiers_exist_early(self):
        """Somber weapons cost ONE stone per level, so 'affordable to +N' just means owning [1]..[N] --
        density matters less, existence is the whole contract.

        Only meaningful when the recipe actually RESERVES somber stones. The playtest recipe does not
        (it predates the single-budget model, when somber came free from the vanilla pool), so this
        skips there rather than asserting a floor the recipe never promised. The shipped default DOES
        reserve them -- see DefaultRecipeEconomyFloor.
        """
        if not PLAYTEST_RECIPE.get("somber_stones"):
            pytest.skip("playtest recipe reserves no somber_stones -- nothing promised, nothing to hold")
        _assert_low_somber_early(self)


def _assert_low_somber_early(test):
    from Fill import distribute_items_restrictive

    test.world_setup(seed=0xE1DE8)
    distribute_items_restrictive(test.multiworld)
    player = test.world.player

    sphere_of = {}
    for s, locs in enumerate(test.multiworld.get_spheres()):
        for loc in locs:
            sphere_of[loc] = s

    seen = set()
    for loc in test.multiworld.get_locations(player):
        if sphere_of.get(loc, 99) <= 1 and loc.item is not None and loc.item.player == player:
            m = _SOMBER_RE.match(loc.item.name)
            if m:
                seen.add(int(m.group(1)))
    missing = [t for t in range(1, fb.EARLY_TARGET_LEVEL + 1) if t not in seen]
    test.assertFalse(
        missing,
        f"somber tiers {missing} absent from spheres 0-1: the early somber ladder is walled at its "
        f"first hole (the spec promises +{fb.EARLY_TARGET_LEVEL}). Present low tiers: {sorted(seen)}")


class DefaultRecipeEconomyFloor(WorldTestBase):
    """The SHIPPED default recipe -- i.e. what a yaml that never mentions curated_filler gets.

    The playtest recipe above is a historical artifact: it was written when juice had a private budget
    and somber stones came free from the vanilla pool, so it weights neither. Under a single budget
    those omissions mean literally zero of each, which is the correct and loud consequence of unifying
    the passes -- but it means the playtest recipe cannot guard the somber economy. The default can,
    and the default is what most seeds will actually run.
    """

    game = GAME
    options = {"num_regions": 4, "enable_dlc": True}

    def test_default_recipe_reserves_the_economy(self):
        from worlds.eldenring.features.filler_curation import CuratedFiller

        recipe = CuratedFiller.default
        for cat in ("stones", "somber_stones", "runes"):
            self.assertGreater(recipe.get(cat, 0), 0,
                               f"the shipped default must RESERVE {cat} -- it owns the whole tail now")
        self.assertGreater(recipe.get("juice", 0), 0,
                           "the shipped default must still inject gear (juice), or v0.2 loses "
                           "pool_builder's entire reason for existing")

    def test_early_weapon_upgrade_is_affordable(self):
        _assert_early_upgrade_affordable(self)

    def test_low_somber_tiers_exist_early(self):
        _assert_low_somber_early(self)


# ---- loudness: a pass that cannot meet its contract must SAY SO ---------------------------------
# The old design's defining sin was not that it was wrong, it was that it was QUIET. pool_builder ate
# curated_filler's larder and neither said a word; stone_ramp ran out of convertible slots
# (`while _deficit > 0 and _li < len(_locs)`) and simply stopped. That silence is why a broken upgrade
# economy shipped to a live playtest. CONTRIBUTING's bar: any yaml -> clean gen or graceful reject.
class LeanSeedWarnsRatherThanShipsQuietly(WorldTestBase):
    """A seed too small for its recipe's stone weight to matter is ALLOWED -- but it must say so.

    The old design's defining sin was not being wrong, it was being QUIET: pool_builder ate
    curated_filler's larder without a word, and stone_ramp ran out of convertible slots and simply
    stopped. That silence is why a broken upgrade economy reached a live playtest.
    """

    game = GAME
    # SIZE IS THE POINT HERE (a seed too small for its recipe) and it does not change; only the
    # ending does, because #768 made a 1-region `region_locks` seed illegal at gen.
    options = {"num_regions": 1, "curated_filler": {"stones": 2, "juice": 98},
               "ending_condition": "great_runes"}

    def test_thin_stone_reservation_is_warned(self):
        import logging

        with self.assertLogs("Greenfield", level=logging.WARNING) as cm:
            fb.allocate(self.world, fb.budget_slots(self.world))
        msg = "\n".join(cm.output)
        # TWO warnings can fire here and BOTH honour this class's contract, so accept either. The
        # second one only became reachable when `num_regions: 1` started keeping one region
        # (SPEC-ashen-capital-lock): a genuinely one-region tail is small enough that `stones: 2`
        # of 100 weights rounds to ZERO, and the allocator's zero-share path fires instead of its
        # cannot-afford path. Pinning only the first made this class fail on the very seed shape
        # its own fixture asks for -- and the fix is NOT to relax it to "some warning happened",
        # because "it was quiet" is precisely the sin being guarded.
        afforded = "Smithing Stone [1]" in msg and "afford" in msg
        zeroed = "rounded its share to ZERO" in msg and "no smithing-stone economy" in msg
        self.assertTrue(afforded or zeroed,
                        "a thin stone reservation must announce itself as either 'cannot afford "
                        "the ladder' or 'rounded to zero, no stone economy'. Got:\n" + msg)


class AllocationIsExact(WorldTestBase):
    game = GAME
    options = {"num_regions": 4}

    def test_allocation_sums_to_the_budget_exactly(self):
        """One owner, one budget, no leakage: every tail slot is accounted for by exactly one
        category. A pass that quietly under-fills its share is how the larder went missing."""
        for total in (0, 1, 7, 250, fb.budget_slots(self.world)):
            alloc = fb.allocate(self.world, total)
            self.assertEqual(sum(alloc.values()), total,
                             f"allocator lost or invented slots at budget={total}: {alloc}")

    def test_plan_fills_every_slot(self):
        total = fb.budget_slots(self.world)
        self.assertGreater(total, 0)
        self.assertEqual(len(fb.plan(self.world, total)), total,
                         "the materialiser must produce exactly one decision per budget slot")


def test_recipe_rejects_unknown_category():
    """CONTRIBUTING: any yaml -> clean gen or GRACEFUL REJECT. A typo'd category must not be silently
    dropped -- silently dropping `stone: 20` (singular) is how you ship a seed with no stones."""
    from Options import OptionError
    from worlds.eldenring.features import filler_budget as fb

    class _Fake:
        class options:
            class curated_filler:
                value = {"stone": 20}      # typo: should be "stones"
        player = 1

    with pytest.raises(OptionError) as e:
        fb.recipe_of(_Fake())
    assert "unknown category" in str(e.value)


class EarlyGuarantee(WorldTestBase):
    """THE SIZE-INDEPENDENCE GATE.

    `early_stone_floor` is a claim about SUPPLY -- the seed HOLDS enough Smithing Stone [1]. On the
    4-region seed above that also lands them EARLY, but only by accident: spheres 0-1 are ~80% of a
    small seed, so almost everything is early. Scale the seed up and the same reservation delivers
    almost nothing up front, in silence -- the FillerEconomyFloor test would still pass while a player
    on a big seed stood at +0. That accident is what this class exists to stop relying on.

    So filler_budget DECLARES the early stones to AP (`local_early_items`) and Fill places them in
    locations reachable from the START state. This test runs at a LARGE num_regions -- where the pool
    floor guarantees nothing early -- and asserts the guarantee survives anyway.
    """

    game = GAME
    # Somber weight added on purpose: the shipped playtest recipe has none, so a somber guarantee would
    # be unpayable and filler_budget would (correctly) warn and clamp. Here we want both ladders live.
    options = {"num_regions": 12, "enable_dlc": True,
               "curated_filler": {**PLAYTEST_RECIPE, "somber_stones": 12}}

    def test_early_stones_are_reachable_from_the_start(self):
        from Fill import distribute_items_restrictive

        self.world_setup(seed=0xE1DE7)
        distribute_items_restrictive(self.multiworld)
        world = self.world
        player = world.player

        want = fb.early_guarantee(world)
        self.assertTrue(want, "the guarantee is empty -- the oracle is broken, not the code")

        spheres = list(self.multiworld.get_spheres())
        self.assertTrue(spheres, "no fill spheres -- cannot evaluate reachability")
        start_reachable = spheres[0]          # reachable with NO items == Fill's `base_state`

        got = defaultdict(int)
        for loc in start_reachable:
            if loc.item is not None and loc.item.player == player:
                got[loc.item.name] += 1

        shortfalls = [f"{nm}: guaranteed {n} reachable from the start, found {got[nm]}"
                      for nm, n in sorted(want.items()) if got[nm] < n]
        self.assertFalse(
            shortfalls,
            "the early upgrade guarantee did not survive a large seed -- this is the bug the 4-region "
            "test cannot see:\n  %s\n(%d own checks are reachable from the start, of %d total.)"
            % ("\n  ".join(shortfalls), len(start_reachable),
               len([l for l in self.multiworld.get_locations(player) if l.item is not None])))


# ---- THE SOMBER LADDER IS PRESENCE, NOT DENSITY -------------------------------------------------
# How many draws of the somber reservation the presence claim is sampled over. A one-shot assertion
# here would be worse than useless: the defect this class exists for is that the draw is an i.i.d.
# weighted SAMPLE, so any single draw is a coin flip and a green one proves nothing at all. The
# per-draw absence probabilities on the pre-fix code at num_regions=1 are [3] ~4% and [9] ~65%, so
# 200 draws makes "the floor is missing" a certainty rather than a hope, while still costing under a
# second (no fill, no world rebuild -- just the allocator, reseeded).
SOMBER_PRESENCE_DRAWS = 200


class SomberTierPresenceFloor(WorldTestBase):
    """THE MOTIVATING CASE, AT THE SIZE IT WAS REPORTED (CONTRIBUTING rule 11).

    2026-08-02, a player on a 1-region seed: "zero Somber Smithing Stone [3] in the game". A somber
    weapon costs ONE stone per level and the tier IS the level, so an absent tier is not a thin
    economy -- it is a WALL at that exact weapon level, for the whole seed. Density floors cannot see
    that; only PRESENCE can.

    Two holes let it ship, and this class closes both:

      * `filler_budget._draw_stones` did `if somber: return out` BEFORE the deepest-first top-up, so
        the guarantee the module advertises was regular-[1]-only and no somber tier had any floor.
      * `_assert_low_somber_early` -- the only somber gate there was -- checks tiers (1, 2) at
        num_regions=4. Tier 3, the tier the spec promises and the player reported, is exactly the one
        it does not look at, and 4 regions is exactly the size at which the bug is rarest.

    So: num_regions=1 (the reported size, and the worst case -- the smaller the seed the smaller the
    reservation), every tier 1..9, sampled over SOMBER_PRESENCE_DRAWS reseeded draws of the real
    allocator.

    THE ORACLE IS THE POOL, NOT THE RESERVATION. Vanilla somber stones on kept checks are PROTECTED
    from displacement (`_ECONOMY_SUBSTR` catches "Smithing Stone"), so they are genuinely in the
    seed and a tier they already cover does not need to spend a reservation slot on itself. The
    vanilla half is re-derived here from LOCATIONS + LOCATION_ITEM rather than imported from the
    code under test.
    """

    game = GAME
    # 🛑 CONTRIBUTING RULE 11: the reported size was ONE REGION and it stays one region. #768
    # made that seed illegal under the default ending, so the rune goal carries it -- changing
    # num_regions instead would have retired the motivating case to make a test pass.
    options = {"num_regions": 1, "enable_dlc": True, "ending_condition": "great_runes"}

    def _vanilla_somber(self):
        """{tier} of somber stone the kept vanilla checks already pay -- derived, not imported."""
        seen = set()
        for rn in [HUB] + list(self.world._kept()):
            for (_n, ap_id, _f) in LOCATIONS.get(rn, []):
                m = _SOMBER_RE.match(LOCATION_ITEM.get(ap_id) or "")
                if m:
                    seen.add(int(m.group(1)))
        return seen

    def test_every_somber_tier_is_present_on_a_one_region_seed(self):
        import logging
        import random as _random

        world = self.world
        total = fb.budget_slots(world)
        self.assertGreater(total, 0, "a 1-region seed has no filler budget -- the oracle is broken")
        alloc = fb.allocate(world, total)
        self.assertGreater(
            alloc.get("somber_stones", 0), 0,
            "the shipped default recipe must still RESERVE somber stones at num_regions=1 -- "
            "without a reservation there is nothing for a presence floor to be a floor OVER")

        vanilla = self._vanilla_somber()
        tiers = tuple(range(1, fb.SOMBER_TIERS + 1))
        absent = Counter()
        saved = world.random
        # A 1-region seed legitimately trips allocate()'s thin-stone-reservation warning on EVERY
        # call, and 200 identical copies of it would bury this test's own failure message when it
        # fires. That warning has its own gate (LeanSeedWarnsRatherThanShipsQuietly), so muting the
        # logger for the sampling loop hides nothing that is not asserted elsewhere.
        gf_log = logging.getLogger("Greenfield")
        was = gf_log.level
        try:
            gf_log.setLevel(logging.ERROR)
            for i in range(SOMBER_PRESENCE_DRAWS):
                world.random = _random.Random(0xB0553 + i)
                seen = set(vanilla)
                for nm in fb.plan(world, total):
                    m = _SOMBER_RE.match(nm or "")
                    if m:
                        seen.add(int(m.group(1)))
                for t in tiers:
                    if t not in seen:
                        absent[t] += 1
        finally:
            gf_log.setLevel(was)
            world.random = saved

        self.assertFalse(
            dict(absent),
            "somber tier(s) absent from the POOL on a 1-region seed -- a somber weapon in those seeds "
            "cannot pass the level below the missing tier, ever:\n  %s\n"
            "(%d draws of a %d-slot budget; reservation=%d somber stones; vanilla kept checks already "
            "cover tiers %s. The draw is an i.i.d. weighted sample, so this is not bad luck -- it is "
            "the absence of a coverage floor.)"
            % ("\n  ".join(f"Somber Smithing Stone [{t}]: missing in {n}/{SOMBER_PRESENCE_DRAWS} draws"
                           for t, n in sorted(absent.items())),
               SOMBER_PRESENCE_DRAWS, total, alloc.get("somber_stones", 0), sorted(vanilla) or "none"))

    def test_the_early_margin_is_stocked_on_a_one_region_seed(self):
        """THE 2026-08-04 REPORT (boblerrr's playtest): the Somber [1]/[2] sphere-0 floors "may not
        be getting restricted" on small num_regions seeds. Measured on pre-fix HEAD over 54 full
        generations at num_regions=1: the POOL held fewer than EARLY_GUARANTEE_MARGIN copies of
        Somber [1] in 8 seeds, [2] in 5, [3] in 11 -- and sphere 0 tracked the pool EXACTLY, seed
        for seed. So the restriction was never the broken half: `local_early_items` placed every
        copy the pool could pay, `declare_early_items` clamped the rest away and warned. A
        guarantee that clamps to supply is a hope, and the supply has to be created where the
        reservation is drawn: the coverage floor now stocks the early tiers to the guarantee's own
        count.

        Same sampling shape as the presence test above, for the same reason: the draw is an i.i.d.
        weighted sample, so a one-shot green is a coin flip, not a finding (per-draw shortfall on
        pre-fix HEAD is ~10-20% per tier; over SOMBER_PRESENCE_DRAWS reseeded draws the pre-fix
        failure is a certainty).
        """
        import logging
        import random as _random

        world = self.world
        total = fb.budget_slots(world)
        alloc = fb.allocate(world, total)
        self.assertGreaterEqual(
            alloc.get("somber_stones", 0), fb.SOMBER_TIERS + fb.EARLY_TARGET_LEVEL,
            "the default reservation cannot even hold coverage + the early margin -- the fixture "
            "is broken, not the code")

        vanilla = Counter()
        for rn in [HUB] + list(world._kept()):
            for (_n, ap_id, _f) in LOCATIONS.get(rn, []):
                m = _SOMBER_RE.match(LOCATION_ITEM.get(ap_id) or "")
                if m:
                    vanilla[int(m.group(1))] += 1

        low = tuple(range(1, fb.EARLY_TARGET_LEVEL + 1))
        short = Counter()
        saved = world.random
        gf_log = logging.getLogger("Greenfield")
        was = gf_log.level
        try:
            gf_log.setLevel(logging.ERROR)
            for i in range(SOMBER_PRESENCE_DRAWS):
                world.random = _random.Random(0xEA51E + i)
                got = Counter(vanilla)
                for nm in fb.plan(world, total):
                    m = _SOMBER_RE.match(nm or "")
                    if m:
                        got[int(m.group(1))] += 1
                for t in low:
                    if got[t] < fb.EARLY_GUARANTEE_MARGIN:
                        short[t] += 1
        finally:
            gf_log.setLevel(was)
            world.random = saved

        self.assertFalse(
            dict(short),
            "the pool holds fewer low somber stones than `early_guarantee` promises early, so "
            "`declare_early_items` clamps the early floor away with only a warning:\n  %s\n"
            "(%d draws of a %d-slot budget; reservation=%d; vanilla kept checks hold %s; the "
            "guarantee wants %dx of each of Somber [1..%d].)"
            % ("\n  ".join(
                   f"Somber Smithing Stone [{t}]: short in {n}/{SOMBER_PRESENCE_DRAWS} draws"
                   for t, n in sorted(short.items())),
               SOMBER_PRESENCE_DRAWS, total, alloc.get("somber_stones", 0),
               dict(sorted(vanilla.items())) or "none",
               fb.EARLY_GUARANTEE_MARGIN, fb.EARLY_TARGET_LEVEL))

    def test_the_early_somber_floor_survives_a_one_region_fill(self):
        """END TO END, at the reported size: the sphere-0 half of the same report. EarlyGuarantee
        below runs the identical assertion at num_regions=12, where the reservation is large and
        the margin is nearly always drawn by luck -- exactly the accident that class exists to
        distrust, one size down. The seed is pinned to one whose somber draw holds a single [1]
        and a single [2] on pre-fix HEAD (probe, 2026-08-04), so pre-fix this fails
        deterministically: fill restricted perfectly, delivered the one copy sphere 0 could be
        paid, and the promise was short by construction, not by placement.
        """
        from Fill import distribute_items_restrictive

        self.world_setup(seed=1044)
        distribute_items_restrictive(self.multiworld)
        world = self.world

        want = {nm: n for nm, n in fb.early_guarantee(world).items() if nm.startswith("Somber")}
        self.assertTrue(want, "the somber early guarantee is empty -- the oracle is broken")

        spheres = list(self.multiworld.get_spheres())
        self.assertTrue(spheres, "no fill spheres -- cannot evaluate reachability")
        got = Counter()
        for loc in spheres[0]:
            if loc.item is not None and loc.item.player == world.player:
                got[loc.item.name] += 1

        shortfalls = [f"{nm}: guaranteed {n} reachable from the start, found {got[nm]}"
                      for nm, n in sorted(want.items()) if got[nm] < n]
        self.assertFalse(
            shortfalls,
            "the somber early floor did not survive a 1-region seed -- the supply clamped below "
            "the guarantee and fill had nothing left to restrict:\n  " + "\n  ".join(shortfalls))

    def test_regular_stone_draw_is_untouched_by_the_somber_floor(self):
        """The somber floor must not move ONE regular stone.

        `_draw_stones` is one function serving two ladders, so a change to the somber branch is a
        change to a shared code path. This restates the PRE-2026-08-02 regular algorithm -- draw by
        the taper, then top up Smithing Stone [1] to `early_stone_supply` by converting the deepest
        stones drawn -- and asserts prod still emits it item-for-item from the same RNG state. If the
        somber work ever perturbs the regular draw (an extra random call, a reordered top-up), this
        fails with the exact sequence that changed rather than as a distant density regression.
        """
        import random as _random

        world = self.world
        label = "Smithing Stone"
        weights = fb._regular_stone_weights(int(world.options.flatten_regular_upgrades.value))
        tiers = [t for t in weights if f"{label} [{t}]" in ITEM_CATALOG]
        w = [weights[t] for t in tiers]
        floor_supply = fb.early_stone_supply(world)
        t1 = f"{label} [1]"

        saved = world.random
        try:
            for n in (1, 5, 40, 200):
                for seed in range(15):
                    world.random = _random.Random(0xC0FFEE + seed)
                    got = fb._draw_stones(world, n, somber=False)

                    rng = _random.Random(0xC0FFEE + seed)
                    ref = [f"{label} [{t}]" for t in rng.choices(tiers, weights=w, k=n)]
                    floor = min(floor_supply, n)
                    have = sum(1 for s in ref if s == t1)
                    if have < floor:
                        deepest = sorted(
                            (i for i, s in enumerate(ref) if s != t1),
                            key=lambda i: -int(ref[i].rsplit("[", 1)[1].rstrip("]")))
                        for i in deepest[: floor - have]:
                            ref[i] = t1
                    self.assertEqual(
                        got, ref,
                        f"the regular smithing-stone draw changed (n={n}, rng seed offset {seed}). "
                        f"The somber presence floor is only allowed to touch the somber branch.")
        finally:
            world.random = saved

    def test_a_reservation_smaller_than_the_ladder_degrades_shallow_first_and_says_so(self):
        """n < 9 cannot hold nine tiers. That is ALLOWED -- the floor never grows the reservation --
        but the module's rule is that a degraded pass ANNOUNCES ITSELF, and the degradation has to be
        the sensible one: cover the SHALLOW tiers, because a missing Somber [1] walls a somber weapon
        at +0 while a missing [9] costs only the last rung of a ladder most runs never reach.

        Called DIRECTLY with the vanilla contribution stubbed empty, because that is the only way to
        reach the guard on purpose: how many tiers a real 1-region seed's kept checks already cover
        depends on which regions rolled, so on some seeds a 4-stone reservation IS enough and the
        branch never runs. A guard the fixture only sometimes triggers is a guard that is only
        sometimes tested (and it would fail as a flake, not as a finding).
        """
        import logging
        import random as _random
        from unittest.mock import patch

        world = self.world
        n = 4
        saved = world.random
        try:
            world.random = _random.Random(0xDEEDBEE)
            with patch.object(fb, "_vanilla_somber_counts", lambda _w: Counter()):
                with self.assertLogs("Greenfield", level=logging.WARNING) as cm:
                    out = fb._draw_stones(world, n, somber=True)
        finally:
            world.random = saved

        self.assertEqual(len(out), n, "the floor must never grow the reservation")
        msg = "\n".join(cm.output)
        self.assertIn("somber reservation", msg)
        self.assertIn("cannot pass", msg)

        covered = set(int(_SOMBER_RE.match(nm).group(1)) for nm in out)
        uncovered = [t for t in range(1, fb.SOMBER_TIERS + 1) if t not in covered]
        self.assertTrue(uncovered, "n=4 cannot cover 9 tiers -- the fixture is wrong, not the code")
        # SHALLOW-FIRST, stated as one property: every tier below the first hole is covered. (The
        # reservation may legitimately also hold tiers ABOVE the hole -- those are stones the taper
        # happened to draw and the floor had no reason to spend.)
        first_hole = min(uncovered)
        self.assertEqual(
            sorted(t for t in covered if t < first_hole), list(range(1, first_hole)),
            f"the degradation must cover the SHALLOW tiers first: covered={sorted(covered)}, "
            f"first missing tier={first_hole}. A missing low tier walls a somber weapon at its base; "
            f"a missing high one costs the last rung of a ladder most runs never reach.")

    def test_a_tier_the_vanilla_pool_already_covers_does_not_spend_a_reservation_slot(self):
        """The floor's second half: it leans on what the seed ALREADY holds.

        Somber stones are protected from displacement, so a vanilla one on a kept check is really in
        the pool. Spending a reservation slot to duplicate a tier that is already there would take
        that slot from a tier that is not -- which is the whole reason the accounting exists rather
        than a blanket "one of each, always". Stub the vanilla contribution to a known set and assert
        the floor spends the reservation on that set's COMPLEMENT. (The taper may still draw a
        vanilla-covered tier of its own accord -- that is a draw, not a floor conversion.)
        """
        import random as _random
        from unittest.mock import patch

        world = self.world
        vanilla = {5, 6, 7, 8, 9}
        saved = world.random
        try:
            world.random = _random.Random(0x5EEDED)
            with patch.object(fb, "_vanilla_somber_counts", lambda _w: Counter({t: 1 for t in vanilla})):
                out = fb._draw_stones(world, fb.SOMBER_TIERS, somber=True)
        finally:
            world.random = saved

        drawn = set(int(_SOMBER_RE.match(nm).group(1)) for nm in out)
        self.assertEqual(len(out), fb.SOMBER_TIERS, "the floor must never grow the reservation")
        self.assertEqual(
            sorted(drawn | vanilla), list(range(1, fb.SOMBER_TIERS + 1)),
            f"pool coverage is incomplete: reservation drew {sorted(drawn)}, vanilla covers "
            f"{sorted(vanilla)}")
        self.assertTrue(
            {1, 2, 3, 4} <= drawn,
            f"the reservation must cover the tiers vanilla does NOT: drew {sorted(drawn)}")
