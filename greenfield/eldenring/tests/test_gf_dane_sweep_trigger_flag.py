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

🛑🛑 AND THE THIRD HALF, WHICH IS THE ONE THAT WILL SAVE YOU (2026-08-24, the #987 corpus audit).
The obvious next move after this fix is to run the same predicate over the whole corpus and re-key
everything it names. `tools/audit_sweep_trigger_flags.py` does the census: of 244 trigger keys, 145
are set directly, 79 through the parameterized-init shape, and **20 are set as flags NOWHERE in the
corpus** -- the three Scadutree Avatar proxies and 17 duo/phase partner entities.

THAT LIST IS NOT A BUG LIST, and this repo already holds the logs that prove it:

    tests/fixtures/sweep_kill_bobler_scadutree.log
        12:58:20  sweep-watch: census -- 1 group(s), 0 already set: [2050480810(49)]
        13:03:47  sweep-watch: trigger flag 2050480810 -> SET (49 member(s) in its group)
        13:03:47  Received item: Boss sweep (Scadu Altus)
    tests/fixtures/sweep_kill_suppressed_head.log
        14:10:05  sweep-watch: trigger flag 31220801 -> SET (12 member(s) in its group)
        14:10:05  sweep-watch: trigger flag 31220802 -> SET (12 member(s) in its group)

Three of the twenty were OBSERVED FIRING AND PAYING OUT in captured player sessions. Whatever
writes them is not an EMEVD flag instruction -- it is the same unwritten mechanism every
entity-keyed interior sweep has always rested on, and the premise `flag_equals_id` encodes.
**SUFFICIENT IS NOT NECESSARY**: corpus-absence is a lead to check against in-game evidence, the
way Spinks' report drove this issue, never a licence to re-key a working trigger. Re-keying is not
free -- measured 2026-08-24, merging the three Avatar proxies onto 2050480800 moved the sweep
ownership digest 991951420a8525a4 -> 5847d65898b36345, re-owned 33 member links and took
MAJOR_SWEEP_TRIGGERS 40 -> 41, all to "fix" a sweep the logs show working.

Run:  python -m pytest greenfield/eldenring/tests/test_gf_dane_sweep_trigger_flag.py
"""
import os

import pytest

pytest.importorskip("worlds.eldenring")

from worlds.eldenring.boss_healthbars import BOSS_HEALTHBARS  # noqa: E402
from worlds.eldenring.boss_sweeps import DUNGEON_SWEEPS, SWEEP_REGION  # noqa: E402

DANE_DEFEAT_FLAGS = {2049440800: "m61_49_44", 2050430800: "m61_50_43"}
DANE_ENTITY_IDS = (2049440710, 2050430710)
# Scadutree Avatar, m61_50_48 -- three phase entries, no derivable defeat flag, entity-keyed.
NO_DERIVATION_ENTITY_KEYS = (2050480810, 2050480811, 2050480812)
# Entity-keyed triggers the EMEVD corpus sets as flags NOWHERE and that a captured player session
# nonetheless shows FIRING. flag -> (fixture log, the line that witnesses it).
OBSERVED_FIRING_ENTITY_KEYS = {
    2050480810: ("sweep_kill_bobler_scadutree.log",
                 "sweep-watch: trigger flag 2050480810 -> SET"),
    31220801: ("sweep_kill_suppressed_head.log",
               "sweep-watch: trigger flag 31220801 -> SET"),
    31220802: ("sweep_kill_suppressed_head.log",
               "sweep-watch: trigger flag 31220802 -> SET"),
}


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


@pytest.mark.parametrize("flag,witness", sorted(OBSERVED_FIRING_ENTITY_KEYS.items()))
def test_a_key_the_corpus_never_sets_can_still_fire_in_game(flag, witness):
    """The refutation, pinned: these entity-keyed triggers are in the audit's NEVER-SET list AND on
    record firing. Keep the witness beside the claim so the next corpus-wide audit cannot conclude
    they are dead and re-key them (#987; tools/audit_sweep_trigger_flags.py)."""
    log_name, line = witness
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", log_name)
    if not os.path.isfile(path):
        pytest.skip("%s is repo-only" % log_name)
    text = open(path, encoding="utf-8").read()
    assert line in text, (
        "%s no longer witnesses %d firing. That log is the ONLY evidence that a trigger the EMEVD "
        "sets nowhere still pays out; without it the corpus audit's NEVER-SET list reads as a bug "
        "list and someone re-keys a working sweep (#987)." % (log_name, flag))
    assert flag in BOSS_HEALTHBARS, (
        "trigger %d was re-keyed away, but %s shows it FIRING and paying out. Corpus-absence is a "
        "lead, not a defect -- SUFFICIENT IS NOT NECESSARY (#987)." % (flag, log_name))
