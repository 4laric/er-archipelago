"""Dedicated spell vendors are keyed on the MERCHANT (talk ESD), never the ShopLineupParam 100-block.

MOTIVATING CASE (rule 11, 2026-08-05). A player reported a Limgrave Lock -- our own progression -- on
`Caelid :: [Sorcery] Night Shard - from Sage Gowry [f110750]` (ap 7770249), a check behind Gowry's
questline: his talk ESD gates the whole shop range on flag 4167, "NPC349 Corrupt Elder_Character
state transition". Gowry sells FOUR checks and every one is a spell, yet he was tagged ShopNonSpell
AND pinned as a ShopSlot -- because "dedicated spell vendor" was measured over the ShopLineupParam
100-BLOCK. His rows are 1001xx, so his spells scored against block 1001, the Twin Maiden Husks hub
block (6/24 spells = 25%), and a 100%-spell merchant inherited a general store's ratio.

WHY A DERIVED POPULATION rather than four pinned ap-ids: the gate is on the MERCHANT, and a literal
list drifts the moment his stock changes. Every assertion re-derives merchant -> stock from the
committed tables (merchant_shops.tsv joined to shop_data.SHOP_ROW_IDS), so a regression re-opens the
hole loudly instead of quietly agreeing with a stale constant.

AND THE SPY. test_spy_block_keying_would_still_misclassify_gowry keeps this file from going vacuous:
it asserts Gowry's BLOCK is still majority-non-spell, i.e. the retired rule would STILL get him
wrong. If someone reverts the keying, the tests above fail while the spy passes. If the underlying
data ever shifts so the old rule would have caught him anyway, the spy fails and tells you this file
has stopped guarding the thing it claims to guard.
"""
import ast
import importlib.util
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:                                        # direct/unittest fallback
    sys.path.insert(0, HERE)
    from _util import find_repo_root, REPO_ONLY_REASON

_ROOT = find_repo_root(HERE)
pytestmark = pytest.mark.skipif(_ROOT is None, reason=REPO_ONLY_REASON)

GOWRY = "349006000"          # Sage Gowry's talk ESD
D_HUNTER = "319006000"       # D, Hunter of the Dead -- the other merchant the re-key drops
GOWRY_AP = 7770249           # the reported check: [Sorcery] Night Shard
GOWRY_BLOCK = 1001           # the hub block his rows live in -- the source of the old bug
HUB_TILE = "m11_10"          # Twin Maiden Husks: a mirror, never a competing seller
_SPELL = re.compile(r"\[(Sorcery|Incantation)\]", re.I)


def _gf(*parts):
    return os.path.join(_ROOT, "greenfield", *parts)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tags():
    return _load("_gf_location_tags_under_test", _gf("eldenring", "location_tags.py"))


def _shop_row_ids():
    return _load("_gf_shop_data_under_test", _gf("eldenring", "shop_data.py")).SHOP_ROW_IDS


def _names():
    """ap -> location name. The name carries the [Sorcery]/[Incantation] prefix; the canonical item
    name does not (_resolve_item strips it), which is why the raw name is the only complete signal."""
    src = open(_gf("eldenring", "data.py"), encoding="utf-8").read()
    pat = r"\(\s*('(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\")\s*,\s*(\d+)\s*,\s*(\d+)\s*\)"
    return {int(m.group(2)): ast.literal_eval(m.group(1)) for m in re.finditer(pat, src)}


def _merchant_stock():
    """talk_id -> set of ap-ids it opens OUTSIDE the hub (the funnel's own _field_openers rule)."""
    row_talks, talk_maps = {}, {}
    for line in open(_gf("merchant_shops.tsv"), encoding="utf-8-sig"):
        q = line.rstrip("\n").split("\t")
        if len(q) < 5 or not q[0].isdigit():
            continue
        row_talks.setdefault(int(q[0]), set()).add(q[1])
        talk_maps.setdefault(q[1], set()).add(q[4].strip())
    stock = {}
    for aps, rows in _shop_row_ids().items():
        for row in rows:
            for talk in row_talks.get(row, ()):
                if any(m != HUB_TILE for m in talk_maps.get(talk, ())):
                    stock.setdefault(talk, set()).add(int(aps))
    assert stock, "merchant_shops.tsv joined to SHOP_ROW_IDS produced NOTHING -- inputs collapsed"
    return stock


def test_gowry_stock_is_entirely_spells():
    names = _names()
    stock = _merchant_stock().get(GOWRY, set())
    assert stock, "Sage Gowry opens no checks -- the join lost him, so the rest of this file is mute"
    non_spell = sorted(a for a in stock if not _SPELL.search(names.get(a, "")))
    assert not non_spell, (
        "Gowry is the motivating case precisely because his stock is 100%% spells; these are not: %r"
        % [(a, names.get(a)) for a in non_spell])
    assert GOWRY_AP in stock, "the reported check is no longer attributed to Gowry"


def test_gowry_holds_no_progression_slot():
    lt = _tags()
    assert GOWRY not in lt.SHOP_SLOT_PINS, (
        "Sage Gowry is pinned as a ShopSlot again -- a questline-gated spell vendor may not host "
        "this world's progression (ap %s was the reported Limgrave Lock)" % GOWRY_AP)
    assert "spell vendor" in lt.SHOP_SLOT_SKIPS.get(GOWRY, ""), (
        "Gowry must be SKIPPED with a stated reason, not silently absent from the funnel")
    tags = lt.LOCATION_TAGS.get(GOWRY_AP, [])
    assert "ShopSlot" not in tags and "ShopNonSpell" not in tags, (
        "ap %s still carries %r" % (GOWRY_AP, tags))


def test_d_hunter_of_the_dead_is_also_a_spell_vendor():
    """The re-key drops two merchants, not one; the second must not regress silently."""
    lt = _tags()
    assert D_HUNTER not in lt.SHOP_SLOT_PINS
    assert "spell vendor" in lt.SHOP_SLOT_SKIPS.get(D_HUNTER, "")


def test_no_pinned_merchant_sells_any_spell():
    """The general invariant -- zero tolerance, not a ratio. This is the rule; Gowry is one case."""
    names, stock, lt = _names(), _merchant_stock(), _tags()
    # WITNESS (test_gf_vacuous_pass): assert the scan SAW candidates in this function, not just in
    # the helper -- an empty pin set would otherwise satisfy the emptiness assertion below for
    # exactly the reason a correct implementation would.
    assert lt.SHOP_SLOT_PINS, "no ShopSlot pins at all -- this invariant would pass vacuously"
    offenders = {}
    for talk in lt.SHOP_SLOT_PINS:
        spells = sorted(a for a in stock.get(talk, set()) if _SPELL.search(names.get(a, "")))
        if spells:
            offenders[talk] = [(a, names.get(a)) for a in spells]
    assert not offenders, "pinned merchants that stock a spell: %r" % offenders


def test_spy_block_keying_would_still_misclassify_gowry():
    """Anti-vacuity: prove the retired 100-block rule still gets Gowry wrong, so the tests above are
    testing the fix rather than agreeing with data that fixed itself."""
    names, rows = _names(), _shop_row_ids()
    blocks = {}
    for aps, rw in rows.items():
        if rw:
            blocks.setdefault(rw[0] // 100, []).append(int(aps))
    members = blocks.get(GOWRY_BLOCK, [])
    assert members, "block %s vanished -- the spy can no longer prove anything" % GOWRY_BLOCK
    frac = sum(1 for a in members if _SPELL.search(names.get(a, ""))) / len(members)
    assert frac < 0.5, (
        "block %s is now majority-spell (%.2f), so the OLD rule would have caught Gowry too and "
        "this file no longer demonstrates the bug it was written for" % (GOWRY_BLOCK, frac))
    assert GOWRY_AP in members, "Gowry's reported check no longer sits in the hub block"
