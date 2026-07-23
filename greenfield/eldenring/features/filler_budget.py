"""THE filler tail has ONE owner.

Before this module, three passes each owned a slice of the same resource and had no contract with
each other:

  1. pool_builder (additive, PASS 1) -- frozen at scope=all_filler / intensity=max / cap=0, it
     converted essentially the WHOLE junk-consumable larder into `useful` juice gear.
  2. filler_curation.curate (in-place swap, PASS 2) -- ran AFTER, and selected candidates that are
     junk-consumable AND not useful. pool_builder had just marked the larder useful. So curate()
     found an empty larder and the yaml's `curated_filler: {stones: 20, ...}` recipe delivered ~3
     items out of an entitlement of ~534.
  3. core.post_fill stone_ramp -- measured its stone deficit against what was already placed,
     concluded supply was adequate, and no-op'd.

Each pass was locally correct. The composition put a live playtest in fill-sphere 2 holding a +0
weapon, and NOTHING RAISED. The passes had been defending against each other by hand for months --
`displaceable_filler` existed only so two of them couldn't drift, pool_builder force-classified its
own output `useful` so the others wouldn't seize it back, and PoolBuilderScope's docstring shipped a
warning that its own aggressive setting "can thin the stone/rune economy that stone_ramp draws from".
Passes that need classification bits, shared predicates and docstring warnings to avoid eating each
other are one mechanism wearing three coats.

So: ONE pass, ONE budget, ONE arbitration point.

    partition  -> every tail slot the seed has to spend (rune-fallback checks + displaceable junk),
                  minus what the other contributors (locks, boss keys, progressive) already ate.
    allocate   -> the recipe, applied ONCE. Economy categories (stones, somber_stones, runes) are a
                  RESERVATION taken off the top and are never scaled down. Everything else splits the
                  remainder by weight. `juice` is a category like any other -- it no longer has a
                  private budget.
    materialize-> core writes the plan into the tail slots. There is no second pass to undo it.

The starvation is now UNREPRESENTABLE rather than merely fixed: a budget too small to pay the economy
reservation RAISES at generation instead of shipping a +0-weapon seed. Nothing in this module exits a
loop early and shrugs -- every shortfall either raises or warns by name (CONTRIBUTING: a degraded pass
must announce itself; the old `while _deficit > 0 and _li < len(_locs)` silently running out of slots
is exactly how the bug survived).

Guarded by tests/test_gf_filler_economy_floor.py, which asserts against the COMPOSED default pipeline
-- because a pass tested in isolation structurally cannot see this class of bug. Six
test_gf_pool_builder_*.py files and a filler_curation suite were all green while the seed was broken.
"""
import logging
from collections import defaultdict
from typing import Dict, List, Optional

from BaseClasses import ItemClassification
from Options import OptionError

from ..item_ids import ITEM_CATALOG
from ..data import HUB, LOCATIONS
from ..item_ids import LOCATION_ITEM
from .filler_curation import CATEGORIES, _VALID_CATS, displaceable_filler
from .pool_builder import juice_order_for_floor, INTENSITY_FLOOR, CATEGORY_OPTION
from ..item_tiers import ITEM_TIER_CATEGORY

# `juice` is a first-class recipe category now. It has no private budget any more -- if you want gear
# injection you weight it like anything else, and it competes with stones on the same tail.
JUICE = "juice"
JUNK = "junk"          # pseudo-category: keep whatever vanilla junk the check already paid
VALID = frozenset(_VALID_CATS) | {JUICE}

# The economy. These are a RESERVATION off the top and are NEVER scaled down: a seed that cannot
# afford them is a seed whose upgrade curve is broken, and it should fail loudly at gen rather than
# quietly ship. (This is the whole lesson of the bug this module exists to kill.)
ECONOMY = ("stones", "somber_stones", "runes")

# Juice rarity floor. Was pool_builder_intensity; frozen at `max` since v0.2, so it is a constant now.
JUICE_FLOOR = INTENSITY_FLOOR["max"]

# Regular smithing stones are drawn tier-weighted, not uniformly. Two facts drive it:
#   * the ladder: reaching +N costs `stones_per_tier` of each tier it passes through;
#   * the run: not every run reaches +24, and a tier-8 stone is dead for the whole early game and for
#     most runs entirely. A tier serves a shrinking slice of the playerbase the deeper it sits.
# So each tier's weight is its ladder cost tapered linearly by depth. This taper is a DESIGN CHOICE,
# not a derivation -- it is the one judgment constant in this module, and it is deliberately a single
# named number rather than smeared across a sphere-coupled placement pass (coupling a player-visible
# economy to an invisible fill artifact is precisely what made stone_ramp both wrong and unfixable).
STONE_TIERS = 8
SOMBER_TIERS = 9

# ---- the affordability SPEC, stated in player terms ---------------------------------------------
# These two constants are the bar the stone reservation is sized against, and they live HERE, in prod,
# because a fix is a predicate production calls -- not a number a test asserts about behaviour it
# cannot influence. tests/test_gf_filler_economy_floor.py imports them, so the spec and the code that
# satisfies it can never drift apart.
#
# COLLECTION_RATE: fill spheres are a 100%-COLLECTION artifact -- sphere 0 of a 4-region seed is ~40%
# of the entire seed, and nobody clears 693 checks before moving on. Assuming they do is exactly why
# the deleted stone_ramp always concluded there was no deficit while the player stood at +0.
COLLECTION_RATE = 0.25          # a thorough player has cleared about a quarter of what is open
EARLY_TARGET_LEVEL = 3          # ...and should be able to afford +3. Meek on purpose.


# Fill SCATTER headroom. `early_stone_floor` is what must be reachable EARLY; the pool floor is what
# the seed must HOLD to deliver that. Those are not the same number, because fill scatters some of the
# supply past sphere 1 -- and sizing the supply to exactly the early requirement means every last stone
# has to land early or the promise breaks. It did: on a 4-region seed the pool held 24 and only 21
# reached spheres 0-1 (CI cleared it by a hair; Alaric's box did not, 2026-07-13).
#
# So the supply carries headroom. This is a judgment constant like the taper -- deliberately ONE named
# number with a stated reason, not a sphere-coupled placement pass. It does NOT need to be exact: over-
# supplying early stones is cheap (they are filler competing with junk consumables), whereas
# under-supplying is the +0-weapon seed this module exists to prevent. Asymmetric cost, so round up.
EARLY_SUPPLY_HEADROOM = 1.5


def early_stone_floor(world) -> int:
    """How many Smithing Stone [1] must be REACHABLE EARLY for a COLLECTION_RATE player to afford
    +EARLY_TARGET_LEVEL. Derived from the game's own ladder under the live flatten setting -- no magic
    number. This is the requirement; `early_stone_supply` is what it costs to meet it."""
    need = _regular_stone_need(_flatten(world))
    return int(need[1] / COLLECTION_RATE + 0.5)


def early_stone_supply(world) -> int:
    """How many Smithing Stone [1] the POOL must hold so that `early_stone_floor` of them actually
    land early, given that fill scatters some of the supply deeper. See EARLY_SUPPLY_HEADROOM."""
    return int(early_stone_floor(world) * EARLY_SUPPLY_HEADROOM + 0.5)


# ---- the EARLY GUARANTEE (AP local_early_items) --------------------------------------------------
# `early_stone_floor` above is a claim about SUPPLY: the seed HOLDS enough stones. It only lands them
# early by accident -- on a small seed spheres 0-1 are most of the world, so nearly everything is
# early; at a large num_regions they are a thin slice and the same reservation delivers ~nothing up
# front, silently. (That accident is exactly what the 4-region test was quietly relying on.)
#
# So we also DECLARE the early stones to AP: `multiworld.local_early_items`, which Fill honours by
# placing them in locations reachable from the START state. That is a statement of INTENT -- we never
# look at a sphere, and fill still chooses the location. (Reading spheres and second-guessing fill is
# what made the deleted stone_ramp both wrong and unfixable.) It degrades rather than explodes: Fill
# uses `allow_partial=True` and warns if it cannot place them all.
#
# THE MARGIN (Alaric, 2026-07-13): guarantee TWICE the ladder cost, not the COLLECTION_RATE-inflated
# floor. The floor's 4x inflation exists because a stone lying somewhere in the seed might never be
# found; a guaranteed-early stone only has to be found in the START REGION, so a 2x margin -- "you
# need to pick up half of them" -- is the honest number. 12 regular stones, not 24.
EARLY_GUARANTEE_MARGIN = 2


def _somber_stone_need(level: int) -> Dict[int, int]:
    """{tier: stones} to take a SOMBER weapon to +level. Somber weapons cost ONE stone per level and
    the tier IS the level (+3 needs Somber [1], [2], [3] -- one each). `flatten_regular_upgrades` is
    regular-only, hence no flatten term.

    NB the ladders are not commensurate: somber caps at +10 where regular caps at +25, so somber +3 is
    roughly regular +7.5 in effective terms. Targeting the same EARLY_TARGET_LEVEL for both is
    therefore GENEROUS to somber -- deliberately, because it is cheap (6 stones total at the 2x margin)
    and a somber weapon is a unique one the player actually wants to invest in early."""
    return {t: 1 for t in range(1, min(level, SOMBER_TIERS) + 1)}


def early_guarantee(world) -> Dict[str, int]:
    """{item name: count} to hand AP as `local_early_items` -- the stones that must be reachable from
    the start. Derived from both ladders; no magic numbers, one named margin."""
    out: Dict[str, int] = {}
    reg = _regular_stone_need(_flatten(world))
    out[f"Smithing Stone [1]"] = reg[1] * EARLY_GUARANTEE_MARGIN
    for tier, n in _somber_stone_need(EARLY_TARGET_LEVEL).items():
        out[f"Somber Smithing Stone [{tier}]"] = n * EARLY_GUARANTEE_MARGIN
    return out


def declare_early_items(world, pool_names: List[str]) -> Dict[str, int]:
    """Register the early guarantee with AP. Called from core.create_items with the pool it just built.

    CLAMPED TO THE POOL, and it says so when it clamps. `local_early_items` can only place items that
    are actually IN the itempool -- AP scans the pool for matching names and silently places nothing if
    there are none. So a recipe with no `somber_stones` weight would get a somber guarantee that reads
    fine in the code and delivers nothing in the seed. That is the exact failure mode this module
    exists to make impossible, so: clamp to what the pool holds, and WARN by name on any shortfall.

    Only ever ADDS to local_early_items, so it composes with anything else wanting an early item.
    Returns what it actually declared (diagnostics / tests)."""
    want = early_guarantee(world)
    excl = set(getattr(world, "gf_dlc_excluded", ()))
    want = {nm: n for nm, n in want.items() if nm in ITEM_CATALOG and nm not in excl and n > 0}
    if not want:
        return {}

    have = defaultdict(int)
    for nm in pool_names:
        if nm in want:
            have[nm] += 1

    declared: Dict[str, int] = {}
    short: List[str] = []
    for nm, n in sorted(want.items()):
        n_ok = min(n, have[nm])
        if n_ok < n:
            short.append(f"{nm}: wanted {n} early, pool holds {have[nm]}")
        if n_ok > 0:
            declared[nm] = n_ok

    if short:
        logging.getLogger("Greenfield").warning(
            "[eldenring:%s] filler_budget: the early guarantee cannot be paid in full -- %s. The pool "
            "simply does not contain these stones (a curated_filler recipe with no `stones` / "
            "`somber_stones` weight has no upgrade economy to make early). Add the weight, or accept "
            "that this seed's early upgrade curve is whatever vanilla happened to leave lying around.",
            world.player, "; ".join(short))

    if not declared:
        return {}
    early = world.multiworld.local_early_items[world.player]
    for nm, n in declared.items():
        early[nm] = max(early.get(nm, 0), n)
    logging.getLogger("Greenfield").info(
        "[eldenring:%s] filler_budget: early guarantee -> %s (reachable from the start; %dx the ladder "
        "cost to +%d)",
        world.player, ", ".join(f"{n}x {nm}" for nm, n in sorted(declared.items())),
        EARLY_GUARANTEE_MARGIN, EARLY_TARGET_LEVEL)
    return declared


def _regular_stone_need(flatten: int) -> Dict[int, int]:
    """{tier: stones} to reach +24. The game's ladder: 2/4/6 per level within a tier, each level capped
    at `flatten` when flatten > 0 (mirrors the client)."""
    need = defaultdict(int)
    for lvl in range(1, 25):
        tier = (lvl - 1) // 3 + 1
        vanilla = (2, 4, 6)[(lvl - 1) % 3]
        need[tier] += min(vanilla, flatten) if flatten > 0 else vanilla
    return need


def _regular_stone_weights(flatten: int) -> Dict[int, float]:
    """{tier: draw weight} for Smithing Stone [1..8]: ladder cost, tapered by run depth."""
    need = _regular_stone_need(flatten)
    return {t: need[t] * (1.0 - (t - 1) / STONE_TIERS) for t in range(1, STONE_TIERS + 1)}


def _somber_stone_weights() -> Dict[int, float]:
    """Somber weapons cost ONE stone per level, so the ladder is flat and only the run-depth taper
    applies: you cannot use a Somber [9] until +8, and most runs never get there."""
    return {t: 1.0 - (t - 1) / SOMBER_TIERS for t in range(1, SOMBER_TIERS + 1)}


def _flatten(world) -> int:
    o = getattr(world.options, "flatten_regular_upgrades", None)
    return int(o.value) if o is not None else 0


# ---- the budget --------------------------------------------------------------------------------
def budget_slots(world) -> int:
    """Every tail slot this seed has to spend.

    = rune-fallback checks (no vanilla item -> would pay Rune)
    + displaceable junk-consumable checks (`displaceable_filler` -- the SAME predicate core's
      extras-sort uses to rank these to the tail, so the budget and the drop order cannot drift)
    - slots the other contributors already ate (locks, boss keys, progressive copies).

    This is the number pool_builder used to compute privately as `_rune_tail` and then spend entirely
    on itself. It is now the shared budget, and it has exactly one consumer.
    """
    excl = getattr(world, "gf_dlc_excluded", ())
    n = 0
    for rn in [HUB] + list(world._kept()):
        for (_name, ap_id, _flag) in LOCATIONS.get(rn, []):
            nm = LOCATION_ITEM.get(ap_id)
            if not (nm and nm in ITEM_CATALOG):
                n += 1                                   # rune-fallback check
            elif not (excl and nm in excl) and displaceable_filler(world, nm):
                n += 1                                   # displaceable junk consumable
    reserved = int(getattr(world, "_gf_reserved_slots", 0) or 0)
    return max(0, n - reserved)


def recipe_of(world) -> Dict[str, int]:
    opt = getattr(world.options, "curated_filler", None)
    raw = dict(getattr(opt, "value", None) or {})
    for cat in raw:
        if cat not in VALID:
            raise OptionError(
                f"curated_filler: unknown category {cat!r}. Valid: {', '.join(sorted(VALID))}")
    recipe = {c: int(w) for c, w in raw.items() if int(w) > 0}
    if not recipe:
        # An EXPLICITLY empty recipe is a coherent request -- "leave the whole tail exactly as vanilla
        # paid it" -- so it is honoured, not rejected. But it is now a much bigger request than it used
        # to be: this recipe owns the WHOLE tail, so {} also means no gear injection and no upgrade
        # economy. That is a decision, and a decision that big does not get to be silent.
        logging.getLogger("Greenfield").warning(
            "[eldenring:%s] curated_filler is empty: the filler tail stays exactly as vanilla paid it "
            "-- NO gear injection (juice) and NO smithing-stone / rune economy at all. This is a much "
            "larger choice than it was before the filler tail got a single owner. Weight `juice` and "
            "`stones` if you did not mean it.", world.player)
        return {JUNK: 100}
    if JUICE not in recipe:
        # Loud, not silent. Under the old two-budget model juice had its own private allocation and a
        # recipe without a `juice` key still got gear; under one budget it does not. That is a real
        # behaviour change for an existing yaml and it must announce itself.
        logging.getLogger("Greenfield").warning(
            f"[eldenring:{world.player}] curated_filler has no `juice` weight: the filler tail now has "
            f"ONE budget, so this seed gets NO pool_builder gear injection. Add e.g. `juice: 60` to the "
            f"recipe if you want rare/legendary gear in the tail.")
    return recipe


def allocate(world, total: int) -> Dict[str, int]:
    """{category: count}, summing to exactly `total`.

    Economy first and in full (never scaled). Everything else splits what is left, by weight, and any
    scale-down is warned by name. Rounding residue lands in `junk`, which is free by construction (it
    means "keep the vanilla item this check already paid").
    """
    recipe = recipe_of(world)
    weights = sum(recipe.values())
    alloc: Dict[str, int] = {c: 0 for c in recipe}
    if total <= 0:
        return alloc

    econ = {c: (total * recipe[c]) // weights for c in ECONOMY if c in recipe}
    econ_total = sum(econ.values())
    if econ_total > total:
        raise OptionError(
            f"curated_filler: the economy reservation ({econ_total} items: "
            f"{', '.join(f'{c}={n}' for c, n in econ.items())}) exceeds the entire filler budget "
            f"({total} slots). This seed cannot pay for its own upgrade curve. Lower the "
            f"{'/'.join(ECONOMY)} weights or keep more regions.")
    alloc.update(econ)

    rest = {c: w for c, w in recipe.items() if c not in econ}
    rest_budget = total - econ_total
    rest_weights = sum(rest.values())
    if rest_weights > 0:
        for c, w in rest.items():
            alloc[c] = (rest_budget * w) // rest_weights
    # Rounding residue -> junk (keeps the vanilla item; always satisfiable).
    residue = total - sum(alloc.values())
    if residue > 0:
        alloc[JUNK] = alloc.get(JUNK, 0) + residue

    # A DEGRADED PASS MUST ANNOUNCE ITSELF. The reservation is proportional, so it can always be paid
    # in principle -- what it CANNOT always do is clear the affordability spec, because a small seed
    # simply has a small tail. That is not an error (a 1-region seed is allowed to be lean), but it is
    # exactly the condition that shipped a +0-weapon playtest, and it must never again pass in silence.
    stones = alloc.get("stones", 0)
    if stones > 0:
        weights = _regular_stone_weights(_flatten(world))
        tier1 = stones * weights[1] / sum(weights.values())
        floor = early_stone_supply(world)
        if tier1 < floor:
            logging.getLogger("Greenfield").warning(
                "[eldenring:%s] filler_budget: the stone reservation buys ~%.0f Smithing Stone [1] but "
                "a player who clears %.0f%% of the early game needs %d to afford +%d. This seed's "
                "filler tail (%d slots) is too small for the recipe's stone weight to matter. Raise "
                "`stones` in curated_filler, or keep more regions.",
                world.player, tier1, COLLECTION_RATE * 100, floor, EARLY_TARGET_LEVEL, total)
    elif "stones" in recipe:
        logging.getLogger("Greenfield").warning(
            "[eldenring:%s] filler_budget: `stones` is weighted in the recipe but the budget (%d "
            "slots) rounded its share to ZERO. The seed has no smithing-stone economy.",
            world.player, total)
    return alloc


# ---- materialising the plan --------------------------------------------------------------------
def _members(world, cat: str) -> List[str]:
    excl = set(getattr(world, "gf_dlc_excluded", ()))
    return [m for m in CATEGORIES.get(cat, ()) if m in ITEM_CATALOG and m not in excl]


def _draw_stones(world, n: int, somber: bool) -> List[str]:
    weights = _somber_stone_weights() if somber else _regular_stone_weights(_flatten(world))
    label = "Somber Smithing Stone" if somber else "Smithing Stone"
    tiers = [t for t in weights if f"{label} [{t}]" in ITEM_CATALOG]
    if not tiers:
        raise OptionError(f"{label} tiers missing from the item catalog -- data.py needs regenerating")
    w = [weights[t] for t in tiers]
    out = [f"{label} [{t}]" for t in world.random.choices(tiers, weights=w, k=n)]
    if somber:
        return out

    # THE EARLY FLOOR IS A GUARANTEE, NOT A HOPE (2026-07-13).
    #
    # `random.choices` is a weighted SAMPLE, so the tier-1 count is a binomial around n * share -- it
    # lands near the target on average and below it about half the time. `allocate()` knew the
    # reservation might not buy the floor and merely WARNED, which is how a seed that cannot afford a
    # +3 weapon still shipped. This module's own thesis is that the starvation should be
    # UNREPRESENTABLE; a coin-flip is not that.
    #
    # So: draw by the taper as before, then TOP UP to the floor by converting the DEEPEST stones drawn.
    # Deepest-first is the cheapest possible correction -- the taper already says a tier-8 stone is dead
    # for the whole early game and for most runs entirely, so those are the slots we least mind
    # spending. Everything above the floor still follows the taper untouched.
    #
    # This does NOT couple the economy to fill spheres (the mistake that made stone_ramp unfixable). It
    # is a statement about the POOL: the seed HOLDS enough tier-1 stones. Where fill puts them is fill's
    # business.
    floor = min(early_stone_supply(world), n)
    t1 = f"{label} [1]"
    have = sum(1 for s in out if s == t1)
    if have >= floor:
        return out
    deepest = sorted(
        (i for i, s in enumerate(out) if s != t1),
        key=lambda i: -_tier_of(out[i]),
    )
    for i in deepest[: floor - have]:
        out[i] = t1
    return out


def _tier_of(name: str) -> int:
    """`Smithing Stone [7]` -> 7. Names are generated by this module, so the shape is ours to rely on."""
    return int(name.rsplit("[", 1)[1].rstrip("]"))


def plan(world, total: int) -> List[Optional[str]]:
    """An ordered, shuffled list of length `total`: the item NAME for each tail slot, or None to keep
    whatever the check already paid (the `junk` share, and the Rune sentinel where a check had no
    vanilla item).

    Every category either fills its allocation exactly or warns by name with the shortfall. No loop
    here exits early and shrugs.
    """
    alloc = allocate(world, total)
    out: List[Optional[str]] = []

    for cat, n in sorted(alloc.items()):
        if n <= 0:
            continue
        if cat == JUNK:
            out += [None] * n
        elif cat == "stones":
            out += _draw_stones(world, n, somber=False)
        elif cat == "somber_stones":
            out += _draw_stones(world, n, somber=True)
        elif cat == JUICE:
            order = [nm for nm in juice_order_for_floor(JUICE_FLOOR)
                     if nm not in set(getattr(world, "gf_dlc_excluded", ()))]
            # PER-CATEGORY juice (pool_builder_pct_weapons / _spells / ...) still works: those percents
            # now split the JUICE allocation rather than carving a second private slice out of the
            # tail. Same knob, same meaning ("what share of my gear injection is spells?"), but it can
            # no longer grow the juice budget at the economy's expense -- which is the whole point of
            # a single owner. No percents set (the default) = best-first across every category.
            pcts = {}
            for opt, gear_cat in CATEGORY_OPTION.items():
                o = getattr(world.options, opt, None)
                v = max(0, min(100, int(o.value))) if o is not None else 0
                if v > 0:
                    pcts[gear_cat] = v
            if pcts:
                picks = []
                tot = sum(pcts.values())
                for gear_cat, pct in sorted(pcts.items()):
                    want = (n * pct) // tot
                    cat_items = [nm for nm in order if ITEM_TIER_CATEGORY.get(nm) == gear_cat]
                    if len(cat_items) < want:
                        logging.getLogger("Greenfield").warning(
                            "[eldenring:%s] juice category %s: catalog holds %d items at the rarity "
                            "floor but %d were allocated; the shortfall spills to junk.",
                            world.player, gear_cat, len(cat_items), want)
                    picks += cat_items[:want]
            else:
                picks = order[:n]                 # best-first: legendary, then rare, then B-tier
            if len(picks) < n:
                logging.getLogger("Greenfield").warning(
                    f"[eldenring:{world.player}] juice: catalog holds {len(picks)} items at the rarity "
                    f"floor but the recipe allocated {n}. Spilling {n - len(picks)} slot(s) to junk.")
                out += [None] * (n - len(picks))
            out += picks
        else:
            members = _members(world, cat)
            if not members:
                logging.getLogger("Greenfield").warning(
                    f"[eldenring:{world.player}] curated_filler category {cat!r} has no members "
                    f"available (DLC filtered?): spilling its {n} slot(s) to junk.")
                out += [None] * n
            else:
                out += [world.random.choice(members) for _ in range(n)]

    if len(out) != total:
        raise AssertionError(
            f"filler_budget produced {len(out)} items for {total} slots -- the allocator and the "
            f"materialiser disagree. This is a bug in this module, not in the yaml.")
    world.random.shuffle(out)
    world.gf_filler_alloc = dict(alloc)          # diagnostics; core exposes it in slot_data
    return out


def classify(world, item) -> None:
    """Juice is intentional USEFUL gear. Some catalog gear (notably spells/incantations) carries the
    GOODS FullID nibble, so core._classify_full defaults it to `filler`. There is no second pass left
    to seize it any more, but AP's fill treats useful and filler differently and juice is meant to be
    the former.

    EXCEPTION: natural_progression uses some juice-tier WEAPONS as region GATE KEYS (e.g.
    Dragon-Hunter's Great Katana gates Jagged Peak; Magma Wyrm's Scalesword / Inquisitor's Girandole
    gate Altus). core._class_for marks those PROGRESSION (world.gf_natural_keys) and they MUST stay
    progression -- demoting a gate key to `useful` makes has()/fill blind to it and strands its region
    (all_state can't reach Jagged Peak; fill can strand the seed). Never demote a designated key."""
    if item.name in _JUICE_NAMES and item.name not in getattr(world, "gf_natural_keys", ()):
        item.classification = ItemClassification.useful


_JUICE_NAMES = frozenset(juice_order_for_floor(JUICE_FLOOR))
