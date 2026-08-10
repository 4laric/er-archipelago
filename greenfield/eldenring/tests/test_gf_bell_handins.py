"""The bell -> merchant table, re-derived rather than trusted (er-archipelago#325).

`features/merchant_bells.py` turns a shop open into ONE event-flag write, and the whole feature
rests on `greenfield/bell_handins.tsv` being right about which flag belongs to which merchant. A
wrong row here does not fail loudly: it hands the player a DIFFERENT merchant's shelf at the Twin
Maidens and nothing anywhere says so. So the claims the feature makes are re-checked here against
data the feature does not own.

⭐ THE MOTIVATING CASE, as a test (CONTRIBUTING rule 11). boblerrr asked for bell bearings on first
merchant interaction. The client keys that off the `ShopLineupParam` range the game hands it when
the buy menu opens -- so the load-bearing claim is *"every range in this table is a range a real
merchant's own talk script opens"*, and `greenfield/esd_gates.tsv` (mined independently, from the
MERCHANTS' scripts rather than the Maidens') is the witness. It was 38 of 38 exact when the table
was cut; anything less means a merchant moved and the feature would silently stop firing for them.
"""
import csv
import os
import unittest

# Both TSVs live beside the package in the source tree and are copied INTO it by
# tools/gf_test.py's `*.tsv` glob, which is the run CI does. Resolve from either -- first existing
# wins. Hardcoding one path makes the gate pass in the dev tree and vanish in CI.
_HERE = os.path.dirname(os.path.abspath(__file__))
_GF_PKG = os.path.dirname(_HERE)
_GREENFIELD = os.path.dirname(_GF_PKG)


def _tsv(name):
    return next((p for p in (os.path.join(_GF_PKG, name), os.path.join(_GREENFIELD, name))
                 if os.path.isfile(p)), os.path.join(_GF_PKG, name))


def _rows(name):
    with open(_tsv(name), encoding="utf-8-sig") as fh:
        lines = [l for l in fh if not l.startswith("#")]
    return list(csv.DictReader(lines, delimiter="\t"))


# The Twin Maidens' OWN buy menu. It is the range the 2026-08-08 ESD probe actually observed
# (`cmd 22 args [101800, 101897]`), so it is the one open that must resolve to no bell -- otherwise
# standing at the hub would hand in whatever it collided with.
_TWIN_MAIDENS_RANGE = (101800, 101897)

# The twelve bells that release rows inside block 1018 by eventFlag_forRelease instead of adding a
# menu entry: the four peddlers and eight DLC sellers. They have no shop range, and the table must
# NOT invent one for them -- pinned by flag so a future widening has to argue with this list.
_TRANCHE_ONLY_BELLS = {
    11109745, 11109746, 11109747, 11109748,          # Bone / Meat / Medicine / Gravity Stone
    11109792, 11109793, 11109794, 11109795,          # Herbalist / Mushroom-Seller [1][2] / Grease
    11109796, 11109797, 11109798, 11109799,          # Mold / Igon / Spellmachinist / String-Seller
}


class TestBellHandins(unittest.TestCase):

    def setUp(self):
        self.rows = _rows("bell_handins.tsv")
        self.assertTrue(self.rows,
                        "bell_handins.tsv missing/empty -- this gate degrades SILENTLY without it")

    def test_the_columns_the_generator_reads_are_present(self):
        """tools/gen_merchant_bells.py splits on these five; a rename would bake a wrong table."""
        for col in ("handin_flag", "bell_goods_id", "bell_name", "shop_begin", "shop_end"):
            self.assertIn(col, self.rows[0], f"bell_handins.tsv lost the {col} column")

    def test_every_range_is_one_a_merchants_own_talk_opens(self):
        """THE load-bearing claim. esd_gates.tsv is mined from the MERCHANTS' scripts; this table
        is mined from the Twin Maidens'. They must agree about every range, or the client is
        watching for an open that never happens."""
        merchant_ranges = {(int(r["shop_begin"]), int(r["shop_end"]))
                           for r in _rows("esd_gates.tsv")}
        self.assertTrue(merchant_ranges, "esd_gates.tsv missing/empty -- cannot witness anything")
        missing = [(r["bell_name"], r["shop_begin"], r["shop_end"]) for r in self.rows
                   if (int(r["shop_begin"]), int(r["shop_end"])) not in merchant_ranges]
        self.assertEqual([], missing,
                         "no merchant talk opens these ranges, so the bell would never be handed in")

    def test_the_ranges_are_pairwise_disjoint(self):
        """The client looks a bell up BY the range it observed. Overlapping ranges make that
        ambiguous, and `bell_for_range` would answer with whichever one sorted first."""
        spans = sorted((int(r["shop_begin"]), int(r["shop_end"])) for r in self.rows)
        for (alo, ahi), (blo, bhi) in zip(spans, spans[1:]):
            self.assertLess(ahi, blo, f"ranges {alo}..{ahi} and {blo}..{bhi} overlap")

    def test_the_twin_maidens_own_shelf_is_not_a_merchant(self):
        spans = {(int(r["shop_begin"]), int(r["shop_end"])) for r in self.rows}
        # Witness: without this the assertions below pass just as happily on an empty table, which
        # is the failure mode test_gf_vacuous_pass exists to ratchet down.
        self.assertTrue(spans, "no ranges to check -- this gate would pass vacuously")
        lo, hi = _TWIN_MAIDENS_RANGE
        for alo, ahi in spans:
            self.assertFalse(alo <= lo and hi <= ahi,
                             f"the Maidens' own shelf {lo}..{hi} sits inside bell range {alo}..{ahi}")

    def test_the_tranche_only_bells_are_absent(self):
        """They unlock stock by eventFlag_forRelease and have no merchant range. Guessing one would
        hand the player someone else's shelf -- see tools/datamine_bell_handins.py for why the
        obvious goods-set join resolves only 4 of 12 and two of those are coincidence."""
        emitted = {int(r["handin_flag"]) for r in self.rows}
        self.assertTrue(emitted, "no flags to check -- this gate would pass vacuously")
        self.assertEqual(set(), emitted & _TRANCHE_ONLY_BELLS)

    def test_every_name_is_ascii(self):
        """The name is rendered by the GAME's font in a toast, which has no glyph for non-ASCII.
        The datamine folds `Kale`; this is the gate that keeps the fold honest."""
        for r in self.rows:
            self.assertTrue(r["bell_name"].isascii(), f"{r['bell_name']!r} is not ASCII")
            self.assertTrue(r["bell_name"].strip(), "a bell with no name would toast as blank")

    def test_the_flags_are_in_the_twin_maiden_hand_in_band(self):
        """11109710.. (base) and 11109790.. (DLC) are the two runs the Maidens' ESD writes. A flag
        outside them is not a hand-in and writing it would set something unrelated in the save."""
        for r in self.rows:
            self.assertTrue(11109710 <= int(r["handin_flag"]) <= 11109799,
                            f"{r['bell_name']}: flag {r['handin_flag']} is not a hand-in flag")


class TestMerchantBellsOption(unittest.TestCase):

    def test_the_option_is_declared_and_defaults_off(self):
        """An OFF default is what lets this ship without a lockstep client: an absent key parses
        false, so a seed rolled today is unchanged."""
        from ..features.merchant_bells import MerchantBellsFeature, MerchantBellsOnTalk
        self.assertIn("merchant_bells_on_talk", MerchantBellsFeature.OPTIONS)
        self.assertEqual(0, MerchantBellsOnTalk.default)

    def test_the_handshake_tag_matches_the_contract_key(self):
        """OPTIONS_SUBKEYS is not folded into CONTRACT_HASH, so the tag is the ONLY thing stopping
        an older client reporting VERSION: OK and then never reading the key."""
        from ..features.merchant_bells import CLIENT_FEATURE_TAG
        from ..contract import OPTIONS_SUBKEYS
        self.assertEqual("merchant_bells_on_talk", CLIENT_FEATURE_TAG)
        self.assertIn(CLIENT_FEATURE_TAG, [k.name for k in OPTIONS_SUBKEYS])


if __name__ == "__main__":
    unittest.main()
