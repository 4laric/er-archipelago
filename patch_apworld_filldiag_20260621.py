#!/usr/bin/env python3
# patch_apworld_filldiag_20260621.py  (run on Windows from repo root)
#
# DIAGNOSTIC (inert unless env ER_DUMP_FILL is set). Dumps the pool/location/advancement
# composition at the end of create_items so we can see WHY 'No more spots to place N items'
# fires on tight num_regions seeds -- is it advancement > reachable (injectable pressure) or
# priority crowding (headroom)? Writes a timestamped file to Archipelago/output/.
# Remove after diagnosis. Idempotent; aborts if the anchor moved.
#
# USE: set ER_DUMP_FILL=1 and generate the 3 failing seeds, then share the dump files.

import sys, io, os
DEFAULT = os.path.join("Archipelago", "worlds", "eldenring", "__init__.py")
MARKER  = "ER_DUMP_FILL"
ANCHOR = (
'        self.multiworld.itempool += self.local_itempool\n'
'\n'
'    @staticmethod\n'
'    def _small_golden_rune_tier(name: str) -> int:'
)
BLOCK = (
'        self.multiworld.itempool += self.local_itempool\n'
'\n'
'        # FILL DIAGNOSTIC (env ER_DUMP_FILL) -- inert unless set. Dumps pool/location/advancement\n'
'        # composition to Archipelago/output/ so a single gen run reveals the overflow bucket.\n'
'        import os as _os\n'
'        if _os.environ.get("ER_DUMP_FILL"):\n'
'            import time as _time\n'
'            from collections import Counter as _Counter\n'
'            _locs = list(self.multiworld.get_unfilled_locations(self.player))\n'
'            _pool = list(self.local_itempool)\n'
'            _adv = [it for it in _pool if it.advancement]\n'
'            def _cat(_n):\n'
'                if _n.endswith("Lock"): return "region_lock"\n'
'                if "Great Rune" in _n: return "great_rune"\n'
'                if "Torch" in _n: return "spelunker_torch"\n'
'                if "Rune" in _n: return "rune_item"\n'
'                return "other_adv"\n'
'            _advcat = _Counter(_cat(it.name) for it in _adv)\n'
'            _byregion = _Counter()\n'
'            for _l in _locs:\n'
'                _pr = getattr(_l, "parent_region", None)\n'
'                _byregion[getattr(_pr, "name", "?")] += 1\n'
'            _seed = getattr(self.multiworld, "seed", "?")\n'
'            _ts = _time.strftime("%Y%m%d_%H%M%S")\n'
'            _fn = _os.path.join("output", "ER_FILLDIAG_%s_%s_%s.txt" % (self.player, _seed, _ts))\n'
'            try:\n'
'                with io.open(_fn, "w", encoding="utf-8") as _f:\n'
'                    _f.write("player=%s seed=%s\\n" % (self.player_name, _seed))\n'
'                    _f.write("total_locations_unfilled=%d\\n" % len(_locs))\n'
'                    _f.write("total_pool_items=%d\\n" % len(_pool))\n'
'                    _f.write("advancement_items=%d\\n" % len(_adv))\n'
'                    _f.write("priority_locations=%d\\n" % len(self.all_priority_locations))\n'
'                    _f.write("slack_locations_minus_advancement=%d\\n" % (len(_locs) - len(_adv)))\n'
'                    _f.write("advancement_by_category=%s\\n" % dict(_advcat))\n'
'                    _f.write("advancement_item_names:\\n")\n'
'                    for _n, _c in _Counter(it.name for it in _adv).most_common():\n'
'                        _f.write("  %3d %s\\n" % (_c, _n))\n'
'                    _f.write("locations_per_region:\\n")\n'
'                    for _r, _c in _byregion.most_common():\n'
'                        _f.write("  %3d %s\\n" % (_c, _r))\n'
'                print("ER_DUMP_FILL: wrote %s (locs=%d adv=%d prio=%d)"\n'
'                      % (_fn, len(_locs), len(_adv), len(self.all_priority_locations)))\n'
'            except Exception as _e:\n'
'                print("ER_DUMP_FILL write failed:", _e)\n'
'\n'
'    @staticmethod\n'
'    def _small_golden_rune_tier(name: str) -> int:'
)

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    if not os.path.isfile(path):
        print("ERROR: file not found:", path); return 2
    with io.open(path, "r", encoding="utf-8", newline="") as f:
        src = f.read()
    nl = "\r\n" if "\r\n" in src else "\n"
    body = src.replace("\r\n", "\n")
    if MARKER in body:
        print("ALREADY APPLIED -- no change."); return 0
    if body.count(ANCHOR) != 1:
        print("ERROR: anchor found %d (expected 1). Aborting." % body.count(ANCHOR)); return 3
    body = body.replace(ANCHOR, BLOCK, 1)
    out = body.replace("\n", nl) if nl == "\r\n" else body
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    print("APPLIED." if MARKER in out.replace("\r\n","\n") else "FAILED verify.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
