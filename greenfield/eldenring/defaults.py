"""FROZEN behaviour -- settings that used to be yaml knobs but are now simply THE BEHAVIOUR.

v0.2 slims the option matrix (Alaric 2026-07-11) on one principle: anything always left ON in the
playtest yaml just IS the behaviour, and half-built modes are frozen OFF rather than exposed.

The option CLASSES stay declared in their features on purpose. They still document the knob, and --
critically -- the features still EMIT their slot_data / options-echo keys, just with a constant
value. So collapsing the yaml surface costs ZERO client churn: the contract the built Rust client
validates on connect is unchanged (completion_scaling_floor, global_scadutree_blessing, auto_upgrade
and flatten_regular_upgrades are REQUIRED options-echo keys -- they keep being emitted).

Mechanism: the names below are (a) filtered out of GFOptions so no yaml can set them, and
(b) injected back onto world.options as frozen stand-ins in generate_early, before any feature reads
them. Removing the now-unreachable off-branches is a safe follow-up, not a prerequisite.
"""


class Frozen:
    """Stand-in for a removed yaml option. Mimics the only bits of an AP Option that features read:
    `.value` (int / list / dict) and, for Choice-derived options, `.current_key` (str), which
    features compare by name (e.g. pool_builder_scope.current_key == "all_filler")."""

    __slots__ = ("value", "current_key", "_name")

    def __init__(self, value, current_key=None, name="<unknown>"):
        self.value = value
        self.current_key = current_key
        self._name = name

    def __getattr__(self, attr):
        if attr in ("value", "current_key", "_name"):   # unset slot -> plain miss, never recurse
            raise AttributeError(attr)
        # A Frozen stand-in only carries `.value` and `.current_key`. If a feature reads anything else
        # off a frozen option (`.range_end`, `.options`, iteration, ...) it silently would have gotten
        # an AttributeError that reads like a typo. Fail LOUDLY and say exactly what happened -- a
        # degraded read must announce itself, not look like absence (CONTRIBUTING: runtime visibility).
        raise AttributeError(
            f"frozen option {self._name!r}: a feature read attribute {attr!r}, which the Frozen "
            f"stand-in does not carry (it has only .value and .current_key). Either the feature needs "
            f"a real Option (un-freeze it in FROZEN_OPTIONS) or Frozen must grow that attribute.")


# name -> (value, current_key). current_key is REQUIRED for Choice-derived options.
FROZEN_OPTIONS = {
    # ---- always-on in the playtest yaml -> now the behaviour -------------------------------------
    "item_shuffle": (1, None),                 # every check pays its real vanilla item. THE randomizer.
    # A shop check keeps the price of the ware it USED to sell, so a slot that cost 3500 can end up
    # selling a Golden Rune [1] (worth 2000) -- randomised reward, un-randomised cost, and the check
    # goes uncollected because nobody presses a slot that is strictly bad. Rolled into
    # [0, 2x the rune's own worth] instead (Alaric 2026-07-25). Frozen ON: it is the behaviour, not a
    # knob -- unfreeze here if it ever needs to be player-visible.
    "rune_shop_pricing": (1, None),
    # The pool_builder_* knobs are now CONSTANTS of features/filler_budget, which is the single owner
    # of the filler tail. `scope` is meaningless (there is one budget: rune tail + displaceable junk),
    # `intensity` is the allocator's JUICE_FLOOR, and `juice_cap` is gone -- juice is a recipe weight
    # competing with stones on the same budget instead of a private allocation that ate them.
    # RETIRED 2026-07-28 -- these four are now Options.Removed stubs (features/pool_builder.py), so a
    # stale yaml naming them RAISES rather than being silently dropped. A Removed option cannot be
    # frozen: there is no value to freeze.
    #   "pool_builder"            -> say `juice: 0` in curated_filler
    #   "pool_builder_scope"      -> filler_budget.budget_slots defines the tail
    #   "pool_builder_juice_cap"  -> the `juice` weight IS the cap
    # UNFROZEN 2026-07-28: `pool_builder_intensity` is a live knob again (filler_budget.juice_floor).
    # It was frozen because the refactor left it inert; it is not inert any more, and "how good does
    # gear have to be to count" is a real choice with a real cost (a higher floor is a SMALLER
    # catalog, so it yields LESS gear, not better gear).
    #   "pool_builder_intensity": (2, "max"),
    # SUPERSEDED and frozen so it cannot be set: "what share of the tail is juice?" is now simply the
    # `juice` weight in the curated_filler recipe. Left settable, it would be a silent no-op -- and a
    # knob that quietly does nothing is the exact failure class this whole change exists to kill.
    #   "pool_builder_juice_pct"  -> the `juice` weight IS the share (Removed stub)

    # 2, not the playtest yaml's 3: at 2 the starting upgrade level still REQUIRES stones, which keeps
    # smithing stones meaningful as checks. It errs generous. (3 made regular weapons so cheap to bring
    # up that the 2026-07 playtest ran almost exclusively SOMBER weapons.) -- Alaric 2026-07-11
    "stone_ramp": (0, None),                   # mechanism DELETED (see core.post_fill); class inert
    "flatten_regular_upgrades": (2, None),
    "auto_upgrade": (1, None),
    "start_with_lantern": (1, None),   # replaces the old start Torch: hands-free pouch light
    "start_with_flasks": (1, None),
    "start_with_steed": (1, None),
    "start_with_bell": (1, None),      # unique-grant path: flag 60110 latch, skip-if-owned
    "start_with_physick": (1, None),   # unique-grant path: flag 60020 latch, skip-if-owned
    "start_with_whetstone": (1, None), # unique-grant path: flag 60130 latch, skip-if-owned
    "start_with_region_lock": (1, None),
    "reveal_all_maps": (1, None),
    "no_weapon_requirements": (1, None),
    "early_leveling": (1, None),
    "buyable_stonesword_keys": (1, None),
    "protect_missable_locations": (1, None),
    "legacy_dungeon_keys": (1, None),
    "varied_filler": (1, None),
    # NB curated_filler is deliberately NOT frozen. It is now THE recipe for the entire filler tail
    # (features/filler_budget) and therefore the one genuinely interesting player-facing lever left on
    # this surface -- it decides the whole pool economy. Its v0.2 default lives on the option class
    # (features/filler_curation.CuratedFiller.default), so a yaml that never mentions it still gets a
    # real economy. Same treatment as progression_surface.
    # progressive_flasks is deliberately NOT frozen any more (un-frozen 2026-07-15). It was frozen
    # OFF on 2026-07-12 because the unified flask ladder BRICKED THE GAME: er-logic reconcile.rs
    # folded a progressive item's tier goods into `unique_goods` -- a SELF-HEALING "the player should
    # OWN this" set, correct for the stone bell bearings the tier system was built for, catastrophic
    # for a CONSUMABLE. A Golden Seed / Sacred Tear is SPENT at the grace, so the reconciler saw it
    # missing and handed it back: upgrade, re-grant, upgrade, re-grant -- unbounded, until flask
    # potency ran past its cap and the game CTD'd (Alaric, live playtest 2026-07-12).
    #
    # FIXED client-side (from-software-archipelago-clients bb418fd, merged 85d500f): every rung now
    # declares `consumed` (contract.py NESTED_GRANTS -- REQUIRED bool), and reconcile.rs routes a
    # consumed rung's goods through `d.ledgered` keyed by the copy's stream index -- granted exactly
    # ONCE, exactly like overflow -- while owned rungs (bell bearings) keep the unique_goods
    # self-heal. Proven by the er-logic reconcile suite (consumed_tier_grants_once_and_stays_spent_
    # after_consumption and friends). The option is now a REAL yaml toggle, default ON, declared on
    # features/progressive.ProgressiveFlasks -- the intended flask economy for v0.2.
    # UNFROZEN 2026-07-28 (player request, Nexus/ShadowTL: "is it possible to disable dungeon_sweep").
    # It was frozen as part of the v0.2 option slim, not because the other values were unfinished:
    # `none` was already handled (`boss_locks.py:267` gates every sweep emit on `value != 0`) and
    # already covered by test_gf_boss_locks ("a fresh world with dungeon_sweep=none emits no sweep
    # keys"). A knob that works and is hidden is a different thing from a knob that is not ready.
    # "dungeon_sweep": (2, "all"),
    # UNFROZEN 2026-07-31, default still OFF. The 2026-07-18 balance call below stands as the DEFAULT
    # -- it is not a reason to keep the knob unreachable. The freeze had a second, unintended effect:
    # the option could not be set from yaml at all, so the feature could never be playtested, so the
    # bug that it did nothing outside the DLC went unnoticed for its entire life. A knob that cannot
    # be turned on cannot be tested (the same reasoning that unfroze dungeon_sweep on 2026-07-28).
    #
    # The original call, still the default: with the DLC enemy scaling handled separately, the
    # per-DLC-region blessing FLOOR made the DLC "way too easy" -- you arrived at each area already at
    # its expected blessing without collecting a single Scadutree Fragment. off = the game grants
    # blessing ONLY from fragments you actually hold, exactly as vanilla.
    # "global_scadutree_blessing": (0, "off"),
    "progression_surface_mode": (2, "strict"),
    # NB: `progression_surface` is deliberately NOT frozen -- it is the one genuinely interesting
    # player-facing lever (WHICH locations may hold progression), it is finished, and its categories are
    # ground-truth audited. It lives in features/progression_surface.py as an OptionSet with the v0.2
    # default baked in, so a yaml that never mentions it generates exactly as before. Narrowing it is
    # safe: the feasibility ladder widens rather than failing, and an empty set turns confinement off.
    "important_locations": (["Remembrance", "Seedtree", "Church", "Boss", "Fragment", "Revered"], None),

    # ---- half-built / superseded -> frozen OFF (finish later, then re-expose) --------------------
    "boss_keys": (0, None),                    # boss locks half-built (ref items never created)
    "boss_lock_placement": (1, "own_region"),  # inert while boss_keys is off

    "progressive_stone_bells": (0, None),
    "progressive_stonesword_keys": (0, None),
    "stone_injection": (0, None),              # DELETED mechanism; the class is inert
    "filler_upgrade_weight": (1, None),        # inert under the always-on item_shuffle
    # UN-FROZEN 2026-07-27. `completion_scaling_floor` is the difficulty FLOOR -- the hard-mode knob
    # -- and it is now a real yaml option again (features/scaling.CompletionScalingFloor, default 0 =
    # unchanged). It was frozen at 0 on 2026-07-11 as part of the surface slim, which is also the only
    # reason its units bug never reached a player: core._options_echo emitted the raw PERCENT while
    # the client parses an HP MULTIPLIER, so any value above 3 pinned the whole game to the top
    # scaling tier. Fixed in the same change (features/scaling.floor_multiplier); do NOT re-freeze
    # this without also deciding what happens to that conversion.
}


def apply_frozen(options) -> None:
    """Inject the frozen stand-ins onto a world's options so features read them exactly as before.
    Never overwrites a field that is still yaml-settable; idempotent."""
    for name, (value, key) in FROZEN_OPTIONS.items():
        if not hasattr(options, name):
            setattr(options, name, Frozen(value, key, name))
