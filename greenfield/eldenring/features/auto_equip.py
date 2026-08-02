"""auto_equip -- "use what you get": a received weapon or armour piece goes straight onto you.

The shared runtime client already implements the whole behaviour (`auto_equip.rs`, armed from
`core.rs` via `er_logic::options::parse_auto_equip`): the receive loop queues every WEAPON or
PROTECTOR FullID that arrives, and `auto_equip::tick` drains the queue once the item is in the bag,
writing the four coupled `EquipGameData` representations through the game's own refcounted
`ChrAsm::operator=`. It clobbers whatever occupies the slot, mid-boss-fight included -- that IS the
feature (Alaric 2026-08-01: "always equip, including in a boss fight -- that's the vision"), and the
motivating case is the French Challenge run format (Wretch + randomizer + use-what-you-get +
permadeath), where the first thing you pick up defines your build and you get no say in it.

🛑 WHAT THIS FILE FIXES. The client shipped all of that reading `slot_data["options"]["auto_equip"]`
-- and the apworld had NEVER emitted that key, for any seed. `parse_bool_option` on an absent key is
`false`, so the feature was inert for every ER player and nothing anywhere said so; the cross-side
gate (`tests/test_gf_client_contract_paths.py`) listed `/options/auto_equip` as a known undeclared
client read. This is the world half: the option, the contract declaration, the echo, and the
handshake tag.

WHY THERE IS A `slot_data` HOOK AT ALL, when the sibling toggles (`weapon_reqs`, `upgrades`) have
none. The VALUE rides in the `options` sub-dict, which `core._options_echo` owns centrally --
features never write into it (contract.py's OPTIONS_SUBKEYS header). But `_contract_hash()` folds in
CONTRACT and NOT OPTIONS_SUBKEYS, so adding an options sub-key does not move the hash: an older
client reports `VERSION: OK` and then silently cannot see the key, and the setting the player chose
evaporates. `requiresClientFeatures` is the one instrument that closes that gap, and it is a
per-FEATURE emission -- so this file emits the tag `auto_equip`, and ONLY when the option is actually
on, because a default seed must still connect to any client (same rule as
`features/scaling.py`'s `scaling_ceiling`). The tag is in `er-logic/src/client_features.rs`
SUPPORTED as of the same release; a client without it REFUSES the connect and says why, which is the
whole point -- the alternative is a silent no-op that reads exactly like the feature not existing.
"""
from Options import Toggle
from ..registry import Feature, register
from .. import contract

# The er-logic client_features.rs SUPPORTED tag for this behaviour. One string, named once: the
# handshake is worthless if the world and the client disagree about the spelling.
CLIENT_FEATURE_TAG = "auto_equip"


class AutoEquip(Toggle):
    """Wear whatever the multiworld sends you. A weapon or armour piece is put on the moment it
    lands in your bag, replacing whatever was in that slot -- including in the middle of a boss
    fight, and including a weapon your build cannot use. You do not choose your kit; the item order
    does. Off by default. A seed with this on requires a client that supports it and will say so
    rather than connect and quietly ignore the setting."""
    display_name = "Auto-Equip Received Gear"


@register
class AutoEquipFeature(Feature):
    name = "auto_equip"
    OPTIONS = {"auto_equip": AutoEquip}

    def slot_data(self, world):
        # The VALUE is emitted centrally by core._options_echo (contract key options.auto_equip).
        # All this hook owns is the client-feature handshake, and only when the seed actually uses
        # the feature -- an OFF seed emits nothing here and connects to any client.
        if not world.options.auto_equip.value:
            return {}
        return {contract.REQUIRES_CLIENT_FEATURES: [CLIENT_FEATURE_TAG]}
