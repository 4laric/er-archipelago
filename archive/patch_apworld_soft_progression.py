#!/usr/bin/env python3
r"""
patch_apworld_soft_progression.py  (run on Windows from repo root)

New option soft_progression (Toggle, default off): the "wiggle room" knob. Under STRICT
accessibility (full / items -- not minimal), demote progression items that gate NOTHING in logic
to `useful`, freeing fill slack so the MEANINGFUL progression lands on important_locations under
full -- without spending the meaningful-progression budget (nobody wants a Bell Bearing on a boss).

Demote set (all refs=0, verified): upgrade Bell Bearings (smithing/somber/glovewort) + the
Progressive Flask of Wondrous Physick. (Smithing stones are already `filler`; keys like Imbued
Sword Key gate real dungeons and stay progression.)

Why gated on accessibility != minimal: under minimal everything spills anyway, so demotion is
pointless there; the value is making `full` viable while keeping its priority pass binding.

Idempotent; asserts anchors.
"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))
ER   = os.path.join(ROOT, "Archipelago", "worlds", "eldenring")
INIT = os.path.join(ER, "__init__.py")
OPTS = os.path.join(ER, "options.py")

def load(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def save(p, s):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(s)
def nl_of(s): return "\r\n" if "\r\n" in s else "\n"
def once(s, old, new, label, marker):
    if marker in s: return s, False
    n = s.count(old)
    if n != 1: raise SystemExit(f"[FAIL] {label}: expected 1 anchor, found {n}")
    return s.replace(old, new, 1), True

changed = False

# ===== options.py =====
o = load(OPTS); NL = nl_of(o)
cls = NL.join([
"class SoftProgression(Toggle):",
"    \"\"\"Wiggle room for `accessibility: full`. Demote progression that gates NOTHING in logic --",
"    upgrade Bell Bearings (smithing/somber/glovewort) and the Progressive Flask of Wondrous Physick",
"    -- to `useful` when accessibility is strict (full/items). Frees fill slack so the meaningful",
"    progression lands on important_locations under full, without diluting it (no Bell Bearings on",
"    your boss drops). No effect under minimal (everything spills there anyway). See SPEC.\"\"\"",
"    display_name = \"Soft Progression (demote boring progression to useful under full)\"",
"",
"",
])
o, ch = once(o, "class PoolBuilder(Toggle):", cls + "class PoolBuilder(Toggle):",
             "options: insert SoftProgression", "class SoftProgression(Toggle):"); changed |= ch
o, ch = once(o, "    blessing_option: BlessingOption",
             "    blessing_option: BlessingOption" + NL + "    soft_progression: SoftProgression",
             "options: dataclass", "    soft_progression: SoftProgression"); changed |= ch
o, ch = once(o, "        BlessingOption,",
             "        BlessingOption," + NL + "        SoftProgression,",
             "options: option group", "        SoftProgression,"); changed |= ch
save(OPTS, o)

# ===== __init__.py: demotion in generate_early (after merchant-bell block) =====
i = load(INIT); NL = nl_of(i)
mb = (
'        if self.options.merchant_bell_logic.value == 1:' + NL +
'            for _bell in merchant_bell_names(bool(self.options.enable_dlc)):' + NL +
'                item_table[_bell].skip = False' + NL +
'                item_table[_bell].classification = ItemClassification.progression')
blk = NL + NL.join([
"",
"        # Soft progression (wiggle room): under strict accessibility (full/items), demote boring",
"        # progression that gates NOTHING in logic -- upgrade Bell Bearings + Progressive Flask of",
"        # Wondrous Physick -- to useful, so meaningful progression lands on important_locations",
"        # under full without being diluted. (Smithing stones are already filler.) See SPEC.",
"        if (self.options.soft_progression.value",
"                and self.options.accessibility.value != self.options.accessibility.option_minimal):",
"            for _sp in item_table.values():",
"                if _sp.classification == ItemClassification.progression and (",
"                        \"Bell Bearing\" in _sp.name or \"Flask of Wondrous Physick\" in _sp.name):",
"                    _sp.classification = ItemClassification.useful",
])
i, ch = once(i, mb, mb + blk, "init: soft_progression demotion", "Soft progression (wiggle room):"); changed |= ch
save(INIT, i)

print("[OK] soft-progression patch applied." if changed else "[OK] already applied -- no changes.")
