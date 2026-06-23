#!/usr/bin/env python3
# patch_apworld_progression_topup_20260621.py  (run on Windows from repo root)
#
# Dynamic progression TOP-UP -- the flip side of soft_progression / progression_skip_balancing.
# When a seed marks more important_locations (PRIORITY) than it has advancement items to fill
# them, AP silently downgrades the surplus priority slots to normal, so important_locations
# quietly receive filler. This promotes the shortfall from a ranked ladder (S/A-tier gear, then
# the biggest rune drops) to progression_skip_balancing: it carries the advancement bit (so it
# COUNTS for the priority fill and is reachability-guaranteed) but is skipped by the cross-player
# balancing pass, so a flood of promoted loot does not distort sphere math.
#
# Fires only on a real deficit and promotes exactly enough -> no-op for unconstrained seeds.
# Candidate pool self-caps the promotion (if candidates < deficit, the rest downgrade as today).
# Idempotent; aborts if the anchor moved. Repackage the apworld + gen-test a num_regions seed.

import sys, io, os
DEFAULT = os.path.join("Archipelago", "worlds", "eldenring", "__init__.py")
MARKER  = "_prog_topup_deficit"

ANCHOR = (
'        # Add items to itempool\n'
'        self.multiworld.itempool += self.local_itempool'
)
BLOCK = (
'        # Dynamic progression top-up (flip side of soft_progression / progression_skip_balancing):\n'
'        # when more important_locations (PRIORITY) are marked than there are advancement items to\n'
'        # fill them, AP silently downgrades the surplus priority slots -> important_locations quietly\n'
'        # get filler. Promote the shortfall from a ranked ladder (S/A-tier gear, then the biggest\n'
'        # rune drops) to progression_skip_balancing: carries the advancement bit (counts for the\n'
'        # priority fill + reachability-guaranteed) but skips the cross-player balancing pass. Fires\n'
'        # only on a real deficit; the candidate pool self-caps. (patch_apworld_progression_topup)\n'
'        _prog_topup_deficit = len(self.all_priority_locations) - sum(\n'
'            1 for _it in self.local_itempool if _it.advancement)\n'
'        if _prog_topup_deficit > 0:\n'
'            _RUNE_PROMO_RANK = {\n'
'                "Lord\'s Rune": 0, "Hero\'s Rune [5]": 1, "Hero\'s Rune [4]": 2,\n'
'                "Hero\'s Rune [3]": 3, "Hero\'s Rune [2]": 4, "Hero\'s Rune [1]": 5,\n'
'                "Numen\'s Rune": 6, "Golden Rune [10]": 7, "Golden Rune [9]": 8,\n'
'                "Golden Rune [8]": 9,\n'
'            }\n'
'            def _topup_rank(_it):\n'
'                _t = ITEM_TIERS.get(_it.name)\n'
'                if _t == "S": return (0, 0)\n'
'                if _t == "A": return (1, 0)\n'
'                if _it.name in _RUNE_PROMO_RANK: return (2, _RUNE_PROMO_RANK[_it.name])\n'
'                return None\n'
'            _topup_cands = sorted(\n'
'                ((_topup_rank(_it), _i, _it) for _i, _it in enumerate(self.local_itempool)\n'
'                 if (not _it.advancement) and _topup_rank(_it) is not None),\n'
'                key=lambda _p: (_p[0], _p[1]))\n'
'            for _r, _i, _it in _topup_cands[:_prog_topup_deficit]:\n'
'                _it.classification = ItemClassification.progression_skip_balancing\n'
'\n'
'        # Add items to itempool\n'
'        self.multiworld.itempool += self.local_itempool'
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
        print("ALREADY APPLIED (marker present) -- no change."); return 0
    c = body.count(ANCHOR)
    if c != 1:
        print("ERROR: anchor found %d (expected 1). Aborting." % c); return 3
    body = body.replace(ANCHOR, BLOCK, 1)
    out = body.replace("\n", nl) if nl == "\r\n" else body
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    with io.open(path, "r", encoding="utf-8", newline="") as f:
        chk = f.read().replace("\r\n", "\n")
    ok = (MARKER in chk
          and "progression_skip_balancing" in chk
          and chk.count("self.multiworld.itempool += self.local_itempool") == 1)
    print("APPLIED." if ok else "WROTE but verification FAILED -- inspect.")
    print("  newline:", "CRLF" if nl == "\r\n" else "LF", " bytes:", len(out))
    return 0 if ok else 5

if __name__ == "__main__":
    raise SystemExit(main())
