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

# Same two-place resolve, for the file NEXUS-DESCRIPTION.txt sends a confused player to. It ships
# from release/ rather than beside the package, so the installed-world leg looks under <repo>.
_KNOWN_ISSUES = next((p for p in (os.path.join(_GF_PKG, "release", "KNOWN-ISSUES.md"),
                                  os.path.join(_REPO, "release", "KNOWN-ISSUES.md"))
                      if os.path.isfile(p)), "")

_GETTING_UNSTUCK = next((p for p in (os.path.join(_GF_PKG, "release", "GETTING-UNSTUCK.md"),
                                     os.path.join(_REPO, "release", "GETTING-UNSTUCK.md"))
                         if os.path.isfile(p)), "")

# Backticked snake_case words that are ENGLISH, not options. Keep this list SHORT and justified --
# every entry is a place the gate cannot help, so a long list means the gate is decorative.
_NOT_OPTIONS = {
    "spine",        # a VALUE of num_regions_order ("`spine` order"), not a key
    "rolled",       # ditto
    # `vanilla_order` is the CURRENT second value of num_regions_order (#563 brought the fixed
    # order back under that name after `spine` was deleted). Same category as the two above: a
    # value the guide has to name to explain the option. 🛑 It is here because the guide started
    # naming it 2026-08-12 and this gate went red -- which is the gate working. `spine` stays
    # listed because the migration note still mentions it, not because it is still a choice.
    "vanilla_order",
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


def _unstuck_text():
    assert _GETTING_UNSTUCK, (
        "the shipped GETTING-UNSTUCK.md was not installed beside the world; a rescue guide that "
        "package_release.ps1 or tools/gf_test.py omits does not reach players or CI")
    with open(_GETTING_UNSTUCK, encoding="utf-8") as fh:
        return fh.read()


def test_the_rescue_guide_is_linked_and_covers_the_reported_dead_ends():
    """#722's actual support cases, not a generic documentation-exists assertion."""
    guide = _guide_text()
    rescue = _unstuck_text()
    assert "GETTING-UNSTUCK.md" in guide, (
        "the shipped player guide does not lead a trapped player to the rescue guide")
    for witness in (
        "!warp 11102950",
        "!grace liurnia",
        "!give 0x40001fd4",
        "!give 0x4000230a",
        "!setflag 71102 1",
        "!setflag 71105 1",
        "pick up any item",
        r"%LocalAppData%\Programs\garyttierney\me3\log",
        "beside that DLL",
    ):
        assert witness.lower() in rescue.lower(), (
            f"GETTING-UNSTUCK.md lost #722's motivating recovery detail: {witness!r}")


def test_rescue_commands_are_explicitly_scoped_to_the_client_console():
    """A typoed command is worse than no guide: it sends an already-stuck player to a dead end.

    This gate pins the recovery subset rather than duplicating the client's whole help list. The
    client owns that list; the guide says `!help` is the exhaustive source and documents only the
    commands its recovery procedures actually invoke.
    """
    rescue = _unstuck_text()
    commands = set(re.findall(r"!(?:[a-z]+)", rescue))
    assert commands == {"!check", "!flag", "!give", "!grace", "!help", "!setflag", "!warp"}


def _live_option_names():
    from worlds.AutoWorld import AutoWorldRegister
    return set(AutoWorldRegister.world_types[GAME].options_dataclass.type_hints)


def test_the_guide_is_actually_present():
    """Without this the two tests below pass VACUOUSLY -- which is how the guide got out of date in
    the first place."""
    assert _GUIDE, ("the shipped player guide was not found. It is packaged with required = $true, "
                    "so if it has moved, this gate must move with it rather than skip.")


def test_region_unconfirmed_tracker_label_is_explained_to_players():
    """#1024: the F6 tracker exposes this generator label, so the shipped guide must define it."""
    text = re.sub(r"\s+", " ", _guide_text().lower())
    assert "(region unconfirmed)" in text
    assert "exact region has not yet been verified" in text
    assert "cannot hold a progression item" in text


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


def test_the_separate_save_guide_explains_me3_clones_the_vanilla_save():
    """Seeing old character names in the AP menu must not be diagnosed as sharing.

    me3 creates a missing custom save by copying the base save. Without saying
    that, "separate save" sounds like a new empty character list and sends
    players toward an unnecessary Alt Saves installation.
    """
    text = _guide_text().lower()
    assert "copies" in text and "er0000.sl2" in text and "ap_me3.sl2" in text
    assert "not visible" in text and "vanilla" in text
    assert "alt" in text and "saves dll" in text and "not needed" in text


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


_CONFUSE_HEADING = "## Things that will confuse you the first time"
_CURATION_SECTION = "## What fills your junk checks"


def _section(text, heading):
    """The body of one `## ` section: heading to the next `## ` at column 0, or EOF."""
    start = text.find(heading)
    if start < 0:
        return ""
    body = text[start + len(heading):]
    nxt = re.search(r"^## ", body, re.M)
    return body[:nxt.start()] if nxt else body


def test_the_curated_pool_is_disclosed_where_a_confused_player_looks():
    """#617, CONTRIBUTING rule 11, and the reporter was the most experienced player we have.

    > 2026-08-12, boblerrr in the playtest thread: a session spent counting vanilla items he could
    > not find -- tears, staffs, sorceries, incantations, talismans, Ashes of War -- posted as a
    > list of "missing items". Almost none of it was a defect. The filler tail is spent by
    > `curated_filler`, farmable enemy drops carry no flag and can never be checks, and the presence
    > floor injects a fixed roster. **He was surprised the pool was curated at all.**

    The writeup existed and was accurate -- section 8 of 9, around line 400 of 560, reachable only
    by someone already looking for it. `## Things that will confuse you the first time` is the
    section written for exactly this failure mode and had eight entries, none about the pool. The
    closest one framed pool anomalies as the vanilla-item-leak BUG, which is the opposite of the
    answer and sends the player to file a report.

    So the gate is on the SECTION, not the document: an accurate paragraph 250 lines below the place
    a confused player stops reading is how this shipped. It must name the curation and it must point
    at the section that explains it, so the entry stays a signpost rather than becoming a second,
    drifting copy of the recipe.
    """
    text = _guide_text()
    section = _section(text, _CONFUSE_HEADING)
    assert section, (
        f"`{_CONFUSE_HEADING}` is gone from the shipped guide. If it was renamed, this gate must "
        f"move with it rather than pass vacuously -- vacuous doc gates are this file's whole "
        f"origin story.")
    assert "curated_filler" in section or "curated" in section.lower(), (
        f"`{_CONFUSE_HEADING}` says nothing about the item pool being curated. It is the section a "
        f"first-time player reads to tell odd-but-intended from broken, and the single most "
        f"common non-bug report we get is vanilla items missing from the pool (#617).")
    title = _CURATION_SECTION[len("## "):]
    assert _CURATION_SECTION in text, (
        f"the entry above points at `{_CURATION_SECTION}` and that section is not in the guide. A "
        f"signpost to a section that has been renamed or deleted is worse than no signpost.")
    assert title in section, (
        f"`{_CONFUSE_HEADING}` raises the curated pool without pointing at `{_CURATION_SECTION}`, "
        f"which is where the recipe, the defaults and the dials actually live. Name that section "
        f"verbatim: a player who is told the pool is curated and not told where to read about it "
        f"is left exactly as suspicious as before, and an entry that re-explains the recipe inline "
        f"is a second copy that will drift.")


def test_known_issues_lists_the_curated_pool_as_by_design():
    """#617's second half, and it is a routing bug rather than a documentation one.

    release/NEXUS-DESCRIPTION.txt sends every confused player to this exact file, in these words:
    *"The full, honest list -- including the by-design behaviors that get reported as bugs."* Its
    `## By-design behaviours` list had six entries and none of them was the pool. A player doing
    precisely what we told him to do could not find the answer, which is worse than not being told
    where to look.

    Gated in this file rather than a new one because it is the same failure as every gate above it:
    the writeup existed, on a surface the affected player never reaches.
    """
    if not _KNOWN_ISSUES:
        pytest.skip("release/KNOWN-ISSUES.md not found beside the package or at the repo root")
    with open(_KNOWN_ISSUES, encoding="utf-8") as fh:
        text = fh.read()

    section = _section(text, "## By-design behaviours")
    assert section, (
        "`## By-design behaviours` is gone from release/KNOWN-ISSUES.md. NEXUS-DESCRIPTION.txt "
        "advertises it by name as the way to tell by-design from bugs, so if it was renamed both "
        "that file and this gate must move with it.")
    assert "curated_filler" in section, (
        "the by-design list does not name `curated_filler`. It is the recipe that spends the whole "
        "filler tail, on by default, and the reason vanilla items are missing from a seed -- the "
        "most-reported non-bug this project has (#617). A player routed here from the Nexus page "
        "to check whether something is by design must find it here.")
