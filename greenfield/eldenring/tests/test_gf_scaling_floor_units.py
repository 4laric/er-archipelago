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
    assert "minimum_enemy_difficulty" not in defaults.FROZEN_OPTIONS, (
        "minimum_enemy_difficulty is frozen -- the difficulty floor is unreachable from yaml, "
        "and the percent->multiplier conversion it needs is now dead code.")
    assert sc.Scaling.OPTIONS["minimum_enemy_difficulty"] is sc.MinimumEnemyDifficulty


def test_range_spans_the_whole_ladder_and_defaults_to_no_change():
    # The old range_end of 50 was written against the percent reading and never revisited; under the
    # real (multiplier) semantics it could not express "floor at the top tier" meaningfully at all.
    assert sc.MinimumEnemyDifficulty.range_end == 100
    assert sc.MinimumEnemyDifficulty.range_start == 0
    assert sc.MinimumEnemyDifficulty.default == 0, "new options default to no-change"


def test_docstring_describes_the_real_scale():
    """CONTRIBUTING options hygiene: "a docstring that lies is a bug" -- and this option's docstring
    is the specific one that lied (it said "percent of max" of an unstated quantity, while the wire
    carried an HP multiplier). It feeds the yaml reference layer, so pin that it names the units."""
    doc = sc.MinimumEnemyDifficulty.__doc__.lower()
    assert "hp" in doc, "the docstring must say what the scale multiplies (enemy HP)"
    assert "rune" in doc, "the docstring must say rune rewards are unaffected -- players ask"


def test_ramp_option_is_reachable_and_defaults_to_the_linear_curve():
    assert "difficulty_ramp_speed" not in defaults.FROZEN_OPTIONS
    assert sc.Scaling.OPTIONS["difficulty_ramp_speed"] is sc.DifficultyRampSpeed
    assert sc.DifficultyRampSpeed.default == 0, "default must be the unchanged even ramp"
    assert sc.DifficultyRampSpeed.range_start == 0 and sc.DifficultyRampSpeed.range_end == 100


def test_both_difficulty_sliders_point_the_same_way():
    """THE USABILITY RULE, pinned. Two difficulty knobs that disagree about which direction is
    harder is a bug players hit before they hit any of ours. `minimum_enemy_difficulty` rises with
    difficulty, so `difficulty_ramp_speed` is INVERTED against the internal ramp_pct to match."""
    assert sc.MinimumEnemyDifficulty.default == 0 and sc.DifficultyRampSpeed.default == 0, (
        "both default to 0 = least change")
    # higher speed -> lower ramp_pct -> the top tier is reached EARLIER -> harder
    pcts = [sc.ramp_pct_from_speed(v) for v in (0, 25, 50, 75, 100)]
    assert pcts == sorted(pcts, reverse=True), f"speed must invert monotonically, got {pcts}"
    assert sc.ramp_pct_from_speed(0) == 100, "speed 0 is the unchanged even ramp"
    assert sc.ramp_pct_from_speed(100) == 1, "speed 100 is maximum almost immediately"
    assert sc.ramp_pct_from_speed(-5) == 100 and sc.ramp_pct_from_speed(999) == 1, "clamps"


def test_the_old_option_names_raise_instead_of_being_ignored():
    """Archipelago drops unknown yaml keys silently, so a rename would leave the old key reading
    like a setting and doing nothing (the hazard test_gf_shipping_yaml exists for). Options.Removed
    raises instead."""
    import Options
    for old in ("completion_scaling_floor", "completion_scaling_ramp"):
        cls = sc.Scaling.OPTIONS[old]
        assert issubclass(cls, Options.Removed), f"{old} must be a Removed stub"
        cls("")  # absent / empty is fine
        with pytest.raises(Exception):
            cls("50")  # a stale yaml VALUE must be refused


@pytest.mark.parametrize("pct,expect_top", [(0, False), (25, False), (50, False), (100, True)])
def test_emitted_multiplier_resolves_to_a_sane_tier(pct, expect_top):
    top = len(scaling_ladder.SCALING_HP_LADDER) - 1
    tier = _floor_tier(scaling_ladder.floor_multiplier(pct))
    assert tier == round(pct / 100 * top)
    assert (tier == top) is expect_top, (
        "completion_scaling_floor: %d %s the top tier" % (pct, "should reach" if expect_top
                                                          else "must NOT reach"))


def _ceiling_tier(mult, ladder=scaling_ladder.SCALING_HP_LADDER):
    """The client's ceiling search, restated (er-logic ceiling_tier_from_multiplier): the LAST rung
    no stronger than `mult`. Deliberately the mirror of _floor_tier, not a reuse."""
    hits = [i for i, hp in enumerate(ladder) if hp <= mult]
    return hits[-1] if hits else 0


def test_ceiling_option_is_reachable_and_defaults_to_uncapped():
    assert "maximum_enemy_difficulty" not in defaults.FROZEN_OPTIONS
    assert sc.Scaling.OPTIONS["maximum_enemy_difficulty"] is sc.MaximumEnemyDifficulty
    assert sc.MaximumEnemyDifficulty.default == 100, "default must be no cap"
    assert sc.MaximumEnemyDifficulty.range_start == 0


@pytest.mark.parametrize("pct", [0, 25, 50, 75, 100])
def test_ceiling_percent_round_trips_through_the_clients_search(pct):
    top = len(scaling_ladder.SCALING_HP_LADDER) - 1
    assert _ceiling_tier(scaling_ladder.ceiling_multiplier(pct)) == round(pct / 100 * top)


def test_ceiling_and_floor_round_the_OPPOSITE_way():
    """The two conversions are mirrors, and reusing one for both would cap a rung high. Pin it on a
    value strictly BETWEEN two rungs, which is the only place the difference shows."""
    lad = scaling_ladder.SCALING_HP_LADDER
    mid = (lad[5] + lad[6]) / 2
    assert _ceiling_tier(mid) == 5, "a ceiling takes the last rung NO STRONGER than the value"
    assert _floor_tier(mid) == 6, "a floor takes the first rung AT LEAST as strong"


class TestSlotDataUnits:
    """END TO END on a generated world -- the composition, not the pieces. CONTRIBUTING rule 11: a
    pipeline of individually correct stages can still drop the exact case it was built for, so the
    motivating value (25) is asserted after the whole `fill_slot_data` path, by name."""

    @staticmethod
    def _slot_data(pct):
        WorldTestBase = pytest.importorskip("test.bases").WorldTestBase

        class _T(WorldTestBase):
            game = GAME
            options = {"minimum_enemy_difficulty": pct}

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

    def test_a_cap_reaches_the_wire_and_flags_the_client_requirement(self):
        WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
        from worlds.eldenring import contract

        class _T(WorldTestBase):
            game = GAME
            options = {"maximum_enemy_difficulty": 50}

        t = _T()
        t.setUp()
        try:
            sd = t.world.fill_slot_data()
        finally:
            t.tearDown()
        top = len(scaling_ladder.SCALING_HP_LADDER) - 1
        nested = sd["options"]["completion_scaling_ceiling"]
        assert nested == scaling_ladder.ceiling_multiplier(50)
        assert _ceiling_tier(nested) == round(50 / 100 * top) < top, "the cap must actually cap"
        # ...and the seed must TELL the client, or an old one would ignore the cap in silence.
        assert sd.get(contract.REQUIRES_CLIENT_FEATURES) == ["scaling_ceiling"]

    def test_an_uncapped_seed_demands_nothing_of_the_client(self):
        """Default seeds must connect to ANY client. The handshake is a cost you pay only when you
        opt into the thing that costs it -- otherwise it is a compatibility break for everyone."""
        from worlds.eldenring import contract
        sd = self._slot_data(0)
        assert contract.REQUIRES_CLIENT_FEATURES not in sd, (
            "an uncapped seed declared a client requirement it does not have")
        assert sd["options"]["completion_scaling_ceiling"] == scaling_ladder.SCALING_HP_LADDER[-1], (
            "uncapped must still EMIT the key, as the top rung -- presence must not carry meaning")

    def test_an_inverted_floor_and_ceiling_is_refused_at_generation(self):
        """CONTRIBUTING's headline gate: an incompatible combination fails at options-validation with
        a message naming BOTH options -- not a FillError, not a config that generates and plays
        wrong."""
        WorldTestBase = pytest.importorskip("test.bases").WorldTestBase

        class _T(WorldTestBase):
            game = GAME
            options = {"minimum_enemy_difficulty": 80, "maximum_enemy_difficulty": 20}

        t = _T()
        with pytest.raises(Exception) as ei:
            t.setUp()
            t.world.fill_slot_data()
        msg = str(ei.value)
        assert "minimum_enemy_difficulty" in msg and "maximum_enemy_difficulty" in msg, (
            f"the error must name BOTH options, got: {msg}")

    def test_max_floor_reaches_the_top_of_the_ladder(self):
        sd = self._slot_data(100)
        nested = sd["options"]["completion_scaling_floor"]
        assert nested == scaling_ladder.SCALING_HP_LADDER[-1]
        assert _floor_tier(nested) == len(scaling_ladder.SCALING_HP_LADDER) - 1
