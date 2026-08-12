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

⭐ NO `requiresClientFeatures` TAG ON THE CAPABILITY ITSELF, DELIBERATELY -- and this is where they
differ from auto_equip. The handshake exists so a client too old to see a key REFUSES rather than
silently ignoring the player's setting. But `auto_equip.rs` was NEW when its option landed, whereas
these two capabilities are OLDER than every client in circulation: the tag would have to be added to
the client's `SUPPORTED` list first, and until a build carrying it is out, a seed emitting the tag
would refuse to connect on **every client that already implements the feature** -- including the
playtester the option is being added for. That is strictly worse than the sibling precedent
(`weapon_reqs.py`, whose option ships with no tag for exactly this reason).

🛑 THAT REASONING STOPS DEAD AT `medium`, WHICH IS WHY THE TAG EXISTS NOW (2026-08-12, #548). It
covered `off` and `light` because an old client's reading of them is the CORRECT one: absent or 0 is
off, and 1 is the light roll it already implements. `medium` is a value no released client has ever
seen, and `parse_bool_option` turns it into a nonzero -- so an old client hands the player LIGHT.
The player asked for the weaker setting and silently got the strongest one, which is #536's shape
and the one direction a difficulty option must never fail in. So `medium` -- and ONLY `medium` --
emits `requiresClientFeatures ["no_equip_load_roll"]`, the tag in the client's `client_features.rs`
SUPPORTED list since v0.3.11. This is precisely the "if a future change makes the behaviour
version-sensitive, the tag is the right instrument then" case the paragraph above anticipated.

Both default OFF, so a seed rolled today is byte-identical apart from two new keys reading 0, and an
`off` or `light` seed still connects to every client that could run it before.
"""
from Options import Choice, Toggle
from ..registry import Feature, register
from .. import contract

# The er-logic client_features.rs SUPPORTED tag for the ROLL MODE (not for the feature: see the
# module docstring for why light needs no tag and medium does). One string, named once -- a
# handshake whose two sides spell the tag differently refuses every client, including the ones
# that support it.
CLIENT_FEATURE_TAG = "no_equip_load_roll"


class NoEquipLoad(Choice):
    """What your equipment weighs, and therefore which roll you get.

    off (default) -- equipment weighs what it weighs. Your kit is a budget you spend.
    light -- equipment weighs nothing, so you are always at light roll whatever you wear. Heavy
    armour and greatshields cost you nothing at all.
    medium -- never worse than a medium roll. Your equip-load ceiling is raised far enough that no
    real kit can push you into a fat roll, but the light-roll threshold still moves with what you
    put on, so what you wear is still a decision.

    The game recomputes max equip load every frame from Endurance, so the client cannot write the
    number: it multiplies the WEIGHT side with a silent permanent SpEffect, and logs the equip load
    it actually got so the setting can be checked rather than taken on trust.

    `medium` requires a client that supports it, and a seed using it refuses an older one rather
    than connecting -- an old client reads it as "on" and gives you `light`, which is the stronger
    setting you did not ask for. `off` and `light` connect to any client, as they always have."""
    display_name = "Equipment Weight"
    option_off = 0
    option_light = 1
    option_medium = 2
    # 🛑 THE LEGACY SPELLINGS, AND THEY ARE LOAD-BEARING. This option shipped as a Toggle, so yamls
    # in the wild say `no_equip_load: true`. AP's Choice.from_any tests `type(data) == int`, and
    # `type(True)` is `bool`, NOT int -- so a bare yaml boolean falls through to from_text("True")
    # and needs these aliases to resolve at all. Without them every existing yaml that turned this
    # on becomes an OptionError at generation. `true` maps to light because light is what `true`
    # has always meant, which is also why light is 1 and medium is 2 on the wire.
    alias_true = 1
    alias_false = 0
    alias_on = 1
    alias_off = 0
    default = 0


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
        # Both VALUES ride in the `options` sub-dict, which core._options_echo owns centrally
        # (features never write into it -- contract.py's OPTIONS_SUBKEYS header). This feature
        # DECLARES the options; the echo carries them.
        #
        # All this hook owns is the roll-mode handshake, and ONLY for `medium` -- see the module
        # docstring. An off or light seed emits nothing here and connects to any client, exactly as
        # it did before this option grew a third value.
        if world.options.no_equip_load.value != NoEquipLoad.option_medium:
            return {}
        return {contract.REQUIRES_CLIENT_FEATURES: [CLIENT_FEATURE_TAG]}
