"""Greenfield matt-free Elden Ring apworld — MVP (Shattering).

Design (see ../LESSONS-LEARNED.md): rules are keyed by REGION only, never by matt location names.
Hub-and-spoke: Menu -> Roundtable Hold (free) -> each region, entrance gated by "<Region> Lock".
Goal: collect every region lock. Location source: data.py (generated matt-free, flag-keyed).

Client contract: fill_slot_data emits locationFlags {ap_id: [game event flag]} (the only location->
client coupling). Region-open flags for lock receipt are a TODO (reuse map_region_data open flags).
"""
from dataclasses import dataclass
from typing import Dict, Any, List

from BaseClasses import Region, Location, Item, ItemClassification
from worlds.AutoWorld import World, WebWorld
from Options import PerGameCommonOptions

from .data import HUB, REGIONS, LOCATIONS

GAME = "Elden Ring Matt-Free"
FILLER = "Rune"

# ---- id spaces (locks + filler for items; locations reuse backbone ap_ids) ----
_ITEM_BASE = 7770000
item_name_to_id: Dict[str, int] = {f"{r} Lock": _ITEM_BASE + i for i, r in enumerate(REGIONS)}
item_name_to_id[FILLER] = _ITEM_BASE + len(REGIONS)

location_name_to_id: Dict[str, int] = {
    name: ap_id for locs in LOCATIONS.values() for (name, ap_id, _flag) in locs
}

# ap_id -> game event flag, for the runtime client (locationFlags)
_LOCATION_FLAGS: Dict[str, List[int]] = {
    str(ap_id): [flag] for locs in LOCATIONS.values() for (_name, ap_id, flag) in locs
}


class MFItem(Item):
    game = GAME


class MFLocation(Location):
    game = GAME


@dataclass
class MFOptions(PerGameCommonOptions):
    pass


class MFWeb(WebWorld):
    theme = "stone"


class MattFreeEldenRingWorld(World):
    game = GAME
    web = MFWeb()
    options_dataclass = MFOptions
    options: MFOptions
    item_name_to_id = item_name_to_id
    location_name_to_id = location_name_to_id
    origin_region_name = "Menu"

    # ---- items ----
    def create_item(self, name: str) -> MFItem:
        cls = ItemClassification.progression if name.endswith(" Lock") else ItemClassification.filler
        return MFItem(name, cls, self.item_name_to_id[name], self.player)

    def get_filler_item_name(self) -> str:
        return FILLER

    def create_items(self) -> None:
        pool: List[MFItem] = [self.create_item(f"{r} Lock") for r in REGIONS]
        total_locations = sum(len(v) for v in LOCATIONS.values())
        pool += [self.create_item(FILLER) for _ in range(total_locations - len(pool))]
        self.multiworld.itempool += pool

    # ---- regions (hub-and-spoke) ----
    def _add_locations(self, region: Region, region_name: str) -> None:
        for (name, ap_id, _flag) in LOCATIONS.get(region_name, []):
            region.locations.append(MFLocation(self.player, name, ap_id, region))

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        hub = Region(HUB, self.player, self.multiworld)
        self.multiworld.regions += [menu, hub]
        menu.connect(hub)                    # Roundtable Hold is free
        self._add_locations(hub, HUB)
        for r in REGIONS:
            reg = Region(r, self.player, self.multiworld)
            self.multiworld.regions.append(reg)
            self._add_locations(reg, r)
            lock = f"{r} Lock"
            hub.connect(reg, f"To {r}", rule=lambda state, l=lock: state.has(l, self.player))

    # ---- goal: collect every region lock ----
    def set_rules(self) -> None:
        locks = [f"{r} Lock" for r in REGIONS]
        self.multiworld.completion_condition[self.player] = \
            lambda state: state.has_all(locks, self.player)

    # ---- client contract ----
    def fill_slot_data(self) -> Dict[str, Any]:
        return {
            "world_logic": "region_lock",
            "locationFlags": _LOCATION_FLAGS,
            # TODO: regionOpenFlags {"<Region> Lock": [open_flag]} so the client flips a region open
            # on lock receipt (reuse map_region_data reveal/open flags). apIdsToItemIds for received-
            # item grants is the next layer (locks grant = set region-open flag; filler = a game item).
        }
