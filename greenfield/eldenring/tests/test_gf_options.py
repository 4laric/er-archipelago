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


# ---------------------------------------------------------------------------------------------
# region_grace_unlock -- the combination sweep for single-grace mode (added 2026-07-29).
#
# CONTRIBUTING's headline gate: a new option must generate cleanly in combination with the ones it
# can interact with. This one touches the grace BUNDLE, so what matters is what changes which
# regions exist and which bundles are withheld -- num_regions and natural_progression. It moves no
# item and gates nothing, so these assert exactly that rather than just "it genned".
# ---------------------------------------------------------------------------------------------
_GRACE_COMBOS = (
    ("default",           "all",       {}),
    ("landmarks",         "landmarks", {}),
    ("landmarks_small",   "landmarks", {"num_regions": 6}),
    ("landmarks_natural", "landmarks", {"natural_progression": True}),
    # DLC on purpose: the landmarks partition follows the WARP MENU, not region size, and the DLC is
    # where that bites -- Gravesite 17 graces -> 1, Scadu Altus 17 -> 1. Accepted, but a seed that
    # generates DLC regions must still emit a well-formed bundle for them.
    ("landmarks_dlc",     "landmarks", {"enable_dlc": True}),
    ("entrance",          "entrance",  {}),
    ("entrance_small",    "entrance",  {"num_regions": 6}),
    ("entrance_natural",  "entrance",  {"natural_progression": True}),
)


def _grace_world(mode, extra, seed=4242):
    """A world at a PINNED seed.

    The seed is not decoration. `setUp()` leaves the seed unset, so AP picks a fresh random one per
    instantiation -- and the item-pool comparison below then diffs two different SEEDS and blames
    the option. It failed exactly that way when first written ('Black Blade' != 'Bewitching Branch'
    at index 329, pure filler RNG). Any cross-world comparison has to hold the seed fixed or it is
    measuring noise."""
    class _T(WorldTestBase):
        game = GAME
        options = dict(extra, region_grace_unlock=mode)
    t = _T("runTest")
    t.options = dict(extra, region_grace_unlock=mode)
    t.world_setup(seed)
    return t


@pytest.mark.parametrize("label,mode,extra", _GRACE_COMBOS, ids=[c[0] for c in _GRACE_COMBOS])
def test_region_grace_unlock_combinations_generate_clean(label, mode, extra):
    from worlds.eldenring.features.graces import bundle_withheld
    t = _grace_world(mode, extra)
    try:
        sd = t.world.fill_slot_data()
        rg = sd["regionGraces"]
        assert rg, "%s: no regionGraces emitted at all" % label
        if mode == "entrance":
            over = {k: len(v) for k, v in rg.items() if len(v) > 1}
            assert not over, (
                "%s: entrance mode granted more than one grace for %s -- the bundle is supposed to "
                "be exactly the region's front door." % (label, over))
        elif mode == "landmarks":
            from worlds.eldenring.region_graces import (
                REGION_GRACE_LANDMARKS, REGION_GRACE_POINTS)
            for k, got in rg.items():
                if not got:
                    continue                       # withheld; asserted separately below
                region = k[: -len(" Lock")]
                want = sorted(f for f in REGION_GRACE_LANDMARKS.get(region, ())
                              if f in REGION_GRACE_POINTS.get(region, ()))
                assert got == (want or [min(got)]), (
                    "%s: %s got %s, expected the generated landmarks set %s. The tier must come "
                    "from REGION_GRACE_LANDMARKS, not be recomputed at runtime -- a second "
                    "derivation is a second thing to drift." % (label, region, got, want))
        else:
            assert sum(len(v) for v in rg.values()) > len(rg), (
                "%s: `all` should grant many graces per region; the default changed" % label)
        # The half that matters: entrance mode must never become a way past a wall.
        leaked = [k for k in rg if rg[k] and bundle_withheld(t.world, k[: -len(" Lock")])]
        assert not leaked, (
            "%s: a gated child behind an armed wall was granted a grace anyway (%s). Entrance mode "
            "must not open a door the `all` bundle deliberately withholds." % (label, leaked))
    finally:
        pass


def test_entrance_mode_moves_no_item_and_no_check():
    """A convenience setting: same checks, same pool, only the warp bundle differs."""
    a = _grace_world("all", {}, seed=4242)
    sd_a = a.world.fill_slot_data()
    pool_a = sorted(i.name for i in a.multiworld.itempool if i.player == a.player)
    e = _grace_world("entrance", {}, seed=4242)   # SAME seed -- see _grace_world
    sd_e = e.world.fill_slot_data()
    pool_e = sorted(i.name for i in e.multiworld.itempool if i.player == e.player)
    assert sd_a["locationFlags"] == sd_e["locationFlags"], (
        "region_grace_unlock changed the CHECK set -- it must only change which graces a lock lights")
    assert pool_a == pool_e, "region_grace_unlock changed the ITEM POOL; it must not"


def test_the_three_tiers_are_nested_and_strictly_ordered():
    """entrance subset-of landmarks subset-of all, per region -- and strictly smaller overall.

    This is the invariant that makes the option legible: a coarser tier can only ever REMOVE warp
    points, never swap them for different ones. If landmarks ever picked a grace `all` does not
    grant, or entrance picked one outside landmarks, the tiers would not be a ladder and a player
    moving one notch could LOSE a grace they expected to keep and gain one they did not ask for.
    """
    seen = {}
    for tier in ("all", "landmarks", "entrance"):
        w = _grace_world(tier, {}, seed=4242)
        seen[tier] = w.world.fill_slot_data()["regionGraces"]

    for lock, wide in seen["all"].items():
        mid, narrow = seen["landmarks"].get(lock, []), seen["entrance"].get(lock, [])
        assert set(mid) <= set(wide), (
            "%s: landmarks granted %s which `all` does not -- the tiers are not nested"
            % (lock, sorted(set(mid) - set(wide))))
        assert set(narrow) <= set(mid), (
            "%s: entrance granted %s which landmarks does not -- the tiers are not nested"
            % (lock, sorted(set(narrow) - set(mid))))

    totals = {t: sum(len(v) for v in rg.values()) for t, rg in seen.items()}
    assert totals["all"] > totals["landmarks"] > totals["entrance"], (
        "the three tiers must be strictly decreasing in size; got %s. If landmarks has collapsed "
        "onto entrance the middle setting is pointless, and if it has collapsed onto `all` it is "
        "not doing anything." % totals)


def test_landmarks_is_the_middle_setting_where_it_matters():
    """Regions the warp menu genuinely splits must get more than one grace at `landmarks`.

    The tier is UNEVEN by construction (it follows the menu, not region size) and three regions
    legitimately reduce to a single grace -- Gravesite, Scadu Altus and Weeping, accepted 2026-07-29.
    So this does not demand a floor everywhere; it demands that the big base-game regions the menu
    DOES split still come out split, which is the whole point of offering a middle setting."""
    w = _grace_world("landmarks", {}, seed=4242)
    rg = w.world.fill_slot_data()["regionGraces"]
    for region in ("Liurnia", "Caelid", "Limgrave", "Altus"):
        got = rg.get("%s Lock" % region)
        if got is None:
            continue                               # not kept in this seed
        assert len(got) > 1, (
            "%s reduced to %d grace(s) at `landmarks`. That region's sub-areas are exactly what the "
            "middle tier exists to expose; if the partition changed, re-verify it BY NAME before "
            "re-baselining this." % (region, len(got)))
