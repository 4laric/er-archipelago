"""THE FINALE -- the Ashen Capital / Elden Throne as a CONDITIONAL, never-rollable region.

Godfrey (Hoarah Loux, f510070), the Elden Beast (f510230), Sir Gideon Ofnir (f510060) and the seven
m11_05 map lots (incl. [Incantation] Erdtree Heal f11057000 and Erdtree's Favor +2 f11057100) used
to be excluded as "ashen_capital_dead: post-Erdtree-burn content, unreachable". That was a
conditional truth wearing a blanket exclusion (ruling 2026-07-14): the Ashen Capital is reachable
exactly when the player can burn the Erdtree, and the burn's trigger is game data --
common.emevd $Event(900) waits solely on flag 9116 (Maliketh dead, set only by m13_00 = Crumbling
Farum Azula), then warps into m11_05; m19_00 (Elden Throne) is entered only through m11_05's burnt
Erdtree. gen_data._finale_derive re-derives all of it from the artifacts on every regen.

Per-seed rule (this feature):
  * the finale locations EXIST iff every FINALE_REQUIRES region ('Farum Azula', 'Leyndell') is
    kept this seed. Leyndell owns the finale maps' measured kick geometry (play_regions 11050 +
    19000, region_groups.py), so the client's kick enforces the region through Leyndell's lock;
    Farum Azula is where the burn trigger (Maliketh) lives.
  * the region hangs off FINALE_HOST_REGION (Leyndell) with an entrance requiring EVERY
    FINALE_REQUIRES Lock, so fill can never strand progression behind an unburnable Erdtree.
  * count-neutrality: core counts this feature's locations via world.gf_extra_locations and this
    feature contributes exactly one pool item per location (the vanilla ware under item_shuffle,
    filler otherwise) -- items == locations holds by construction.
  * detection: core merges world.gf_extra_location_flags into slot_data locationFlags, so the
    client's flag poll sees the finale flags; all ten are ItemLotParam-awarded (check_lots_table
    map/items), so award + suppression ride the existing static machinery.
  * the goal: when the finale exists it IS the goal (features/goal_locations.py tier 0) -- the
    Ashen Capital is the game's real terminus even though Farum Azula outranks Leyndell in SPINE.

Telemetry (CONTRIBUTING: a feature is armed, or it says why not): logs armed-with-N or
inert-because-X once per generation.
"""
import logging

from BaseClasses import Region, Location

from ..registry import Feature, register
from ..data import LOCATIONS, FINALE_REGION, FINALE_REQUIRES, FINALE_HOST_REGION

try:
    from ..item_ids import LOCATION_ITEM
except Exception:  # not yet generated
    LOCATION_ITEM = {}

_GAME = "Elden Ring"


class FinaleLocation(Location):
    game = _GAME


def finale_active(kept) -> bool:
    """THE per-seed existence rule, single-sourced here (coverage.py and the tests call this too):
    the finale exists iff every prerequisite region is kept."""
    return set(FINALE_REQUIRES) <= set(kept)


def finale_entries():
    return list(LOCATIONS.get(FINALE_REGION, ()))


@register
class Finale(Feature):
    name = "finale"

    def generate_early(self, world) -> None:
        kept = list(world._kept())
        entries = finale_entries()
        world.gf_finale_active = bool(entries) and finale_active(kept)
        if world.gf_finale_active:
            # core reads these two attributes (documented seams in core.create_items /
            # core._base_slot_data): the location count keeps the pool count-exact, the flag map
            # keeps the client's flag poll complete.
            world.gf_extra_locations = list(getattr(world, "gf_extra_locations", ())) + entries
            flags = dict(getattr(world, "gf_extra_location_flags", {}))
            flags.update({ap_id: int(flag) for (_n, ap_id, flag) in entries})
            world.gf_extra_location_flags = flags
            logging.getLogger("Greenfield").info(
                "[eldenring:%s] finale ARMED with %d checks (%s kept) -- goal = %s",
                world.player, len(entries), "+".join(FINALE_REQUIRES), FINALE_REGION)
        else:
            missing = sorted(set(FINALE_REQUIRES) - set(kept))
            logging.getLogger("Greenfield").info(
                "[eldenring:%s] finale INERT: prerequisite region(s) %s not kept -- goal falls "
                "back to the terminal-region rule", world.player, missing or "<no data>")

    def create_regions(self, world) -> None:
        if not getattr(world, "gf_finale_active", False):
            return
        region = Region(FINALE_REGION, world.player, world.multiworld)
        world.multiworld.regions.append(region)
        for (name, ap_id, _flag) in finale_entries():
            region.locations.append(FinaleLocation(world.player, name, ap_id, region))
        host = world.multiworld.get_region(FINALE_HOST_REGION, world.player)
        # Entrance rule: EVERY prerequisite Lock (the host's own Lock is re-required for
        # robustness; its entrance already enforces it). This is what makes fill unable to strand
        # progression behind an unburnable Erdtree: reaching the finale in logic == holding the
        # locks of the regions the burn chain physically needs.
        locks = [f"{r} Lock" for r in FINALE_REQUIRES]
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
