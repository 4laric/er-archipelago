#!/usr/bin/env python3
"""
patch_baker_scaling_diag_20260622.py  --  RUN ON WINDOWS (Alaric), rebuild SoulsRandomizers (Release).

Per-enemy completion-scaling diagnostic. Instruments the scale-only pass (EnemyRandomizer.cs, the
no-enemy-rando path) so each enemy logs WHY it did or didn't scale. Gated behind env var
ER_DUMP_SCALING=1 so normal bakes are unaffected; output goes to the bake log (ap_bake_*.log).

Grep the log for `SCALEDIAG`. Each line:
    SCALEDIAG <entityId> <model>/<class> '<name>' [tags] native=<t> reshaped=<t> sp=<id> -> <verdict>
Verdicts:
    APPLIED            scaling speffect attached (native != reshaped)
    SKIP no-event-map  enemy's map has no EMEVD ("Unknown event map target ...") -> can't attach
    SKIP unchanged     native == reshaped (e.g. tier-1 fallback enemies like c5170 golems)
    SKIP no-section    native or reshaped <= 0
    SKIP no-area-value no scaling SpEffect row for that (src,tgt) tier pair

So: the Furnace Golems should show 'SKIP no-event-map' (m61_11_11_02 / m61_12_11_02) or 'SKIP
unchanged' (tier-1 fallback, pre furnace-golem patch); the Knight of the Solitary Gaol (2046410800,
c0000/MinorBoss) should show 'APPLIED'. Enemies absent from the dump entirely are not in `infos`.

Control flow is UNCHANGED (every continue still triggers on the same condition); only logging is added,
and it no-ops unless ER_DUMP_SCALING=1. NOTE: covers the scale-only path only (enemy_rando OFF). System
is not imported in this file, so Environment is fully qualified. Idempotent, CRLF-safe, anchor-verified.
"""

import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
CS = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon", "EnemyRandomizer.cs")
results = []

def _read(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def _write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(t)
def _eol(t): return "\r\n" if "\r\n" in t else "\n"
def _norm(s, eol): return s.replace("\r\n", "\n").replace("\n", eol)

_ANCHOR = (
    '                int scaleOnlyCount = 0;\n'
    '                foreach (KeyValuePair<int, EnemyInfo> soEntry in infos)\n'
    '                {\n'
    '                    int soTarget = soEntry.Key;\n'
    '                    EnemyInfo soInfo = soEntry.Value;\n'
    '                    if (revMapping.ContainsKey(soTarget)) continue;     // already handled (empty in scale-only)\n'
    '                    if (!ownerMap.ContainsKey(soTarget)) continue;      // no event map -> can\'t init scaling\n'
    '                    getScalingSections(soTarget, soTarget, out int soSrc, out int soTgt);\n'
    '                    if (soSrc <= 0 || soTgt <= 0 || soSrc == soTgt) continue;\n'
    '                    if (!scalingSpEffects.Areas.TryGetValue((soSrc, soTgt), out ScalingEffects.AreaScalingValue soSp)) continue;\n'
    '                    string soEvent = (soInfo.Class == EnemyClass.Helper || soInfo.IsBossTarget) ? "scale2" : "scale";\n'
    '                    int soScaleSp = soInfo.IsFixedSource\n'
    '                        ? (soInfo.HasTag("nonunique") ? soSp.FixedScaling : soSp.UniqueFixedScaling)\n'
    '                        : soSp.RegularScaling;\n'
    '                    addCommonFuncInit(soEvent, soTarget, new List<object> { soTarget, soScaleSp });\n'
    '                    scaleOnlyCount++;\n'
    '                }\n'
)

_REPLACE = (
    '                int scaleOnlyCount = 0;\n'
    '                bool scaleDiag = System.Environment.GetEnvironmentVariable("ER_DUMP_SCALING") == "1";\n'
    '                foreach (KeyValuePair<int, EnemyInfo> soEntry in infos)\n'
    '                {\n'
    '                    int soTarget = soEntry.Key;\n'
    '                    EnemyInfo soInfo = soEntry.Value;\n'
    '                    if (revMapping.ContainsKey(soTarget)) continue;     // already handled (empty in scale-only)\n'
    '                    if (!ownerMap.ContainsKey(soTarget))                // no event map -> can\'t init scaling\n'
    '                    {\n'
    '                        if (scaleDiag) Console.WriteLine($"SCALEDIAG {soTarget} {soInfo.ModelID}/{soInfo.Class} \'{soInfo.Name}\' [{soInfo.Tags}] -> SKIP no-event-map");\n'
    '                        continue;\n'
    '                    }\n'
    '                    getScalingSections(soTarget, soTarget, out int soSrc, out int soTgt);\n'
    '                    if (soSrc <= 0 || soTgt <= 0 || soSrc == soTgt)\n'
    '                    {\n'
    '                        if (scaleDiag) Console.WriteLine($"SCALEDIAG {soTarget} {soInfo.ModelID}/{soInfo.Class} \'{soInfo.Name}\' native={soSrc} reshaped={soTgt} -> SKIP {(soSrc == soTgt ? "unchanged" : "no-section")}");\n'
    '                        continue;\n'
    '                    }\n'
    '                    if (!scalingSpEffects.Areas.TryGetValue((soSrc, soTgt), out ScalingEffects.AreaScalingValue soSp))\n'
    '                    {\n'
    '                        if (scaleDiag) Console.WriteLine($"SCALEDIAG {soTarget} {soInfo.ModelID}/{soInfo.Class} \'{soInfo.Name}\' native={soSrc} reshaped={soTgt} -> SKIP no-area-value");\n'
    '                        continue;\n'
    '                    }\n'
    '                    string soEvent = (soInfo.Class == EnemyClass.Helper || soInfo.IsBossTarget) ? "scale2" : "scale";\n'
    '                    int soScaleSp = soInfo.IsFixedSource\n'
    '                        ? (soInfo.HasTag("nonunique") ? soSp.FixedScaling : soSp.UniqueFixedScaling)\n'
    '                        : soSp.RegularScaling;\n'
    '                    addCommonFuncInit(soEvent, soTarget, new List<object> { soTarget, soScaleSp });\n'
    '                    if (scaleDiag) Console.WriteLine($"SCALEDIAG {soTarget} {soInfo.ModelID}/{soInfo.Class} \'{soInfo.Name}\' native={soSrc} reshaped={soTgt} sp={soScaleSp} -> APPLIED");\n'
    '                    scaleOnlyCount++;\n'
    '                }\n'
)

def edit():
    tag = "scale-only per-enemy SCALEDIAG"
    text = _read(CS); eol = _eol(text)
    if _norm("bool scaleDiag = System.Environment.GetEnvironmentVariable", eol) in text:
        results.append((tag, "IDEMPOTENT", "diag already present")); return
    a = _norm(_ANCHOR, eol)
    n = text.count(a)
    if n != 1:
        results.append((tag, "FAIL", "anchor count=%d (expected 1)" % n)); return
    _write(CS, text.replace(a, _norm(_REPLACE, eol)))
    ok = _norm("SCALEDIAG", eol) in _read(CS)
    results.append((tag, "PASS" if ok else "FAIL", "written" if ok else "verify failed"))

edit()
print("\n=== patch_baker_scaling_diag summary ===")
worst = 0
for tag, status, detail in results:
    print("  [%-10s] %s  --  %s" % (status, tag, detail))
    if status == "FAIL": worst = 1
print("=== %s ===" % ("ALL OK" if not worst else "FAIL"))
sys.exit(worst)
