"""The difficulty FLOOR, gated on a REAL generated world: `completion_scaling_floor` must reach the
wire in the unit the client parses, and its two same-named slot_data keys must stay in different
unit spaces.

Companion to `test_gf_scaling_ladder_mirror.py`, which owns the cross-repo half (the ladder mirror
and the round-trip against the client's own source) and runs standalone without AP. This file owns
the half that needs a world: the option is reachable from yaml, and the value survives
`core._options_echo` end to end.

THE BUG (found 2026-07-27, latent since 2026-07-06). The world documented
`completion_scaling_floor` as "a percent of max" and emitted the raw int; the client reads it as an
HP MULTIPLIER (`er-logic/scaling.rs floor_tier_from_multiplier`, first tier whose `hp >= value`) over
a ladder topping out at 3.703. So anything above 3 selected the TOP tier -- `25` would have pinned
every enemy in the game to 3.70x HP from the moment the player left Roundtable. Never shipped only
because the option was frozen at 0. Full postmortem in scaling_ladder.py.

WHY BOTH KEYS EXIST. `completion_scaling_floor` appears TWICE in slot_data by design:
`sd["completion_scaling_floor"]` is the player-facing PERCENT (informational / spoiler-side) and
`sd["options"]["completion_scaling_floor"]` is the MULTIPLIER the client actually reads. Same name,
two unit spaces. That is a trap for a future tidy-up, so it is asserted here rather than left to be
rediscovered (CONTRIBUTING rule 3: name the space wherever two components exchange a value).
"""
import pytest

pytest.importorskip("worlds.eldenring")

from worlds.eldenring import defaults, scaling_ladder  # noqa: E402
from worlds.eldenring.features import scaling as sc  # noqa: E402

GAME = "Elden Ring"


def _floor_tier(floor_mult, ladder=scaling_ladder.SCALING_HP_LADDER):
    """The client's search, restated (er-logic/scaling.rs floor_tier_from_multiplier). The Rust
    source is pinned to this shape by test_gf_scaling_ladder_mirror."""
    for i, hp in enumerate(ladder):
        if hp >= floor_mult:
            return i
    return len(ladder) - 1


def test_option_is_reachable_from_yaml():
    assert "completion_scaling_floor" not in defaults.FROZEN_OPTIONS, (
        "completion_scaling_floor is frozen again -- the difficulty floor is unreachable from yaml, "
        "and the percent->multiplier conversion it needs is now dead code.")
    assert sc.Scaling.OPTIONS["completion_scaling_floor"] is sc.CompletionScalingFloor


def test_range_spans_the_whole_ladder_and_defaults_to_no_change():
    # The old range_end of 50 was written against the percent reading and never revisited; under the
    # real (multiplier) semantics it could not express "floor at the top tier" meaningfully at all.
    assert sc.CompletionScalingFloor.range_end == 100
    assert sc.CompletionScalingFloor.range_start == 0
    assert sc.CompletionScalingFloor.default == 0, "new options default to no-change"


def test_docstring_describes_the_real_scale():
    """CONTRIBUTING options hygiene: "a docstring that lies is a bug" -- and this option's docstring
    is the specific one that lied (it said "percent of max" of an unstated quantity, while the wire
    carried an HP multiplier). It feeds the yaml reference layer, so pin that it names the units."""
    doc = sc.CompletionScalingFloor.__doc__.lower()
    assert "hp" in doc, "the docstring must say what the scale multiplies (enemy HP)"
    assert "3.70" in doc, "the docstring must name the top of the ladder, not just 'max'"


@pytest.mark.parametrize("pct,expect_top", [(0, False), (25, False), (50, False), (100, True)])
def test_emitted_multiplier_resolves_to_a_sane_tier(pct, expect_top):
    top = len(scaling_ladder.SCALING_HP_LADDER) - 1
    tier = _floor_tier(scaling_ladder.floor_multiplier(pct))
    assert tier == round(pct / 100 * top)
    assert (tier == top) is expect_top, (
        "completion_scaling_floor: %d %s the top tier" % (pct, "should reach" if expect_top
                                                          else "must NOT reach"))


class TestSlotDataUnits:
    """END TO END on a generated world -- the composition, not the pieces. CONTRIBUTING rule 11: a
    pipeline of individually correct stages can still drop the exact case it was built for, so the
    motivating value (25) is asserted after the whole `fill_slot_data` path, by name."""

    @staticmethod
    def _slot_data(pct):
        WorldTestBase = pytest.importorskip("test.bases").WorldTestBase

        class _T(WorldTestBase):
            game = GAME
            options = {"completion_scaling_floor": pct}

        t = _T()
        t.setUp()
        try:
            return t.world.fill_slot_data()
        finally:
            t.tearDown()

    def test_top_level_is_the_percent_and_nested_is_the_multiplier(self):
        pct = 25
        sd = self._slot_data(pct)
        top = len(scaling_ladder.SCALING_HP_LADDER) - 1

        assert sd["completion_scaling_floor"] == pct, (
            "the top-level legacy copy must stay the player-facing PERCENT")

        nested = sd["options"]["completion_scaling_floor"]
        assert nested == scaling_ladder.floor_multiplier(pct), (
            "options.completion_scaling_floor must be the HP MULTIPLIER the client parses")
        assert nested != pct, (
            "the two same-named keys collapsed to a single unit -- that IS the bug. Top-level is "
            "the percent; options.* is the multiplier. See scaling_ladder.floor_multiplier.")
        assert _floor_tier(nested) < top, (
            "a mid-range floor reached the TOP tier through the real slot_data path -- the "
            "conversion is not being applied where it matters.")

    def test_default_seed_wire_is_unchanged(self):
        """A yaml that never mentions the option must emit exactly what it emitted before the option
        was reachable: the int 0, in both places."""
        sd = self._slot_data(0)
        assert sd["completion_scaling_floor"] == 0
        nested = sd["options"]["completion_scaling_floor"]
        assert nested == 0 and isinstance(nested, int), (
            "default seed emitted %r -- default slot_data must not change" % (nested,))

    def test_max_floor_reaches_the_top_of_the_ladder(self):
        sd = self._slot_data(100)
        nested = sd["options"]["completion_scaling_floor"]
        assert nested == scaling_ladder.SCALING_HP_LADDER[-1]
        assert _floor_tier(nested) == len(scaling_ladder.SCALING_HP_LADDER) - 1
