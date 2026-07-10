"""progression_surface -- CONFINE this world's own progression to a small, high-confidence location
set (v0.2; matt-style "important locations" restriction, not a soft weight).

matt's standalone ER randomizer HARD-RESTRICTS key items to an "important locations" whitelist (major
bosses always, plus opt-in golden-seed trees / sacred-tear churches / shops / other bosses); a separate
"bias slider" only tunes difficulty WITHIN that set. The bedrock AP port only got the SOFT half (mark
PRIORITY, advancement gets first crack -- features/curated_fill here). This feature adds the HARD half:
it pulls this world's OWN progression out of the pool and places it, via Fill.fill_restrictive, ONTO the
selected surface only -- default = MajorBoss (the ~24 boss_arena arena majors + the hand-picked
MAJOR_BOSS_EXTRAS, tagged 'MajorBoss' in location_tags). Everything else lands normally.

WHAT COUNTS AS "OUR PROGRESSION": the region Locks (the region-lock spine's gate items) plus any
conditionally-progression items -- required Great Runes (great_runes goal), Leyndell-gate runes, legacy
dungeon keys. Boss Keys are DELIBERATELY EXEMPT: with boss_keys on there are ~24 of them, they'd swamp
the tiny surface, and features/boss_locks already keeps them reachable in logic.

FEASIBILITY LADDER (never FillError): a surface smaller than the number of locks to place -- or a seed
with no sphere-0 anchor -- can't host every lock. So strict mode WIDENS the allowed surface one grouped
rung at a time (MajorBoss -> +Remembrance,GreatRune -> +Boss,KeyItem,Legendary -> +Seedtree,Church) and,
for anything still unplaced, RETURNS it to the pool for normal fill. Because the terminal action is
"back to the pool", generation can never hard-fail from this feature: worst case it degrades to v0.1
scatter. (The +Seedtree rung also unlocks the 2 Roundtable-Hold Golden Seeds, an always-reachable
sphere-0 bootstrap, so a no-precollect seed can still seed the lock chain.)

BASE-STATE FIX: reachability during the pre-fill is evaluated from mw.get_all_state(False) AFTER the
restricted items are pulled -- so the rest of the pool (Boss Keys, foreign advancement, any precollected
region Lock) counts as available, and a Boss-Key-gated boss check doesn't look falsely unreachable.
Placed locks are collected (lock=True) so multiworld progression-balancing can't later move them off the
surface. Runs from core.pre_fill; supersedes curated_fill when the mode is soft/strict.
"""
from Options import OptionList, Choice
from ..registry import Feature, register
from .. import contract

try:
    from ..location_tags import LOCATION_TAGS
except Exception:  # not yet generated -> feature is a no-op
    LOCATION_TAGS = {}


# Grouped widen order for the feasibility ladder. Each group is ADDED to the user's base surface in
# turn. Shop is intentionally NOT here: it would dump locks onto the hundreds of hub shop slots and
# defeat the restriction -- Shop is only ever in play if the user explicitly selects it in the base.
_WIDEN_GROUPS = [["Remembrance", "GreatRune"], ["Boss", "KeyItem", "Legendary"], ["Seedtree", "Church"]]
_BOSS_KEY_PREFIX = "Boss Key:"


class ProgressionSurface(OptionList):
    """Location classes allowed to HOST this world's own progression (region Locks + any required/gate
    Great Runes + legacy keys) under strict/soft mode. Default = MajorBoss (the ~24 arena majors plus
    the hand-picked field-boss extras). Add classes to widen -- e.g. Remembrance, GreatRune, Seedtree,
    Church, or Shop. Same vocabulary as Important / Big-Ticket Locations; Enia is always excluded."""
    display_name = "Progression Surface"
    default = ["MajorBoss"]
    valid_keys = frozenset(contract.IMPORTANT_LOCATION_TYPES)


class ProgressionSurfaceMode(Choice):
    """How the Progression Surface is enforced. off = v0.1 behavior (curated_fill toggle honored).
    soft = mark-and-spill over the surface (old curated_fill semantics: first crack, leftovers scatter).
    strict = CONFINE this world's progression to the surface, widening only via the feasibility ladder
    when the surface can't host every lock. Default strict."""
    display_name = "Progression Surface Mode"
    option_off = 0
    option_soft = 1
    option_strict = 2
    default = 2


# ---- pure, host-testable helpers (no AP import; unit-tested with synthetic tags) ------------------
def selected_surface(sel):
    """Filter a raw selection (list of class names) to the valid vocabulary, order preserved."""
    valid = set(contract.IMPORTANT_LOCATION_TYPES)
    return [c for c in (sel or []) if c in valid]


def build_ladder(selection):
    """Ordered list of allowed-class-sets for the STRICT feasibility ladder, starting from the user's
    base surface and widening by _WIDEN_GROUPS. Pure. Empty selection -> [] (feature no-op)."""
    base = selected_surface(selection)
    if not base:
        return []
    rungs = [list(base)]
    acc = list(base)
    for grp in _WIDEN_GROUPS:
        add = [c for c in grp if c not in acc]
        if add:
            acc = acc + add
            rungs.append(list(acc))
    return rungs


def allowed_ap_ids(tags_map, classes):
    """ap-ids whose tags make them big-ticket for `classes` (Enia hard-excluded). Pure."""
    sel = set(classes)
    return {ap for ap, tags in tags_map.items() if contract.is_big_ticket(tags, sel)}


def is_restricted_progression(item, player):
    """True iff `item` is THIS world's own progression that we confine: advancement, owned by `player`,
    and NOT a Boss Key (those are exempt). Pure over an item-like with .player/.advancement/.name."""
    if getattr(item, "player", None) != player or not getattr(item, "advancement", False):
        return False
    return not str(getattr(item, "name", "")).startswith(_BOSS_KEY_PREFIX)


def lock_region_name(item_name):
    """'Limgrave Lock' -> 'Limgrave'; None for a non-lock name. Pure."""
    s = str(item_name)
    return s[:-len(" Lock")] if s.endswith(" Lock") else None


def regions_with_major_boss(region_names, tags_map=None, locations=None):
    """Subset of `region_names` that HOST at least one MajorBoss location -- the regions eligible to be
    the strict sphere-0 anchor. Pure over the generated LOCATION_TAGS + LOCATIONS maps (defaults to the
    module globals). Empty if tags aren't generated yet (caller then falls back to any region)."""
    tm = LOCATION_TAGS if tags_map is None else tags_map
    if locations is None:
        try:
            from ..data import LOCATIONS as locations
        except Exception:
            locations = {}
    locs = locations
    out = set()
    for r in region_names:
        for (_n, ap, _f) in locs.get(r, []):
            if "MajorBoss" in (tm.get(ap) or ()):
                out.add(r)
                break
    return out


# ---- AP glue --------------------------------------------------------------------------------------
def _mode(world):
    o = getattr(world.options, "progression_surface_mode", None)
    return int(o.value) if o is not None else 0


def _restricted_items(world):
    return [it for it in world.multiworld.itempool
            if is_restricted_progression(it, world.player)]


def _open_allowed(world, classes):
    """Unfilled locations of this player whose tags are big-ticket for `classes`."""
    ids = allowed_ap_ids(LOCATION_TAGS, classes)
    out = []
    for loc in world.multiworld.get_locations(world.player):
        ap = getattr(loc, "address", None)
        if ap is not None and ap in ids and loc.item is None:
            out.append(loc)
    return out


def _place(world, allowed, to_place, lock):
    """One fill_restrictive pass. Base state = get_all_state(False) (the base-state fix): the rest of
    the pool + precollected + already-placed locks count as available, so gated majors look reachable.
    fill_restrictive mutates to_place in place, leaving only the UNPLACED items."""
    from Fill import fill_restrictive
    mw = world.multiworld
    state = mw.get_all_state(False)
    try:
        fill_restrictive(mw, state, allowed, to_place, single_player_placement=True,
                         lock=lock, allow_partial=True)
    except TypeError:  # older AP signature without allow_partial
        fill_restrictive(mw, state, allowed, to_place, single_player_placement=True)


def apply(world) -> None:
    """core.pre_fill hook (mode soft/strict). Confine this world's own progression to the selected
    surface; widen via the ladder; return the remainder to the pool. Never FillErrors."""
    mode = _mode(world)
    if mode == 0 or not LOCATION_TAGS:
        return
    surface = selected_surface(getattr(world.options, "progression_surface", None)
                              and world.options.progression_surface.value)
    if not surface:
        return
    mw = world.multiworld
    to_place = _restricted_items(world)
    if not to_place:
        return
    try:
        import Fill  # noqa: F401  -- ensure the fill API exists before we disturb the pool
    except Exception:
        return
    n0 = len(to_place)
    for it in to_place:
        mw.itempool.remove(it)
    strict = (mode == 2)
    rungs = build_ladder(surface) if strict else [list(surface)]
    resolved = rungs[0] if rungs else list(surface)
    for classes in rungs:
        if not to_place:
            break
        allowed = _open_allowed(world, classes)
        world.random.shuffle(allowed)
        resolved = classes
        _place(world, allowed, to_place, lock=strict)
    # Anything the surface (+ladder) could not host goes back to the pool for normal fill -> winnable.
    for it in to_place:
        mw.itempool.append(it)
    world.gf_prog_surface_resolved = list(resolved)
    world.gf_prog_surface_spilled = len(to_place)
    world.gf_prog_surface_placed = n0 - len(to_place)


@register
class ProgressionSurfaceFeature(Feature):
    name = "progression_surface"
    OPTIONS = {"progression_surface": ProgressionSurface,
               "progression_surface_mode": ProgressionSurfaceMode}
    # No items, no slot_data key in Cut 1 (client contract = Cut 2). Placement runs centrally from
    # core.pre_fill via apply() (locations exist + get_all_state valid there).
