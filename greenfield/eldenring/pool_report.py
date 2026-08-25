"""pool_report -- "how much of my game am I putting into everyone else's?", answered with numbers.

THE QUESTION, VERBATIM (LordChungle, Nexus, 2026-08-08):

    "If I am playing with 5 other people who have 200 checks each, then 2/3 of the checks that get
     picked up go to me and 2/3 of the checks sent to others are from me, making the multiworld
     randomizer overly centralized on only my game. [...] I am wondering around how many of the
     checks are filler checks. If 40 checks are considered progression checks then are the rest
     filler?"

He is right to ask and he could not have found out. The seed-size tab tells him how many checks he
has, `wizard/pool-composition.json` tells him roughly what share of them is filler, and NOTHING
anywhere told him how many ITEMS that turns into in someone else's world -- which is the number that
decides whether a six-player game is about Elden Ring or about five people opening Elden Ring boxes.
The two facts he needs are not derivable from each other: locality options move the second without
touching the first.

WHAT IS COUNTED, AND WHY THERE ARE TWO NUMBERS

  * BEFORE the fill (`estimate`) -- how many of this world's items are ALLOWED to leave. That is
    exactly `pool - local_items`, it is a property of the options alone, and it is the number the
    yaml wizard can show a player who has not generated anything yet.
  * AFTER the fill (`measured`) -- how many of this world's items ACTUALLY landed in another
    player's world. This is smaller, always, and by a factor nobody can predict from the options:
    AP's fill spreads a world's items over every world in proportion to open locations, so with five
    other players of 200 checks each, a 1,266-check Elden Ring slot keeps most of its own pool
    simply because most of the open locations are its own.

🛑 REPORTING ONLY THE ESTIMATE WOULD ANSWER A QUESTION NOBODY ASKED. "4,900 items may travel" is
true and reads like a threat; "you sent 431 items out, 388 of them filler" is the same seed. The
estimate is a CEILING, and it is labelled as one everywhere it is printed.

🛑 AND THE MEASURED NUMBER IS ONLY AVAILABLE ONCE, in post_fill/write_spoiler. There is no hook that
sees a completed fill and a live options object except those, which is why this is a plain module
called from core rather than a registry Feature (registry hooks stop at slot_data). coverage.py has
the same shape for the same reason.

Progression is not in either number by construction -- `progression_surface_mode` defaults to
`strict` and pre-places every Lock on our own surface, so zero progression items reach the AP pool.
The count still classifies what it finds instead of assuming that, because the assumption is an
option away from being false and a report that quietly stops being true is worse than no report.

Matt-free: reads the multiworld's own item pool and the AP `local_items` set. No curated data.
"""
from typing import Any, Dict

from BaseClasses import ItemClassification

_LOG = "Elden Ring"


def _classify(item) -> str:
    """filler / useful / progression, from AP's own classification. `trap` counts as filler -- from
    the receiving player's side that is what it is: not a thing they needed."""
    cls = getattr(item, "classification", None)
    if cls is None:
        return "filler"
    if cls & ItemClassification.progression:
        return "progression"
    if cls & ItemClassification.useful:
        return "useful"
    return "filler"


def estimate(world) -> Dict[str, Any]:
    """The CEILING, from the options alone: how many of this world's items are permitted to travel.

    Counts COPIES, not distinct names. `local_items` is name-keyed, so a name held back holds back
    every copy of itself -- and copies are what a player feels, since the pool has hundreds of
    Smithing Stones and one Blasphemous Blade.
    """
    pool = [it for it in world.multiworld.itempool if it.player == world.player]
    try:
        local = set(world.options.local_items.value)
    except Exception:
        local = set()
    out = {"pool": len(pool), "free": 0, "held": 0,
           "free_filler": 0, "free_useful": 0, "free_progression": 0}
    for it in pool:
        if it.name in local:
            out["held"] += 1
            continue
        out["free"] += 1
        out["free_" + _classify(it)] += 1
    return out


def _tally(rows, me, local) -> Dict[str, Any]:
    """PURE tally over ONE universe (placed locations), so numerator and denominator can never
    disagree. `rows` = iterable of (item_owner, location_owner, is_event, item_name, class).

    🛑 THE UNIVERSE MUST BE THE SAME FOR BOTH HALVES (the #995 bug). Reading `sent` from placed
    locations and the ceiling from `multiworld.itempool` counts two different sets -- itempool
    EXCLUDES event items (region locks, goal, sweep grants: created straight onto event locations),
    so the ratio can exceed 100%. Here everything comes from the same walk:
      * `is_event` (an event location, `loc.address is None`) items are LOCKED home -- never
        travel-eligible, so they are kept out of `travelable`;
      * `held` = travel-eligible items your `local_items` pins home;
      * `free = travelable - held`, and `sent` (your items at a FOREIGN location) is a subset of it
        by construction (an event can't be foreign, a held item stays home) -- so `sent <= free`
        ALWAYS, and the percentage is bounded at 100%.

    `location.item.player` is the OWNER; `location.player` is where it SITS.
    """
    sent = received = home = travelable = held = 0
    by_class = {"filler": 0, "useful": 0, "progression": 0}
    for owner, sits_in, is_event, name, cls in rows:
        if owner == me:
            if not is_event:
                travelable += 1
                if name in local:
                    held += 1
            if sits_in != me:
                sent += 1
                by_class[cls] += 1
            else:
                home += 1
        elif sits_in == me:
            received += 1
    return {"sent": sent, "received": received, "home": home,
            "pool": travelable, "held": held, "free": travelable - held,
            "sent_filler": by_class["filler"], "sent_useful": by_class["useful"],
            "sent_progression": by_class["progression"]}


def measured(world) -> Dict[str, Any]:
    """The TRUTH, after the fill, measured from the placed locations alone (see [`_tally`])."""
    try:
        local = set(world.options.local_items.value)
    except Exception:
        local = set()
    me = world.player

    def _rows():
        for loc in world.multiworld.get_locations():
            it = loc.item
            if it is None:
                continue
            yield (it.player, loc.player, loc.address is None,
                   getattr(it, "name", ""), _classify(it))

    return _tally(_rows(), me, local)


def summary(world) -> Dict[str, Any]:
    """Both halves plus the player count, in one dict. Solo seeds are reported as solo rather than
    as "0 sent": a lone player has nowhere to send anything, and a bare 0 reads like a setting has
    gone wrong."""
    out = {"players": world.multiworld.players}
    out.update(estimate(world))
    if world.multiworld.players > 1:
        out.update(measured(world))
    return out


def _line(world, s: Dict[str, Any]) -> str:
    name = world.multiworld.get_player_name(world.player)
    if s["players"] <= 1:
        return (f"Elden Ring ({name}) multiworld contribution: solo seed -- nothing travels. "
                f"{s['pool']} items in the pool.")
    # DENOMINATOR IS `free`, NOT `pool` (#995): `sent` and `free` are both measured from the same
    # post-fill walk (events excluded), so `sent <= free` and the percentage cannot exceed 100%.
    pct = (100.0 * s["sent"] / s["free"]) if s["free"] else 0.0
    return (f"Elden Ring ({name}) multiworld contribution: sent {s['sent']} of {s['free']} "
            f"free-to-travel items into other worlds ({pct:.1f}%) -- {s['sent_filler']} filler, "
            f"{s['sent_useful']} useful, {s['sent_progression']} progression; received "
            f"{s['received']}. {s['held']} of your {s['pool']} items were held local by your "
            f"options.")


def log(world) -> None:
    """One INFO line per slot at post_fill. Wrapped: a report may not be the thing that kills a
    generation, and every number here is derived from state other code already validated."""
    import logging
    try:
        logging.getLogger(_LOG).info(_line(world, summary(world)))
    except Exception as e:      # pragma: no cover -- diagnostics never fail a seed
        logging.getLogger(_LOG).debug("pool_report failed: %r", e)


def write_spoiler(world, handle) -> None:
    """The same figures in the spoiler, where a host can see them per slot without a live log."""
    try:
        s = summary(world)
    except Exception as e:      # pragma: no cover
        handle.write(f"\n  (pool report failed: {e!r})\n")
        return
    handle.write("\n" + _line(world, s) + "\n")
    if s["players"] > 1:
        handle.write("  Held local by your options: keep_local / keep_local_rune_cap / "
                     "local_item_only / filler_foreign_pct, plus any local_items you listed.\n")
