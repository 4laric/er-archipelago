"""TIER-A: the SweepSlot split -- SweepSlotMajor / SweepSlotMinor (issue #734).

Alaric, on the issue: *"we should maybe be drawing a distinction between major boss sweep slot and
minor/all boss sweep slot."* A sweep payout off a legacy-dungeon boss and one off a cave boss are
different bargains, and plain `SweepSlot` priced them the same.

THE RULING (2026-08-16), and each half of it is a test below:

  * **"major" means the `MajorBoss` class**, not `legacy`. The two disagree 46 ways, so this is not
    a distinction without a difference -- 41 legacy triggers are not major and 5 majors are not
    legacy.
  * **The membership is EMITTED, not re-derived.** `boss_sweeps.MAJOR_SWEEP_TRIGGERS` comes from
    gen_data, where `MajorBoss` is decided from all four of its sources. The cheap world-side
    reconstruction (location_tags + boss_reward_lots) reaches about half the triggers and drops
    Promised Consort Radahn, Starscourge Radahn and the Fire Giant -- so the test that matters most
    here is the one that names those bosses.
  * **The subclasses are SUBSETS and are off by default.** The `Boss` / `LegacyBoss` / `FieldBoss`
    precedent: a seed that does not ask for them is byte-unchanged.

Run:  python -m pytest greenfield/eldenring/tests/test_gf_sweep_slot_split.py
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))))

from worlds.eldenring import contract  # noqa: E402
from worlds.eldenring.boss_sweeps import DUNGEON_SWEEPS, MAJOR_SWEEP_TRIGGERS  # noqa: E402
from worlds.eldenring.features import progression_surface as ps  # noqa: E402

try:
    from worlds.eldenring.boss_healthbars import BOSS_HEALTHBARS
except Exception:                                        # pragma: no cover - data leaf must exist
    BOSS_HEALTHBARS = {}


def _named(fragment):
    """Triggers whose healthbar name contains `fragment`. Names are advisory -- used to ADDRESS a
    boss in a failure message, never to decide membership (the derivation is all flags)."""
    return [t for t in DUNGEON_SWEEPS
            if fragment.lower() in (BOSS_HEALTHBARS.get(t, ("", "", "", ""))[3] or "").lower()]


# ---------------------------------------------------------------------------------------------
# The vocabulary
# ---------------------------------------------------------------------------------------------
def test_both_subclasses_are_in_the_vocabulary_and_are_derived():
    for cls in ("SweepSlotMajor", "SweepSlotMinor"):
        assert cls in contract.SURFACE_CLASSES
        assert cls in contract.SURFACE_DERIVED_CLASSES, (
            "%s carries no location tag -- it is resolved per seed from that seed's own sweeps, "
            "exactly like SweepSlot, and check_sweep_cut_partition reads this set" % cls)


def test_the_default_surface_is_unchanged():
    """🛑 The whole point of "subsets, off by default". SweepSlot joining the default changed every
    seed once (#631); this must not do it again."""
    assert "SweepSlot" in contract.SURFACE_DEFAULT_CLASSES
    assert not ({"SweepSlotMajor", "SweepSlotMinor"} & set(contract.SURFACE_DEFAULT_CLASSES))


def test_the_wizard_can_draw_them():
    """`surface_class_meta` RAISES on a class with no family or no label, and it is the only thing
    standing between a new class and a bare key rendered in a grid of labelled ones."""
    meta = {m["key"]: m for m in ps.surface_class_meta()}
    for cls in ("SweepSlotMajor", "SweepSlotMinor"):
        assert meta[cls]["family"] == "sweeps"
        assert meta[cls]["label"] and meta[cls]["hint"]


def test_the_wizard_is_told_that_sweepslot_already_contains_them():
    """Otherwise a player ticks SweepSlot and SweepSlotMajor together and is told it bought
    something. It did not. The derived classes carry no tags, so the tag-derived containment loop
    cannot see them -- this is the branch that covers that."""
    contains = ps.class_containment()
    assert set(contains.get("SweepSlot", ())) >= {"SweepSlotMajor", "SweepSlotMinor"}


# ---------------------------------------------------------------------------------------------
# The partition
# ---------------------------------------------------------------------------------------------
def test_the_two_subclasses_partition_sweepslot_exactly():
    """No sweep in both, none in neither. If a third bucket ever appears it appears HERE, not in a
    player's seed as a sweep that quietly stopped being selectable."""
    everything = contract.sweeps_for_surface_class(DUNGEON_SWEEPS, "SweepSlot", MAJOR_SWEEP_TRIGGERS)
    major = contract.sweeps_for_surface_class(DUNGEON_SWEEPS, "SweepSlotMajor", MAJOR_SWEEP_TRIGGERS)
    minor = contract.sweeps_for_surface_class(DUNGEON_SWEEPS, "SweepSlotMinor", MAJOR_SWEEP_TRIGGERS)
    assert set(everything) == set(DUNGEON_SWEEPS)
    assert not (set(major) & set(minor))
    assert set(major) | set(minor) == set(DUNGEON_SWEEPS)


def test_an_unknown_class_selects_nothing_rather_than_everything():
    """The failure direction matters: falling back to the whole map would let a typo in the
    vocabulary put foreign progression on every sweep in the seed."""
    assert contract.sweeps_for_surface_class(DUNGEON_SWEEPS, "SweepSlotMinour",
                                             MAJOR_SWEEP_TRIGGERS) == {}


def test_major_is_a_real_minority_of_the_sweeps():
    """A split whose halves are 218/0 would be a knob that does nothing. Bounds, not a pin: the
    roster moves when the datamine improves, and this should not go red for being RIGHT."""
    assert 20 <= len(MAJOR_SWEEP_TRIGGERS) <= 90, len(MAJOR_SWEEP_TRIGGERS)
    assert MAJOR_SWEEP_TRIGGERS <= set(DUNGEON_SWEEPS), (
        "a major trigger with no sweep group is a major boss that lost its sweep (#540's shape)")


# ---------------------------------------------------------------------------------------------
# ⭐ The three bosses that decide WHERE the derivation lives
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("who", ["Starscourge Radahn", "Fire Giant"])
def test_the_festival_rekeyed_bosses_are_major(who):
    """🛑 THE REASON THIS IS EMITTED FROM gen_data AND NOT REBUILT WORLD-SIDE.

    Three field bosses keep their persistent defeat flag in a `12`-prefix form while the achievement
    roster and BOSS_REWARD_DEFEAT both carry the `10`-prefix entity flag (Radahn 1052380800 ->
    1252380800, Fire Giant 1052520800 -> 1252520800). A join that does not bridge those forms calls
    two demigods minor bosses -- and it does it silently, because the trigger still exists and still
    has a sweep. `_festival_alias` bridges BOTH halves of the derivation; it was one-sided at first
    and Radahn was the boss that caught it.
    """
    trigs = _named(who)
    assert trigs, "%s has no sweep trigger at all -- that is a different bug" % who
    assert any(t in MAJOR_SWEEP_TRIGGERS for t in trigs), (
        "%s is a major boss and his sweep must be in SweepSlotMajor" % who)


def test_legacy_would_have_been_the_wrong_answer():
    """The issue offered `legacy` as the free, "defensible, data-clean" definition of major. It is
    not the same set, and this test is the evidence -- if someone later simplifies the predicate to
    `class == "legacy"`, these bosses are what changes hands."""
    legacy = {t for t in DUNGEON_SWEEPS if BOSS_HEALTHBARS.get(t, ("", "", "", ""))[2] == "legacy"}
    if not legacy:
        pytest.skip("BOSS_HEALTHBARS not importable in this layout")
    assert legacy != MAJOR_SWEEP_TRIGGERS
    # Majors that are not legacy: the roster reaches out into the field and the mini-dungeons.
    assert MAJOR_SWEEP_TRIGGERS - legacy
    # Legacy bosses nobody would call major.
    # 🛑 NOT a list of "bosses that ought to be minor" -- that judgement belongs to #737's
    # derivation, not here. These are legacy-class triggers that `MajorBoss` does NOT contain today,
    # so they are exactly the rows that would change hands if the predicate were simplified to
    # `class == "legacy"`. (The Godskin Duo reads the other way and is deliberately absent: it IS on
    # the roster, which is a fact about MajorBoss, not about this split.)
    for who in ("Tree Sentinel", "Scadutree Avatar"):
        trigs = _named(who)
        assert trigs and not any(t in MAJOR_SWEEP_TRIGGERS for t in trigs), (
            "%s is a legacy-class trigger and is NOT on the major roster -- if this flips, the "
            "predicate quietly became `legacy`" % who)


# ---------------------------------------------------------------------------------------------
# #363: does the split hand anyone half a dungeon?
# ---------------------------------------------------------------------------------------------
def test_no_map_local_dungeon_straddles_the_split():
    """The issue's open worry: "a dungeon with two triggers already nominates twice; if the two land
    in different subclasses, a player selecting one subclass gets a partial dungeon."

    Measured: of the maps whose triggers straddle major/minor, NONE are map-local classes. Every
    straddle is a legacy or field map, whose sweeps are region-divvy or per-tile and never promised
    one map's worth of checks in the first place. So the predicate stays per-TRIGGER. This test is
    what makes that an ongoing fact rather than a 2026-08-16 observation.
    """
    if not BOSS_HEALTHBARS:
        pytest.skip("BOSS_HEALTHBARS not importable in this layout")
    map_local = frozenset(contract.SWEEP_MINI_CLASSES)
    by_map = {}
    for t in DUNGEON_SWEEPS:
        row = BOSS_HEALTHBARS.get(t)
        if row:
            by_map.setdefault(row[0], []).append(t)
    straddling = []
    for mp, trigs in by_map.items():
        if len(trigs) < 2:
            continue
        n_major = sum(t in MAJOR_SWEEP_TRIGGERS for t in trigs)
        if 0 < n_major < len(trigs) and all(
                BOSS_HEALTHBARS[t][2] in map_local for t in trigs):
            straddling.append(mp)
    assert not straddling, (
        "map-local sweep group(s) split across SweepSlotMajor/Minor, so selecting one subclass "
        "pays out half a dungeon (#363): %s -- either promote the whole arena or state the "
        "exception here" % sorted(straddling))
