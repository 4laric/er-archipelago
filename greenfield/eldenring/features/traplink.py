"""TrapLink participation.

The client advertises the protocol tag only after it has parsed this slot option.  A seed with the
toggle enabled also declares the client capability so an older DLL refuses loudly instead of
accepting a setting it cannot honor.
"""

from Options import Toggle

from .. import contract
from ..registry import Feature, register


CLIENT_FEATURE_TAG = "trap_link"


class TrapLink(Toggle):
    """Sends the traps you get to other Trap Link players, and receives theirs.

    Trap Link lets games in a multiworld trigger each other's traps. Off by default; only
    useful if other players use it too. A trap from another player hits you only if this
    client recognizes its name; the rest are ignored. Needs an up-to-date client; older ones
    refuse the seed.
    """

    display_name = "Trap Link"


@register
class TrapLinkFeature(Feature):
    name = "traplink"
    OPTIONS = {"trap_link": TrapLink}

    def slot_data(self, world):
        if not bool(world.options.trap_link.value):
            return {}
        return {contract.REQUIRES_CLIENT_FEATURES: [CLIENT_FEATURE_TAG]}
