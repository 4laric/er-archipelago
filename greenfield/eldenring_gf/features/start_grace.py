"""Start experience -- Roundtable Hold as the start, early leveling, map reveal (matt-free).

The run starts at Roundtable Hold (the hub). This feature emits:
  startRegion = "Roundtable Hold" (HUB) -- the client's start anchor.
  startGraces = [71190] + early-leveling flags. 71190 is the Roundtable Hold warp-unlock grace
    (Table of Lost Grace, m11_10; confirmed in the prior apworld's base-hub startgraces). The run's
    first OPEN region comes from the precollected random region lock (core.create_items) -- its bundle
    graces light on receipt -- so this list only needs the hub grace to bootstrap the first warp.
  reveal_all_maps (bool).

startGraces doubles as the client's "set these flags at start" list (startgrants.rs), so Early Leveling
rides here: 4680 (Level Up enable) + 951 (Melina first-meeting done) -- the two flags her accord sets,
confirmed in-game (set both, rest, Level Up works, no cutscene). The first entry (a real grace) is the
client's clobber read-back sentinel. All ids are from prior in-game-verified work; none invented.
"""
from Options import DefaultOnToggle, Toggle
from ..registry import Feature, register
from .. import contract
from ..data import HUB

_ROUNDTABLE_GRACE = 71190       # Roundtable Hold, Table of Lost Grace (m11_10) warp-unlock flag
_LEVEL_UP_FLAG = 4680           # Level Up enable
_MELINA_SUPPRESS_FLAG = 951     # Melina first-meeting done / suppress her hand-off


class RevealAllMaps(DefaultOnToggle):
    """Reveal the whole world map (and the underground view) at the start, so you can navigate the
    shattered world. On by default. The client (startgrants.rs) owns the RE'd flag set -- base map
    reveal flags + underground view-unlock 82001 -- and applies them once, gated on the settled
    world; greenfield just requests it via this bool."""
    display_name = "Reveal All Maps"


class EarlyLeveling(DefaultOnToggle):
    """Level Up at any Site of Grace from the start, skipping Melina's accord and her meeting
    cutscene (sets event flags 4680 + 951). On by default so a Roundtable-start run can level
    immediately. The client sets these via the startGraces flag list."""
    display_name = "Early Leveling (skip Melina)"


class StartWithRegionLock(Toggle):
    """Start holding ONE random region's lock, so a region is open from Roundtable at run start
    (core.create_items precollects it; count-neutral). Off by default (the curated presets in
    greenfield/presets/ turn it on). When off, every region starts sealed and the first lock must be
    found -- still beatable because AP fill guarantees a Roundtable-reachable region Lock."""
    display_name = "Start With A Region Lock"


@register
class StartGrace(Feature):
    name = "start_grace"
    OPTIONS = {
        "reveal_all_maps": RevealAllMaps,
        "early_leveling": EarlyLeveling,
        "start_with_region_lock": StartWithRegionLock,
    }

    def slot_data(self, world):
        graces = [_ROUNDTABLE_GRACE]
        if world.options.early_leveling.value:
            graces += [_LEVEL_UP_FLAG, _MELINA_SUPPRESS_FLAG]
        return {
            contract.START_REGION: HUB,
            contract.START_GRACES: graces,
            contract.REVEAL_ALL_MAPS: bool(world.options.reveal_all_maps.value),
        }
