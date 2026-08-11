"""The two claimant filters in gen_data._build_merchant_shop_region, re-derived from the TSVs.

er-archipelago#556 and #558. `merchant_shops.tsv` says which PHYSICAL merchant opens each shop row,
and that table is what stops a shop check inheriting its ShopLineupParam block's region. But a row's
claimant list is derived from an `OpenRegularShop(begin, end)` range enumerated wholesale, and a flag
is pinned only when its claimants resolve to EXACTLY ONE region -- so one bogus claimant does not add
a wrong answer, it silently REMOVES the correction and reinstates the block guess. Both filters below
exist to delete a claimant that cannot be standing where the table says.

⭐ THE MOTIVATING CASE, AS A TEST (CONTRIBUTING rule 11). boblerrr's 2026-08-11 seed kept Liurnia and
still got an all-vanilla bell shelf from `Nomadic Merchant's Bell Bearing [5]`, whose merchant stands
in Liurnia. Its 13 rows shipped as Weeping -- a region NEITHER claimant stands in -- because Merchant
Kale's ESD range over-runs his own block into theirs. `test_bell5_rows_pin_to_liurnia` is that seed.

🛑 WHAT THESE TESTS ARE NOT. They re-derive from `merchant_shops.tsv` + `bell_handins.tsv`, the same
inputs gen_data reads, so they cannot witness that gen_data APPLIED the filter. That is what
`test_gf_merchant_region.py`'s anchors do, against the COMMITTED data.py. Both halves are needed: this
file pins the RULE, that one pins the OUTPUT.
"""
import csv
import os
import unittest
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_GF_PKG = os.path.dirname(_HERE)
_GREENFIELD = os.path.dirname(_GF_PKG)


def _tsv(name):
    return next((p for p in (os.path.join(_GF_PKG, name), os.path.join(_GREENFIELD, name))
                 if os.path.isfile(p)), os.path.join(_GF_PKG, name))


def _rows(name):
    with open(_tsv(name), encoding="utf-8-sig") as fh:
        lines = [l for l in fh if not l.startswith("#")]
    return list(csv.DictReader(lines, delimiter="\t"))


def _claims():
    """(talk, npc, name, tile) -> {row id}, HUB re-sell tile excluded. One key per merchant INSTANCE:
    the filters drop a single merchant's claim on a row, never the row."""
    out = defaultdict(set)
    for r in _rows("merchant_shops.tsv"):
        tile = (r.get("map_id") or "").strip()
        if not tile or tile == "m11_10":
            continue
        try:
            rid = int(r["row_id"])
        except (KeyError, ValueError):
            continue
        out[(r.get("talk_id"), r.get("npc_param_id"), r.get("merchant_name"), tile,
             (r.get("map_source") or "").strip())].add(rid)
    return out


class TestNoMsbPlacementNoClaim(unittest.TestCase):
    """FILTER 1. map_source == 'binder' means the talk ESD was found inside a map binder and never
    matched an MSB placement, so its map id is where the FILE was packed, not where anybody stands."""

    def test_binder_source_is_exactly_the_unattributed_lines(self):
        # The filter keys on map_source, so the claim that map_source is a proxy for "no NPC" has to
        # be measured, not assumed. If these three ever come apart, the filter is keying on the wrong
        # column and this test is the only place that would say so.
        rows = _rows("merchant_shops.tsv")
        binder = [r for r in rows if (r.get("map_source") or "").strip() == "binder"]
        self.assertTrue(binder, "no map_source=binder lines at all -- the filter has no subject, "
                                "which means the datamine changed shape and FILTER 1 is now dead code")
        self.assertEqual(len(binder), 134, "the no-MSB claimant count moved; re-verify the filter")
        bad = [r["row_id"] for r in binder
               if (r.get("npc_param_id") or "").strip() or (r.get("merchant_name") or "").strip()]
        self.assertEqual(bad, [], "map_source=binder line(s) that DO carry an npc/name: %r -- "
                                  "map_source is no longer a proxy for 'no MSB placement'" % bad[:10])
        named = [r["row_id"] for r in rows
                 if (r.get("map_source") or "").strip() != "binder"
                 and not (r.get("npc_param_id") or "").strip()]
        self.assertEqual(named, [], "npc-less line(s) NOT marked binder: %r" % named[:10])

    def test_the_origin_tile_is_never_a_real_placement(self):
        # WITNESS, not a count. m60_00_00 is the overworld ORIGIN tile: no merchant stands there, so
        # every line claiming it must be caught by FILTER 1 or the filter is not doing its job.
        at_origin = [r for r in _rows("merchant_shops.tsv")
                     if (r.get("map_id") or "").strip() == "m60_00_00"]
        # WITNESS. Without this the test passes just as happily if the origin tile stops appearing in
        # the table at all -- which is the failure mode where the filter has quietly lost its subject.
        self.assertEqual(len(at_origin), 36, "expected 36 origin-tile claimant line(s), found %d -- "
                                             "the table changed shape, re-verify FILTER 1"
                                             % len(at_origin))
        leaked = sorted({(r.get("talk_id"), r.get("map_source")) for r in at_origin
                         if (r.get("map_source") or "").strip() != "binder"})
        self.assertEqual(leaked, [], "origin-tile placement(s) FILTER 1 would keep: %r" % (leaked,))

    def test_the_filter_discriminates_by_line_not_by_map(self):
        # 🛑 THE TEST THAT NEARLY WENT THE OTHER WAY. m11_00 (Leyndell) hosts BOTH kinds of line: the
        # nameless talk 800001100 (binder, noise) and Scribe Corhyn at npc 523510034 (msb+binder, a
        # real Leyndell placement from his questline). An earlier draft of this test asserted m11_00
        # was an impossible merchant map and FAILED on Corhyn -- correctly. The filter must drop the
        # first and keep the second, so a map-level rule is wrong and this pins that.
        at_m11 = {(r.get("talk_id"), (r.get("map_source") or "").strip(), r.get("merchant_name"))
                  for r in _rows("merchant_shops.tsv") if (r.get("map_id") or "").strip() == "m11_00"}
        self.assertIn(("351001100", "msb+binder", "Scribe Corhyn"), at_m11,
                      "Corhyn's real m11_00 placement is gone: %r" % (sorted(at_m11),))
        self.assertIn(("800001100", "binder", ""), at_m11,
                      "the nameless m11_00 claimant is gone: %r" % (sorted(at_m11),))

    def test_no_row_loses_its_last_claimant(self):
        # The filter must be free: dropping a claimant may un-split a flag, never blind a row. A row
        # left with zero claimants would fall back to the legacy block guess -- the bug, re-created.
        cl = _claims()
        before = {r for rs in cl.values() for r in rs}
        after = {r for k, rs in cl.items() if k[4] != "binder" for r in rs}
        # TWO WITNESSES, because "no row was blinded" is trivially true of a filter that does nothing.
        self.assertGreater(len(before), 400, "only %d claimed row(s) (515 measured 2026-08-11) -- "
                                             "the table is not being read" % len(before))
        dropped = sum(len(rs) for k, rs in cl.items() if k[4] == "binder")
        self.assertEqual(dropped, 134, "FILTER 1 dropped %d claim(s), expected 134" % dropped)
        self.assertEqual(sorted(before - after), [],
                         "row(s) whose ONLY claimant was a binder line -- FILTER 1 would blind them")


class TestOneBellRangePerMerchant(unittest.TestCase):
    """FILTER 2. bell_handins.tsv's ranges are pairwise disjoint and each is one merchant's OWN
    block, so a claimant spanning two of them has an ESD range that over-ran its block."""

    def setUp(self):
        self.bells = []
        for r in _rows("bell_handins.tsv"):
            try:
                self.bells.append((int(r["shop_begin"]), int(r["shop_end"]), r["bell_name"]))
            except (KeyError, ValueError):
                pass
        self.assertTrue(self.bells, "bell_handins.tsv empty -- FILTER 2 has no discriminator")
        self.claims = {k: v for k, v in _claims().items() if k[4] != "binder"}

    def bell_of(self, row):
        for a, b, n in self.bells:
            if a <= row <= b:
                return n
        return None

    def test_bell_ranges_are_pairwise_disjoint(self):
        # The whole filter rests on this. Overlapping ranges would make "spans two bells" meaningless.
        # WITNESS: 38 is the mined count (38 of 38 matched the merchants' own scripts when the table
        # was cut -- see test_gf_bell_handins). A shrunken table makes "no overlaps" free.
        self.assertEqual(len(self.bells), 38, "expected 38 bell ranges, found %d" % len(self.bells))
        spans = sorted((a, b, n) for a, b, n in self.bells)
        overlaps = [(spans[i], spans[i + 1]) for i in range(len(spans) - 1)
                    if spans[i][1] >= spans[i + 1][0]]
        self.assertEqual(overlaps, [], "overlapping bell ranges: %r" % (overlaps,))

    def test_exactly_one_merchant_over_reaches_and_it_is_kale(self):
        # A NAMED witness, not a bare count: if a second merchant starts over-reaching, the filter
        # will silently start deleting ITS claims too, and that should be a decision, not a diff.
        spanning = {k: sorted(x for x in {self.bell_of(r) for r in rs} if x)
                    for k, rs in self.claims.items()}
        spanning = {k: v for k, v in spanning.items() if len(v) > 1}
        self.assertEqual(len(spanning), 1, "expected exactly ONE over-reaching merchant instance, got "
                                           "%d: %r" % (len(spanning), sorted(spanning)))
        (k, ranges), = spanning.items()
        self.assertIn("Kal", k[2], "the over-reaching instance is no longer Kale: %r" % (k,))
        self.assertEqual(ranges, ["Isolated Merchant's Bell Bearing [1]", "Kale's Bell Bearing",
                                  "Nomadic Merchant's Bell Bearing [5]"])

    def test_block_majority_would_pick_the_wrong_block(self):
        # ⚠️ Records a REJECTED design so nobody re-derives it. The cheap version of this filter is
        # "keep the 100-id block the claimant claims most of". Kale claims 18 rows of block 1005 (his)
        # and 26 of 1006 (not his), so the cheap version deletes his own shop and keeps the theft.
        kale = next(rs for k, rs in self.claims.items() if "Kal" in (k[2] or ""))
        by_block = defaultdict(int)
        for r in kale:
            by_block[r // 100] += 1
        self.assertEqual(max(by_block, key=by_block.get), 1006,
                         "block-majority no longer picks the wrong block; re-read the filter comment "
                         "before concluding the cheap rule is now safe")
        self.assertEqual(dict(by_block), {1005: 18, 1006: 26})

    def test_deference_can_never_orphan_a_bell_range(self):
        # The rule drops a spanning claimant's rows in range B only when some OTHER instance claims
        # rows in B and in NO other range -- an exclusive owner. So every range keeps a claimant.
        ranges_of = {k: {self.bell_of(r) for r in rs if self.bell_of(r)} for k, rs in self.claims.items()}
        exclusive = defaultdict(set)
        for k, rs in ranges_of.items():
            if len(rs) == 1:
                exclusive[next(iter(rs))].add(k)
        survivors = defaultdict(set)
        for k, rs in self.claims.items():
            for r in rs:
                b = self.bell_of(r)
                if b and len(ranges_of[k]) > 1 and exclusive.get(b) and k not in exclusive[b]:
                    continue
                survivors[r].add(k)
        claimed = {r for rs in self.claims.values() for r in rs}
        # WITNESS: the rule has to have BITTEN for "it orphaned nothing" to mean anything. 26 is
        # Kale's two stolen tranches (13 + 13).
        bitten = sum(1 for k, rs in self.claims.items() for r in rs
                     if self.bell_of(r) and len(ranges_of[k]) > 1
                     and exclusive.get(self.bell_of(r)) and k not in exclusive[self.bell_of(r)])
        self.assertEqual(bitten, 26, "FILTER 2 dropped %d claim(s), expected 26" % bitten)
        orphans = sorted(r for r in claimed if not survivors[r])
        self.assertEqual(orphans, [], "row(s) left with no claimant by FILTER 2: %r" % orphans[:10])

    def test_bell5_rows_pin_to_liurnia(self):
        # ⭐ THE MOTIVATING CASE. boblerrr's seed kept Liurnia; these 13 rows shipped as Weeping.
        # Asserted on the RULE's output here; the shipped answer is asserted in test_gf_merchant_region.
        rows = [r for r in range(100625, 100650)
                if any(r in rs for rs in self.claims.values())]
        self.assertTrue(rows, "no claimant for bell [5]'s range at all -- the derivation went dark")
        for r in rows:
            keep = sorted(k[2] or "(unnamed)" for k, rs in self.claims.items()
                          if r in rs and len({self.bell_of(x) for x in rs if self.bell_of(x)}) <= 1)
            self.assertEqual(keep, ["Nomadic Merchant"],
                             "row %d's surviving claimant(s) after FILTER 2: %r -- expected the "
                             "Nomadic Merchant who owns the block" % (r, keep))


if __name__ == "__main__":
    unittest.main()
