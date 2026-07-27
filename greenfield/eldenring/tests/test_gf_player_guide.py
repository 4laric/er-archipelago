"""The SHIPPED player guide must not name an option that does not exist.

WHY THIS FILE EXISTS (2026-07-27, and it is embarrassing)
--------------------------------------------------------
There are TWO files called "Player Guide (v0.2)":

    Elden-Ring-Archipelago-Player-Guide.md   repo root -- SHIPPED (package_release.ps1,
                                             required = $true), linked from README and SETUP.md
    release-v0.2/PLAYER-GUIDE.md             referenced by NOTHING, packaged by NOTHING

They are forked copies that have diverged. I wrote the whole player-facing writeup of the new
difficulty options into the SECOND one -- the one no player ever receives -- and only found out by
being asked "player guide updated for scaling?". Docs had no equivalent of
`test_gf_shipping_yaml`, which exists for exactly this class of mistake one directory over.

So this gates the file that SHIPS:

  1. every option-shaped name it mentions is a real option (a rename leaves the guide describing a
     key Archipelago will silently ignore -- the same silent-ignore hazard, one layer up);
  2. the difficulty options are actually documented there, by name.

(2) is the CONTRIBUTING rule-11 half: the case that motivated the work is the acceptance test. A
generic "names are valid" check would have passed happily on a guide that never mentioned scaling at
all, which is precisely the state this was in.

NOT gated here: whether the two guides agree. Deleting or merging the unshipped duplicate is a call
for Alaric, not a test. It carries a header saying it is not shipped.
"""
import os
import re

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

GAME = "Elden Ring"

_HERE = os.path.dirname(os.path.abspath(__file__))
_GF_PKG = os.path.dirname(_HERE)
_REPO = os.path.dirname(os.path.dirname(_GF_PKG))

# Resolve from the source tree OR from beside the installed package (same convention as
# test_gf_shipping_yaml's yaml lookup, and for the same reason: the suite runs from an installed
# world where <repo> is the AP checkout).
_GUIDE = next((p for p in (os.path.join(_GF_PKG, "Elden-Ring-Archipelago-Player-Guide.md"),
                           os.path.join(_REPO, "Elden-Ring-Archipelago-Player-Guide.md"))
               if os.path.isfile(p)), "")

# Backticked snake_case words that are ENGLISH, not options. Keep this list SHORT and justified --
# every entry is a place the gate cannot help, so a long list means the gate is decorative.
_NOT_OPTIONS = {
    "spine",        # a VALUE of num_regions_order ("`spine` order"), not a key
    "rolled",       # ditto
    "region_locks", "great_runes",  # values of ending_condition
}


def _guide_text():
    if not _GUIDE:
        pytest.skip("player guide not found beside the package or at the repo root")
    with open(_GUIDE, encoding="utf-8") as fh:
        return fh.read()


def _live_option_names():
    from worlds.AutoWorld import AutoWorldRegister
    return set(AutoWorldRegister.world_types[GAME].options_dataclass.type_hints)


def test_the_guide_is_actually_present():
    """Without this the two tests below pass VACUOUSLY -- which is how the guide got out of date in
    the first place."""
    assert _GUIDE, ("the shipped player guide was not found. It is packaged with required = $true, "
                    "so if it has moved, this gate must move with it rather than skip.")


def test_every_option_the_guide_names_exists():
    """A renamed option leaves the guide telling players to set a key Archipelago silently ignores.

    Options.Removed stubs still count as real: `completion_scaling_floor` is deliberately named in
    the guide's migration note, and it IS still a field (one that raises on use), so it resolves
    here without an allowlist entry. That is the behaviour we want -- the guide may name a dead key
    precisely because it is telling you it is dead.
    """
    real = _live_option_names()
    named = {w for w in re.findall(r"`([a-z][a-z0-9_]{3,})`", _guide_text())}
    unknown = sorted(named - real - _NOT_OPTIONS)
    assert unknown == [], (
        f"the shipped player guide names {len(unknown)} thing(s) that are not options and not in "
        f"the prose allowlist: {unknown}. Either the option was renamed and the guide was not "
        f"updated, or it is English and belongs in _NOT_OPTIONS.")


def test_the_difficulty_options_are_documented_where_players_will_read_them():
    """CONTRIBUTING rule 11. These shipped with a full writeup in the WRONG file; a gate that only
    checked name validity would have been green the whole time."""
    text = _guide_text()
    for opt in ("minimum_enemy_difficulty", "maximum_enemy_difficulty", "difficulty_ramp_speed"):
        assert opt in text, (
            f"{opt} is a player-facing option and is not mentioned in the SHIPPED player guide "
            f"({os.path.basename(_GUIDE)}). Note there is a second, UNSHIPPED guide at "
            f"release-v0.2/PLAYER-GUIDE.md -- documenting it there does not reach players.")
