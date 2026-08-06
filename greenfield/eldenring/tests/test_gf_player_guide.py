"""The SHIPPED player guide must not name an option that does not exist.

WHY THIS FILE EXISTS (2026-07-27, and it is embarrassing)
--------------------------------------------------------
There are TWO files called "Player Guide (v0.2)":

    Elden-Ring-Archipelago-Player-Guide.md   repo root -- SHIPPED (package_release.ps1,
                                             required = $true), linked from README and SETUP.md
    release/PLAYER-GUIDE.md             referenced by NOTHING, packaged by NOTHING

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
    "player_only", "scaled",        # values of global_scadutree_blessing
    # CATEGORY WEIGHTS INSIDE `curated_filler` -- sub-keys of one option, not options themselves.
    # The guide has to name them (they are what a player actually edits), and each is checked for
    # real by test_gf_shipping_yaml_recipe against filler_curation.CuratedFiller.default, which is a
    # stronger gate than name-existence: it compares the shipped numbers to the code's.
    "juice", "stones", "somber_stones", "runes", "throwables", "pots", "greases", "foods", "boluses",
    "junk",         # the drop target when a category over-allocates; prose, not a key
    # VALUES of dungeon_sweep
    "bosses", "minidungeons", "none",
    # VALUES of pool_builder_intensity ("max" doubles as a dungeon_sweep-adjacent word, but all
    # three are option VALUES the guide has to name to explain the rarity floor).
    "normal", "high", "max",
    # VALUES of region_grace_unlock ("all" is already above as a dungeon_sweep value)
    "entrance", "landmarks",
    # VALUES of goal
    "auto", "elden_beast", "promised_consort",
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
            f"release/PLAYER-GUIDE.md -- documenting it there does not reach players.")


def test_the_receiving_is_dead_fingerprint_is_documented_where_players_will_read_it():
    """CONTRIBUTING rule 11, and the same mistake as the one above wearing different clothes.

    The `RandomizerHelper.dll` hook conflict has been written up in full since v0.2 -- in
    release/ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md, a document whose title advertises a
    feature the affected player is not using and will therefore never open. On 2026-08-05 a report
    of exactly this ("the item stays in my inventory instead of being sent anywhere") took a
    multi-step investigation across two logs and the client source to reach an answer we already
    had on disk, because the SHIPPED guide a stuck player does open said nothing about it.

    Gated on the dll name specifically: it is the string a player, or whoever is helping them,
    will search for. A generic "is there a troubleshooting section" check would have been green
    for the whole period this was undiscoverable.
    """
    text = _guide_text()
    assert "RandomizerHelper.dll" in text, (
        "the shipped player guide does not name RandomizerHelper.dll. It is the most common cause "
        "of 'my checks send but I never receive anything', and documenting it only in "
        "release/ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md does not reach a player who does "
        "not already know that is what they are hitting.")


def test_the_separate_save_promise_is_never_unconditional():
    """CONTRIBUTING rule 11, and the third outing for this file's own lesson.

    2026-08-03, boblerrr on the Nexus page: *"even though im using a custom save format it seems
    like it still uses my sl2 save ... i keep seeing my ap file in my regular save so that's a bit
    scary"*. He was right, and our docs had told him otherwise. Three of them promised a separate
    save (`AP_me3.sl2`) with no condition attached, and release/SETUP.md did it **three lines
    above** the paragraph telling him to launch through matt's randomizer instead -- which is the
    one launch path where the promise does not hold, because the redirection lives in the `me3`
    profile's `savefile` line and matt's launcher never reads it.

    The SHIPPED guide said nothing about saves at all, so the player who went looking found
    nothing. Hence this gate, on the shipped file: it must raise the subject, and it must not
    raise it as an unconditional promise. Gated on the paragraph rather than the document, because
    a warning three sections away from the reassurance is how this got shipped in the first place.
    """
    text = _guide_text()
    assert "AP_me3.sl2" in text, (
        "the shipped player guide never mentions the save file. Whether an Archipelago character "
        "lands in the player's real save depends on how they launched, they have no way to guess "
        "that, and the one who found out did so by opening vanilla Elden Ring and seeing it there.")

    paragraphs = [p for p in text.split("\n\n") if "AP_me3.sl2" in p]
    for para in paragraphs:
        lowered = para.lower()
        assert any(word in lowered for word in ("randomiz", "loader", "launch")), (
            "a paragraph names AP_me3.sl2 without saying the separate save depends on the launch "
            "path:\n\n" + para + "\n\nThe separation comes from `savefile` in the me3 profile, "
            "not from the client. Stated flat, this is false for every player following our own "
            "instructions to launch through matt's randomizer.")


def test_the_dlc_region_count_the_guide_states_is_the_real_one():
    """#404, and CONTRIBUTING rule 11 again -- the reporter typed the number we gave him.

    > *"maximum listed regions in the yaml is stated to be 31. for me 31 led to generation failure,
    > 30 works fine"*

    `NumRegions.range_end` is `len(REGIONS)` and has been 30 (17 base + 13 DLC) the whole time; five
    shipped files said 31, so the documented maximum was one past what Archipelago would accept. The
    guide's number has to be checked against the collection, not against 30 -- a DLC region added
    later must move the doc, and a gate written as `== 30` would be the same typed-literal mistake
    this issue is about.
    """
    from worlds.eldenring.data import REGIONS

    claims = [int(n) for n in re.findall(r"(\d+) with the DLC", _guide_text())]
    assert claims, (
        "the shipped guide no longer states a DLC-on region count. If that line moved, this gate "
        "must move with it rather than pass vacuously -- which is how the wrong number survived.")
    assert all(n == len(REGIONS) for n in claims), (
        f"the shipped guide claims {claims} regions with the DLC on; there are {len(REGIONS)}. A "
        f"player who types the documented maximum gets a generation failure.")
