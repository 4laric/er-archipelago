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


def test_range_spans_the_whole_ladder_and_defaults_to_the_vanilla_floor():
    # The old range_end of 50 was written against the percent reading and never revisited; under the
    # real (multiplier) semantics it could not express "floor at the top tier" meaningfully at all.
    assert sc.MinimumEnemyDifficulty.range_end == 100
    assert sc.MinimumEnemyDifficulty.range_start == 0

    # 🛑 THE MOTIVATING CASE, AND IT IS A RETRACTION (2026-08-05, same day, unreleased). This test
    # briefly asserted 25, on the argument that vanilla applies TWO scaling rows per enemy -- a rung
    # and a second row at the same index +400 -- making its effective HP floor 3.56x against our
    # 1.141x. That was a PRODUCT COMPUTED FROM PARAM COLUMNS, and per-enemy measurement disproved it:
    #
    #     npc 36000012, carried [7020, 7420], vanilla base hp 755  ->  observed max_hp 967
    #     755 x 1.281 (the RUNG rate) = 967.  The 7420 row contributes NOTHING.
    #
    # Six enemies reconstruct to the unit digit on rung-only, and eleven carrying just our applied
    # rung read residual 1.000. The band's `effectTargetSelf` is 1, identical to the ladder, so the
    # target flags do not explain it -- the column is simply not read on this path.
    #
    # So 0 IS the vanilla-equivalent floor. Raising this default again needs a MEASUREMENT, not an
    # arithmetic argument from param columns.
    assert sc.MinimumEnemyDifficulty.default == 0
    assert scaling_ladder.floor_multiplier(sc.MinimumEnemyDifficulty.default) == 0, (
        "the int 0 is load-bearing: a yaml that never mentions this option must generate "
        "byte-identically to one from before the option was reachable")
    # ...and the whole ladder is still expressible for anyone who wants a harder floor.
    assert scaling_ladder.floor_multiplier(25) == 2.266
    assert scaling_ladder.tier_for_floor_multiplier(2.266) == 5


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
    assert sc.DifficultyRampSpeed.default == 0, "the ramp still defaults to the even curve"
    # 🛑 THE FLOOR'S DEFAULT IS NOT THIS TEST'S BUSINESS, and asserting it here is what broke main.
    # The value lived in two places: `test_range_spans_the_whole_ladder_...` (which owns it) and a
    # second copy here, added alongside the floor-25 default. The revert (#395) updated the owner to
    # `== 0` and could not see this one, so a correct revert turned main red. A DIRECTION rule holds
    # at every value the option can take -- including 0 -- so it must not name one.
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


def test_ceiling_option_is_reachable_and_defaults_to_auto():
    """Default changed 100 -> `auto` on 2026-07-30 (cap the curve to the LENGTH of the run). The
    guarantee the old assertion was protecting is NOT the literal 100 -- it is that a seed nobody
    configured stays uncapped, and that is pinned below and in
    test_an_uncapped_seed_demands_nothing_of_the_client."""
    assert "maximum_enemy_difficulty" not in defaults.FROZEN_OPTIONS
    assert sc.Scaling.OPTIONS["maximum_enemy_difficulty"] is sc.MaximumEnemyDifficulty
    assert sc.MaximumEnemyDifficulty.default == scaling_ladder.AUTO_CEILING, "default must be auto"
    assert sc.MaximumEnemyDifficulty.special_range_names == {"auto": scaling_ladder.AUTO_CEILING}
    assert sc.MaximumEnemyDifficulty.range_start == 0


def test_auto_on_a_full_map_is_still_uncapped():
    """The compatibility promise, at the unit level: num_regions 0 means ALL regions, so a yaml that
    configures nothing resolves to 100 -- no cap, and therefore no client-feature handshake."""
    assert scaling_ladder.auto_ceiling_pct(0, 30) == 100
    assert scaling_ladder.resolve_max_difficulty_pct(
        scaling_ladder.AUTO_CEILING, 0, 30, 0) == 100


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


def test_enemy_scaling_is_reachable_and_defaults_to_on():
    """The vanilla switch is a real yaml option, not a frozen constant, and the default is unchanged
    behaviour -- a seed that never mentions it scales exactly as before."""
    assert "enemy_scaling" not in defaults.FROZEN_OPTIONS
    assert sc.Scaling.OPTIONS["enemy_scaling"] is sc.EnemyScaling
    assert sc.EnemyScaling.default == 1


class TestVanillaScaling:
    """`enemy_scaling: false` must reach the client's own arm/disarm switch.

    CONTRIBUTING rule 11: the motivating case is "I want the item randomizer without the difficulty
    curve", and the only thing that delivers it is the ONE key er-logic `parse_scaling_config` reads
    before anything else. Assert that key by name through the real `fill_slot_data` path -- a feature
    that computed a correct curve and forgot to flip this would look entirely correct in review.
    """

    @staticmethod
    def _slot_data(on, seed=1):
        """slot_data for `enemy_scaling: on`, generated AT A FIXED SEED.

        🛑 THE SEED IS THE POINT. `setUp()` alone generates at a random seed, so two calls are two
        different worlds and every seed-derived key differs -- test_gf_world documents five of them
        (`_SEED_VARYING`) and fill-dependent keys like goalRequiredItems behave the same way.
        Comparing those two dicts and demanding exactly one key change is a comparison that can only
        pass by luck; it did until #390 perturbed the random stream.

        Holding the seed makes the two worlds differ by exactly the option under test, which is the
        only way `test_off_changes_nothing_else_on_the_wire` can mean what its name says. Excluding
        the noisy keys instead would have been filtering the gate's output: a real leak from the
        scaling feature into goalRequiredItems would look identical to stream drift, and be silenced.
        """
        WorldTestBase = pytest.importorskip("test.bases").WorldTestBase

        class _T(WorldTestBase):
            game = GAME
            options = {"num_regions": 0, "enemy_scaling": on}

        t = _T()
        t.setUp()
        try:
            t.world_setup(seed=seed)      # same pattern as test_gf_world's determinism tests
            return t.world.fill_slot_data()
        finally:
            t.tearDown()

    def test_off_disarms_the_client(self):
        sd = self._slot_data(False)
        assert sd["completion_scaling"] == 0, (
            "er-logic parse_scaling_config returns None on a falsey completion_scaling, which is "
            "what leaves every enemy vanilla. Any other value arms the sweep.")

    def test_on_is_the_shipped_curve(self):
        assert self._slot_data(True)["completion_scaling"] == 4, "4 = smoothstep, the shipped curve"

    # ---- #408: the two copies of the switch -------------------------------------------------
    #
    # 🛑 THE MOTIVATING CASE (CONTRIBUTING rule 11), AND IT SHIPPED. `completion_scaling` rides in
    # slot_data TWICE -- the top-level legacy copy (features/scaling.slot_data) and
    # sd["options"]["completion_scaling"] (core._options_echo). The client reads THE SECOND ONE:
    # er-logic `parse_scaling_config` calls `options::parse_bool_option(sd, "completion_scaling")`,
    # which resolves `/options/completion_scaling`, and short-circuits the entire sweep on it.
    #
    # The feature's copy was gated on the option from the day `enemy_scaling` was added. The echo's
    # was a BARE LITERAL 4. So an `enemy_scaling: false` seed emitted:
    #
    #     "completion_scaling": 0,              <- correct, gated, and IGNORED
    #     "options": { "completion_scaling": 4, ...}   <- the copy the client actually parses
    #
    # ...and the option was unreachable from yaml. Confirmed live on 0.3.5: a player's slot_data
    # showed exactly that pair and his client scaled 240 enemies at 1.14x on a seed he had turned
    # scaling off for. Every test above passed throughout -- test_off_disarms_the_client asserts the
    # top-level copy, which was never the broken one. THE PAIR is the property.
    #
    # Parametrised over BOTH values on purpose: an equality that only holds where both sides are
    # nonzero would have passed against the literal too (4 == 4 with scaling on).
    @pytest.mark.parametrize("on,expect", [(False, 0), (True, 4)])
    def test_both_copies_of_the_switch_agree(self, on, expect):
        sd = self._slot_data(on)
        top = sd["completion_scaling"]
        nested = sd["options"]["completion_scaling"]
        assert nested == top, (
            "completion_scaling disagrees across its two slot_data copies: top-level %r vs "
            "options.%r. The CLIENT reads options.completion_scaling (er-logic "
            "parse_scaling_config), so the options copy is the one that decides whether the sweep "
            "runs -- a gated top-level copy beside a hard-coded one is the option being unreachable "
            "from yaml. Resolve both through features/scaling.completion_scaling_id." % (top, nested))
        assert nested == expect, (
            "enemy_scaling=%r must emit completion_scaling %d in BOTH copies, got %r"
            % (on, expect, nested))

    def test_the_switch_is_not_a_constant_in_the_options_echo(self):
        """The SHAPE of the defect, pinned at the source (an unfired guard is untested, and the
        end-to-end test above cannot say WHY it went red). `_options_echo` is the sub-dict the
        client reads; a literal in it silently overrides a correctly gated feature copy. This asks
        the AST whether the value for the switch is a constant, which is the thing that was wrong.
        """
        import ast
        import inspect
        import textwrap
        from worlds.eldenring import core, contract

        src = textwrap.dedent(inspect.getsource(core.GreenfieldEldenRingWorld._options_echo))
        tree = ast.parse(src)
        found = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            for k, v in zip(node.keys, node.values):
                # contract.COMPLETION_SCALING -- matched by attribute name, so a renamed wire key
                # cannot slip past this.
                if isinstance(k, ast.Attribute) and k.attr == "COMPLETION_SCALING":
                    found.append(v)
        assert len(found) == 1, (
            "expected exactly one contract.COMPLETION_SCALING entry in _options_echo, found %d"
            % len(found))
        assert not isinstance(found[0], ast.Constant), (
            "contract.COMPLETION_SCALING is a literal in _options_echo. That is #408: it overrides "
            "the gated top-level copy and makes enemy_scaling unreachable. Read the option.")
        assert contract.COMPLETION_SCALING == "completion_scaling"

    def test_off_changes_nothing_else_on_the_wire(self):
        """One switch, read in one place. The client short-circuits on `completion_scaling` before
        reading the ranges, so withholding them would buy nothing and would make an off-seed a second
        slot_data shape to reason about -- and a shape that only exists for one option value is a
        shape nobody tests."""
        off, on = self._slot_data(False), self._slot_data(True)
        assert off.keys() == on.keys(), "an off-seed must not be a different wire SHAPE"
        differing = sorted(k for k in on if off[k] != on[k])
        # `options` joined this list on 2026-08-06 and that is the FIX, not noise: before #408 the
        # options sub-dict did not move with the switch, which is precisely why the switch did not
        # work. The assertion is DESCENDED INTO below rather than loosened -- "one key, plus the
        # same key inside options" is still exactly one switch.
        assert differing == ["completion_scaling", "options"], (
            f"turning scaling off changed {differing} -- it must change the switch and nothing "
            "else. Both worlds are generated at the SAME seed, so anything listed here is a real "
            "leak from the scaling feature, not fill noise -- do NOT fix this by excluding a key.")
        nested = sorted(k for k in on["options"] if off["options"][k] != on["options"][k])
        assert nested == ["completion_scaling"], (
            f"inside the options sub-dict, scaling off changed {nested} -- only the arm/disarm "
            "switch may move. Every other options key is independent of it.")


class TestSlotDataUnits:
    """END TO END on a generated world -- the composition, not the pieces. CONTRIBUTING rule 11: a
    pipeline of individually correct stages can still drop the exact case it was built for, so the
    motivating value (25) is asserted after the whole `fill_slot_data` path, by name."""

    @staticmethod
    def _slot_data(pct):
        WorldTestBase = pytest.importorskip("test.bases").WorldTestBase

        class _T(WorldTestBase):
            game = GAME
            options = {"num_regions": 0, "minimum_enemy_difficulty": pct}

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
            options = {"num_regions": 0, "maximum_enemy_difficulty": 50}

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
            options = {"num_regions": 0, "minimum_enemy_difficulty": 80, "maximum_enemy_difficulty": 20}

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
