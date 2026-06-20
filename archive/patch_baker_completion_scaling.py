#!/usr/bin/env python3
"""
patch_baker_completion_scaling.py -- C# baker layer for Completion-Percent Scaling (idea #2).
SPEC: SPEC-completion-scaling.md. Pairs with patch_apworld_completion_scaling.py.

Reshapes each enemy's EXISTING geographic scaling tier along a curve + floor and writes it into
targetScalingSections, so the randomizer's existing SpEffect path scales each enemy IN PLACE.
flat = vanilla; gentle = easier-for-longer; steep = harder-sooner. No region->enemy bridge: ER's
geographic tier IS the completion order. Reuses the machinery 'scalerandom' already exercises.

EnemyRandomizer.cs (CRLF): add fields CompletionScaleMode/FloorPct; reshape block before the local
getScalingSections(), forcing opt["scale"] on.
ArchipelagoForm.cs (LF): thread the two values from slot_data["options"] onto the ER instance.

CONSTRAINT (v1): only runs when enemy_rando is ON (this method runs only inside the enemy pass).
OPEN (playtest): consider carving hand-tuned great-rune bosses out of the reshape. Not done in v1.
Run on Windows; rebuild SoulsRandomizers. Idempotent. Per-file line endings preserved.
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


ER_CTOR = _crlf("            this.eventConfig = eventConfig;\n        }\n")
ER_FIELDS = _crlf('''
        // Completion-percent scaling (SPEC-completion-scaling.md): set by ArchipelagoForm from
        // slot_data before Run(). Mode 0=off/1=flat/2=gentle/3=steep; FloorPct = min tier % of
        // MaxTier. Reshapes each enemy's existing geographic tier in place. Inert (0) for GUI.
        public int CompletionScaleMode = 0;
        public int CompletionScaleFloorPct = 0;
''')

ER_RESHAPE_ANCHOR = _crlf("            bool getScalingSections(int source, int target, out int sourceSection, out int targetSection, bool ignoreCustom = false)\n")
ER_RESHAPE = _crlf('''\
            // Completion-percent scaling (SPEC-completion-scaling.md): reshape each enemy's native
            // tier along a curve + floor (flat = vanilla). Writes targetScalingSections so the
            // existing SpEffect path scales the enemy IN PLACE. Forces opt["scale"] on.
            if (game.EldenRing && ann.ScalingSections != null && CompletionScaleMode > 0)
            {
                opt["scale"] = true;
                if (targetScalingSections == ann.ScalingSections)
                {
                    targetScalingSections = new Dictionary<int, int>(ann.ScalingSections);
                }
                int compMaxTier = scalingSpEffects.MaxTier;
                double compFloor = Math.Max(0, Math.Min(50, CompletionScaleFloorPct)) / 100.0;
                double compCurve(double d) =>
                    CompletionScaleMode == 2 ? Math.Pow(d, 1.6)
                    : CompletionScaleMode == 3 ? Math.Pow(d, 0.55)
                    : d;
                foreach (KeyValuePair<int, int> compEntry in ann.ScalingSections)
                {
                    int compTarget = compEntry.Key;
                    int compSection = compEntry.Value;
                    if (compSection <= 0) continue;
                    double compD = compMaxTier > 1 ? (compSection - 1.0) / (compMaxTier - 1.0) : 0.0;
                    double compT = compFloor + compCurve(compD) * (1.0 - compFloor);
                    int compNew = (int)Math.Round(compT * compMaxTier);
                    if (compNew < 1) compNew = 1;
                    if (compNew > compMaxTier) compNew = compMaxTier;
                    targetScalingSections[compTarget] = compNew;
                }
            }
''')

AF_ANCHOR = b"new EnemyRandomizer(game, enemyEvents, enemyEventConfig).Run(opt, preset);"
AF_REPL = _lf(
    'var erRando = new EnemyRandomizer(game, enemyEvents, enemyEventConfig);\n'
    '                    // Completion-percent scaling (SPEC-completion-scaling.md): mode + floor\n'
    '                    // from slot_data (read like dungeon_sweep). 0 => off.\n'
    '                    erRando.CompletionScaleMode = (slotData["options"] as JObject)?["completion_scaling"]?.Value<int>() ?? 0;\n'
    '                    erRando.CompletionScaleFloorPct = (slotData["options"] as JObject)?["completion_scaling_floor"]?.Value<int>() ?? 0;\n'
    '                    erRando.Run(opt, preset);'
)


def patch_er(data):
    if b"CompletionScaleMode" in data:
        print("[skip] EnemyRandomizer.cs already patched.")
        return data, False
    data = _ins_after(data, ER_CTOR, ER_FIELDS, "ER fields")
    data = _ins_before(data, ER_RESHAPE_ANCHOR, ER_RESHAPE, "ER reshape")
    return data, True


def patch_af(data):
    if b"erRando.CompletionScaleMode" in data:
        print("[skip] ArchipelagoForm.cs already patched.")
        return data, False
    data = _replace(data, AF_ANCHOR, AF_REPL, "AF Run wiring")
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
        print("[ok] patched EnemyRandomizer.cs")
    if afc:
        _write(AF, af2)
        print("[ok] patched ArchipelagoForm.cs")
    if not (erc or afc):
        print("[done] nothing to do.")
    else:
        print("[done] baker layer applied. Rebuild SoulsRandomizers, bake-test with enemy_rando + steep.")


if __name__ == "__main__":
    main()
