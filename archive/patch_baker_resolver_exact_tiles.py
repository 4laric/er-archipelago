#!/usr/bin/env python3
r"""patch_baker_resolver_exact_tiles.py

In-place REFRESH of CompApRegionForMap in EnemyRandomizer.cs for the sphere-scaling bridge
(Track C, SPEC-num-regions-chain.md). The original bridge (patch_baker_sphere_scaling_bridge.py)
shipped a COARSE m60 XX/YY band guess + a couple wrong AP region names; this swaps that for an
EXACT m60 tile -> AP region switch derived from grace_flags.tsv x REGION_GRACE_POINTS, and fixes
the legacy names to match the apworld region_order.

Why a separate patch: the bridge is already applied to EnemyRandomizer.cs (its idempotency marker
trips), so re-running the (now-updated) bridge is a no-op. This migrates an already-applied .cs.
A FRESH bridge apply (on a reverted .cs) already emits the exact switch -- this patch is only for
the already-patched tree. Idempotent: skips if the exact switch (case "50_36":) is already present.

Fixes: bands -> exact tiles for Weeping/Liurnia/Caelid/Dragonbarrow/Altus/Mt.Gelmir (unmatched m60
-> null = v1 geographic fallback; Limgrave/Capital Outskirts have no grace tiles so they ride v1);
"Academy of Raya Lucaria" -> "Raya Lucaria Academy"; "Nokron, Eternal City" -> "...Start".

Run on Windows from repo root:
    python patch_baker_resolver_exact_tiles.py
CRLF-preserving (the file is CRLF); exact-match byte replace; idempotent.
"""
import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ER = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon", "EnemyRandomizer.cs")
if not os.path.exists(ER):
    sys.exit("ERROR: EnemyRandomizer.cs not found under SoulsRandomizers/RandomizerCommon (run from repo root).")

OLD_BAND = '                        if (compTy >= 51) return "Consecrated Snowfield";\r\n                        if (compTy >= 47) return "Mountaintops of the Giants";\r\n                        if (compTy >= 43) return "Altus Plateau";\r\n                        if (compTx >= 47) return "Caelid";\r\n                        if (compTy >= 38) return "Liurnia of the Lakes";\r\n                        if (compTy <= 35) return "Weeping Peninsula";\r\n                        return "Limgrave";\r\n'
NEW_SWITCH = '                        // Exact m60 tile -> AP region (grace_flags.tsv x REGION_GRACE_POINTS; bands cannot separate\r\n                        // Liurnia/Altus/Mt.Gelmir/Caelid -- they interleave in YY). Unmatched -> null (v1 fallback).\r\n                        string compTile = compTx.ToString("D2") + "_" + compTy.ToString("D2");\r\n                        switch (compTile)\r\n                        {\r\n                            case "41_32":\r\n                            case "41_33":\r\n                            case "42_33":\r\n                            case "43_31":\r\n                            case "43_34":\r\n                            case "44_33":\r\n                            case "44_34":\r\n                            case "45_33":\r\n                                return "Weeping Peninsula";\r\n                            case "33_44":\r\n                            case "33_46":\r\n                            case "33_47":\r\n                            case "34_43":\r\n                            case "34_44":\r\n                            case "34_46":\r\n                            case "34_47":\r\n                            case "34_48":\r\n                            case "34_49":\r\n                            case "35_43":\r\n                            case "35_47":\r\n                            case "35_50":\r\n                            case "36_41":\r\n                            case "36_43":\r\n                            case "36_45":\r\n                            case "37_42":\r\n                            case "37_44":\r\n                            case "37_46":\r\n                            case "37_47":\r\n                            case "37_48":\r\n                            case "38_40":\r\n                            case "38_41":\r\n                            case "38_43":\r\n                            case "38_45":\r\n                            case "38_46":\r\n                            case "38_47":\r\n                            case "38_48":\r\n                            case "38_50":\r\n                            case "39_40":\r\n                            case "39_41":\r\n                            case "39_42":\r\n                            case "39_44":\r\n                                return "Liurnia of The Lakes";\r\n                            case "46_39":\r\n                            case "46_40":\r\n                            case "47_39":\r\n                            case "47_40":\r\n                            case "48_36":\r\n                            case "48_37":\r\n                            case "48_38":\r\n                            case "48_39":\r\n                            case "48_40":\r\n                            case "49_37":\r\n                            case "49_38":\r\n                            case "49_39":\r\n                            case "50_38":\r\n                                return "Caelid";\r\n                            case "50_36":\r\n                            case "51_36":\r\n                                return "Dragonbarrow";\r\n                            case "36_52":\r\n                            case "37_51":\r\n                            case "38_51":\r\n                            case "39_51":\r\n                            case "39_53":\r\n                            case "39_54":\r\n                            case "40_52":\r\n                            case "40_53":\r\n                            case "40_54":\r\n                            case "41_52":\r\n                            case "41_54":\r\n                            case "42_55":\r\n                                return "Altus Plateau";\r\n                            case "35_53":\r\n                            case "36_54":\r\n                            case "37_52":\r\n                            case "37_53":\r\n                            case "38_53":\r\n                            case "38_54":\r\n                                return "Mt. Gelmir";\r\n                            default: return null;\r\n                        }\r\n'
NAME_FIXES = [
    ('return "Academy of Raya Lucaria";', 'return "Raya Lucaria Academy";'),
    ('return "Nokron, Eternal City";',    'return "Nokron, Eternal City Start";'),
]

with open(ER, "rb") as f:
    b = f.read()
txt = b.decode("utf-8")

if 'case "50_36":' in txt:
    print("  [skip] EnemyRandomizer.cs resolver already has the exact-tile switch.")
    sys.exit(0)

if txt.count(OLD_BAND) != 1:
    sys.exit("  [FAIL] band block found %d times (expected 1); not modified. "
             "Is the original bridge applied unmodified?" % txt.count(OLD_BAND))
txt = txt.replace(OLD_BAND, NEW_SWITCH, 1)

for old, new in NAME_FIXES:
    if txt.count(old) != 1:
        sys.exit("  [FAIL] name-fix anchor %r found %d times (expected 1); not modified." % (old, txt.count(old)))
    txt = txt.replace(old, new, 1)

with open(ER, "wb") as f:
    f.write(txt.encode("utf-8"))
print("  [ok]   resolver refreshed: exact m60 tile switch + Dragonbarrow + name fixes.")
print("DONE -- rebuild SoulsRandomizers, then enemy-OFF bake.")
