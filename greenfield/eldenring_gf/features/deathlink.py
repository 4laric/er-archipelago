"""SPEC-PARITY Phase 7 -- DeathLink option surface (COMPLETE).

The client already implements DeathLink send/receive; this feature just exposes AP's standard
death_link toggle and forwards the flag in slot_data so the client knows whether to arm it.
Pure option -> slot_data, no data files. Matt-free.
"""
from Options import DeathLink
from ..registry import Feature, register


@register
class DeathLinkFeature(Feature):
    name = "deathlink"
    OPTIONS = {"death_link": DeathLink}  # AP's standard toggle (default off)

    def slot_data(self, world):
        return {"death_link": bool(world.options.death_link.value)}
