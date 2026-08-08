"""body_tuning -- two long-shipped client capabilities that no seed has ever been able to turn on.

`no_equip_load` (weightless equipment -> permanent light roll) and `no_fall_damage` are fully
implemented client-side and have been for months: `no_equip_load.rs` / `no_fall_damage.rs` each
repurpose a vetted no-op `SpEffectParam` row, re-arm it on every map load, and apply it to the
player. Both read `slot_data["options"][<key>]`.

🛑 WHAT THIS FILE FIXES, and it is the same defect `features/auto_equip.py` fixed for auto_equip:
**the apworld has NEVER emitted either key, for any seed.** `parse_bool_option` on an absent key is
`false`, so both features were inert for every ER player who has ever rolled, and nothing anywhere
said so -- the cross-side gate (`tests/test_gf_client_contract_paths.py`) simply listed
`/options/no_equip_load` and `/options/no_fall_damage` as known undeclared client reads. That
allowlist is the record of the bug, not the fix; auto_equip's entry was deleted when it got a
producer, and these two follow it out.

⭐ NO `requiresClientFeatures` TAG, DELIBERATELY -- and this is where they differ from auto_equip.
The handshake exists so a client too old to see a key REFUSES rather than silently ignoring the
player's setting. But `auto_equip.rs` was NEW when its option landed, whereas these two capabilities
are OLDER than every client in circulation: the tag would have to be added to the client's
`SUPPORTED` list first, and until a build carrying it is out, a seed emitting the tag would refuse
to connect on **every client that already implements the feature** -- including the playtester the
option is being added for. That is strictly worse than the sibling precedent (`weapon_reqs.py`,
whose option ships with no tag for exactly this reason). If a future change makes the behaviour
version-sensitive, the tag is the right instrument then.

Both default OFF, so a seed rolled today is byte-identical apart from two new keys reading 0.
"""
from Options import Toggle
from ..registry import Feature, register


class NoEquipLoad(Toggle):
    """Equipment weighs nothing, so you are always at light roll no matter what you are wearing.
    The game recomputes max equip load every frame from Endurance, so the client instead zeroes the
    WEIGHT side with a silent permanent SpEffect -- heavy armour and greatshields cost you nothing.
    Off by default."""
    display_name = "Weightless Equipment"


class NoFallDamage(Toggle):
    """You take no damage from falling. Does not save you from a bottomless pit -- the game still
    kills you for leaving the map -- but ordinary drops, cliffs and shortcuts stop hurting.
    Off by default."""
    display_name = "No Fall Damage"


@register
class BodyTuningFeature(Feature):
    name = "body_tuning"
    OPTIONS = {"no_equip_load": NoEquipLoad, "no_fall_damage": NoFallDamage}

    def slot_data(self, world):
        # Nothing to emit here: both VALUES ride in the `options` sub-dict, which
        # core._options_echo owns centrally (features never write into it -- contract.py's
        # OPTIONS_SUBKEYS header). This feature exists to DECLARE the options; the echo carries them.
        return {}
