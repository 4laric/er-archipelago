"""minibaker -- runtime shop injection so Stonesword Keys are infinitely buyable (matt-free).

The "mini-baker" does at runtime what the retired offline baker did to regulation.bin: the shared
client (minibaker.rs) repurposes one reserved ShopLineupParam row into an always-in-stock, unlimited
Stonesword Key vendor at the Twin Maiden Husks. With keys always purchasable, imp-statue (fog-seal)
checks can never be permanently locked, so the whole "missable behind a stonesword key" class is
dissolved -- no datamine, no missable tagging needed for them.

Greenfield just RESERVES the row and emits its id; the client does the live param write. gen_data
excludes the reserved row's flag (60290 / row 101801, the Twin Maidens' Blue Cipher Ring slot) from
shop checks so the repurpose never clobbers a tracked check. Emitting 0 (feature off) leaves the slot
vanilla. On by default. No effect on any non-greenfield seed (the client only acts when this key is set).
"""
from Options import DefaultOnToggle
from ..registry import Feature, register
from .. import contract

# ShopLineupParam row the client repurposes (Twin Maiden Husks Blue Cipher Ring slot, in-game verified
# 2026-07-06). equipType is already 3 (goods) so the client only rewrites equipId/value/stock/qty.
STONESWORD_VENDOR_ROW = 101801


class BuyableStoneswordKeys(DefaultOnToggle):
    """Sell Stonesword Keys at the Twin Maiden Husks with unlimited stock (mini-baker). Keeps imp-statue
    checks from ever being permanently missable. On by default; the client repurposes one reserved shop
    slot at runtime, so turning it off simply leaves that slot vanilla."""
    display_name = "Buyable Stonesword Keys"


@register
class MiniBakerFeature(Feature):
    name = "minibaker"
    OPTIONS = {"buyable_stonesword_keys": BuyableStoneswordKeys}

    def slot_data(self, world):
        on = bool(world.options.buyable_stonesword_keys.value)
        return {contract.STONESWORD_VENDOR_ROW: STONESWORD_VENDOR_ROW if on else 0}
