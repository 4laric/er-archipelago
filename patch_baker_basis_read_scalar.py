#!/usr/bin/env python3
r"""patch_baker_basis_read_scalar.py

Fix the sphere-basis read bug in ArchipelagoForm.cs. slotData is a Dictionary<string, object>
populated by the AP client: nested JSON objects come back as Newtonsoft JObject, but SCALAR values
come back as boxed CLR primitives (a JSON int -> boxed `long`), NOT JToken. The two reads of the
top-level scalar key "completionScalingBasis" guard on `... is JToken`, which is FALSE for a boxed
long, so the ternary falls through to `: 0`. Result: CompletionScaleBasis is silently 0 on every
bake -> the sphere path (gated on ==1) never runs -> geographic fallback, even though the zip/server
carry the key and the binary has the bridge.

(regionSphereTargets reads fine because it's a nested object -> JObject -> `is JObject` passes.
mode/floor read fine because they live INSIDE the options JObject where every node is a JToken.)

Fix: accept either a JToken (JValue) or a boxed scalar via Convert.ToInt32. Applied to both the
enemy-rando path and the scale-only path.

Edits SoulsRandomizers/RandomizerCommon/ArchipelagoForm.cs (LF file). Two unique single-line
anchors (no newline dependence). Idempotent (skips if Convert.ToInt32(erSphBasis) present).
Run on Windows from repo root:
    python patch_baker_basis_read_scalar.py
Then rebuild SoulsRandomizers (-Randomizer) and re-bake. Requires `using System;` (already present).
"""
import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
AF = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon", "ArchipelagoForm.cs")
if not os.path.exists(AF):
    sys.exit("ERROR: ArchipelagoForm.cs not found under SoulsRandomizers/RandomizerCommon (run from repo root).")

with open(AF, "rb") as f:
    data = f.read()

if b"Convert.ToInt32(erSphBasis)" in data:
    print("  [skip] basis scalar read already fixed.")
    sys.exit(0)

# enemy-rando path (~L732)
ER_OLD = (b'erRando.CompletionScaleBasis = (slotData.TryGetValue("completionScalingBasis", out var erSphBasis) '
          b'&& erSphBasis is JToken erSphBasisTok) ? erSphBasisTok.Value<int>() : 0;')
ER_NEW = (b'erRando.CompletionScaleBasis = (slotData.TryGetValue("completionScalingBasis", out var erSphBasis) '
          b'&& erSphBasis != null) ? (erSphBasis is JToken erSphBasisTok ? erSphBasisTok.Value<int>() '
          b': Convert.ToInt32(erSphBasis)) : 0;')

# scale-only path (~L770)
SC_OLD = (b'scaleRando.CompletionScaleBasis = (slotData.TryGetValue("completionScalingBasis", out var scSphBasis) '
          b'&& scSphBasis is JToken scSphBasisTok) ? scSphBasisTok.Value<int>() : 0;')
SC_NEW = (b'scaleRando.CompletionScaleBasis = (slotData.TryGetValue("completionScalingBasis", out var scSphBasis) '
          b'&& scSphBasis != null) ? (scSphBasis is JToken scSphBasisTok ? scSphBasisTok.Value<int>() '
          b': Convert.ToInt32(scSphBasis)) : 0;')

for old, label in ((ER_OLD, "enemy-rando basis read"), (SC_OLD, "scale-only basis read")):
    if data.count(old) != 1:
        sys.exit("  [FAIL] %s: anchor x%d (want 1). No write. (Is the sphere bridge applied to ArchipelagoForm.cs?)"
                 % (label, data.count(old)))

data = data.replace(ER_OLD, ER_NEW, 1)
data = data.replace(SC_OLD, SC_NEW, 1)

with open(AF, "wb") as f:
    f.write(data)

print("  [ok]   basis read now accepts a boxed scalar (both enemy-rando + scale-only paths).")
print("DONE -- rebuild SoulsRandomizers (-Randomizer), re-bake the dlc_only basis:sphere seed. "
      "The bake log should now show 'CompletionScaling sphere basis: reshaped N' + the 'UNMAPPED maps' block.")
