"""A boss whose ARENA is quest-gated must not host required progression.

THE BUG THIS PINS (player report, 2026-07-27, three-player multiworld). A region Lock was placed on
`Deeproot Depths :: Remembrance of the Lichdragon - Fortissax` (flag 510110). Fortissax is fightable
only inside Fia's Deathbed Dream, which does not exist until she has been handed the Cursemark of
Death -- so the check could never be reached and the seed could not be finished. Two independent
defects had to line up, and both are fixed together because either one alone still strands a player:

  1. THE CHECK WAS NOT TAGGED. Every other member of Fia's cluster was already questline-missable in
     `gen_data.QUEST_GATED_FLAGS` -- f400392 (the Cursemark itself), f400339 (Fia's Hood), f400348
     (Inseparable Sword), f9502 (Mending Rune of the Death-Prince). The boss reward was not, because
     every gate screen we own reads an AWARD SITE and this gate is on the EXISTENCE OF THE FIGHT
     (see `_BOSS_ARENA_QUEST_GATED` in gen_data.py). It is also the only member carrying MajorBoss +
     Remembrance, i.e. the one member features/progression_surface actively STEERS Locks onto.

  2. THE PREREQUISITE ITEM WAS DELETED FROM THE POOL. features/filler_curation called every Goods
     item junk (an ID-nibble test), so the filler allocator overwrote both `Cursemark of Death`
     copies in essentially every seed -- which is why the reporter could not find one anywhere in
     three worlds' spoiler logs. Now subtracted via the param-derived KEY_ITEM_GOODS.

WHY FORTISSAX AND NOT EVERY QUEST-ADJACENT BOSS: a region Lock lights that region's grace bundle, so
the player warps past the physical route (Ranni's chain into Lake of Rot, the medallion lifts, the
Pureblood Medal are all bypassed). A warp cannot bypass a fight that has not been created yet.

⚠️ RED UNTIL A REGEN, AND THAT IS THE HANDSHAKE, NOT A BUG. Both fixes live in `gen_data.py`, whose
outputs (`missable_locations.py`, `item_ids.py`) are generated on Alaric's box -- the licensing-
restricted params are not in CI or the sandbox. Until `build.ps1 -Greenfield` runs, the tagged flag
and KEY_ITEM_GOODS are absent and these tests fail by design. They are written to fail on the ABSENT
DATUM with that message rather than to skip, because a skip here reads exactly like a pass.
"""
import csv
import os
import unittest

import pytest

from ._util import world_items  # noqa: E402

pytest.importorskip("worlds.eldenring")

from worlds.eldenring.data import LOCATIONS                       # noqa: E402
from worlds.eldenring.missable_locations import MISSABLE_LOCATIONS  # noqa: E402
from worlds.eldenring.location_tags import LOCATION_TAGS, DEFAULTED_REGION_APS  # noqa: E402
from worlds.eldenring.contract import SURFACE_DEFAULT_CLASSES     # noqa: E402
from worlds.eldenring.features.progression_surface import allowed_ap_ids  # noqa: E402
from worlds.eldenring.features import filler_curation as fc       # noqa: E402

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
GAME = "Elden Ring"

# Fia's Deathbed-Dream cluster, keyed by EVENT FLAG (ap_ids renumber; flags do not). Four of the five
# were already tagged before this test existed -- they are here so the assertion is about the CLUSTER,
# not about the one member that broke. A future questline award that joins this cluster and is not
# tagged fails here too.
DEATHBED_DREAM_FLAGS = {
    9502:   "Mending Rune of the Death-Prince (Fia's reward)",
    400339: "Fia's Hood",
    400348: "Inseparable Sword",
    400392: "Cursemark of Death (the handover that opens the dream)",
    510110: "Remembrance of the Lichdragon -- FORTISSAX, the fight the dream contains",
}

# REVIEWED AND RULED OUT, recorded so nobody re-adds them (Alaric, live-game, 2026-07-28). Both sit
# beside Fia's awards in the Deeproot listing, and proximity is not membership:
#
#   f510350  [Sorcery] Fia's Mist -- the drop from FIA'S CHAMPIONS, an ordinary fight you can reach
#            by warping to the nearby grace. It was tagged for a few minutes on the assumption that
#            "Fia's" meant the questline; it does not, and that is exactly the mistake this constant
#            exists to stop. THE DISCRIMINATOR FOR THIS WHOLE CLASS IS NOT "quest-adjacent", IT IS
#            "the fight does not exist until a questline creates it" -- a boss you can warp to and
#            hit is reachable the moment its region Lock lights the graces.
#   f540660  Ash of War: Golden Land -- an ordinary pickup.
NOT_DEATHBED_DREAM_FLAGS = {510350: "Fia's Mist (drop of Fia's Champions -- warp to the grace)",
                            540660: "Ash of War: Golden Land"}

# The item the whole cluster hangs on. Named here (not derived) ON PURPOSE: this is the motivating
# case, and the assertion below is that the DERIVED key-item set covers it -- if it stops covering
# it, the derivation regressed and the seed is strandable again.
PREREQUISITE_ITEM = "Cursemark of Death"


def _flag_to_ap():
    out = {}
    for locs in LOCATIONS.values():
        for (_name, ap_id, flag) in locs:
            out.setdefault(flag, ap_id)
    return out


class DeathbedDreamCluster(unittest.TestCase):
    def test_every_cluster_member_that_is_a_check_is_missable(self):
        f2a = _flag_to_ap()
        untagged = []
        for flag, what in sorted(DEATHBED_DREAM_FLAGS.items()):
            ap = f2a.get(flag)
            if ap is None:
                continue                      # not emitted as a check in this build -- nothing to tag
            if ap not in MISSABLE_LOCATIONS:
                untagged.append(f"f{flag} (ap {ap}) -- {what}")
        self.assertFalse(untagged,
                         "quest-gated check(s) can host REQUIRED progression:\n  "
                         + "\n  ".join(untagged)
                         + "\n(if this is the only failure, gen_data.py is fixed and the generated "
                           "table is stale: run build.ps1 -Greenfield)")

    def test_the_cluster_has_not_swallowed_its_neighbours(self):
        """A missable tag costs a filler slot, so the set must stay a claim about the QUESTLINE and
        not drift into 'everything near Fia'. These were reviewed and ruled OUT."""
        f2a = _flag_to_ap()
        wrong = [f"f{flag} ({what})" for flag, what in sorted(NOT_DEATHBED_DREAM_FLAGS.items())
                 if f2a.get(flag) in MISSABLE_LOCATIONS]
        self.assertFalse(wrong, "reviewed-OUT check(s) got tagged questline-missable: "
                                + ", ".join(wrong))

    def test_the_fight_is_on_the_surface_fill_steers_toward(self):
        """WHY the tag is load-bearing rather than belt-and-braces: the Fortissax reward carries
        MajorBoss+Remembrance, so it is inside the DEFAULT progression surface -- the small set
        features/progression_surface confines this world's region Locks to. If this ever stops being
        true the tag is still correct, but the exposure it removes is smaller than it was."""
        f2a = _flag_to_ap()
        ap = f2a.get(510110)
        self.assertIsNotNone(ap, "the Fortissax remembrance is not an emitted check any more")
        self.assertIn("MajorBoss", LOCATION_TAGS.get(ap, ()),
                      "Fortissax lost its MajorBoss tag -- re-read the surface exposure argument")
        surface = allowed_ap_ids(LOCATION_TAGS, SURFACE_DEFAULT_CLASSES,
                                 defaulted=DEFAULTED_REGION_APS)
        self.assertIn(ap, surface,
                      "the default progression surface no longer includes the Fortissax reward")


class KeyItemsSurviveTheFillerTail(unittest.TestCase):
    def test_key_item_set_is_present_and_bounded(self):
        """Derived from EquipParamGoods.goodsType == 1 by gen_data. Empty = a pre-regen item_ids.py,
        and the junk predicate silently reverts to the behaviour that deleted the Cursemark."""
        n = len(fc._KEY_ITEM_GOODS)
        self.assertGreater(n, 0,
                           "item_ids.KEY_ITEM_GOODS is absent/empty -- key items are displaceable "
                           "junk again. Run build.ps1 -Greenfield.")
        # An upper bound, not a pin: goodsType 1 is an inventory TAB, and if it turns out to cover
        # hundreds of items the pool shape changed far more than this fix intends and that should be
        # argued about, not shipped quietly.
        self.assertLess(n, 300,
                        f"KEY_ITEM_GOODS holds {n} items -- goodsType 1 is broader than the ~40 keys "
                        "this fix assumed; narrow the derivation rather than reinstating a hand list")

    def test_the_prerequisite_item_is_not_junk(self):
        self.assertFalse(fc._is_junk_consumable(PREREQUISITE_ITEM),
                         f"{PREREQUISITE_ITEM!r} is junk-classified, so the filler allocator may "
                         "overwrite it and Fia's questline becomes uncompletable in every seed")

    def test_no_keyitem_tagged_check_pays_a_displaceable_item(self):
        """The class, not the case: every check the world tags KeyItem hands over a gate/travel key.
        None of those may be displaceable, or the key can be deleted from the pool while the door it
        opens stays in logic."""
        from worlds.eldenring.item_ids import LOCATION_ITEM

        class _Filler:
            """A world whose classification promotes NOTHING -- the worst case. features/
            legacy_key_gates saves some of these by promoting them to progression, and relying on
            that would hide the ones it does not promote."""
            def _class_for(self, _name):
                from BaseClasses import ItemClassification
                return ItemClassification.filler

        bad = []
        for ap, tags in LOCATION_TAGS.items():
            if "KeyItem" not in tags:
                continue
            nm = LOCATION_ITEM.get(ap)
            if nm and fc.displaceable_filler(_Filler(), nm):
                bad.append(f"{nm} (ap {ap})")
        self.assertFalse(bad, "KeyItem checks pay displaceable items: " + ", ".join(sorted(bad)))


class FortissaxRejectsProgression(WorldTestBase):
    """The acceptance test, at fill level: the reported seed placed a region Lock here."""
    game = GAME
    options = {"item_shuffle": True}

    def test_location_rejects_advancement(self):
        f2a = _flag_to_ap()
        ap = f2a.get(510110)
        loc = next((l for l in self.multiworld.get_locations(self.world.player)
                    if getattr(l, "address", None) == ap), None)
        if loc is None:
            self.skipTest("Deeproot Depths is not a kept region in the default option set")
        # world_items, not itempool: pre_fill has already PLACED this world's own progression
        # (progression_surface) and precollected the start anchor, so the pool no longer holds them.
        prog = next((i for i in world_items(self)
                     if i.player == self.world.player and i.advancement), None)
        self.assertIsNotNone(prog, "expected an advancement item in the pool")
        self.assertFalse(loc.item_rule(prog),
                         "the Fortissax reward accepts a progression item -- the 2026-07-27 softlock")
        if loc.item is not None and loc.item.player == self.world.player:
            self.assertFalse(loc.item.advancement, "progression was PLACED on the Fortissax reward")


_PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _rows(name):
    """A committed greenfield tsv, installed beside the package by tools/gf_test.py. Skips loudly if
    it is absent -- an oracle with no input asserts nothing, which reads exactly like a pass."""
    path = os.path.join(_PKG, name)
    if not os.path.isfile(path):
        pytest.skip("%s not installed beside the package -- this oracle would run BLIND" % name)
    with open(path, encoding="utf-8-sig", newline="") as fh:
        yield from csv.DictReader(
            (ln for ln in fh if not ln.lstrip().startswith("#")), delimiter="\t")


class EsdGiftHandovers(unittest.TestCase):
    """The keeper for gen_data._ESD_GIFT_GATED: re-derive the join here, so the set cannot rot into a
    frozen list. An NPC dialogue handover exists only while that NPC is alive and in that state; the
    region-lock model calls the check reachable the moment its region opens."""

    def _gift_check_aps(self):
        lot2flag = {}
        for r in _rows("flag_lots.tsv"):
            if (r.get("table") or "").strip() != "map":
                continue
            try:
                lot2flag.setdefault(int(r["lot"]), int(r["flag"]))
            except (KeyError, TypeError, ValueError):
                continue
        f2a = _flag_to_ap()
        out = {}
        for r in _rows("esd_gifts.tsv"):
            try:
                lot = int((r.get("item_lot") or "").strip())
            except (TypeError, ValueError):
                continue
            ap = f2a.get(lot2flag.get(lot))
            if ap is not None:
                out[ap] = lot
        return out

    def test_the_join_still_lands_on_checks(self):
        """A join that silently yields nothing is the failure mode here (the tsvs open with a comment
        block, so a DictReader over the raw handle reads a `#` line as its header and returns zero
        rows). A FLOOR, not a pin: more is fine, a collapse is the bug."""
        self.assertGreaterEqual(len(self._gift_check_aps()), 40,
                                "the esd_gifts lot->flag->check join collapsed -- it landed on 48 "
                                "live checks when it was written")

    def test_every_dialogue_handover_is_missable(self):
        untagged = sorted(ap for ap in self._gift_check_aps() if ap not in MISSABLE_LOCATIONS)
        self.assertFalse(untagged,
                         "%d NPC-handover check(s) can host REQUIRED progression: %s\n(gen_data is "
                         "fixed and the generated table is stale: run build.ps1 -Greenfield)"
                         % (len(untagged), untagged[:12]))


class SurfaceCountsOnlyHostableChecks(WorldTestBase):
    """A missable check cannot accept an advancement item, so it is not surface. It was counted
    anyway until 2026-07-28, and Deeproot Depths is where that stopped being cosmetic: its ONLY
    surface member is the Fortissax reward."""
    game = GAME
    options = {"item_shuffle": True}

    def test_missable_is_barred_from_the_surface(self):
        from worlds.eldenring.features.progression_surface import (
            _world_barred_aps, missable_barred_aps, allowed_ap_ids)
        barred = _world_barred_aps(self.world)
        self.assertTrue(missable_barred_aps(self.world),
                        "the missable guard is on by default -- its set should be non-empty")
        surface = allowed_ap_ids(LOCATION_TAGS, SURFACE_DEFAULT_CLASSES, defaulted=barred)
        leaked = sorted(set(surface) & set(MISSABLE_LOCATIONS))
        self.assertFalse(leaked, f"missable checks counted as surface: {leaked}")

    def test_a_region_is_not_anchor_eligible_on_an_unhostable_boss(self):
        """regions_with_major_boss decides strict-mode sphere-0 anchor eligibility. Deeproot Depths'
        only MajorBoss check is the Fortissax reward; once that is tagged the region hosts nothing,
        and saying otherwise is how a claim outlives the check it was built on."""
        from worlds.eldenring.features.progression_surface import (
            _world_barred_aps, regions_with_major_boss)
        from worlds.eldenring.data import LOCATIONS as _LOCS
        barred = _world_barred_aps(self.world)
        eligible = regions_with_major_boss(list(_LOCS), barred=barred)
        f2a = _flag_to_ap()
        if f2a.get(510110) not in MISSABLE_LOCATIONS:
            self.skipTest("pre-regen table: the Fortissax reward is not tagged yet")
        self.assertNotIn("Deeproot Depths", eligible,
                         "Deeproot Depths is still anchor-eligible on a check no Lock can land on")

    def test_turning_the_guard_off_gives_the_surface_back(self):
        """The option means what it says: `protect_missable_locations` off is a deliberate 'I accept
        questline requirements', and then these checks really can host progression."""
        from worlds.eldenring.features.progression_surface import missable_barred_aps

        class _Off:
            class options:
                class protect_missable_locations:
                    value = 0
        self.assertFalse(missable_barred_aps(_Off()))
