"""Region provenance ORACLE -- Predicate A: grace-arbitrated same-map consistency (tier A, independent).

SPEC-provenance-oracle-20260710.md. The dominant maintenance cost in this repo is manual "re-pin X to
region Y" (gen_data's FLAG_REGION_OVERRIDE is ~40 hand rows, nearly all found by playing the game) --
patching the OUTPUT of a wrong derivation. This gate makes a whole class of mis-pin illegal instead of
waiting for an in-game report.

INDEPENDENT GROUND TRUTH -- two joins, neither touching the derivation under test
---------------------------------------------------------------------------------
1. WHERE the game puts each check: `greenfield/msb_flag_region.tsv`
   (tools/datamine_msb_item_regions.py) proves, for a check's acquisition flag, WHICH PHYSICAL MAP the
   game places its item in. The tsv's `source` column names which chain proved it:
     treasure  MSB Event/Treasure -> ItemLotID -> ItemLotParam_map.getItemFlagId*     (map-placed loot)
     enemy     MSB Part/Enemy -> NPCParamID -> NpcParam.itemLotId_{enemy,map} -> flags (NPC/enemy drops)
     event     per-map EMEVD award site -> item lot -> flags                          (BOSS drops)
2. WHICH REGION each interior map is: the GRACE JOIN in tools/map_region_oracle.py --
   grace_flags.tsv (warpUnlockFlag -> mapTile) JOIN grace_region_map_*.tsv (grace_flag ->
   play_region_id, i.e. BonfireWarpParam.bonfireSubCategoryId) folded to greenfield regions via its
   documented PLAY_REGION_TO_GF table (sourced from elden_ring_artifacts/REGION_ID_MAP.md).
Neither join reads region_map.csv or re-runs gen_data's region derivation (Fable's rule: a checker
that shares derivation code with the thing it checks is not an oracle).

WHY NOT MAJORITY-VOTE (the v2 arbiter this replaces)
----------------------------------------------------
v2 took each map's majority data.py region as truth. Two proven defects killed it:
  * the majority can BE the bug: m11_10 IS Roundtable Hold, but the coarse 'Leyndell / Roundtable /
    Shunning-Grounds' -> 'Altus Plateau' bucket makes Altus the majority there, so the vote blamed the
    two CORRECT rows (Ensha's drops 400490 / 11107900, deliberate FLAG_REGION_OVERRIDE entries) and
    blessed four real Roundtable mis-pins as "truth";
  * overworld tiles straddle boundaries (72 false violations), see SCOPE below.

PREDICATE A -- grace-arbitrated same-map consistency
----------------------------------------------------
Every data.py check whose item the game places in INTERIOR map M must carry a region in M's
grace-derived region set (almost always a single region). Disagreement = violation naming the flag,
item, data.py region, grace-truth region and the source chain -- unless a reasoned override row in
`region_overrides.tsv` justifies it. A map whose own graces straddle a boundary (m10_00 holds both
Stormveil- and Stormhill-bucket graces) is adjudicated by MEMBERSHIP in the set: still sound (any
cross-boundary region is a violation), just less sharp on that one map; the sets are printed.

SCOPE -- what the arbiter deliberately does NOT adjudicate (counted and printed, never silent)
----------------------------------------------------------------------------------------------
  * OVERWORLD maps (m60_*/m61_*): these map ids are SPATIAL TILES and a single tile legitimately
    straddles region boundaries, so same-map consistency is INVALID there by construction. Overworld
    region provenance is already gated independently by test_gf_grace_region_correctness.py (per-grace
    play_region oracle) + the tile decode it verifies.
  * Interior maps with NO warp grace (e.g. m32_02): the grace join cannot arbitrate them. EXCLUDED and
    listed -- we do NOT fall back to majority-vote.
  * MIXED-placement flags (>=1 interior map AND >=1 overworld tile, e.g. 400220 Kenneth Haight,
    reachable in Limgrave tiles and on Godrick's throne): the overworld sites are out of scope, so the
    flag's full placement set cannot be proven single-region; judging only the interior site could
    raise a FALSE violation. Excluded, counted.
  * MULTI-MAP flags whose interior maps resolve to >1 region (drop lots are reusable; a questline NPC
    or invader placed in several maps shares one drop flag): any region data.py picks is defensible,
    so a violation here would be FALSE. Excluded, counted, printed.
This is the difference between "the oracle cannot adjudicate this" and "data.py is wrong". The gate
must never confuse the two.

SCOPE / KNOWN LIMITS (honest)
  * The mixed/multi-map exclusions are only COMPLETE on a FULL-map tsv: a partial (--maps) scan can
    make a multi-site flag look single-map and raise a FALSE mis-pin. The tsv records its own scope on
    a leading `# maps=...` line and this gate prints it; only `# maps=all` is gate-grade.
  * Coverage is whatever the extractor can PROVE. Flags with no treasure/enemy/event row (shop stock,
    quest hand-ins, grants keyed off nothing map-local) are simply not adjudicated here.
  * tsv or grace artifacts absent -> the gate SKIPS (like the grace oracle) rather than passing
    vacuously.

Run:  python -m pytest greenfield/eldenring/tests/test_gf_region_provenance_oracle.py
  or: python greenfield/eldenring/tests/test_gf_region_provenance_oracle.py
"""
import csv
import importlib.util
import os
import unittest
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)
GREENFIELD = os.path.dirname(GF_PKG)
REPO = os.path.dirname(GREENFIELD)
def _find_up(rel, start=GF_PKG):
    d = os.path.abspath(start)
    for _ in range(8):
        cand = os.path.join(d, rel)
        if os.path.exists(cand):
            return cand
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return None

MSB_TSV = _find_up("msb_flag_region.tsv") or _find_up(os.path.join("greenfield", "msb_flag_region.tsv")) or ""
OVERRIDES_TSV = _find_up("region_overrides.tsv") or _find_up(os.path.join("greenfield", "region_overrides.tsv")) or ""
DATA_PY = os.path.join(GF_PKG, "data.py")
ORACLE_PY = _find_up(os.path.join("tools", "map_region_oracle.py")) or ""


def _load_arbiter():
    """tools/map_region_oracle.py -- the grace-join arbiter (see its module docs for the fold table)."""
    if not ORACLE_PY or not os.path.isfile(ORACLE_PY):
        return None
    spec = importlib.util.spec_from_file_location("_map_region_oracle", ORACLE_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_data_flag_regions():
    spec = importlib.util.spec_from_file_location("_gfdata", DATA_PY)
    data = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(data)
    f2r = defaultdict(set)
    f2name = {}
    for reg, locs in data.LOCATIONS.items():
        for _nm, _aid, flag in locs:
            f2r[int(flag)].add(reg)
            f2name[int(flag)] = _nm
    return f2r, f2name


def _load_overrides():
    """flag -> region overrides (reason-carrying table). Absent/optional -> empty."""
    ov = {}
    if not OVERRIDES_TSV or not os.path.isfile(OVERRIDES_TSV):
        return ov
    with open(OVERRIDES_TSV, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            if row.get("key_kind") == "flag":
                try:
                    ov[int(row["key"])] = row["region"]
                except (KeyError, ValueError):
                    pass
    return ov


def _load_msb():
    """-> (map_flags {map_id: {flag}}, flag_src {(flag, map_id): {source}}, scope str). None if absent."""
    if not MSB_TSV or not os.path.isfile(MSB_TSV):
        return None, None, ""
    map_flags = defaultdict(set)
    flag_src = defaultdict(set)
    scope = "all"                                   # v1 tsv had no scope line -> assume full
    with open(MSB_TSV, encoding="utf-8", newline="") as fh:
        lines = []
        for line in fh:
            if line.startswith("#"):
                for tok in line[1:].split():
                    if tok.startswith("maps="):
                        scope = tok[len("maps="):]
                continue
            lines.append(line)
    for row in csv.DictReader(lines, delimiter="\t"):
        try:
            flag = int(row["flag"])
        except (KeyError, TypeError, ValueError):
            continue
        map_id = row.get("map_id")
        if not map_id:
            continue
        map_flags[map_id].add(flag)
        flag_src[(flag, map_id)].add(row.get("source") or "treasure")   # v1 tsv has no source column
    return map_flags, flag_src, scope


def _is_overworld(map_id):
    return map_id.startswith("m60_") or map_id.startswith("m61_")


def excluded_flags(map_flags, map_truth):
    """Flags the oracle CANNOT adjudicate (module docs, SCOPE): -> {flag: reason str}.

    Never silent: every exclusion carries its reason and is printed by the gate."""
    flag_interior = defaultdict(set)                # flag -> interior maps WITH grace truth
    flag_overworld = defaultdict(set)
    for map_id, flags in map_flags.items():
        for f in flags:
            if _is_overworld(map_id):
                flag_overworld[f].add(map_id)
            elif map_id in map_truth:
                flag_interior[f].add(map_id)
    out = {}
    for f, interior in flag_interior.items():
        if flag_overworld.get(f):
            out[f] = ("mixed interior/overworld placement %s -- overworld sites are out of scope, "
                      "single-region cannot be proven" % sorted(interior | flag_overworld[f]))
            continue
        if len(interior) > 1:
            union = set().union(*(map_truth[m] for m in interior))
            if len(union) > 1:
                out[f] = ("multi-map placement %s resolving to >1 region %s -- any of them is "
                          "defensible" % (sorted(interior), sorted(union)))
    return out


def find_violations(map_flags, f2r, map_truth, overrides=None, flag_src=None, f2name=None):
    """Predicate A, as a PURE function so the negative controls can inject their own tables.

    map_truth: {interior map_id: set(gf regions)} -- the independent grace-join arbiter.
    -> (violations[str], maps_checked, excluded {flag: reason}, no_grace_maps [map_id])"""
    overrides = overrides or {}
    flag_src = flag_src or {}
    f2name = f2name or {}
    excluded = excluded_flags(map_flags, map_truth)
    violations = []
    maps_checked = 0
    no_grace = []
    for map_id, flags in sorted(map_flags.items()):
        if _is_overworld(map_id):
            continue                    # out of scope by construction (module docs) -- counted by caller
        truth = map_truth.get(map_id)
        if not truth:
            no_grace.append(map_id)     # no warp grace -> cannot arbitrate; NO majority fallback
            continue
        if not any(f2r.get(f) for f in flags):
            continue                    # map holds no randomized check -- nothing to adjudicate
        maps_checked += 1
        for f in sorted(flags):
            regs = f2r.get(f)
            if not regs:                # not a randomized check -- nothing to adjudicate
                continue
            if f in excluded:           # cannot adjudicate (mixed / multi-map) -- see excluded_flags
                continue
            if regs & set(truth):       # membership: boundary maps carry >1 plausible region
                continue
            if overrides.get(f) in regs:    # a reasoned override row justifies this placement
                continue
            src = ",".join(sorted(flag_src.get((f, map_id), {"?"})))
            nm = f2name.get(f)
            violations.append(
                "  map %s: flag %s%s in data.py region %s but the game places it in %s "
                "(grace-truth region %s, proved via %s); re-pin it (gen_data FLAG_REGION_OVERRIDE"
                " / ROW_MAP_REGION_FIX) or add a reasoned row to region_overrides.tsv"
                % (map_id, f, " (%s)" % nm if nm else "", sorted(regs), map_id, sorted(truth), src))
    return violations, maps_checked, excluded, no_grace


class ProvenanceOracle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map_flags, cls.flag_src, cls.scope = _load_msb()
        cls.f2r, cls.f2name = _load_data_flag_regions()
        cls.ov = _load_overrides()
        arb = _load_arbiter()
        cls.map_truth, cls.truth_meta = (arb.load_map_truth() if arb else (None, "tools/map_region_oracle.py absent"))

    def _require_tables(self):
        if self.map_flags is None:
            self.skipTest(f"{os.path.basename(MSB_TSV) or 'msb_flag_region.tsv'} absent -- regenerate "
                          "on Windows (python tools/datamine_msb_item_regions.py)")
        if self.map_truth is None:
            self.skipTest("grace-join arbiter unavailable (%s) -- this independent oracle needs "
                          "elden_ring_artifacts/, gated like test_gf_grace_region_correctness"
                          % self.truth_meta)

    def test_A_same_map_single_region(self):
        """Every check the game places in interior map M must carry M's grace-truth region in data.py."""
        self._require_tables()
        violations, maps_checked, excluded, no_grace = find_violations(
            self.map_flags, self.f2r, self.map_truth, self.ov, self.flag_src, self.f2name)
        overworld = sorted(m for m in self.map_flags if _is_overworld(m))
        ow_flags = {f for m in overworld for f in self.map_flags[m]}
        gated = {f for m, fl in self.map_flags.items()
                 if not _is_overworld(m) and self.map_truth.get(m)
                 for f in fl if self.f2r.get(f) and f not in excluded}
        by_src = Counter(s for srcs in self.flag_src.values() for s in srcs)
        print(f"\n[provenance oracle] scope maps={self.scope}; arbiter={self.truth_meta['grace_region_map']} "
              f"({self.truth_meta['interior_maps']} interior maps arbitrated, boundary sets: "
              f"{self.truth_meta['boundary_maps']})")
        print(f"[provenance oracle] {maps_checked} interior map(s) adjudicated; {len(gated)} data.py "
              f"check(s) under the gate; placements by source: {dict(by_src)}")
        print(f"[provenance oracle] SKIPPED {len(overworld)} overworld tile map(s) ({len(ow_flags)} "
              "placement flags): m60_/m61_ ids are spatial tiles that straddle region boundaries -- "
              "same-map consistency is invalid there; overworld provenance is gated by "
              "test_gf_grace_region_correctness.py instead")
        print(f"[provenance oracle] SKIPPED {len(no_grace)} interior map(s) with no warp grace (cannot "
              f"arbitrate, NO majority fallback): {no_grace}")
        print(f"[provenance oracle] {len(excluded)} flag(s) excluded as unadjudicable:")
        for f in sorted(excluded):
            print(f"    flag {f}: {excluded[f]}")
        if self.scope != "all":
            print("[provenance oracle] WARNING: partial tsv -- the mixed/multi-map exclusion is "
                  "incomplete, a violation here may be an unscanned sibling placement. Regenerate "
                  "full on Windows.")
        self.assertFalse(
            violations,
            "game-placement disagrees with data.py region (%d map(s) checked):\n%s"
            % (maps_checked, "\n".join(violations)))

    def test_A_catches_a_synthetic_enemy_drop_mispin(self):
        """NEGATIVE CONTROL: an enemy/boss-drop flag pinned to the wrong region MUST be caught -- and an
        ambiguous (multi-region) flag MUST NOT be, since that would be a false positive."""
        map_flags = {
            "mAA_00": {1, 2, 3, 9},                 # region-A block
            "mBB_00": {4, 5, 6, 9},                 # region-B block
        }
        map_truth = {"mAA_00": {"A"}, "mBB_00": {"B"}}   # injected grace-join arbiter
        f2r = {1: {"A"}, 2: {"A"},
               3: {"B"},                            # <- mis-pinned boss drop, placed in the A block
               4: {"B"}, 5: {"B"}, 6: {"B"},
               9: {"A"}}                            # <- same drop reachable in BOTH blocks: ambiguous
        flag_src = {(3, "mAA_00"): {"enemy"}, (9, "mAA_00"): {"enemy"}, (9, "mBB_00"): {"enemy"}}
        violations, maps_checked, excluded, no_grace = find_violations(
            map_flags, f2r, map_truth, {}, flag_src)
        self.assertEqual(maps_checked, 2)
        self.assertEqual(no_grace, [])
        self.assertEqual(sorted(excluded), [9], "multi-region flag 9 must be excluded, not flagged")
        self.assertEqual(len(violations), 1, f"expected exactly the flag-3 mis-pin, got {violations}")
        self.assertIn("flag 3", violations[0])
        self.assertIn("enemy", violations[0])       # the failure names the chain that proved it
        fixed = dict(f2r)
        fixed[3] = {"A"}                            # ...and the same table, correctly pinned, is clean
        clean, _n, _e, _g = find_violations(map_flags, fixed, map_truth, {}, flag_src)
        self.assertFalse(clean, f"correctly-pinned table must be clean, got {clean}")
        # a graceless map must be reported, not majority-guessed:
        _v, checked, _e, ng = find_violations({"mCC_00": {1}}, f2r, map_truth, {}, {})
        self.assertEqual((checked, ng), (0, ["mCC_00"]))

    def test_A_would_have_caught_rennala_remembrance_mispin(self):
        """REGRESSION (in-game 2026-07-08): flag 197 (Remembrance of the Full Moon Queen) was pinned to
        Stormveil Castle although Rennala is in m14 Raya Lucaria -- a soft-lock. It is a boss drop, so
        only the `event` chain can see it. Re-injecting the historical value must produce a violation."""
        self._require_tables()
        maps_197 = sorted(m for m, fl in self.map_flags.items() if 197 in fl)
        if not maps_197:
            self.skipTest("flag 197 not in the tsv (regenerate including --sources event)")
        self.assertEqual(maps_197, ["m14_00"],
                         "the game awards Rennala's remembrance from m14_00 (Raya Lucaria) alone")
        self.assertIn("event", {s for m in maps_197 for s in self.flag_src[(197, m)]},
                      "197 is a boss drop -- it must come from the EMEVD `event` chain, not Treasure")
        # REGION-SPINE v2 (2026-07-13): m14_00 no longer FOLDS into Liurnia -- Raya Lucaria Academy
        # (play_region 14000) is its own region now, so the grace join arbitrates it to itself. That
        # is strictly better for this very bug: Rennala's remembrance sits in the region the game
        # actually puts her in, instead of a bucket she was welded into.
        m14_truth = self.map_truth.get("m14_00")
        self.assertEqual(m14_truth, frozenset({"Raya Lucaria Academy"}),
                         "grace join must arbitrate m14_00 to Raya Lucaria Academy (its own region "
                         "since region-spine v2; it used to fold into Liurnia)")
        self.assertTrue(self.f2r.get(197) & m14_truth,
                        "data.py must pin 197 to m14_00's grace-truth region (today's live value)")

        historical = dict(self.f2r)
        historical[197] = {"Stormveil"}                         # the 2026-07-08 mis-pin
        violations, _n, excluded, _g = find_violations(
            self.map_flags, historical, self.map_truth, self.ov, self.flag_src)
        self.assertNotIn(197, excluded, "197 is placed in exactly one map -- it must not be excluded")
        self.assertTrue([v for v in violations if " flag 197 " in v],
                        "the oracle FAILED to catch the very mis-pin it exists to catch: %s" % violations)

    def test_A_ensha_roundtable_rows_are_not_blamed(self):
        """REGRESSION (majority-vote defect #2): m11_10 IS Roundtable Hold; Ensha's drops 400490 /
        11107900 are correctly pinned there by deliberate FLAG_REGION_OVERRIDE rows. Majority-vote
        blamed them (Altus was the m11_10 majority). The grace arbiter must NOT."""
        self._require_tables()
        self.assertEqual(self.map_truth.get("m11_10"), frozenset({"Roundtable Hold"}),
                         "grace join must arbitrate m11_10 to Roundtable Hold (grace 71110, pid 11100)")
        violations, _n, _e, _g = find_violations(
            self.map_flags, self.f2r, self.map_truth, self.ov, self.flag_src, self.f2name)
        blamed = [v for v in violations if " flag 400490 " in v or " flag 11107900 " in v]
        self.assertFalse(blamed, "the arbiter blamed Ensha's CORRECT Roundtable rows:\n%s" % blamed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
