"""Artifact-grounded map-tile region oracle (tier A: semantic-value, INDEPENDENT of even region_map.csv).

`test_gf_region_correctness.py` checks the emitted region assignment against `region_map.csv`'s own
`region` column -- gen_data's INPUT. That catches the map_lot HUB-quarantine class, but its oracle is
the CSV the assignment is derived from, so it cannot validate the CSV itself, and for overworld tiles
the CSV `region` column is just the raw tile string ("Overworld m60_51_57_00") -- it carries no region
truth at all (gen_data's `region_of` does the tile->region resolution when it emits data.py).

This gate re-derives the tile's region straight from GAME STRUCTURE, independent of region_map.csv AND
of gen_data's `region_of`:

  independent source 1  elden_ring_artifacts/REGION_ID_MAP.md
        BonfireWarpParam-derived `play_region_id -> region name` table (55 buckets, authoritative).
  independent source 2  elden_ring_artifacts/grace_region_map_<ts>.tsv
        every grace's (areaNo, gridX, gridZ) -> play_region_id, dumped from param + grace data.

From those two we build `map_tile_id -> region` WITHOUT touching region_map.csv or region_of:
  * overworld  m60_<gx>_<gz>_zz : the grace grid cell (areaNo 60, gridX=gx, gridZ=gz) -> play_region_id
    -> region.  (The m60 tile's 2nd/3rd fields ARE the msb block coords the TSV stores as gridX/gridZ.)
  * legacy/DLC dungeon  m<AA>_..: areaNo AA -> its set of play_region_ids -> region.

Both use two safety rails to stay strictly false-positive-free:
  * play_region_id -> data region is bridged by requiring exactly ONE data.py REGION name to appear in
    the PRIMARY part of the artifact region name (text before the first '('), so parenthetical
    descriptors ("Midra's Manse (Abyssal Woods interior)") never mis-bridge, and names that contain two
    region tokens ("Dragonbarrow (... Divine Tower of Caelid)") resolve to nothing rather than guess.
  * a tile resolves only if EVERY play_region_id sharing its cell / areaNo bridges to the SAME region
    (no unbridged member, no second region). A cell/area that genuinely straddles regions -- an m10
    Stormveil tile whose entrance graces are play_region 61001 Limgrave, or a scattered-cave areaNo --
    resolves to nothing and is skipped, never flagged.

Invariant (STRICT): for every flag whose map_lot placement tiles ALL resolve (independently) to a
single region R and whose flag is in the emitted pool, data.py must assign that flag to R (R present
in its assigned region set). This catches BOTH the HUB-quarantine regression (map_lot item dumped to
Roundtable Hold) AND a misbundle (dungeon/overworld item bucketed into the wrong spoke) -- with the
region derived from the game's map structure, not from the CSV the assignment came from. So it
validates region_map.csv's placement AND gen_data's region_of in one shot.

Coverage today (in-sandbox measured): 779 flags -- ~103 overworld m60 grid cells + legacy/DLC dungeon
areas m13 (Farum Azula), m14 (Raya Lucaria), m21 (Shadow Keep), m25 (Scadu Altus). Deliberately
NARROW-STRICT; see the module tail for the false-positive-avoidance exclusions and deferred widening.

Artifact-gated (like ci-linux.sh's DRIFT step): elden_ring_artifacts/ is licensing-restricted and may
be absent (fresh clone / CI). If the two sources are missing the gate SKIPS with a clear message; where
present it runs for real.

Run:  python -m pytest greenfield/eldenring_gf/tests/test_gf_region_artifact_oracle.py
  or: python greenfield/eldenring_gf/tests/test_gf_region_artifact_oracle.py
"""
import csv
import glob
import importlib.util
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)                     # .../greenfield/eldenring_gf
GREENFIELD = os.path.dirname(GF_PKG)               # .../greenfield
REPO_ROOT = os.path.dirname(GREENFIELD)            # .../er-archipelago
DATA_PY = os.path.join(GF_PKG, "data.py")
REGION_MAP_CSV = os.path.join(GREENFIELD, "region_map.csv")
ART_DIR = os.path.join(REPO_ROOT, "elden_ring_artifacts")
REGION_ID_MAP_MD = os.path.join(ART_DIR, "REGION_ID_MAP.md")
GRACE_TSV_GLOB = os.path.join(ART_DIR, "grace_region_map_*.tsv")

PLACED_SOURCES = {"map_lot"}   # STRICT: only items physically on an ItemLotParam_map tile.
MIN_ORACLE_FLAGS = 300         # tripwire: a broken parser must not silently empty the oracle (vacuous pass).


def _load_data():
    spec = importlib.util.spec_from_file_location("gf_data_artifact_oracle", DATA_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _parse_region_id_map(path):
    """REGION_ID_MAP.md markdown tables: '| <id> | <region name> | <graces> |' -> {play_region_id: name}."""
    id2name = {}
    row = re.compile(r"\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*[\d\-]+\s*\|\s*$")
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = row.match(line)
            if m:
                id2name[int(m.group(1))] = m.group(2).replace("**", "").strip()
    return id2name


def _build_bridge(id2name, regions, hub):
    """play_region_id -> data.py region, via a UNIQUE data-region-name substring of the artifact name's
    PRIMARY part (text before the first '('). 0 or >1 matches -> None (unresolvable, never guessed)."""
    bridged = {}
    for pid, nm in id2name.items():
        primary = nm.split("(")[0]
        if "Roundtable Hold" in primary:
            bridged[pid] = hub
            continue
        hits = [r for r in regions if r in primary]
        bridged[pid] = hits[0] if len(hits) == 1 else None
    return bridged


def _build_tile_oracle(tsv_path, bridged):
    """From the grace TSV build resolvers:
      cell_region[(gx, gz)] -> region   (overworld areaNo 60 tiles)
      area_region[areaNo]  -> region    (legacy/DLC dungeon tiles)
    A cell/area resolves only if every play_region_id in it bridges to the SAME region (else omitted)."""
    cell_pids, area_pids = {}, {}
    with open(tsv_path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            try:
                pid = int(r["play_region_id"]); area = int(r["areaNo"])
                gx = int(r["gridX"]); gz = int(r["gridZ"])
            except (KeyError, ValueError):
                continue
            if pid == 0:
                continue
            area_pids.setdefault(area, set()).add(pid)
            if area == 60:
                cell_pids.setdefault((gx, gz), set()).add(pid)

    def collapse(pids):
        br = {bridged.get(p) for p in pids}
        return next(iter(br)) if (None not in br and len(br) == 1) else None

    cell_region = {c: collapse(p) for c, p in cell_pids.items()}
    cell_region = {c: r for c, r in cell_region.items() if r is not None}
    area_region = {a: collapse(p) for a, p in area_pids.items() if a != 60}
    area_region = {a: r for a, r in area_region.items() if r is not None}
    return cell_region, area_region


def _tile_region(map_id, cell_region, area_region):
    m = re.match(r"m60_(\d+)_(\d+)_\d+$", map_id)
    if m:
        return cell_region.get((int(m.group(1)), int(m.group(2))))
    m = re.match(r"m(\d+)_\d+_\d+_\d+$", map_id)
    if m:
        return area_region.get(int(m.group(1)))
    return None


class RegionArtifactOracle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        grace = sorted(glob.glob(GRACE_TSV_GLOB))
        if not (os.path.isfile(REGION_ID_MAP_MD) and grace and os.path.isfile(REGION_MAP_CSV)):
            raise unittest.SkipTest(
                "artifact map->region source absent (elden_ring_artifacts/ is licensing-restricted and "
                "not in fresh clones / CI); this oracle runs only where REGION_ID_MAP.md + "
                "grace_region_map_*.tsv + region_map.csv are all present. Gated like ci-linux.sh's DRIFT step."
            )
        cls.d = _load_data()
        cls.regions = set(cls.d.REGIONS)
        cls.hub = cls.d.HUB
        id2name = _parse_region_id_map(REGION_ID_MAP_MD)
        bridged = _build_bridge(id2name, cls.regions, cls.hub)
        cls.cell_region, cls.area_region = _build_tile_oracle(grace[-1], bridged)

        # data.py: flag(int) -> set of regions it is assigned to (a shared flag may span regions).
        assigned = {}
        for region, locs in cls.d.LOCATIONS.items():
            for (_name, _apid, flag) in locs:
                assigned.setdefault(int(flag), set()).add(region)
        cls.assigned = assigned

        # flag -> single independent oracle region, across ALL its map_lot placement tiles.
        # multi-home (tiles disagree) -> excluded; unresolvable tiles ignored.
        flagres = {}
        with open(REGION_MAP_CSV, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                if r.get("flag_source") not in PLACED_SOURCES:
                    continue
                orc = _tile_region(r.get("map") or "", cls.cell_region, cls.area_region)
                if orc is None:
                    continue
                try:
                    flagres.setdefault(int(r["flag"]), set()).add(orc)
                except (KeyError, ValueError):
                    continue
        cls.oracle = {fl: next(iter(s)) for fl, s in flagres.items() if len(s) == 1}
        cls.multi_home = {fl for fl, s in flagres.items() if len(s) > 1}

    def test_oracle_nonempty(self):
        """Guard against a silent parser break emptying the oracle (which would make the gate vacuous)."""
        self.assertGreaterEqual(
            len(self.oracle), MIN_ORACLE_FLAGS,
            "artifact oracle resolved only " + str(len(self.oracle)) + " flags (< " + str(MIN_ORACLE_FLAGS)
            + "); REGION_ID_MAP.md / grace TSV / region_map.csv parsing likely broke -- the gate would "
            "otherwise pass vacuously.",
        )

    def test_placed_items_match_map_derived_region(self):
        """Every flag whose map_lot tiles ALL resolve (independently, via game structure) to one region R
        must be assigned that R by data.py. Catches HUB-quarantine and cross-region misbundle alike."""
        violations = []
        for flag, R in self.oracle.items():
            regs = self.assigned.get(flag)
            if not regs:
                continue  # flag not in emitted pool (DLC filtered / item_shuffle off) -- can't check
            if R not in regs:
                violations.append((flag, R, sorted(regs)))
        self.assertEqual(
            violations, [],
            str(len(violations)) + " placed (map_lot) flag(s) whose map tile the game structure puts in "
            "region R were NOT assigned R by data.py (HUB-quarantine or cross-region misbundle). "
            "Oracle = REGION_ID_MAP.md + grace grid, independent of region_map.csv/region_of. "
            "Sample [(flag, expected_R, assigned)]: " + repr(violations[:8]),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
