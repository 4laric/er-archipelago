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
rung at a time, highest-confidence first (MajorBoss -> +Remembrance,GreatRune -> +KeyItem -> +Boss ->
+Legendary -> +Seedtree,Church) and,
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
from Options import OptionSet, Choice, DefaultOnToggle
from ..registry import Feature, register
from .. import contract

try:
    from ..location_tags import LOCATION_TAGS
except Exception:  # not yet generated -> feature is a no-op
    LOCATION_TAGS = {}


# Grouped widen order for the feasibility ladder, HIGHEST-CONFIDENCE FIRST. Each group is ADDED to the
# user's base surface in turn. The order is a confidence ranking: Remembrance/GreatRune are the same
# named demigods' guaranteed drops (≈ MajorBoss certainty); KeyItem is a small, hand-reviewable set (~14)
# so it comes BEFORE Legendary, which is a large scattered set (~84) nobody can vouch for from memory;
# Boss (the fixed minor-boss arenas) sits between them; Seedtree/Church (the collectible markers) stay
# last. Shop is intentionally NOT here: it would dump locks onto the hundreds of hub shop slots and
# defeat the restriction -- Shop is only ever in play if the user explicitly selects it in the base.
_WIDEN_GROUPS = [["Remembrance", "GreatRune"], ["KeyItem"], ["Boss"], ["Legendary"], ["Seedtree", "Church"]]
_BOSS_KEY_PREFIX = "Boss Key:"


class ProgressionSurface(OptionSet):
    """WHICH LOCATIONS MAY HOLD PROGRESSION. The location classes allowed to host this world's own
    progression (region Locks, any required/gate Great Runes, legacy keys) -- and, in a multiworld,
    the classes where OTHER players' progression can land in your world.

    Default (193 locations): the major bosses and remembrances, the great runes, the key items, and the
    collectathon lines -- Sacred Tears (Church), Golden Seeds (Seedtree), Scadutree Fragments and
    Revered Spirit Ashes for the DLC -- plus ShopSlot.

    ShopSlot is AT MOST one slot per merchant, never every shop row: a merchant enters the pool once,
    so however large their stock they can hold at most one progression item and cannot dominate the
    surface by breadth. The pinned slot is a ware that merchant ALONE sells (one stock flag game-wide,
    so the location is unambiguous), stocked from the start and with a resolved region; merchants with
    no such ware are skipped at regen (location_tags.SHOP_SLOT_SKIPS lists them with reasons). Use
    `Shop`/`ShopNonSpell` instead if you actually want a merchant-heavy seed -- be aware that is ~70%
    of the surface and the game becomes "farm runes, buy your progression".

    Narrowing is safe: the feasibility ladder widens automatically rather than failing to generate, and
    an EMPTY set turns the confinement off entirely (progression scatters as vanilla AP fill decides).
    Basin = Crystal Tears; Boss = every boss-healthbar drop; Legendary = the param-rarity legendaries."""
    display_name = "Progression Surface"
    # The v0.2 default. This was three classes (33 locations) for one reason: the location DATA could
    # not be trusted, so it was held to what a human could hand-verify. The provenance work (MSB/EMEVD
    # ground truth, the region oracle, the phantom-flag guard) removed that constraint, and the category
    # tags are now derived from what each flag's ItemLotParam lot actually GRANTS -- audited against
    # ground truth: Sacred Tear 13/13, Golden Seed 43/43, Scadutree Fragment 46/46, Revered 23/23.
    # Single-sourced in contract.py: the AP-free tracker generator needs this same selection and
    # cannot import an AP OptionSet. See contract.SURFACE_DEFAULT_CLASSES.
    default = contract.SURFACE_DEFAULT_CLASSES
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


class ConfineForeignProgression(DefaultOnToggle):
    """Confine OTHER players' progression to your Progression Surface too, not just your own.

    ON (default): in a multiworld, another world's advancement items may only be placed on your
    surface locations -- the same high-confidence checks your own region Locks use -- never on your
    filler checks. So a foreign key spell lands on a major-boss/remembrance/key-item check of yours,
    not on a random Smithing Stone pickup. OFF: foreign progression scatters across any reachable
    location of yours, which is standard Archipelago behaviour.

    No effect in a solo seed, or when Progression Surface Mode is off. It never blocks generation:
    your OWN progression keeps its feasibility-ladder + spill safety valve, and foreign progression
    that will not fit your surface simply lands in its own world instead (only YOUR filler checks are
    barred to it -- other worlds are untouched)."""
    display_name = "Confine Foreign Progression"


# ---- pure, host-testable helpers (no AP import; unit-tested with synthetic tags) ------------------
def selected_surface(sel):
    """Filter a raw selection to the valid vocabulary, in CANONICAL (vocabulary) order.

    DETERMINISM: this option is an OptionSet, and a Python set of strings does NOT have a stable
    iteration order across processes (string hashing is randomised per run). Ordering by the selection
    would therefore make the ladder -- and the fill that follows it -- differ between two runs of the
    SAME seed. So the order comes from the VOCABULARY, never from the caller's container. (This is the
    same class of bug as regionSphereTargetRanges being emitted in set-iteration order, 2026-07-11.)
    Accepts a list or a set; the result is identical either way."""
    chosen = set(sel or ())
    return [c for c in contract.IMPORTANT_LOCATION_TYPES if c in chosen]


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


def _roundtable_merchant_aps():
    """Roundtable Hold (the always-open hub) MERCHANT ShopSlots -- Enia (remembrance weapons/armor)
    and the Twin Maiden Husks. BARRED from the progression surface (Alaric 2026-07-18): the hub is
    reachable at spawn, so a Lock / key item placed on a hub merchant slot is 'progression' you already
    hold on turn one -- trivial. This rule touches ONLY hub ShopSlots; the hub's Golden Seed checks
    (Seedtree, physical pickups) are left to the normal surface/defaulted logic. Derived from the
    generated data, so a regen that adds or moves a hub ShopSlot is covered without a hand-list."""
    try:
        from ..data import LOCATIONS, HUB
        from ..location_tags import LOCATION_TAGS as _lt
    except Exception:
        return frozenset()
    return frozenset(ap for (_n, ap, _f) in LOCATIONS.get(HUB, ())
                     if "ShopSlot" in _lt.get(ap, ()))


def allowed_ap_ids(tags_map, classes, defaulted=None):
    """ap-ids whose tags put them ON THE SURFACE for `classes` (Roundtable-Hold merchants -- Enia +
    Twin Maiden Husks -- hard-excluded). Pure.

    Checks in `defaulted` (DEFAULTED_REGION_APS) are BARRED regardless of tags: their region was a
    guess that fell back to the hub, so AP believes them reachable at spawn while the item actually
    spawns wherever it really lives. Fill put a STORMVEIL CASTLE LOCK on one such Golden Seed
    (flag 400220, really in Stormveil) in a Caelid-start seed -- unwinnable. A guessed region may not
    carry progression. See gen_data._region_is_derived(). The hub MERCHANT slots are barred for a
    related reason -- always reachable at spawn -> trivial progression (see _roundtable_merchant_aps)."""
    sel = set(classes)
    if defaulted is None:
        try:
            from ..location_tags import DEFAULTED_REGION_APS as _d
        except Exception:
            _d = frozenset()
        try:
            # m11_00 (normal Leyndell): destroyed when Maliketh dies (the Erdtree burns). Same rule --
            # a check the player can put permanently out of reach may not carry progression.
            from ..location_tags import ERDTREE_BURN_APS as _b
        except Exception:
            _b = frozenset()
        defaulted = frozenset(_d) | frozenset(_b)
    # Hub merchant slots are barred in EVERY path (own + foreign), regardless of how `defaulted` was
    # computed/passed -- this is the single surface chokepoint both confinements funnel through.
    # SURFACE_EXCLUDE_APS (hand-excluded surface-tagged checks, e.g. Secret Rite Scroll -- gen_data
    # _SURFACE_EXCLUDE_FLAGS) are barred here too, always, for the same reason.
    try:
        from ..location_tags import SURFACE_EXCLUDE_APS as _sx
    except Exception:
        _sx = frozenset()
    barred = frozenset(defaulted) | _roundtable_merchant_aps() | frozenset(_sx)
    return {ap for ap, tags in tags_map.items()
            if contract.has_class(tags, sel) and ap not in barred}


def is_restricted_progression(item, player):
    """True iff `item` is THIS world's own progression that we confine: advancement, owned by `player`,
    and NOT a Boss Key (those are exempt). Pure over an item-like with .player/.advancement/.name."""
    if getattr(item, "player", None) != player or not getattr(item, "advancement", False):
        return False
    return not str(getattr(item, "name", "")).startswith(_BOSS_KEY_PREFIX)


def foreign_advancement_barred(item, player):
    """True iff `item` is ANOTHER player's advancement item -- the thing confine_foreign_progression
    keeps off this world's non-surface (filler) checks. Our OWN items (any classification) and any
    non-advancement item pass. Pure over an item-like with .player/.advancement. The core item_rule on
    a non-surface location is `not foreign_advancement_barred(item, self.player)`."""
    return bool(getattr(item, "advancement", False)) and getattr(item, "player", None) != player


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
def _selection(world):
    """The classes this world's surface is built from. ONE resolution, read by BOTH apply() (where the
    locks go) and slot_data() (what the client stars). If those two ever computed the surface
    differently we would be back to two lists disagreeing -- which is the bug big-ticket was."""
    opt = getattr(world.options, "progression_surface", None)
    return opt.value if opt is not None else None


def _mode(world):
    o = getattr(world.options, "progression_surface_mode", None)
    return int(o.value) if o is not None else 0


def confined_surface_ids(world):
    """The ap-ids of THIS world that MAY host foreign progression, when confine_foreign_progression is
    on -- i.e. the selected surface. Core bars other players' advancement on every own location whose
    ap-id is NOT in this set, confining foreign progression to the same checks the own region Locks use.
    Returns None when the feature is inactive (option off, surface mode off, empty surface, or tags not
    generated), meaning 'apply no foreign bar'. Uses the SAME surface resolution as apply()/slot_data(),
    so where foreign progression may land and where own progression is placed can never disagree."""
    o = getattr(world.options, "confine_foreign_progression", None)
    if o is None or not int(getattr(o, "value", 0)) or _mode(world) == 0 or not LOCATION_TAGS:
        return None
    classes = selected_surface(_selection(world))
    if not classes:
        return None
    return allowed_ap_ids(LOCATION_TAGS, classes, defaulted=_world_barred_aps(world))


def _restricted_items(world):
    return [it for it in world.multiworld.itempool
            if is_restricted_progression(it, world.player)]


def _world_barred_aps(world):
    """The per-world no-progression set for surface math: DEFAULTED_REGION_APS always; the
    ERDTREE_BURN_APS burn-strand bar only while the capital reconciler is NOT armed (armed = the
    client restores m11_00, so the strand those APs were barred for cannot happen -- SPEC-capital-
    reconciler.md). Mirrors core._add_locations' item_rule carve-out; the two must agree or the
    surface would star checks the item_rule forbids (or vice versa)."""
    try:
        from ..location_tags import DEFAULTED_REGION_APS as _d
    except Exception:
        _d = frozenset()
    if getattr(world, "gf_capital_reconciler", False):
        return frozenset(_d)
    try:
        from ..location_tags import ERDTREE_BURN_APS as _b
    except Exception:
        _b = frozenset()
    return frozenset(_d) | frozenset(_b)


def _open_allowed(world, classes):
    """Unfilled locations of this player whose tags put them ON THE SURFACE for `classes`."""
    ids = allowed_ap_ids(LOCATION_TAGS, classes, defaulted=_world_barred_aps(world))
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
    surface = selected_surface(_selection(world))
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

    # D (2026-07-10): break the boss-key <-> region-lock cycle. When boss_keys is on, the default
    # surface IS key-gated boss checks, and `_place` validates against get_all_state (which counts
    # every Boss Key as held), so a region Lock freezes onto a key-gated check while the key itself can
    # land behind that very Lock => softlock (reproduced ~24% under accessibility:minimal). For every
    # Lock we placed on a key-gated check, PRECOLLECT that Boss Key -- making get_all_state's assumption
    # actually true -- and add one filler to stay count-neutral. Independent of accessibility mode /
    # fill order / multiworld. As non-boss premium surfaces are added, fewer keys land here and boss
    # keys regain teeth (Locks stop always landing on boss checks). See boss_locks.key_gate_map.
    try:
        from .boss_locks import key_gate_map
        gate = key_gate_map(world)
    except Exception:
        gate = {}
    precollected = 0
    if gate:
        for loc in mw.get_locations(world.player):
            ap = getattr(loc, "address", None)
            placed = getattr(loc, "item", None)
            if ap not in gate or placed is None:
                continue
            if not is_restricted_progression(placed, world.player):
                continue
            kname = gate[ap]
            kitem = next((it for it in mw.itempool
                          if it.player == world.player and it.name == kname), None)
            if kitem is None:
                continue  # key already precollected (another Lock on the same boss) or not in pool
            mw.itempool.remove(kitem)
            mw.push_precollected(kitem)
            mw.itempool.append(world.create_filler())
            precollected += 1
    world.gf_prog_surface_keys_precollected = precollected


def audit_reachable(world) -> None:
    """post_fill SAFETY NET (F). From a REAL CollectionState (precollected only), verify every own
    advancement item is actually reachable. Any own advancement item at an unreachable location is a
    shipped softlock under accessibility:minimal (AP skips its own full-accessibility check there).

    RESCUE-THEN-FAIL: first try to salvage the seed -- swap each stranded item into a reachable,
    unlocked, filler-holding location of ours (the filler moves to the now-unreachable slot, which is
    harmless). Reachability only grows as progression moves into reachable slots, so we iterate + re-
    sweep until stable. Only raise FillError when a stranded item CANNOT be rescued (its placement is
    locked, or no reachable filler slot remains) -- so a salvageable seed ships instead of dying, and a
    genuinely unwinnable one fails loudly at generation instead of hours into a playthrough. Catches
    any residual boss-key/region-lock cycle or stranded rune/legacy key, whatever minted it. FAIL-OPEN
    on an internal audit error (never block gen on an audit bug). Only guards the surface regime."""
    if _mode(world) == 0:
        return
    try:
        from BaseClasses import CollectionState
        from Fill import FillError, swap_location_item
    except Exception as e:
        import logging
        logging.getLogger("Greenfield").warning("audit_reachable: imports failed (%r)", e)
        return

    mw = world.multiworld
    player = world.player

    def _detail(locs):
        return ", ".join(f"{l.item.name} @ {l.name}" for l in locs[:8])

    def _stranded(state, locs):
        return [l for l in locs if l.item is not None and l.item.player == player
                and l.item.advancement and not l.can_reach(state)]

    try:
        my_locs = list(mw.get_locations(player))
        rescued = 0
        for _ in range(len(my_locs) + 2):
            state = CollectionState(mw)
            state.sweep_for_advancements()
            stranded = _stranded(state, my_locs)
            if not stranded:
                break
            locked = [l for l in stranded if l.locked]
            if locked:  # a locked placement can't be moved -> unrescuable
                raise FillError(f"[greenfield] {len(locked)} own progression item(s) LOCKED & unreachable "
                                f"after fill -- unrescuable soft-lock; regenerate. First: {_detail(locked)}")
            _strand_ids = {id(l) for l in stranded}
            targets = [l for l in my_locs
                       if not l.locked and l.item is not None and not l.item.advancement
                       and id(l) not in _strand_ids and l.can_reach(state)]
            if not targets:
                raise FillError(f"[greenfield] {len(stranded)} own progression item(s) unreachable and no "
                                f"reachable filler slot to rescue into; regenerate. First: {_detail(stranded)}")
            moved = 0
            for sl in stranded:
                if not targets:
                    break
                swap_location_item(sl, targets.pop())  # stranded prog -> reachable slot; filler -> sl
                rescued += 1
                moved += 1
            if moved == 0:
                raise FillError(f"[greenfield] {len(stranded)} own progression item(s) unreachable; rescue "
                                f"made no progress; regenerate. First: {_detail(stranded)}")
        else:  # loop exhausted without converging
            state = CollectionState(mw)
            state.sweep_for_advancements()
            remaining = _stranded(state, my_locs)
            if remaining:
                raise FillError(f"[greenfield] {len(remaining)} own progression item(s) unrescuable after "
                                f"max iterations; regenerate. First: {_detail(remaining)}")
        world.gf_prog_surface_rescued = rescued
    except FillError:
        raise
    except Exception as e:  # audit malfunction must never fail an otherwise-good gen
        import logging
        logging.getLogger("Greenfield").warning(
            "progression_surface.audit_reachable skipped (internal error: %r)", e)


@register
class ProgressionSurfaceFeature(Feature):
    name = "progression_surface"
    OPTIONS = {"progression_surface": ProgressionSurface,
               "progression_surface_mode": ProgressionSurfaceMode,
               "confine_foreign_progression": ConfineForeignProgression}
    # Placement runs centrally from core.pre_fill via apply() (locations exist + get_all_state valid).
    # The foreign-progression bar is set in core._add_locations (item_rule), using confined_surface_ids.

    def slot_data(self, world):
        """Ship the surface to the CLIENT. This is the set the tracker stars.

        It REPLACES `bigTicketLocations`, which was a second list of "important checks" naming a set
        progression could never reach: big-ticket targeted {MajorBoss, Remembrance, GreatRune} while
        the surface is {Remembrance, Seedtree, Church, Boss, Fragment, Revered} -- intersection
        Remembrance alone. The client was starring MajorBoss/GreatRune checks that this module FORBIDS
        a region Lock from ever occupying. A tracker pointing at checks the locks cannot be on is worse
        than no tracker: it teaches the player something false.

        Emitting the surface itself makes that drift unrepresentable -- "where the locks may be" and
        "what the client stars" are now one expression, evaluated once.
        """
        if _mode(world) == 0:
            return {contract.PROGRESSION_SURFACE_LOCATIONS: []}
        classes = selected_surface(_selection(world))
        ids = allowed_ap_ids(LOCATION_TAGS, classes, defaulted=_world_barred_aps(world))
        own = {loc.address for loc in world.multiworld.get_locations(world.player)
               if getattr(loc, "address", None) is not None}
        return {contract.PROGRESSION_SURFACE_LOCATIONS: sorted(i for i in ids if i in own)}
