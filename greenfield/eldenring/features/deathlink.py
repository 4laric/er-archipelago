"""SPEC-PARITY Phase 7 -- DeathLink option surface (COMPLETE).

The client already implements DeathLink send/receive; this feature just exposes AP's standard
death_link toggle and forwards the flag in slot_data so the client knows whether to arm it.
Pure option -> slot_data, no data files. Matt-free.
"""
from Options import DeathLink, Toggle
from ..registry import Feature, register
from .. import contract


class NoRuneLoss(Toggle):
    """Keep your runes when you die. Off by default.

    Independent of DeathLink: it applies to every death, including ones you cause yourself. The
    client withholds the runes before the game banks the bloodstain and pays them back on respawn,
    so no bloodstain is left behind and nothing is duplicated."""
    display_name = "No Rune Loss on Death"


@register
class DeathLinkFeature(Feature):
    name = "deathlink"
    OPTIONS = {
        "death_link": DeathLink,  # AP's standard toggle (default off)
        "no_rune_loss": NoRuneLoss,
    }

    def slot_data(self, world):
        sd = {contract.DEATH_LINK: bool(world.options.death_link.value)}
        # An OPTIONS_SUBKEY does not move CONTRACT_HASH (see client_features.rs), so an old client
        # would ignore `no_rune_loss` in total silence -- the player sets "keep my runes", dies, and
        # loses them, which is indistinguishable from the feature not existing. Declare the tag ONLY
        # when the seed actually depends on it, so default seeds still connect to any client.
        if world.options.no_rune_loss.value:
            sd[contract.REQUIRES_CLIENT_FEATURES] = ["no_rune_loss"]
        return sd
