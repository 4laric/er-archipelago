#!/usr/bin/env python3
"""
patch_baker_dlc_boss_tiers_20260622.py  --  RUN ON WINDOWS, rebuild SoulsRandomizers (Release) + rebake.

Gives DLC bosses a NATIVE scaling tier so completion_scaling scales them toward the region from the
right direction. Unique DLC bosses carry no area scaling speffect -> they hit the tier-1 fallback in
ScalingEffects.InitializeEldenScaling -> under sphere basis the curve scales them UP from tier 1 to the
region target (Rellana: 1->18 in Castle Ensis), multiplying already boss-level base stats = far too
strong. Regular DLC mobs (real speffects, native ~21-35) correctly scale DOWN, so the bosses stand out.

FIX: a MODEL-keyed table (covers every instance/phase) applied right after manualEntityTiers, giving
each boss its approximate vanilla DLC tier (21-35 band). Now native(~23) -> region target(18) scales
DOWN. exclude:unkillable (rando) is untouched -- this only fixes scaling classification.

TIER VALUES ARE A TUNABLE FIRST PASS. Validate with the scaling diag (patch_baker_scaling_diag +
ER_DUMP_SCALING=1): the per-region regular-enemy native tiers are the right reference. Bump a boss up
if it still feels soft, down if too strong. Not included (by design): c5170 furnace golems (separate
patch / gimmick), c0000 bosses e.g. Knight of the Solitary Gaol (classify via map inference already),
c6xxx (uncertain provenance), and all BASE-game bosses (also exclude:unkillable -- add later if you do
non-dlc_only runs).

Idempotent, CRLF-safe, anchor-verified.
"""
import os, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
CS = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon", "ScalingEffects.cs")
results = []
def _read(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def _write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(t)
def _eol(t): return "\r\n" if "\r\n" in t else "\n"
def _norm(s, eol): return s.replace("\r\n", "\n").replace("\n", eol)
def edit(tag, anchor, replace_with, sentinel):
    text = _read(CS); eol = _eol(text)
    if _norm(sentinel, eol) in text:
        results.append((tag, "IDEMPOTENT", "present")); return
    a = _norm(anchor, eol); n = text.count(a)
    if n != 1:
        results.append((tag, "FAIL", "anchor count=%d" % n)); return
    _write(CS, text.replace(a, _norm(replace_with, eol)))
    results.append((tag, "PASS" if _norm(sentinel, eol) in _read(CS) else "FAIL", "written"))

# A. apply loop (model-keyed) just before `return ret;`
edit("A boss-tier apply loop",
    anchor="            }\n\n            return ret;\n        }\n",
    sentinel="bossModelTiers.TryGetValue",
    replace_with=(
        "            }\n"
        "            // DLC boss native tiers (Alaric 2026-06-22): override classification by MODEL so\n"
        "            // every instance/phase is covered. Applied last -> wins over the tier-1 fallback\n"
        "            // and speffect passes, so the completion-scaling curve scales the boss toward the\n"
        "            // region instead of UP from 1. See bossModelTiers.\n"
        "            foreach (KeyValuePair<int, EnemyData> bossEntry in defaultData)\n"
        "            {\n"
        "                if (bossModelTiers.TryGetValue(bossEntry.Value.Model, out int bossTier))\n"
        "                {\n"
        "                    ret[bossEntry.Key] = bossTier;\n"
        "                }\n"
        "            }\n"
        "\n"
        "            return ret;\n"
        "        }\n"
    ))

# B. the bossModelTiers dict, before manualEntityTiers
edit("B bossModelTiers dict",
    anchor="        private static readonly Dictionary<int, int> manualEntityTiers = new Dictionary<int, int>\n",
    sentinel="Dictionary<string, int> bossModelTiers",
    replace_with=(
        "        // DLC boss native tiers (model -> approx vanilla DLC tier, 21-35 band). Without this they\n"
        "        // fall to native tier 1 and completion_scaling scales them UP instead of DOWN. TUNABLE\n"
        "        // first pass -- validate per-region regular-enemy tiers with ER_DUMP_SCALING. (Alaric)\n"
        "        private static readonly Dictionary<string, int> bossModelTiers = new Dictionary<string, int>\n"
        "        {\n"
        '            ["c5210"] = 22,  // Divine Beast Dancing Lion (Belurat)\n'
        '            ["c5300"] = 23,  // Rellana, Twin Moon Knight (Castle Ensis)\n'
        '            ["c5010"] = 24,  // Golden Hippopotamus (Scadu Altus)\n'
        '            ["c5000"] = 25,  // Commander Gaius (Scadu Altus)\n'
        '            ["c5200"] = 25,  // Metyr, Mother of Fingers (Cathedral of Manus Metyr)\n'
        '            ["c5020"] = 25,  // Putrescent Knight (Stone Coffin Fissure)\n'
        '            ["c5030"] = 27,  // Romina, Saint of the Bud (Ancient Ruins of Rauh)\n'
        '            ["c5130"] = 27,  // Messmer the Impaler (Shadow Keep)\n'
        '            ["c5051"] = 27,  // Midra, Lord of Frenzied Flame (Abyssal Woods)\n'
        '            ["c5230"] = 28,  // Scadutree Avatar (Scaduview)\n'
        '            ["c5120"] = 30,  // Bayle the Dread (Jagged Peak)\n'
        '            ["c5220"] = 34,  // Radahn, Consort of Miquella (Enir-Ilim, final)\n'
        "            // minibosses / field bosses (lower band)\n"
        '            ["c5081"] = 21,  // Chief Bloodfiend\n'
        '            ["c5040"] = 22,  // Curseblade Labirith\n'
        '            ["c5070"] = 22,  // Twin Axe Death Knight\n'
        '            ["c5810"] = 21,  // Demi-Human Swordmaster Onze\n'
        '            ["c5820"] = 23,  // Rugalea the Great Red Bear\n'
        '            ["c5840"] = 23,  // Black Knight Garrew\n'
        '            ["c5730"] = 21,  // Demi-Human Queen Marigga\n'
        '            ["c5312"] = 24,  // Jori, Elder Inquisitor\n'
        '            ["c5580"] = 24,  // Jagged Peak Drake\n'
        '            ["c5370"] = 26,  // Ancient Dragon Senessax\n'
        '            ["c5860"] = 25,  // Ghostflame Dragon\n'
        "        };\n"
        "\n"
        "        private static readonly Dictionary<int, int> manualEntityTiers = new Dictionary<int, int>\n"
    ))

print("\n=== patch_baker_dlc_boss_tiers summary ===")
worst = 0
for t, s, d in results:
    print("  [%-10s] %s -- %s" % (s, t, d))
    if s == "FAIL": worst = 1
print("=== %s ===" % ("ALL OK" if not worst else "FAIL"))
sys.exit(worst)
