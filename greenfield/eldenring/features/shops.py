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


# ER FullID category nibble for GOODS (shopPreviewGoods values are FullIDs; see module docstring).
_GOODS_NIBBLE = 0x40000000

# Dedicated spare EquipParamGoods rows for REGION-LOCK shop previews. Each is a row that EXISTS
# (so the client can write its FMG/icon), has the [ERROR] placeholder name (no real name to clobber),
# and is referenced by NO lot / shop / recipe -- the exact AP_PLACEHOLDER_GOODS (8852) criterion,
# and clear of 8852 and the low/system band. Derived from EquipParamGoods.csv + GoodsName.fmg +
# ShopLineupParam*/ItemLotParam* on the pinned artifacts (2026-07-20 verification: 332 spare rows
# total). 64 rows >> the ~54 max region locks, so every lock name gets its own distinct row -- a
# lock's preview never shares a row with a real good OR with another lock.
_LOCK_PREVIEW_SPARE_GOODS = (
    9314, 9315, 9316, 9317, 9318, 9319, 9332, 9333, 9334, 9335, 9336, 9337, 9338, 9339,
    9349, 9350, 9351, 9352, 9353, 9354, 9355, 9356, 9357, 9358, 9359, 9366, 9367, 9368,
    9369, 9370, 9394, 9395, 9396, 9397, 9398, 9399, 9404, 9405, 9406, 9407, 9408, 9409,
    9410, 9424, 9425, 9426, 9427, 9428, 9429, 9430, 9442, 9443, 9444, 9445, 9446, 9447,
    9448, 9449, 9450, 50200, 50201, 50202, 50203, 51760,
)


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
        lock_names = sorted(f"{r} Lock" for r in world._kept())
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
                # own-world item: a region Lock takes its dedicated per-name spare; every other own
                # good is sold as itself by shop_sell, so keep its true (vanilla) preview.
                repointed = name_to_preview.get(it.name)
                if repointed is not None:
                    preview[key] = repointed
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
                "[eldenring:%s] shop flowering: %d foreign slot(s) exceeded the %d free spare goods "
                "and SHARE one preview good (they still flower, but show a single shared name). Widen "
                "_LOCK_PREVIEW_SPARE_GOODS from the 332-row spare pool to give each its own name.",
                world.player, _overflow, len(_free))

        return {contract.SHOP_ROW_FLAGS: flags, contract.SHOP_PREVIEW_GOODS: preview}
