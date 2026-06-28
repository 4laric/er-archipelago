#!/usr/bin/env python3
"""
patch_apworld_grace_rando_no_hub_special_20260622.py  --  RUN ON WINDOWS (Alaric).

DESIGN CHANGE on top of patch_apworld_grace_rando_hub_grant_20260622.py.

Desired behavior (Alaric 2026-06-22): when grace_rando is ON, the dlc_only HUB (Gravesite Plain)
gets NO special treatment -- it is randomized like every other region (one rolled freebie lit at
start, the other graces scattered as in-region TOKEN drops). The hub_grant patch did the opposite
(lit ALL 10 Gravesite graces at start, skipped Gravesite in the builder).

The risk that motivated the old full-grant was "graces neither granted nor findable": Gravesite has
10 grace points, so 9 become drops and need 9 hostable filler checks in-region; any overflow that
finds no check would vanish. This patch closes that hole by making the start_graces block light the
hub's freebie PLUS any overflow grace that was NOT placed as a drop -- so every Gravesite grace is
guaranteed to be either lit at load or findable as a drop, never lost.

This patch:
  A. Builder un-skip: remove the `if dlc_only and region == "Gravesite Plain": continue` so the hub
     randomizes like any region.
  B. Builder bookkeeping: record, per region, the set of grace flags actually PLACED as drops
     (self._grace_rando_placed_by_region) so the start_graces block can tell freebie+overflow apart.
  C. start_graces (dlc_only): under grace_rando, light only the Gravesite graces NOT placed as drops
     (= freebie + overflow). Without grace_rando, keep the full-fast-travel grant (all graces lit).
     71190 (Roundtable) + 76101 (First Step) anchors are untouched in both paths.

Idempotent, CRLF-safe, anchor-verified. Assumes patch_apworld_grace_rando_hub_grant_20260622.py is
applied (the current 'grant ALL Gravesite' + 'builder skips hub' state). If an anchor is missing it
reports FAIL/IDEMPOTENT and changes nothing -- hand back the current __init__.py and I'll re-anchor.
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

# ---------------------------------------------------------------- A. builder un-skip the hub
_SKIP_BLOCK = (
    "                # Hub region (Gravesite Plain in dlc_only) is granted IN FULL at load by the\n"
    "                # start_graces block -- never randomize it, or the builder and the hub grant fight\n"
    "                # over the same graces (the 'bad interaction'). Other regions -- incl. base-game\n"
    "                # hubs that only get a single anchor grace lit -- randomize normally. (Alaric 2026-06-22)\n"
    "                if self.options.dlc_only and _gr_region == \"Gravesite Plain\":\n"
    "                    continue\n"
)
_SKIP_REPLACE = (
    "                # grace_rando: the hub (Gravesite Plain in dlc_only) is randomized like every\n"
    "                # other region -- NO special treatment. Its rolled freebie + any drop-overflow are\n"
    "                # lit at load by the start_graces block (which lights all Gravesite graces NOT\n"
    "                # placed as in-region token drops), so nothing vanishes. (Alaric 2026-06-22)\n"
)
def unskip_hub():
    tag = "A builder un-skip hub (Gravesite randomizes normally)"
    text = _read(INIT); eol = _eol(text)
    done = _norm("grace_rando: the hub (Gravesite Plain in dlc_only) is randomized like every", eol)
    if done in text:
        results.append((tag, "IDEMPOTENT", "hub already un-skipped")); return
    block = _norm(_SKIP_BLOCK, eol)
    n = text.count(block)
    if n != 1:
        results.append((tag, "FAIL", "hub skip block found %d times (expected 1)" % n)); return
    text = text.replace(block, _norm(_SKIP_REPLACE, eol))
    _write(INIT, text)
    ok = done in _read(INIT)
    results.append((tag, "PASS" if ok else "FAIL", "un-skipped" if ok else "post-write verify failed"))
unskip_hub()

# ---------------------------------------------------------------- B1. init placed-by-region dict
_INIT_ANCHOR = (
    "            self._grace_rando_freebie_by_region = {}\n"
    "            self._grace_items_placed = {}\n"
)
_INIT_REPLACE = (
    "            self._grace_rando_freebie_by_region = {}\n"
    "            self._grace_items_placed = {}\n"
    "            self._grace_rando_placed_by_region = {}\n"
)
def add_placed_init():
    tag = "B1 init _grace_rando_placed_by_region"
    text = _read(INIT); eol = _eol(text)
    sentinel = _norm("self._grace_rando_placed_by_region = {}", eol)
    if sentinel in text:
        results.append((tag, "IDEMPOTENT", "init already present")); return
    anchor = _norm(_INIT_ANCHOR, eol)
    n = text.count(anchor)
    if n != 1:
        results.append((tag, "FAIL", "init anchor found %d times (expected 1)" % n)); return
    text = text.replace(anchor, _norm(_INIT_REPLACE, eol))
    _write(INIT, text)
    ok = sentinel in _read(INIT)
    results.append((tag, "PASS" if ok else "FAIL", "inserted" if ok else "post-write verify failed"))
add_placed_init()

# ---------------------------------------------------------------- B2. record placed flags per region
_LOOP_ANCHOR = (
    "                _gr_fi = 0\n"
    "                for _gr_i in range(_gr_k):\n"
    "                    _gr_iname = GRACE_FLAG_TO_ITEM.get(_gr_items[_gr_i])\n"
    "                    if not _gr_iname:\n"
    "                        continue\n"
    "                    _gr_cands[_gr_i].place_locked_item(self.create_item(_gr_iname))\n"
    "                    self.multiworld.itempool.remove(_gr_fillers[_gr_fi])\n"
    "                    _gr_fi += 1\n"
    "                    self._grace_items_placed[_gr_iname] = _gr_items[_gr_i]\n"
    "                if len(_gr_items) > _gr_fi:\n"
    "                    _gr_dropped += len(_gr_items) - _gr_fi\n"
)
_LOOP_REPLACE = (
    "                _gr_fi = 0\n"
    "                _gr_placed_flags = set()\n"
    "                for _gr_i in range(_gr_k):\n"
    "                    _gr_iname = GRACE_FLAG_TO_ITEM.get(_gr_items[_gr_i])\n"
    "                    if not _gr_iname:\n"
    "                        continue\n"
    "                    _gr_cands[_gr_i].place_locked_item(self.create_item(_gr_iname))\n"
    "                    self.multiworld.itempool.remove(_gr_fillers[_gr_fi])\n"
    "                    _gr_fi += 1\n"
    "                    self._grace_items_placed[_gr_iname] = _gr_items[_gr_i]\n"
    "                    _gr_placed_flags.add(_gr_items[_gr_i])\n"
    "                self._grace_rando_placed_by_region[_gr_region] = _gr_placed_flags\n"
    "                if len(_gr_items) > _gr_fi:\n"
    "                    _gr_dropped += len(_gr_items) - _gr_fi\n"
)
def record_placed():
    tag = "B2 record placed flags per region"
    text = _read(INIT); eol = _eol(text)
    sentinel = _norm("self._grace_rando_placed_by_region[_gr_region] = _gr_placed_flags", eol)
    if sentinel in text:
        results.append((tag, "IDEMPOTENT", "placed-flag recording already present")); return
    anchor = _norm(_LOOP_ANCHOR, eol)
    n = text.count(anchor)
    if n != 1:
        results.append((tag, "FAIL", "placement-loop anchor found %d times (expected 1)" % n)); return
    text = text.replace(anchor, _norm(_LOOP_REPLACE, eol))
    _write(INIT, text)
    ok = sentinel in _read(INIT)
    results.append((tag, "PASS" if ok else "FAIL", "inserted" if ok else "post-write verify failed"))
record_placed()

# ---------------------------------------------------------------- C. start_graces: freebie+overflow only
_SG_ANCHOR = (
    "            start_graces = [62080, 62081, 62082, 62083, 62084]\n"
    "            start_graces += [int(_p[0]) for _p in REGION_GRACE_POINTS.get(\"Gravesite Plain\", [])]\n"
    "            start_graces += [71190]"
)
_SG_REPLACE = (
    "            start_graces = [62080, 62081, 62082, 62083, 62084]\n"
    "            # grace_rando (no hub special-treatment): light only the Gravesite graces that did NOT\n"
    "            # become in-region token drops -- i.e. the rolled freebie + any overflow that found no\n"
    "            # filler check. Guarantees every Gravesite grace is either lit here or findable as a\n"
    "            # drop (none vanish). Without grace_rando the hub stays fully fast-travelable.\n"
    "            if getattr(self.options, 'grace_rando', None) and self.options.grace_rando.value:\n"
    "                _gp_placed = getattr(self, '_grace_rando_placed_by_region', {}).get(\"Gravesite Plain\", set())\n"
    "                start_graces += [int(_p[0]) for _p in REGION_GRACE_POINTS.get(\"Gravesite Plain\", [])\n"
    "                                 if _p[0] not in _gp_placed]\n"
    "            else:\n"
    "                start_graces += [int(_p[0]) for _p in REGION_GRACE_POINTS.get(\"Gravesite Plain\", [])]\n"
    "            start_graces += [71190]"
)
def start_graces_freebie_only():
    tag = "C start_graces hub = freebie+overflow under grace_rando"
    text = _read(INIT); eol = _eol(text)
    sentinel = _norm("_gp_placed = getattr(self, '_grace_rando_placed_by_region', {}).get(\"Gravesite Plain\"", eol)
    if sentinel in text:
        results.append((tag, "IDEMPOTENT", "start_graces hub branch already present")); return
    anchor = _norm(_SG_ANCHOR, eol)
    n = text.count(anchor)
    if n != 1:
        results.append((tag, "FAIL", "start_graces anchor found %d times (expected 1)" % n)); return
    text = text.replace(anchor, _norm(_SG_REPLACE, eol))
    _write(INIT, text)
    ok = sentinel in _read(INIT)
    results.append((tag, "PASS" if ok else "FAIL", "inserted" if ok else "post-write verify failed"))
start_graces_freebie_only()

print("")
print("=== patch_apworld_grace_rando_no_hub_special summary ===")
worst = 0
for tag, status, detail in results:
    print("  [%-10s] %s  --  %s" % (status, tag, detail))
    if status == "FAIL": worst = 1
print("=== %s ===" % ("ALL OK (PASS/IDEMPOTENT)" if not worst else "ONE OR MORE FAIL -- review above"))
sys.exit(worst)
