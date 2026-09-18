"""Grace attunement -- a region hands over ONE grace on unlock, and the rest bloom once the player
has physically touched `grace_attunement` of them.

The point of the option is to cut TRAVERSAL, so the invariants that matter are conservation (the
gate can never lose or invent a grace relative to the ungated bundle) and reachability (a gate that
can never fire, or that fires to grant nothing, is a bug wearing a setting's clothes).

🛑 THE DEFAULT MUST BE A BYTE-EXACT NO-OP. `grace_attunement` defaults to 0 and every seed rolled
before this feature existed has to keep generating identically, so the off case is asserted against
the SAME seed's ungated bundles rather than against a hand-typed table.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring import contract  # noqa: E402
from worlds.eldenring.tables.region_graces import REGION_GRACE_POINTS  # noqa: E402
from worlds.eldenring.tables.region_open_flags import REGION_OPEN_FLAGS  # noqa: E402
from worlds.eldenring.region_spine import REGION_PARENT  # noqa: E402
from worlds.eldenring.features.graces import _ENTRANCE_COMPONENT_GRACES  # noqa: E402

GAME = "Elden Ring"
_THRESHOLD = 4


class _Base(WorldTestBase):
    game = GAME
    run_default_tests = False

    def _slot(self):
        return self.world.fill_slot_data()

    def _graces(self):
        return self._slot()[contract.REGION_GRACES]

    def _pair(self):
        """One snapshot, both keys.

        🛑 NEVER read `region_graces` from one fill_slot_data() and `grace_attunement` from another.
        That is what caught the non-idempotent anchor draw, and a test that does it accidentally is
        asserting across two different worlds.
        """
        slot = self._slot()
        return slot[contract.REGION_GRACES], slot[contract.GRACE_ATTUNEMENT]


class AttunementOff(_Base):
    options = {"num_regions": 0, "grace_attunement": 0}

    def test_key_is_absent_when_the_option_is_off(self):
        # An absent key is the contract's own `required: false` case, and it is what every
        # already-rolled seed emits. Emitting an empty dict instead would still be a change.
        self.assertNotIn(contract.GRACE_ATTUNEMENT, self._slot())

    def test_no_client_feature_is_demanded_when_the_option_is_off(self):
        # 🛑 The handshake makes an unsupporting client REFUSE the connect. Demanding a feature on
        # a default seed would lock out every existing build for a setting nobody turned on.
        req = self._slot().get(contract.REQUIRES_CLIENT_FEATURES) or []
        self.assertNotIn("grace_attunement", req)

    def test_every_bundle_is_the_full_region(self):
        # Off is a byte-exact no-op: every kept region's bundle is its full grace set -- gated
        # children included, since no wall is armed anywhere (Raya since 2026-08-16, Leyndell
        # since the 2026-09-14 rune-wall retirement). The REGION_PARENT skip this test used to
        # carry died with the last wall it excused.
        graces = self._graces()
        for region, points in REGION_GRACE_POINTS.items():
            self.assertEqual(sorted(graces.get(f"{region} Lock", [])), sorted(points),
                             f"{region}'s bundle moved with the option OFF")


class AttunementOn(_Base):
    options = {"num_regions": 0, "grace_attunement": _THRESHOLD}

    def test_the_gate_conserves_every_grace(self):
        # anchor + members must reconstruct the ungated bundle EXACTLY -- no grace may be dropped
        # (unreachable warp) or duplicated (a bloom that re-grants what the Lock already lit).
        graces, gates = self._pair()
        for key, gate in gates.items():
            region = key[: -len(" Lock")]
            self.assertEqual(sorted(graces[key] + gate["members"]), sorted(REGION_GRACE_POINTS[region]),
                             f"{region}: anchor + members != the region's grace points")

    def test_one_entry_per_component_is_handed_over_on_unlock(self):
        graces, gates = self._pair()
        for key in gates:
            region = key[: -len(" Lock")]
            expected = len(_ENTRANCE_COMPONENT_GRACES.get(region, [None]))
            self.assertEqual(len(graces[key]), expected, f"{key} must preserve component entries")

    def test_the_anchor_is_the_regions_own_front_door(self):
        # The default anchor is the region's own front door: REGION_OPEN_FLAGS where it is a real
        # grace, else the derived entrance (a gated child's open flag is synthetic -- a kick latch,
        # never a bundle member -- so entrance_grace over the bundle stands in, the same grace the
        # `entrance` tier hands out). Either way the anchor is somewhere the player arrives, never
        # a warp past a wall.
        from worlds.eldenring.features.graces import entrance_grace  # noqa: E402
        graces, gates = self._pair()
        for key in gates:
            region = key[: -len(" Lock")]
            if region in _ENTRANCE_COMPONENT_GRACES:
                self.assertEqual(graces[key], _ENTRANCE_COMPONENT_GRACES[region])
                continue
            front = REGION_OPEN_FLAGS.get(region)
            want = front if front in REGION_GRACE_POINTS[region] else entrance_grace(
                list(REGION_GRACE_POINTS[region]), region)
            self.assertEqual(graces[key][0], want,
                             f"{region}'s anchor is not its front door")

    def test_no_gate_can_bloom_an_empty_set(self):
        # The `touchable <= threshold` skip exists for exactly this. A region gated at its own
        # boundary attunes only on its last grace and then grants nothing.
        for key, gate in self._slot()[contract.GRACE_ATTUNEMENT].items():
            self.assertGreater(len(gate["bloom"]), 0, f"{key} would attune and grant nothing")
            self.assertGreaterEqual(len(gate["members"]), gate["threshold"],
                                    f"{key} can never reach its own threshold")

    def test_withheld_bundles_are_never_gated(self):
        # 🛑 THE PREMISE IS VACUOUS ON EVERY CURRENT SEED -- and the test stays, pointed at both
        # directions, so a returning wall cannot slip back in. A gated child with an EMPTY bundle
        # (an armed wall withholding it) must never appear in the gates: handing it an anchor would
        # put a warp target on the far side of a wall the GAME enforces -- the 2026-07-14 bug. A
        # child WITH a bundle (every child, since the Raya 2026-08-16 and Leyndell 2026-09-14
        # retirements) gates exactly like an ungated region, and conservation (above) owns it.
        graces, gates = self._pair()
        kept = set(self.world._kept())
        self.assertTrue([c for c in REGION_PARENT if c in kept],
                        "no gated child is kept this seed -- the conditional below proves nothing")
        for child in REGION_PARENT:
            if child not in kept:
                continue
            key = f"{child} Lock"
            if not graces.get(key):
                self.assertNotIn(key, gates, f"{child} is withheld and must not be gated")

    def test_the_client_feature_is_demanded(self):
        self.assertIn("grace_attunement", self._slot()[contract.REQUIRES_CLIENT_FEATURES])

    def test_slot_data_is_idempotent(self):
        # ⭐ THE MOTIVATING CASE. `_attune_split` used to draw its random anchor inline, so a second
        # fill_slot_data() rolled a different one and the two calls disagreed about which grace the
        # region hands over. Asserted on the DEFAULT anchor too because the memo is shared.
        first, second = self.world.fill_slot_data(), self.world.fill_slot_data()
        self.assertEqual(first[contract.REGION_GRACES], second[contract.REGION_GRACES])
        self.assertEqual(first[contract.GRACE_ATTUNEMENT], second[contract.GRACE_ATTUNEMENT])

    def test_the_gate_is_not_vacuous(self):
        # ⭐ Guards against the whole feature silently skipping every region -- which is how a
        # conservation test that iterates an EMPTY dict passes while shipping nothing.
        self.assertGreater(len(self._slot()[contract.GRACE_ATTUNEMENT]), 10)


class AttunementRandomAnchor(_Base):
    options = {"num_regions": 0, "grace_attunement": _THRESHOLD, "grace_attunement_anchor": "random_grace"}

    def test_a_random_anchor_is_still_a_real_grace_of_its_own_region(self):
        # REGION_GRACE_POINTS already excludes boss-gated and arena graces, so every candidate is a
        # physically-present warp point -- but the anchor must come from the RIGHT region's list.
        graces, gates = self._pair()
        for key in gates:
            region = key[: -len(" Lock")]
            self.assertIn(graces[key][0], REGION_GRACE_POINTS[region],
                          f"{region}'s random anchor is not one of its own graces")

    def test_a_random_anchor_is_stable_across_calls(self):
        first, second = self.world.fill_slot_data(), self.world.fill_slot_data()
        self.assertEqual(first[contract.REGION_GRACES], second[contract.REGION_GRACES],
                         "the random anchor must be drawn ONCE, not per fill_slot_data() call")
        self.assertEqual(first[contract.GRACE_ATTUNEMENT], second[contract.GRACE_ATTUNEMENT])

    def test_conservation_holds_for_a_random_anchor_too(self):
        graces, gates = self._pair()
        for key, gate in gates.items():
            region = key[: -len(" Lock")]
            self.assertEqual(sorted(graces[key] + gate["members"]), sorted(REGION_GRACE_POINTS[region]))
