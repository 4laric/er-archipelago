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

    __slots__ = ("value", "current_key")

    def __init__(self, value, current_key=None):
        self.value = value
        self.current_key = current_key


# name -> (value, current_key). current_key is REQUIRED for Choice-derived options.
FROZEN_OPTIONS = {
    # ---- always-on in the playtest yaml -> now the behaviour -------------------------------------
    "item_shuffle": (1, None),                 # every check pays its real vanilla item. THE randomizer.
    "pool_builder": (1, None),
    "pool_builder_scope": (1, "all_filler"),
    "pool_builder_intensity": (2, "max"),
    "pool_builder_juice_cap": (0, None),       # 0 = auto-size to the whole Rune tail
    "curated_fill": (1, None),
    "stone_ramp": (1, None),
    "flatten_regular_upgrades": (2, None),     # Alaric 2026-07-11: 2 (playtest yaml used 3)
    "auto_upgrade": (1, None),
    "start_with_torch": (1, None),
    "start_with_flasks": (1, None),
    "start_with_steed": (1, None),
    "start_with_region_lock": (1, None),
    "reveal_all_maps": (1, None),
    "no_weapon_requirements": (1, None),
    "early_leveling": (1, None),
    "buyable_stonesword_keys": (1, None),
    "protect_missable_locations": (1, None),
    "legacy_dungeon_keys": (1, None),
    "varied_filler": (1, None),
    "dungeon_sweep": (2, "all"),
    "progression_surface_mode": (2, "strict"),
    "important_locations": (["Remembrance", "Seedtree", "Church", "Boss", "Fragment", "Revered"], None),
    "big_ticket_locations": (["MajorBoss", "Remembrance", "GreatRune"], None),
    "progression_surface": (["MajorBoss", "Remembrance", "GreatRune"], None),

    # ---- half-built / superseded -> frozen OFF (finish later, then re-expose) --------------------
    "boss_keys": (0, None),                    # boss locks half-built (ref items never created)
    "boss_lock_placement": (1, "own_region"),  # inert while boss_keys is off
    "progressive_flasks": (0, None),
    "progressive_stone_bells": (0, None),
    "progressive_stonesword_keys": (0, None),
    "stone_injection": (0, None),              # superseded by the always-on stone_ramp
    "filler_upgrade_weight": (1, None),        # inert under the always-on item_shuffle
    "completion_scaling_floor": (0, None),     # scaling.py still emits the key (client contract)
    "global_scadutree_blessing": (0, "off"),   # ditto
}


def apply_frozen(options) -> None:
    """Inject the frozen stand-ins onto a world's options so features read them exactly as before.
    Never overwrites a field that is still yaml-settable; idempotent."""
    for name, (value, key) in FROZEN_OPTIONS.items():
        if not hasattr(options, name):
            setattr(options, name, Frozen(value, key))
