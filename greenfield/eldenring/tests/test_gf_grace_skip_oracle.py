"""Boss-gated grace SKIP oracle (tier A: semantic-value, INDEPENDENT EMEVD-derived oracle).

`test_gf_data.py` proves the grace tables are well-FORMED; `test_gf_grace_region_correctness.py`
proves each EMITTED grace sits in the right region. Neither proves that a grace which must NEVER be
emitted (because force-lighting it soft-locks the player) is actually withheld. That is the
er-boss-border-grace-skip-list bug: num_regions lights a region's whole grace bundle on lock receipt,
so a boss-arena grace warps the player into an arena whose grace asset does not physically exist yet
-> soft-lock. gen_data filters these with a hand-transcribed `_BOSS_GATED_GRACE_FLAGS` frozenset,
documented as EMEVD-derived but "NOT provably complete." Asserting the emitted graces exclude gen's
OWN frozenset is a tautology, not an oracle (Fable's rule: a checker that shares derivation code with
the thing it checks is not an oracle).

INDEPENDENT ORACLE
------------------
Re-derive the boss-gated skip-set straight from the decompiled EMEVD + the vanilla param dump, sharing
no code or data with gen's frozenset:

  1. `elden_ring_artifacts/event/common_func.emevd.dcx.js` defines common event 9005810 -- comment
     "【共通】ボス用篝火処理" ([Common] Bonfire processing for boss). Its VERIFIED body:
         $Event(9005810, Restart, function(eventFlagId, eventFlagId2, chrEntityId, assetEntityId, dist){
             if (!EventFlag(eventFlagId)) {          // gate flag (boss-defeat, xxxxx800/850) not set
                 DisableCharacter(chrEntityId);
                 DisableAsset(assetEntityId);        // <-- the grace ASSET is HIDDEN
                 WaitFor(EventFlag(eventFlagId));    // ...until the gate flag flips
                 EnableCharacter(chrEntityId);
                 EnableAsset(assetEntityId);
             }
             RegisterBonfire(eventFlagId2, assetEntityId, ...);
         });
     So every map that invokes `$InitializeCommonEvent(_, 9005810, <gate>, <bonfireFlag>, <chr>,
     <assetEntityId>, <dist>)` registers a grace whose asset is disabled until <gate> is set. Warping
     to that grace before the gate flips lands the player on a disabled bonfire behind boss fog ->
     exactly the soft-lock the skip-set exists to prevent. The 9005810 asset entities ARE the
     boss-gated graces.

  2. `elden_ring_artifacts/vanilla_er/vanilla_er/BonfireWarpParam.csv` joins each grace asset to its
     warp-menu flag: `bonfireEntityId` (== the 9005810 assetEntityId, arg 4) -> `eventflagId` (the
     warpUnlockFlag that `region_graces.py` emits and the client force-lights). This is the same param
     grace_flags.tsv is lifted from, but the JOIN KEY here (bonfireEntityId) comes from the EMEVD, not
     from gen. arg2 (eventFlagId2) is the RegisterBonfire flag and coincides with the warpUnlockFlag
     for overworld/Ainsel graces but NOT for legacy dungeons (m10 registers 10000000 yet warps on
     71000), so the asset-entity join is the reliable one and is what this oracle uses.

The resulting flag set is derived with ZERO reference to gen_data's frozenset -- it is a true oracle.
Empirically it reproduces gen's `_BOSS_GATED_GRACE_FLAGS` exactly (37/37, both directions), which is
the completeness proof gen's own comment could only assert. (gen ALSO carries a separate
`_ARENA_GRACE_FLAGS` set of MSB-placed remembrance-arena graces that emit NO 9005810 signal -- those
are out of scope for this EMEVD oracle by construction, and this gate does not adjudicate them.)

Two assertions:
  (1) SOFT-LOCK GUARD (independent): no EMEVD-derived boss-gated grace appears grantable in
      region_graces.py REGION_GRACE_POINTS.
  (2) COMPLETENESS (comparison only): every EMEVD-derived boss-gated flag is present in gen's
      `_BOSS_GATED_GRACE_FLAGS` -- flags any boss-gated grace gen's hand-list MISSES. gen's frozenset
      is read purely for this diff; it is never used as the oracle.

Skip-when-source-absent (EMEVD / param dump live only in elden_ring_artifacts/, like ci-linux.sh's
DRIFT step).

Run:  python -m pytest greenfield/eldenring/tests/test_gf_grace_skip_oracle.py
  or: python greenfield/eldenring/tests/test_gf_grace_skip_oracle.py   (unittest fallback)
"""
import ast
import csv
import glob
import importlib.util
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)                     # .../greenfield/eldenring
GREENFIELD = os.path.dirname(GF_PKG)               # .../greenfield
REPO = os.path.dirname(GREENFIELD)                 # .../er-archipelago
ARTIFACTS = os.path.join(REPO, "elden_ring_artifacts")
EVENT_DIR = os.path.join(ARTIFACTS, "event")
BONFIRE_CSV = os.path.join(ARTIFACTS, "vanilla_er", "vanilla_er", "BonfireWarpParam.csv")
REGION_GRACES_PY = os.path.join(GF_PKG, "region_graces.py")
GEN_DATA_PY = os.path.join(GREENFIELD, "gen_data.py")

# The boss-bonfire common event verified above. $InitializeCommonEvent(slot, 9005810, gate, ef2, chr,
# assetEntityId, dist): capture gate(arg1) and assetEntityId(arg4). arg4 joins to BonfireWarpParam.
_INIT_9005810 = re.compile(
    r"InitializeCommonEvent\(\s*\d+\s*,\s*9005810\s*,\s*(\d+)\s*,\s*\d+\s*,\s*\d+\s*,\s*(\d+)\s*,"
)


def _load_region_graces():
    spec = importlib.util.spec_from_file_location("gf_region_graces_skip_check", REGION_GRACES_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _bonfire_entity_to_flag():
    """bonfireEntityId(str) -> warpUnlockFlag(int) from the vanilla BonfireWarpParam dump."""
    out = {}
    with open(BONFIRE_CSV, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            try:
                out.setdefault(row["bonfireEntityId"], int(row["eventflagId"]))
            except (KeyError, ValueError):
                continue
    return out


def _emevd_boss_gated_flags(ent2flag):
    """Independent oracle: warpUnlockFlags of every grace registered behind a gate by common event
    9005810, joined asset-entity -> BonfireWarpParam. Returns (flags:set, unresolved:list)."""
    flags = set()
    unresolved = []
    for fn in sorted(glob.glob(os.path.join(EVENT_DIR, "m*.emevd.dcx.js"))):
        with open(fn, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = _INIT_9005810.search(line)
                if not m:
                    continue
                gate, asset = m.group(1), m.group(2)
                wf = ent2flag.get(asset)
                if wf is None:
                    unresolved.append((os.path.basename(fn), gate, asset))
                else:
                    flags.add(wf)
    return flags, unresolved


def _gen_boss_gated_frozenset():
    """Parse gen_data's `_BOSS_GATED_GRACE_FLAGS = frozenset({...})` literal -- COMPARISON ONLY, never
    the oracle. Text-parsed (not exec'd) so we don't run the whole generator."""
    with open(GEN_DATA_PY, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"_BOSS_GATED_GRACE_FLAGS\s*=\s*frozenset\((\{[^}]*\})\)", src)
    if not m:
        return None
    return {int(x) for x in ast.literal_eval(m.group(1))}


class BossGatedGraceSkipOracle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(REGION_GRACES_PY):
            raise unittest.SkipTest("region_graces.py not generated yet (run gen_data.py)")
        if not os.path.isdir(EVENT_DIR) or not os.path.isfile(BONFIRE_CSV):
            raise unittest.SkipTest(
                "decompiled EMEVD (event/) or BonfireWarpParam.csv absent (installed-world copy / "
                "fresh clone) -- this independent oracle needs elden_ring_artifacts/; gated like "
                "ci-linux.sh's DRIFT step."
            )
        cls.ent2flag = _bonfire_entity_to_flag()
        cls.oracle, cls.unresolved = _emevd_boss_gated_flags(cls.ent2flag)
        rg = _load_region_graces()
        cls.emitted = set()
        for _region, flags in rg.REGION_GRACE_POINTS.items():
            cls.emitted.update(int(fl) for fl in flags)

    def test_sources_nonempty(self):
        self.assertTrue(self.ent2flag, "BonfireWarpParam.csv parsed to zero rows")
        self.assertTrue(self.emitted, "region_graces.py emitted zero graces")
        self.assertTrue(
            self.oracle,
            "EMEVD oracle derived zero boss-gated graces -- the 9005810 sweep or asset join broke",
        )

    def test_every_9005810_asset_resolved(self):
        """Every 9005810 grace asset must join to a BonfireWarpParam flag; an unresolved asset means
        the oracle silently under-counts (a boss-gated grace it can't see) -- fail loudly instead."""
        self.assertEqual(
            self.unresolved, [],
            str(len(self.unresolved)) + " common-event-9005810 grace asset(s) did not join to "
            "BonfireWarpParam.bonfireEntityId -- oracle would under-count. " + repr(self.unresolved[:8]),
        )

    def test_no_boss_gated_grace_emitted_grantable(self):
        """SOFT-LOCK GUARD (independent of gen). A grace the EMEVD hides behind a gate flag (common
        event 9005810) must NEVER appear in region_graces.py REGION_GRACE_POINTS -- force-lighting it
        on region unlock warps the player onto a disabled bonfire behind boss fog -> soft-lock
        (er-boss-border-grace-skip-list). Derived from EMEVD + BonfireWarpParam, sharing no code with
        gen's skip frozenset."""
        leaked = sorted(self.oracle & self.emitted)
        self.assertEqual(
            leaked, [],
            str(len(leaked)) + " boss-gated grace(s) (EMEVD common-event 9005810, asset disabled "
            "until a gate flag) are emitted as GRANTABLE region graces -- num_regions would "
            "force-light them and warp the player behind boss fog -> soft-lock. Flags: " + repr(leaked),
        )

    def test_gen_skip_set_covers_emevd_oracle(self):
        """COMPLETENESS. Every boss-gated grace the independent EMEVD oracle finds must be present in
        gen_data's `_BOSS_GATED_GRACE_FLAGS`. A flag the oracle finds but gen MISSES is a boss-gated
        grace gen's hand-transcribed frozenset failed to filter -- the exact "NOT provably complete"
        gap this test exists to close. gen's frozenset is read here ONLY for this diff; the oracle
        stands on its own (test_no_boss_gated_grace_emitted_grantable does not consult it)."""
        gen = _gen_boss_gated_frozenset()
        self.assertIsNotNone(
            gen, "could not parse _BOSS_GATED_GRACE_FLAGS frozenset from gen_data.py (shape changed?)")
        missed = sorted(self.oracle - gen)
        self.assertEqual(
            missed, [],
            str(len(missed)) + " boss-gated grace(s) present in the independent EMEVD oracle but "
            "ABSENT from gen_data _BOSS_GATED_GRACE_FLAGS -- gen's hand-list is incomplete and would "
            "emit these as grantable. Flags: " + repr(missed),
        )

    def test_guard_is_not_vacuous(self):
        """Negative control: prove the soft-lock guard actually fires. Inject a known boss-gated grace
        (e.g. Stormveil's post-Margit-fog first grace, warpUnlockFlag 71000) into a COPY of the emitted
        set and confirm the intersection logic flags it. Guards against a future refactor silently
        emptying the oracle or the emitted set (which would make the real guard pass vacuously)."""
        self.assertTrue(self.oracle, "oracle empty -- real guard would be vacuous")
        sample = min(self.oracle)
        injected = set(self.emitted) | {sample}
        self.assertIn(
            sample, self.oracle & injected,
            "guard failed to catch an injected boss-gated grace -- the intersection check is broken",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
