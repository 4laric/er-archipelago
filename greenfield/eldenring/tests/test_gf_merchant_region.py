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
