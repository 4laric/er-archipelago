#!/usr/bin/env python3
"""
patch_apworld_grace_rando_fix_20260622.py  --  RUN ON WINDOWS (Alaric).

CORRECTIVE patch for grace_rando. The original patch_apworld_grace_rando_20260621.py
half-applied: its items (GRACE_FLAG_TO_ITEM), the fill_slot_data freebie READ site, and the
"graceItems" slot_data EMIT all landed -- but its step C2 (the freebie BUILDER) silently
no-op'd. Cause: C2's sentinel was `def pre_fill(self) -> None:`, which ALREADY exists in
__init__.py (the main pre_fill at #MARK: Pre-fill), so the patch reported that step IDEMPOTENT
and never inserted the builder. Result: with grace_rando ON, `_grace_rando_freebie_by_region`
and `_grace_items_placed` are never populated -> every region lights 0 graces and 0 grace-token
checks get placed (worse than OFF).

This patch:
  1. (builder) Inlines the grace_rando freebie+drop builder at the TOP of the EXISTING pre_fill
     (instead of colliding with a second def). Runs on every config because the chain branches
     lower in pre_fill `return` early. Populates the same attributes the existing read site
     (fill_slot_data, ~L5128) and emit ("graceItems", ~L5558) already consume.
  2. (hub) Makes the dlc_only start_graces block grace_rando-aware: the Gravesite hub lights only
     its single random freebie at load (the other Gravesite graces become explore-to-find token
     drops, placed by the builder) instead of all of them. Falls back to the first Gravesite grace
     as a guaranteed warp anchor if no freebie was recorded.

Interaction note: with grace_rando AND a chain (dlc_only_chain / num_regions_chain), a grace drop
could land on a boss-drop chain host; the chain degrades gracefully (warns + precollects that
lock) -- no crash. Plain region_lock / dlc_only is unaffected.

All edits idempotent, CRLF-safe, anchor-verified (EOL-agnostic). Re-run reports IDEMPOTENT.
See SPEC-grace-rando.md.
"""

import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PKG  = os.path.join(ROOT, "Archipelago", "worlds", "eldenring")
INIT = os.path.join(PKG, "__init__.py")

results = []  # (tag, status, detail)

def _read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()

def _write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)

def _eol(text):
    return "\r\n" if "\r\n" in text else "\n"

def _norm(s, eol):
    return s.replace("\r\n", "\n").replace("\n", eol)

def edit(tag, path, anchor, insert_after=None, replace_with=None, sentinel=None, before=False):
    try:
        text = _read(path)
    except FileNotFoundError:
        results.append((tag, "FAIL", "file not found: %s" % path)); return
    eol = _eol(text)
    if sentinel and _norm(sentinel, eol) in text:
        results.append((tag, "IDEMPOTENT", "sentinel present")); return
    a = _norm(anchor, eol)
    n = text.count(a)
    if n == 0:
        results.append((tag, "FAIL", "anchor not found")); return
    if n > 1:
        results.append((tag, "FAIL", "anchor not unique (%d matches)" % n)); return
    if replace_with is not None:
        new = text.replace(a, _norm(replace_with, eol))
    else:
        ins = _norm(insert_after, eol)
        new = text.replace(a, (ins + a) if before else (a + ins))
    _write(path, new)
    chk = _read(path)
    ok = (_norm(sentinel, eol) in chk) if sentinel else True
    results.append((tag, "PASS" if ok else "FAIL", "written" if ok else "post-write verify failed"))

# ---------------------------------------------------------------- 1. builder (top of pre_fill)
_BUILDER = (
    "        # grace_rando (SPEC-grace-rando.md): receiving a region's lock lights ONE random\n"
    "        # grace (warp-in); every OTHER (non-boss/border) grace becomes a TOKEN item locked at\n"
    "        # a filler check INSIDE that same region. Count-neutral (one pool filler removed per\n"
    "        # placement). Built at the TOP of pre_fill so it runs on every config (the chain\n"
    "        # branches below return early). The hub's single freebie is lit at load by the\n"
    "        # start_graces block. Inert unless grace_rando + region gating.\n"
    "        # (patch_apworld_grace_rando_fix_20260622.py)\n"
    "        if (getattr(self.options, 'grace_rando', None) and self.options.grace_rando.value\n"
    "                and self.options.world_logic < 3):\n"
    "            _gr_SKIP = frozenset({71240, 71401, 76415, 76422, 76508, 76509, 76852, 76853,\n"
    "                                  76930, 76931, 73204, 73207, 76209, 76229, 76301, 76350,\n"
    "                                  76351, 76356})\n"
    "            self._grace_rando_freebie_by_region = {}\n"
    "            self._grace_items_placed = {}\n"
    "            _gr_dropped = 0\n"
    "            for _gr_region in sorted(REGION_GRACE_POINTS):\n"
    "                _gr_flags = [p[0] for p in REGION_GRACE_POINTS[_gr_region]\n"
    "                             if p[0] not in _gr_SKIP]\n"
    "                if not _gr_flags:\n"
    "                    continue\n"
    "                _gr_free = self.random.choice(_gr_flags)\n"
    "                self._grace_rando_freebie_by_region[_gr_region] = [_gr_free]\n"
    "                _gr_items = [f for f in _gr_flags if f != _gr_free]\n"
    "                if not _gr_items:\n"
    "                    continue\n"
    "                try:\n"
    "                    _gr_robj = self.multiworld.get_region(_gr_region, self.player)\n"
    "                except KeyError:\n"
    "                    _gr_dropped += len(_gr_items)\n"
    "                    continue\n"
    "                _gr_cands = [l for l in _gr_robj.locations\n"
    "                             if l.address is not None and l.item is None\n"
    "                             and l.progress_type != LocationProgressType.PRIORITY\n"
    "                             and l.name not in getattr(self, 'all_priority_locations', set())]\n"
    "                self.random.shuffle(_gr_cands)\n"
    "                _gr_fillers = [it for it in self.multiworld.itempool\n"
    "                               if it.classification == ItemClassification.filler]\n"
    "                _gr_k = min(len(_gr_items), len(_gr_cands), len(_gr_fillers))\n"
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
    "            if self._grace_items_placed or _gr_dropped:\n"
    "                warning(f'{self.player_name}: grace_rando placed '\n"
    "                        f'{len(self._grace_items_placed)} grace drop(s); {_gr_dropped} '\n"
    "                        f'dropped for lack of room.')\n"
)
edit(
    "1 grace_rando builder (top of pre_fill)", INIT,
    anchor="    def pre_fill(self) -> None: #MARK: Pre-fill\n",
    sentinel="self._grace_rando_freebie_by_region = {}",
    insert_after=_BUILDER,
)

# ---------------------------------------------------------------- 2. hub start_graces branch
edit(
    "2 hub start_graces grace_rando branch", INIT,
    anchor='            start_graces += [int(_p[0]) for _p in REGION_GRACE_POINTS.get("Gravesite Plain", [])]\n',
    sentinel="_gr_hub = getattr(self, '_grace_rando_freebie_by_region'",
    replace_with=(
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
    ),
)

print("")
print("=== patch_apworld_grace_rando_fix summary ===")
worst = 0
for tag, status, detail in results:
    print("  [%-10s] %s  --  %s" % (status, tag, detail))
    if status == "FAIL":
        worst = 1
print("=== %s ===" % ("ALL OK (PASS/IDEMPOTENT)" if not worst else "ONE OR MORE FAIL -- review above"))
sys.exit(worst)
