"""vanilla_pool -- one lever that turns the whole item-pool curation off, both halves at once.

THE ASK (#618, off boblerrr's 2026-08-12 playtest thread)
--------------------------------------------------------
*"Make sure we have an option to turn pool curation off, so you just get straight up vanilla pool."*

The mechanism to do half of it already existed and worked: `curated_filler: {}` makes
`filler_budget.recipe_of` return `{JUNK: 100}`, i.e. "leave every tail check paying exactly what
vanilla paid it". `defaults.py` keeps `curated_filler` deliberately unfrozen so a yaml can say that.

WHY A LEVER RATHER THAN "DOCUMENT THE RECIPE" (the ruling this module enforces)
------------------------------------------------------------------------------
Because the empty recipe is not a vanilla pool, and it LOOKS like one.

`features/presence_floor.py` injects a `useful` copy of every roster item -- 18 high-tier physick
tears plus the smithing bell bearings -- that is not already sitting on a kept check. It declared no
OPTIONS and was not in FROZEN_OPTIONS: it was simply UNCONDITIONAL. So a player who found
`curated_filler: {}`, typed it, and went looking still got up to 18 tears that vanilla never put
where they landed, with nothing anywhere to tell him why.

That is not a hypothetical. It is the report this issue came from: bobler counted 19 "present"
tears against a catalog that is complete at 37/37 and concluded items were missing. Nineteen is the
18-item floor roster plus the one Gravesite tear his seed happened to keep. **The floor was working.
It just made a complete catalog look half-empty, and no option could stand it down.**

So the two halves are one request and they get one switch. A player asking for a vanilla pool should
not have to know that "the pool" is assembled by two features, nor discover the second one by
counting tears. ONE OPTION MEANS ONE THING.

WHAT IT DOES, EXACTLY
---------------------
  1. `filler_budget.recipe_of` returns `{JUNK: 100}` regardless of `curated_filler` -- every tail
     check keeps the item `LOCATION_ITEM` says vanilla paid it.
  2. `presence_floor.absent_roster` returns empty -- nothing is injected.

Both are reads of `is_on()` below, in the two modules that own those behaviours. This module owns
only the option and the predicate: per features/README.md an option has exactly one declaring
feature, and the behaviour stays with the feature that already implements it.

OVERRIDE, NOT REJECT -- and the reason is `curated_filler`'s default
--------------------------------------------------------------------
`CuratedFiller.default` is a real nine-category recipe, so EVERY yaml has a non-empty recipe whether
or not its author typed one, and Archipelago cannot tell an explicit recipe from the default it
filled in. Rejecting `vanilla_pool: true` alongside a non-empty `curated_filler` would therefore
reject the plain default yaml -- the exact trap `features/vanilla_placement.py` documents for
`num_regions`, and it chose ignore-with-a-log there for the same reason. So this overrides, and says
so in the generation log, once, by name.

🛑 WHAT IT DELIBERATELY DOES NOT TOUCH. The lever is scoped to the AP ITEM POOL -- what is placed on
your checks. It does not stand down `reroll_enemy_drops` (farmable, unflagged lots that were never
checks) or the shop-stock reroll, because neither puts anything in the pool; they change what the
game hands you OUTSIDE the check system, and a player who wants those vanilla has options for them
already. Nor does it touch `varied_filler`, which is frozen ON: the handful of checks whose vanilla
ware has no catalog entry (the Rune-fallback sentinel) still draw varied junk, because there is no
vanilla item on record to restore. That residue is real, it is small, and it is named here rather
than papered over -- see the SCOPE note in tests/test_gf_vanilla_pool.py.

WORLD-ONLY, NO CLIENT HALF, NO VERSION BUMP
-------------------------------------------
Nothing here reaches the wire. `core._options_echo` is a hand-written named subset and this option is
not in it; no `ContractKey` is declared, so `CONTRACT_HASH` cannot move, and
`test_gf_options_echo_covers_its_producers` (declaration -> producer) has nothing new to find. Same
footing as `vanilla_placement`'s "ZERO CLIENT WORK". Pool composition is decided entirely at
generation; the client is handed the same slot_data shape it always was.
"""
import logging

from Options import Toggle

from ..registry import Feature, register


class VanillaPool(Toggle):
    """Turn item-pool curation off: your checks pay what they pay in vanilla Elden Ring. Off by
    default, and it is the ONE switch you need -- it replaces the whole `curated_filler` recipe with
    "keep what the check already paid" AND stops the guaranteed physick-tear / bell-bearing set
    being added to the pool. Those are the two separate things that make a seed's item spread differ
    from vanilla's, which is why emptying `curated_filler` on its own is not enough: it does the
    first only, and such a seed still hands you up to 18 crystal tears vanilla never placed.

    (Items are still SHUFFLED between checks -- this decides which items exist, not where they sit.
    `vanilla_placement` is the option for that.)

    You give up a lot: no gear injection, no smithing-stone economy, no rune economy, and no
    guarantee that a physick tear or a bell bearing exists at all in a seed that seals their home
    regions. That is what vanilla means here -- the curation is what was buying those. If what you
    wanted was less gear rather than none, weight `curated_filler` down instead of setting this.

    Overrides `curated_filler` rather than conflicting with it: the recipe has a real default, so a
    yaml that never mentions it still has one, and rejecting the combination would reject the
    shipped template. The generation log names the override when it happens."""
    display_name = "Vanilla Item Pool"


def is_on(world) -> bool:
    """True when this seed was asked for a vanilla pool.

    Deliberately tolerant of a missing option: `filler_budget` and `presence_floor` both call this,
    and both are imported by test harnesses and pre-regen tooling that build worlds without the full
    option surface. A missing option means the mode is off, which is the no-change default."""
    o = getattr(getattr(world, "options", None), "vanilla_pool", None)
    return bool(o is not None and o.value)


def log_override_once(world) -> None:
    """Say, once per world, that the mode overrode a recipe the player may have written.

    CONTRIBUTING: a degrade or an override announces itself. This is the ONLY line the mode prints on
    a clean run, and it exists because `curated_filler` is the option a player was told to edit --
    silently ignoring their recipe is how the last round of pool confusion started."""
    if getattr(world, "_gf_vanilla_pool_logged", False):
        return
    world._gf_vanilla_pool_logged = True
    logging.getLogger("Greenfield").info(
        "[eldenring:%s] vanilla_pool is ON: the item pool is left as vanilla built it. The "
        "curated_filler recipe is overridden with `junk` (every filler check keeps the item vanilla "
        "paid it) and the presence floor injects nothing, so this seed has NO gear injection, NO "
        "smithing-stone or rune economy, and no guaranteed physick tears or bell bearings.",
        world.player)


@register
class VanillaPoolFeature(Feature):
    name = "vanilla_pool"
    # No ITEMS and no slot_data: this feature only ever REMOVES things from the pool, and it does
    # that inside the two features that put them there. Nothing new goes on the wire -- see the
    # module docstring's world-only note.
    ITEMS = {}
    OPTIONS = {"vanilla_pool": VanillaPool}
