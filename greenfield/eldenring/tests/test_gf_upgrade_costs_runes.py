"""`tools/upgrade_costs.RUNE_VALUE` must equal what the params publish.

WHY (#749, 2026-08-16). It was a hand-written table headed "KNOWN constants (no source file)", and
7 of its 22 rows disagreed with the params while the source file it said did not exist
(`shop_stock_data.RUNE_PAYOUT`) sat two directories up:

    Hero's Rune [1]-[5]     2,500 / 3,800 / 5,000 / 6,250 / 7,500   vs  15,000 - 35,000
    Shadow Realm Rune [1]     1,000                                 vs   7,500
    Shadow Realm Rune [2]     1,600                                 vs  10,000

Those five Hero's figures are Golden Rune [7]/[9]/[10]/[11]/[12]'s payouts, so whatever produced the
table was reading down the wrong column -- the same shape as the off-by-one the `KeepLocalRuneCap`
option help carried (#747), which is why the two were plausibly one mistake made twice. It also
omitted nine catalog runes outright. The other 15 rows were correct, which is what let it survive.

🛑 THIS TEST TYPES NO PAYOUTS. It asks the params, exactly as #747's prose gate does. A test
carrying the right 31 numbers would just be the next place for them to drift, and the whole defect
was a second copy of a number that already had a home.

Not a skip-bearing suite: `tools/` lives inside the package, so `gf_test.py` installs it beside the
world and this runs in the `tests` job like any other.
"""
import importlib.util
import os
import sys
import unittest

import pytest

pytest.importorskip("worlds.eldenring")
from worlds.eldenring.item_ids import ITEM_CATALOG              # noqa: E402
from worlds.eldenring.shop_stock_data import RUNE_PAYOUT        # noqa: E402
import worlds.eldenring as _pkg                                 # noqa: E402

_GOODS_NIBBLE, _ROW_MASK = 0x40000000, 0x0FFFFFFF


def _upgrade_costs():
    """Load it the way its only other test does -- by path. `tools/` is a script package; importing
    it as `worlds.eldenring.tools.upgrade_costs` would run its `sys.path` surgery under a different
    name and is not how the analyzer is used."""
    path = os.path.join(os.path.dirname(os.path.abspath(_pkg.__file__)), "tools", "upgrade_costs.py")
    assert os.path.isfile(path), "tools/upgrade_costs.py is not installed beside the world: %s" % path
    spec = importlib.util.spec_from_file_location("_er_upgrade_costs_runes", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _params_say():
    return {name: int(RUNE_PAYOUT[full & _ROW_MASK])
            for name, full in ITEM_CATALOG.items()
            if (full & 0xF0000000) == _GOODS_NIBBLE and (full & _ROW_MASK) in RUNE_PAYOUT}


class UpgradeCostsRuneValues(unittest.TestCase):

    def test_every_row_matches_the_params(self):
        want, got = _params_say(), _upgrade_costs().RUNE_VALUE
        # WITNESS: an equality between two empty dicts is not a pass. The base game alone ships 21
        # money runes; a corpus that has collapsed is a broken derivation, not a clean one.
        self.assertGreater(len(want), 20,
                           "only %d rune(s) derived from the params -- RUNE_PAYOUT/ITEM_CATALOG is "
                           "not being read, and this gate would pass vacuously" % len(want))
        wrong = {n: (got[n], want[n]) for n in want if n in got and got[n] != want[n]}
        self.assertFalse(wrong, "RUNE_VALUE disagrees with the params on %d row(s): %s"
                                % (len(wrong), sorted(wrong.items())[:5]))

    def test_no_rune_is_missing(self):
        """The hand-list omitted nine, including every Shadow Realm Rune above [2]. A solver that
        spends a multiset against a cost cannot see the difference between 'worth nothing' and
        'not in the table' unless the table is complete."""
        want, got = _params_say(), _upgrade_costs().RUNE_VALUE
        # WITNESS (test_gf_vacuous_pass ratchet): "nothing missing" is only a claim if there was a
        # corpus to miss. Asserted per-test because the scan reads one test at a time.
        self.assertGreater(len(want), 20, "the params corpus collapsed (%d runes)" % len(want))
        missing = sorted(set(want) - set(got))
        self.assertFalse(missing, "RUNE_VALUE omits %d rune(s): %s" % (len(missing), missing))

    def test_no_extra_names(self):
        """The other direction: a name the params do not price is either a typo or a non-rune, and
        both are worth a red rather than a silent zero."""
        want, got = _params_say(), _upgrade_costs().RUNE_VALUE
        self.assertGreater(len(got), 20, "RUNE_VALUE collapsed (%d rows) -- 'no extras' would be "
                                         "vacuous over an empty table" % len(got))
        extra = sorted(set(got) - set(want))
        self.assertFalse(extra, "RUNE_VALUE prices %d item(s) the params do not: %s" % (len(extra), extra))

    def test_the_module_still_imports_without_the_generated_data(self):
        """🛑 THE PROPERTY THE DERIVATION MUST NOT COST US. upgrade_costs.py degrades to built-in
        defaults when `upgrade_costs_data` is absent, on purpose, so the analyzer imports anywhere.
        `_derive_rune_values` catches ImportError and returns {} for the same reason -- an empty
        table, not a partial hand-list, because the solvers can see a KeyError and cannot see a
        silent zero."""
        uc = _upgrade_costs()
        self.assertTrue(callable(uc._derive_rune_values))
        self.assertIsInstance(uc.RUNE_VALUE, dict)
        # The fallback path is reachable and returns the empty table rather than raising.
        saved = dict(sys.modules)
        try:
            for name in ("shop_stock_data", "item_ids"):
                sys.modules[name] = None            # force `from X import Y` to raise ImportError
            self.assertEqual(uc._derive_rune_values(), {},
                             "the no-generated-data path must degrade to {}, not raise or guess")
        finally:
            sys.modules.clear()
            sys.modules.update(saved)


if __name__ == "__main__":
    unittest.main()
