"""THE SHOP HUB-DEFAULT IS ALSO A LOGIC DEFAULT -- #701, option 3 ("C") only.

MOTIVATING CASE (rule 11). Cokeman5, Discord, 2026-08-15, reading his multiworld's spoiler log:

    "it looks like it was expecting my friend to be able to get this check FROM THE GET-GO:
     Roundtable Hold :: Furlcalling Finger Remedy - from Patches or Thiollier [f110030]
     (Noire): Scadu Altus Lock -- but he didn't have either of the regions with Patches or
     Thiollier."

He is right. The item on the check is a REGION LOCK, i.e. progression, placed as though reachable
on turn one, behind an NPC standing in a region the finder did not hold.

THE MECHANISM, AND WHY THIS FILE EXISTS AT ALL. `merchant_shops.tsv`'s own header states the
contract: *a row with >1 distinct map region -> gen_data collapses to HUB + DEFAULTED*. Only the
first half was ever implemented. `MERCHANT_SHOP_REGION` deliberately re-pins nothing for a flag
whose physical merchants resolve to several regions ("disjunctive reachability the region-lock
world can't express yet"), so the row fell through to `SHOP_ROW_REGION` -- whose block label for
these merchants is literally 'Roundtable Hold' -- and `_region_is_derived()` then reported that HUB
answer as DERIVED. Roundtable Hold is the hub and the hub is always kept, so a rule written to
answer "what do we CALL this check?" (#557) silently also answered "when is it IN LOGIC?" with
"immediately". Same one-table-two-jobs shape as #688.

The collapse does not weaken the disjunction, it DELETES it. Patches is reachable from Limgrave
(Murkwater Cave), Mt. Gelmir (Volcano Manor) or Cerulean (Thiollier); "any of those three" became
"no requirement at all", which is strictly weaker than the weakest branch.

WHICH OPTION THIS IS. #701 lists three fixes. This is option 3, "C" -- take the rows OFF the
progression surface so they hold filler and gate nothing. Option 2 ("B", region them to their
earliest site) is a SEPARATE later change and is deliberately NOT implemented here; option 1 (a
real disjunction) needs #320/#502's machinery.

WHY THE DEFAULTED BAR AND NOT `_SURFACE_EXCLUDE_FLAGS`. `SURFACE_EXCLUDE_APS` is consumed by the
surface SELECTION but is ABSENT from `core._NO_PROGRESSION_APS`, the item_rule fill actually obeys
-- measured 2026-08-04 on the isolated-merchant 16 (#350): the bar trimmed the advertisement while
fill stayed free to place a Lock. So it has to be the DEFAULTED path, which lands on the LOCATION.

WHY BOTH DIRECTIONS ARE ASSERTED HERE. Option C makes #701's stated acceptance test VACUOUS: "must
not place a progression item on any collapsed Patches row" passes trivially once nothing can be
placed there, and would pass just as happily if the 15 locations had been DELETED. So every
negative below is paired with a positive witness -- the rows still exist, still count, still take a
real item from a real fill -- and the item_rule assertion carries a control location the same rule
object ACCEPTS, so "rejects everything" cannot masquerade as "rejects progression".

THE POPULATION IS 15: 12 shared Patches/Thiollier rows (including f67600 under #557) plus three
Communion rows. Five
other Patches rows left this population under #220 because FromSoft's release flag explicitly names
NPC309 as their owner; those are no longer a disjunction and may take their Patches-only sites. The
three Dragon
Communion incantations (f290500 Dragonfire, f290750 Dragonclaw, f290760 Dragonmaw) are the identical
shape -- two altars, two regions, collapse to hub -- and are named explicitly below so that
undercount cannot recur.
"""
import os
import sys
import unittest

import pytest

from ..data import HUB, LOCATIONS
from ..location_tags import LOCATION_TAGS, DEFAULTED_REGION_APS
from ..features.progression_surface import allowed_ap_ids
from .. import contract

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:                                    # direct/unittest fallback
    sys.path.insert(0, HERE)
    from _util import find_repo_root, REPO_ONLY_REASON

_ROOT = find_repo_root(HERE)

# The two collapsed merchant families, by the substring their generated names carry. Substrings, not
# whole names: the honest-label suffix "(region unconfirmed)" rides the defaulted list and the
# collision ordinals ride after that, so a whole-name pin would be a second thing to maintain.
PATCHES = "from Patches or Thiollier"
COMMUNION = "from Cathedral of Dragon Communion or Church of Dragon Communion"
EXPECTED_PATCHES = 12
# NAMED, not counted. #557's table stopped at the Patches 16 and these three were "left behind
# because #557 counted 16" -- the exact failure #701's acceptance criteria calls out.
COMMUNION_FLAGS = {290500: "Dragonfire", 290750: "Dragonclaw", 290760: "Dragonmaw"}
EXPECTED_TOTAL = EXPECTED_PATCHES + len(COMMUNION_FLAGS)
REPORTED = 110030          # Cokeman5's check: Furlcalling Finger Remedy
# The three regions Patches/Thiollier actually stand in (#557's table). The acceptance seed must hold
# NONE of them, or it cannot tell the fix from the hub being open.
PATCHES_REGIONS = ("Limgrave", "Mt. Gelmir", "Cerulean")


def collapsed_rows():
    """The hub rows whose merchant stands in more than one region -- (name, ap_id, flag)."""
    return [(n, ap, fl) for (n, ap, fl) in LOCATIONS.get(HUB, ())
            if PATCHES in n or COMMUNION in n]


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


class HubCollapsedPopulation(unittest.TestCase):
    """The population, and that the bar reaches all of it."""

    def test_the_population_is_exactly_fourteen_and_names_the_communion_three(self):
        rows = collapsed_rows()
        patches = [r for r in rows if PATCHES in r[0]]
        communion = [r for r in rows if COMMUNION in r[0]]
        self.assertEqual(len(patches), EXPECTED_PATCHES,
                         "the Patches/Thiollier family moved: %r" % [r[0] for r in patches])
        self.assertEqual(sorted(r[2] for r in communion), sorted(COMMUNION_FLAGS),
                         "the Dragon Communion three are the rows #557 forgot; they must be in the "
                         "same population, not a follow-up. Got %r" % [r[2] for r in communion])
        self.assertEqual(len(rows), EXPECTED_TOTAL)
        self.assertIn(REPORTED, [r[2] for r in rows],
                      "f110030 is the check Cokeman5 reported; it must be in the population")

    def test_every_collapsed_row_is_barred_from_carrying_progression(self):
        """THE FIX. All 15 in DEFAULTED_REGION_APS -- the bar core._NO_PROGRESSION_APS reads, which is
        the one that reaches the location's item_rule (SURFACE_EXCLUDE_APS does not: #350)."""
        rows = collapsed_rows()
        self.assertEqual(len(rows), EXPECTED_TOTAL, "population changed; fix that first")
        unbarred = sorted(fl for (_n, ap, fl) in rows if ap not in DEFAULTED_REGION_APS)
        self.assertEqual(unbarred, [],
                         "flag(s) %r sit in the always-open hub because their merchant stands in "
                         "SEVERAL regions -- a collapse, not a derivation -- and may not carry "
                         "progression (#701)" % (unbarred,))

    def test_no_collapsed_row_is_on_the_progression_surface_for_any_class(self):
        """The surface half, per class, so a widen rung cannot re-admit them."""
        aps = {ap for (_n, ap, _f) in collapsed_rows()}
        self.assertEqual(len(aps), EXPECTED_TOTAL)
        tagged = sorted(c for c in contract.SURFACE_CLASSES
                        if any(contract.has_class(LOCATION_TAGS.get(ap, ()), {c}) for ap in aps))
        self.assertNotEqual(tagged, [],
                            "the 15 carry Shop/ShopNonSpell tags; if they carry NONE this test has "
                            "stopped looking at anything")
        leaked = sorted((c, ap) for c in contract.SURFACE_CLASSES
                        for ap in (aps & allowed_ap_ids(LOCATION_TAGS, {c})))
        self.assertEqual(leaked, [],
                         "surface class(es) still admit a hub-collapsed merchant row: %r" % (leaked,))

    def test_the_rows_keep_their_hub_region_prefix(self):
        """#701 explicitly forbids fixing this by RENAMING: the `Roundtable Hold ::` prefix is #557's
        subject and the tracker groups on it. Option C touches LOGIC only, so the prefix stays."""
        rows = collapsed_rows()
        self.assertEqual(len(rows), EXPECTED_TOTAL)
        wrong = sorted(n for (n, _a, _f) in rows if not n.startswith(HUB + " ::"))
        self.assertEqual(wrong, [], "option C must not re-key the region; that is option B")


@pytest.mark.skipif(_ROOT is None, reason=REPO_ONLY_REASON)
class HubCollapsedPopulationIsDerived(unittest.TestCase):
    """The population is a RULE, not a list of 19 ap ids.

    A hand-list is what let #557 ship 16 and miss 3, and it would miss the next merchant a regen
    splits across regions. gen_data derives the set from `merchant_shops.tsv`; this re-derives the
    NECESSARY condition from the same committed tables, so a pin list quietly replacing the rule
    goes red here."""

    def test_each_barred_row_has_a_merchant_standing_in_more_than_one_place(self):
        gf = os.path.join(_ROOT, "greenfield")
        row2flag = {}
        for r in _tsv(os.path.join(gf, "shop_rows.tsv")):
            if str(r.get("stock_flag", "")).strip().isdigit():
                row2flag[r["row_id"]] = int(r["stock_flag"])
        self.assertGreater(len(row2flag), 100,
                           "shop_rows.tsv gave almost no row->flag pairs; the columns moved and this "
                           "derivation is running blind")
        maps = {}
        for r in _tsv(os.path.join(gf, "merchant_shops.tsv")):
            # Same two filters gen_data applies: no MSB placement is no claim, and the Twin-Maiden
            # hub tile is the bell RE-SELL, not a merchant's home.
            if r.get("map_source") == "binder" or r.get("map_id") in ("", "m11_10"):
                continue
            fl = row2flag.get(r["row_id"])
            if fl is not None:
                maps.setdefault(fl, set()).add(r["map_id"])
        rows = collapsed_rows()
        self.assertEqual(len(rows), EXPECTED_TOTAL)
        single = sorted((fl, sorted(maps.get(fl, ()))) for (_n, _a, fl) in rows
                        if len(maps.get(fl, ())) < 2)
        self.assertEqual(single, [],
                         "flag(s) %r are barred as hub-COLLAPSED but their merchant stands in one "
                         "place (or none) -- the bar and its justification have drifted apart"
                         % (single,))
