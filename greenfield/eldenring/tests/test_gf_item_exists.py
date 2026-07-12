"""EVERY CHECK'S ITEM MUST EXIST IN THE GAME.

The sibling of the phantom-FLAG guard. That one asks "does this acquisition flag exist?"; this asks
"does the thing the lot hands you exist?"

13 checks shipped pointing at an ItemLotParam row whose every item resolves to NO NAME ANYWHERE IN
THE GAME -- 8 goods ids (310, 401, 9800, 9801, 12302, 12307, 3000600, 8178) have no EquipParamGoods
row at all, and the rest are FromSoft's own cut-content placeholders whose FMG entry literally reads
"[ERROR]" or "%null%". They fell back to Rune filler, so they were checks holding a rune, hung on an
item that does not exist: the flag may never fire, and the seed can then never be 100%'d.

Our own pipeline had already said so and we shipped anyway -- `item_ids: 4811 of 4857 locations
resolved (99.0%)`. A number printed at gen time is not a gate.

CROSS-VALIDATED: Bedrock's independently-built (matt-lineage) table contains ZERO of the 13.

SIGHTED-ONLY: needs elden_ring_artifacts (params + the item-name FMGs), so it SKIPS on the GitHub
runner and RUNS in run_ci.ps1. That is the same shape as the provenance oracle, and it is why the
Windows gate is the one that matters.
"""
import csv
import glob
import os
import unittest
import xml.etree.ElementTree as ET

from ..data import LOCATIONS

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _artifacts():
    for up in (HERE, os.path.dirname(HERE), os.path.dirname(os.path.dirname(HERE))):
        p = os.path.join(up, "elden_ring_artifacts")
        if os.path.isdir(p):
            return p
    return None


PLACEHOLDERS = ("%null%", "[ERROR]")
# lotItemCategory -> FMG stem. Derived empirically over every lot row in the game
# (1->Goods 95%, 2->Weapon 99%, 3->Protector 99%, 4->Accessory 100%, 5->Gem 98%).
# Categories 0 and 6 (24 rows) are ambiguous and are NEVER judged.
CAT_FMG = {1: "Goods", 2: "Weapon", 3: "Protector", 4: "Accessory", 5: "Gem"}


class TestEveryCheckItemExists(unittest.TestCase):

    def test_no_check_points_at_an_item_that_does_not_exist(self):
        art = _artifacts()
        if not art:
            self.skipTest("elden_ring_artifacts absent -- item-existence oracle cannot run (it is "
                          "SIGHTED-only; run_ci.ps1 runs it, the GitHub runner cannot)")
        msg = os.path.join(art, "msg")
        vv = os.path.join(art, "vanilla_er", "vanilla_er")
        if not (os.path.isdir(msg) and os.path.isdir(vv)):
            self.skipTest("artifacts present but msg/ or vanilla_er/ missing")

        named = {}
        for cat, stem in CAT_FMG.items():
            ids = set()
            # *Name*.fmg.xml -- the _dlc01/_dlc02 tables MUST be included. Omitting them makes the
            # entire DLC look like cut content (an earlier pass "found" 893 dead checks that way).
            for fp in glob.glob(os.path.join(msg, "item*-msgbnd-dcx", stem + "Name*.fmg.xml")):
                for t in ET.parse(fp).getroot().iter("text"):
                    i, txt = t.get("id"), (t.text or "").strip()
                    if i and txt and txt not in PLACEHOLDERS:
                        ids.add(int(i))
            named[cat] = ids
        self.assertTrue(all(named.values()), "item-name FMGs parsed empty -- the oracle would pass vacuously")

        lots = {}
        for fn in ("ItemLotParam_map.csv", "ItemLotParam_enemy.csv"):
            with open(os.path.join(vv, fn), newline="", encoding="utf-8-sig") as fh:
                for r in csv.DictReader(fh):
                    try:
                        fl = int(r.get("getItemFlagId", 0) or 0)
                    except ValueError:
                        continue
                    if fl <= 0:
                        continue
                    for k in range(1, 9):
                        try:
                            iid = int(r.get("lotItemId%02d" % k, 0) or 0)
                            cat = int(r.get("lotItemCategory%02d" % k, 0) or 0)
                        except ValueError:
                            continue
                        if iid > 0:
                            lots.setdefault(fl, []).append((iid, cat))

        def is_named(iid, cat):
            if cat not in named:
                return True                                   # cat 0/6: never judged
            if iid in named[cat]:
                return True
            # weapons carry their reinforcement in the id: +N == base + N
            return cat == 2 and (iid // 100) * 100 in named[cat]

        bad = []
        for region, locs in LOCATIONS.items():
            for (name, ap, flag) in locs:
                items = lots.get(flag)
                if items and not any(is_named(i, c) for i, c in items):
                    bad.append(f"{name} (ap {ap}, flag {flag}, region {region}, items {items})")
        self.assertEqual(
            bad, [],
            "%d check(s) point at an item that does not exist in the game (no param row, or the FMG "
            "name is FromSoft's '[ERROR]'/'%%null%%' cut-content placeholder). They fall back to Rune "
            "filler and their flag may never fire, so the seed can never be 100%%'d:\n  %s"
            % (len(bad), "\n  ".join(bad)))
