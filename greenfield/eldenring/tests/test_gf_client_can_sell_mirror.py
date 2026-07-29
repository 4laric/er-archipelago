"""`shops._client_can_sell` must mirror the client's `is_synthetic_goods` -- it had drifted.

THE BUG, in game 2026-07-29 (Alaric: "no reason to be doing AP Flower on an ash of war", plus
`?GoodsInfo?` in the item panel).

The synthetic-placeholder floor is GOODS-ONLY. The client says so and always has:

    // Goods-only: a real item in any other category is never synthetic, regardless of how large
    // its id is (e.g. the ~99M NPC weapons).
    pub fn is_synthetic_goods(q) -> bool {
        item_category_of(q) == CATEGORY_GOODS && row_id_of(q) > SYNTHETIC_GOODS_MIN_ID
    }

The world dropped the category condition and applied the floor to EVERY category. Weapon and
protector row ids sit well above it -- Sacrificial Axe is row 14,110,000, Oathseeker Knight Greaves
5,000,300, against a floor of 3,780,000 -- so essentially every weapon and armour piece was reported
unsellable. Each then fell through to the shop_preview override and drew a spare preview row.

Measured on one solo seed: 65 slots consuming spares (the ENTIRE pool), of which only 38% could
carry a description. After the fix: 10 slots, 100% describable.

🛑 `_client_can_sell`'s own docstring says it MIRRORS the client filter, and the module comment says
"the client half is the one that decides, so keep this in step with it". Nothing compared them, so
the mirror drifted and the prose kept claiming it had not. That is what this file is for.
"""
import os
import re
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = find_repo_root(HERE)
_CODEC = os.path.join(_ROOT or "", "from-software-archipelago-clients",
                      "crates", "er-codec", "src", "lib.rs")

GOODS = 0x40000000


@unittest.skipUnless(_ROOT is not None, REPO_ONLY_REASON)
class SyntheticFloorIsGoodsOnly(unittest.TestCase):

    def test_the_python_side_only_applies_the_floor_to_goods(self):
        """Parsed with `ast`, NOT imported.

        The first version of this test did `spec.loader.exec_module` on shops.py, which needs the AP
        env, so it hit its own skipTest and asserted nothing -- I built a dormant gate while fixing
        dormant gates. The rule is structural, so read the structure: the floor comparison must sit
        inside a condition that also tests the GOODS nibble.
        """
        import ast
        path = os.path.join(_ROOT, "greenfield", "eldenring", "features", "shops.py")
        tree = ast.parse(open(path, encoding="utf-8").read())
        fn = next((n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name == "_client_can_sell"), None)
        self.assertIsNotNone(fn, "_client_can_sell is gone -- the mirror's python half moved")

        guarded = unguarded = 0
        for node in ast.walk(fn):
            if not isinstance(node, ast.If):
                continue
            src = ast.dump(node.test)
            if "_SYNTHETIC_GOODS_MIN_ID" not in src:
                continue
            if "_GOODS_NIBBLE" in src or "CATEGORY_GOODS" in src:
                guarded += 1
            else:
                unguarded += 1
        self.assertTrue(guarded or unguarded,
                        "_client_can_sell no longer references the synthetic floor at all -- if the "
                        "rule moved, move this test with it rather than deleting it")
        self.assertEqual(
            unguarded, 0,
            "_client_can_sell applies the synthetic-placeholder floor WITHOUT a goods check. The "
            "floor is goods-only (er_codec::is_synthetic_goods). Applied to every category it "
            "misreports weapons and armour as unsellable -- Sacrificial Axe is row 14,110,000 and "
            "Oathseeker Knight Greaves 5,000,300 against a 3,780,000 floor -- so they draw spare "
            "preview rows and wear the AP flower on an item the client is selling natively.")

    def test_the_rust_side_still_says_goods_only(self):
        """If the CLIENT ever widens its floor, this mirror must be revisited, not silently kept."""
        if not os.path.isfile(_CODEC):
            self.skipTest("client not checked out beside the repo")
        with open(_CODEC, encoding="utf-8") as fh:
            src = fh.read()
        m = re.search(r"pub fn is_synthetic_goods\([^)]*\)\s*->\s*bool\s*\{(.*?)\}", src, re.S)
        self.assertIsNotNone(m, "is_synthetic_goods not found -- the mirror's other half moved")
        body = m.group(1)
        self.assertIn("CATEGORY_GOODS", body,
                      "the client's synthetic floor no longer mentions CATEGORY_GOODS. If it now "
                      "applies to every category, shops._client_can_sell must change WITH it -- "
                      "that divergence is the bug this file exists for.")


if __name__ == "__main__":
    unittest.main()
