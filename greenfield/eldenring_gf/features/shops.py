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
from ..data import HUB

try:
    from ..shop_data import SHOP_ROW_FLAGS, SHOP_LOC_REGION, SHOP_PREVIEW_GOODS
except Exception:  # not yet generated
    SHOP_ROW_FLAGS, SHOP_LOC_REGION, SHOP_PREVIEW_GOODS = {}, {}, {}


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
        flags = {aid: fl for aid, fl in SHOP_ROW_FLAGS.items()
                 if SHOP_LOC_REGION.get(int(aid)) in scope}
        preview = {aid: g for aid, g in SHOP_PREVIEW_GOODS.items() if aid in flags}
        return {"shopRowFlags": flags, "shopPreviewGoods": preview}
