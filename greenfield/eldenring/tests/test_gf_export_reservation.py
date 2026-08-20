"""#918's ruling: confine stays 100; a dedicated pass reserves the useful-export share.

The heavyweight acceptance instrument is tools/gf_multiworld_smoke.py (real generations, the
derived-floor guard, CI's regen-and-fill job) -- measured on 2026-08-20: useful items reaching
non-ER partners went 0 -> 983 across the six-gen matrix, pooled useful:filler composition 1.01:1,
so filler_foreign_pct's measured 70 stands. These tests hold the pure halves and the no-op edges
that a full generation cannot isolate.
"""
import unittest

from ..features.export_reservation import eligible_useful, reservation_size


class TestReservationSize(unittest.TestCase):
    def test_the_uniformity_share(self):
        # 40 useful, partner holds a quarter of the open grid -> a quarter of the useful tier.
        self.assertEqual(reservation_size(40, 100, 400), 10)

    def test_rounds_rather_than_truncates(self):
        # foreign_open kept large so the capacity cap (tested below) cannot mask the rounding.
        self.assertEqual(reservation_size(10, 100, 300), 3)   # 3.33 -> 3
        self.assertEqual(reservation_size(10, 100, 400), 2)   # 2.5 -> banker's 2

    def test_capped_by_partner_capacity(self):
        # More share than the partner has open slots: cap, never oversubscribe.
        self.assertEqual(reservation_size(1000, 5, 10), 5)

    def test_zero_edges_are_zero(self):
        self.assertEqual(reservation_size(0, 100, 400), 0)
        self.assertEqual(reservation_size(40, 0, 400), 0)
        self.assertEqual(reservation_size(40, 100, 0), 0)


class _Item:
    def __init__(self, name, player, useful=True, advancement=False):
        self.name, self.player = name, player
        self.useful, self.advancement = useful, advancement


class _Opts:
    class local_items:
        value = {"Held Sword"}


class _MW:
    def __init__(self, pool):
        self.itempool = pool


class _World:
    player = 1
    options = _Opts()

    def __init__(self, pool):
        self.multiworld = _MW(pool)


class TestEligibleUseful(unittest.TestCase):
    def test_the_filter_is_the_documented_one(self):
        pool = [
            _Item("Free Sword", 1),                       # in
            _Item("Held Sword", 1),                       # OUT: local_items (keep_local flows here)
            _Item("Their Sword", 2),                      # OUT: not ours
            _Item("Rune", 1, useful=False),               # OUT: filler
            _Item("Liurnia Lock", 1, advancement=True),   # OUT: progression is the bias levers' job
        ]
        got = [i.name for i in eligible_useful(_World(pool))]
        # WITNESS: the positive case must be present, or every exclusion below is vacuous.
        self.assertEqual(got, ["Free Sword"])
