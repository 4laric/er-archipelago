"""The rune ladder printed in the OPTION HELP must be the ladder the params publish.

WHY THIS EXISTS (2026-08-16). `KeepLocalRuneCap`'s docstring -- which is what a player reads in the
options UI, and which is copied verbatim into `release/EldenRing.yaml`, which is what a player reads
in their own yaml -- carried four wrong claims at once:

  * "0 (default) is OFF -- no rune is held back by this option", while the default was 12,500 and it
    held 18 of the 31 rune items;
  * a heading, "Why the default is 6250", left over from a ruling that moved to 12,500, arguing for
    6250 in a paragraph directly above a measurement paragraph that bolded 12,500;
  * a ladder off by one from [4] up -- "[4] 1,600, [8] 3,800, [10] 6,250, [13] 12,500" against the
    params' 1,200 / 3,000 / 5,000 / 10,000;
  * and therefore the wrong item named for the cap: 6,250 is Golden Rune [11], not [10], and 12,500
    is Numen's Rune, not Golden Rune [13].

None of it could fail. This is #707's shape -- prose that stopped describing the code -- in help
text rather than in a guard, and prose is exactly where this project has been bitten most.

🛑 THIS TEST TYPES NO PAYOUT. It reads every "<rune name> <number>" pair out of the prose and asks
the params whether that pairing is true. A test that listed the right numbers would just be a fifth
place for them to drift.
"""
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

pytest.importorskip("worlds.eldenring")
from worlds.eldenring.item_categories import rune_payout          # noqa: E402
from worlds.eldenring.features.local_items import KeepLocalRuneCap  # noqa: E402

_ROOT = find_repo_root(HERE)

# "Golden Rune [13]  10,000" / "Numen's Rune 12,500" / "Marika's Rune     80,000".
# Deliberately loose on whitespace and thousands separators -- the prose is laid out for humans.
_PAIR = re.compile(r"([A-Z][A-Za-z']*(?: Realm)? Rune(?: \[\d+\])?)\s+([\d,]{3,7})(?!\d)")


def _pairs(text):
    out = []
    for name, num in _PAIR.findall(text):
        payout = rune_payout(name)
        if payout is None:
            continue            # not a catalog rune item (e.g. prose about "Rune" the filler)
        out.append((name, int(num.replace(",", "")), payout))
    return out


def _check(text, where):
    pairs = _pairs(text)
    assert len(pairs) >= 5, (
        "%s: found only %d rune name/value pair(s) -- the ladder is gone or the layout changed, and "
        "a gate that matches nothing passes vacuously" % (where, len(pairs)))
    wrong = [(n, claimed, real) for n, claimed, real in pairs if claimed != real]
    assert not wrong, (
        "%s claims rune payouts the params disagree with: %s. The params are ground truth "
        "(EquipParamGoods.refId_default -> SpEffectParam.soul, via shop_stock_data.RUNE_PAYOUT); "
        "fix the prose, not the table." % (
            where, "; ".join("%s says %s, really %s" % (n, c, r) for n, c, r in wrong)))


def test_the_option_docstring_ladder_matches_the_params():
    _check(KeepLocalRuneCap.__doc__ or "", "KeepLocalRuneCap.__doc__")


def test_the_option_docstring_does_not_claim_the_default_is_off():
    """The single most misleading line: it told the player nothing was held while 18 items were.

    ⚠️ QUOTED SPANS ARE STRIPPED FIRST, and that is not a loophole. The corrected docstring QUOTES
    the old wrong line in its own correction note -- which is the right thing for it to do, and it
    tripped this gate on the first run. A live claim is made in the prose; a dead one is in quotes
    being described. Strip `"..."` and what is left is what the option is actually asserting."""
    doc = re.sub(r'"[^"]*"', " ", KeepLocalRuneCap.__doc__ or "").lower()
    assert "(default) is off" not in doc, (
        "the docstring says the default is OFF. The default is %s." % KeepLocalRuneCap.default)
    assert str(KeepLocalRuneCap.default) in doc.replace(",", ""), (
        "the docstring never states the actual default (%s)" % KeepLocalRuneCap.default)


@pytest.mark.skipif(_ROOT is None, reason=REPO_ONLY_REASON)
def test_the_shipped_yaml_ladder_matches_the_params():
    """The yaml is the copy players actually read, and it drifted in lockstep with the docstring."""
    path = os.path.join(_ROOT, "release", "EldenRing.yaml")
    if not os.path.isfile(path):
        pytest.skip("release/EldenRing.yaml not present")
    text = open(path, encoding="utf-8").read()
    block = text[text.find("keep_local_rune_cap") - 3000:text.find("keep_local_rune_cap") + 200]
    _check(block, "release/EldenRing.yaml (rune cap block)")


@pytest.mark.skipif(_ROOT is None, reason=REPO_ONLY_REASON)
def test_the_player_guide_states_the_actual_rune_cap_default():
    """The option tour repeated the old default-off claim after the option moved to 12,500."""
    path = os.path.join(_ROOT, "Elden-Ring-Archipelago-Player-Guide.md")
    text = open(path, encoding="utf-8").read()
    start = text.find("**`keep_local_rune_cap`**")
    end = text.find("\n- **`", start + 1)
    assert start >= 0 and end > start, "the player guide's rune-cap option block is missing"
    block = text[start:end].lower().replace(",", "")
    assert str(KeepLocalRuneCap.default) in block, (
        "the player guide never states the actual rune-cap default (%s)"
        % KeepLocalRuneCap.default)
    assert "0 (the default)" not in block, (
        "the player guide still says the rune cap defaults off; it defaults to %s"
        % KeepLocalRuneCap.default)


@pytest.mark.skipif(_ROOT is None, reason=REPO_ONLY_REASON)
def test_the_shipped_yaml_has_no_shell_escaping_artifacts():
    """`Hero'''s` and `Lord'''s` shipped to players in the rune-cap comment -- a here-string
    escaping artifact that survived because nothing reads the yaml as prose."""
    path = os.path.join(_ROOT, "release", "EldenRing.yaml")
    if not os.path.isfile(path):
        pytest.skip("release/EldenRing.yaml not present")
    lines = open(path, encoding="utf-8").read().split("\n")
    # WITNESS (the test_gf_vacuous_pass ratchet): an empty `bad` proves nothing unless the scan
    # is reading a real yaml. A truncated or moved file would pass this silently -- the same
    # class of defect as the prose it is guarding.
    assert len(lines) > 200, ("release/EldenRing.yaml is %d lines -- the scan is not reading "
                              "the shipped template" % len(lines))
    assert any("keep_local_rune_cap" in l for l in lines), "the rune-cap block is gone"
    bad = [(i, l) for i, l in enumerate(lines, 1) if "'''" in l]
    assert not bad, "shell-escaping artifacts in the shipped yaml: %s" % bad[:4]
