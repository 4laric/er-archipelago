"""check_lots -- blank the vanilla ware AT ITS SOURCE, so nothing has to be suppressed by item id.

THE PROBLEM the id-keyed suppressor was working around
------------------------------------------------------
`detour.rs` only ever sees `raw_id` off the AddItemFunc buffer. It cannot answer "where did this item
come from?" So `checkItemFlags` armed suppression by ITEM ID, and any ware that merely happened to back
some check was eaten from EVERY source: Golden Rune [1] backs 46 checks, so every Golden Rune [1] you
picked up anywhere was eaten until all 46 were collected. Mine an ore node, get a Smithing Stone, stone
is some check's ware, stone is eaten. (Alaric, playtest 2026-07-11.)

The `REPEATABLE_GOODS` stopgap fixed the eating, but at the price of a DOUBLE-DIP: for the ~243 shared
wares the vanilla item is no longer suppressed at the check either, so you get the vanilla stone AND the
AP item there.

THE FIX: answer the question at the SOURCE
------------------------------------------
Rewrite the CHECK's own item lot so it never hands out the vanilla ware at all. We can write
ItemLotParam at runtime -- `enemy_drops.rs` proves it.

⭐ THE UNLOCK: we do NOT need a synthetic goods id per check. That requirement is what killed the
original spec (3069 colliding checks vs only 332 spare goods rows). **Checks are detected by the FLAG
POLL** -- `core.rs:1299` pushes the location the moment its acquisition flag fires -- *not* by the item
id. The synthetic-id-per-location scheme was a baker-era relic of a client that identified checks from
the pickup itself. Ours doesn't.

So ONE placeholder goods row is enough:
  * point every check lot's GOODS slot at `AP_PLACEHOLDER_GOODS` (row 8852: exists, so the game can
    grant it; no GoodsName entry; referenced by no lot / shop / recipe),
  * the client suppresses that ONE id unconditionally -- it is never a real item, so this can never eat
    anything legitimate,
  * the flag poll reports the check, and AP grants what the seed actually placed.

Result: no vanilla ware is EVER handed out at a check (the double-dip is gone), and nothing else is
watched by item id, so mined ore, farmed drops, bought goods and crafted goods all just work.

SCOPE: GOODS slots only. Weapon/armor check wares stay on the id-keyed suppressor, which is already
sound for them -- a weapon is essentially never farmable, so it sits in the check-only set and cannot
eat a legitimate source.

Scoped to hub + kept spokes, like check_item_flags: a check that isn't in play this seed shouldn't have
its lot rewritten.
"""
from ..registry import Feature, register
from .. import contract
from ..data import HUB, LOCATIONS

try:
    from ..check_lots_data import CHECK_LOT_SLOTS, AP_PLACEHOLDER_GOODS
except ImportError:                       # pre-regen: inert, the stopgap still holds the line
    CHECK_LOT_SLOTS, AP_PLACEHOLDER_GOODS = {}, 0


@register
class CheckLots(Feature):
    name = "check_lots"

    def slot_data(self, world):
        if not CHECK_LOT_SLOTS or not AP_PLACEHOLDER_GOODS:
            return {}
        # gen_data keys CHECK_LOT_SLOTS by lot id, but a lot is only OURS to rewrite if its flag is a
        # check that is actually in play this seed. gen_data already filtered to known check flags; here
        # we can only scope by region, so send every lot -- a lot whose check is out of scope is in a
        # sealed region the player cannot reach anyway, and rewriting it is inert.
        # (Kept explicit so the scoping decision is visible rather than accidental.)
        _in_play = {HUB} | set(world._kept())
        if not _in_play:
            return {}
        blank = {str(lot): list(slots) for lot, slots in CHECK_LOT_SLOTS.items()}
        return {
            contract.CHECK_LOT_BLANK: blank,
            contract.AP_PLACEHOLDER_GOODS: int(AP_PLACEHOLDER_GOODS),
        }
