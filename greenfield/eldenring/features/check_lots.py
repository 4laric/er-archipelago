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
import logging

from ..registry import Feature, register
from .. import contract
from ..data import HUB, LOCATIONS

try:
    from ..check_lots_data import (CHECK_LOT_SLOTS_MAP, CHECK_LOT_SLOTS_ENEMY,
                                   AP_PLACEHOLDER_GOODS)
    _LEGACY = {}
except ImportError:                       # check_lots_data predates the map/enemy split
    CHECK_LOT_SLOTS_MAP, CHECK_LOT_SLOTS_ENEMY = {}, {}
    try:
        from ..check_lots_data import CHECK_LOT_SLOTS as _LEGACY, AP_PLACEHOLDER_GOODS
    except ImportError:                   # no generated data at all: inert
        _LEGACY, AP_PLACEHOLDER_GOODS = {}, 0


@register
class CheckLots(Feature):
    name = "check_lots"

    def slot_data(self, world):
        if not (CHECK_LOT_SLOTS_MAP or CHECK_LOT_SLOTS_ENEMY or _LEGACY) or not AP_PLACEHOLDER_GOODS:
            return {}
        # THE TABLE TRAVELS WITH THE LOT. ItemLotParam_map and ItemLotParam_enemy are two different
        # tables and the same row id can exist in BOTH. gen_data used to merge them into one {lot:
        # slots} dict, throwing the table away, and the client then GUESSED -- it tried map first and
        # fell back to enemy. So an enemy lot whose id also lived in map was never blanked, and a boss
        # that is "just an enemy" would hand out its vanilla drop and fire no check.
        #
        # Sending them separately is not a nicety: it makes "no collisions" a CHECKABLE statement
        # rather than an assumption. (gen_data reports zero collisions today -- so this split is
        # currently load-bearing for nothing, and that is exactly what we want to know.)
        #
        # NB -- this comment used to cite Alaric's 2026-07-12 Unsightly Catacombs report ("enemy lot
        # 30120") as the bug this split fixed. That attribution was WRONG and is retracted: there is
        # no enemy lot 30120 (ItemLotParam_enemy has zero rows in that range), both bosses have
        # itemLotId_enemy = -1, and the real cause was that the reward's acquisition flag (520110) had
        # no location at all -- common.emevd awards that family off a reward flag the map EMEVD flips,
        # and its 6-digit flag decoded to no map tile, so gen_data dropped the check. See
        # tools/datamine_boss_reward_lots.py.
        #
        # Scoping: gen_data already filtered to real check flags; we can only scope by region here, so
        # send every lot. A lot whose check is out of scope sits in a sealed region the player cannot
        # reach, and rewriting it is inert. (Kept explicit so the decision is visible, not accidental.)
        _in_play = {HUB} | set(world._kept())
        if not _in_play:
            return {}
        if _LEGACY:
            # PRE-SPLIT DATA. Emit the legacy key so the client keeps its old (guessing) behaviour --
            # degrading to "as broken as yesterday" beats going silently INERT, which would hand out the
            # vanilla ware at EVERY check. But say so: until gen_data.py is re-run, every boss that is
            # "just an enemy" whose lot id collides with a map row still pays its vanilla drop.
            logging.getLogger("Greenfield").warning(
                "[eldenring:%s] check_lots_data.py predates the ItemLotParam map/enemy split: falling "
                "back to the legacy merged table, so the client must GUESS which param table each lot "
                "lives in. It guesses map-first, so enemy (boss) drops colliding with a map row are NOT "
                "suppressed and will hand out their vanilla item. Re-run `python greenfield/gen_data.py` "
                "to fix.", world.player)
            return {
                contract.CHECK_LOT_BLANK: {str(l): list(sl) for l, sl in _LEGACY.items()},
                contract.AP_PLACEHOLDER_GOODS: int(AP_PLACEHOLDER_GOODS),
            }
        return {
            contract.CHECK_LOT_BLANK_MAP:
                {str(lot): list(slots) for lot, slots in CHECK_LOT_SLOTS_MAP.items()},
            contract.CHECK_LOT_BLANK_ENEMY:
                {str(lot): list(slots) for lot, slots in CHECK_LOT_SLOTS_ENEMY.items()},
            contract.AP_PLACEHOLDER_GOODS: int(AP_PLACEHOLDER_GOODS),
        }
