#!/usr/bin/env python3
"""
patch_baker_sphere_scaling_bridge.py -- Track C of the num_regions chain / sphere-ordered scaling
feature (TODO #22). SPEC: SPEC-num-regions-chain.md, frozen contract section 4.

WHAT THIS DOES
--------------
The v1 completion scaling (patch_baker_completion_scaling.py + patch_baker_scaleonly_pass.py)
reshapes every enemy's NATIVE GEOGRAPHIC tier along a curve+floor. That is "basis=geographic":
ER's built-in geographic ordering IS the difficulty ramp. This bridge adds "basis=sphere": instead
of reading the enemy's geographic tier, the target tier comes from the AP FILL SPHERE of the region
the enemy lives in -- so difficulty ramps along the apworld's lock chain (early chain link easier
than a late link), not along ER's geography.

The contract (SPEC section 4, FROZEN) ships two NEW slot_data keys at the TOP LEVEL:
  completionScalingBasis : int   -- 0 geographic (v1), 1 sphere (this bridge)
  regionSphereTargets    : { "<AP region name>": float in [0,1], 4dp }
        target = floor + curve(region_sphere / maxSphere) * (1 - floor), precomputed by the apworld.
The float is ALREADY the post-curve, post-floor [0,1] target tier fraction -- the baker multiplies it
by MaxTier and rounds, it does NOT re-apply the curve/floor (those live in the apworld for sphere
basis; geographic basis still applies them here exactly as v1).

THREE EDITS
-----------
EnemyRandomizer.cs (CRLF):
  E1. Two new fields next to CompletionScaleMode/FloorPct:
        public int CompletionScaleBasis = 0;                     // 0 geographic, 1 sphere
        public Dictionary<string,double> RegionSphereTargets;    // AP region name -> target [0,1]
  E2. A self-contained MSB-map -> AP-region resolver + per-enemy override, spliced INTO the existing
      reshape loop right where compT is computed. When basis==sphere AND the enemy's region resolves
      AND that region is in RegionSphereTargets, compT is overridden with the region's target. Every
      other enemy (unmapped map, region not in the table, basis=geographic) keeps the v1 compT, so
      this is strictly additive and safe. A counter (compSphereHits) is printed by the diag below.

      *** MSB->AP-region resolver is a STUB (see CompApRegionForMap). It is keyed on the enemy's
          EnemyInfo.Map (an MSB id like "m10_00_00_00" / "m60_42_36_00"). The starter table covers
          the legacy dungeons + the m60 overworld-tile prefix bands, but it is NOT complete and the
          AP region NAMES must be reconciled with the apworld's region_order on Windows. Until the
          table is filled, unmapped enemies simply fall back to v1 geographic -- correct, just not
          yet sphere-shaped. See HANDOFF-num-regions-chain-trackC.md "Remaining for Windows". ***
  E3. Diag line (mirrors patch_baker_completion_scaling_diag.py) printing how many enemies were
      reshaped by a region sphere target vs left on geographic.

ArchipelagoForm.cs (LF):
  A1/A2. Thread completionScalingBasis + regionSphereTargets onto BOTH EnemyRandomizer callsites
         (the enemy-rando-ON pass and the scale-only pass). Top-level slot_data keys, read with
         TryGetValue because they are absent on pre-contract seeds (basis defaults 0 = v1).

HARD RULES honoured: byte-splice only, never edits the real .cs (Alaric runs on Windows + rebuilds),
idempotent, per-file line endings preserved (ER=CRLF, AF=LF). Anchors are unique-count-checked.

PREREQ: patch_baker_completion_scaling.py AND patch_baker_scaleonly_pass.py already applied (this
patch FAILs loudly if their anchors are missing -- it reuses their fields + reshape loop + diag).
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
ER = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon", "EnemyRandomizer.cs")
AF = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon", "ArchipelagoForm.cs")


def _read(p):
    with open(p, "rb") as f:
        return f.read()


def _write(p, d):
    with open(p, "wb") as f:
        f.write(d)


def _crlf(t):
    return t.replace("\n", "\r\n").encode("utf-8")


def _lf(t):
    return t.encode("utf-8")


def _ins_before(data, anchor, insert, label):
    if data.count(anchor) != 1:
        raise SystemExit(f"[FAIL] {label}: anchor x{data.count(anchor)} (want 1). No write.")
    return data.replace(anchor, insert + anchor, 1)


def _ins_after(data, anchor, insert, label):
    if data.count(anchor) != 1:
        raise SystemExit(f"[FAIL] {label}: anchor x{data.count(anchor)} (want 1). No write.")
    return data.replace(anchor, anchor + insert, 1)


def _replace(data, anchor, repl, label):
    if data.count(anchor) != 1:
        raise SystemExit(f"[FAIL] {label}: anchor x{data.count(anchor)} (want 1). No write.")
    return data.replace(anchor, repl, 1)


# ====================================================================================
# EnemyRandomizer.cs  (CRLF)
# ====================================================================================

# --- E1: two fields, inserted after the existing CompletionScaleFloorPct field ---
ER_FIELD_ANCHOR = _crlf("        public int CompletionScaleFloorPct = 0;\n")
ER_FIELDS = _crlf(
    "        // Sphere-ordered scaling (SPEC-num-regions-chain.md section 4, basis=sphere). Set by\n"
    "        // ArchipelagoForm from the top-level slot_data keys completionScalingBasis +\n"
    "        // regionSphereTargets. Basis 0 = geographic (v1, native tier reshape); 1 = sphere\n"
    "        // (per-region target from the AP fill order). RegionSphereTargets maps an AP region\n"
    "        // NAME -> a [0,1] target tier fraction the apworld already curved+floored. Null/empty\n"
    "        // or basis 0 => the v1 geographic path is used unchanged. Inert for GUI bakes.\n"
    "        public int CompletionScaleBasis = 0;\n"
    "        public Dictionary<string, double> RegionSphereTargets = null;\n"
)

# --- compSphereHits declaration, inserted right before the reshape loop body. Anchored on the
# compFloor line that opens the reshape body (unique). ---
ER_HITS_ANCHOR = _crlf(
    "                double compFloor = Math.Max(0, Math.Min(50, CompletionScaleFloorPct)) / 100.0;\n"
)
ER_HITS_DECL = _crlf(
    "                int compSphereHits = 0;   // enemies whose tier came from a region sphere target\n"
)

# --- E2: per-enemy sphere override, spliced where the reshape computes compT ---
# We REPLACE the single compT line (added by patch_baker_completion_scaling.py) so the geographic
# compT is computed first, then conditionally overridden by the region sphere target.
ER_COMPT_ANCHOR = _crlf(
    "                    double compT = compFloor + compCurve(compD) * (1.0 - compFloor);\n"
)
ER_COMPT_REPL = _crlf(
    "                    double compT = compFloor + compCurve(compD) * (1.0 - compFloor);\n"
    "                    // Sphere basis override (SPEC-num-regions-chain.md section 4): if this enemy's\n"
    "                    // AP region has a precomputed sphere target, use it DIRECTLY as the target tier\n"
    "                    // fraction (already curved+floored by the apworld). Else keep the geographic\n"
    "                    // compT above (unmapped map / region absent / basis=geographic).\n"
    "                    if (CompletionScaleBasis == 1 && RegionSphereTargets != null && RegionSphereTargets.Count > 0)\n"
    "                    {\n"
    "                        string compRegion = CompApRegionForMap(\n"
    "                            infos.TryGetValue(compTarget, out EnemyInfo compInfo) ? compInfo.Map : null);\n"
    "                        if (compRegion != null && RegionSphereTargets.TryGetValue(compRegion, out double compSphereT))\n"
    "                        {\n"
    "                            compT = compSphereT < 0.0 ? 0.0 : (compSphereT > 1.0 ? 1.0 : compSphereT);\n"
    "                            compSphereHits++;\n"
    "                        }\n"
    "                    }\n"
)

# --- E3: sphere diag line, inserted right after the existing CompletionScaling diag line ---
ER_DIAG_ANCHOR = _crlf(
    "                Console.WriteLine($\"CompletionScaling: mode={CompletionScaleMode} floor={CompletionScaleFloorPct}% \"\n"
    "                    + $\"MaxTier={compMaxTier} -> retiered enemies up={csUp} down={csDown} same={csSame}\");\n"
)
ER_DIAG_INS = _crlf(
    "                if (CompletionScaleBasis == 1)\n"
    "                    Console.WriteLine($\"CompletionScaling sphere basis: reshaped {compSphereHits} enemies by region target \"\n"
    "                        + $\"(targets={(RegionSphereTargets?.Count ?? 0)}); remainder on geographic fallback.\");\n"
)

# --- E2-resolver: the MSB-map -> AP-region resolver method, inserted as a sibling local function
# just BEFORE the existing local getScalingSections (the first local fn after the reshape block, so
# the resolver shares scope with the reshape loop). STUB table -- see HANDOFF. ---
ER_RESOLVER_ANCHOR = _crlf(
    "            bool getScalingSections(int source, int target, out int sourceSection, out int targetSection, bool ignoreCustom = false)\n"
)
ER_RESOLVER = _crlf(
    "            // MSB-map -> AP-region resolver for sphere-basis scaling (SPEC-num-regions-chain.md\n"
    "            // section 4). Input = EnemyInfo.Map, an MSB id (\"m10_00_00_00\" legacy dungeon, or\n"
    "            // \"m60_TT_TT_00\" overworld tile). Output = an AP REGION NAME matching the apworld's\n"
    "            // region_order (the keys of RegionSphereTargets). Returns null when unknown -> caller\n"
    "            // falls back to the v1 geographic tier (safe).\n"
    "            //\n"
    "            // *** STUB / INCOMPLETE -- VERIFY + EXTEND ON WINDOWS. ***\n"
    "            // The baker has no ready-made MSB->AP-region table: BossAttribution builds region\n"
    "            // membership from per-check positions + AP areas threaded in from ArchipelagoForm,\n"
    "            // which are NOT in scope here, and map_region_data.REGIONS is keyed on runtime\n"
    "            // FieldArea ids (61000...) not MSB ids. This starter table covers the legacy-dungeon\n"
    "            // MSBs + the m60 overworld-tile prefix bands, with names guessed to match the apworld.\n"
    "            // Reconcile every name against Archipelago/worlds/eldenring region_order (region names\n"
    "            // are full strings like \"Limgrave\", \"Stormveil Castle\"). Unmapped maps are harmless\n"
    "            // (geographic fallback) but never sphere-shaped, so fill this to make the feature bite.\n"
    "            string CompApRegionForMap(string msbMap)\n"
    "            {\n"
    "                if (string.IsNullOrEmpty(msbMap)) return null;\n"
    "                // Exact legacy-dungeon / interior MSB -> AP region name (extend me).\n"
    "                switch (msbMap)\n"
    "                {\n"
    "                    case \"m10_00_00_00\": return \"Stormveil Castle\";\n"
    "                    case \"m11_00_00_00\": return \"Leyndell, Royal Capital\";\n"
    "                    case \"m11_05_00_00\": return \"Leyndell, Ashen Capital\";\n"
    "                    case \"m13_00_00_00\": return \"Crumbling Farum Azula\";\n"
    "                    case \"m14_00_00_00\": return \"Raya Lucaria Academy\";\n"
    "                    case \"m15_00_00_00\": return \"Miquella's Haligtree\";\n"
    "                    case \"m16_00_00_00\": return \"Volcano Manor\";\n"
    "                    case \"m18_00_00_00\": return \"Stranded Graveyard\";\n"
    "                    case \"m19_00_00_00\": return \"Elphael, Brace of the Haligtree\";\n"
    "                    // Undergrounds (m12 quadrants) -- VERIFY split.\n"
    "                    case \"m12_01_00_00\": return \"Ainsel River\";\n"
    "                    case \"m12_02_00_00\": return \"Siofra River\";\n"
    "                    case \"m12_03_00_00\": return \"Deeproot Depths\";\n"
    "                    case \"m12_04_00_00\": return \"Ainsel River Main\";\n"
    "                    case \"m12_05_00_00\": return \"Mohgwyn Palace\";\n"
    "                    case \"m12_07_00_00\": return \"Siofra River\";\n"
    "                    case \"m12_09_00_00\": return \"Nokron, Eternal City Start\";\n"
    "                    default: break;\n"
    "                }\n"
    "                // Overworld tiles m60_XX_YY_00: classify by the FogMod-style XX/YY band. These\n"
    "                // bands are a COARSE GUESS off the world grid; refine against the apworld. The\n"
    "                // tile id parse mirrors the locId scheme noted in BossAttribution (m60_37_54_00).\n"
    "                if (msbMap.StartsWith(\"m60_\") && msbMap.Length >= 9)\n"
    "                {\n"
    "                    int compTx, compTy;\n"
    "                    if (int.TryParse(msbMap.Substring(4, 2), out compTx)\n"
    "                        && int.TryParse(msbMap.Substring(7, 2), out compTy))\n"
    "                    {\n"
    "                        // y high = north. VERY rough geographic bands; replace with the apworld's\n"
    "                        // tile->region grouping (map_region_data area_ids are runtime ids, not these).\n"
    "                        // Exact m60 tile -> AP region (derived from grace_flags.tsv x REGION_GRACE_POINTS;\n"
    "                        // bands cannot separate Liurnia/Altus/Mt.Gelmir/Caelid -- they interleave in YY).\n"
    "                        // Limgrave/Capital Outskirts have no grace tiles here -> unmatched falls to null (v1).\n"
    "                        string compTile = compTx.ToString(\"D2\") + \"_\" + compTy.ToString(\"D2\");\n"
    "                        switch (compTile)\n"
    "                        {\n"
    "                            case \"41_32\":\n"
    "                            case \"41_33\":\n"
    "                            case \"42_33\":\n"
    "                            case \"43_31\":\n"
    "                            case \"43_34\":\n"
    "                            case \"44_33\":\n"
    "                            case \"44_34\":\n"
    "                            case \"45_33\":\n"
    "                                return \"Weeping Peninsula\";\n"
    "                            case \"33_44\":\n"
    "                            case \"33_46\":\n"
    "                            case \"33_47\":\n"
    "                            case \"34_43\":\n"
    "                            case \"34_44\":\n"
    "                            case \"34_46\":\n"
    "                            case \"34_47\":\n"
    "                            case \"34_48\":\n"
    "                            case \"34_49\":\n"
    "                            case \"35_43\":\n"
    "                            case \"35_47\":\n"
    "                            case \"35_50\":\n"
    "                            case \"36_41\":\n"
    "                            case \"36_43\":\n"
    "                            case \"36_45\":\n"
    "                            case \"37_42\":\n"
    "                            case \"37_44\":\n"
    "                            case \"37_46\":\n"
    "                            case \"37_47\":\n"
    "                            case \"37_48\":\n"
    "                            case \"38_40\":\n"
    "                            case \"38_41\":\n"
    "                            case \"38_43\":\n"
    "                            case \"38_45\":\n"
    "                            case \"38_46\":\n"
    "                            case \"38_47\":\n"
    "                            case \"38_48\":\n"
    "                            case \"38_50\":\n"
    "                            case \"39_40\":\n"
    "                            case \"39_41\":\n"
    "                            case \"39_42\":\n"
    "                            case \"39_44\":\n"
    "                                return \"Liurnia of The Lakes\";\n"
    "                            case \"46_39\":\n"
    "                            case \"46_40\":\n"
    "                            case \"47_39\":\n"
    "                            case \"47_40\":\n"
    "                            case \"48_36\":\n"
    "                            case \"48_37\":\n"
    "                            case \"48_38\":\n"
    "                            case \"48_39\":\n"
    "                            case \"48_40\":\n"
    "                            case \"49_37\":\n"
    "                            case \"49_38\":\n"
    "                            case \"49_39\":\n"
    "                            case \"50_38\":\n"
    "                                return \"Caelid\";\n"
    "                            case \"50_36\":\n"
    "                            case \"51_36\":\n"
    "                                return \"Dragonbarrow\";\n"
    "                            case \"36_52\":\n"
    "                            case \"37_51\":\n"
    "                            case \"38_51\":\n"
    "                            case \"39_51\":\n"
    "                            case \"39_53\":\n"
    "                            case \"39_54\":\n"
    "                            case \"40_52\":\n"
    "                            case \"40_53\":\n"
    "                            case \"40_54\":\n"
    "                            case \"41_52\":\n"
    "                            case \"41_54\":\n"
    "                            case \"42_55\":\n"
    "                                return \"Altus Plateau\";\n"
    "                            case \"35_53\":\n"
    "                            case \"36_54\":\n"
    "                            case \"37_52\":\n"
    "                            case \"37_53\":\n"
    "                            case \"38_53\":\n"
    "                            case \"38_54\":\n"
    "                                return \"Mt. Gelmir\";\n"
    "                            default: return null;\n"
    "                        }\n"
    "                    }\n"
    "                }\n"
    "                return null;\n"
    "            }\n"
)


def patch_er(data):
    if b"CompletionScaleBasis" in data:
        print("[skip] EnemyRandomizer.cs already has sphere bridge.")
        return data, False
    # prereqs from the v1 patches
    if data.count(ER_FIELD_ANCHOR) != 1:
        raise SystemExit("[FAIL] EnemyRandomizer.cs: CompletionScaleFloorPct field missing -- apply "
                         "patch_baker_completion_scaling.py FIRST. No write.")
    if data.count(ER_COMPT_ANCHOR) != 1:
        raise SystemExit("[FAIL] EnemyRandomizer.cs: reshape compT line missing -- apply "
                         "patch_baker_completion_scaling.py FIRST. No write.")
    if data.count(ER_DIAG_ANCHOR) != 1:
        raise SystemExit("[FAIL] EnemyRandomizer.cs: CompletionScaling diag line missing -- apply "
                         "patch_baker_completion_scaling_diag.py FIRST. No write.")
    data = _ins_after(data, ER_FIELD_ANCHOR, ER_FIELDS, "ER sphere fields")
    data = _ins_before(data, ER_HITS_ANCHOR, ER_HITS_DECL, "ER compSphereHits decl")
    data = _replace(data, ER_COMPT_ANCHOR, ER_COMPT_REPL, "ER compT sphere override")
    data = _ins_after(data, ER_DIAG_ANCHOR, ER_DIAG_INS, "ER sphere diag")
    data = _ins_before(data, ER_RESOLVER_ANCHOR, ER_RESOLVER, "ER MSB->region resolver")
    return data, True


# ====================================================================================
# ArchipelagoForm.cs  (LF)
# ====================================================================================
# Shared helper text emitted at both callsites. We insert AFTER each existing
# CompletionScaleFloorPct assignment. Builds the Dictionary<string,double> from the top-level
# regionSphereTargets JObject (absent on pre-contract seeds -> stays null -> v1 path).
AF_SPHERE_BLOCK = (
    "{VAR}.CompletionScaleBasis = (slotData.TryGetValue(\"completionScalingBasis\", out var {V}Basis) "
    "&& {V}Basis is JToken {V}BasisTok) ? {V}BasisTok.Value<int>() : 0;\n"
    "{IND}if (slotData.TryGetValue(\"regionSphereTargets\", out var {V}Tgt) && {V}Tgt is JObject {V}TgtObj)\n"
    "{IND}{{\n"
    "{IND}    var {V}Map = new Dictionary<string, double>();\n"
    "{IND}    foreach (var {V}Prop in {V}TgtObj.Properties())\n"
    "{IND}        {V}Map[{V}Prop.Name] = {V}Prop.Value.Value<double>();\n"
    "{IND}    {VAR}.RegionSphereTargets = {V}Map;\n"
    "{IND}}}\n"
)

# Callsite 1: enemy-rando-ON pass (erRando). Anchor = its FloorPct assignment (20-space indent).
AF_ANCHOR_1 = (
    "                    erRando.CompletionScaleFloorPct = (slotData[\"options\"] as JObject)?"
    "[\"completion_scaling_floor\"]?.Value<int>() ?? 0;\n"
)
AF_INS_1 = _lf(
    "                    // Sphere basis + per-region targets (SPEC-num-regions-chain.md section 4),\n"
    "                    // top-level slot_data keys; absent on pre-contract seeds -> basis 0 = v1.\n"
    "                    " + AF_SPHERE_BLOCK.format(VAR="erRando", V="erSph", IND="                    ")
)

# Callsite 2: scale-only pass (scaleRando). Anchor = its FloorPct assignment (16-space indent).
AF_ANCHOR_2 = (
    "                scaleRando.CompletionScaleFloorPct = (slotData[\"options\"] as JObject)?"
    "[\"completion_scaling_floor\"]?.Value<int>() ?? 0;\n"
)
AF_INS_2 = _lf(
    "                // Sphere basis + per-region targets (SPEC-num-regions-chain.md section 4),\n"
    "                // top-level slot_data keys; absent on pre-contract seeds -> basis 0 = v1.\n"
    "                " + AF_SPHERE_BLOCK.format(VAR="scaleRando", V="scSph", IND="                ")
)


def patch_af(data):
    if b"CompletionScaleBasis" in data:
        print("[skip] ArchipelagoForm.cs already has sphere bridge.")
        return data, False
    a1 = AF_ANCHOR_1.encode("utf-8")
    a2 = AF_ANCHOR_2.encode("utf-8")
    if data.count(a1) != 1:
        raise SystemExit("[FAIL] ArchipelagoForm.cs: erRando FloorPct anchor missing -- apply "
                         "patch_baker_completion_scaling.py FIRST. No write.")
    if data.count(a2) != 1:
        raise SystemExit("[FAIL] ArchipelagoForm.cs: scaleRando FloorPct anchor missing -- apply "
                         "patch_baker_scaleonly_pass.py FIRST. No write.")
    data = data.replace(a1, a1 + AF_INS_1, 1)
    data = data.replace(a2, a2 + AF_INS_2, 1)
    return data, True


def main():
    for p in (ER, AF):
        if not os.path.isfile(p):
            raise SystemExit(f"[FAIL] not found: {p}")
    er = _read(ER)
    er2, erc = patch_er(er)
    af = _read(AF)
    af2, afc = patch_af(af)
    if erc:
        _write(ER, er2)
        print("[ok] patched EnemyRandomizer.cs (sphere fields + resolver + override + diag)")
    if afc:
        _write(AF, af2)
        print("[ok] patched ArchipelagoForm.cs (thread basis + targets onto both callsites)")
    if not (erc or afc):
        print("[done] nothing to do.")
    else:
        print("[done] sphere bridge applied. Rebuild SoulsRandomizers; enemy-OFF bake with "
              "completionScalingBasis=1 -> expect 'sphere basis: reshaped N enemies' in the log. "
              "FINISH the CompApRegionForMap stub on Windows (see HANDOFF-num-regions-chain-trackC.md).")


if __name__ == "__main__":
    main()
