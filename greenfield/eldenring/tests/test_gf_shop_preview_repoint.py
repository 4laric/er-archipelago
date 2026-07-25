"""The shop-slot PREVIEW REPOINT -- who gets a spare goods row, and who must not.

Context (2026-07-25). `shopPreviewGoods` tells the client which goods row to display for a shop
check. The client honours it by rewriting that row's FMG name/info/caption and its iconId -- both
GLOBAL to the goods row -- and, since the companion client fix, by writing the row onto the slot's
`ShopLineupParam.equipId` so the override is actually visible.

Three populations, three different correct answers:

  * REGION LOCK          -> its own dedicated spare (one per lock name).
  * FOREIGN item         -> a spare from the remaining pool.
  * OWN-WORLD, SELLABLE  -> keep the TRUE vanilla preview. `shop_sell` rewrites the row to sell the
                            real item, so it needs no override at all, and handing it a spare would
                            make the client repoint a row shop_sell owns.
  * OWN-WORLD, UNSELLABLE (gem / Ash of War / custom) -> a spare, exactly like a foreign item.
                            shop_sell cannot sell these (no ShopLineupParam equipType), so they fall
                            through to the display override -- and with a VANILLA preview good that
                            override hits the client's real-good guard and the slot silently reads as
                            its vanilla ware. That is the defect Alaric hit in-game on 2026-07-25:
                            a slot reading "Armorer's Cookbook [2]" that paid out an Ash of War.

The last one is the bug this file exists to keep fixed.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.features import shops as shops_feature  # noqa: E402
from worlds.eldenring.shop_data import SHOP_PREVIEW_GOODS  # noqa: E402

GAME = "Elden Ring"

_GOODS = 0x40000000
_WEAPON = 0x00000000
_PROTECTOR = 0x10000000
_ACCESSORY = 0x20000000
_GEM = 0x80000000


class ClientCanSell(WorldTestBase):
    """`_client_can_sell` MIRRORS the client's scout_proof `er_sell_id` filter. If the two disagree,
    a slot is either flowered when it did not need to be (harmless -- one spare wasted) or left
    vanilla when it did (the bug). The asymmetry is why UNKNOWN must answer False."""

    game = GAME
    options = {}

    def _with_catalog(self, catalog):
        """Swap ITEM_CATALOG for the duration of one assertion -- the predicate reads it at call
        time, and the real catalog's contents are a generated artifact we must not pin here."""
        orig = shops_feature.ITEM_CATALOG
        shops_feature.ITEM_CATALOG = catalog
        try:
            return {nm: shops_feature._client_can_sell(nm) for nm in catalog}
        finally:
            shops_feature.ITEM_CATALOG = orig

    def test_sellable_categories_keep_their_vanilla_preview(self):
        got = self._with_catalog({
            "A Weapon": _WEAPON | 1030000,
            "An Armour": _PROTECTOR | 40000,
            "A Talisman": _ACCESSORY | 1000,
            "A Consumable": _GOODS | 105,
        })
        self.assertEqual(got, {k: True for k in got},
                         "shop_sell natively sells all four of these -- they must NOT draw a spare")

    def test_a_gem_reward_is_not_sellable(self):
        # An Ash of War. equipType has no gem value, so shop_sell bails and the slot needs a spare.
        got = self._with_catalog({"An Ash of War": _GEM | 10000})
        self.assertFalse(got["An Ash of War"])

    def test_synthetic_goods_are_not_sellable(self):
        # The AP-injected synthetic band is excluded by the client's filter too.
        got = self._with_catalog({"Synthetic": _GOODS | 3_800_000})
        self.assertFalse(got["Synthetic"])

    def test_an_unknown_item_refuses_rather_than_guessing(self):
        # Not in ITEM_CATALOG -> we cannot know the category. Answering True here is how the slot
        # silently keeps a vanilla preview it cannot support; answering False costs one spare row.
        got = self._with_catalog({"Known": _GOODS | 105})
        self.assertNotIn("Unknown Item", got)
        orig = shops_feature.ITEM_CATALOG
        shops_feature.ITEM_CATALOG = {}
        try:
            self.assertFalse(shops_feature._client_can_sell("Unknown Item"))
        finally:
            shops_feature.ITEM_CATALOG = orig


class _StubItem:
    def __init__(self, name, player):
        self.name = name
        self.player = player


class _StubLoc:
    def __init__(self, address, item):
        self.address = address
        self.item = item


class PreviewRepointBranches(WorldTestBase):
    """Drive the repoint decision directly, with STUBBED placements.

    Why stubs and not a generated seed: `fill_slot_data` reads `loc.item`, and in a solo
    WorldTestBase world almost nothing is placed at that point -- probing this suite found 3 of 486
    shop preview slots carrying an item, and 0 foreign / 0 own-world-unsellable among them (a solo
    seed has no foreign items by definition). A seed-driven assertion here would therefore pass
    without ever entering the branch it claims to test, which is the vacuous-oracle failure this
    repo keeps paying for. Stubbing the placements is what gives the test teeth: delete the
    own-world-unsellable arm and `test_an_own_world_gem_reward_draws_a_spare` goes red.
    """

    game = GAME
    options = {"num_regions": 6, "num_regions_order": "spine"}

    def _preview_for(self, placements):
        """placements: {ap_id (str) -> (item_name, owning_player)}. Returns the emitted preview map."""
        w = self.world
        locs = [_StubLoc(int(aid), _StubItem(nm, pl)) for aid, (nm, pl) in placements.items()]
        orig = w.multiworld.get_locations
        w.multiworld.get_locations = lambda player=None: locs
        try:
            return w.fill_slot_data()["shopPreviewGoods"]
        finally:
            w.multiworld.get_locations = orig

    def _two_shop_ap_ids(self):
        """Two in-scope shop check ap-ids, taken from the emitted preview map itself."""
        spg = self.world.fill_slot_data()["shopPreviewGoods"]
        ids = sorted(spg, key=int)
        self.assertGreaterEqual(len(ids), 2, "need at least two in-scope shop checks to test with")
        return ids[0], ids[1], spg

    def test_an_own_world_gem_reward_draws_a_spare(self):
        """THE REGRESSION. An own-world Ash of War is not natively sellable, so leaving it on its
        vanilla preview good is what made a slot read "Armorer's Cookbook [2]" while paying an Ash
        of War (Alaric, in-game 2026-07-25)."""
        aid, _, vanilla_map = self._two_shop_ap_ids()
        gem_name = "-- test gem --"
        orig = shops_feature.ITEM_CATALOG
        shops_feature.ITEM_CATALOG = dict(orig)
        shops_feature.ITEM_CATALOG[gem_name] = _GEM | 10000
        try:
            preview = self._preview_for({aid: (gem_name, self.world.player)})
        finally:
            shops_feature.ITEM_CATALOG = orig
        spares = {g | _GOODS for g in shops_feature._LOCK_PREVIEW_SPARE_GOODS}
        self.assertNotEqual(preview[aid], vanilla_map[aid],
                            "an unsellable own-world reward must NOT keep its vanilla preview good")
        self.assertIn(preview[aid], spares,
                      "it must be repointed at a datamined spare, never at another real good")

    def test_an_own_world_sellable_reward_keeps_its_vanilla_preview(self):
        """The other half, and the one a careless fix breaks: shop_sell rewrites this row to sell the
        real item, so it needs no override -- and handing it a spare would make the client repoint a
        row shop_sell owns."""
        aid, _, vanilla_map = self._two_shop_ap_ids()
        w_name = "-- test weapon --"
        orig = shops_feature.ITEM_CATALOG
        shops_feature.ITEM_CATALOG = dict(orig)
        shops_feature.ITEM_CATALOG[w_name] = _WEAPON | 1030000
        try:
            preview = self._preview_for({aid: (w_name, self.world.player)})
        finally:
            shops_feature.ITEM_CATALOG = orig
        self.assertEqual(preview[aid], vanilla_map[aid])

    def test_a_foreign_reward_draws_a_spare(self):
        aid, _, vanilla_map = self._two_shop_ap_ids()
        foreign_player = self.world.player + 1
        preview = self._preview_for({aid: ("Someone Else's Thing", foreign_player)})
        spares = {g | _GOODS for g in shops_feature._LOCK_PREVIEW_SPARE_GOODS}
        self.assertIn(preview[aid], spares)

    def test_a_region_lock_takes_its_own_dedicated_spare(self):
        aid, other, _ = self._two_shop_ap_ids()
        lock = sorted(f"{r} Lock" for r in self.world._kept())[0]
        preview = self._preview_for({aid: (lock, self.world.player)})
        spares = {g | _GOODS for g in shops_feature._LOCK_PREVIEW_SPARE_GOODS}
        self.assertIn(preview[aid], spares)
        # Lock spares are allotted per NAME from the head of the pool; foreign/unsellable draw from
        # the tail. The two allotments must not collide, or a lock and a foreign item share a name.
        foreign = self._preview_for({other: ("Someone Else's Thing", self.world.player + 1)})
        self.assertNotEqual(preview[aid], foreign[other])


class SparePoolSafety(WorldTestBase):
    """The spare pool's defining property, asserted where it can actually be seen."""

    game = GAME
    options = {"num_regions": 6, "num_regions_order": "spine"}

    def test_no_spare_is_a_good_the_seed_can_grant(self):
        # The client refuses to override a good the seed can GRANT (shop_preview's REAL_GOODS guard).
        # If a spare ever collided with one, the client would silently leave that slot vanilla -- the
        # feature would go quietly inert rather than fail, which is the whole disease this repo
        # documents. Assert the disjointness instead of trusting the datamine's comment.
        from worlds.eldenring.core import _AP_IDS_TO_ITEM_IDS
        grantable_goods = {v & 0x0FFFFFFF for v in _AP_IDS_TO_ITEM_IDS.values()
                           if (v & 0xF0000000) == _GOODS}
        overlap = set(shops_feature._LOCK_PREVIEW_SPARE_GOODS) & grantable_goods
        self.assertEqual(
            overlap, set(),
            "spare preview rows must never be goods the seed can grant; %r overlap" % sorted(overlap))
