"""#701 OPTION 2 ("B") -- A COLLAPSED MERCHANT ROW TAKES ITS EARLIEST KEPT SITE (the tables).

Third file on #701. `test_gf_hub_collapsed_merchant_rows.py` and `..._seed.py` are option 3 ("C"):
the 14 `Roundtable Hold ::` rows whose seller stands in more than one region were in logic AT SPAWN
in every seed (Cokeman5's Scadu Altus Lock on `Furlcalling Finger Remedy - from Patches or Thiollier
[f110030]`, 2026-08-15), so C barred them from carrying progression at all. This file is option 2:
give the row a REAL region -- the EARLIEST of its own sites that the seed KEPT, in `region_spine.SPINE`
order -- gate it on reaching that region, and let it carry progression again.

🛑 THE ACCEPTANCE TEST FLIPS MEANING, DELIBERATELY. C's guard says "a seed holding none of Patches'
regions places no progression on these rows"; B's says "a seed holding one of them MAY". Both are
true at once because they are about DIFFERENT SEEDS, and that is the whole design:

    B NARROWS C's BAR, IT DOES NOT REMOVE IT. No kept site -> no region to stand behind -> C's bar,
    unchanged. A `num_regions` draw that keeps none of {Limgrave, Mt. Gelmir, Cerulean} is a
    legitimate seed and must still generate, so C's behaviour is B's FALLBACK.

C's two files must stay green with this change; `test_gf_hub_collapsed_merchant_site_seed.py`
re-asserts the fallback from B's side against a real seed, so deleting C's files would not silently
delete the rule. This file is the AP-FREE half -- the generated table, the pure SPINE rule and the
tsv derivation -- split out for the same reason C split its two: an AP import at module scope skips
the WHOLE module where Archipelago is absent, and a table assertion has no reason to go dark there.

WHY EARLIEST-KEPT IS SAFE, not merely convenient. The honest rule is a DISJUNCTION -- reachable if
the player holds ANY site -- which the region-lock world still cannot express (#320/#502, #701
option 1, not in scope). Requiring one NAMED site is STRICTER than that disjunction, so it can only
ever refuse a placement the player could have reached, never assert one they could not. It is EXACT
when the seed kept exactly one site.

WHY THE SITES ARE NOT SIMPLY "EVERY REGION THE MERCHANT IS PLACED IN" (gen_data FILTER 3). Patches'
npc_param 523090020 is placed on three OVERWORLD tiles as well -- Scenic Isle (Liurnia), Seethewater
(Mt. Gelmir) and Road of Iniquity (Altus). One npc_param is one character: the game shows it in at
most one of those at a time, on a quest-state condition this pipeline does not model, so none of them
is a place we can ASSERT the merchant is. Counting them would have handed these rows ALTUS, which is
force-kept in every base seed (the capital's only parent), and option B would then have lifted its
bar on essentially every seed on the weakest evidence in the table. Dropping ambiguous placements
leaves exactly the three regions #557's human-reviewed table names -- a derived rule reproducing a
reviewed list -- and leaves the Dragon Communion pair untouched.

THE DRAGON COMMUNION THREE ARE TESTED SEPARATELY (#557 forgot them once already, which is why #701
had to say "the population is 19, not 16"). Their sites are their OWN pair, {Caelid, Limgrave}, and
`Caelid` is first in both the tsv and the alphabet while `Limgrave` is first in SPINE -- so an
implementation that took the first entry of the list instead of the SPINE-earliest fails below.
"""
import os
import sys
import unittest

import pytest

from ..location_tags import DEFAULTED_REGION_APS, HUB_COLLAPSED_SITE_APS, SHOP_RELEASE_GATED_APS
from ..region_spine import SPINE, earliest_kept_site
from .test_gf_hub_collapsed_merchant_rows import (
    COMMUNION, COMMUNION_FLAGS, EXPECTED_PATCHES, EXPECTED_TOTAL, PATCHES, PATCHES_REGIONS,
    REPORTED, collapsed_rows)

# The Dragon Communion altars: Cathedral (Caelid) and Church (Limgrave). Named here for the same
# reason PATCHES_REGIONS is named in the sibling file -- so the fixture can state its own shape.
COMMUNION_REGIONS = ("Caelid", "Limgrave")


def _sites_by_family():
    """(patches_rows, communion_rows) as [(ap, tuple(sites))], read from the generated table."""
    patches, communion = [], []
    for (name, ap, _fl) in collapsed_rows():
        sites = tuple(HUB_COLLAPSED_SITE_APS.get(ap, ()))
        (patches if PATCHES in name else communion).append((ap, sites))
    return patches, communion


class CollapsedSiteTable(unittest.TestCase):
    """The generated half: which sites each collapsed row has, and that B rides C's population."""

    def test_every_collapsed_row_has_sites_and_they_are_all_still_defaulted(self):
        """B's population IS C's population -- the composition, asserted rather than assumed."""
        rows = collapsed_rows()
        self.assertEqual(len(rows), EXPECTED_TOTAL, "population changed; fix the sibling file first")
        missing = sorted(fl for (_n, ap, fl) in rows if ap not in HUB_COLLAPSED_SITE_APS)
        self.assertEqual(missing, [],
                         "collapsed row(s) %r have no site list, so option B can never region them "
                         "and they are stuck on option C forever" % (missing,))
        outside = sorted(ap for ap in HUB_COLLAPSED_SITE_APS if ap not in DEFAULTED_REGION_APS)
        self.assertEqual(outside, [],
                         "ap(s) %r carry option-B sites but are NOT in DEFAULTED_REGION_APS -- B is a "
                         "NARROWING of C's bar; a row outside that bar has nothing to narrow" % (outside,))

    def test_the_patches_eleven_have_exactly_the_three_reviewed_regions(self):
        patches, _ = _sites_by_family()
        self.assertEqual(len(patches), EXPECTED_PATCHES)
        wrong = sorted((ap, s) for (ap, s) in patches if set(s) != set(PATCHES_REGIONS))
        self.assertEqual(wrong, [],
                         "a Patches/Thiollier row's sites are not %r: %r. Altus/Liurnia here means "
                         "gen_data FILTER 3 stopped dropping multi-placed npc_params, and Altus is "
                         "kept in EVERY base seed" % (sorted(PATCHES_REGIONS), wrong[:3]))
        self.assertIn(REPORTED, [fl for (_n, _a, fl) in collapsed_rows()])

    def test_the_dragon_communion_three_have_their_own_pair(self):
        """#557 counted 16 and left these out; they get the same rule over THEIR OWN regions."""
        _, communion = _sites_by_family()
        self.assertEqual(len(communion), len(COMMUNION_FLAGS))
        wrong = sorted((ap, s) for (ap, s) in communion if set(s) != set(COMMUNION_REGIONS))
        self.assertEqual(wrong, [], "a Dragon Communion row's sites are not %r: %r"
                                    % (sorted(COMMUNION_REGIONS), wrong))

    def test_every_site_is_a_real_region(self):
        """A site the seed can never keep is a permanent, silent bar -- and a lock name that does not
        exist. SPINE is the authority; it is a permutation of REGIONS (test_gf_data)."""
        seen = sorted({s for sites in HUB_COLLAPSED_SITE_APS.values() for s in sites})
        self.assertGreaterEqual(len(seen), 4,
                                "the site table names %d distinct region(s); it has stopped seeing "
                                "the two families and this check would pass on an empty table" % len(seen))
        unknown = [s for s in seen if s not in set(SPINE)]
        self.assertEqual(unknown, [], "site(s) %r are not regions of this world" % (unknown,))


class EarliestKeptSite(unittest.TestCase):
    """The pure rule, over kept-subsets a seed search would take minutes to stumble on."""

    def test_none_kept_returns_none_which_is_option_c(self):
        self.assertIsNone(earliest_kept_site(PATCHES_REGIONS, set()))
        self.assertIsNone(earliest_kept_site(PATCHES_REGIONS, {"Altus", "Liurnia", "Caelid"}),
                          "regions that are NOT sites must not resolve one -- Altus in particular is "
                          "kept in every base seed")

    def test_it_is_the_earliest_KEPT_one_not_the_earliest_one(self):
        """Two different kept-subsets, so a hardcoded 'Limgrave' cannot pass."""
        self.assertEqual(earliest_kept_site(PATCHES_REGIONS, set(PATCHES_REGIONS)), "Limgrave")
        self.assertEqual(earliest_kept_site(PATCHES_REGIONS, {"Mt. Gelmir", "Cerulean"}), "Mt. Gelmir")
        self.assertEqual(earliest_kept_site(PATCHES_REGIONS, {"Cerulean"}), "Cerulean")
        self.assertEqual(earliest_kept_site(PATCHES_REGIONS, {"Stormveil", "Cerulean"}), "Cerulean",
                         "Stormveil is EARLIER in SPINE than Cerulean but is not a site of this row")

    def test_the_communion_pair_resolves_in_spine_order_not_list_order(self):
        """`Caelid` is first in the tuple and in the alphabet; `Limgrave` is first in SPINE."""
        self.assertEqual(earliest_kept_site(COMMUNION_REGIONS, {"Caelid", "Limgrave"}), "Limgrave")
        self.assertEqual(earliest_kept_site(COMMUNION_REGIONS, {"Caelid"}), "Caelid")
        self.assertIsNone(earliest_kept_site(COMMUNION_REGIONS, {"Mt. Gelmir", "Cerulean"}),
                          "the Communion rows must NOT ride the Patches rows' sites")

    def test_spine_puts_the_sites_where_this_rule_assumes(self):
        """The rule is only 'earliest' if SPINE says so; pin the order the assertions above encode."""
        rank = {r: i for i, r in enumerate(SPINE)}
        self.assertLess(rank["Limgrave"], rank["Caelid"])
        self.assertLess(rank["Limgrave"], rank["Mt. Gelmir"])
        self.assertLess(rank["Mt. Gelmir"], rank["Cerulean"])


# --------------------------------------------------------------------------- the derivation half

_HERE = os.path.dirname(os.path.abspath(__file__))
try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:                                    # direct/unittest fallback
    sys.path.insert(0, _HERE)
    from _util import find_repo_root, REPO_ONLY_REASON

_ROOT = find_repo_root(_HERE)


def _tsv(path):
    hdr = None
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if hdr is None:
                hdr = parts
                continue
            yield dict(zip(hdr, parts))


@pytest.mark.skipif(_ROOT is None, reason=REPO_ONLY_REASON)
class Filter3DropsMultiPlacedInstances(unittest.TestCase):
    """gen_data FILTER 3, re-derived from the committed tables -- AND SHOWN TO FIRE.

    A guard nothing exercises is untested. This one has one job: keep Patches' three OVERWORLD
    placements (one npc_param, three tiles) out of the site list, because that npc_param's Altus tile
    would otherwise hand every base seed a free lift. So the test asserts both halves -- that a
    multi-placed instance EXISTS on the reported check, and that the sites the rule keeps are exactly
    the single-placement ones."""

    def _instances(self, flag):
        gf = os.path.join(_ROOT, "greenfield")
        row2flag = {}
        for r in _tsv(os.path.join(gf, "shop_rows.tsv")):
            if str(r.get("stock_flag", "")).strip().isdigit():
                row2flag[r["row_id"]] = int(r["stock_flag"])
        self.assertGreater(len(row2flag), 100, "shop_rows.tsv gave almost no row->flag pairs")
        inst = {}
        for r in _tsv(os.path.join(gf, "merchant_shops.tsv")):
            # gen_data's own two claimant filters: no MSB placement is no claim, and the Twin-Maiden
            # hub tile is the bell RE-SELL, not a merchant's home.
            if r.get("map_source") == "binder" or r.get("map_id") in ("", "m11_10"):
                continue
            if row2flag.get(r["row_id"]) != flag:
                continue
            inst.setdefault((r["talk_id"], r["npc_param_id"], r["merchant_name"]), set()).add(r["map_id"])
        self.assertTrue(inst, "no merchant instance claims flag %s; this derivation is blind" % flag)
        return inst

    def test_the_reported_check_really_has_a_multi_placed_merchant_and_it_is_dropped(self):
        inst = self._instances(REPORTED)
        multi = {k: sorted(v) for k, v in inst.items() if len(v) > 1}
        self.assertTrue(multi, "no merchant instance on f%d is placed in more than one map, so FILTER "
                               "3 fires on nothing here and this rule is untested" % REPORTED)
        for k, maps in multi.items():
            self.assertTrue(all(m.startswith("m60") for m in maps),
                            "a multi-placed instance %r spans non-overworld maps %r -- re-read the "
                            "filter before trusting it" % (k, maps))
        single = sorted({m for v in inst.values() if len(v) == 1 for m in v})
        self.assertEqual(len(single), len(PATCHES_REGIONS),
                         "f%d should keep exactly %d single-placement site(s) (Murkwater, Volcano "
                         "Manor, Thiollier); got %r" % (REPORTED, len(PATCHES_REGIONS), single))
        self.assertNotEqual(sorted({m for v in inst.values() for m in v}), single,
                            "nothing was dropped, so the site list is the raw claim list again")

    def test_the_dragon_communion_altars_are_single_placed_so_the_filter_changes_nothing(self):
        for flag in sorted(COMMUNION_FLAGS):
            inst = self._instances(flag)
            multi = {k: sorted(v) for k, v in inst.items() if len(v) > 1}
            self.assertEqual(multi, {}, "f%d gained a multi-placed altar %r -- the Communion pair is "
                                        "supposed to be two npc_params with one placement each"
                                        % (flag, multi))
            self.assertEqual(len(inst), len(COMMUNION_REGIONS),
                             "f%d is claimed by %d instance(s), not the two altars" % (flag, len(inst)))
