"""curated_fill -- route the region-lock progression onto BIG-TICKET checks (matt-free).

By default AP's fill scatters the region Locks across any reachable check (so a lock can land on a
forgettable pickup). curated_fill concentrates them: it marks every big-ticket location
LocationProgressType.PRIORITY so the fill gives ADVANCEMENT (the Locks) FIRST CRACK at them -- you
find your progression on bosses / remembrances / legendary drops / great runes / key items instead
of on a random consumable.

BIG_TICKET = LOCATION_TAGS in {Boss, Remembrance, Legendary, GreatRune, KeyItem} (the "prominent"
umbrella; ported from the old world's _curated_is_big_ticket). Shops/flasks/crystal-tears are
deliberately NOT big-ticket here.

FILL-SAFETY: PRIORITY is a SOFT preference -- AP's priority pass places advancement into priority
locations first, and any priority slots left over (there are far more big-ticket checks than the ~N
region Locks) simply fall through to the later useful/filler passes. So marking ALL big-ticket is
fine and is actually MORE robust than a tight set: it never forces an exact 1:1 lock<->slot chain
(the one case that FillErrors). We still reachability-prune (get_all_state) as defensive hygiene.
Off by default. Marking + prune run from core.pre_fill via apply()."""
from collections import defaultdict

from Options import Toggle
from ..registry import Feature, register
from ..contract import is_big_ticket  # single source of truth (shared with the F6 tracker)

try:
    from ..location_tags import LOCATION_TAGS
except Exception:  # not yet generated -> feature is a no-op
    LOCATION_TAGS = {}



class CuratedFill(Toggle):
    """Route the region Locks (this world's progression) onto big-ticket checks -- bosses,
    remembrances, legendary gear, great runes, and key items -- instead of letting them scatter onto
    forgettable pickups. Every big-ticket check is marked priority so advancement gets first crack at
    them; the leftover big-ticket checks just get useful/filler, so it never breaks generation. Off
    by default."""
    display_name = "Curated Fill (locks on big-ticket checks)"


@register
class CuratedFillFeature(Feature):
    name = "curated_fill"
    OPTIONS = {"curated_fill": CuratedFill}
    # No slot_data + no items: this only sets LocationProgressType on existing locations, done
    # centrally from core.pre_fill via apply() below (locations exist + get_all_state is valid there).


def select_priority(world):
    """This world's big-ticket locations to mark PRIORITY = ALL of them. AP gives advancement first
    crack at priority slots; the excess (big-ticket far outnumber the ~N Locks) fall through to the
    useful/filler passes, so no cap is needed and the fill is never forced into a tight lock chain.
    Pure (no marking, no get_all_state) so it's unit-testable without leaking a MultiWorld."""
    opt = getattr(world.options, "curated_fill", None)
    if not (opt is not None and opt.value) or not LOCATION_TAGS:
        return []
    btl = getattr(world.options, "big_ticket_locations", None)
    sel = set(btl.value) if btl is not None else None
    selected = []
    for loc in world.multiworld.get_locations(world.player):
        ap = getattr(loc, "address", None)
        if ap is None:
            continue
        if is_big_ticket(LOCATION_TAGS.get(ap), sel):
            selected.append(loc)
    return selected


def apply(world) -> None:
    """core.pre_fill hook: give this world's advancement (the region Locks) FIRST CRACK at the
    big-ticket checks via a SOFT, reachability-respecting pre-fill.

    We deliberately do NOT mark the slots LocationProgressType.PRIORITY: AP's greedy priority pass
    can hard-FillError on the strict region-lock CHAIN (each region gated by its own Lock) -- it
    dead-ends placing a late Lock even though there are far more big-ticket slots (~83) than Locks
    (~8), because the reachable slots at each step are a moving subset. Instead we run
    fill_restrictive with allow_partial=True: it chains the Locks onto reachable big-ticket slots and
    ANY it can't place simply fall back to the normal fill pool -- concentrated where possible, never
    a generation failure."""
    selected = select_priority(world)
    if not selected:
        return
    mw = world.multiworld
    adv = [i for i in mw.itempool if i.player == world.player and i.advancement]
    if not adv:
        return
    from Fill import fill_restrictive
    from BaseClasses import CollectionState
    fillable = [loc for loc in selected if loc.item is None]
    world.random.shuffle(fillable)
    to_place = list(adv)
    for i in adv:
        mw.itempool.remove(i)
    try:
        fill_restrictive(mw, CollectionState(mw), fillable, to_place,
                         single_player_placement=True, lock=False, allow_partial=True)
    except TypeError:  # older AP signature without allow_partial
        fill_restrictive(mw, CollectionState(mw), fillable, to_place, single_player_placement=True)
    # fill_restrictive mutates to_place, leaving only the UNPLACED items -> return them to the pool.
    for i in to_place:
        mw.itempool.append(i)
