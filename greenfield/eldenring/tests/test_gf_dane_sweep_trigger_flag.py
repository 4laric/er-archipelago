"""Dryleaf Dane's two sweeps must key on his DEFEAT FLAGS, not his entity ids (#987).

MOTIVATING CASE (CONTRIBUTING rule 11), Spinks via #987: killing Dryleaf Dane paid his own drop and
nothing else -- both of his sweeps sat armed forever. 41 checks (24 + 17, both Scadu Altus).

THE BUG. `tools/datamine_boss_healthbars.py` re-keys a trigger by its EMEVD-derived defeat flag
only for `field`-class bosses. m61, the DLC overworld, is deliberately classed `legacy` (so its
sweeps get the region-divvy path instead of a Chebyshev neighbourhood the field pass cannot build
for m61 tiles) -- so it inherited field's "defeat flag == entity id" ASSUMPTION without field's
EMEVD check. For 27 of 28 m61 bosses the assumption happens to hold. For Dane it does not:

    event/m61_49_44_00.emevd.dcx.js  $Event(2049442800)   (unparameterized)
        WaitFor(CharacterDead(2049440710) && EventFlag(2049442810));
        HandleBossDefeatAndDisplayBanner(2049440710, TextBannerType.EnemyFelled);
        ...  SetNetworkconnectedEventFlagID(2049440800, ON);
    event/m61_50_43_00.emevd.dcx.js  $Event(2050432800)   -> SetNetworkconnectedEventFlagID(2050430800, ON)

`2049440710` / `2050430710` are ENTITY ids and are set as event flags NOWHERE in the corpus, so the
client's flag-watch polled two numbers the game never sets. This is a VANILLA defect -- nothing to
do with enemy randomisation, which cannot move a `CharacterDead(<placement>)` wait.

🛑 WHY THE SECOND HALF OF THIS TEST EXISTS. The fix must NOT reuse field's drop-loudly rule. Three
m61 entries (the Scadutree Avatar phases) have NO derivable defeat flag; dropping them would delete
16 members' sweeps to fix 41. The gate keeps the existing entity key when no flag can be derived,
and that behaviour is pinned here so a later tightening cannot silently trade one bug for another.

Run:  python -m pytest greenfield/eldenring/tests/test_gf_dane_sweep_trigger_flag.py
"""
import pytest

pytest.importorskip("worlds.eldenring")

from worlds.eldenring.boss_healthbars import BOSS_HEALTHBARS  # noqa: E402
from worlds.eldenring.boss_sweeps import DUNGEON_SWEEPS, SWEEP_REGION  # noqa: E402

DANE_DEFEAT_FLAGS = {2049440800: "m61_49_44", 2050430800: "m61_50_43"}
DANE_ENTITY_IDS = (2049440710, 2050430710)
# Scadutree Avatar, m61_50_48 -- three phase entries, no derivable defeat flag, entity-keyed.
NO_DERIVATION_ENTITY_KEYS = (2050480810, 2050480811, 2050480812)


@pytest.mark.parametrize("flag,tile", sorted(DANE_DEFEAT_FLAGS.items()))
def test_dane_is_keyed_by_his_defeat_flag(flag, tile):
    assert flag in BOSS_HEALTHBARS, (
        "boss_healthbars lost Dryleaf Dane's %s trigger %d. That flag is what the EMEVD actually "
        "sets on his death; keying anything else is a sweep that can never fire (#987)." % (tile, flag))
    assert BOSS_HEALTHBARS[flag][1] == tile
    assert "Dryleaf Dane" in BOSS_HEALTHBARS[flag][3]
    members = DUNGEON_SWEEPS.get(flag)
    assert members, "sweep %d (%s) has no members -- Dane's %d checks are stranded again" % (
        flag, tile, len(members or ()))
    assert SWEEP_REGION.get(flag) == "Scadu Altus"


@pytest.mark.parametrize("ent", DANE_ENTITY_IDS)
def test_danes_entity_ids_are_not_sweep_triggers(ent):
    # The whole defect in one assertion: an entity id that no EMEVD ever passes to
    # Set[Networkconnected]EventFlagID cannot be a trigger the client can ever see fire.
    assert ent not in BOSS_HEALTHBARS, (
        "%d is Dryleaf Dane's ENTITY id, not a flag -- it is set as an event flag nowhere in the "
        "corpus, so its sweep never fires (#987)." % ent)
    assert ent not in DUNGEON_SWEEPS
    assert ent not in SWEEP_REGION


@pytest.mark.parametrize("ent", NO_DERIVATION_ENTITY_KEYS)
def test_m61_entries_without_a_derivation_keep_their_entity_key(ent):
    assert ent in BOSS_HEALTHBARS, (
        "m61 entry %d vanished. It has no derivable defeat flag, so the m61 re-key must KEEP its "
        "existing entity key -- never drop it: dropping deletes a live sweep (#987)." % ent)
    assert "Scadutree Avatar" in BOSS_HEALTHBARS[ent][3]
    assert DUNGEON_SWEEPS.get(ent), "Scadutree Avatar sweep %d lost its members" % ent


def test_every_m61_trigger_flag_is_a_flag_the_game_can_set():
    """Corpus-wide shape check: no m61 trigger may keep an entity-id key that ENDS in a non-flag
    suffix. Dane's ...0710 was the only one; the Avatar's ...08xx keys are in the 08xx defeat-flag
    band the game does use, which is why keeping them is safe."""
    offenders = sorted(k for k, v in BOSS_HEALTHBARS.items()
                       if v[0].startswith("m61") and not (str(k)[6:8] == "08"))
    assert offenders == [], (
        "m61 trigger(s) %r are not in the 08xx defeat-flag band -- almost certainly raw entity ids "
        "that no EMEVD sets, i.e. sweeps that can never fire (#987)." % offenders)
