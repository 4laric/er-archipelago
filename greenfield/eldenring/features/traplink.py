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
    """Share trap items with other TrapLink players.

    A trap received through Archipelago is broadcast once when it enters your local trap queue.
    Linked traps use an exact compatible Elden Ring trap name; unknown foreign trap names are
    ignored rather than converted into an arbitrary effect. Incoming linked traps never echo back.
    """

    display_name = "TrapLink"


@register
class TrapLinkFeature(Feature):
    name = "traplink"
    OPTIONS = {"trap_link": TrapLink}

    def slot_data(self, world):
        if not bool(world.options.trap_link.value):
            return {}
        return {contract.REQUIRES_CLIENT_FEATURES: [CLIENT_FEATURE_TAG]}
