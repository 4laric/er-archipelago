"""Radahn festival gate (matt-free, LOGIC-only).

Radahn's own rewards -- Radahn's Great Rune (173-sibling flag 172) and Remembrance of the Starscourge
(510300) -- are handed out by the Radahn fight at the Redmane Castle FESTIVAL. In vanilla the festival
only begins once you have reached Altus Plateau, so those two Caelid checks actually sit behind the
ALTUS PLATEAU LOCK on top of Caelid's own Lock. Without this rule a seed can place a progression item
on a Radahn check and believe it reachable with just the Caelid Lock, when the fight needs Altus first
-- the same stranding shape as the Morgott's-Great-Rune mis-region.

We apply the Altus-Lock requirement ALWAYS: when Altus is sealed (num_regions), its Lock is never
placed, so `state.has("Altus Plateau Lock")` stays False and the Radahn checks become unreachable --
which is correct (no Altus -> no festival -> no Radahn reward; the great_runes goal clamps to the
runes actually reachable, so it stays winnable). Under `accessibility: minimal` an unsatisfiable rule
simply makes those checks non-progression rather than breaking the fill.

Alternative (client, not done here): auto-set the festival-start flag on connect -- like the
Fingerslayer Blade grant -- which would instead make the festival always available and let the Radahn
checks be Caelid-reachable with no cross-region dependency. If that lands, drop this gate.
"""
from ..registry import Feature, register

try:
    from ..data import LOCATIONS
except Exception:  # pragma: no cover
    LOCATIONS = {}
try:
    from ..region_spine import GOAL_REGION
except Exception:  # pragma: no cover
    GOAL_REGION = "Altus Plateau"

# Radahn's own drops (the festival fight). Keyed by acquisition flag so it survives ap-id churn.
_FESTIVAL_FLAGS = frozenset({172, 510300})
_ALTUS_LOCK = f"{GOAL_REGION} Lock"


def _festival_location_ids():
    out = set()
    for _reg, locs in LOCATIONS.items():
        for (_name, ap_id, flag) in locs:
            if int(flag) in _FESTIVAL_FLAGS:
                out.add(ap_id)
    return out


@register
class FestivalGate(Feature):
    name = "festival_gate"

    def set_rules(self, world) -> None:
        targets = _festival_location_ids()
        if not targets:
            return
        player = world.player
        for loc in world.multiworld.get_locations(player):
            if getattr(loc, "address", None) not in targets:
                continue
            prev = loc.access_rule
            loc.access_rule = (lambda state, p=prev, lk=_ALTUS_LOCK:
                               p(state) and state.has(lk, player))

    def slot_data(self, world):
        return {}  # LOGIC-only; no client contract key
