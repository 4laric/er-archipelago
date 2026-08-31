"""Reviewed direct quest-prerequisite placement exclusions (#832).

The generated questline model is evidence, not executable logic.  This small table records only
human-reviewed edges where a same-player filler quest item placed on its own dependent check would
self-lock the pickup.  Each dependent location rejects that one prerequisite and keeps every other
rule it already had; the item remains ordinary filler everywhere else.
"""

from ..data import LOCATIONS
from ..registry import Feature, register


# (source flag, dependent flag, item name).  Flags keep this table directly comparable with the
# typed `flag:<id> -> flag:<id>` evidence table; AP ids are derived below.
REVIEWED_PREREQUISITES = (
    (400392, 510110, "Cursemark of Death"),
    (400031, 400033, "Lord of Blood's Favor"),
    (400310, 400320, "Unalloyed Gold Needle"),
    (400321, 400324, "Unalloyed Gold Needle"),
    (1039547300, 400323, "Valkyrie's Prosthesis"),
    (12027080, 400391, "Fingerslayer Blade"),
    (12027080, 400394, "Fingerslayer Blade"),
    (114, 400393, "Dark Moon Ring"),
)

# (goods row, dependent flag, item name).  These are stronger than the flag-to-flag edges above:
# the path-sensitive ESD slice reaches the inventory test/consumption itself.  Keep them separate so
# the evidence test cannot accidentally pretend that an item-possession root was a source-check flag.
REVIEWED_ITEM_PREREQUISITES = (
    (8975, 400311, "Unalloyed Gold Needle"),
    # Fia's ESD consumes the Cursemark and sets 12039161. Her common-event state manager then
    # advances 4129 -> 4130; Fortissax's defeat advances 4130 -> 4131, and m12_03 awards lot 103350
    # (f9502) only at state 4131. Placing the Cursemark on that Mending Rune check is therefore a
    # direct self-lock, not a cone-level guess (#1085).
    (8191, 9502, "Cursemark of Death"),
)


_AP_IDS_BY_FLAG = {}
for _rows in LOCATIONS.values():
    for _name, _ap_id, _flag in _rows:
        _AP_IDS_BY_FLAG.setdefault(int(_flag), set()).add(int(_ap_id))


@register
class QuestPrerequisiteRules(Feature):
    name = "quest_prerequisite_rules"

    def set_rules(self, world) -> None:
        barred_by_ap = {}
        for _source_flag, target_flag, item_name in REVIEWED_PREREQUISITES:
            for ap_id in _AP_IDS_BY_FLAG.get(target_flag, ()):
                barred_by_ap.setdefault(ap_id, set()).add(item_name)
        for _goods_row, target_flag, item_name in REVIEWED_ITEM_PREREQUISITES:
            for ap_id in _AP_IDS_BY_FLAG.get(target_flag, ()):
                barred_by_ap.setdefault(ap_id, set()).add(item_name)

        for loc in world.multiworld.get_locations(world.player):
            barred = barred_by_ap.get(getattr(loc, "address", None))
            if not barred:
                continue
            previous = loc.item_rule
            loc.item_rule = lambda item, prev=previous, names=frozenset(barred), pl=world.player: (
                prev(item) and not (item.player == pl and item.name in names)
            )
