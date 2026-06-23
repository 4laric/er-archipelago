#!/usr/bin/env python3
"""
patch_apworld_grace_rando_20260621.py  --  RUN ON WINDOWS (Alaric).

Grace Rando (region gating only). Inverts the region-fusion grace bundle (TODO #13):
  - Receiving a region's lock item lights ONE RANDOM grace in that region (the warp-in point)
    instead of all/graces_per_region.
  - Every OTHER (non-boss/non-border) grace in the region becomes an individual AP TOKEN item,
    dropped (locked) at a filler check INSIDE that same region. Count-neutral: one pool filler is
    removed per placed grace, so the pool never grows (no FillError). Graces beyond available
    in-region filler are DROPPED with a warning.
  - Client (separate patch_client_grace_items_*.py) sets that one warp flag on receipt, by item name.

See SPEC-grace-rando.md. All edits idempotent, CRLF-safe, anchor-verified (EOL-agnostic); a re-run
reports IDEMPOTENT and changes nothing.
"""

import os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PKG  = os.path.join(ROOT, "Archipelago", "worlds", "eldenring")
OPTIONS = os.path.join(PKG, "options.py")
ITEMS   = os.path.join(PKG, "items.py")
INIT    = os.path.join(PKG, "__init__.py")

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

# ---------------------------------------------------------------- A. options.py
edit(
    "A1 options.GraceRando class", OPTIONS,
    anchor="class RegionAccessLogic(Choice):",
    before=True,
    sentinel="class GraceRando(Toggle):",
    insert_after=(
        'class GraceRando(Toggle):\n'
        '    """Grace rando (region gating only). Instead of a region lock lighting ALL of that\n'
        "    region's Sites of Grace, receiving the lock lights ONE RANDOM grace (your warp-in point)\n"
        '    and every OTHER grace in the region becomes an individual item dropped at a check INSIDE\n'
        '    that same region -- found by exploring. Count-neutral (swaps for filler), so it never\n'
        '    grows the pool. No effect unless world_logic is a region-gating mode."""\n'
        '    display_name = "Grace Rando"\n'
        '\n'
    ),
)
edit(
    "A2 options dataclass field", OPTIONS,
    anchor="    graces_per_region: GracesPerRegion\n",
    sentinel="    grace_rando: GraceRando\n",
    insert_after="    grace_rando: GraceRando\n",
)

# ---------------------------------------------------------------- B. items.py
edit(
    "B1 ERItemData.grace field", ITEMS,
    anchor='    map: bool = False\n    """Maps"""\n',
    sentinel="    grace: bool = False",
    insert_after=(
        '\n'
        '    grace: bool = False\n'
        '    """grace_rando: AP token grace item (no er_code; client sets one warp flag by item name)"""\n'
    ),
)
edit(
    "B2 grace token items", ITEMS,
    anchor="_all_items = _vanilla_items + _dlc_items\n",
    sentinel="GRACE_FLAG_TO_ITEM",
    replace_with=(
        "# grace_rando: one AP TOKEN item per Site-of-Grace warp flag. er_code=None -> recognized by\n"
        "# NAME client-side (like region locks); sets that one warp flag on receipt. Generated\n"
        "# deterministically (sorted) so item ids are stable across the multiworld; the world only\n"
        "# PLACES a subset (defining unused tokens is harmless). Names use grace_data.GRACE_PLACE_NAMES\n"
        "# when available (baked from the PlaceName FMG), else a unique flag-tagged placeholder.\n"
        "from .grace_data import REGION_GRACE_POINTS as _GR_RGP\n"
        "try:\n"
        "    from .grace_data import GRACE_PLACE_NAMES as _GR_PLACE_NAMES\n"
        "except ImportError:\n"
        "    _GR_PLACE_NAMES = {}\n"
        "_grace_items = []\n"
        "GRACE_FLAG_TO_ITEM = {}\n"
        "_gr_seen = set()\n"
        "for _gr_region in sorted(_GR_RGP):\n"
        "    for _gr_pt in _GR_RGP[_gr_region]:\n"
        "        _gr_flag = _gr_pt[0]\n"
        "        if _gr_flag in _gr_seen:\n"
        "            continue\n"
        "        _gr_seen.add(_gr_flag)\n"
        "        _gr_pretty = _GR_PLACE_NAMES.get(_gr_flag)\n"
        "        _gr_name = (f'Grace: {_gr_pretty} ({_gr_region})' if _gr_pretty\n"
        "                    else f'Grace: {_gr_region} #{_gr_flag}')\n"
        "        if _gr_name in GRACE_FLAG_TO_ITEM.values():\n"
        "            _gr_name = f'{_gr_name} #{_gr_flag}'\n"
        "        _grace_items.append(ERItemData(_gr_name, None, ERItemCategory.GOODS,\n"
        "                                       classification=ItemClassification.filler,\n"
        "                                       inject=True, grace=True))\n"
        "        GRACE_FLAG_TO_ITEM[_gr_flag] = _gr_name\n"
        "\n"
        "_all_items = _vanilla_items + _dlc_items + _grace_items\n"
    ),
)

# ---------------------------------------------------------------- C. __init__.py
edit(
    "C1 import GRACE_FLAG_TO_ITEM", INIT,
    anchor="item_descriptions, item_table, item_table_vanilla, item_name_groups",
    sentinel="GRACE_FLAG_TO_ITEM",
    insert_after=", GRACE_FLAG_TO_ITEM",
)

_PREFILL = (
    "    def pre_fill(self) -> None:\n"
    "        # grace_rando: lock grants ONE random grace per region; every other (non-boss/border)\n"
    "        # grace becomes a TOKEN item locked at a filler check INSIDE that same region. Count-\n"
    "        # neutral (one pool filler removed per placement). Inert unless grace_rando + region\n"
    "        # gating. See SPEC-grace-rando.md.\n"
    "        if not (getattr(self.options, 'grace_rando', None) and self.options.grace_rando.value\n"
    "                and self.options.world_logic < 3):\n"
    "            return\n"
    "        from .grace_data import REGION_GRACE_POINTS as _RGP\n"
    "        _SKIP = frozenset({71240, 71401, 76415, 76422, 76508, 76509, 76852, 76853, 76930, 76931,\n"
    "                           73204, 73207, 76209, 76229, 76301, 76350, 76351, 76356})\n"
    "        self._grace_rando_freebie_by_region = {}\n"
    "        self._grace_items_placed = {}\n"
    "        _dropped = 0\n"
    "        for _region in sorted(_RGP):\n"
    "            _flags = [p[0] for p in _RGP[_region] if p[0] not in _SKIP]\n"
    "            if not _flags:\n"
    "                continue\n"
    "            _freebie = self.random.choice(_flags)\n"
    "            self._grace_rando_freebie_by_region[_region] = [_freebie]\n"
    "            _item_flags = [f for f in _flags if f != _freebie]\n"
    "            if not _item_flags:\n"
    "                continue\n"
    "            try:\n"
    "                _robj = self.multiworld.get_region(_region, self.player)\n"
    "            except KeyError:\n"
    "                _dropped += len(_item_flags)\n"
    "                continue\n"
    "            _cands = [l for l in _robj.locations\n"
    "                      if l.address is not None and l.item is None\n"
    "                      and l.progress_type != LocationProgressType.PRIORITY\n"
    "                      and l.name not in getattr(self, 'all_priority_locations', set())]\n"
    "            self.random.shuffle(_cands)\n"
    "            _fillers = [it for it in self.multiworld.itempool\n"
    "                        if it.classification == ItemClassification.filler]\n"
    "            _k = min(len(_item_flags), len(_cands), len(_fillers))\n"
    "            for _i in range(_k):\n"
    "                _iname = GRACE_FLAG_TO_ITEM.get(_item_flags[_i])\n"
    "                if not _iname:\n"
    "                    continue\n"
    "                _cands[_i].place_locked_item(self.create_item(_iname))\n"
    "                self.multiworld.itempool.remove(_fillers[_i])\n"
    "                self._grace_items_placed[_iname] = _item_flags[_i]\n"
    "            if len(_item_flags) > _k:\n"
    "                _dropped += len(_item_flags) - _k\n"
    "                warning(f'{self.player_name}: grace_rando dropped {len(_item_flags) - _k} grace '\n"
    "                        f'drop(s) in {_region} (in-region filler slots/pool filler exhausted).')\n"
    "        if self._grace_items_placed or _dropped:\n"
    "            warning(f'{self.player_name}: grace_rando placed {len(self._grace_items_placed)} grace '\n"
    "                    f'drop(s); {_dropped} dropped for lack of room.')\n"
    "\n"
)
edit(
    "C2 pre_fill method", INIT,
    anchor="    def fill_slot_data(self) -> Dict[str, object]:\n",
    before=True,
    sentinel="def pre_fill(self) -> None:",
    insert_after=_PREFILL,
)
edit(
    "C3 fill_slot_data freebie", INIT,
    anchor="                region_graces.setdefault(_lock, []).extend(_spread(_points, _n))\n",
    sentinel="_grace_rando_freebie_by_region",
    replace_with=(
        "                if getattr(self.options, 'grace_rando', None) and self.options.grace_rando.value:\n"
        "                    _chosen = getattr(self, '_grace_rando_freebie_by_region', {}).get(_region, [])\n"
        "                else:\n"
        "                    _chosen = _spread(_points, _n)\n"
        "                region_graces.setdefault(_lock, []).extend(_chosen)\n"
    ),
)

def edit_c4():
    tag = "C4 emit graceItems"
    try:
        text = _read(INIT)
    except FileNotFoundError:
        results.append((tag, "FAIL", "file not found: %s" % INIT)); return
    eol = _eol(text)
    if "graceItems" in text:
        results.append((tag, "IDEMPOTENT", "graceItems already emitted")); return
    lines = text.split(eol)
    val = 'getattr(self, "_grace_items_placed", {})'
    for i, ln in enumerate(lines):
        if "regionGraces" not in ln:
            continue
        indent = ln[:len(ln) - len(ln.lstrip())]
        m_sub = re.search(r'\bslot_data\s*\[\s*["\']regionGraces["\']\s*\]\s*=', ln)
        m_lit = re.search(r'["\']regionGraces["\']\s*:', ln)
        if m_sub:
            newln = '%sslot_data["graceItems"] = %s' % (indent, val)
        elif m_lit:
            newln = '%s"graceItems": %s,' % (indent, val)
        else:
            continue
        lines.insert(i + 1, newln)
        _write(INIT, eol.join(lines))
        chk = _read(INIT)
        results.append((tag, "PASS" if "graceItems" in chk else "FAIL",
                        "inserted after line %d: %s" % (i + 1, ln.strip()[:60])))
        return
    results.append((tag, "FAIL",
                    'could not locate regionGraces emit -- add manually: slot_data["graceItems"] = ' + val))
edit_c4()

print("")
print("=== patch_apworld_grace_rando summary ===")
worst = 0
for tag, status, detail in results:
    print("  [%-10s] %s  --  %s" % (status, tag, detail))
    if status == "FAIL":
        worst = 1
print("=== %s ===" % ("ALL OK (PASS/IDEMPOTENT)" if not worst else "ONE OR MORE FAIL -- review above"))
sys.exit(worst)
