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
import re
from collections import Counter, defaultdict

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring.data import LOCATIONS, HUB  # noqa: E402
from worlds.eldenring.item_ids import LOCATION_ITEM  # noqa: E402
from worlds.eldenring.features import filler_curation as fc  # noqa: E402

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

# Fraction of the checks open to them that a player has actually cleared when they are "in sphere N".
# Fill spheres are a 100%-COLLECTION artifact: sphere 0 of a 4-region seed is ~40% of the entire seed.
# Nobody clears 693 checks before moving on. stone_ramp's supply model assumes they do, which is the
# precise reason it concludes there is no deficit while the player stands at +0. A quarter is already
# a thorough player.
COLLECTION_RATE = 0.25

# The weapon level a player should be able to AFFORD by the end of the early game (spheres 0-1).
# +3 is deliberately meek: it is the first upgrade tier, reachable in vanilla ER within the first
# hour, and it is the level the playtest could not reach with an entire sphere behind them.
EARLY_TARGET_LEVEL = 3

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


class FillerEconomyFloor(WorldTestBase):
    """The seed that broke, reproduced under the shipped frozen defaults."""

    game = GAME
    options = {"num_regions": 4, "num_regions_order": "rolled", "enable_dlc": True,
               "curated_filler": PLAYTEST_RECIPE}

    # ---- entitlement: the recipe must actually receive its share of the larder ------------------
    def test_curated_recipe_receives_its_share_of_the_filler_budget(self):
        counts = Counter(i.name for i in world_pool_items(self))
        larder = _junk_larder(self.world)
        self.assertGreater(larder, 0, "seed has no junk-consumable larder -- oracle is broken, not the code")
        total_w = sum(PLAYTEST_RECIPE.values())

        # The consumable roster is the recipe's most visible output and is drawn ONLY by curate() --
        # no other pass creates a Fire Pot. If pool_builder has eaten the larder, this is ~zero.
        roster_cats = ("throwables", "pots", "greases", "foods", "boluses", "perfumes")
        roster_w = sum(PLAYTEST_RECIPE[c] for c in roster_cats)
        entitled = larder * (roster_w / total_w)
        got = _delivered(counts, roster_cats)
        self.assertGreaterEqual(
            got, SHARE_FLOOR * entitled,
            f"curated roster starved: recipe weights it {roster_w}/{total_w} of a {larder}-item junk "
            f"larder (entitled ~{entitled:.0f}), delivered {got}. Some OTHER pass consumed the filler "
            f"tail before curate() ran. The filler tail needs a single owner that takes the recipe as "
            f"a reservation off the top.")

    def test_recipe_stones_reach_the_pool(self):
        counts = Counter(i.name for i in world_pool_items(self))
        larder = _junk_larder(self.world)
        total_w = sum(PLAYTEST_RECIPE.values())
        entitled = larder * (PLAYTEST_RECIPE["stones"] / total_w)

        # Vanilla stones are protected from displacement (_ECONOMY_SUBSTR), so they are a FLOOR the
        # recipe adds on top of -- the recipe's contribution is what we are checking for.
        vanilla_stones = sum(
            1 for rn in [HUB] + list(self.world._kept())
            for (_n, ap_id, _f) in LOCATIONS.get(rn, [])
            if (LOCATION_ITEM.get(ap_id) or "").startswith("Smithing Stone [")
        )
        got = sum(c for n, c in counts.items() if _STONE_RE.match(n))
        self.assertGreaterEqual(
            got, vanilla_stones + SHARE_FLOOR * entitled,
            f"the recipe's `stones: {PLAYTEST_RECIPE['stones']}` weight bought nothing: entitled to "
            f"~{entitled:.0f} stones on top of the {vanilla_stones} vanilla ones, pool holds {got}.")

    # ---- affordability: the felt bug, stated in the player's terms ------------------------------
    def test_early_weapon_upgrade_is_affordable(self):
        """A player who has cleared a realistic fraction of the early game can afford a +3 weapon.

        This is the assertion the playtest failed in the most literal way available: sphere 2, +0.
        It is deliberately a DENSITY claim, not a total-supply claim. Supply-at-100%-collection is the
        model stone_ramp already uses, and it is the model that declared this seed healthy.
        """
        from Fill import distribute_items_restrictive

        self.world_setup(seed=0xE1DE7)
        distribute_items_restrictive(self.multiworld)   # spheres only exist post-fill
        world = self.world
        player = world.player

        sphere_of = {}
        for s, locs in enumerate(self.multiworld.get_spheres()):
            for loc in locs:
                sphere_of[loc] = s
        self.assertTrue(sphere_of, "no fill spheres -- cannot evaluate reachability")

        early = [loc for loc in self.multiworld.get_locations(player)
                 if sphere_of.get(loc, 99) <= 1 and loc.item is not None and loc.item.player == player]
        self.assertTrue(early, "no early own-world locations -- oracle is broken, not the code")

        by_tier = defaultdict(int)
        for loc in early:
            m = _STONE_RE.match(loc.item.name)
            if m:
                by_tier[int(m.group(1))] += 1

        flatten = int(getattr(world.options, "flatten_regular_upgrades").value)
        need = _stones_needed(EARLY_TARGET_LEVEL, flatten)

        shortfalls = []
        for tier, required in sorted(need.items()):
            # They cleared COLLECTION_RATE of what was open, so the stones must be dense enough that
            # that fraction still covers the cost.
            floor = required / COLLECTION_RATE
            if by_tier[tier] < floor:
                shortfalls.append(
                    f"Smithing Stone [{tier}]: need {required} to reach +{EARLY_TARGET_LEVEL} "
                    f"(flatten={flatten}); at a {COLLECTION_RATE:.0%} clear rate that requires "
                    f"{floor:.0f} placed across spheres 0-1, found {by_tier[tier]}")
        self.assertFalse(
            shortfalls,
            "early upgrade economy is too sparse to afford +%d -- a player deep into the seed is still "
            "at +0:\n  %s\n(%d of this world's own checks live in spheres 0-1.)"
            % (EARLY_TARGET_LEVEL, "\n  ".join(shortfalls), len(early)))

    def test_low_somber_tiers_exist_early(self):
        """Somber weapons cost ONE stone per level, so 'affordable to +N' just means owning [1]..[N].
        The low somber tiers must therefore be PRESENT early -- density matters less, existence is the
        whole contract. Guards the somber half of the economy against the same starvation."""
        from Fill import distribute_items_restrictive

        self.world_setup(seed=0xE1DE8)
        distribute_items_restrictive(self.multiworld)
        player = self.world.player

        sphere_of = {}
        for s, locs in enumerate(self.multiworld.get_spheres()):
            for loc in locs:
                sphere_of[loc] = s

        seen = set()
        for loc in self.multiworld.get_locations(player):
            if sphere_of.get(loc, 99) <= 1 and loc.item is not None and loc.item.player == player:
                m = _SOMBER_RE.match(loc.item.name)
                if m:
                    seen.add(int(m.group(1)))
        missing = [t for t in (1, 2) if t not in seen]
        self.assertFalse(
            missing,
            f"somber tiers {missing} absent from spheres 0-1: a somber weapon cannot leave +0. "
            f"Present low tiers: {sorted(seen)}")
