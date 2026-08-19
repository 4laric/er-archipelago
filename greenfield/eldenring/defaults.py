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


# `Options.Visibility.none`, inlined as a plain int so this module needs no Archipelago import.
# AP's spoiler writer tests `res.visibility & Visibility.spoiler`; 0 makes that falsy and it moves on.
_VISIBILITY_NONE = 0


class Frozen:
    """Stand-in for a removed yaml option. Mimics the only bits of an AP Option that get read:
    `.value` (int / list / dict), for Choice-derived options `.current_key` (str), which features
    compare by name (e.g. pool_builder_scope.current_key == "all_filler"), and `.visibility`.

    🛑 `.visibility` is read by ARCHIPELAGO, not by us -- `BaseClasses.Spoiler.to_file` walks every
    option on every world and does `res.visibility & Visibility.spoiler`. Without it a Frozen raised
    the AttributeError below FROM INSIDE THE SPOILER WRITER, which is a crash at the very end of a
    successful generation: the seed is filled, and then the write fails. Found by `fuzz_gf.py`
    (2026-08-09) on `start_with_whetblades`; it predates progression_bias and reproduces on main.

    It is `none` rather than `spoiler` because that is what a frozen option IS -- not a knob the
    player has, so not a choice the spoiler should record as one. FROZEN_OPTIONS below is the record
    of what the behaviour actually is, and it is versioned with the code that reads it.
    ⚠️ Flipping this to `spoiler` would also need `current_option_name`, which the writer reads on
    the next line. Don't change one without the other."""

    __slots__ = ("value", "current_key", "visibility", "_name")

    def __init__(self, value, current_key=None, name="<unknown>"):
        self.value = value
        self.current_key = current_key
        self.visibility = _VISIBILITY_NONE
        self._name = name

    def __getattr__(self, attr):
        if attr in ("value", "current_key", "visibility", "_name"):  # unset slot -> plain miss
            raise AttributeError(attr)
        # A Frozen stand-in carries only `.value`, `.current_key` and `.visibility`. Anything else
        # (`.range_end`, `.options`, `.current_option_name`, iteration, ...) would otherwise raise a
        # bare AttributeError that reads like a typo. Fail LOUDLY and say exactly what happened -- a
        # degraded read must announce itself, not look like absence (CONTRIBUTING: runtime visibility).
        # 🛑 The reader is not always a feature of ours: `.visibility` was reached by ARCHIPELAGO's
        # own spoiler writer, so "check the feature" was the wrong first place to look. Say both.
        raise AttributeError(
            f"frozen option {self._name!r}: attribute {attr!r} was read -- by one of our features or "
            f"by Archipelago itself -- and the Frozen stand-in does not carry it (only .value, "
            f".current_key and .visibility). Either it needs a real Option (un-freeze it in "
            f"FROZEN_OPTIONS) or Frozen must grow that attribute.")


# name -> (value, current_key). current_key is REQUIRED for Choice-derived options.
FROZEN_OPTIONS = {
    # ---- always-on in the playtest yaml -> now the behaviour -------------------------------------
    "item_shuffle": (1, None),                 # every check pays its real vanilla item. THE randomizer.
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
    # UNFROZEN 2026-08-13 at Alaric's call. It was frozen ON in the v0.2 slim because the flagship
    # playtest yaml always turned it on, which made it the behaviour -- but "any gear the multiworld
    # hands you is usable" is a real difficulty choice, not plumbing, and a player who wants build
    # requirements to mean something had no way to say so.
    #
    # 🛑 THE CLASS DEFAULT MOVED WITH IT, to 1. A bare `Toggle` defaults to 0, so unfreezing alone
    # would have flipped every seed that does not name the option from "requirements removed" to
    # "requirements enforced" -- silently, inside a release, which is exactly what
    # [[er-unfreezing-an-option-needs-the-class-default]] and the PoolBuilderIntensity revert were
    # about. `test_gf_weapon_reqs.test_the_unfrozen_default_matches_the_freeze_value` pins it.
    #   "no_weapon_requirements": (1, None),
    "early_leveling": (1, None),
    "buyable_stonesword_keys": (1, None),
    # UNFROZEN 2026-08-17 by ruling #582: this is now a three-level Choice whose default protects
    # both progression and useful items. The old frozen value remains expressible as `progression`.
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
    # NB: `progression_surface` is deliberately NOT frozen -- it is the one genuinely interesting
    # player-facing lever (WHICH locations may hold progression), it is finished, and its categories are
    # ground-truth audited. It lives in features/progression_surface.py as an OptionSet with the v0.2
    # default baked in, so a yaml that never mentions it generates exactly as before. Narrowing it is
    # safe: the feasibility ladder widens rather than failing, and an empty set turns confinement off.
    # important_locations was here. DELETED 2026-08-02 (Alaric): it forced 256 checks to reject
    # plain filler purely so a "meaningful" check paid out something good. No winnability role --
    # progression_surface owns that -- and 5 of its 6 classes were already surface classes, so its
    # only unique reach was `Boss` (91 checks off-surface). Its item_rule took no player argument,
    # so those 256 checks refused EVERY world's plain filler: a pure multiworld tax for flavour.
    # The `Boss` tag stays a valid surface class; it just no longer forces juice onto anything.

    # ---- half-built / superseded -> frozen OFF (finish later, then re-expose) --------------------
    "boss_keys": (0, None),                    # boss locks half-built (ref items never created)
    "boss_lock_placement": (1, "own_region"),  # inert while boss_keys is off

    # progressive_stone_bells UNFROZEN 2026-08-10 (issue #506). It was never half-built: the
    # ladders, the Twin Maidens' shop-unlock flags, the pool counts and the sphere-0 forcing
    # were all ported verbatim from the matt-based apworld and have sat here, complete and
    # unreachable, since the v0.2 slim. A player asked for exactly this knob and could not
    # find it. 🛑 The class default is Toggle 0 -- the SAME value it was frozen at -- so no
    # existing seed moves; test_the_unfrozen_default_matches_the_freeze_value pins that, which
    # is the check the PoolBuilderIntensity unfreeze went without.
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

    # ---- complete and shipped, but off the yaml surface by choice ---------------------------------
    # Not half-built like the block above: the capability works, the client implements it, and the
    # key keeps being emitted. It is frozen because the option surface is a budget and this one did
    # not earn its row -- unfreezing is deleting the line below, nothing more.
    #
    # 🛑 FROZEN AT THE CLASS DEFAULT (Toggle -> 0), so no seed moves in either direction: freezing it
    # today changes nothing for a player who never set it, and unfreezing it later changes nothing
    # either. That is the property the block above had to be repaired to get.
    "no_fall_damage": (0, None),  # features/body_tuning.NoFallDamage; shipped in v0.4.0, frozen 08-13
}


def apply_frozen(options) -> None:
    """Inject the frozen stand-ins onto a world's options so features read them exactly as before.
    Never overwrites a field that is still yaml-settable; idempotent."""
    for name, (value, key) in FROZEN_OPTIONS.items():
        if not hasattr(options, name):
            setattr(options, name, Frozen(value, key, name))
