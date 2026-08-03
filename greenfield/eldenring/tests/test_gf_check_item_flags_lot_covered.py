"""#321 -- checkItemFlags must not arm an id whose every backing check is neutralised at its LOT.

THE DEFECT (boblerrr, Nexus, 2026-08-03): a vanilla WEAPON that backs a check is eaten by the
id-keyed suppressor no matter where it came from. `detour.rs` only ever sees `raw_id` off the
AddItemFunc buffer, so it cannot tell a check pickup from a farmed drop. A suppressed CHECK pickup is
harmless -- the AP grant delivers instead -- but a suppressed NON-check copy has no grant behind it
and is simply destroyed.

THE FALSE PREMISE this removes, `features/check_lots.py` header verbatim:

    "GOODS slots only. Weapon/armor check wares stay on the id-keyed suppressor, which is already
     sound for them: a weapon is essentially never farmable, so it lives in the check-only set and
     cannot eat a legitimate source."

`enemy_drops.rs` refutes it in the client tree: 4891 enemy lots carry no flag (farmable) and its
reroll rewrites "only the GOODS slots -- weapon/armor/talisman drop slots keep their vanilla
contents." So a farmable enemy CAN drop a vanilla weapon that backs a check, and every such drop was
eaten -- the 2026-07-11 Golden Rune [1] incident, surviving on the non-goods side.

THE RULE ASSERTED HERE: `check_lots` repoints a check's own lot at the placeholder -- for goods since
2026-07-14 and for non-goods since CAN_WRITE_SLOT_CATEGORY -- so an id whose EVERY backing check is
lot-covered has nothing left to suppress. Arming it is pure downside.

Measured on the full-region scope 2026-08-03: 1289 armed ids -> 211 (all 475 goods and 285 of 367
weapons dropped).

SCOPE, stated so nobody reads more into a green suite than it earns: this does NOT close #321. The
residue is the LOT-LESS checks (EMEVD awards), which have no source to neutralise and keep eating
non-check copies -- weapon 0x6acfc0, the id in boblerrr's log, is one of them.
`test_lot_less_checks_stay_armed` pins that residue on purpose.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase

from worlds.eldenring.check_lots_data import CHECK_LOT_FLAGS  # noqa: E402


def _flagset(flags):
    return {int(f) for f in flags}


class CheckItemFlagsLotCoverage(WorldTestBase):
    game = "Elden Ring"
    run_default_tests = False
    options = {"num_regions": 0, "item_shuffle": True}

    def test_no_armed_id_is_fully_lot_covered(self):
        # THE FIX. Every emitted id must keep at least ONE backing check that the lot pass cannot
        # neutralise; otherwise the entry can only ever eat a legitimate non-check copy.
        sd = self.world.fill_slot_data()
        offenders = [int(full) for full, flags in sd.get("checkItemFlags", {}).items()
                     if _flagset(flags) <= CHECK_LOT_FLAGS]
        assert not offenders, (
            "%d id(s) are armed although EVERY backing check is repointed at the placeholder, so "
            "there is nothing left to suppress and the entry can only eat a farmed / awarded copy "
            "(#321). Sample: %s" % (len(offenders), [hex(x) for x in sorted(offenders)[:8]]))

    def test_partially_covered_ids_stay_armed(self):
        # The subset test must be FULL, not "any". `should_suppress` needs EVERY mapped flag
        # collected, so an id with one uncovered backing check still has a real check to protect.
        # Dropping those would reintroduce the vanilla-ware leak the table exists to stop. This
        # test exists so a future "drop on ANY covered flag" rewrite fails loudly here.
        sd = self.world.fill_slot_data()
        emitted = sd.get("checkItemFlags", {})
        for full, flags in emitted.items():
            fs = _flagset(flags)
            if fs & CHECK_LOT_FLAGS and not fs <= CHECK_LOT_FLAGS:
                assert str(full) in emitted, \
                    "partially-covered id %s was dropped -- its uncovered check would leak" % full

    def test_lot_less_checks_stay_armed(self):
        # The residue is load-bearing: a check with no item lot (EMEVD award) cannot be neutralised
        # at the source, so the id-keyed suppressor is the ONLY mechanism it has. If this ever goes
        # empty the drop rule has become too broad.
        sd = self.world.fill_slot_data()
        lotless = [full for full, flags in sd.get("checkItemFlags", {}).items()
                   if not (_flagset(flags) & CHECK_LOT_FLAGS)]
        assert lotless, (
            "checkItemFlags emitted NO lot-less id. Either every check is now lot-covered -- in "
            "which case delete the feature outright and say so -- or the drop rule is eating the "
            "residue it must keep.")

    def test_the_table_did_not_go_empty(self):
        # Emptiness floor. An empty table makes the client log `vanilla suppressor INERT` and every
        # lot-less check leaks its vanilla ware -- the failure mode this change is most likely to
        # produce, and one a green suite would otherwise report as a pass.
        sd = self.world.fill_slot_data()
        assert sd.get("checkItemFlags"), "checkItemFlags is empty -- the suppressor would go INERT"

    def test_the_lot_flag_table_is_populated(self):
        # Guards the OTHER silent failure: if CHECK_LOT_FLAGS regenerates empty (stale
        # check_lots_data.py), every test above passes vacuously and the drop stops happening.
        assert len(CHECK_LOT_FLAGS) > 1000, \
            "CHECK_LOT_FLAGS has %d entries -- expected the full check-lot flag set (~4290); a " \
            "stale or pre-#321 check_lots_data.py makes the drop rule a no-op" % len(CHECK_LOT_FLAGS)

    def test_no_emitted_flag_is_mapped_by_two_ids(self):
        # ⭐ THE ENFORCING GATE for the client-side FLAG-SET DISARM.
        #
        # The client may release an armed id once the check's OWN acquisition flag fires, instead of
        # waiting for the server to report it collected. That is only sound while no flag is mapped
        # by TWO ids: if it were, picking up one id's check would set a flag that releases the OTHER
        # id whose check has not fired -- which is exactly the Traveler's Clothes leak (item
        # 0x100f90c4 / flag 15007980, playtest 2026-07-03) that forced collected-set keying in the
        # first place.
        #
        # Measured 2026-08-03: every such pair lives inside the 1078 ids the lot-coverage drop above
        # removes, so the emitted residue is shared-flag-free. That is a PROPERTY OF THE DATA, not of
        # the code, so it needs a gate -- otherwise a future regen can quietly reintroduce the leak
        # into a client that has already stopped waiting for the collected-set.
        #
        # 🛑 If this ever fires, the client disarm is UNSOUND for this seed. Do not weaken this test;
        # either keep the offending ids out of the emitted table, or turn the disarm off.
        sd = self.world.fill_slot_data()
        owners = {}
        for full, flags in sd.get("checkItemFlags", {}).items():
            for f in _flagset(flags):
                owners.setdefault(f, []).append(full)
        shared = {f: ids for f, ids in owners.items() if len(ids) > 1}
        assert not shared, (
            "%d acquisition flag(s) are mapped by more than one emitted FullID, so setting one "
            "id's flag would release another id whose check has not fired -- the flag-set disarm "
            "is unsound here. Sample: %s"
            % (len(shared), {f: ids for f, ids in list(shared.items())[:4]}))
