"""Host tests for shop_coloring.color_spare_rows (issue #937). Pure module, no AP imports.

THE INVARIANT UNDER TEST: no two slots visible in one shop menu share a spare-pool color, and a
private (non-repaintable-menu) slot's color is touched by nobody else. The MOTIVATING CASE is the
real corpus shape: the Twin Maiden re-sell menu holds 31 checks, Enia's transposition menu 51, the
pool 79 -- the old first-come draw parked hundreds of slots on one shared row.
"""
import importlib.util
import os
import unittest

# importlib-load by path (the test_gf_data.py pattern): eldenring/__init__ pulls AP imports this
# AP-free test must not need.
_PATH = os.path.join(os.path.dirname(__file__), "..", "shop_coloring.py")
_spec = importlib.util.spec_from_file_location("shop_coloring_under_test", _PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
color_spare_rows = _mod.color_spare_rows


def _reg(a, b):
    return ("OpenRegularShop", a, b)


def _enia(a, b):
    return ("OpenTranspositionShop", a, b)


class RepaintableColoring(unittest.TestCase):
    def test_same_menu_slots_never_share(self):
        scopes = [_reg(100, 124)]
        slots = [(f"s{i}", [100 + i]) for i in range(10)]
        colors, overflow = color_spare_rows(slots, scopes, 40)
        self.assertEqual(overflow, [])
        self.assertEqual(len(set(colors.values())), 10, "one menu, all distinct")

    def test_disjoint_menus_reuse_colors(self):
        # THE POINT OF #937: two merchants' shelves may share rows because the client repaints at
        # open. 60 slots over two disjoint regular menus must fit in far fewer than 60 colors.
        scopes = [_reg(100, 199), _reg(300, 399)]
        slots = [(f"a{i}", [100 + i]) for i in range(30)] + \
                [(f"b{i}", [300 + i]) for i in range(30)]
        colors, overflow = color_spare_rows(slots, scopes, 40)
        self.assertEqual(overflow, [])
        self.assertEqual(len(set(colors.values())), 30, "colors reused across menus")
        for menu in ("a", "b"):
            menu_colors = [c for k, c in colors.items() if k.startswith(menu)]
            self.assertEqual(len(set(menu_colors)), 30, "still distinct within each menu")

    def test_multi_row_slot_conflicts_in_every_menu_it_appears_in(self):
        # A stock flag can sit on several rows (SHOP_ROW_IDS '7770013': Kale's row + the Twin
        # Maiden re-sell row). Its color must clash with BOTH menus' occupants.
        scopes = [_reg(100, 124), _reg(200, 224)]
        slots = [("both", [100, 200]), ("kale", [101]), ("twin", [201])]
        colors, _ = color_spare_rows(slots, scopes, 10)
        self.assertNotEqual(colors["both"], colors["kale"])
        self.assertNotEqual(colors["both"], colors["twin"])

    def test_overlapping_ranges_constrain_jointly(self):
        # Kale's over-wide range covers other merchants' rows; slots under both ranges are
        # co-visible in the wide menu and must all differ there.
        scopes = [_reg(100, 199), _reg(150, 249)]
        slots = [("w", [120]), ("x", [160]), ("y", [170]), ("z", [230])]
        colors, _ = color_spare_rows(slots, scopes, 10)
        self.assertEqual(len({colors["x"], colors["y"], colors["w"]}), 3)
        self.assertEqual(len({colors["x"], colors["y"], colors["z"]}), 3)


class PrivateColoring(unittest.TestCase):
    def test_non_repaintable_menu_slots_get_untouched_colors(self):
        scopes = [_reg(100, 199), _enia(300, 399)]
        slots = [(f"r{i}", [100 + i]) for i in range(5)] + \
                [(f"e{i}", [300 + i]) for i in range(5)]
        colors, overflow = color_spare_rows(slots, scopes, 40)
        self.assertEqual(overflow, [])
        repaint = {c for k, c in colors.items() if k.startswith("r")}
        private = {c for k, c in colors.items() if k.startswith("e")}
        self.assertEqual(len(private), 5, "each private slot has its own color")
        self.assertFalse(repaint & private, "a private color is touched by NOBODY else")

    def test_a_slot_in_both_menu_kinds_is_private(self):
        # Its Enia appearance cannot be repainted, so its baseline label must stand alone.
        scopes = [_reg(100, 199), _enia(150, 249)]
        slots = [("dual", [160]), ("reg", [110])]
        colors, _ = color_spare_rows(slots, scopes, 10)
        self.assertNotEqual(colors["dual"], colors["reg"])

    def test_rangeless_rows_bucket_per_block_and_are_private(self):
        # No harvested scope: same block => assumed same shelf => distinct; and never repaintable.
        slots = [("m1", [900001]), ("m2", [900002]), ("far", [1600101])]
        colors, overflow = color_spare_rows(slots, [], 10)
        self.assertEqual(overflow, [])
        self.assertNotEqual(colors["m1"], colors["m2"])
        self.assertEqual(len(set(colors.values())), 3, "private slots never share, even cross-block")


class Degradation(unittest.TestCase):
    def test_private_overflow_parks_on_the_shared_last_color(self):
        scopes = [_enia(100, 199)]
        slots = [(f"e{i}", [100 + i]) for i in range(8)]
        colors, overflow = color_spare_rows(slots, scopes, 5)
        # 4 usable colors (last reserved for overflow), 8 slots -> 4 colored, 4 overflow
        self.assertEqual(len(colors), 4)
        self.assertEqual(len(overflow), 4)
        self.assertNotIn(4, colors.values(), "the last color is the overflow row, never assigned")

    def test_repaintables_are_never_starved_by_privates(self):
        # 30 privates then a busy regular menu, pool 20: privates must NOT eat the colors the
        # repaintable menu needs -- repaintables are colored first by construction.
        scopes = [_reg(100, 124), _enia(300, 399)]
        slots = [(f"e{i}", [300 + i]) for i in range(30)] + \
                [(f"r{i}", [100 + i]) for i in range(10)]
        colors, overflow = color_spare_rows(slots, scopes, 20)
        r_colors = [c for k, c in colors.items() if k.startswith("r")]
        self.assertEqual(len(r_colors), 10, "every repaintable slot colored")
        self.assertEqual(len(set(r_colors)), 10)
        self.assertTrue(all(k.startswith("e") for k in overflow), "only privates degraded")

    def test_zero_pool_returns_everything_as_overflow(self):
        colors, overflow = color_spare_rows([("a", [1]), ("b", [2])], [], 0)
        self.assertEqual(colors, {})
        self.assertEqual(overflow, ["a", "b"])


class Determinism(unittest.TestCase):
    def test_same_input_same_output(self):
        scopes = [_reg(100, 149), _enia(150, 249), _reg(200, 299)]
        slots = [(f"s{i}", [95 + i * 7]) for i in range(30)]
        first = color_spare_rows(slots, scopes, 25)
        for _ in range(3):
            self.assertEqual(color_spare_rows(slots, scopes, 25), first)

    def test_output_order_is_input_order(self):
        scopes = [_reg(100, 199)]
        slots = [("z", [101]), ("a", [102]), ("m", [103])]
        colors, _ = color_spare_rows(slots, scopes, 10)
        self.assertEqual(list(colors), ["z", "a", "m"])


class CorpusShape(unittest.TestCase):
    """The real proportions: busiest regular menu 31, Enia 51, pool 79 minus a lock head."""

    def test_the_measured_corpus_shape_colors_within_pool(self):
        scopes = [_reg(101800, 101897), _reg(100350, 100399), _reg(102250, 102289),
                  _enia(101898, 101949)]
        slots = ([(f"t{i}", [101800 + i]) for i in range(31)] +      # Twin Maiden re-sell
                 [(f"n{i}", [100350 + i]) for i in range(29)] +      # nomad
                 [(f"d{i}", [102250 + i]) for i in range(25)] +      # DLC merchant
                 [(f"enia{i}", [101898 + i]) for i in range(20)])    # Enia (private)
        colors, overflow = color_spare_rows(slots, scopes, 74)       # 79 pool minus a 5-lock head
        self.assertEqual(overflow, [])
        repaint_max = max(c for k, c in colors.items() if not k.startswith("enia"))
        self.assertLess(repaint_max, 31, "repaintable watermark = the busiest single menu")
        self.assertEqual(len({c for k, c in colors.items() if k.startswith("enia")}), 20)


if __name__ == "__main__":
    unittest.main()
