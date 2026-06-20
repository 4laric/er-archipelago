#!/usr/bin/env python3
"""
patch_baker_sweep_log.py -- log the boss/grace -> check sweep mappings succinctly during the bake.

WHY: the C# boss-attribution writes sweep_flags into apconfig.json (raw {flag:[locIds]}), and emits a
one-line count summary (ap_sweep_diag). Alaric wants the actual MAPPINGS readable -- "<Boss> (flag): N
checks" -- so a bake can be eyeballed (exactly what we had to reconstruct by hand). The boss NAMES exist
inside BossAttribution.Compute (roster Boss.Name/Region) but aren't surfaced.

WHAT (2 LF C# files):
 1. BossAttribution.cs -- Compute gains `out Dictionary<int,string> flagNames` (flag -> "Boss [Region]",
    or "Grace <flag>"), built from the roster + graces just before `return sweep;`.
 2. ArchipelagoForm.cs -- pass the new out var at the call site, then append a readable per-flag
    breakdown (sorted by check count) to the existing ap_sweep_diag file.

Result in ap_sweep_diag, after the existing summary line:
    sweep mappings (boss/grace -> checks):
      Morgott, the Omen King [Leyndell, Royal Capital] (flag 11000800): 143 checks
      Full-Grown Fallingstar Beast [Mt. Gelmir] (flag 1037530800): 19 checks
      ...

Idempotent (sentinel). Byte-level, LF preserved. Run on Windows, then rebuild SoulsRandomizers (Release)
and re-bake. No apworld/client change.
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
BA = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon", "BossAttribution.cs")
AF = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon", "ArchipelagoForm.cs")

SENTINEL = b"sweep mappings (boss/grace -> checks)"

BA_EDITS = [
    (
        "Compute signature: add out flagNames",
        b"            Dictionary<int, Vector3> entityPos, out Stats stats)\n",
        b"            Dictionary<int, Vector3> entityPos, out Stats stats, out Dictionary<int, string> flagNames)\n",
    ),
    (
        "build flagNames before return",
        b"            return sweep;\n",
        b"            // Succinct name per sweep flag (boss name [region] / grace) for the bake log (ap_sweep_diag).\n"
        b"            flagNames = new Dictionary<int, string>();\n"
        b"            foreach (var rb in roster)\n"
        b"                if (rb.Flag != 0 && !flagNames.ContainsKey(rb.Flag))\n"
        b"                    flagNames[rb.Flag] = rb.Name + (string.IsNullOrEmpty(rb.Region) ? \"\" : \" [\" + rb.Region + \"]\");\n"
        b"            foreach (var gp in graces)\n"
        b"                if (!flagNames.ContainsKey(gp.Flag))\n"
        b"                    flagNames[gp.Flag] = \"Grace \" + gp.Flag;\n"
        b"            return sweep;\n",
    ),
]

AF_EDITS = [
    (
        "call site: pass out sweepFlagNames",
        b"                            apEntityPos, out var sweepStats);\n",
        b"                            apEntityPos, out var sweepStats, out var sweepFlagNames);\n",
    ),
    (
        "append readable mapping to ap_sweep_diag",
        b'                            File.WriteAllText(Util.ApDiagPath("ap_sweep_diag"),\n'
        b'                                sweepLine + "\\ngraces collected: " + apSweepGraces.Count\n'
        b'                                + "\\nentity positions (drop-check): " + apEntityPos.Count + "\\n");\n',
        b'                            // Succinct readable mapping: each sweep flag -> boss/grace name + check count.\n'
        b'                            string sweepBreakdown = string.Join("\\n", sweep\n'
        b'                                .OrderByDescending(kv => kv.Value.Count)\n'
        b'                                .Select(kv => "  " + (sweepFlagNames.TryGetValue(kv.Key, out var _nm) ? _nm : "?")\n'
        b'                                    + " (flag " + kv.Key + "): " + kv.Value.Count + " checks"));\n'
        b'                            File.WriteAllText(Util.ApDiagPath("ap_sweep_diag"),\n'
        b'                                sweepLine + "\\ngraces collected: " + apSweepGraces.Count\n'
        b'                                + "\\nentity positions (drop-check): " + apEntityPos.Count\n'
        b'                                + "\\n\\nsweep mappings (boss/grace -> checks):\\n" + sweepBreakdown + "\\n");\n',
    ),
]


def patch_file(path, edits):
    if not os.path.isfile(path):
        sys.exit("ERROR: not found: %s" % path)
    with open(path, "rb") as f:
        data = f.read()
    if SENTINEL in data:
        print("  [skip] %s already patched." % os.path.basename(path))
        return
    for desc, old, new in edits:
        n = data.count(old)
        if n != 1:
            sys.exit("ERROR: %s anchor '%s' found %d (want 1). Aborting; no write."
                     % (os.path.basename(path), desc, n))
        data = data.replace(old, new, 1)
        print("  [ok] %s" % desc)
    if b"\r\n" in data:
        sys.exit("ERROR: %s gained CRLF; aborting." % os.path.basename(path))
    with open(path, "wb") as f:
        f.write(data)


def main():
    patch_file(BA, BA_EDITS)
    patch_file(AF, AF_EDITS)
    # verify
    for p in (BA, AF):
        with open(p, "rb") as f:
            chk = f.read()
    assert b"out Dictionary<int, string> flagNames" in open(BA, "rb").read(), "VERIFY FAILED BA sig"
    assert SENTINEL in open(AF, "rb").read(), "VERIFY FAILED AF mapping"
    assert b"out var sweepFlagNames" in open(AF, "rb").read(), "VERIFY FAILED AF call"
    print("Patched + verified. Next: rebuild SoulsRandomizers (Release) + re-bake. No apworld/client change.")


if __name__ == "__main__":
    main()
