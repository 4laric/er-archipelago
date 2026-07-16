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

    def test_scaduview_regression(self):
        """The 2026-07-15 Scaduview kick, pinned: its front-door grace 76935 ("Hinterland") stands
        on m21_00's DEFAULT ground -- in-game measured play_region 2100010, bucket 21000 -- which
        is Shadow Keep's PRIMARY bucket (shared with the whole Keep interior), so it can never be
        rebucketed to Scaduview. The honest encoding is containment: REGION_PARENT must gate
        Scaduview behind Shadow Keep, keeping 76935 ancestor-owned rather than foreign."""
        self.assertEqual(self.ground.get(76935), (21000,),
                         "grace_ground.tsv lost the MEASURED 76935 -> 21000 row (client kick line "
                         "2026-07-15); re-run tools/datamine_grace_ground.py --emit")
        self.assertIn(21000, self.play_ids.get("Shadow Keep", ()),
                      "bucket 21000 is the Keep interior's own bucket; moving it strands the Keep")
        self.assertEqual(self.parent.get("Scaduview"), "Shadow Keep",
                         "Scaduview's front door stands on Shadow Keep ground: without the "
                         "containment parent its lock warps the player straight into a kick")
        self.assertEqual(self.open_flags.get("Scaduview"), 76935,
                         "Scaduview's front door must stay 76935 (ancestor-owned), not silently "
                         "demote to an underivable grace")

    def test_charos_regression(self):
        """The literal 2026-07-15 in-game failure, pinned: Charo's front door 76841 stands on
        bucket 68400 (measured play_region 6840000), so 68400 must be owned by Charo's -- the
        kick range for that ground clears on the Charo's Lock, not Cerulean's."""
        self.assertIn(68400, self.play_ids.get("Charo's", ()),
                      "bucket 68400 (Charo's Hidden Grave ground, in-game measured) must belong "
                      "to Charo's or its lock warps the player into a kick")
        self.assertEqual(self.ground.get(76841), (68400,))
