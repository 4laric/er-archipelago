"""item_categories + the fine-grained locality controls + pool_report (WorldTestBase).

THE MOTIVATING CASE, and therefore the acceptance test (CONTRIBUTING rule 11) -- boblerrr on
Discord, 2026-08-08: "crafting materials should be local, upgrade materials other than bell bearing
can be local prob, same with ghost gloveworts, every single consumable item should be local prob,
small rune amounts should not be sent out". `KeepLocalIsTheDiscordAsk` below is that yaml, asserted
clause by clause -- including the one that says what must STILL travel, because a control that keeps
everything is the control we already had.

The partition tests are the load-bearing ones: "how many items am I sending out" is only answerable
if every item is in exactly one category, so that property is asserted directly rather than trusted.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring import item_categories as ic          # noqa: E402
from worlds.eldenring import pool_report                     # noqa: E402
from worlds.eldenring.item_ids import ITEM_CATALOG, GOODS_TYPE  # noqa: E402

GAME = "Elden Ring"


def _local(tb):
    return set(tb.world.options.local_items.value)


class TaxonomyIsAPartition(WorldTestBase):
    game = GAME
    options = {"num_regions": 1}

    def test_generated_inputs_are_present(self):
        # Every assertion below is vacuous on a pre-regen tree, so say so loudly rather than pass.
        self.assertTrue(ITEM_CATALOG, "item_ids.py must be generated")
        self.assertTrue(GOODS_TYPE, "item_ids.py must carry GOODS_TYPE (gen_data.py regen)")

    def test_every_catalog_item_has_exactly_one_category(self):
        cats = {n: ic.category_of(n) for n in ITEM_CATALOG}
        self.assertEqual(len(cats), len(ITEM_CATALOG))
        unknown = sorted({c for c in cats.values()} - set(ic.CATEGORIES))
        self.assertFalse(unknown, f"category_of returned keys outside CATEGORIES: {unknown}")

    def test_census_sums_to_the_catalog(self):
        # The count is the product. If the census and the catalog disagree, every number this
        # feature shows a player is wrong by the difference and nothing else would say so.
        self.assertEqual(sum(ic.census().values()), len(ITEM_CATALOG))

    def test_goods_umbrella_is_exactly_the_goods_nibble(self):
        # THE REGRESSION THIS FILE EXISTS FOR. `exclude_local_item_only: [goods]` predates the
        # split and is in players' yamls; it must release the same set it always released. The
        # first draft of UMBRELLAS built `goods` from GOODS_TYPE_CATEGORY.values() and so omitted
        # `runes`, which are carved out by payout rather than by type.
        umbrella = set(ic.expand(["goods"]))
        by_nibble = {n for n, full in ITEM_CATALOG.items()
                     if (full & 0xF0000000) == ic.GOODS_NIBBLE}
        by_category = {n for n in ITEM_CATALOG if ic.category_of(n) in umbrella}
        self.assertEqual(by_category, by_nibble)

    def test_runes_are_the_payout_items_not_the_name_match(self):
        runes = {n for n in ITEM_CATALOG if ic.category_of(n) == "runes"}
        self.assertTrue(runes)
        for n in runes:
            self.assertIsNotNone(ic.rune_payout(n), f"{n} is in `runes` with no payout")
        # a name match on "Rune" would sweep these three in; the payout column does not.
        for decoy in ("Rune Arc", "Godrick's Great Rune"):
            if decoy in ITEM_CATALOG:
                self.assertNotEqual(ic.category_of(decoy), "runes")

    def test_the_categories_the_ask_names_are_populated(self):
        c = ic.census()
        for k in ("consumables", "crafting", "upgrade_materials", "runes"):
            self.assertGreater(c.get(k, 0), 0, f"category {k} is empty -- the option cannot work")
        # ghost gloveworts and smithing stones are the same category; bell bearings are NOT.
        self.assertEqual(ic.category_of("Ghost Glovewort [1]"), "upgrade_materials")
        self.assertEqual(ic.category_of("Smithing Stone [1]"), "upgrade_materials")
        bells = [n for n in ITEM_CATALOG if n.endswith("Bell Bearing")]
        self.assertTrue(bells)
        for b in bells:
            self.assertEqual(ic.category_of(b), "key_items")


class KeepLocalIsTheDiscordAsk(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "item_shuffle": True,
               "keep_local": ["consumables", "crafting", "upgrade_materials"]}

    def test_the_named_categories_are_held(self):
        local = _local(self)
        held = [n for n in ITEM_CATALOG
                if ic.category_of(n) in ("consumables", "crafting", "upgrade_materials")]
        self.assertTrue(held)
        missing = [n for n in held if n not in local]
        self.assertFalse(missing, f"{len(missing)} named-category items not held (e.g. {missing[:3]})")

    def test_gear_still_travels(self):
        # A locality control that holds everything is `local_item_only`, which already existed.
        # What makes this one worth adding is what it LEAVES alone.
        local = _local(self)
        for cat in ("weapons", "armor", "talismans", "spells"):
            free = [n for n in ITEM_CATALOG if ic.category_of(n) == cat and n not in local]
            self.assertTrue(free, f"no {cat} left free to travel")

    def test_progression_is_untouched(self):
        local = _local(self)
        locks = [n for n in self.world.item_name_to_id if n.endswith(" Lock")]
        self.assertTrue(locks)
        for lk in locks:
            self.assertNotIn(lk, local)


class KeepLocalRuneCapHoldsTheSmallOnes(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "item_shuffle": True, "keep_local_rune_cap": 3000}

    def test_cheap_runes_held_expensive_runes_free(self):
        local = _local(self)
        small = [n for n in ITEM_CATALOG
                 if (p := ic.rune_payout(n)) is not None and p <= 3000]
        big = [n for n in ITEM_CATALOG
               if (p := ic.rune_payout(n)) is not None and p > 3000]
        self.assertTrue(small and big, "the cap must actually split the rune ladder")
        self.assertFalse([n for n in small if n not in local])
        self.assertFalse([n for n in big if n in local], "runes above the cap must stay free")

    def test_nothing_else_is_swept_in(self):
        local = _local(self)
        # WITNESS: without this the assertion below passes just as happily on a cap that held
        # nothing at all, which is the failure it is meant to catch.
        self.assertTrue(local, "the rune cap held nothing -- there is no over-reach to test for")
        non_rune_held = [n for n in ITEM_CATALOG if n in local and ic.rune_payout(n) is None]
        self.assertFalse(non_rune_held,
                         f"the rune cap held non-rune items: {non_rune_held[:5]}")


class RuneCapOffByDefault(WorldTestBase):
    game = GAME
    options = {"num_regions": 1, "item_shuffle": True}

    def test_default_holds_nothing(self):
        # 0 is OFF, not "a cap of zero runes". A default that quietly localized the whole rune
        # ladder would change every existing seed's multiworld shape without anyone asking.
        # WITNESS: an empty pool would make "nothing is held local" true for the wrong reason.
        pool = [i for i in self.world.multiworld.itempool if i.player == self.world.player]
        self.assertTrue(pool, "the seed produced no items -- 'nothing held' would be vacuous")
        self.assertEqual(self.world.options.keep_local_rune_cap.value, 0)
        self.assertFalse(_local(self))

    def test_report_counts_the_whole_pool_as_free(self):
        est = pool_report.estimate(self.world)
        self.assertEqual(est["held"], 0)
        self.assertEqual(est["free"], est["pool"])
        self.assertGreater(est["pool"], 0)
        self.assertEqual(est["free"], est["free_filler"] + est["free_useful"] + est["free_progression"])


class ReportCountsWhatIsHeld(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "item_shuffle": True, "keep_local": ["goods"]}

    def test_held_and_free_partition_the_pool(self):
        est = pool_report.estimate(self.world)
        self.assertEqual(est["held"] + est["free"], est["pool"])
        self.assertGreater(est["held"], 0, "keep_local: [goods] must hold something back")
        self.assertGreater(est["free"], 0, "gear must still be free with only goods held")

    def test_solo_summary_says_solo(self):
        # A solo seed has nowhere to send anything; the summary must not report a measured 0 as
        # though it were a multiworld result.
        s = pool_report.summary(self.world)
        self.assertEqual(s["players"], 1)
        self.assertNotIn("sent", s)


# ---------------------------------------------------------------------------------------------
# pool_report.measured() needs a COMPLETED MULTI-PLAYER FILL, which no test in this suite builds
# and which a WorldTestBase cannot be (it is solo by construction). So it is called DIRECTLY, over
# a hand-built set of placements -- [[guard-absent-from-corpus-needs-a-direct-call]]: a branch no
# test in the corpus can reach is untested however green the suite is, and this is the branch that
# produces the only number a player will quote.
#
# What is actually at risk here is one confusion, and it is a silent one: `location.player` is whose
# world the item SITS IN and `item.player` is whose world it CAME FROM. Read either alone and you
# get a plausible number that answers a different question -- `item.player == me` over all locations
# counts my own items at home, which in a default seed is most of the pool.
class _Item:
    def __init__(self, player, classification):
        self.player = player
        self.classification = classification
        self.name = "x"


class _Loc:
    def __init__(self, player, item):
        self.player = player
        self.item = item


class _MW:
    players = 3

    def __init__(self, locs):
        self._locs = locs

    def get_locations(self):
        return self._locs

    def get_player_name(self, p):
        return f"P{p}"


class _World:
    player = 1

    def __init__(self, locs):
        self.multiworld = _MW(locs)


def test_measured_reads_owner_and_holder_separately():
    from BaseClasses import ItemClassification as IC
    mine_filler = _Item(1, IC.filler)
    mine_useful = _Item(1, IC.useful)
    mine_prog = _Item(1, IC.progression)
    theirs = _Item(2, IC.filler)
    locs = [
        _Loc(2, mine_filler),   # sent  -- my filler in P2's world
        _Loc(3, mine_useful),   # sent  -- my useful in P3's world
        _Loc(2, mine_prog),     # sent  -- my progression in P2's world
        _Loc(1, mine_filler),   # NOT sent: my item, my world (the classic miscount)
        _Loc(1, theirs),        # received
        _Loc(3, theirs),        # neither: someone else's item, someone else's world
        _Loc(1, None),          # unfilled
    ]
    m = pool_report.measured(_World(locs))
    assert m["sent"] == 3, m
    assert m["received"] == 1, m
    assert (m["sent_filler"], m["sent_useful"], m["sent_progression"]) == (1, 1, 1), m


def test_report_line_is_readable_and_names_both_numbers():
    s = {"players": 3, "pool": 1000, "free": 400, "held": 600, "free_filler": 300,
         "free_useful": 100, "free_progression": 0, "sent": 120, "received": 45,
         "sent_filler": 100, "sent_useful": 20, "sent_progression": 0}
    line = pool_report._line(_World([]), s)
    assert "sent 120 of 1000" in line
    assert "100 filler" in line
    assert "600 items were held local" in line
    # the ceiling has to be labelled as one -- an unlabelled 400 next to a 120 reads as a conflict
    assert "ceiling" in line


def test_solo_line_does_not_report_a_measured_zero():
    line = pool_report._line(_World([]), {"players": 1, "pool": 500, "free": 500, "held": 0,
                                          "free_filler": 0, "free_useful": 0, "free_progression": 0})
    assert "solo seed" in line
    assert "sent 0" not in line
