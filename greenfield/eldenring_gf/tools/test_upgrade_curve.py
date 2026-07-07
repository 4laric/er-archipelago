"""Unit tests for the upgrade-curve solvers + a synthetic per-sphere run. Pure Python (no AP)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import upgrade_costs as uc
import analyze_upgrade_curve as az


def test_standard_count_accurate_vanilla_ladder():
    # +1/+2/+3 cost Smithing Stone [1] x2/x4/x6 -> 12 total for +3; 11 stops at +2.
    assert uc.max_standard_level({"Smithing Stone [1]": 12}) == 3
    assert uc.max_standard_level({"Smithing Stone [1]": 11}) == 2
    assert uc.max_standard_level({"Smithing Stone [1]": 0}) == 0
    # crossing a tier needs the next stone: 12x[1] + nothing -> can't reach +4
    assert uc.max_standard_level({"Smithing Stone [1]": 100}) == 3


def test_flatten_reduces_standard_cost():
    # flatten=1 -> each level costs 1 of its tier stone; +3 now needs only 3x[1].
    assert uc.max_standard_level({"Smithing Stone [1]": 3}, stones_per_level=1) == 3
    assert uc.max_standard_level({"Smithing Stone [1]": 2}, stones_per_level=1) == 2
    # flatten never makes it EASIER-than-real to go further than vanilla with the same stones
    have = {f"Smithing Stone [{i}]": 6 for i in range(1, 9)}
    assert uc.max_standard_level(have, stones_per_level=1) >= uc.max_standard_level(have)


def test_full_standard_needs_ancient_dragon():
    have = {f"Smithing Stone [{i}]": 12 for i in range(1, 9)}
    assert uc.max_standard_level(have) == 24          # no Ancient Dragon -> caps at +24
    have["Ancient Dragon Smithing Stone"] = 1
    assert uc.max_standard_level(have) == 25


def test_somber_one_per_level():
    have = {f"Somber Smithing Stone [{i}]": 1 for i in range(1, 10)}
    assert uc.max_somber_level(have) == 9             # missing Ancient Dragon Somber -> +9
    have["Somber Ancient Dragon Smithing Stone"] = 1
    assert uc.max_somber_level(have) == 10
    # a gap in the tier chain blocks progress (needs [3] specifically for +3)
    assert uc.max_somber_level({"Somber Smithing Stone [1]": 1, "Somber Smithing Stone [2]": 1}) == 2


def test_step_based_curves_monotone():
    for fn in (uc.max_flask_charges, uc.max_flask_potency, uc.max_scadutree, uc.max_revered):
        vals = [fn(n) for n in range(0, 60)]
        assert vals == sorted(vals), f"{fn.__name__} must be non-decreasing"
    # flask charges report TOTAL (base + bought); the others start at 0.
    assert uc.max_flask_charges(0) == uc.FLASK_BASE_CHARGES
    for fn in (uc.max_flask_potency, uc.max_scadutree, uc.max_revered):
        assert fn(0) == 0


def test_character_level_from_runes():
    assert uc.max_character_level(0, start_level=1) == 1
    lo = uc.max_character_level(10_000, start_level=1)
    hi = uc.max_character_level(1_000_000, start_level=1)
    assert 1 < lo < hi
    assert uc.runes_from_items({"Golden Rune [13]": 3}) == 30000


def test_synthetic_sphere_run_is_cumulative_monotone():
    # sphere 0: two [1]; sphere 1: two more [1] (enough for +2); sphere 2: a [2] batch + a seed
    spheres = [
        ["Smithing Stone [1]", "Smithing Stone [1]"],
        ["Smithing Stone [1]", "Smithing Stone [1]", "Golden Seed"],
        ["Smithing Stone [2]"] * 2 + ["Smithing Stone [1]"] * 8 + ["Golden Seed"],
    ]
    rows = az.curves_for_seed(spheres, stones_per_level=None, start_level=1)
    assert len(rows) == 3
    for c in ("standard", "flask_charges", "level"):
        seq = [r[c] for r in rows]
        assert seq == sorted(seq), f"{c} must be non-decreasing across spheres: {seq}"
    assert rows[0]["standard"] == 1          # 2x[1] -> +1
    assert rows[-1]["standard"] >= 4          # cumulative 12x[1] + 6x[2] -> at least +4
    assert rows[-1]["flask_charges"] > uc.FLASK_BASE_CHARGES   # two Golden Seeds -> above base


def test_analyze_aggregates_across_seeds():
    dumps = [
        ("seedA", {"P": [["Smithing Stone [1]"] * 12, ["Golden Seed"]]}),
        ("seedB", {"P": [["Smithing Stone [1]"] * 2, ["Golden Seed", "Golden Seed"]]}),
    ]
    agg, maxs = az.analyze(dumps, player=None, stones_per_level=None, start_level=1)
    assert maxs == 2
    # sphere 0 standard: seedA (12x[1]) -> +3, seedB (2x[1]) -> +1
    assert sorted(agg["standard"][0]) == [1, 3]


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([os.path.abspath(__file__), "-q"]))
