"""Leyndell great-rune gate (opt-in-by-default) -- the capital sits behind >=N Great Runes.

Region-spine v2: Leyndell is a first-class GOAL region again (m11 Royal + Ashen fold + m19 Fractured
Marika). This gate adds a LOGIC access rule to its checks: >=N Great Runes (any of the game's Great
Runes) IN ADDITION to the Leyndell Lock, mirroring the vanilla "two great runes to enter the
capital". The m35 Shunning-Grounds rode this gate while it was folded into Altus; it is the SEWER
region now, gated by its own Lock and not by runes.

Winnability by construction: the N runes that satisfy the gate are marked PROGRESSION (core._class_for
reads world.gf_leyndell_runes), so AP fill guarantees N Great Runes are reachable and -- because the
Leyndell checks require them -- places them OUTSIDE Leyndell. N is CLAMPED to the number of Great Runes
actually in the pool this seed (world._available_runes()), so sealing rune regions (num_regions) or
DLC Only simply lowers the requirement (to 0 = no gate) rather than making a seed unbeatable.

Option `leyndell_runes_required` (Range 0..6, default 2). 0 -> no gate (and world.gf_leyndell_runes is
empty, so nothing is marked progression and default fill is unchanged). Base-game only: under DLC Only
the goal region (Leyndell) is sealed, so the gate auto-skips. In-game the wall needs no client half at
all (gated-children fix, 2026-07-14): the capital's grace bundle is WITHHELD (features/graces.py), so
the only way in is the game's own main gate, which opens when the player holds N Great Runes -- the
runes arrive as AP items and the client's key-item grant makes the game count them. This gate's job
is the LOGIC mirror: mark N runes progression and require them on Leyndell's entrance + checks so
fill never strands progression past a wall it can't prove open.
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
# Capital map prefixes: m11 = Leyndell Royal + Ashen Capital, m19 = Fractured Marika / final
# arena. The acquisition flag encodes the map (mAA -> AA......), so an m11/m19 flag in the goal
# region is a capital check. Restricting to GOAL_REGION keeps HUB-overridden m11_10 Roundtable
# checks out (they region to the hub). m35 left this list with the Sewer split (v2); 510250
# (Mohg the Omen) left with it.
_LEYNDELL_PREFIXES = ("11", "19")
_LEYNDELL_EXTRA_FLAGS = frozenset({173, 510040, 60520})  # Morgott GR + Rem. Omen King, Godfrey pouch
# Gating items forbidden on Leyndell-gated locs = Great Runes (the gate's own prerequisite) PLUS the
# folded-dungeon legacy keys (Academy Glintstone Key, Hole-Laden Necklace) -- keeping a key off a
# rune-gated capital check breaks the Metyr<->Leyndell cross-gate cycle (FillError 2026-07-10).
_LEGACY_KEY_NAMES = frozenset({"Academy Glintstone Key", "Hole-Laden Necklace"})
_GATING_ITEMS = frozenset(GREAT_RUNES) | _LEGACY_KEY_NAMES


def _gated_region_names(world):
    """Every region physically behind the 'To <GOAL_REGION>' edge, DERIVED from the live region
    graph: the goal region plus everything reachable through its exits -- the Sewer (gated child,
    region_spine.REGION_PARENT) and the finale's Ashen Capital (features/finale.py hangs it off the
    capital), plus any future child, without this list needing to know their names. A location in
    this subtree sits behind the rune wall, so a gating item placed there can deadlock the very
    gate it opens. Empty when the goal region is sealed this seed (dlc_only)."""
    try:
        start = world.multiworld.get_region(GOAL_REGION, world.player)
    except KeyError:
        return frozenset()
    seen = {GOAL_REGION}
    stack = [start]
    while stack:
        for exit_ in stack.pop().exits:
            dst = getattr(exit_, "connected_region", None)
            if dst is not None and dst.name not in seen:
                seen.add(dst.name)
                stack.append(dst)
    return frozenset(seen)


def _leyndell_location_ids():
    out = set()
    for reg, locs in LOCATIONS.items():
        if reg != GOAL_REGION:
            continue
        for (_name, ap_id, flag) in locs:
            if str(flag)[:2] in _LEYNDELL_PREFIXES or int(flag) in _LEYNDELL_EXTRA_FLAGS:
                out.add(ap_id)
    return out


class LeyndellRunesRequired(Range):
    """Great Runes needed to access Leyndell (m11 Royal/Ashen + Fractured Marika), on top of the
    Leyndell Lock. 0 disables the gate. Clamped down to the Great Runes actually in the pool, so it
    can never make a seed unbeatable."""
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
        player = world.player
        # ENTRANCE rule (2026-07-14, gated-children fix): the rune requirement also guards the
        # "To Leyndell" edge itself. core.create_regions parents gated children (REGION_PARENT), so
        # Leyndell hangs off Altus and the SEWER hangs off Leyndell -- gating the entrance makes the
        # rune wall transitive exactly like the physical one (the m35 well is inside the capital;
        # you cannot reach it runeless). The per-location rules below stay: they carry the
        # item_rule cycle-breaker and cover the capital checks directly.
        try:
            entrance = world.multiworld.get_entrance(f"To {GOAL_REGION}", player)
        except KeyError:
            entrance = None  # goal region sealed (dlc_only) -- generate_early already bailed then
        if entrance is not None:
            prev_ent = entrance.access_rule
            entrance.access_rule = (lambda state, p=prev_ent, gr=GREAT_RUNES, k=need:
                                    p(state) and sum(1 for g in gr if state.has(g, player)) >= k)
        # ITEM rule (2026-07-15, sewer-rune FillError): the _GATING_ITEMS bar must cover the WHOLE
        # walled subtree, not just the capital's own m11/m19 checks. Under accessibility:minimal,
        # AP's fill_restrictive SKIPS the reachability check whenever the exploration state can
        # already beat the game (Fill.py perform_access_check) -- and with the region_locks ending
        # the completion condition never mentions the gate runes, so a rune's OWN placement is
        # exactly when the check is skipped (a Lock's never is: completion needs every Lock, so
        # "beaten" is false while that Lock is in hand). The strict progression_surface pre-fill
        # then LOCKS the rune wherever item_rule allows: seed 36 locked Godrick's Great Rune onto
        # Mohg the Omen (Sewer :: [Incantation] Bloodflame Talons, f510250) -- behind the very
        # wall it opens -- and post_fill's audit_reachable correctly FillErrored. item_rule is the
        # one rule can_fill honors UNCONDITIONALLY, so it, not the (transitive) entrance rule, is
        # the load-bearing guard; it must span every region the wall spans. The Sewer had this bar
        # while m35 rode the prefix list; the v2 region split silently dropped it.
        gated_regions = _gated_region_names(world)
        leyndell = _leyndell_location_ids()
        for loc in world.multiworld.get_locations(player):
            region = getattr(getattr(loc, "parent_region", None), "name", None)
            if region not in gated_regions:
                continue
            if getattr(loc, "address", None) in leyndell:
                prev = loc.access_rule
                loc.access_rule = (lambda state, p=prev, gr=GREAT_RUNES, k=need:
                                   p(state) and sum(1 for g in gr if state.has(g, player)) >= k)
            prev_item = loc.item_rule
            loc.item_rule = (lambda item, pv=prev_item:
                             pv(item) and item.name not in _GATING_ITEMS)

    def slot_data(self, world):
        return {}  # LOGIC-only; no client contract key yet (hard in-game gate = follow-up)
