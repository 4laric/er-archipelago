"""Leyndell great-rune gate (opt-in-by-default) -- the capital sits behind >=N Great Runes.

Leyndell was folded into the Altus Plateau goal region (capstone re-carve), so "Leyndell" is a SUBSET
of Altus's checks -- the capital proper (m11 Royal + Ashen), Subterranean Shunning-Grounds (m35, entered
from the capital) and the Fractured Marika / final arena (m19). This gate adds a LOGIC access rule to
exactly those checks: you need >=N Great Runes (any of the game's Great Runes) IN ADDITION to the Altus
Lock, mirroring the vanilla "two great runes to enter the capital" feel.

Winnability by construction: the N runes that satisfy the gate are marked PROGRESSION (core._class_for
reads world.gf_leyndell_runes), so AP fill guarantees N Great Runes are reachable and -- because the
Leyndell checks require them -- places them OUTSIDE Leyndell. N is CLAMPED to the number of Great Runes
actually in the pool this seed (world._available_runes()), so sealing rune regions (num_regions) or
DLC Only simply lowers the requirement (to 0 = no gate) rather than making a seed unbeatable.

Option `leyndell_runes_required` (Range 0..6, default 2). 0 -> no gate (and world.gf_leyndell_runes is
empty, so nothing is marked progression and default fill is unchanged). Base-game only: under DLC Only
the goal region (Leyndell) is sealed, so the gate auto-skips. LOGIC-only for now; a client hard-gate
(kick out of the m11/m35/m19 play_regions until N runes) is a follow-up (needs a slot_data + client
flag-watch pass, like the region kick-watch).
"""
from Options import Range
from ..registry import Feature, register

try:
    from ..region_spine import GOAL_REGION
except Exception:  # pragma: no cover
    GOAL_REGION = "Altus Plateau"
try:
    from ..data import LOCATIONS
except Exception:
    LOCATIONS = {}
try:
    from ..item_ids import ITEM_CATALOG
except Exception:
    ITEM_CATALOG = {}

# Great Rune item names (matt-free: read from the greenfield catalog, same rule as core.GREAT_RUNES).
GREAT_RUNES = sorted(nm for nm in ITEM_CATALOG if nm.endswith("Great Rune"))
# Folded-Leyndell map prefixes: m11 = Leyndell Royal + Ashen Capital, m35 = Subterranean
# Shunning-Grounds (dropped into from the capital), m19 = Fractured Marika / final arena. The
# acquisition flag encodes the map (mAA -> AA......), so an m11/m35/m19 flag in the goal region is a
# capital check. Restricting to GOAL_REGION keeps Altus's own overworld checks (61xxx/63xxx/76xxx) out.
_LEYNDELL_PREFIXES = ("11", "35", "19")


def _leyndell_location_ids():
    out = set()
    for reg, locs in LOCATIONS.items():
        if reg != GOAL_REGION:
            continue
        for (_name, ap_id, flag) in locs:
            if str(flag)[:2] in _LEYNDELL_PREFIXES:
                out.add(ap_id)
    return out


class LeyndellRunesRequired(Range):
    """Great Runes needed to access Leyndell (the folded capital: m11 Royal/Ashen + Shunning-Grounds
    + Fractured Marika), on top of the Altus Plateau Lock. 0 disables the gate. Clamped down to the
    Great Runes actually in the pool, so it can never make a seed unbeatable."""
    display_name = "Leyndell Great Runes Required"
    range_start = 0
    range_end = 6
    default = 2


@register
class LeyndellGate(Feature):
    name = "leyndell_gate"
    OPTIONS = {"leyndell_runes_required": LeyndellRunesRequired}

    def generate_early(self, world) -> None:
        # Pick the concrete runes that satisfy the gate (clamped to what's in the pool); core marks
        # these progression so fill guarantees them reachable OUTSIDE Leyndell. Empty -> gate off.
        world.gf_leyndell_runes = []
        opt = getattr(world.options, "leyndell_runes_required", None)
        want = int(opt.value) if opt is not None else 0
        if want <= 0 or not GREAT_RUNES:
            return
        if not (getattr(world.options, "item_shuffle", None) and world.options.item_shuffle.value):
            return  # runes only enter the pool when vanilla items are shuffled
        if GOAL_REGION not in world._kept():
            return  # DLC Only / sealed goal region -> no Leyndell to gate
        avail = world._available_runes()             # Great Runes actually in the pool this seed
        want = min(want, len(avail))
        world.gf_leyndell_runes = sorted(avail)[:want]

    def set_rules(self, world) -> None:
        runes = getattr(world, "gf_leyndell_runes", [])
        if not runes:
            return
        need = len(runes)
        leyndell = _leyndell_location_ids()
        if not leyndell:
            return
        player = world.player
        for loc in world.multiworld.get_locations(player):
            if getattr(loc, "address", None) not in leyndell:
                continue
            prev = loc.access_rule
            loc.access_rule = (lambda state, p=prev, gr=GREAT_RUNES, k=need:
                               p(state) and sum(1 for g in gr if state.has(g, player)) >= k)

    def slot_data(self, world):
        return {}  # LOGIC-only; no client contract key yet (hard in-game gate = follow-up)
