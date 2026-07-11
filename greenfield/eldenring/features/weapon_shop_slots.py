"""weapon_shop_slots -- constrain WEAPON shop slots to own-world ER weapons (matt-free).

Parity port of the old apworld's WEAPON_SHOP_SLOT_GUARD (rules_mixin.py). WHY it exists:

The shared runtime client (shop_sell.rs) rewrites an own-world shop row's ShopLineupParam
equipId/equipType to its actual AP reward so the slot NATIVELY sells + displays the real item.
But SHOP_CTD_GUARD refuses to rewrite a WEAPON-category row whose reward is a NON-weapon -- that
combo crashed the purchase path (3x repro 2026-07-03). Guarded rows stay on the vanilla-sell path:
the row keeps selling the VANILLA good (the player receives it -- a leak) while the echo grant still
delivers the real reward separately. Net in-game: weapon shop slots preview vanilla AND hand over the
vanilla good (double-grant), even though the reward is randomized. (Alaric, greenfield 2026-07-06.)

The old apworld avoided this by forcing every weapon shop slot to hold an own-world ER weapon, so the
client only ever rewrites weapon->weapon (safe, native) -- correct preview, no vanilla leak, single
grant. Greenfield never ported that constraint; this feature restores it.

Matt-free: a slot is a WEAPON slot iff its vanilla preview FullID (shop_data.SHOP_PREVIEW_GOODS,
gen_data-derived) has the WEAPON category nibble (0x0); an item is an own-world weapon iff its
ITEM_CATALOG FullID (item_ids.py, gen_data-derived) has the WEAPON nibble. Purely fill-side: no
slot_data key, the client is unaffected.
"""
from ..registry import Feature, register

# ER FullID category nibble: WEAPON=0x0, PROTECTOR=0x1..., ACCESSORY=0x2..., GOODS=0x4..., GEM=0x8...
_NIBBLE_MASK = 0xF0000000
_WEAPON_NIBBLE = 0x00000000

try:
    from ..shop_data import SHOP_PREVIEW_GOODS  # {str(ap_id): vanilla FullID} (single-good rows)
except Exception:  # not yet generated
    SHOP_PREVIEW_GOODS = {}
try:
    from ..item_ids import ITEM_CATALOG  # {item_name: FullID}
except Exception:  # not yet generated
    ITEM_CATALOG = {}


def _is_weapon_full(full) -> bool:
    return full is not None and (full & _NIBBLE_MASK) == _WEAPON_NIBBLE


def _is_weapon_slot(address) -> bool:
    """A randomized shop slot whose VANILLA ware is a weapon (client would guard a non-weapon reward)."""
    return _is_weapon_full(SHOP_PREVIEW_GOODS.get(str(address)))


def _is_own_weapon(item, player) -> bool:
    """Own-world item that is an ER weapon (client-safe native weapon->weapon rewrite)."""
    if item.player != player:
        return False
    return _is_weapon_full(ITEM_CATALOG.get(item.name))


@register
class WeaponShopSlots(Feature):
    name = "weapon_shop_slots"

    def set_rules(self, world) -> None:
        if not SHOP_PREVIEW_GOODS or not ITEM_CATALOG:
            return
        slots = [loc for loc in world.multiworld.get_locations(world.player)
                 if getattr(loc, "address", None) is not None and _is_weapon_slot(loc.address)]
        if not slots:
            return
        # Fill-safety (mirrors important_locations): only enforce where the pool can supply enough
        # own-world weapons. A degenerate pool (e.g. item_shuffle off) has few/no weapons; enforcing
        # would over-constrain the fill and FillError/churn. Skip cleanly -- the guard is moot then,
        # and a vanilla-preview weapon slot is a cosmetic gap, not a crash.
        avail = sum(1 for i in world.multiworld.itempool if _is_own_weapon(i, world.player))
        if avail < len(slots):
            return
        for loc in slots:
            prev = loc.item_rule
            loc.item_rule = lambda item, p=prev, pl=world.player: p(item) and _is_own_weapon(item, pl)
