"""Options-description gate (greenfield analog of the eldenring options-description gate).

Every greenfield/feature option this world defines must carry a non-empty class docstring -- that
docstring is the description the options wizard / webhost surfaces, so a blank one ships a mystery
knob. AP-common options (DeathLink and friends, whose class __module__ is "Options") are inherited,
not ours to document, so they're skipped. WorldTestBase; importorskips when AP isn't importable
(source-tree sandbox), so it's a no-op there and only runs once the world is installed under
Archipelago/worlds/.

Run (from the Archipelago dir, world installed):
    python -m pytest worlds/eldenring/tests/test_gf_options.py
"""
import dataclasses
import typing

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

GAME = "Elden Ring"


class OptionsDescriptionGate(WorldTestBase):
    game = GAME

    def test_every_feature_option_has_a_description(self):
        dc = self.world.options_dataclass
        # Resolve field annotations to the actual Option classes (fields store the type).
        hints = typing.get_type_hints(dc)
        missing = []
        checked = 0
        for f in dataclasses.fields(dc):
            opt_cls = hints.get(f.name, f.type)
            module = getattr(opt_cls, "__module__", "") or ""
            # AP-common options live in the top-level Options module -> inherited, not ours.
            if module.startswith("Options"):
                continue
            checked += 1
            doc = getattr(opt_cls, "__doc__", None)
            if not (doc and doc.strip()):
                missing.append(f.name)
        self.assertGreater(
            checked, 0, "no greenfield/feature options found -- gate would be vacuous")
        self.assertEqual(
            missing, [],
            "these greenfield/feature options have an empty class docstring (description): "
            + ", ".join(missing))


# ---------------------------------------------------------------------------------------------
# completion_scaling_floor -- the option matrix for the difficulty floor (un-frozen 2026-07-27).
#
# CONTRIBUTING's headline gate: flip the option, in combination with the existing ones, and get a
# clean gen. The floor is emitted through core._options_echo AFTER a unit conversion
# (scaling_ladder.floor_multiplier), so the combinations that matter are the ones that change the
# SHAPE of the scaling wire around it -- a one-region seed (no depth to ramp over, max_target == 0,
# where the client resolves EVERY region to the floor) and a DLC-only seed (a different kept set and
# the only configuration that can also emit dlcScadutreeFloorRanges).
#
# The units themselves are gated in test_gf_scaling_floor_units.py / test_gf_scaling_ladder_mirror.py;
# this is the combination sweep, not a third copy of that assertion.
# ---------------------------------------------------------------------------------------------
def test_a_default_all_regions_seed_spans_the_WHOLE_ladder():
    """THE REGRESSION THIS CATCHES, and it is not a fill failure.

    A broken order-ramp emits one target for every region. The seed still generates, every fill check
    still passes, and the player just... never sees difficulty change. Verified by breaking it
    (2026-07-27): forcing a constant target collapsed the span from 19 to 6.

    Note it did NOT go flat -- `_SCALING_BUCKET_DELTA` bumps a Caelid bucket, so at least two tiers
    survive any breakage that keeps Caelid. A "did every region get the same tier?" check would have
    called that break healthy. The SPAN is the property with teeth.
    """
    from worlds.eldenring import contract, scaling_ladder

    class _T(WorldTestBase):
        game = GAME
        options = {"num_regions": 0}

    t = _T()
    t.setUp()
    try:
        sd = t.world.fill_slot_data()
    finally:
        t.tearDown()

    n = len(scaling_ladder.SCALING_HP_LADDER)
    targets = [x for _lo, _hi, x in sd[contract.REGION_SPHERE_TARGET_RANGES]]
    mx = max(targets)
    assert mx > 0, "every region emitted target 0 -- the ramp produced no curve at all"
    tiers = sorted(round(x / mx * (n - 1)) for x in targets)
    assert tiers[0] == 0, f"shallowest region is tier {tiers[0]}, expected 0 at a default floor"
    assert tiers[-1] == n - 1, f"deepest region is tier {tiers[-1]}, expected the top rung {n - 1}"
    assert len(set(tiers)) >= n // 2, (
        f"the curve resolved to only {len(set(tiers))} distinct tiers out of {n}. An all-regions "
        f"seed at default settings should populate most of the ladder; this many collisions means "
        f"the ramp collapsed.")


_FLOORS = (0, 25, 100)
_COMBOS = (
    ("base_all_regions", {}),
    ("one_region", {"num_regions": 1}),
    ("small_rolled", {"num_regions": 4, "num_regions_order": "rolled"}),
    ("dlc", {"enable_dlc": True}),
    ("dlc_only", {"dlc_only": True}),
)


@pytest.mark.parametrize("floor", _FLOORS)
@pytest.mark.parametrize("label,extra", _COMBOS, ids=[c[0] for c in _COMBOS])
def test_scaling_floor_combinations_generate_clean(floor, label, extra):
    """Every floor x seed-shape combination must generate and emit a well-formed wire -- no
    OptionError, no stack trace, no silently-absent key."""
    from worlds.eldenring import contract, scaling_ladder

    class _T(WorldTestBase):
        game = GAME
        options = dict(extra, minimum_enemy_difficulty=floor)

    t = _T()
    t.setUp()
    try:
        sd = t.world.fill_slot_data()
    finally:
        t.tearDown()

    nested = sd["options"]["completion_scaling_floor"]
    assert nested == scaling_ladder.floor_multiplier(floor), (
        "%s @ floor=%d: options.completion_scaling_floor is %r, expected the converted multiplier %r"
        % (label, floor, nested, scaling_ladder.floor_multiplier(floor)))
    assert sd["completion_scaling_floor"] == floor, (
        "%s @ floor=%d: the top-level legacy copy must stay the raw percent" % (label, floor))

    # The floor rides alongside the target wire; it must not disturb it. An EMPTY wire is the one
    # shape the client refuses to arm on (scaling.rs parse_scaling_config H4/R6), so assert presence
    # rather than assuming it (CONTRIBUTING rule 2: an empty result is a failure, not a clean run).
    ranges = sd[contract.REGION_SPHERE_TARGET_RANGES]
    assert ranges, ("%s @ floor=%d: regionSphereTargetRanges is EMPTY -- the client would refuse to "
                    "arm enemy scaling and leave every enemy vanilla." % (label, floor))
    assert all(len(t3) == 3 and t3[0] == t3[1] for t3 in ranges), (
        "%s @ floor=%d: malformed [lo, hi, target] triples" % (label, floor))
