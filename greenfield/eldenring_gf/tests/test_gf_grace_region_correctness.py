"""Grace region-assignment CORRECTNESS gate (tier A: semantic-value, independent oracle).

`test_gf_data.py` proves the grace tables are well-FORMED (unique flags, every region non-empty). It
never proves a grace was bundled into the RIGHT region. That blind spot is where two green-while-broken
grace bugs lived (TRIAGE-test-upgrades-20260706.md):
  - gf-dungeon-grace-misbundle: cave/tower graces defaulting into Limgrave (the coarse cave/catacomb
    fallback) instead of the overworld region the dungeon physically sits under.
  - er-boss-border-grace-skip-list: boss-arena / fog-gated graces emitted as grantable front doors
    that should be SKIPPED (force-lighting one warps the player into a sealed arena -> soft-lock).

This gate closes the misbundle case with an INDEPENDENT oracle and DOCUMENTS the skip-list case
(no clean independent artifact exists yet -- see below), per Fable's rule: "a checker that shares
derivation code with the thing it checks is not an oracle."

INDEPENDENT SOURCE
------------------
`elden_ring_artifacts/grace_region_map_<ts>.tsv` -- grace_flag -> play_region_id, lifted from
`BonfireWarpParam.bonfireSubCategoryId` (the warp-menu bucket; see REGION_ID_MAP.md), plus
`grace_flags.tsv` (warpUnlockFlag -> mapTile) to tell a dungeon grace from an overworld one.

Why this is INDEPENDENT of the derivation under test: gen_data assigns a DUNGEON grace's region via
the map-id keyed `DUNGEON_REGION_OVERRIDE` / `_pref2maj(region_of())` path -- the exact path the
misbundle bug lived in -- and NEVER via the raw play_region_id. So cross-checking a dungeon grace's
emitted region against its play_region_id (this oracle) never re-runs that buggy transform.

OVERWORLD graces: gen ORIGINALLY bucketed these by `PLAY2AP[tile_pr(grace_tile)]` -- the per-tile
anchor VOTE, which this file once believed equalled the grace's own pid (hence "near-circular, skip
them"). That assumption was FALSE for boundary tiles: 76301 "Altus Plateau" (tile 38,50) and 76502
"Grand Lift of Rold" (tile 49,53) sit on tiles whose vote is Liurnia/Mountaintops but whose pid is
Altus (63xxx), so they leaked into the wrong bundle (in-game report 2026-07-08). gen now buckets
overworld graces by the authoritative pid too, so the overworld-boundary pin below guards that path
(a regression to tile_pr re-breaks it -- pid and tile-vote genuinely differ on boundary tiles).

Overworld play_region_ids partition the Lands Between by the thousands prefix (REGION_ID_MAP.md):
61xxx = Limgrave/Weeping landmass, 62xxx = Liurnia, 63xxx = Altus/Gelmir, 64xxx = Caelid/Dragonbarrow,
65xxx = Mountaintops/Snowfield. A dungeon whose independent pid is a Caelid pid (64xxx) can never
legitimately sit in a Limgrave-cluster (61xxx) region -- that cross-CLUSTER assignment is the
unambiguous misbundle signature. (Within a cluster the hand-curation legitimately floats a dungeon to
an adjacent region -- e.g. Wyndham Catacombs pid 63001/Gelmir is correctly curated to Altus -- so this
oracle deliberately checks the CLUSTER, not the fine pid, to avoid flagging legitimate curation.)

Run:  python -m pytest greenfield/eldenring_gf/tests/test_gf_grace_region_correctness.py
  or: python greenfield/eldenring_gf/tests/test_gf_grace_region_correctness.py   (unittest fallback)
"""
import csv
import glob
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)                     # .../greenfield/eldenring_gf
GREENFIELD = os.path.dirname(GF_PKG)               # .../greenfield
REPO = os.path.dirname(GREENFIELD)                 # .../er-archipelago
ARTIFACTS = os.path.join(REPO, "elden_ring_artifacts")
REGION_GRACES_PY = os.path.join(GF_PKG, "region_graces.py")
GRACE_FLAGS_TSV = os.path.join(ARTIFACTS, "grace_flags.tsv")

# Emitted OVERWORLD region -> its overworld cluster (thousands prefix of the play_region_id space).
# Transcribed from REGION_ID_MAP.md; the prefix is a real structural bucket in BonfireWarpParam, not
# an invented grouping. Legacy/DLC/underground regions (Stormveil, Leyndell, Land of Shadow, Eternal
# Cities, ...) are intentionally ABSENT -- their graces carry legacy/DLC pids this oracle does not
# adjudicate (a Divine Tower legitimately reached through the DLC is out of scope here).
REGION_CLUSTER = {
    "Limgrave": 61,
    "Weeping Peninsula": 61,
    "Liurnia of the Lakes": 62,
    "Altus Plateau": 63,
    "Mt. Gelmir": 63,
    "Caelid": 64,
    "Mountaintops of the Giants": 65,
    "Consecrated Snowfield": 65,
}

# Documented boundary/connector graces: a warp/lift/hidden-path grace that physically BRIDGES two
# clusters and is curated to the cluster it LEADS INTO. Each entry is a named connector, verifiable
# from the independent grace_name column -- NOT a blanket suppression. A NEW entry here must cite the
# connector it represents, or it is masking a real misbundle.
BOUNDARY_GRACE_ALLOW = {
    73020: "Hidden Path to the Haligtree -- connector dungeon (pid 63003/Altus) that EXITS into "
           "Consecrated Snowfield (cluster 65); curated to the region it leads into.",
}

# UNDERGROUND / LEGACY play_region_ids with an UNAMBIGUOUS greenfield region (REGION_ID_MAP.md).
# The cross-cluster oracle above only adjudicates OVERWORLD pids (61000-65999); a dungeon grace whose
# independent pid is a non-overworld bucket falls straight through its net. That blind spot is exactly
# where the Subterranean Shunning-Grounds misbundle lived: pid 35000 graces (Underground Roadside
# 73501, Forsaken Depths 73502, Leyndell Catacombs 73503, Frenzied Flame Proscription 73504) inherited
# Liurnia because region_map.csv mislabels every m35 row "Divine Tower" (-> Liurnia via REGION_MAP),
# and the grace region is derived from the majority region of its map-prefix checks (in-game report
# 2026-07-07). Each pid maps to a single greenfield region per REGION_ID_MAP.md; an emitted DUNGEON
# grace carrying such a pid must land in that region (boss-gated graces like 73500 Cathedral of the
# Forsaken are not emitted at all, so are simply absent -- not adjudicated here).
LEGACY_PID_REGION = {
    35000: "Leyndell",  # Subterranean Shunning-Grounds (a sub-level UNDER Leyndell; REGION_ID_MAP.md)
}

# play_region_ids that are OVERWORLD (the only ones the cluster arithmetic applies to).
OW_PID_LO, OW_PID_HI = 61000, 65999


def _load_region_graces():
    spec = importlib.util.spec_from_file_location("gf_region_graces_check", REGION_GRACES_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_grace_pids():
    """grace_flag(int) -> play_region_id(int) from the independent BonfireWarp-derived TSV."""
    path = glob.glob(os.path.join(ARTIFACTS, "grace_region_map_*.tsv"))
    if not path:
        return None
    out = {}
    with open(sorted(path)[-1], encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            try:
                out[int(row["grace_flag"])] = int(row["play_region_id"])
            except (KeyError, ValueError):
                continue
    return out


def _load_grace_tiles():
    """warpUnlockFlag(int) -> mapTile(str) from grace_flags.tsv (dungeon vs overworld)."""
    out = {}
    with open(GRACE_FLAGS_TSV, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            try:
                out[int(row["warpUnlockFlag"])] = row["mapTile"]
            except (KeyError, ValueError):
                continue
    return out


def _is_dungeon(tile):
    # Overworld tiles are m60_* (Lands Between) / m61_* (DLC Gravesite). Everything else -- caves
    # (m31), catacombs (m30), tunnels (m32), divine towers (m34), legacy dungeons (m10-m2x) -- is a
    # dungeon interior whose region gen derives via the map-id override path, not the raw pid.
    return not (tile.startswith("m60") or tile.startswith("m61"))


class GraceRegionCorrectness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(REGION_GRACES_PY):
            raise unittest.SkipTest("region_graces.py not generated yet (run gen_data.py)")
        cls.pids = _load_grace_pids()
        if cls.pids is None or not os.path.isfile(GRACE_FLAGS_TSV):
            raise unittest.SkipTest(
                "grace_region_map_*.tsv / grace_flags.tsv absent (installed-world copy / fresh "
                "clone) -- this independent oracle needs elden_ring_artifacts/; gated like "
                "ci-linux.sh's DRIFT step."
            )
        cls.tiles = _load_grace_tiles()
        rg = _load_region_graces()
        cls.emitted = {}          # grace_flag -> emitted region
        for region, flags in rg.REGION_GRACE_POINTS.items():
            for fl in flags:
                cls.emitted[int(fl)] = region

    def test_sources_nonempty(self):
        self.assertTrue(self.pids, "grace_region_map parsed to zero rows")
        self.assertTrue(self.tiles, "grace_flags.tsv parsed to zero rows")
        self.assertTrue(self.emitted, "region_graces.py emitted zero graces")

    def test_dungeon_graces_not_cross_cluster_misbundled(self):
        """gf-dungeon-grace-misbundle guard. A DUNGEON grace whose INDEPENDENT play_region_id belongs
        to overworld cluster X must not be bundled into an overworld region of a DIFFERENT cluster
        (e.g. a Caelid-pid cave dumped into a Limgrave-cluster region). Independent of gen: gen derives
        the dungeon region from DUNGEON_REGION_OVERRIDE / region_of (map-id keyed), never from this
        pid. Scoped to dungeon graces sitting in an overworld-cluster region -- the exact bug surface;
        legacy/DLC-region assignments (Divine Towers -> Land of Shadow, etc.) are out of scope and
        tracked separately below."""
        bad = []
        checked = 0
        for fl, region in sorted(self.emitted.items()):
            cluster = REGION_CLUSTER.get(region)
            if cluster is None:
                continue                                   # legacy/DLC region: not adjudicated here
            tile = self.tiles.get(fl)
            if not tile or not _is_dungeon(tile):
                continue                                   # overworld grace: gen used pid -> circular
            pid = self.pids.get(fl)
            if pid is None or not (OW_PID_LO <= pid <= OW_PID_HI):
                continue                                   # legacy/underground pid: no cluster
            checked += 1
            if pid // 1000 != cluster:
                if fl in BOUNDARY_GRACE_ALLOW:
                    continue                               # documented connector
                bad.append((fl, pid, pid // 1000, region, cluster, tile))
        self.assertGreater(checked, 0, "no dungeon graces cross-checked -- source join broke")
        self.assertEqual(
            bad, [],
            str(len(bad)) + " dungeon grace(s) misbundled across overworld clusters "
            "(gf-dungeon-grace-misbundle): a dungeon whose independent pid-cluster != its emitted "
            "region's cluster and is not a documented connector. "
            "(flag, pid, pid_cluster, region, region_cluster, tile): " + repr(bad[:8]),
        )

    # Overworld boundary graces whose per-tile anchor VOTE disagrees with their authoritative pid
    # (in-game report 2026-07-08). Pinned: gen must bundle these by pid, not tile_pr.
    OVERWORLD_BOUNDARY_GRACE_PINS = {
        76301: ("Altus Plateau", 63000),  # "Altus Plateau" grace, tile 38,50 votes Liurnia -> pid 63000
        76502: ("Altus Plateau", 63003),  # "Grand Lift of Rold", tile 49,53 votes Mountaintops -> pid 63003
    }

    def test_overworld_boundary_graces_follow_authoritative_pid(self):
        """Pinned regression (in-game 2026-07-08): an OVERWORLD grace on a contested boundary tile must
        be bundled by its own play_region_id, not the per-tile anchor vote. 76301 'Altus Plateau' leaked
        into Liurnia (its lock lit the Altus grace) and 76502 'Grand Lift of Rold' into Mountaintops;
        both carry Altus (63xxx) pids. Also asserts the GENERAL invariant for every overworld grace with
        an overworld pid: emitted-region cluster == pid cluster (a revert to tile_pr re-breaks it, since
        pid and tile-vote genuinely differ on boundary tiles)."""
        for fl, (region, pid) in self.OVERWORLD_BOUNDARY_GRACE_PINS.items():
            self.assertEqual(self.pids.get(fl), pid, f"independent source pid for grace {fl} changed")
            self.assertEqual(
                self.emitted.get(fl), region,
                f"overworld grace {fl} must be bundled under {region!r} (its play_region {pid}); got "
                f"{self.emitted.get(fl)!r} -- regressed to the per-tile anchor vote?")
        bad = []
        for fl, region in self.emitted.items():
            tile = self.tiles.get(fl)
            if not tile or _is_dungeon(tile):
                continue
            pid = self.pids.get(fl)
            cluster = REGION_CLUSTER.get(region)
            if pid is None or not (OW_PID_LO <= pid <= OW_PID_HI) or cluster is None:
                continue
            if pid // 1000 != cluster:
                bad.append((fl, pid, region, cluster, tile))
        self.assertEqual(
            bad, [],
            f"{len(bad)} overworld grace(s) bundled into a region whose cluster != their play_region "
            f"cluster (per-tile-vote regression, 2026-07-08): {bad[:8]}")

    def test_boundary_allow_entries_are_actually_cross_cluster(self):
        """Keep the connector allow-list honest: every entry must genuinely be a dungeon grace whose
        pid-cluster differs from its emitted region (a stale allow entry that no longer fires is dead
        masking and should be removed)."""
        stale = []
        for fl in BOUNDARY_GRACE_ALLOW:
            region = self.emitted.get(fl)
            pid = self.pids.get(fl)
            cluster = REGION_CLUSTER.get(region) if region else None
            if cluster is None or pid is None or not (OW_PID_LO <= pid <= OW_PID_HI):
                stale.append(fl); continue
            if pid // 1000 == cluster:
                stale.append(fl)
        self.assertEqual(stale, [], f"stale BOUNDARY_GRACE_ALLOW entries (no longer misbundled): {stale}")

    def test_underground_pid_graces_in_correct_region(self):
        """gf-liurnia-shunning-grounds-misbundle guard (in-game report 2026-07-07). The cross-cluster
        oracle skips non-overworld pids, so pid-35000 (Subterranean Shunning-Grounds) graces slipped
        into Liurnia undetected. Independent of gen: the expected region comes from REGION_ID_MAP.md
        keyed on the BonfireWarp-derived play_region_id, NOT from gen's map-id override path. Every
        EMITTED grace whose independent pid has an unambiguous region must be bundled there."""
        bad = []
        checked = 0
        for fl, region in sorted(self.emitted.items()):
            expect = LEGACY_PID_REGION.get(self.pids.get(fl))
            if expect is None:
                continue
            checked += 1
            if region != expect:
                bad.append((fl, self.pids.get(fl), region, expect, self.tiles.get(fl)))
        self.assertGreater(checked, 0, "no underground-pid graces cross-checked -- source join broke")
        self.assertEqual(
            bad, [],
            str(len(bad)) + " underground/legacy-pid grace(s) misbundled: an emitted grace whose "
            "independent play_region_id maps unambiguously to region X (REGION_ID_MAP.md) is bundled "
            "elsewhere. (flag, pid, emitted_region, expected_region, tile): " + repr(bad),
        )

    def test_shunning_grounds_four_graces_under_leyndell(self):
        """Pinned regression for the four reported graces. Subterranean Shunning-Grounds (m35, pid
        35000) sits UNDER Leyndell; these must be bundled under Leyndell, never Liurnia. Guards against
        the fix silently dropping them (a boss-gated skip would remove them from Leyndell too)."""
        want = {
            73501: "Underground Roadside",
            73502: "Forsaken Depths",
            73503: "Leyndell Catacombs",
            73504: "Frenzied Flame Proscription",
        }
        for fl, nm in want.items():
            self.assertEqual(
                self.emitted.get(fl), "Leyndell",
                f"grace {fl} ({nm}, Subterranean Shunning-Grounds pid 35000) must be under Leyndell, "
                f"got {self.emitted.get(fl)!r} (in-game misbundle into Liurnia, 2026-07-07)",
            )


class BossArenaGraceSkipList(unittest.TestCase):
    """er-boss-border-grace-skip-list (Invariant 2) -- DOCUMENTED SKIP, no independent oracle yet.

    The bug: boss-arena / fog-gated graces force-lit on region unlock warp the player into a sealed
    arena -> soft-lock. gen_data filters them with `_SKIP_GRACE_FLAGS` (EMEVD common-event 9005810
    sweep + a hand ARENA set). But that frozenset IS the derivation under test -- asserting the emitted
    graces exclude gen's own skip set is a tautology, not an oracle (Fable's rule).

    No clean INDEPENDENT artifact exists: FOGWALL-CATALOG.md catalogues overworld region-seam fog
    (explicitly finds NONE) and boss/dungeon-entrance fog collision -- it does not enumerate which
    grace flags sit behind a fog/arena gate. The only truly independent source would be re-parsing the
    decompiled `elden_ring_artifacts/event/*.emevd.dcx.js` common-event 9005810 grace-hide calls
    ourselves (an EMEVD-derived oracle, independent of gen's frozenset) -- deferred as a follow-up
    (mirrors this file's "deeper layer" note in test_gf_region_correctness.py). Rather than assert
    against gen's own list (fake independence) or invent a set (flaky), this is left as an explicit
    skip so the gap is TRACKED, per the task's "documented xfail/skip, do NOT invent a list."
    """

    def test_boss_arena_skip_list_needs_independent_emevd_oracle(self):
        raise unittest.SkipTest(
            "no independent boss-arena/fog grace source; gen's _SKIP_GRACE_FLAGS is the derivation "
            "under test. Follow-up: derive the skip set from event/*.emevd.dcx.js common-event "
            "9005810 grace-hide calls and assert none is emitted as a grantable region grace."
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
