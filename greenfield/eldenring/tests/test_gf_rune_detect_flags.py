"""No AP check is ever DETECTED on a flag in vanilla's Great Rune possession band (170-179).

THE COLLISION, from the decompiled corpus in this repo's own `gen_inputs.db` bundle:

  * `elden_ring_artifacts/event/common.emevd.dcx.js:1110` -- $Event(730)
    大ルーン所持数チェック ("check number of large runes in possession") is
    `CountEventFlags(TargetEventFlagType.EventFlag, 170, 179) >= countThreshold`. The WHOLE BAND is
    vanilla's rune counter; its threshold-2 output (flag 182) is what the 王都の封印 capital seal
    reads. Anything living in that band is read by the game as "the player holds a Great Rune".
  * `elden_ring_artifacts/event/common.emevd.dcx.js:3124` -- $Event(6905) fills the band from the
    demigod remembrance reward flags: 510010->171, 510300->172, 510040->173, 510220->174,
    510120->175, 510200->176, 197->177.

WHY THIS IS PINNED (client lost-check scenario, 2026-09-13). clients #685 makes the client SET
171-177 when it DELIVERS a Great Rune, so third-party rune counters -- thefifthmatt's gates, and
vanilla's own $Event(730) capital wall -- agree with the AP inventory instead of reading zero for a
player holding six runes. But those same flags were the six boss-rune locations' DETECTION flags,
and each is its boss lot's `getItemFlagId`: setting 171 before Godrick dies marks lot 10010
collected, the pickup never fires the flag the poll waits on, and check 7770001 can never be sent.
Delivered rune, lost location, and an unwinnable seed if the goal wanted that check.

`features/great_runes.GREAT_RUNE_DETECT_FLAGS` moves the six polls onto the BOSS DEFEAT flags and
leaves the band to the client. This file is what stops the band being re-colonised later: the next
person to put a check on 171-176 has to read the paragraph above first.

NB the data.py ROW is deliberately untouched -- name, ap_id and flag all still say 171. That is the
whetblade precedent (CHANGELOG v0.2.18, "receiving a whetblade collected its own location"): a
detection repoint is not a rename, and 171 is still the acquisition flag the lot and `check_lots`
are keyed on. Only the EMITTED detection flag moves, which is a split `coverage.py` already models
(`rec.detect_flag = emitted_location_flags.get(ap_id, flag)`).
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.features.great_runes import (  # noqa: E402
    GREAT_RUNE_DETECT_FLAGS, detect_flag_overrides)
from worlds.eldenring.tables.data import LOCATIONS  # noqa: E402
from worlds.eldenring.tables.boss_healthbars import BOSS_HEALTHBARS  # noqa: E402

GAME = "Elden Ring"

# Vanilla's Great Rune possession band -- $Event(730) counts exactly this range.
POSSESSION_BAND = range(170, 180)

# The six, stated independently of the feature so a typo there cannot silently agree with itself:
# ap_id -> (possession flag it used to detect on, boss defeat flag it detects on now, boss name).
EXPECTED = {
    7770001: (171, 10000800, "Godrick the Grafted"),
    7770002: (172, 1252380800, "Starscourge Radahn"),
    7770003: (173, 11000800, "Morgott, the Omen King"),
    7770004: (174, 16000800, "Rykard, Lord of Blasphemy"),
    7770005: (175, 12050800, "Mohg, Lord of Blood"),
    7770006: (176, 15000800, "Malenia, Blade of Miquella"),
}


def test_the_repoint_table_says_what_this_file_says():
    """The feature's table and this file's table are written out separately and must agree."""
    assert GREAT_RUNE_DETECT_FLAGS == {ap: defeat for ap, (_p, defeat, _n) in EXPECTED.items()}


def test_every_target_is_a_real_boss_defeat_flag_for_the_right_boss():
    """The repoint targets are DEFEAT flags, cross-checked against the repo's own boss name
    authority -- not hand-copied numbers. This is what catches the festival-alias trap: Radahn's
    persistent defeat flag is the `12`-prefix 1252380800, and the `10`-prefix 1052380800 that
    `BOSS_REWARD_DEFEAT` carries would never fire a poll."""
    for ap_id, (_poss, defeat, who) in EXPECTED.items():
        assert defeat in BOSS_HEALTHBARS, (
            f"{ap_id}: {defeat} is not a known boss defeat flag -- if this is a remembrance REWARD "
            f"flag (510xxx) it is one hop short, and it is already some other check's detect flag")
        assert BOSS_HEALTHBARS[defeat][3] == who, (
            f"{ap_id}: flag {defeat} is {BOSS_HEALTHBARS[defeat][3]!r}, not {who!r}")


def test_no_repoint_target_is_in_the_possession_band():
    """The whole point: the new flags must be OUTSIDE 170-179, or nothing was fixed."""
    for ap_id, flag in GREAT_RUNE_DETECT_FLAGS.items():
        assert flag not in POSSESSION_BAND, f"{ap_id} repointed to {flag}, still inside the band"


def test_no_repoint_target_collides_with_another_locations_detect_flag():
    """🛑 THE REASON THE TARGET IS THE DEFEAT FLAG AND NOT THE 510xxx FLAG $Event(6905) READS.

    Every 510xxx remembrance reward flag is ALREADY the detect flag of its own Remembrance check
    (510010 = `Remembrance of the Grafted` 7770653, and so on). Repointing a rune onto one would
    put two locations on one flag, so picking up the Remembrance would also send the Great Rune
    check -- the same lost/ghost-check class, moved one flag to the left."""
    table_flags = {flag for rows in LOCATIONS.values() for (_n, _ap, flag) in rows}
    for ap_id, flag in GREAT_RUNE_DETECT_FLAGS.items():
        assert flag not in table_flags, (
            f"{ap_id} repointed to {flag}, which is already some location's detect flag")


class TestEmittedFlagsAvoidThePossessionBand(WorldTestBase):
    """THE INVARIANT, asserted over what is actually SENT rather than over the table."""
    game = GAME
    options = {"num_regions": 0}  # keep everything, so all six runes are in scope

    def test_no_emitted_location_detects_on_the_possession_band(self):
        emitted = {int(k): int(v) for k, v in self.world.fill_slot_data()["locationFlags"].items()}
        offenders = {ap: fl for ap, fl in emitted.items() if fl in POSSESSION_BAND}
        assert not offenders, (
            f"{len(offenders)} location(s) detect on vanilla's Great Rune possession band "
            f"170-179: {sorted(offenders.items())[:10]}. common.emevd $Event(730) counts that whole "
            f"band as runes held, and clients #685 writes into it on every rune delivery -- a check "
            f"detected there is collected the moment the client hands the player a rune.")

    def test_the_six_are_emitted_on_their_boss_defeat_flags(self):
        emitted = {int(k): int(v) for k, v in self.world.fill_slot_data()["locationFlags"].items()}
        for ap_id, (_poss, defeat, who) in EXPECTED.items():
            assert emitted.get(ap_id) == defeat, (
                f"{who}'s rune check {ap_id} emitted {emitted.get(ap_id)}, expected {defeat}")

    def test_the_data_py_row_is_untouched(self):
        """Names are datapackage identity and the flag column is the ACQUISITION flag the lot and
        check_lots are keyed on. Only the emitted detection flag moves."""
        rows = {ap: (name, flag) for r in LOCATIONS.values() for (name, ap, flag) in r}
        for ap_id, (poss, _defeat, _who) in EXPECTED.items():
            name, flag = rows[ap_id]
            assert flag == poss, f"{ap_id} data.py flag moved to {flag}; it must stay {poss}"
            assert f"[f{poss}]" in name, f"{ap_id} name {name!r} lost its [f{poss}] identity suffix"


class TestReducedSeedPublishesOnlyWhatItKept(WorldTestBase):
    """The override is SCOPED. `core._base_slot_data` merges `gf_extra_location_flags` blind and
    then back-fills loc_regions from data.LOCATIONS, so an unscoped override would invent a check
    in a region the draw never kept."""
    game = GAME
    options = {"num_regions": 3}

    def test_overrides_are_a_subset_of_the_seeds_own_locations(self):
        emitted = {int(k) for k in self.world.fill_slot_data()["locationFlags"]}
        for ap_id in detect_flag_overrides(self.world):
            assert ap_id in emitted, f"{ap_id} overridden but not in this seed"

    def test_no_emitted_location_detects_on_the_possession_band(self):
        emitted = {int(k): int(v) for k, v in self.world.fill_slot_data()["locationFlags"].items()}
        assert not {ap: fl for ap, fl in emitted.items() if fl in POSSESSION_BAND}
