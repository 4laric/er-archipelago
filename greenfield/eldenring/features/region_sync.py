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
    """Share region unlocks with the other Elden Ring players in this multiworld.

    For seamless co-op. Everyone plays in ONE physical world (the co-op host's), but each player
    has their own Archipelago slot -- so if one of you has unlocked Liurnia and the rest have not,
    the rest get kicked out of it and cannot follow. With this on, the moment ANY Elden Ring player
    who also turned it on unlocks a region, that region's door opens for all of you: the map gate
    lifts and its Sites of Grace light up.

    It only opens the door. It does NOT give anyone else the region's key item -- that stays
    wherever the multiworld put it, and finding your own is still what counts for your items and
    your goal. Nothing about how the seed is generated changes, so you can turn this on without
    making anyone's game easier to complete.

    Turn it on for every Elden Ring player in the co-op group; players who leave it off are not
    affected either way, and other games in the multiworld never see it.
    """

    display_name = "Region Sync"


@register
class RegionSyncFeature(Feature):
    name = "region_sync"
    OPTIONS = {"region_sync": RegionSync}

    def slot_data(self, world):
        if not bool(world.options.region_sync.value):
            return {}
        return {contract.REQUIRES_CLIENT_FEATURES: [CLIENT_FEATURE_TAG]}
