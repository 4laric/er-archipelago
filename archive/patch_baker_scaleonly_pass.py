#!/usr/bin/env python3
"""
patch_baker_scaleonly_pass.py -- isolate completion scaling from enemy randomization.

GOAL (Alaric, 2026-06-19, for playtest): run completion_scaling WITHOUT randomize_enemies.
SPEC-completion-scaling.md open-Q C: "Forcing opt[scale] ... means owning the in-place scale pass on
its own -- confirm that path is safe without a relocation map." This patch owns that pass.

WHY a new pass is needed (verified in source): the scaling SpEffect is only stamped in the transplant
loop (EnemyRandomizer.cs ~L7637 `foreach transfer in revMapping`). With enemy rando off, the permutation
is identity, and the transplant loop SKIPS identity entries (`if (source == target) continue;` ~L3303)
BEFORE populating revMapping -- so revMapping is empty and nothing scales. We can't reuse that loop.

DESIGN (surgical, reuses tested machinery, no factoring of the 8k-line RunGame):
  EnemyRandomizer.cs (CRLF):
    1. new field `public bool ScaleOnly = false;`
    2. `isRandomized(...)` short-circuits to false when ScaleOnly -> every silo gets the identity
       mapping it already assigns at ~L1643, and anyRandomized stays false (no swaps).
    3. a self-contained in-place apply block inserted just before the EMEVD-write loop (~L7925).
       For every enemy (identity), it calls the existing local getScalingSections(target,target,...)
       (native -> reshaped section, honors noscale tags), looks up the existing scalingSpEffects.Areas
       table, and emits the existing addCommonFuncInit("scale"/"scale2", ...). All helpers + state
       (ownerMap, newEvents, infos, targetScalingSections) are already in scope at that point.
  ArchipelagoForm.cs (LF):
    4. else-branch on the randomize_enemies gate: when ER && completion_scaling>0 && enemy rando off,
       build the enemy randomizer exactly like the rando branch (Base\events.txt config), set
       ScaleOnly=true + CompletionScale fields, and Run(opt, null). Identity pass + in-place scaling.

The reshape that fills targetScalingSections (added by patch_baker_completion_scaling.py ~L1071) runs
on CompletionScaleMode>0 regardless of randomization, so geographic v1 works today; the sphere v2
reshape (separate patch) will too -- this pass is basis-agnostic.

PREREQ: patch_baker_completion_scaling.py must already be applied (provides CompletionScaleMode/
FloorPct fields + the reshape block). This patch FAILs loudly if its field anchor is missing.

Run on Windows; rebuild SoulsRandomizers. Idempotent. Per-file line endings preserved (ER=CRLF, AF=LF).
bake-test: completion_scaling=steep + randomize_enemies=false -> ap_bake log should show
"CompletionScaling scale-only: applied in-place scaling to N enemies".
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


# ---------------- EnemyRandomizer.cs (CRLF) ----------------

# 1. ScaleOnly field, grouped with the completion-scaling fields from patch_baker_completion_scaling.py.
ER_FIELD_ANCHOR = _crlf("        public int CompletionScaleFloorPct = 0;\n")
ER_FIELD = _crlf(
    "        // Scale-only mode (SPEC-completion-scaling.md open-Q C): when set, isRandomized()\n"
    "        // returns false for every class -> identity permutation (no swaps), but the reshaped\n"
    "        // tiers are applied IN PLACE by the scale-only block before the EMEVD-write loop. Lets\n"
    "        // completion_scaling run with enemy_rando OFF. Set by ArchipelagoForm. Inert for GUI.\n"
    "        public bool ScaleOnly = false;\n"
)

# 2. isRandomized short-circuit.
ER_ISRAND_ANCHOR = _crlf("            bool isRandomized(EnemyClass type)\n            {\n")
ER_ISRAND = _crlf("                if (ScaleOnly) return false;  // force identity permutation; scaling applied in place\n")

# 3. In-place scale-only apply block, just before the reverse-mapping / EMEVD-write loop.
ER_APPLY_ANCHOR = _crlf("            // Reverse mapping for Elden Ring, where we may need to create new emevds\n")
ER_APPLY = _crlf('''\
            // Scale-only completion scaling (SPEC-completion-scaling.md open-Q C). With ScaleOnly the
            // permutation is identity, so the transplant loop above scaled nothing (it skips
            // source==target). Apply the reshaped tiers in place here, reusing getScalingSections
            // (native -> targetScalingSections, honors noscale), the scaling SpEffect table, and
            // addCommonFuncInit -- exactly the machinery the transplant scaling uses.
            if (ScaleOnly && CompletionScaleMode > 0 && game.EldenRing && ann.ScalingSections != null)
            {
                int scaleOnlyCount = 0;
                foreach (KeyValuePair<int, EnemyInfo> soEntry in infos)
                {
                    int soTarget = soEntry.Key;
                    EnemyInfo soInfo = soEntry.Value;
                    if (revMapping.ContainsKey(soTarget)) continue;     // already handled (empty in scale-only)
                    if (!ownerMap.ContainsKey(soTarget)) continue;      // no event map -> can't init scaling
                    getScalingSections(soTarget, soTarget, out int soSrc, out int soTgt);
                    if (soSrc <= 0 || soTgt <= 0 || soSrc == soTgt) continue;
                    if (!scalingSpEffects.Areas.TryGetValue((soSrc, soTgt), out ScalingEffects.AreaScalingValue soSp)) continue;
                    string soEvent = (soInfo.Class == EnemyClass.Helper || soInfo.IsBossTarget) ? "scale2" : "scale";
                    int soScaleSp = soInfo.IsFixedSource
                        ? (soInfo.HasTag("nonunique") ? soSp.FixedScaling : soSp.UniqueFixedScaling)
                        : soSp.RegularScaling;
                    addCommonFuncInit(soEvent, soTarget, new List<object> { soTarget, soScaleSp });
                    scaleOnlyCount++;
                }
                Console.WriteLine($"CompletionScaling scale-only: applied in-place scaling to {scaleOnlyCount} enemies (no enemy rando).");
            }

''')

# ---------------- ArchipelagoForm.cs (LF) ----------------

# 4. else-branch on the randomize_enemies gate. Anchor = end of the non-ER else + close of the
#    inner type-switch + close of the outer randomize_enemies if (unique in the file).
AF_ANCHOR = _lf(
    "                    new EnemyRandomizer(game, events, eventConfig).Run(opt, preset);\n"
    "                }\n"
    "            }\n"
)
AF_INSERT = _lf('''\
            else if (type == FromGame.ER
                     && (((JObject)slotData["options"])?["completion_scaling"]?.Value<int>() ?? 0) > 0)
            {
                // Completion scaling WITHOUT enemy randomization (SPEC-completion-scaling.md open-Q C;
                // enemy_rando:false isolation for playtest). Run the enemy pass in scale-only mode:
                // ScaleOnly forces an identity permutation (no swaps) and EnemyRandomizer applies the
                // reshaped tiers in place. Mirrors the ER enemy-rando setup above (Base\\events.txt).
                EventConfig scaleEventConfig;
                using (var reader = File.OpenText($@"{game.Dir}\\Base\\events.txt"))
                {
                    scaleEventConfig = new DeserializerBuilder().Build().Deserialize<EventConfig>(reader);
                }
                var scaleEvents = new Events(
                    null,
                    darkScriptMode: true,
                    paramAwareMode: true,
                    valueSpecs: scaleEventConfig.ValueTypes);
                var scaleRando = new EnemyRandomizer(game, scaleEvents, scaleEventConfig);
                scaleRando.ScaleOnly = true;
                scaleRando.CompletionScaleMode = (slotData["options"] as JObject)?["completion_scaling"]?.Value<int>() ?? 0;
                scaleRando.CompletionScaleFloorPct = (slotData["options"] as JObject)?["completion_scaling_floor"]?.Value<int>() ?? 0;
                scaleRando.Run(opt, null);
            }
''')


def patch_er(data):
    if b"public bool ScaleOnly" in data:
        print("[skip] EnemyRandomizer.cs already patched.")
        return data, False
    if data.count(ER_FIELD_ANCHOR) != 1:
        raise SystemExit("[FAIL] EnemyRandomizer.cs: CompletionScaleFloorPct field not found -- "
                         "apply patch_baker_completion_scaling.py FIRST. No write.")
    data = _ins_after(data, ER_FIELD_ANCHOR, ER_FIELD, "ER ScaleOnly field")
    data = _ins_after(data, ER_ISRAND_ANCHOR, ER_ISRAND, "ER isRandomized short-circuit")
    data = _ins_before(data, ER_APPLY_ANCHOR, ER_APPLY, "ER scale-only apply block")
    return data, True


def patch_af(data):
    if b"scaleRando.ScaleOnly = true;" in data:
        print("[skip] ArchipelagoForm.cs already patched.")
        return data, False
    data = _ins_after(data, AF_ANCHOR, AF_INSERT, "AF scale-only else-branch")
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
        print("[ok] patched EnemyRandomizer.cs (ScaleOnly field + isRandomized + apply block)")
    if afc:
        _write(AF, af2)
        print("[ok] patched ArchipelagoForm.cs (scale-only else-branch)")
    if not (erc or afc):
        print("[done] nothing to do.")
    else:
        print("[done] scale-only layer applied. Rebuild SoulsRandomizers; bake-test "
              "completion_scaling=steep + randomize_enemies=false.")


if __name__ == "__main__":
    main()
