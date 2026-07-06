"""SPEC-PARITY Phase 7 -- starting items (COMPLETE).

Grants a starting Torch so dark caves/catacombs are navigable before you reach a grace (you can't
warp out until you light a grace). The Torch is WEAPON param id 24000000; its client FullID is
24000000 | 0x00000000 = 24000000 (WEAPON category nibble = 0, matching core's _AP_IDS_TO_ITEM_IDS
FullID convention). startItems is a list of FullIDs the client grants at game start. Matt-free
(single vanilla item id, no derivation).
"""
from Options import DefaultOnToggle
from ..registry import Feature, register

# ER Torch: WEAPON param id 24000000; FullID = id | WEAPON_NIBBLE(0x00000000) = 24000000.
_TORCH_FULL_ID = 24000000


class StartWithTorch(DefaultOnToggle):
    """Start with a Torch so dark caves and catacombs are navigable before you reach a grace.
    On by default; turn off for a stricter start."""
    display_name = "Start With Torch"


@register
class StartItems(Feature):
    name = "start_items"
    OPTIONS = {"start_with_torch": StartWithTorch}

    def slot_data(self, world):
        items = [_TORCH_FULL_ID] if world.options.start_with_torch.value else []
        return {"startItems": items}
