"""Anchor test: merchant shop checks keep their PHYSICAL-merchant region (regression guard).

This is the backstop for the silent-revert hole (Fable review, 2026-07-23): the Altus Hermit + ~100
other merchant flags are region-corrected by the merchant-ESD derivation (gen_data._build_merchant_shop_
region, from greenfield/merchant_shops.tsv), and their FLAG_REGION_OVERRIDE hand-pins were RETIRED once
the derivation reproduced them. So if merchant_shops.tsv ever goes missing at regen, those flags silently
revert to their wrong ShopLineupParam-block region (the exact shipped bug: Hermit -> Liurnia -> sealed
out of any roll that drops Liurnia). gen_data now fails loud in that case, and this pins a few moved
anchors in the COMMITTED data so a reverted regen can never land green.

Loads the generated data.py by file path -- no Archipelago import, so it runs in CI and in the source
tree alike (it validates the shipped output, not a live world).
"""
import importlib.util
import os

import pytest

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data.py")

# flag -> expected region. Each is a merchant whose PHYSICAL location differs from its shop block's
# region and was verified against ground truth (grace / release-flag self-encoding) in the Fable review.
_ANCHORS = {
    170490: "Altus",    # Prophet Robe -- Hermit Merchant's Shack, tile m60_43_53 (grace 76311)
    66750:  "Altus",    # Perfume Bottle -- same Hermit; the original hand-pin, now derived
    180890: "Caelid",   # Beast-Repellent Torch -- Isolated Merchant's Shack, tile m60_48_41 (grace 76451)
    # ---- #556: the merchants whose tile resolved to NO region at all -------------------------------
    # m10_00 (Stormveil Castle) was the only legacy map absent from dungeon_regions.tsv, so Gostoc's
    # and Rogier's rows had zero resolved regions and fell to the block guess: Gostoc's stock was
    # labelled Kale's shack (Limgrave), Rogier's Ranni's Rise (Liurnia). Neither has ever set foot in
    # either place. These anchors are the OUTPUT half of the fix -- the rule half is in
    # test_gf_merchant_claimant_filters.py, and neither test can substitute for the other.
    100000: "Stormveil",   # Festering Bloody Finger -- Gatekeeper Gostoc, m10_00. Was Limgrave.
    100180: "Stormveil",   # Ancient Dragon Smithing Stone -- Gostoc, m10_00. Was Limgrave.
    120000: "Stormveil",   # Ash of War: Spinning Weapon -- Sorcerer Rogier, m10_00. Was Liurnia.
    120020: "Stormveil",   # Ash of War: Carian Greatsword -- Rogier, m10_00. Was Liurnia.
    # ---- #558: the rows an over-wide ESD range un-pinned ------------------------------------------
    # ⭐ boblerrr's 2026-08-11 seed KEPT Liurnia and still got an all-vanilla shelf from Nomadic
    # Merchant's Bell Bearing [5], whose merchant stands at m60_38_41 = Liurnia. Merchant Kale's
    # OpenRegularShop range over-runs his block into theirs, so the flag saw two regions, refused to
    # pin, and fell back to WEEPING -- a region neither claimant stands in.
    160330: "Liurnia",     # Estoc -- Nomadic Merchant m60_38_41. Was Weeping.
    160460: "Liurnia",     # Astrologer's Staff -- same merchant. Was Weeping.
    200250: "Liurnia",     # Smithing Stone [2] -- same merchant. Was Weeping.
}

# A merchant who never leaves one place cannot have stock in two regions. The flag anchors above pin
# four rows; this pins the WHOLE shelf by the name gen_data writes into the location, so a future
# regen cannot move the other eleven while the sampled four stay put.
_WHOLE_SHELF = {
    "from Gatekeeper Gostoc": {"Stormveil"},
    "from Sorcerer Rogier": {"Stormveil"},
}


def _load_data():
    if not os.path.isfile(_DATA):
        pytest.skip("generated data.py absent (not yet installed/regenerated)")
    spec = importlib.util.spec_from_file_location("gf_data_anchor", _DATA)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_merchant_flags_keep_physical_region():
    data = _load_data()
    flag2reg = {}
    for reg, locs in data.LOCATIONS.items():
        for (_name, _apid, flag) in locs:
            flag2reg[flag] = reg
    wrong = {fl: (flag2reg.get(fl), exp) for fl, exp in _ANCHORS.items() if flag2reg.get(fl) != exp}
    assert not wrong, (
        "merchant shop check(s) reverted off their physical-merchant region -- merchant_shops.tsv likely "
        "missing at the last regen, or the derivation broke. {flag: (got, expected)} = %r" % wrong)


def test_a_stationary_merchants_whole_shelf_is_in_one_region():
    """Sampling four flags cannot catch a partial revert. Gostoc is a gatekeeper and Rogier is in
    Stormveil then the Roundtable; neither sells anywhere else, so every location naming them must
    agree on one region."""
    data = _load_data()
    seen = {}
    for reg, locs in data.LOCATIONS.items():
        for (name, _apid, _flag) in locs:
            for needle in _WHOLE_SHELF:
                if needle in name:
                    seen.setdefault(needle, {}).setdefault(reg, []).append(name)
    for needle, expected in _WHOLE_SHELF.items():
        # WITNESS FIRST: an empty result would pass every assertion below it vacuously.
        assert needle in seen, (
            "no location in the shipped data.py names %r -- the shelf vanished, so this gate is "
            "asserting nothing. Find where the checks went before touching the expectation." % needle)
        got = set(seen[needle])
        assert got == expected, (
            "%r sells across %r, expected %r. Sample: %r"
            % (needle, sorted(got), sorted(expected),
               {r: v[:2] for r, v in seen[needle].items()}))
