"""Grace-skip oracles for the two HAND-CURATED skip classes (tier A: independent artifact-derived).

test_gf_grace_skip_oracle.py proves gen's `_BOSS_GATED_GRACE_FLAGS` complete against the EMEVD
common-event 9005810 (boss BONFIRE hide) oracle. gen carries two MORE skip sets that had no oracle
and both leaked in playtest (2026-07-07):

  - `_ARENA_GRACE_FLAGS` -- remembrance-boss arena graces. Missed Maliketh 71300 until a playtest
    warped a player into Crumbling Farum Azula's sealed arena.
  - `_ASHEN_LEYNDELL_GRACE_FLAGS` -- m11_05 (Leyndell, Ashen Capital), a POST-ERDTREE-BURN map
    variant. Missed until 71123 "Leyndell, Capital of Ash" leaked into the Leyndell grant bundle.

This file adds one independent oracle per class so gen FAILS on the next gap instead of a playtester
finding it.

ORACLE A -- bespoke hidden-bonfire sweep (catches Maliketh 71300)
-----------------------------------------------------------------
VERIFIED: common events 9005811 / 9005812 / 9005813 ("[Common] White door treatment for boss" /
"...Ver2" / "...Ver3" in common_func.emevd.dcx.js) manage the boss WHITE FOG GATE asset, not a
bonfire: body = DisableAsset(fog); WaitFor(phantom-state / activation conditions); EnableAsset(fog);
their assetEntityId arg is the FOG asset. Empirically ZERO of their 162 asset args join to
BonfireWarpParam.bonfireEntityId (test_fog_door_events_gate_fog_not_graces), so fog-door args CANNOT
yield the gated-grace set -- that derivation path is dead, and this test pins that fact.

The real EMEVD signal for Maliketh is a BESPOKE MAP-LOCAL CLONE of the 9005810 body: m13 event
13002805 ("Bonfire processing for Marikes"):
    DisableAsset(13001950); WaitFor(EventFlag(13000800)); EnableAsset(13001950);
    RegisterBonfire(13000000, 13001950, ...)
i.e. a bonfire asset hidden until a gate flag, registered in the SAME event -- exactly the 9005810
semantics, but inlined so the 9005810 oracle cannot see it. Oracle A sweeps every decompiled map
EMEVD for event bodies containing both DisableAsset(N) and RegisterBonfire(_, N) with the same
literal asset N, then joins N -> BonfireWarpParam.eventflagId. Derived with zero reference to gen's
frozensets. On current artifacts it finds exactly {71300}.

KNOWN BLIND SPOT (documented SkipTest, not an invented list): the OVERWORLD remembrance-arena
graces (gen's 76xxx arena entries) live on m60_/m61_ tiles whose EMEVD is present only as .dcx
(Oodle-compressed, no .js decompile in elden_ring_artifacts/event/) and whose appear-on-boss-death
gating is MSB-side (asset enable), with the relevant tile MSBs not unpacked. No clean independent
source exists in the artifact set; the real source is named in the skip message.

ORACLE B -- map-variant (state-gated map swap) graces (catches 71123 + the whole m11_05 set)
--------------------------------------------------------------------------------------------
m11_05 re-places graces at the SAME world position as m11_00 base-Leyndell graces (e.g. 71121 at
(-132.0, y, -386.5) == 71100-series twin exactly; 5 of its 6 graces coincide within 2m). That is the
signature of a STATE-GATED MAP SWAP: two map blocks of the same area occupying one physical space,
only one loaded at a time. Force-lighting the variant's graces via a region lock drops the player
into a world state they have not triggered (pre-burn player in the Ashen Capital). Derivation, from
grace_flags.tsv alone (rowId/warpUnlockFlag/mapTile/posX/posY/posZ -- lifted from BonfireWarpParam,
never from gen):
    1. Restrict to legacy maps (mapTile not m60_*/m61_*): legacy grace coords are map-global;
       overworld tile coords are tile-local and would collide by accident.
    2. Two tiles of the SAME area (mAA equal) are a variant pair if >= 2 graces coincide within
       2.0m on all three axes.
    3. The HIGHER block number is the variant (game boots the _00 block; ceremony/state swaps load
       a higher-block msb over the same space -- m11_00 base -> m11_05 ashen). All graces on the
       variant tile are state-gated, including ones with no positional twin (71123 is NEW in the
       ash state).
On current artifacts this finds exactly one pair, (m11_00, m11_05), gating {71120..71125}.
Corroboration that EMEVD could NOT provide this: m11_05's own emevd registers 11051952-55 (71122-25)
plainly at map init -- the gate is the map swap itself, invisible to event script.

Each oracle asserts (1) no gated grace is emitted grantable in region_graces.REGION_GRACE_POINTS,
(2) COMPLETENESS: oracle set is covered by gen's union skip set (gen's frozensets are text-parsed
for this diff ONLY -- never used as the oracle), and (3) non-vacuity: injecting the known playtest
leak (71300 / 71123) into a scratch copy of REGION_GRACE_POINTS is caught.

Skip-when-source-absent (artifacts live only in elden_ring_artifacts/, like the 9005810 oracle).

Run:  python -m pytest greenfield/eldenring/tests/test_gf_grace_skip_classes.py
  or: python greenfield/eldenring/tests/test_gf_grace_skip_classes.py
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
GRACE_TSV = os.path.join(ARTIFACTS, "grace_flags.tsv")
REGION_GRACES_PY = os.path.join(GF_PKG, "region_graces.py")
GEN_DATA_PY = os.path.join(GREENFIELD, "gen_data.py")

# Playtest leaks of 2026-07-07 -- the non-vacuity anchors each oracle MUST re-find on its own.
MALIKETH_ARENA_FLAG = 71300     # Crumbling Farum Azula: Maliketh arena grace (bespoke event 13002805)
ASHEN_LEAK_FLAG = 71123         # "Leyndell, Capital of Ash" (m11_05 map-variant grace)

# Boss white-fog-door common events (verified in common_func.emevd.dcx.js: they gate the FOG asset).
# InitializeCommonEvent(slot, 900581X, bossFlag, fogAssetEntityId, sfxId, ...): capture arg 2.
_INIT_FOG_DOOR = re.compile(
    r"InitializeCommonEvent\(\s*\d+\s*,\s*(?:9005811|9005812|9005813)\s*,\s*\d+\s*,\s*(\d+)\s*,")
_DISABLE_ASSET = re.compile(r"DisableAsset\(\s*(\d+)\s*\)")
_REGISTER_BONFIRE = re.compile(r"RegisterBonfire\(\s*\d+\s*,\s*(\d+)\s*,")
_VARIANT_EPS = 2.0              # metres; ashen twins differ by <= ~0.8m, unrelated graces by >> 10m


def _load_emitted():
    spec = importlib.util.spec_from_file_location("gf_region_graces_class_check", REGION_GRACES_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    emitted = set()
    for _region, flags in mod.REGION_GRACE_POINTS.items():
        emitted.update(int(fl) for fl in flags)
    return mod.REGION_GRACE_POINTS, emitted


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


def _fog_door_assets():
    """All asset args ever passed to fog-door commons 9005811/9005812/9005813, across map EMEVDs."""
    assets = set()
    for fn in glob.glob(os.path.join(EVENT_DIR, "m*.emevd.dcx.js")):
        with open(fn, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = _INIT_FOG_DOOR.search(line)
                if m:
                    assets.add(m.group(1))
    return assets


def _bespoke_hidden_bonfires(ent2flag):
    """ORACLE A. Sweep every decompiled map EMEVD for an event body that both DisableAsset(N)s and
    RegisterBonfire(_, N)s the SAME literal asset N -- the inlined 9005810 pattern (bonfire hidden
    until a gate flag). Join N -> warpUnlockFlag. Returns (flags:set, hits:list, unresolved:list)."""
    flags, hits, unresolved = set(), [], []
    for fn in sorted(glob.glob(os.path.join(EVENT_DIR, "m*.emevd.dcx.js"))):
        with open(fn, encoding="utf-8", errors="replace") as f:
            src = f.read()
        # Split on $Event( / Event( headers; each chunk approximates one event body (constructor
        # chunk 0 included -- a constructor that hides AND registers a bonfire is the same signal).
        for body in re.split(r"\$?Event\(", src):
            disabled = set(_DISABLE_ASSET.findall(body))
            if not disabled:
                continue
            for asset in _REGISTER_BONFIRE.findall(body):
                if asset in disabled:
                    wf = ent2flag.get(asset)
                    if wf is None:
                        unresolved.append((os.path.basename(fn), asset))
                    else:
                        flags.add(wf)
                        hits.append((os.path.basename(fn), asset, wf))
    return flags, hits, unresolved


def _grace_rows():
    with open(GRACE_TSV, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def _variant_gated_flags(rows):
    """ORACLE B. Position-coincidence sweep of grace_flags.tsv (legacy maps only): tiles of the same
    area with >= 2 graces coincident within _VARIANT_EPS are a base/variant pair; the higher block
    is the state-gated variant. Returns (flags:set, pairs:list[(base, variant, n_coincident)])."""
    bytile = {}
    for r in rows:
        tile = r["mapTile"]
        if tile.startswith(("m60", "m61")):
            continue        # overworld: tile-local coords, and grid tiles are not state variants
        try:
            bytile.setdefault(tile, []).append(
                (int(r["warpUnlockFlag"]), float(r["posX"]), float(r["posY"]), float(r["posZ"])))
        except (KeyError, ValueError):
            continue
    tiles = sorted(bytile)
    gated, pairs = set(), []
    for i, t1 in enumerate(tiles):
        for t2 in tiles[i + 1:]:
            if t1.split("_")[0] != t2.split("_")[0]:
                continue    # variant swaps stay within one area (mAA)
            n = sum(
                1 for _f1, x1, y1, z1 in bytile[t1] for _f2, x2, y2, z2 in bytile[t2]
                if abs(x1 - x2) <= _VARIANT_EPS and abs(y1 - y2) <= _VARIANT_EPS
                and abs(z1 - z2) <= _VARIANT_EPS)
            if n < 2:
                continue
            # game boots the _00 block; state swaps load a higher block over the same space
            base, variant = sorted((t1, t2), key=lambda t: int(t.split("_")[1]))
            pairs.append((base, variant, n))
            gated.update(f for f, _x, _y, _z in bytile[variant])
    return gated, pairs


def _gen_skip_frozensets():
    """Text-parse gen_data's three skip frozensets -- COMPARISON ONLY, never the oracle. Multiline-
    safe (the _ARENA literal spans lines). Returns dict name -> set(int) (value None if unparsed)."""
    with open(GEN_DATA_PY, encoding="utf-8") as f:
        src = f.read()
    out = {}
    for name in ("_BOSS_GATED_GRACE_FLAGS", "_ARENA_GRACE_FLAGS", "_ASHEN_LEYNDELL_GRACE_FLAGS"):
        m = re.search(re.escape(name) + r"\s*=\s*frozenset\((\{.*?\})\)", src, re.DOTALL)
        out[name] = {int(x) for x in ast.literal_eval(m.group(1))} if m else None
    return out


def _artifacts_or_skip():
    if not os.path.isfile(REGION_GRACES_PY):
        raise unittest.SkipTest("region_graces.py not generated yet (run gen_data.py)")
    if not os.path.isdir(EVENT_DIR) or not os.path.isfile(BONFIRE_CSV) \
            or not os.path.isfile(GRACE_TSV):
        raise unittest.SkipTest(
            "elden_ring_artifacts/ (event/ decompiles, BonfireWarpParam.csv, grace_flags.tsv) "
            "absent (fresh clone / installed-world copy) -- independent oracles need the artifact "
            "dump; gated like ci-linux.sh's DRIFT step.")


class BespokeHiddenBonfireOracle(unittest.TestCase):
    """ORACLE A: map-local hidden-until-flag bonfires (the Maliketh 71300 class)."""

    @classmethod
    def setUpClass(cls):
        _artifacts_or_skip()
        cls.ent2flag = _bonfire_entity_to_flag()
        cls.fog_assets = _fog_door_assets()
        cls.oracle, cls.hits, cls.unresolved = _bespoke_hidden_bonfires(cls.ent2flag)
        cls.points, cls.emitted = _load_emitted()

    def test_sources_nonempty(self):
        self.assertTrue(self.ent2flag, "BonfireWarpParam.csv parsed to zero rows")
        self.assertTrue(self.emitted, "region_graces.py emitted zero graces")
        self.assertTrue(self.fog_assets, "no 9005811/9005812/9005813 fog-door inits found at all")

    def test_fog_door_events_gate_fog_not_graces(self):
        """Premise pin: the white-fog-door commons gate FOG assets, never bonfires. If an asset arg
        of 9005811/12/13 ever joins to BonfireWarpParam, a grace is being fog-door-managed directly
        and this oracle's model (and gen's) must be revisited."""
        grace_fog = sorted(self.ent2flag[a] for a in self.fog_assets if a in self.ent2flag)
        self.assertEqual(
            grace_fog, [],
            "fog-door common-event asset(s) joined to bonfire entities -- graces managed by "
            "9005811/12/13 directly, oracle model needs extending. Flags: " + repr(grace_fog))

    def test_all_bespoke_assets_resolved(self):
        """Every hidden-and-registered bonfire asset must join to a warp flag, else the oracle
        silently under-counts."""
        self.assertEqual(
            self.unresolved, [],
            str(len(self.unresolved)) + " bespoke hidden-bonfire asset(s) did not join to "
            "BonfireWarpParam.bonfireEntityId -- oracle would under-count: " + repr(self.unresolved))

    def test_oracle_refinds_maliketh(self):
        """Non-vacuity anchor: the oracle must independently re-find the 2026-07-07 playtest leak
        (Maliketh 71300, bespoke m13 event 13002805) with zero reference to gen's hand-add."""
        self.assertIn(
            MALIKETH_ARENA_FLAG, self.oracle,
            "bespoke hidden-bonfire sweep no longer finds Maliketh 71300 (m13 event 13002805 "
            "DisableAsset(13001950)+RegisterBonfire) -- sweep or artifacts broke. Hits: "
            + repr(self.hits))

    def test_no_bespoke_hidden_grace_emitted_grantable(self):
        """SOFT-LOCK GUARD (independent of gen): no grace whose bonfire asset the EMEVD hides until
        a gate flag may appear in REGION_GRACE_POINTS -- force-lighting it warps the player onto a
        disabled bonfire inside a sealed boss arena."""
        leaked = sorted(self.oracle & self.emitted)
        self.assertEqual(
            leaked, [],
            str(len(leaked)) + " bespoke-hidden boss-arena grace(s) emitted as grantable region "
            "graces (the Maliketh-71300 class). Flags: " + repr(leaked))

    def test_gen_skip_sets_cover_bespoke_oracle(self):
        """COMPLETENESS diff: every bespoke-hidden grace must be in gen's union skip set
        (_BOSS_GATED | _ARENA | _ASHEN_LEYNDELL). gen's frozensets are read ONLY for this diff."""
        gen = _gen_skip_frozensets()
        missing_sets = [k for k, v in gen.items() if v is None]
        self.assertEqual(missing_sets, [],
                         "could not text-parse gen_data skip frozenset(s): " + repr(missing_sets))
        union = gen["_BOSS_GATED_GRACE_FLAGS"] | gen["_ARENA_GRACE_FLAGS"] \
            | gen["_ASHEN_LEYNDELL_GRACE_FLAGS"]
        missed = sorted(self.oracle - union)
        self.assertEqual(
            missed, [],
            str(len(missed)) + " bespoke-hidden boss-arena grace(s) ABSENT from gen_data's skip "
            "sets -- the hand-curated lists are incomplete, these would leak in playtest. Flags: "
            + repr(missed))

    def test_guard_catches_injected_maliketh(self):
        """Negative control: inject the real 2026-07-07 leak (71300) into a scratch copy of
        REGION_GRACE_POINTS and prove the guard fires -- guards against the sweep or the emitted
        load silently going empty (vacuous pass)."""
        scratch = {r: list(fls) for r, fls in self.points.items()}
        next(iter(scratch.values())).append(MALIKETH_ARENA_FLAG)
        injected = set()
        for fls in scratch.values():
            injected.update(int(fl) for fl in fls)
        self.assertIn(
            MALIKETH_ARENA_FLAG, self.oracle & injected,
            "injected Maliketh arena grace 71300 was NOT caught -- oracle A is vacuous")


class MapVariantGraceOracle(unittest.TestCase):
    """ORACLE B: state-gated map-variant graces (the m11_05 Ashen Capital class)."""

    @classmethod
    def setUpClass(cls):
        _artifacts_or_skip()
        cls.oracle, cls.pairs = _variant_gated_flags(_grace_rows())
        cls.points, cls.emitted = _load_emitted()

    def test_oracle_refinds_ashen_leyndell(self):
        """Non-vacuity anchor: the coincidence sweep must independently re-find the m11_00/m11_05
        pair and gate the 2026-07-07 playtest leak 71123 -- including it via its TILE even though it
        is a NEW ash-state grace with no positional twin."""
        self.assertIn(
            ("m11_00_00", "m11_05_00"),
            [(b, v) for b, v, _n in self.pairs],
            "coincidence sweep no longer detects m11_05 as a variant of m11_00; pairs: "
            + repr(self.pairs))
        self.assertIn(
            ASHEN_LEAK_FLAG, self.oracle,
            "variant oracle lost 71123 'Leyndell, Capital of Ash' -- tile-level gating broke")

    def test_no_variant_grace_emitted_grantable(self):
        """PREMATURE-STATE GUARD (independent of gen): no grace on a state-variant map block may be
        emitted grantable -- force-lighting it drops the player into a world state they have not
        triggered (pre-burn player in the Ashen Capital)."""
        leaked = sorted(self.oracle & self.emitted)
        self.assertEqual(
            leaked, [],
            str(len(leaked)) + " map-variant (state-gated) grace(s) emitted as grantable region "
            "graces. Flags: " + repr(leaked) + "; variant pairs: " + repr(self.pairs))

    def test_gen_skip_sets_cover_variant_oracle(self):
        """COMPLETENESS diff: every variant-gated grace must be in gen's union skip set. Flags any
        NEW variant tile (or newly shipped map state) gen's hand list misses."""
        gen = _gen_skip_frozensets()
        self.assertTrue(all(v is not None for v in gen.values()),
                        "could not text-parse gen_data skip frozensets")
        union = gen["_BOSS_GATED_GRACE_FLAGS"] | gen["_ARENA_GRACE_FLAGS"] \
            | gen["_ASHEN_LEYNDELL_GRACE_FLAGS"]
        missed = sorted(self.oracle - union)
        self.assertEqual(
            missed, [],
            str(len(missed)) + " map-variant grace(s) ABSENT from gen_data's skip sets. Flags: "
            + repr(missed) + "; variant pairs: " + repr(self.pairs))

    def test_guard_catches_injected_ashen(self):
        """Negative control: inject the real 2026-07-07 leak (71123) into a scratch copy of
        REGION_GRACE_POINTS and prove the guard fires."""
        scratch = {r: list(fls) for r, fls in self.points.items()}
        next(iter(scratch.values())).append(ASHEN_LEAK_FLAG)
        injected = set()
        for fls in scratch.values():
            injected.update(int(fl) for fl in fls)
        self.assertIn(
            ASHEN_LEAK_FLAG, self.oracle & injected,
            "injected ashen-Leyndell grace 71123 was NOT caught -- oracle B is vacuous")


class OverworldArenaGraceBlindSpot(unittest.TestCase):
    """The overworld remembrance-arena sub-class has NO clean independent source in the artifact
    dump -- documented Skip naming the real source rather than an invented list."""

    def test_overworld_arena_class_needs_tile_decompiles(self):
        _artifacts_or_skip()
        # Measure the blind spot live so the skip message stays honest: emitted graces whose home
        # tile has a .dcx EMEVD but no .js decompile are invisible to Oracle A.
        rows = _grace_rows()
        flag2tile = {}
        for r in rows:
            try:
                flag2tile[int(r["warpUnlockFlag"])] = r["mapTile"]
            except (KeyError, ValueError):
                continue
        _points, emitted = _load_emitted()
        undecompiled = sorted({
            flag2tile[f] for f in emitted
            if f in flag2tile
            and not os.path.isfile(os.path.join(EVENT_DIR, flag2tile[f] + "_00.emevd.dcx.js"))})
        raise unittest.SkipTest(
            "Overworld remembrance-arena graces (gen's 76xxx _ARENA entries, e.g. 76930/76931 "
            "Gaius / 76415 Dragonbarrow-class arenas) appear on boss death via MSB-side asset "
            "enable on m60_/m61_ tiles with NO EMEVD .js decompile in elden_ring_artifacts/event/ "
            "(their gating is invisible to Oracle A's sweep). Real source needed: decompile the "
            "tile .emevd.dcx (and/or unpack the tile .msb.dcx asset enable-flags) with WitchyBND "
            "(Windows-only) for the arena tiles -- until then this sub-class rests on the "
            "playtest-fed hand list. Current oracle blind spot: " + str(len(undecompiled))
            + " emitted-grace tiles without decompiles, e.g. " + repr(undecompiled[:6]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
