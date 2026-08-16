"""THE FINALE -- the Ashen Capital / Elden Throne, entered by ITEM (SPEC-ashen-capital-lock).

Godfrey (Hoarah Loux, f510070), the Elden Beast (f510230), Sir Gideon Ofnir (f510060) and the seven
m11_05 map lots (incl. [Incantation] Erdtree Heal f11057000 and Erdtree's Favor +2 f11057100) used
to be excluded as "ashen_capital_dead: post-Erdtree-burn content, unreachable". That was a
conditional truth wearing a blanket exclusion (ruling 2026-07-14): the Ashen Capital is reachable
exactly when the player can burn the Erdtree, and the burn's trigger is game data --
common.emevd $Event(900) waits solely on flag 9116 (Maliketh dead, set only by m13_00 = Crumbling
Farum Azula), then warps into m11_05; m19_00 (Elden Throne) is entered only through m11_05's burnt
Erdtree. gen_data._finale_derive re-derives all of it from the artifacts on every regen.

⭐ 2026-08-06, SPEC-ashen-capital-lock. The paragraph above is history: the burn is no longer
game data we wait on, it is an ITEM we mint. Pure-runtime means flag 9116 (and, as the probe
found, flag 300 -- without which the Elden Beast's arena is a VOID) are ours to write, so the
Erdtree burn became one synthetic progression item, `Ashen Capital Lock`. That single change
retires the whole conditional apparatus:

  * the finale EXISTS on every seed with the BASE GAME in play -- no force-kept regions, no
    `num_regions: 1` quietly producing four. `data.FINALE_REQUIRES` is now `()` and stays that
    way; `finale_active` asks about the base game, not about a prerequisite set.
  * the region hangs off the HUB (`data.FINALE_HOST_REGION` = Roundtable Hold) behind
    `has("Ashen Capital Lock")`. You reach the Ashen Capital by warping to its OWN graces, never
    through the capital's rune gate -- so Leyndell is not on the way and is not required.
  * the Ashen Capital is still NEVER ROLLABLE: not in REGIONS, never drawn by `num_regions`,
    never counted in the kept set, never the precollected start anchor. It is ten checks and a
    gauntlet, not a place you play (Alaric, 2026-08-06). `describe_kept` is untouched.
  * it now owns its geometry outright -- play_regions 11050 + 19000 and grace bundle
    71122-71125 moved out of Leyndell in region_groups.py -- so the client's kick enforces the
    Ashen lock in its own right. `core._lockless_host` is gone with that change.

NATURAL PROGRESSION is the one mode that keeps the old shape, because it mints no Lock items at
all and so has no item to arm the burn with. There the VANILLA chain is the only burn there is,
and the finale exists iff the burn region (Maliketh) and the map owner are both kept, entered on
those two region events. `finale_requirement_locks` is the single place that difference lives.

Historic per-seed rule (this feature), kept because the tests still name it:
  * count-neutrality: core counts this feature's locations via world.gf_extra_locations and this
    feature contributes exactly one pool item per location (the vanilla ware under item_shuffle,
    filler otherwise) -- items == locations holds by construction.
  * detection: core merges world.gf_extra_location_flags into slot_data locationFlags, so the
    client's flag poll sees the finale flags; all ten are ItemLotParam-awarded (check_lots_table
    map/items), so award + suppression ride the existing static machinery.
  * the goal: when the finale exists it IS the goal (features/goal_locations.py tier 0), and
    since 2026-08-06 `goal: auto` resolves to the Elden Beast on every base-game seed. The finale
    is a fixed gauntlet -- Gideon into Godfrey/Hoarah Loux into Radagon/Elden Beast -- and that
    shape plays well as a capstone under rando no matter what the draw kept (Alaric, decision 3).

Telemetry (CONTRIBUTING: a feature is armed, or it says why not): logs armed-with-N or
inert-because-X once per generation.
"""
import logging

from BaseClasses import Region, Location

from ..registry import Feature, register
from . import vanilla_placement as _vp
from ..data import LOCATIONS, FINALE_REGION, FINALE_REQUIRES, FINALE_HOST_REGION
from . import natural_progression as _np

try:
    from ..data import FINALE_BURN_REGION, FINALE_KICK_OWNER
except Exception:  # pre-regen data.py
    FINALE_BURN_REGION, FINALE_KICK_OWNER = "Farum Azula", "Leyndell"
try:
    from ..region_spine import DLC_REGIONS
except Exception:  # pragma: no cover
    DLC_REGIONS = frozenset()

# THE synthetic item. Named off the region so `core.lock_region_name` and every "<R> Lock"
# convention in the codebase keep working on it unchanged.
ASHEN_LOCK_ITEM = f"{FINALE_REGION} Lock"

try:
    from ..item_ids import LOCATION_ITEM
except Exception:  # not yet generated
    LOCATION_ITEM = {}

_GAME = "Elden Ring"


class FinaleLocation(Location):
    game = _GAME


def base_game_in_play(regions) -> bool:
    """Is any BASE-game region in play? `dlc_only` seals the base game, and the Ashen Capital is
    base-game content, so that is the whole existence question now.

    ⚠️ This is deliberately NOT `not dlc_only`: it reads the resolved region pool rather than the
    yaml, so a future scope option that empties the base game gets the right answer without
    anyone remembering to teach this predicate about it."""
    return bool(set(regions) - set(DLC_REGIONS))


def finale_requirement_locks(world) -> tuple:
    """The item names the finale's entrance requires -- THE single place the natural_progression
    difference lives.

    Everywhere else: the one synthetic `Ashen Capital Lock`, which IS the burn.
    Under natural_progression: no Lock items are minted at all, so there is nothing to arm the
    burn with and the VANILLA chain stands -- you need the region that kills Maliketh and the
    region that owns the map. core.set_rules places a `<Region> Lock` EVENT inside each kept
    region under that mode, so `has_all` over those two names is satisfiable there and means
    exactly "both regions are reachable"."""
    if _np.is_on(world) or _vp.is_on(world):
        return (f"{FINALE_BURN_REGION} Lock", f"{FINALE_KICK_OWNER} Lock")
    # ⭐ THE ASHEN LOCK IS NO LONGER AN ITEM (#768). It used to be minted into the pool and this
    # returned it, so the finale's entrance read `has("Ashen Capital Lock")` and fill could place
    # that Lock in sphere 1 -- a player could stand in the endgame region before doing anything,
    # and #694's "the ending plays and the run does not end" followed from exactly that.
    #
    # It is withheld now and GRANTED BY THE CLIENT once every other goal item is held
    # (client#245, `er_logic::goal_gate`). So the entrance requirement becomes what the client
    # waits for, stated in AP logic: every kept region's Lock, plus any required Great Runes.
    # The two halves must agree or fill and the client would disagree about when the arena opens.
    #
    # 🛑 THE GOAL REGION'S OWN LOCK IS EXCLUDED, and that is not a detail -- it is the thing being
    # granted, so requiring it would be requiring the output as an input, and neither AP's fill nor
    # the client could ever satisfy it. `kept_lock_names` still lists it for the client's
    # region_open_flags lookup; `goal_required_lock_names` is what must not.
    # 🛑 `kept_lock_names`, NOT `goal_required_lock_names`, AND THE DIFFERENCE IS AN ORDERING BUG
    # WAITING TO HAPPEN. This runs from `create_regions`, which AP calls BEFORE `create_items` --
    # and the start anchor is precollected inside `create_items`. So at the moment this rule is
    # built, `precollected_items` is still EMPTY and `goal_required_lock_names` (whose whole job is
    # "minus the precollected anchor") returns every kept lock anyway. Using it here captures a
    # list that then disagrees with the same call made later, which is exactly how the first draft
    # of this failed: "finale entrance shut while holding every other goal item".
    #
    # `kept_lock_names` is the honest list at this point and stays correct afterwards. Requiring
    # the anchor costs nothing -- AP's state holds precollected items from sphere 0 -- so the two
    # readings are satisfied identically in play.
    #
    # ⚠️ The WIRE still excludes it (`goal_required_lock_names` -> goalRequiredItems), because the
    # client waits on items it RECEIVES and the anchor is never sent. Same requirement, two honest
    # spellings of it, and that asymmetry is documented in goal_required_lock_names' own docstring.
    return tuple(world.kept_lock_names()) + tuple(world._required_runes())


def finale_active(regions, natural=False) -> bool:
    """THE per-seed existence rule, single-sourced here (coverage.py and the tests call this too).

    `regions` is the seed's ELIGIBLE region pool (or its kept set, for the static callers): the
    finale exists iff the base game is in play. Under `natural` it falls back to the pre-2026-08-06
    rule -- every FINALE_REQUIRES_NATURAL region kept -- because that mode has no lock to give.
    FINALE_REQUIRES itself is `()` now, and asserting over it would be VACUOUS, so it is not the
    thing consulted here; test_gf_ashen_capital_lock pins that emptiness directly instead."""
    if natural:
        return {FINALE_BURN_REGION, FINALE_KICK_OWNER} <= set(regions)
    return base_game_in_play(regions)


def finale_entries():
    return list(LOCATIONS.get(FINALE_REGION, ()))


@register
class Finale(Feature):
    name = "finale"

    def generate_early(self, world) -> None:
        # The scope is the ELIGIBLE pool, not the kept draw: the Ashen Capital is not rolled, so
        # "is it in this seed" cannot depend on which regions the draw happened to take. Reading
        # _kept() here would make a base-game seed whose draw took only DLC regions build no
        # finale while core still minted its lock -- two answers to one question.
        # vanilla_placement takes the SAME branch as natural_progression here, for the same reason
        # and with the opposite history: that mode has no lock to give, this mode refuses to mint
        # one. Either way the VANILLA chain stands -- kill Maliketh in Farum Azula, own the capital
        # -- which is precisely how the base game reaches the Ashen Capital.
        #
        # 🛑 DISABLING THE FINALE HERE WAS A REAL BUG, caught by a Generate smoke run rather than by
        # the suite: with the Ashen Capital gone, `goal: auto` derived the DLC finale instead and a
        # base+DLC vanilla seed ended at Enir Ilim. A vanilla run ends at the Elden Beast.
        _natural = _np.is_on(world) or _vp.is_on(world)
        scope = list(getattr(world, "gf_eligible", None) or world._kept())
        entries = finale_entries()
        world.gf_finale_active = bool(entries) and finale_active(
            list(world._kept()) if _natural else scope, natural=_natural)
        if world.gf_finale_active:
            # core reads these two attributes (documented seams in core.create_items /
            # core._base_slot_data): the location count keeps the pool count-exact, the flag map
            # keeps the client's flag poll complete.
            world.gf_extra_locations = list(getattr(world, "gf_extra_locations", ())) + entries
            flags = dict(getattr(world, "gf_extra_location_flags", {}))
            flags.update({ap_id: int(flag) for (_n, ap_id, flag) in entries})
            world.gf_extra_location_flags = flags
            logging.getLogger("Greenfield").info(
                "[eldenring:%s] finale ARMED with %d checks behind %s -- goal = %s",
                world.player, len(entries),
                " + ".join(finale_requirement_locks(world)), FINALE_REGION)
        else:
            why = ("natural_progression: %s not both kept"
                   % " / ".join(sorted({FINALE_BURN_REGION, FINALE_KICK_OWNER}))) if _natural \
                else "no base-game region is in play (dlc_only)"
            logging.getLogger("Greenfield").info(
                "[eldenring:%s] finale INERT: %s -- goal falls back to the terminal-region rule",
                world.player, why)

    def create_regions(self, world) -> None:
        if not getattr(world, "gf_finale_active", False):
            return
        region = Region(FINALE_REGION, world.player, world.multiworld)
        world.multiworld.regions.append(region)
        # 🛑 THE FOREIGN BAR HAS TO BE APPLIED HERE TOO. These locations are built directly rather
        # than through core._add_locations, which is where confine_foreign_progression installs its
        # item_rule -- so until 2026-07-28 the finale's 10 checks were the ONE hole in that
        # confinement, and another world's advancement could land on them. Invisible in a solo seed
        # (the option is a no-op there) and invisible at the shipped num_regions default (the finale
        # is INERT unless every FINALE_REQUIRES region is kept), which is why it survived: the first
        # multiworld CI run found it immediately, under natural_progression, 7 leaked placements
        # across two slots.
        _fsurf = getattr(world, "_foreign_confine_surface", None)
        _fbf = getattr(world, "_foreign_barred_fn", None)
        for (name, ap_id, _flag) in finale_entries():
            loc = FinaleLocation(world.player, name, ap_id, region)
            if _fsurf is not None and _fbf is not None and ap_id not in _fsurf:
                _prev = loc.item_rule
                loc.item_rule = lambda item, _p=_prev, _pl=world.player, _f=_fbf: (
                    not _f(item, _pl)) and _p(item)
            region.locations.append(loc)
        host = world.multiworld.get_region(FINALE_HOST_REGION, world.player)
        # ENTRANCE: the HUB, gated on the burn item. You do not walk to the Ashen Capital -- you
        # warp to its own graces, which the lock lights -- so the host is the Roundtable and the
        # rule is the single synthetic item. Under natural_progression this is the two vanilla
        # region events instead (see finale_requirement_locks): that mode mints no locks, and a
        # rule nobody can satisfy would silently make ten checks unfillable rather than loudly
        # unreachable.
        locks = finale_requirement_locks(world)
        host.connect(region, f"To {FINALE_REGION}",
                     rule=lambda state, lk=tuple(locks): state.has_all(lk, world.player))

    def create_items(self, world):
        if not getattr(world, "gf_finale_active", False):
            return []
        out = []
        excl = getattr(world, "gf_dlc_excluded", ())
        for (_name, ap_id, _flag) in finale_entries():
            nm = LOCATION_ITEM.get(ap_id) if world._shuffle_on() else None
            if nm and excl and nm in excl:
                nm = None
            if nm and nm in world.item_name_to_id:
                out.append(world.create_item(nm))
            else:
                out.append(world.create_item(world.get_filler_item_name()))
        return out
