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
    # The pool_builder_* knobs are now CONSTANTS of features/filler_budget, which is the single owner
    # of the filler tail. `scope` is meaningless (there is one budget: rune tail + displaceable junk),
    # `intensity` is the allocator's JUICE_FLOOR, and `juice_cap` is gone -- juice is a recipe weight
    # competing with stones on the same budget instead of a private allocation that ate them.
    "pool_builder": (1, None),
    "pool_builder_scope": (1, "all_filler"),
    "pool_builder_intensity": (2, "max"),
    "pool_builder_juice_cap": (0, None),
    # SUPERSEDED and frozen so it cannot be set: "what share of the tail is juice?" is now simply the
    # `juice` weight in the curated_filler recipe. Left settable, it would be a silent no-op -- and a
    # knob that quietly does nothing is the exact failure class this whole change exists to kill.
    "pool_builder_juice_pct": (100, None),

    # 2, not the playtest yaml's 3: at 2 the starting upgrade level still REQUIRES stones, which keeps
    # smithing stones meaningful as checks. It errs generous. (3 made regular weapons so cheap to bring
    # up that the 2026-07 playtest ran almost exclusively SOMBER weapons.) -- Alaric 2026-07-11
    "stone_ramp": (0, None),                   # mechanism DELETED (see core.post_fill); class inert
    "flatten_regular_upgrades": (2, None),
    "auto_upgrade": (1, None),
    "start_with_torch": (1, None),
    "start_with_flasks": (1, None),
    "start_with_steed": (1, None),
    "start_with_bell": (1, None),      # unique-grant path: flag 60110 latch, skip-if-owned
    "start_with_physick": (1, None),   # unique-grant path: flag 60020 latch, skip-if-owned
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
    # NOT half-built any more. One "Progressive Flask Upgrade" item replaces every Golden Seed and
    # Sacred Tear check one-for-one; the Kth copy grants a seed or a tear on an interleaved schedule,
    # and the player still pays the game's OWN escalating price at the grace -- so the "later pickups
    # buy less" curve is inherited from vanilla, and Sacred Tears (13 in the whole game, flat +1 each,
    # so they arrive rarely and never form a curve) finally move on a visible cadence. Zero client
    # churn: progressiveGrants already supports per-rung goods, and overflow copies already fall
    # through to a Lord's Rune. -- Alaric 2026-07-11
    # ⛔ FROZEN OFF AGAIN (2026-07-12) -- the unified flask ladder BRICKS THE GAME.
    #
    # er-logic reconcile.rs folds a progressive item's tier goods into `unique_goods`: a SELF-HEALING
    # set meaning "the player should OWN this; if it is missing, grant it". That is correct for the
    # stone BELL BEARINGS the tier system was built for -- a bell bearing is a key item you keep.
    #
    # It is catastrophically wrong for a CONSUMABLE. A Golden Seed / Sacred Tear is SPENT at the grace;
    # the moment it leaves the inventory the reconciler sees it missing and re-grants it. Upgrade,
    # re-grant, upgrade, re-grant -- unbounded flask upgrades until the potency runs past its cap and
    # the game CTDs. (Alaric, live playtest 2026-07-12: "sat down at grace, upgraded. still had the
    # option to upgrade so kept going. kept going until game CTD'ed".)
    #
    # Note reconcile.rs already has the right mechanism three lines below: OVERFLOW copies go to
    # `d.ledgered`, keyed by the copy's stream index, so they are granted exactly ONCE. The TIER path
    # never got it, because until now no tier ever granted a consumable.
    #
    # The ladder itself is sound and stays in features/progressive.py. Re-enable ONLY when the client
    # can express "this tier's goods are CONSUMED, not owned" -- i.e. tier grants routed through the
    # ledger. Until then a seed must not ship an item that eats the player's run.
    "progressive_flasks": (0, None),
    "dungeon_sweep": (2, "all"),
    # NOT half-built -- finished on BOTH sides, so it ships at its declared default (2 = scaled), not
    # off. gen has DLC_BLESSING_FLOORS and emits dlcScadutreeFloorRanges (only when this == 2); the
    # client consumes it (er-logic scaling.rs: DLC enemy-tier cap; hook.rs get/set_scadutree_blessing).
    # Freezing it OFF never emitted the floor wire, so the client's floor path was dead code and a DLC
    # player arrived with ~0 blessing and got brutalised -- the exact thing the feature prevents.
    "global_scadutree_blessing": (2, "scaled"),
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
    "completion_scaling_floor": (0, None),     # scaling.py still emits the key (client contract)
}


def apply_frozen(options) -> None:
    """Inject the frozen stand-ins onto a world's options so features read them exactly as before.
    Never overwrites a field that is still yaml-settable; idempotent."""
    for name, (value, key) in FROZEN_OPTIONS.items():
        if not hasattr(options, name):
            setattr(options, name, Frozen(value, key, name))
