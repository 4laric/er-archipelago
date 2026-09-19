"""SPEC-PARITY Phase 7 -- DeathLink option surface (COMPLETE).

The client already implements DeathLink send/receive; this feature just exposes AP's standard
death_link toggle and forwards the flag in slot_data so the client knows whether to arm it.
Pure option -> slot_data, no data files. Matt-free.
"""
from Options import DeathLink, Range, Visibility
from ..registry import Feature, register
from .. import contract


CLIENT_FEATURE_TAG = "death_link_amnesty"


class EldenRingDeathLink(DeathLink):
    """Shares deaths with other players who have Death Link turned on.

    When you die, everyone else with it on dies too, and the other way round. Deaths caused
    by traps count. For a gentler version, set death_link_amnesty_inbound or
    death_link_amnesty_outbound in your yaml.
    """
    # A local subclass ONLY so the tooltip can point at the two amnesty dials, which are hidden
    # from the simple UIs. Behaviour, default (off) and the key are AP's standard toggle, unchanged.
    display_name = "Death Link"


class DeathLinkAmnestyInbound(Range):
    """Makes incoming Death Links less deadly: only every Nth one kills you.

    Only matters when Death Link is on. With 3, only every 3rd Death Link you receive kills
    you and the rest are ignored; 1 (default) counts every one. The count restarts when your
    client reconnects. Above 1 needs an up-to-date client; older ones refuse the seed.
    """
    visibility = Visibility.all & ~Visibility.simple_ui
    display_name = "Death Link Amnesty (Incoming)"
    range_start = 1
    range_end = 100
    default = 1


class DeathLinkAmnestyOutbound(Range):
    """Sends fewer of your deaths to others: only every Nth death is shared.

    Only matters when Death Link is on. With 3, only every 3rd time you die is sent as a
    Death Link; 1 (default) sends every death. The count restarts when your client
    reconnects. Above 1 needs an up-to-date client; older ones refuse the seed.
    """
    visibility = Visibility.all & ~Visibility.simple_ui
    display_name = "Death Link Amnesty (Outgoing)"
    range_start = 1
    range_end = 100
    default = 1


@register
class DeathLinkFeature(Feature):
    name = "deathlink"
    OPTIONS = {
        "death_link": EldenRingDeathLink,  # AP's standard toggle (default off), our tooltip
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
