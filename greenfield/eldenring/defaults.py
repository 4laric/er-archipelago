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
    "pool_builder": (1, None),
    "pool_builder_scope": (1, "all_filler"),
    "pool_builder_intensity": (2, "max"),
    "pool_builder_juice_cap": (0, None),       # 0 = auto-size to the whole Rune tail
    "curated_fill": (1, None),
    "stone_ramp": (1, None),
    # 2, not the playtest yaml's 3: at 2 the starting upgrade level still REQUIRES stones, which keeps
    # smithing stones meaningful as checks. It errs generous. (3 made regular weapons so cheap to bring
    # up that the 2026-07 playtest ran almost exclusively SOMBER weapons.) -- Alaric 2026-07-11
    "flatten_regular_upgrades": (2, None),
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
    # NOT half-built -- finished on BOTH sides, so it ships at its declared default (2 = scaled), not
    # off. gen has DLC_BLESSING_FLOORS and emits dlcScadutreeFloorRanges (only when this == 2); the
    # client consumes it (er-logic scaling.rs: DLC enemy-tier cap; hook.rs get/set_scadutree_blessing).
    # Freezing it OFF never emitted the floor wire, so the client's floor path was dead code and a DLC
    # player arrived with ~0 blessing and got brutalised -- the exact thing the feature prevents.
    "global_scadutree_blessing": (2, "scaled"),
    "progression_surface_mode": (2, "strict"),
    "important_locations": (["Remembrance", "Seedtree", "Church", "Boss", "Fragment", "Revered"], None),
    "big_ticket_locations": (["MajorBoss", "Remembrance", "GreatRune"], None),
    # EXPANDED 2026-07-11. The surface was deliberately tiny (MajorBoss/Remembrance/GreatRune = 57
    # locations) because the location DATA could not be trusted, so it was held to what could be
    # hand-verified. The provenance work (MSB/EMEVD ground truth, the region oracle, the phantom-flag
    # guard) removed that constraint, and the category tags are now derived from what each flag's
    # ItemLotParam lot actually GRANTS -- audited against ground truth: Sacred Tear 13/13,
    # Golden Seed 43/43, Scadutree Fragment 46/46, Revered Spirit Ash 23/23.
    #
    # SHOPS ENTER VIA ShopSlot, NOT Shop. All 479 shop rows stay randomized checks, but only ELEVEN are
    # progression-eligible: ONE per MERCHANT (matt's model -- a merchant enters the pool once, so
    # however large their stock they can hold at most one progression item and cannot dominate by
    # breadth). Dedicated spell vendors (>=50% spells, measured) are excluded. The flat alternatives
    # are both wrong: Shop (479) or ShopNonSpell (395) would make ~70% of the surface a merchant and
    # the seed would play as "farm runes, buy the game".
    "progression_surface": (["KeyItem", "MajorBoss", "Remembrance", "GreatRune",
                             "Church", "Seedtree", "Fragment", "Revered", "ShopSlot"], None),

    # ---- half-built / superseded -> frozen OFF (finish later, then re-expose) --------------------
    "boss_keys": (0, None),                    # boss locks half-built (ref items never created)
    "boss_lock_placement": (1, "own_region"),  # inert while boss_keys is off
    "progressive_flasks": (0, None),
    "progressive_stone_bells": (0, None),
    "progressive_stonesword_keys": (0, None),
    "stone_injection": (0, None),              # superseded by the always-on stone_ramp
    "filler_upgrade_weight": (1, None),        # inert under the always-on item_shuffle
    "completion_scaling_floor": (0, None),     # scaling.py still emits the key (client contract)
}


def apply_frozen(options) -> None:
    """Inject the frozen stand-ins onto a world's options so features read them exactly as before.
    Never overwrites a field that is still yaml-settable; idempotent."""
    for name, (value, key) in FROZEN_OPTIONS.items():
        if not hasattr(options, name):
            setattr(options, name, Frozen(value, key, name))
