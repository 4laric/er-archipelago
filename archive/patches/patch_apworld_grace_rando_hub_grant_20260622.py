#!/usr/bin/env python3
"""
patch_apworld_grace_rando_hub_grant_20260622.py  --  RUN ON WINDOWS (Alaric).

DESIGN CORRECTION on top of patch_apworld_grace_rando_fix_20260622.py.

Desired behavior (Alaric 2026-06-22): the dlc_only HUB (Gravesite Plain) is granted IN FULL at start
(all its graces lit); grace_rando randomizes only the LOCK-GATED regions. The previous fix did the
opposite for the hub (lit only 1 freebie, scattered the other 9 as drops) AND the builder also tried
to randomize Gravesite -- the two fought over the same graces ("bad interaction"): graces ended up
neither granted nor findable.

This patch:
  A. REVERTS the hub start_graces block back to granting ALL Gravesite Plain graces unconditionally
     (undoes the grace_rando hub branch the fix patch added).
  B. Makes the grace_rando builder SKIP the hub region (dlc_only -> "Gravesite Plain") so it never
     rolls a freebie or places grace-token drops there. Other regions randomize normally; base-game
     hubs (which only get a single anchor grace lit, not all) are NOT skipped, so they're unaffected.

Idempotent, CRLF-safe, anchor-verified. Assumes the fix patch is applied (matches the 07:33 regen
behavior). If an anchor is missing it reports FAIL/IDEMPOTENT and changes nothing -- hand back the
current __init__.py and I'll re-anchor.
"""

import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
INIT = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "__init__.py")
results = []

def _read(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def _write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(t)
def _eol(t): return "\r\n" if "\r\n" in t else "\n"
def _norm(s, eol): return s.replace("\r\n", "\n").replace("\n", eol)

# ---------------------------------------------------------------- A. revert hub block
_HUB_BRANCH = (
    "            if getattr(self.options, 'grace_rando', None) and self.options.grace_rando.value:\n"
    "                # grace_rando: hub lights only its single random freebie; the other\n"
    "                # Gravesite graces are TOKEN drops found by exploring (placed in pre_fill).\n"
    "                # Fall back to the first grace as a guaranteed warp anchor if none recorded.\n"
    "                _gr_hub = getattr(self, '_grace_rando_freebie_by_region', {}).get(\"Gravesite Plain\", [])\n"
    "                if not _gr_hub:\n"
    "                    _gr_gp = REGION_GRACE_POINTS.get(\"Gravesite Plain\", [])\n"
    "                    _gr_hub = [int(_gr_gp[0][0])] if _gr_gp else []\n"
    "                start_graces += [int(_f) for _f in _gr_hub]\n"
    "            else:\n"
    '                start_graces += [int(_p[0]) for _p in REGION_GRACE_POINTS.get("Gravesite Plain", [])]\n'
)
_HUB_BARE = (
    '            start_graces += [int(_p[0]) for _p in REGION_GRACE_POINTS.get("Gravesite Plain", [])]\n'
)
def revert_hub():
    tag = "A revert hub block -> grant ALL Gravesite"
    text = _read(INIT); eol = _eol(text)
    marker = _norm("_gr_hub = getattr(self, '_grace_rando_freebie_by_region', {}).get(\"Gravesite Plain\"", eol)
    if marker not in text:
        results.append((tag, "IDEMPOTENT", "hub already grants all Gravesite (no grace_rando branch)")); return
    block = _norm(_HUB_BRANCH, eol)
    n = text.count(block)
    if n != 1:
        results.append((tag, "FAIL", "hub grace_rando block found %d times (expected 1)" % n)); return
    text = text.replace(block, _norm(_HUB_BARE, eol))
    _write(INIT, text)
    ok = marker not in _read(INIT)
    results.append((tag, "PASS" if ok else "FAIL", "reverted to unconditional grant" if ok else "marker remains"))
revert_hub()

# ---------------------------------------------------------------- B. builder skips the hub region
def add_hub_skip():
    tag = "B builder skips hub region (dlc_only Gravesite)"
    text = _read(INIT); eol = _eol(text)
    sentinel = _norm("never randomize it, or the builder and the hub grant fight", eol)
    if sentinel in text:
        results.append((tag, "IDEMPOTENT", "skip already present")); return
    anchor = _norm("            for _gr_region in sorted(REGION_GRACE_POINTS):\n", eol)
    n = text.count(anchor)
    if n == 0:
        results.append((tag, "FAIL", "builder loop anchor not found -- is the fix patch applied?")); return
    if n > 1:
        results.append((tag, "FAIL", "builder loop anchor not unique (%d)" % n)); return
    ins = _norm(
        "                # Hub region (Gravesite Plain in dlc_only) is granted IN FULL at load by the\n"
        "                # start_graces block -- never randomize it, or the builder and the hub grant fight\n"
        "                # over the same graces (the 'bad interaction'). Other regions -- incl. base-game\n"
        "                # hubs that only get a single anchor grace lit -- randomize normally. (Alaric 2026-06-22)\n"
        "                if self.options.dlc_only and _gr_region == \"Gravesite Plain\":\n"
        "                    continue\n", eol)
    text = text.replace(anchor, anchor + ins)
    _write(INIT, text)
    ok = sentinel in _read(INIT)
    results.append((tag, "PASS" if ok else "FAIL", "inserted" if ok else "post-write verify failed"))
add_hub_skip()

print("")
print("=== patch_apworld_grace_rando_hub_grant summary ===")
worst = 0
for tag, status, detail in results:
    print("  [%-10s] %s  --  %s" % (status, tag, detail))
    if status == "FAIL": worst = 1
print("=== %s ===" % ("ALL OK (PASS/IDEMPOTENT)" if not worst else "ONE OR MORE FAIL -- review above"))
sys.exit(worst)
