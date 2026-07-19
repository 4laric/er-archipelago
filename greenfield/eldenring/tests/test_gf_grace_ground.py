"""Grace-ground invariant: every force-lit grace stands on ground its own region (or an ancestor)
owns -- the committed-file mirror of gen_data.py's GRACE-GROUND GATE.

THE BUG THIS KILLS (in-game, 2026-07-15): the Charo's lock lit its front-door grace 76841, the
player warped there, and the kick-watch read play_region 6840000 (bucket 68400) -- which
region_play_ids.py assigned to CERULEAN, whose open flag 76831 was still down:

    kick-watch: play_region 6840000 (sub 68400); range [68400,68400] flag 76831 = false
    -> kick = true; SEALED REGION -- Returning to Roundtable

A region lock that warps you onto a sibling's sealed ground is un-shippable. gen_data refuses to
generate it; this suite asserts the COMMITTED outputs agree (they can drift from the gate by a
hand edit or a stale regen -- the exact classes tests exist for).

Ground truth is greenfield/grace_ground.tsv (tools/datamine_grace_ground.py): per grace, the
play-region bucket(s) of the ground it stands on, derived from MSB Region/PlayArea volumes +
PlayRegionParam tile defaults, calibrated against the in-game Charo's measurement. Graces whose
ground is underivable ('-') or sits on an unassigned (kick-permissive) bucket cannot be judged
and are not judged: unverified is not the same thing as failing.

Loads committed files by path (no Archipelago machinery); SKIPS visibly if the tsv is absent.
"""
import importlib.util
import os
import sys
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)          # installed: <ap>/worlds/eldenring ; source: greenfield/eldenring
GREENFIELD = os.path.dirname(GF_PKG)    # source tree only: greenfield/


def _first(*cands):
    return next((p for p in cands if os.path.isfile(p)), None)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GROUND = _first(os.path.join(GF_PKG, "grace_ground.tsv"),
                os.path.join(GREENFIELD, "grace_ground.tsv"))


def _region_parent():
    """region_spine.REGION_PARENT via a real package import (it does `from .data import REGIONS`),
    without dragging in Archipelago: register a bare `eldenring` package shim first."""
    if "worlds.eldenring" in sys.modules:  # running installed under AP -- use the real thing
        return sys.modules["worlds.eldenring"].region_spine.REGION_PARENT
    if "eldenring" not in sys.modules:
        pkg = types.ModuleType("eldenring")
        pkg.__path__ = [GF_PKG]
        sys.modules["eldenring"] = pkg
    import importlib
    return importlib.import_module("eldenring.region_spine").REGION_PARENT


@unittest.skipIf(GROUND is None, "grace_ground.tsv not present (regen: tools/datamine_grace_ground.py --emit)")
class TestGraceGround(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ground = {}
        with open(GROUND, encoding="utf-8") as fh:
            for ln in fh:
                if ln.startswith("#") or ln.startswith("grace_flag"):
                    continue
                c = ln.rstrip("\n").split("\t")
                if len(c) >= 2 and c[1] != "-":
                    cls.ground[int(c[0])] = tuple(int(b) for b in c[1].split(";"))
        cls.play_ids = _load(os.path.join(GF_PKG, "region_play_ids.py"), "_gg_play_ids").REGION_PLAY_IDS
        cls.graces = _load(os.path.join(GF_PKG, "region_graces.py"), "_gg_graces").REGION_GRACE_POINTS
        cls.open_flags = _load(os.path.join(GF_PKG, "region_open_flags.py"), "_gg_open").REGION_OPEN_FLAGS
        cls.owner = {pid: reg for reg, pids in cls.play_ids.items() for pid in pids}
        cls.parent = _region_parent()

    def _allowed(self, region):
        out = {region}
        r = region
        while r in self.parent:
            r = self.parent[r]
            out.add(r)
        return out

    def test_ground_table_not_hollow(self):
        """A shrunken tsv (regenerated without the MSBs) silently blinds the whole invariant."""
        self.assertGreaterEqual(len(self.ground), 200, "grace_ground.tsv lost its derived rows")

    def test_bundle_graces_stand_on_own_ground(self):
        """No force-lit grace stands on ground provably owned by a foreign region."""
        bad = []
        for region, flags in self.graces.items():
            allowed = self._allowed(region)
            for fl in flags:
                bks = self.ground.get(fl)
                if not bks:
                    continue
                owners = {self.owner.get(b) for b in bks}
                if None in owners:          # unassigned bucket -> kick-permissive, unjudgeable
                    continue
                if not (owners & allowed):
                    bad.append((region, fl, sorted(owners)))
        self.assertFalse(bad,
            "force-lit grace(s) standing on a FOREIGN region's ground (warp-into-a-kick, the "
            "Charo's 68400 class) -- regenerate (gen_data's grace-ground gate excludes these), "
            "or fix region_groups.PLAY_REGION_GROUPS if the bucket owner is wrong: %r" % bad)

    def test_front_doors_stand_on_own_ground(self):
        """The region-open flag IS a grace the lock lights; its ground must be the region's own."""
        bad = []
        for region, fd in self.open_flags.items():
            bks = self.ground.get(fd)
            if not bks:
                continue
            owners = {self.owner.get(b) for b in bks}
            if None in owners:
                continue
            if not (owners & self._allowed(region)):
                bad.append((region, fd, sorted(owners)))
        self.assertFalse(bad, "front-door grace(s) on foreign ground: %r" % bad)

    def test_scaduview_fold_regression(self):
        """Scaduview (the Hinterland) was FOLDED into Shadow Keep 2026-07-19 (Alaric). It never held
        self-contained content -- Gaius + his fragment reward, the Scadutree Avatar, one Finger Ruins,
        all entered THROUGH the Keep -- and its own door ground was already the Keep's (76935 measured
        bucket 21000). This pins the fold so a regen can't silently regress it:
          * Scaduview is no longer a region (gone from open flags, play_ids, REGION_PARENT).
          * grace 76935 ("Hinterland") still stands on bucket 21000 -- now Shadow Keep's OWN ground.
          * Shadow Keep's front door stays its m21_00 entrance 72102, NOT the overworld Hinterland
            grace 76935 that _front_door's overworld-beats-interior heuristic would otherwise pick --
            the whole reason gen_data._FRONT_DOOR_PIN exists (a naive fold = Keep-unlock warps you to
            the back plateau instead of the gate).
          * 76935 still rides the Keep's bundle (lit + warpable on Keep unlock, its own ground)."""
        self.assertNotIn("Scaduview", self.open_flags,
                         "Scaduview folded into Shadow Keep -- must not survive as a region open flag")
        self.assertNotIn("Scaduview", self.play_ids,
                         "Scaduview folded into Shadow Keep -- must own no buckets of its own")
        self.assertNotIn("Scaduview", self.parent,
                         "Scaduview folded in -- no containment parent to keep")
        self.assertEqual(self.ground.get(76935), (21000,),
                         "grace_ground.tsv lost the MEASURED 76935 -> 21000 row (client kick line "
                         "2026-07-15); re-run tools/datamine_grace_ground.py --emit")
        self.assertIn(21000, self.play_ids.get("Shadow Keep", ()),
                      "21000 is the Keep's own bucket, so 76935's ground is the Keep's own ground")
        self.assertEqual(self.open_flags.get("Shadow Keep"), 72102,
                         "Shadow Keep's front door must stay its m21_00 entrance 72102 (the "
                         "_FRONT_DOOR_PIN), NOT the folded-in overworld Hinterland grace 76935")
        self.assertIn(76935, self.graces.get("Shadow Keep", ()),
                      "the folded-in Hinterland grace 76935 must ride the Keep's own bundle")

    def test_charos_regression(self):
        """The literal 2026-07-15 in-game failure, pinned: Charo's front door 76841 stands on
        bucket 68400 (measured play_region 6840000), so 68400 must be owned by Charo's -- the
        kick range for that ground clears on the Charo's Lock, not Cerulean's."""
        self.assertIn(68400, self.play_ids.get("Charo's", ()),
                      "bucket 68400 (Charo's Hidden Grave ground, in-game measured) must belong "
                      "to Charo's or its lock warps the player into a kick")
        self.assertEqual(self.ground.get(76841), (68400,))
