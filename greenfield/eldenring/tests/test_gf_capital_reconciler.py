"""Capital-version reconciler (features/capital.py; SPEC-capital-reconciler.md).

Ground truth (elden_ring_artifacts, 2026-07-14): flag 9116 selects which Leyndell loads (OFF =
Royal m11_00 / bucket 11000, ON = Ashen m11_05 / 11050 + Elden Throne m19 / 19000); its sole
vanilla setter is Maliketh's death (m13_00_00_00.emevd:409); common.emevd $Event(900) runs the
burn and latches 118 last. The client reconciles 9116 to the player's current/target capital, so
the burn never permanently strands the Royal checks -- and while the option is ON, the
ERDTREE_BURN_APS "may not carry progression" bar is LIFTED (the strand it guarded is gone).
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring import contract  # noqa: E402
from worlds.eldenring.features.capital import (  # noqa: E402
    BURN_FLAG, BURN_DONE_FLAG, RELEASE_ROWS, capital_partition,
    _FALLBACK_BURN_FLAG, _FALLBACK_BURN_DONE_FLAG, _FALLBACK_RELEASE_ROWS)
from worlds.eldenring.region_play_ids import REGION_PLAY_IDS  # noqa: E402
from worlds.eldenring.location_tags import (  # noqa: E402
    ERDTREE_BURN_APS, DEFAULTED_REGION_APS, SHOP_RELEASE_GATED_APS)
from worlds.eldenring.data import LOCATIONS, FINALE_REGION  # noqa: E402
from worlds.eldenring.missable_locations import MISSABLE_LOCATIONS  # noqa: E402

GAME = "Elden Ring"

# The measured truth this feature partitions (region_play_ids.py). A change here is a change to
# the capital's kick geometry and must be classified consciously in capital_partition.
# NOTE the numbers did NOT move on 2026-08-06: SPEC-ashen-capital-lock re-homed 11050/19000 from
# Leyndell to the Ashen Capital, but the reconciler's Royal/Ashen answer is bit-for-bit what it
# always was -- which is the point of partitioning the union rather than one region's list.
_EXPECTED_ROYAL = [11000]
_EXPECTED_ASHEN = [11050, 19000]


class TestCapitalPartition:
    def test_live_table_partitions_exactly(self):
        royal, ashen = capital_partition()
        assert (royal, ashen) == (_EXPECTED_ROYAL, _EXPECTED_ASHEN)
        # ...and the partition really is over the GENERATED buckets, not a copy. It read
        # REGION_PLAY_IDS["Leyndell"] alone until SPEC-ashen-capital-lock (2026-08-06) moved 11050
        # and 19000 into the Ashen Capital's own entry, because the finale stopped borrowing the
        # capital's lock for its kick geometry. capital_partition() reads the UNION of the two, so
        # the source-of-truth assertion is the union -- and the two sides of the partition are
        # exactly the two regions' bucket lists, which is the split itself, pinned:
        assert set(royal) | set(ashen) == set(REGION_PLAY_IDS["Leyndell"]) | set(
            REGION_PLAY_IDS[FINALE_REGION])
        assert set(royal) == set(REGION_PLAY_IDS["Leyndell"])
        assert set(ashen) == set(REGION_PLAY_IDS[FINALE_REGION])

    def test_unclaimed_bucket_fails_generation(self):
        # A future regen adding an m11 bucket the rule doesn't claim must DIE, not default --
        # a silently dropped bucket is a latch that is permissive exactly there.
        with pytest.raises(contract.ContractError):
            capital_partition([11000, 11050, 19000, 11200])

    def test_empty_side_fails_generation(self):
        with pytest.raises(contract.ContractError):
            capital_partition([11050, 19000])  # no Royal side
        with pytest.raises(contract.ContractError):
            capital_partition([11000])         # no Ashen side


class TestCapitalPins:
    def test_flags_are_the_derived_ground_truth(self):
        assert BURN_FLAG == 9116      # m13_00_00_00.emevd:409, the only setter in 589 EMEVD
        assert BURN_DONE_FLAG == 118  # $Event(900) completion latch, monotonic

    def test_generated_data_and_fallbacks_agree(self):
        """Once gen_data emits CAPITAL_* into data.py, the pinned fallbacks must EQUAL the
        generated values -- a fallback that drifts from the derivation is a lie about why the
        code works and must fail, not linger (CONTRIBUTING: redundant manual override)."""
        try:
            from worlds.eldenring.data import (CAPITAL_BURN_FLAG, CAPITAL_BURN_DONE_FLAG,
                                               CAPITAL_RELEASE_ROWS)
        except ImportError:
            pytest.skip("data.py predates the capital regen (fallbacks are the live values)")
        assert CAPITAL_BURN_FLAG == _FALLBACK_BURN_FLAG
        assert CAPITAL_BURN_DONE_FLAG == _FALLBACK_BURN_DONE_FLAG
        assert tuple(tuple(r) for r in CAPITAL_RELEASE_ROWS) == _FALLBACK_RELEASE_ROWS

    def test_release_rows_rekey_live_checks_to_the_done_latch(self):
        # Every re-keyed row moves 9116 -> 118, and its stock flag is a REAL check in the world
        # data (Enia's Maliketh armor set): flags 250160/250170/250180/250190.
        assert all(frm == BURN_FLAG and to == BURN_DONE_FLAG for (_r, frm, to) in RELEASE_ROWS)
        assert [r for (r, _f, _t) in RELEASE_ROWS] == [101516, 101517, 101518, 101519]
        all_flags = {f for locs in LOCATIONS.values() for (_n, _a, f) in locs}
        for stock in (250160, 250170, 250180, 250190):
            assert stock in all_flags, f"stock flag {stock} is not a live check -- re-key stale"


class CapitalOnSeed(WorldTestBase):
    """Default (option ON), num_regions 0 = every region kept: the slot_data wire is emitted and
    the Royal Capital may carry progression again."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 0}

    def test_slot_data_wire(self):
        sd = self.world.fill_slot_data()
        assert sd["capitalBurnFlag"] == 9116
        assert sd["capitalBurnDoneFlag"] == 118
        assert sd["capitalAshenPlayRegions"] == _EXPECTED_ASHEN
        assert sd["capitalRoyalPlayRegions"] == _EXPECTED_ROYAL
        assert sd["capitalReleaseRows"] == [[101516, 9116, 118], [101517, 9116, 118],
                                            [101518, 9116, 118], [101519, 9116, 118]]

    def _royal_plain_location(self):
        """A created m11_00 check barred ONLY by the burn strand, so its item_rule isolates the
        carve-out.

        🛑 MISSABLE must be subtracted too, and forgetting it is why this test went red on
        2026-07-27. The predicate excluded defaulted and shop-gated locations but not missable
        ones; when the ESD talk-award corpus scoped in 18 more gesture checks, four of them landed
        in ERDTREE_BURN_APS as `questline` missables (f60805 My Lord, f60830, f60841, f60848) and
        iteration order handed this test one of them. It then asserted the BURN carve-out against a
        location barred by the MISSABLE rule and failed -- a true statement about the wrong
        location. 6 of the 145 burn candidates are missable; 139 remain, so the premise is in no
        danger of running out.
        """
        plain = (set(ERDTREE_BURN_APS) - set(DEFAULTED_REGION_APS)
                 - set(SHOP_RELEASE_GATED_APS) - set(MISSABLE_LOCATIONS))
        for loc in self.multiworld.get_locations(self.player):
            if getattr(loc, "address", None) in plain:
                return loc
        pytest.fail("no plain ERDTREE_BURN location created (premise broken: Leyndell not kept?)")

    def _royal_plain_location_on_surface(self, on_surface):
        """A plain burn location that IS / IS NOT on this seed's progression surface.

        The two rules that can refuse an own Region Lock here are independent, and this test exists
        to isolate exactly one of them. Returns None if the seed has no such location, which the
        caller must treat as "premise absent", not as a pass."""
        plain = (set(ERDTREE_BURN_APS) - set(DEFAULTED_REGION_APS)
                 - set(SHOP_RELEASE_GATED_APS) - set(MISSABLE_LOCATIONS))
        surf = set(getattr(self.world, "_foreign_confine_surface", None) or ())
        for loc in self.multiworld.get_locations(self.player):
            ap = getattr(loc, "address", None)
            if ap in plain and ((ap in surf) == on_surface):
                return loc
        return None

    def test_royal_capital_may_carry_progression_where_the_surface_allows_it(self):
        """The burn-strand carve-out, isolated.

        🛑 NARROWED 2026-08-09 (er-archipelago#491). This used to probe ANY plain burn location with
        a Region Lock and assert the rule permits. `progression_bias` made that false: a released
        Lock is held to the progression surface, so a burn location OFF the surface now refuses it --
        for a completely different reason than the burn strand. Alaric's ruling: the old invariant is
        "false by design, only true when royal capital is in the progression surface, which it need
        not be."

        So the probe moves ONTO the surface, where the lock rule permits and only the burn bar could
        still refuse. The companion below asserts the other half, so the pair states the whole
        ruling instead of quietly dropping the case that changed."""
        loc = self._royal_plain_location_on_surface(True)
        if loc is None:
            pytest.skip("this seed kept no plain ERDTREE_BURN location on the surface")
        prog = self.world.create_item("Farum Azula Lock")  # any own advancement item
        assert prog.advancement
        assert loc.item_rule(prog), \
            f"{loc.name}: reconciler ON must lift the burn-strand progression bar"

    def test_a_released_lock_is_refused_off_the_surface_and_that_is_the_bias_not_the_burn(self):
        """The other half of the ruling, and the reason the test above had to move.

        A plain burn location OFF the surface refuses a RELEASED Lock. That refusal must come from
        progression_bias, not from the burn strand -- so the same location is asserted to accept an
        own advancement item the bias never touched. Without that second assertion this test would
        pass just as happily if the reconciler had silently stopped lifting the burn bar."""
        loc = self._royal_plain_location_on_surface(False)
        if loc is None:
            pytest.skip("this seed kept no plain ERDTREE_BURN location off the surface")
        released = set(getattr(self.world, "gf_locks_released_set", ()) or ())
        if not released:
            pytest.skip("no Lock was released this seed (progression_bias 100?)")
        lock = self.world.create_item(sorted(released)[0])
        assert not loc.item_rule(lock), \
            f"{loc.name}: a RELEASED Lock must be refused off the surface"
        # WITNESS that the burn bar is still lifted -- otherwise the refusal above proves nothing
        # about WHICH rule fired.
        other = self.world.create_item("Rune")
        assert loc.item_rule(other), \
            f"{loc.name}: the burn-strand bar must still be lifted for everything else"

    def test_reconciler_flag_published_for_features(self):
        assert self.world.gf_capital_reconciler is True


class CapitalOffSeed(WorldTestBase):
    """capital_reconciler: false -- the one-flag disable. No wire, and the vanilla one-way burn
    means the ERDTREE_BURN progression bar snaps back (seeds stay winnable without the client)."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 0, "capital_reconciler": False}

    def test_no_wire(self):
        sd = self.world.fill_slot_data()
        # All SEVEN. The two world-state keys joined the family on 2026-08-06
        # (SPEC-ashen-capital-lock) and ride the same off-wire: features/capital.slot_data returns
        # {} outright, so absence is a property of the option, not of each key.
        for key in ("capitalBurnFlag", "capitalBurnDoneFlag", "capitalAshenPlayRegions",
                    "capitalRoyalPlayRegions", "capitalReleaseRows",
                    "capitalWorldBurnFlag", "capitalPreBurnFlag"):
            assert key not in sd, f"{key} emitted with the reconciler off"

    def test_royal_capital_progression_bar_restored(self):
        # Same subtraction as CapitalOnSeed._royal_plain_location, and for a sharper reason: this
        # test asserts the bar IS up, so a missable location would satisfy it via the MISSABLE
        # rule and pass while the burn strand was broken. Excluding them keeps the assertion about
        # the burn strand and nothing else.
        plain = (set(ERDTREE_BURN_APS) - set(DEFAULTED_REGION_APS)
                 - set(SHOP_RELEASE_GATED_APS) - set(MISSABLE_LOCATIONS))
        locs = [l for l in self.multiworld.get_locations(self.player)
                if getattr(l, "address", None) in plain]
        assert locs, "premise broken: no plain ERDTREE_BURN location created"
        prog = self.world.create_item("Farum Azula Lock")
        for loc in locs:
            assert not loc.item_rule(prog), \
                f"{loc.name}: with the reconciler OFF the burn strand is real -- no progression"

    def test_off_still_fills(self):
        # the off-path is a shipping configuration, not a dead branch: it must gen clean.
        assert self.world.gf_capital_reconciler is False


class CapitalRolledSeed(WorldTestBase):
    """A locked seed (num_regions pinned, rolled order): the wire is emitted regardless of which
    regions were kept -- the reconciler defends even seeds whose Leyndell rolled sealed (the
    player can still burn on open-world configs, and the sets are static geometry)."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 4}

    def test_wire_present_on_rolled_seed(self):
        sd = self.world.fill_slot_data()
        assert sd.get("capitalBurnFlag") == 9116
        assert sd.get("capitalAshenPlayRegions") == _EXPECTED_ASHEN
