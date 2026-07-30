"""SPEC-PARITY Phase 4 -- shops as checks (+ merchant-bell logic).

Derivation (matt-free): region_map rows with method in {shop_merchant, shop_multi} carry
flag_source=="shop", and for those rows region_map's `flag` IS ShopLineupParam.eventFlag_forStock
(verified 505/505 on disk against elden_ring_artifacts/vanilla_er ShopLineupParam.csv). cookbook rows
are map_lot/enemy_lot pickups (not shop purchases), so they are NOT shop checks. gen_data.py
pre-generates shop_data.py: SHOP_ROW_FLAGS {str(ap_id): stock_flag} is the client purchase-detect
table, SHOP_LOC_REGION scopes checks to kept regions, SHOP_PREVIEW_GOODS {str(ap_id): FullID} is the
vanilla preview (single-good rows). All keyed by flag / vanilla param, never a matt name
(SPEC-PARITY.md 14.3).

shopPreviewGoods values are FullIDs, NOT raw equipIds: gen_data ORs the ER category nibble
(WEAPON=0, PROTECTOR=0x10000000, ACCESSORY=0x20000000, GOODS=0x40000000, GEM=0x80000000) derived from
ShopLineupParam.equipType (0=weapon,1=protector,2=accessory,3=goods,4=gem, confirmed on disk) into the
equipId. A raw equipId is ambiguous without its category (e.g. 4020 is a valid id in several param
tables); the FullID nibble disambiguates so the client previews the good in the right table. The
feature passes preview values through unchanged.

shopRowFlags is scoped to the hub + kept spokes (many merchant / all shop_multi rows collapse to the
always-kept Roundtable Hold hub). shopPreviewGoods is emitted for the same scoped rows.

MerchantBellLogic=logic_only would gate a bell-bearing merchant's shop checks behind that merchant's
Bell Bearing in logic. This is NOT derivable matt-free from disk: the bell-item flag (e.g. Kale's
Bell Bearing = 400049) appears NOWHERE in ShopLineupParam (0 hits as stock or release flag), because
the Twin Maiden re-sold inventory is added by an EMEVD bell-handover common event, not a param join;
eventFlag_forRelease on those rows is 0 (or an unrelated NPC-availability flag), and region_map.csv
carries no shop-lineup id / bell column. So v1 emits the OPTION only (default off = every shop check
always open); the bell->merchant->shop-rows map is a v2 EMEVD enrichment (SPEC-PARITY 14.3). Empty
dicts remain a valid no-op contract if shop_data.py is absent.
"""
from Options import Choice
from ..registry import Feature, register
from .. import contract
from ..data import HUB

try:
    from ..shop_data import (SHOP_ROW_FLAGS, SHOP_ROW_IDS, SHOP_LOC_REGION,
                             SHOP_PREVIEW_GOODS)
except Exception:  # not yet generated
    SHOP_ROW_FLAGS, SHOP_ROW_IDS, SHOP_LOC_REGION, SHOP_PREVIEW_GOODS = {}, {}, {}, {}

try:
    from ..shop_data import SPARE_PREVIEW_GOODS      # datamined pool (tools/datamine_spare_goods.py)
except Exception:                                   # predates the spare-goods emit
    SPARE_PREVIEW_GOODS = ()

try:
    from ..item_ids import ITEM_CATALOG              # item NAME -> ER FullID (generated)
except Exception:                                   # not yet generated
    ITEM_CATALOG = {}


# ER FullID category nibble for GOODS (shopPreviewGoods values are FullIDs; see module docstring).
_GOODS_NIBBLE = 0x40000000

# Categories the CLIENT can natively sell out of a shop row (shop_sell.equip_type_for: 0 weapon,
# 1 protector, 2 accessory, 3 goods). GEM (0x80000000) and custom weapons have no ShopLineupParam
# equipType, so an own-world reward in one of those is NOT natively sellable -- it falls through to
# the shop_preview display override exactly like a foreign item, and therefore needs a spare of its
# own. This MIRRORS the client's scout_proof `er_sell_id` filter; the client half is the one that
# decides, so keep this in step with it (crates/eldenring-archipelago/src/scout_proof.rs).
_GEM_NIBBLE = 0x80000000
# GEMS (Ashes of War) ARE natively sellable -- added 2026-07-29. This set excluded them on the
# premise that ShopLineupParam has "no equipType" for a gem. That premise is false: vanilla ships
# 135 rows with equipType=4, i.e. merchants sell Ashes of War in the base game.
#
# The cost of the mistake was not one wasted spare. A gem fell through to the preview override, so
# every own-world Ash of War wore the AP flower and drew a spare row -- and only 25 of the 65 spares
# carry GoodsInfo/GoodsCaption, so those slots rendered `?GoodsInfo?` too. Measured on a SOLO seed
# (no foreign items at all): 65 slots repointed to spares, the entire pool exhausted, essentially
# all of it gems. Alaric, in game: "no reason to be doing AP Flower on an ash of war".
# Selling them natively gives the real name, icon and description and returns the pool to the
# slots that genuinely need it.
_SELLABLE_NIBBLES = frozenset((0x00000000, 0x10000000, 0x20000000, _GOODS_NIBBLE, _GEM_NIBBLE))
# Synthetic goods rows (the AP-injected band) are excluded by the client's filter too.
_SYNTHETIC_GOODS_MIN_ID = 3_780_000


def _client_can_sell(item_name):
    """Can shop_sell rewrite a row to natively sell this own-world reward?

    UNKNOWN answers False on purpose. A wrong False costs one spare row out of the pool and nothing
    else -- shop_sell still rewrites the row, and shop_repoint skips every row shop_sell owns, so the
    unused spare is inert. A wrong True is the bug this exists to kill: the slot keeps its vanilla
    preview good, the client's real-good guard protects it, and the player reads the vanilla ware off
    the shelf (Alaric 2026-07-25, an Ash of War behind "Armorer's Cookbook [2]"). Refusing to answer
    beats answering confidently wrong.
    """
    full = ITEM_CATALOG.get(item_name)
    if full is None:
        return False
    nibble = full & 0xF0000000
    # 🛑 THE SYNTHETIC FLOOR IS GOODS-ONLY. This applied it to EVERY category, and weapon/protector
    # row ids routinely sit above it -- Sacrificial Axe is row 14,110,000 and Oathseeker Knight
    # Greaves 5,000,300 against a floor of 3,780,000. So essentially every weapon and armour piece
    # was reported unsellable, fell through to the shop_preview override, and drew a spare row:
    # measured on a solo seed, 64 weapons + 11 protectors doing exactly that, exhausting the pool.
    # That is why an item the client WAS selling natively still wore the AP flower, and why the
    # spare pool was so oversubscribed that most slots got a row with no GoodsInfo/GoodsCaption.
    #
    # The client has always had it right -- er_codec::is_synthetic_goods is
    # `category == GOODS && row > MIN`, and its comment says so: "a real item in any other category
    # is never synthetic, regardless of how large its id is". This function's own docstring claims
    # to MIRROR that filter. It had drifted, and nothing compared the two.
    if nibble == _GOODS_NIBBLE and (full & 0x0FFFFFFF) >= _SYNTHETIC_GOODS_MIN_ID:
        return False
    return nibble in _SELLABLE_NIBBLES

# Dedicated spare EquipParamGoods rows for REGION-LOCK and FOREIGN-item shop previews. Each is a row
# that EXISTS (so the client can write its FMG/icon), has the [ERROR] placeholder name (no real name to
# clobber), and is referenced by NO lot / shop / recipe -- the exact AP_PLACEHOLDER_GOODS (8852)
# criterion, above the 8852 low/system floor. The pool is DATAMINED (tools/datamine_spare_goods.py ->
# greenfield/spare_goods.tsv -> shop_data.SPARE_PREVIEW_GOODS); gen_data emits it so this list tracks
# the artifacts instead of drifting. NOTE the usable pool is ~82 rows, not the 332 an earlier comment
# claimed -- 332 was the raw all-range count; only ~82 sit above the 8852 floor (the rest are in the
# unusable low/system band). 82 > the ~54 max region locks, so every LOCK gets its own distinct row;
# FOREIGN items draw from the remainder and, in a busy multiworld, may exceed it and share a row (still
# flowered, just a shared name -- shops.py logs that overflow). The hardcoded tuple below is the
# FALLBACK for a tree with no regenerated shop_data yet.
_LOCK_PREVIEW_SPARE_GOODS_FALLBACK = (
    9314, 9315, 9316, 9317, 9318, 9319, 9332, 9333, 9334, 9335, 9336, 9337, 9338, 9339,
    9349, 9350, 9351, 9352, 9353, 9354, 9355, 9356, 9357, 9358, 9359, 9366, 9367, 9368,
    9369, 9370, 9394, 9395, 9396, 9397, 9398, 9399, 9404, 9405, 9406, 9407, 9408, 9409,
    9410, 9424, 9425, 9426, 9427, 9428, 9429, 9430, 9442, 9443, 9444, 9445, 9446, 9447,
    9448, 9449, 9450, 50200, 50201, 50202, 50203, 51760,
)
_LOCK_PREVIEW_SPARE_GOODS = tuple(SPARE_PREVIEW_GOODS) or _LOCK_PREVIEW_SPARE_GOODS_FALLBACK


class MerchantBellLogic(Choice):
    """Whether bell-bearing merchants' shop checks require their bell in logic. off = every shop
    check is always open; logic_only would gate them behind the merchant's Bell Bearing. The
    bell->merchant->shop-rows mapping is not derivable matt-free from disk (bell-item flags do not
    appear in ShopLineupParam; the join lives in EMEVD bell-handover events), so v1 carries the
    option only and it is a no-op until a v2 EMEVD enrichment supplies that map (see module docstring)."""
    display_name = "Merchant Bell Logic"
    option_off = 0
    option_logic_only = 1
    default = 0


@register
class Shops(Feature):
    name = "shops"
    OPTIONS = {"merchant_bell_logic": MerchantBellLogic}

    def slot_data(self, world):
        # Hub is always in play; kept() is the spokes. Shop rows collapse to hub or a spoke region.
        scope = {HUB} | set(world._kept())
        # In-scope shop checks (keyed by AP id) and their vanilla stock flag.
        scoped = {aid: fl for aid, fl in SHOP_ROW_FLAGS.items()
                  if SHOP_LOC_REGION.get(int(aid)) in scope}
        # shopRowFlags is keyed by ShopLineupParam ROW id (client shop_flags.rs writes eventFlag_forStock
        # onto that row via repo.get::<ShopLineupParam>(row_id)); the OLD AP-id key made every row read
        # "absent; skipped". SHOP_ROW_IDS[ap_id] = the vanilla row(s) whose stock flag == this check's
        # flag; each such row asserts the flag (idempotent -- greenfield uses the vanilla flag as the AP
        # flag, so the write is a no-op, but the row now RESOLVES instead of erroring).
        flags = {}
        for aid, fl in scoped.items():
            for row_id in SHOP_ROW_IDS.get(aid, []):
                flags[int(row_id)] = fl
        # shopPreviewGoods stays keyed by AP location id (client shop_preview/shop_icon take (loc, good)).
        preview = {aid: g for aid, g in SHOP_PREVIEW_GOODS.items() if aid in scoped}

        # REGION-LOCK PREVIEW REPOINT (2026-07-20). shopPreviewGoods is COSMETIC (the check fires by
        # SHOP_ROW_FLAGS, not the ware), and the client overrides the preview good's shared FMG + icon
        # GLOBALLY per good id. When a region lock lands on a shop check, it inherits that slot's
        # vanilla ware as its preview good -- and if that ware is a real grantable good, every copy
        # the player holds gets relabeled as the lock (playtest: "9 Leyndell Locks" that were 9
        # Perfume Bottles, row 9510). Repoint each lock-holding shop slot at a DEDICATED spare row so
        # the client names/flowers it without touching any real good. Locks are unique items, so one
        # spare per lock NAME (sorted for determinism) suffices; lock names are built exactly as in
        # core.set_rules (`f"{r} Lock"` over _kept()), so they match the placed item names.
        # 🛑 RESERVE FOR LOCKS THAT ACTUALLY LAND ON A SHOP SLOT, NOT FOR EVERY KEPT REGION.
        # This used to enumerate `f"{r} Lock" for r in world._kept()` -- ~30 names -- and hand each a
        # spare up front, so `_free` began at index ~30. Only the first 25 pool rows carry
        # GoodsInfo/GoodsCaption (spare_goods.tsv orders them first), so every FOREIGN slot drew an
        # undescribable row and rendered `?GoodsInfo?`, while ~28 describable rows sat reserved for
        # locks that were never on a shelf. Seen in the wild 2026-07-29: names=10 infos=2, and the
        # 2 was exactly the number of locks that DID land on shop slots.
        # So: find the lock names really sitting on shop checks first, and reserve only those.
        _shop_lock_names = set()
        for _loc in world.multiworld.get_locations(world.player):
            _aid = getattr(_loc, "address", None)
            if _aid is None or str(_aid) not in preview:
                continue
            _it = getattr(_loc, "item", None)
            if _it is not None and getattr(_it, "player", None) == world.player \
                    and _it.name.endswith(" Lock"):
                _shop_lock_names.add(_it.name)
        lock_names = sorted(_shop_lock_names)
        name_to_preview = {nm: (_LOCK_PREVIEW_SPARE_GOODS[i] | _GOODS_NIBBLE)
                           for i, nm in enumerate(lock_names)
                           if i < len(_LOCK_PREVIEW_SPARE_GOODS)}

        # FLOWER EVERY FOREIGN SHOP SLOT (Alaric 2026-07-22, "we should be flowering them all"). The
        # client leaves a shop slot VANILLA whenever its preview good is a REAL grantable good, because
        # flowering re-icons that good's EVERY copy globally (the hazard the lock repoint dodges). A
        # slot holding ANOTHER player's item hits the same wall -- its vanilla ware is usually a real
        # good -- so those foreign checks read as the vanilla item on the shelf. Fix: repoint each
        # foreign slot at a dedicated spare good (exists, [ERROR] name, referenced by nothing, exactly
        # like the lock spares) so the client flowers it without touching any real good. Own-world
        # items stay on shop_sell -- they sell the real item and MUST keep their true preview.
        # Spares past the lock allotment feed the foreign slots; determinism from get_locations' stable
        # order over the sorted pool. Cosmetic only -- the check fires by SHOP_ROW_FLAGS, not the ware.
        player = world.player
        _free = [g | _GOODS_NIBBLE for g in _LOCK_PREVIEW_SPARE_GOODS[len(name_to_preview):]]
        _fi = 0
        _overflow = 0
        for loc in world.multiworld.get_locations(player):
            aid = getattr(loc, "address", None)
            if aid is None:
                continue
            key = str(aid)                     # preview is keyed by STR ap-id (SHOP_PREVIEW_GOODS);
            if key not in preview:             # loc.address is an int -- compare as strings or the
                continue                       # lookup silently never matches (the old lock-repoint bug).
            it = getattr(loc, "item", None)
            if it is None:
                continue
            if getattr(it, "player", None) == player:
                # own-world item: a region Lock takes its dedicated per-name spare; a reward the
                # client can natively SELL keeps its true (vanilla) preview, because shop_sell
                # rewrites the row to sell the real item -- correct name, icon and lore, no override.
                repointed = name_to_preview.get(it.name)
                if repointed is not None:
                    preview[key] = repointed
                    continue
                if _client_can_sell(it.name):
                    continue
                # OWN-WORLD BUT UNSELLABLE -- a synthetic-band good, or a custom item with no real
                # param row behind it. shop_sell cannot vend those, so the slot falls through to the
                # shop_preview override -- and with its VANILLA preview good that override hits the
                # real-good guard and leaves the slot reading as the vanilla ware. Same wall as a
                # foreign item, so: same fix, draw a spare. (Alaric, in-game 2026-07-25: "Armorer's
                # Cookbook [2]" paying an Ash of War.)
                #
                # That exemplar has SINCE BEEN RECLASSIFIED: gems are natively vendable and left this
                # branch on 2026-07-29 -- see _SELLABLE_NIBBLES for the datum (135 vanilla
                # ShopLineupParam rows carry equipType 4). The branch and the hazard are unchanged;
                # only the population reaching it shrank.
                if _fi < len(_free):
                    preview[key] = _free[_fi]
                    _fi += 1
                elif _free:
                    preview[key] = _free[-1]
                    _overflow += 1
                continue
            # FOREIGN item: repoint to a spare so the client flowers it (spare is never a real good).
            if _fi < len(_free):
                preview[key] = _free[_fi]
                _fi += 1
            elif _free:
                preview[key] = _free[-1]   # pool exhausted -> share the last spare (still flowers)
                _overflow += 1
            # else (no spares at all -- e.g. locks consumed the whole pool): leave vanilla, don't crash
        if _overflow:
            import logging
            logging.getLogger("Greenfield").warning(
                "[eldenring:%s] shop flowering: %d foreign/unsellable slot(s) exceeded the %d free "
                "spare goods and SHARE one preview good (they still flower, but show a single shared "
                "name). Widen the spare pool (tools/datamine_spare_goods.py) to give each its own name.",
                world.player, _overflow, len(_free))

        return {contract.SHOP_ROW_FLAGS: flags, contract.SHOP_PREVIEW_GOODS: preview}
