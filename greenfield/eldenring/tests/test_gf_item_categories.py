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
from BaseClasses import ItemClassification                  # noqa: E402
from worlds.eldenring import item_categories as ic          # noqa: E402
from worlds.eldenring import pool_report                     # noqa: E402
from worlds.eldenring.item_ids import ITEM_CATALOG, GOODS_TYPE  # noqa: E402
from worlds.eldenring.item_ids import KEY_ITEM_GOODS  # noqa: E402
from worlds.eldenring.features import presence_floor as pf  # noqa: E402

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
        # ghost gloveworts and smithing stones are the same category; bell bearings are NOT --
        # boblerrr's "upgrade materials other than bell bearing can be local" is the clause, and
        # since 2026-08-12 the bells say so in their own name rather than by hiding in `key_items`.
        self.assertEqual(ic.category_of("Ghost Glovewort [1]"), "upgrade_materials")
        self.assertEqual(ic.category_of("Smithing Stone [1]"), "upgrade_materials")
        bells = [n for n in ITEM_CATALOG if n.endswith("Bell Bearing")]
        self.assertTrue(bells)
        for b in bells:
            self.assertIn(ic.category_of(b),
                          (ic.UPGRADE_BELLS_CATEGORY, ic.MERCHANT_BELLS_CATEGORY), b)
            self.assertNotEqual(ic.category_of(b), "upgrade_materials", b)


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
    # 🛑 `keep_local: []` IS LOAD-BEARING, and it is not the default (#703 ships the goods umbrella
    # minus runes). This class isolates the RUNE CAP: `test_nothing_else_is_swept_in` asserts the cap
    # holds nothing but runes, and inheriting the shipped default would hand it ~700 held goods to
    # trip over -- the cap would look like it was over-reaching when the categories did it.
    options = {"num_regions": 0, "item_shuffle": True, "keep_local_rune_cap": 3000,
               "keep_local": []}

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


class DefaultsAimAtTheOneToOneMix(WorldTestBase):
    """The shipped locality defaults (#703). This class REPLACED `RuneCapOffByDefault`, whose
    objection was: "a default that quietly localized the whole rune ladder would change every
    existing seed's multiworld shape without anyone asking."

    Alaric asked, 2026-08-15 -- aim the export composition at 1:1 useful:filler -- so the default is
    now deliberate rather than absent. The objection is not discarded, it is SPLIT: the half about
    changing seeds without being asked is answered by the ruling, and the half about localizing the
    WHOLE ladder is still enforced below, because 6250 is a cap and not a switch."""

    game = GAME
    options = {"num_regions": 1, "item_shuffle": True}

    def test_the_shipped_defaults_are_the_measured_recipe(self):
        self.assertEqual(self.world.options.keep_local_rune_cap.value, 12500)
        self.assertEqual(
            set(self.world.options.keep_local.value),
            {"consumables", "cookbooks", "crafting", "crystal_tears",
             "merchant_bells", "other", "upgrade_bells", "upgrade_materials"})

    def test_the_default_set_is_goods_minus_the_three_we_release(self):
        """Pinned against the LIVE umbrella rather than a second copy of the list. `goods` is derived
        from the catalog nibble, so a new goods category tomorrow lands here as a red test asking
        whether it should be held or released -- which is the reviewed diff we want, instead of the
        default silently meaning something new."""
        released = {"runes", "key_items", "spells", "spirit_ashes"}
        self.assertEqual(set(self.world.options.keep_local.value),
                         set(ic.UMBRELLAS["goods"]) - released)
        # WITNESS: the umbrella really does contain what we claim to be subtracting, so the equality
        # above is a subtraction that happened rather than two empty-ish sets agreeing.
        self.assertTrue(released <= set(ic.UMBRELLAS["goods"]))

    def test_the_rune_ladder_is_capped_not_localized(self):
        """🛑 The surviving half of the old objection. Runes are the one large filler category left
        open, which is what makes the cap the fine adjustment on the mix -- if the default held every
        rune, that dial would be dead and the export mix would sit at 2.7:1 instead of 1:1."""
        local = _local(self)
        big = [n for n in ITEM_CATALOG
               if (p := ic.rune_payout(n)) is not None and p > 12500]
        self.assertTrue(big, "no rune pays more than the cap -- the split below proves nothing")
        self.assertFalse([n for n in big if n in local],
                         "runes above the cap must still be free to travel")

    def test_key_items_are_released_or_natural_progression_dies(self):
        """🛑 THE ONE THAT COST A RED SMOKE RUN. `key_items` reads like an obvious thing to hold --
        a Hollow Knight player cannot spend a Stonesword Key -- but the category also carries the
        Great Runes, both Dectus medallions and every Remembrance. Holding it took
        tools/gf_multiworld_smoke.py's natural_progression count from 12 cross-world placements to
        ZERO. Asserted directly, because the next person to read the export table will see key_items
        at 32.3% of everything we send and want to add the line back."""
        self.assertNotIn("key_items", set(self.world.options.keep_local.value))
        local = _local(self)
        runes = [n for n in ic.names_in(["key_items"]) if n.endswith("Great Rune")]
        self.assertTrue(runes, "no Great Runes in key_items -- nothing to protect")
        self.assertFalse([n for n in runes if n in local],
                         "Great Runes must stay free to travel (natural_progression)")

    def test_gear_still_travels(self):
        """The point of the recipe is that weapons, armour and talismans go OUT. If a future edit
        widened the default to `goods` or `everything`, every one of them would be held and the
        partner would receive nothing usable -- the exact defect #703 opened on."""
        local = _local(self)
        for cat in ("weapons", "armor", "talismans"):
            names = ic.names_in([cat])
            self.assertTrue(names, f"{cat} resolved to no items -- nothing to prove")
            self.assertFalse([n for n in names if n in local],
                             f"{cat} must stay free to travel")

    def test_report_counts_the_held_half(self):
        est = pool_report.estimate(self.world)
        self.assertGreater(est["pool"], 0)
        self.assertGreater(est["held"], 0, "the shipped default holds nothing -- it used to be OFF")
        self.assertEqual(est["free"], est["pool"] - est["held"])
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


class CookbooksAreTheirOwnCategory(WorldTestBase):
    """goodsType 1 is an inventory TAB: 96 of its 220 members are crafting cookbooks and the rest
    are gate keys, bell bearings, whetblades and prayerbooks. `cookbooks` peels the 96 off.

    THE ORACLE IS ALREADY IN THE TREE. gen_data.py has dropped cookbooks from `KEY_ITEM_GOODS` by
    name since 2026-07-28 (`_KEY_ITEM_NAME_DROP`), so the shipped generated list is an INDEPENDENT
    witness to the same judgement -- built by a different predicate, in a different repo half, at
    regen time. Asserting the new category against it is what stops two definitions of "cookbook"
    from drifting apart, which is the failure this project keeps having.
    """
    game = GAME
    options = {"num_regions": 1}

    def test_cookbooks_are_exactly_what_the_generated_key_item_list_dropped(self):
        self.assertTrue(KEY_ITEM_GOODS, "item_ids.py must carry KEY_ITEM_GOODS (gen_data.py regen)")
        tab = {n for n in ITEM_CATALOG if GOODS_TYPE.get(n) == 1}
        cookbooks = {n for n in ITEM_CATALOG if ic.category_of(n) == ic.COOKBOOKS_CATEGORY}
        self.assertGreater(len(cookbooks), 90, "witness: the roster is real, not an empty carve")
        self.assertEqual(cookbooks, tab - set(KEY_ITEM_GOODS))
        # ...and the two halves still add up to the tab, so nothing fell down the gap.
        self.assertEqual(len(cookbooks) + len(set(KEY_ITEM_GOODS)), len(tab))

    def test_the_mark_cannot_reach_outside_the_tab(self):
        # The carve is gated on goodsType as well as the name. No catalog item called Cookbook lives
        # anywhere else today; if one ever does, it must not be silently reclassified.
        strays = sorted(n for n in ITEM_CATALOG
                        if "Cookbook" in n and GOODS_TYPE.get(n) != 1)
        self.assertFalse(strays, f"'Cookbook' outside goodsType 1: {strays}")
        marked = [n for n in ITEM_CATALOG if "Cookbook" in n]
        self.assertGreater(len(marked), 90, "witness: the mark matched a real roster")

    def test_key_items_still_means_the_whole_tab_in_a_yaml(self):
        # THE COMPAT GATE. `key_items` is in the shipped release/EldenRing.yaml, so a yaml that says
        # it must keep the 220 it always kept -- splitting a category may not quietly release 96
        # items. Same rule, same fix as the `goods` umbrella one class up.
        tab = {n for n in ITEM_CATALOG if GOODS_TYPE.get(n) == 1}
        self.assertEqual(set(ic.names_in(["key_items"])), tab)
        self.assertIn(ic.COOKBOOKS_CATEGORY, ic.expand(["key_items"]))

    def test_the_narrow_category_and_the_umbrella_answer_different_questions(self):
        # Stated in item_categories and pinned here so it is a decision, not a surprise: the tab
        # minus its carve-outs has no selector of its own, and census() reports the narrow count.
        tab = {n for n in ITEM_CATALOG if GOODS_TYPE.get(n) == 1}
        narrow = {n for n in ITEM_CATALOG if ic.category_of(n) == "key_items"}
        bells = {n for n in ITEM_CATALOG if "Bell Bearing" in n}
        # KEY_ITEM_GOODS is the tab minus cookbooks (gen_data drops those by name). The bells came
        # out on top of that, so the narrow category is the generated list minus them -- expressed
        # against the shipped artifact rather than a typed-in number, so a regen cannot strand it.
        self.assertEqual(narrow, set(KEY_ITEM_GOODS) - bells)
        self.assertTrue(bells & set(KEY_ITEM_GOODS), "witness: the bells were inside KEY_ITEM_GOODS")
        self.assertLess(len(narrow), len(tab))
        self.assertEqual(ic.census()["key_items"], len(narrow))
        self.assertEqual(len(ic.names_in(["key_items"])), len(tab))

    def test_cookbooks_are_selectable_and_ride_the_goods_umbrella(self):
        self.assertIn(ic.COOKBOOKS_CATEGORY, ic.SELECTABLE)
        # `goods` derives its member list from the catalog, so a new goods category joins it for
        # free -- that is the property the umbrella was built to have.
        self.assertIn(ic.COOKBOOKS_CATEGORY, ic.expand(["goods"]))
        self.assertEqual(ic.expand([ic.COOKBOOKS_CATEGORY]), [ic.COOKBOOKS_CATEGORY])


class BellBearingsSplitByWhatTheyUnlock(WorldTestBase):
    """All 48 bell bearings do the same thing -- hand one to the Twin Maiden Husks and stock appears
    -- so the game files them together under goodsType 1 with the gate keys. What appears is not the
    same kind of thing, and that is the split: `upgrade_bells` (13) open the smithing economy,
    `merchant_bells` (35) move a dead merchant's own shelf to the hub.

    🛑 THE ORACLE THAT LOOKED RIGHT AND IS NOT. `greenfield/bell_handins.tsv` is the Maidens' talk
    ESD and would have been the derived predicate -- except it covers 23 of the 48 catalog bells and
    its names do not join the catalog (`Kale's` vs `Kale\u0301s`). Deriving from it files Bone
    Peddler's and Herbalist's as upgrade bells. So the carve is by NAME, and the cross-check is
    features/presence_floor's roster: picked by hand for exactly this economy, maintained in a
    different file, and it must agree.
    """
    game = GAME
    options = {"num_regions": 1}

    def test_the_two_bell_categories_partition_the_bells(self):
        bells = {n for n in ITEM_CATALOG if "Bell Bearing" in n}
        up = {n for n in ITEM_CATALOG if ic.category_of(n) == ic.UPGRADE_BELLS_CATEGORY}
        me = {n for n in ITEM_CATALOG if ic.category_of(n) == ic.MERCHANT_BELLS_CATEGORY}
        self.assertGreater(len(bells), 40, "witness: the bell roster is real")
        self.assertEqual(up | me, bells, "a bell bearing fell outside both bell categories")
        self.assertEqual(up & me, set())
        self.assertGreater(len(up), 10, "witness: the upgrade ladder resolved")

    def test_presence_floors_hand_picked_bells_are_all_upgrade_bells(self):
        # THE CROSS-CHECK. presence_floor guarantees these because a seed without them has an
        # amputated upgrade economy -- the same judgement, made independently, in another file.
        roster_bells = [n for n in pf.ROSTER if "Bell Bearing" in n]
        self.assertGreaterEqual(len(roster_bells), 8, "witness: the roster still carries bells")
        for n in roster_bells:
            self.assertEqual(ic.category_of(n), ic.UPGRADE_BELLS_CATEGORY, n)

    def test_the_smithing_ladders_are_all_there_and_no_merchant_joined_them(self):
        up = {n for n in ITEM_CATALOG if ic.category_of(n) == ic.UPGRADE_BELLS_CATEGORY}
        for mark in ("Smithing-Stone Miner's", "Somberstone Miner's",
                     "Glovewort Picker's", "Ghost-Glovewort Picker's"):
            self.assertTrue([n for n in up if mark in n], f"no {mark} bell in upgrade_bells")
        for decoy in ("Bone Peddler's Bell Bearing", "Herbalist's Bell Bearing"):
            if decoy in ITEM_CATALOG:
                self.assertEqual(ic.category_of(decoy), ic.MERCHANT_BELLS_CATEGORY, decoy)

    def test_an_upgrade_bell_is_useful_and_a_merchant_bell_is_not(self):
        self.assertEqual(ic.CATEGORY_CLASS[ic.UPGRADE_BELLS_CATEGORY], ic.USEFUL)
        self.assertEqual(ic.CATEGORY_CLASS[ic.MERCHANT_BELLS_CATEGORY], ic.FILLER)
        sample = sorted(n for n in ITEM_CATALOG
                        if ic.category_of(n) == ic.UPGRADE_BELLS_CATEGORY)
        self.assertTrue(sample, "witness: upgrade_bells is not empty")
        for n in sample:
            self.assertEqual(self.world.create_item(n).classification,
                             ItemClassification.useful, n)

    def test_key_items_still_means_the_whole_tab_after_a_second_split(self):
        # The umbrella covers FOUR pieces now. Same compat gate as the cookbooks split.
        tab = {n for n in ITEM_CATALOG if GOODS_TYPE.get(n) == 1}
        self.assertEqual(set(ic.names_in(["key_items"])), tab)
        for cat in (ic.COOKBOOKS_CATEGORY, ic.UPGRADE_BELLS_CATEGORY, ic.MERCHANT_BELLS_CATEGORY):
            self.assertIn(cat, ic.expand(["key_items"]), cat)

    def test_the_bell_bearings_umbrella_is_both_halves(self):
        bells = {n for n in ITEM_CATALOG if "Bell Bearing" in n}
        self.assertEqual(set(ic.names_in(["bell_bearings"])), bells)
        self.assertIn("bell_bearings", ic.SELECTABLE)
