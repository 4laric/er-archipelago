"""dungeon_sweep's rungs must actually differ -- for a month they did not.

THE BUG. The slot_data emit gated on `dungeon_sweep.value != 0` and never filtered by boss class, so
`minidungeons`, `all` and `bosses` each granted the FULL sweep set. Three distinct player-facing
values, one behaviour. The option's own docstring described the ladder, the player guide repeated it,
and the v0.2.15 release notes told a player by name that `minidungeons` and `bosses` were "the two
middles". All of it was false, and nothing compared the values to each other.

🛑 A CHOICE WHOSE VALUES ARE INTERCHANGEABLE IS A TOGGLE WEARING A LADDER'S CLOTHES. Testing each
value in isolation -- "does it generate?", "does it emit a well-formed wire?" -- passes forever. The
only assertion that catches this compares the values AGAINST EACH OTHER, which is why the test below
is written as a strict ordering rather than four independent cases.

The default moved all -> bosses in the same change: the full set is what every non-none value
already granted, so `bosses` IS the shipped behaviour. Defaulting to `all` would have silently
dropped field sweeps (~38% of them) from every seed under cover of a bug fix.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

GAME = "Elden Ring"
SEED = 4242


def _members(mode):
    """Total swept checks at a rung, at a PINNED seed (kept regions vary per seed)."""
    class _T(WorldTestBase):
        game = GAME
        options = {} if mode is None else {"dungeon_sweep": mode}
    t = _T("runTest")
    t.options = {} if mode is None else {"dungeon_sweep": mode}
    t.world_setup(SEED)
    flags = t.world.fill_slot_data().get("dungeonSweepFlags") or {}
    return sum(len(v) for v in flags.values())


def test_the_rungs_are_strictly_increasing():
    """THE assertion the old suite lacked: the values compared to each other, not in isolation."""
    none, mini, alll, bosses = (_members(m) for m in ("none", "minidungeons", "all", "bosses"))
    assert none == 0, "none must sweep nothing, got %d" % none
    assert none < mini < alll < bosses, (
        "dungeon_sweep rungs are not strictly increasing: none=%d minidungeons=%d all=%d bosses=%d. "
        "If two are equal the option is a toggle pretending to be a ladder -- which is exactly the "
        "state this file exists to prevent." % (none, mini, alll, bosses))


def test_the_default_is_what_actually_shipped():
    """Making the rungs real must not quietly change what a default seed rolls.

    Every non-none value granted the full set before, so the shipped behaviour is `bosses`. Pinning
    this stops a future tidy-up from 'restoring' the documented default and dropping ~38% of sweeps
    from every seed."""
    from worlds.eldenring.features.boss_locks import DungeonSweep
    assert DungeonSweep.default == DungeonSweep.option_bosses, (
        "dungeon_sweep default is no longer `bosses`. The full sweep set is what shipped; changing "
        "this is a balance change and needs saying out loud, not a silent default move.")
    assert _members(None) == _members("bosses")


def test_field_bosses_are_what_all_and_bosses_differ_by():
    """The split that was asked for: `all` is dungeons WITHOUT field bosses."""
    from worlds.eldenring.features.boss_locks import _SWEEP_RUNGS
    assert "field" in _SWEEP_RUNGS["bosses"], "the top rung must include field bosses"
    assert "field" not in _SWEEP_RUNGS["all"], (
        "`all` must EXCLUDE field bosses -- that separation is the whole point of having both")
    assert _SWEEP_RUNGS["minidungeons"] < _SWEEP_RUNGS["all"] < _SWEEP_RUNGS["bosses"], (
        "the rungs must be nested class sets, or a 'higher' setting could lose a sweep a lower one grants")


# Swept checks that DO carry an important tag, as of 2026-07-29. A RATCHET, not an allowlist:
# these six are known debt, and anything new must fail.
#
# 🛑 WHY THEY EXIST. The LEGACY sweep pool is filler-filtered by construction (gen_data's
# `_filler_only` cut, which drops Remembrance/KeyItem/GreatRune/Boss/Legendary/Shop and more). The
# MINIDUNGEON path is not: `_members = _mem_map.get(_bmap, [])` takes the map's checks unfiltered.
# So "sweeps are filler-only" is true of the legacy pool -- which is what bounded the Grafted Scion
# bug to 36 harmless checks -- and NOT true in general. The blurb was corrected to say so.
_KNOWN_IMPORTANT_IN_SWEEPS = {
    7772215,   # Legendary -- Uchigatana, near Deathtouched Catacombs
    7772478,   # Legendary -- Godslayer's Greatsword
    7772562,   # Legendary -- Bull-Goat Helm, near Magma Wyrm Makar
    7772584,   # KeyItem   -- Gaol Upper Level Key
    7772588,   # KeyItem   -- Gaol Lower Level Key
    7772603,   # Boss      -- Dragon Heart, around Dragon's Pit
}


def test_the_important_checks_inside_sweeps_do_not_grow():
    """Ratchet. Sweeps are filler-only in the LEGACY pool but not in the minidungeon path.

    Recorded rather than asserted-away because the six are real and pre-existing: two are DLC gaol
    keys, which a sweep can hand you for killing the boss they gate the route to. Fixing it means
    applying gen_data's `_filler_only` cut to the map path too -- a deliberate change with its own
    balance argument, not something to slip in under a test.

    Until then this stops the set GROWING, which is the part that would go unnoticed."""
    from worlds.eldenring.boss_sweeps import DUNGEON_SWEEPS
    from worlds.eldenring.location_tags import LOCATION_TAGS
    important = {"Remembrance", "Seedtree", "Church", "Boss", "Fragment", "Revered", "Basin",
                 "GreatRune", "KeyItem", "Legendary", "Shop", "ShopNonSpell", "ShopSlot", "MajorBoss"}
    found = {ap for members in DUNGEON_SWEEPS.values() for ap in members
             if important & set(LOCATION_TAGS.get(ap, ()))}
    new = sorted(found - _KNOWN_IMPORTANT_IN_SWEEPS)
    assert not new, (
        "%d NEW important-tagged check(s) entered a sweep pool: %s. A sweep that hands out a key "
        "item makes the rung a progression decision. Either filter them out or justify each one "
        "here." % (len(new), new))
    gone = sorted(_KNOWN_IMPORTANT_IN_SWEEPS - found)
    if gone:
        import warnings
        warnings.warn("%d known important-in-sweep check(s) are gone (%s) -- if that was the "
                      "_filler_only fix, shrink _KNOWN_IMPORTANT_IN_SWEEPS to match." % (len(gone), gone))


def test_the_legacy_pool_specifically_is_clean():
    """The claim that actually bounded the Grafted Scion bug, asserted where it is true."""
    from worlds.eldenring.boss_sweeps import DUNGEON_SWEEPS
    from worlds.eldenring.boss_healthbars import BOSS_HEALTHBARS
    from worlds.eldenring.location_tags import LOCATION_TAGS
    important = {"Remembrance", "Seedtree", "Church", "Boss", "Fragment", "Revered", "Basin",
                 "GreatRune", "KeyItem", "Legendary", "Shop", "ShopNonSpell", "ShopSlot", "MajorBoss"}
    leaked = [ap for fl, members in DUNGEON_SWEEPS.items()
              if (BOSS_HEALTHBARS.get(fl) or (None, None, None))[2] == "legacy"
              for ap in members if important & set(LOCATION_TAGS.get(ap, ()))]
    assert not leaked, (
        "the LEGACY sweep pool is supposed to be filler-only by construction (_filler_only), and %d "
        "important check(s) got in: %s" % (len(leaked), leaked[:5]))
