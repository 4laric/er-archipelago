"""Per-check quest gates proven by event/talk data, narrower than whole vanilla questlines.

The Discarded Palace Key is awarded by common event 3050 only after the Baleful Shadow death flag
f12019280. In v1.17 m12_01 event 12010705, that shadow cannot appear until f12019257; the grace
talk ESD sets f12019257 only after the player owns Miniature Ranni (acquisition f400394) and repeats
the doll conversation three times. No Ranni mansion, Fingerslayer Blade, or other vanilla quest
flag is in the appearance predicate, so AP logic requires the randomized Miniature Ranni item and
ordinary Ainsel region access, but does not reproduce the bypassed vanilla chain.
"""
from ..registry import Feature, register

PALACE_KEY_AP_ID = 7773712
MINIATURE_RANNI = "Miniature Ranni"


def _active(world) -> bool:
    shuffle = getattr(world.options, "item_shuffle", None)
    return bool(shuffle and shuffle.value and "Ainsel River" in set(world._kept()))


@register
class QuestlineCheckGates(Feature):
    name = "questline_check_gates"

    def generate_early(self, world) -> None:
        world.gf_questline_gate_items = [MINIATURE_RANNI] if _active(world) else []

    def set_rules(self, world) -> None:
        if MINIATURE_RANNI not in getattr(world, "gf_questline_gate_items", ()):
            return
        try:
            location = world.multiworld.get_location(
                "Ainsel River :: Discarded Palace Key [f400159]", world.player)
        except KeyError:
            return
        previous = location.access_rule
        location.access_rule = (
            lambda state, p=previous, player=world.player:
            p(state) and state.has(MINIATURE_RANNI, player)
        )
        previous_item = location.item_rule
        location.item_rule = (
            lambda item, p=previous_item: p(item) and item.name != MINIATURE_RANNI
        )

