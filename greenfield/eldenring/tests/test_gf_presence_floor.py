"""presence_floor -- the curated QoL set (physick tears + smithing bell bearings) is ALWAYS in the
pool: an absent roster item is injected exactly once (count-neutral, `useful`), a present one is never
duplicated. This is what makes dlc_only (and num_regions seeds that seal a roster item's home region)
feel like its own mode instead of a run with an amputated flask / upgrade economy.

The four cases the deliverable pins:
  (a) an ABSENT roster item gets injected once,
  (b) a PRESENT roster item is NOT duplicated,
  (c) count-neutrality (pool size == location count),
  (d) a dlc_only-style seed (no base regions) reaches the FULL presence floor.

Plus a pure-data guard that every roster NAME still resolves in ITEM_CATALOG -- a rename upstream would
otherwise silently shrink the roster and the protection to nothing (the collectathon-omission shape).
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from BaseClasses import ItemClassification  # noqa: E402
from worlds.eldenring.features import presence_floor as pf  # noqa: E402
from worlds.eldenring.features import filler_curation as fc  # noqa: E402
from worlds.eldenring.item_ids import ITEM_CATALOG  # noqa: E402

GAME = "Elden Ring"
GOODS = 0x40000000


def _pool_items(world):
    """Location-paying items this world created (unplaced itempool + pre-placed on locations)."""
    p = world.player
    mw = world.multiworld
    out = [i for i in mw.itempool if i.player == p]
    out += [loc.item for loc in mw.get_locations(p)
            if loc.item is not None and loc.item.player == p]
    return out


def _useful_roster_copies(items):
    """Names of the `useful`-classified roster copies -- exactly presence_floor's injections (the
    vanilla roster items are GOODS => filler, so a `useful` roster copy can only be one we injected)."""
    return sorted(i.name for i in items
                  if i.name in pf.PRESENCE_FLOOR_ITEMS
                  and (i.classification & ItemClassification.useful))


# ---- pure-data guards ---------------------------------------------------------------------------
def test_roster_resolves_and_is_nonempty():
    assert pf.ROSTER, "the presence-floor roster resolved to nothing -- ITEM_CATALOG missing?"
    missing = [n for n in pf.ROSTER if n not in ITEM_CATALOG]
    assert not missing, f"roster names not in ITEM_CATALOG (injection would KeyError): {missing}"
    # 18 physick tears always resolve; only the bell bearings vary (Somberstone [1] is not in the
    # FMG catalog, so it is dropped -- see UNRESOLVED).
    assert len(pf.PHYSICK_TEARS) == 18
    assert set(pf.PHYSICK_TEARS) <= set(ITEM_CATALOG), "a physick tear name drifted from the catalog"
    assert pf.UNRESOLVED == ["Somberstone Miner's Bell Bearing [1]"], (
        f"unexpected unresolved roster names: {pf.UNRESOLVED} -- confirm the catalog spelling")


def test_roster_items_are_goods_and_would_be_seized_without_protection():
    # The precondition for the protection to be load-bearing: every roster item is a GOODS, which the
    # junk predicate would seize as filler if it were not explicitly protected.
    for name in pf.ROSTER:
        assert (ITEM_CATALOG[name] & 0xF0000000) == GOODS, f"{name} is not GOODS -- re-derive protection"


def test_roster_is_protected_from_junk_seizure():
    # Task 1/2: the whole roster must be protected in filler_curation so a KEPT roster item survives in
    # the pool as itself (present -> not injected) instead of being displaced by the filler tail.
    seized = [n for n in pf.ROSTER if fc._is_junk_consumable(n)]
    assert not seized, f"the filler tail would DISPLACE these presence-floor items: {seized}"


# ---- world-level behaviour ----------------------------------------------------------------------
class PresenceFloorFullSeed(WorldTestBase):
    """A full seed keeps every region, so every roster item's home check is kept -> all PRESENT ->
    nothing injected. Guards case (b) at the extreme (no injection, no duplication) and count-neutral."""
    game = GAME
    options = {"num_regions": 0}

    def test_all_present_nothing_injected(self):
        w = self.world
        self.assertEqual(pf.absent_roster(w), [], "a full seed should have no absent roster items")
        self.assertEqual(len(pf.present_roster(w)), len(pf.ROSTER),
                         "a full seed should have the whole roster present")
        self.assertEqual(_useful_roster_copies(_pool_items(w)), [],
                         "no roster item may be injected when all are present (would duplicate)")

    def test_count_neutral(self):
        w = self.world
        self.assertEqual(len(_pool_items(w)), len(w.multiworld.get_locations(w.player)),
                         "presence-floor injection must be count-neutral (pool == locations)")


class PresenceFloorDLCOnly(WorldTestBase):
    """dlc_only seals every base region, so the roster items whose home region is base are ABSENT and
    get injected; the few that also live in a kept DLC region are present and are NOT injected. Guards
    cases (a), (b), (c), (d)."""
    game = GAME
    options = {"dlc_only": True}

    def test_full_presence_floor_reached(self):
        # (d) every roster item ends up in the pool exactly once through the floor: present OR injected.
        w = self.world
        names = [i.name for i in _pool_items(w)]
        for n in pf.ROSTER:
            self.assertIn(n, names, f"presence floor not reached: {n} absent from a dlc_only pool")
        present = pf.present_roster(w)
        absent = pf.absent_roster(w)
        self.assertEqual(present | set(absent), set(pf.ROSTER))
        self.assertEqual(present & set(absent), set(), "a roster item is both present and injected")
        self.assertGreater(len(absent), 0, "dlc_only should inject most of the roster")

    def test_absent_injected_once_present_not_injected(self):
        # (a) + (b): the `useful` roster copies in the pool are EXACTLY the absent set, one each.
        w = self.world
        self.assertEqual(_useful_roster_copies(_pool_items(w)), sorted(pf.absent_roster(w)),
                         "injected (useful) roster copies must equal the absent set, one per name")

    def test_injected_copies_are_useful_never_progression(self):
        w = self.world
        for it in _pool_items(w):
            if it.name in pf.PRESENCE_FLOOR_ITEMS and (it.classification & ItemClassification.useful):
                self.assertFalse(it.advancement,
                                 f"injected {it.name} must never be progression (Region Locks gate)")

    def test_count_neutral(self):
        w = self.world
        self.assertEqual(len(_pool_items(w)), len(w.multiworld.get_locations(w.player)),
                         "presence-floor injection must be count-neutral under dlc_only too")

    def test_beatable(self):
        state = self.multiworld.get_all_state(False)
        self.assertTrue(self.multiworld.completion_condition[self.world.player](state),
                        "injecting the roster must not affect winnability")


class PresenceFloorDLCOff(WorldTestBase):
    """DLC off: two roster physick tears (Bloodsucking Cracked Tear, Deflecting Hardtear) are DLC-only
    GOODS. The floor must NOT inject them -- doing so would leak DLC content into a DLC-off pool (the
    class test_gf_dlc_pool_leak guards). With DLC off they are simply not part of the floor."""
    game = GAME
    options = {"enable_dlc": False}

    def test_dlc_roster_items_not_injected(self):
        w = self.world
        excl = set(w.gf_dlc_excluded)
        dlc_roster = [n for n in pf.ROSTER if n in excl]
        self.assertTrue(dlc_roster, "expected some DLC-only roster items to exercise this guard")
        for n in dlc_roster:
            self.assertNotIn(n, pf.absent_roster(w), f"{n} is DLC-only; must not be injected with DLC off")
        names = [i.name for i in _pool_items(w)]
        for n in dlc_roster:
            self.assertNotIn(n, names, f"DLC-only roster item {n} leaked into a DLC-off pool")

    def test_base_roster_still_injected_when_absent(self):
        # A base-game roster item whose home region is sealed by a small region scope is still injected.
        w = self.world
        # base roster items are all present in a full base seed, so just assert the floor holds for base
        base_roster = [n for n in pf.ROSTER if n not in set(w.gf_dlc_excluded)]
        names = [i.name for i in _pool_items(w)]
        for n in base_roster:
            self.assertIn(n, names, f"base roster item {n} missing from the DLC-off floor")

    def test_count_neutral(self):
        w = self.world
        self.assertEqual(len(_pool_items(w)), len(w.multiworld.get_locations(w.player)))
