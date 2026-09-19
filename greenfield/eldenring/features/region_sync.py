"""Region Sync participation (#1005).

A DeathLink-shaped opt-in link for seamless co-op. Pure option -> slot_data (the `options` echo
carries the value; this feature carries the client-capability TAG), no data files, no logic.

🛑 THIS FEATURE CHANGES NOTHING ABOUT GENERATION. It places no items, writes no rules and moves no
region. A synced open is an ACCESS convenience applied by the client -- the same flag write the
console's `!setflag <region open flag> 1` does -- so Fill, logic and the goal are untouched and each
slot still has to find its own region Locks. The option exists only so the client knows whether to
join the link group.

The tag is declared (rather than left to the tolerant absent-reads-false parse) because silently
ignoring this one BREAKS the co-op it exists for: an older client connects, never applies an inbound
open, and its player is region-kicked out from under the party -- which reads as a broken seed, not
an old client. Same argument, same shape, as features/traplink.py.
"""

from Options import Toggle

from .. import contract
from ..registry import Feature, register


CLIENT_FEATURE_TAG = "region_sync"


class RegionSync(Toggle):
    """In Seamless Co-op, opens a region for all players with this on once anyone unlocks it.

    Co-op players share one game on separate slots, so a region only some have unlocked
    kicks the rest out. With this on, when anyone unlocks a region, its door opens for
    everyone else who has it on. Doors only: nobody receives the Region Lock (the item that
    opens a region). Turn it on for every co-op player. Needs an up-to-date client; older
    ones refuse the seed.
    """

    display_name = "Region Sync (Seamless Co-op)"


@register
class RegionSyncFeature(Feature):
    name = "region_sync"
    OPTIONS = {"region_sync": RegionSync}

    def slot_data(self, world):
        if not bool(world.options.region_sync.value):
            return {}
        return {contract.REQUIRES_CLIENT_FEATURES: [CLIENT_FEATURE_TAG]}
