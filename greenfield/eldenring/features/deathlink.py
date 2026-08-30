"""SPEC-PARITY Phase 7 -- DeathLink option surface (COMPLETE).

The client already implements DeathLink send/receive; this feature just exposes AP's standard
death_link toggle and forwards the flag in slot_data so the client knows whether to arm it.
Pure option -> slot_data, no data files. Matt-free.
"""
from Options import DeathLink, Range
from ..registry import Feature, register
from .. import contract


CLIENT_FEATURE_TAG = "death_link_amnesty"


class DeathLinkAmnestyInbound(Range):
    """Only every Nth DeathLink received from another player kills you. One preserves the normal
    DeathLink behavior. Incoming and outgoing deaths use separate counters, which restart when
    the client reconnects."""
    display_name = "DeathLink Amnesty (Incoming)"
    range_start = 1
    range_end = 100
    default = 1


class DeathLinkAmnestyOutbound(Range):
    """Only every Nth local death is sent to the multiworld. One preserves the normal DeathLink
    behavior. Incoming and outgoing deaths use separate counters, which restart when the client
    reconnects."""
    display_name = "DeathLink Amnesty (Outgoing)"
    range_start = 1
    range_end = 100
    default = 1


@register
class DeathLinkFeature(Feature):
    name = "deathlink"
    OPTIONS = {
        "death_link": DeathLink,  # AP's standard toggle (default off)
        "death_link_amnesty_inbound": DeathLinkAmnestyInbound,
        "death_link_amnesty_outbound": DeathLinkAmnestyOutbound,
    }

    def slot_data(self, world):
        data = {contract.DEATH_LINK: bool(world.options.death_link.value)}
        if (world.options.death_link.value
                and (world.options.death_link_amnesty_inbound.value > 1
                     or world.options.death_link_amnesty_outbound.value > 1)):
            data[contract.REQUIRES_CLIENT_FEATURES] = [CLIENT_FEATURE_TAG]
        return data
