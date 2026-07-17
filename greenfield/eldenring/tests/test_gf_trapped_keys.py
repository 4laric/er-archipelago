"""Trapped-key softlock AUDIT (standing gate) -- SPEC: the Lamenter's Gaol class of softlock.

WHY. The region-lock model is COARSE: holding a region's Lock makes the client treat EVERY check in
that region as reachable, ignoring the vanilla key gates INSIDE it. That is fine as long as a key's
own source isn't trapped behind the gate it opens. The Gaol keys broke it: BOTH Gaol keys sit inside
the nested cells they unlock (flags 41027000 / 41027320, both m41), so with the model believing the
whole gaol reachable on the Charo's Lock, fill could place required progression behind keys whose only
sources are behind those same keys -- an unwinnable cycle (Alaric playtest 2026-07-16;
features/legacy_key_gates handles it now).

THE SIGNATURE this gate mines from data (no EMEVD needed): a KEY item whose EVERY vanilla source is a
map-lot flag confined to ONE interior map, with no "spare" source outside it (no overworld m60/m61
pickup, no shop/global source, no second interior map). That is exactly the Gaol shape and the inverse
of the safe Academy Glintstone Key, which has a Liurnia OVERWORLD spare (flag 1034457100) on top of
its m14 source.

CRITICAL: key on the FLAG's encoded map, NOT region_map.csv's `map` column -- that column is
mis-scannable (the Gaol UPPER key's row is mis-tagged m18_00 "Stormveil" though its flag 41027000 is
plainly m41). Keying on the flag is how legacy_key_gates already does it, and why this audit sees the
Gaol pair correctly.

WHAT THIS IS AND ISN'T. This is a CANDIDATE finder, not a proof: "all sources in one interior map"
strongly implies "gates something in that map" (the vanilla design), but confirming the exact gated
range -- i.e. whether a source is behind the gate its own key opens (a real softlock) or a free pickup
elsewhere in the region (benign) -- needs EMEVD, which lives only on the artifact machine. So a NEW
trapped key FAILS this gate and forces a human to classify it: add it to legacy_key_gates
(_LEGACY_KEYS / _MULTI_KEY_GATES) if it self-gates, or to REVIEWED_BENIGN below with a reason.

Run:  python -m pytest greenfield/eldenring/tests/test_gf_trapped_keys.py
"""
import csv
import os
import re

import pytest

pytest.importorskip("worlds.eldenring")
import worlds.eldenring as _erpkg  # noqa: E402
from worlds.eldenring.features.legacy_key_gates import _LEGACY_KEYS, _MULTI_KEY_GATES  # noqa: E402

# Trapped keys REVIEWED as benign -- their sole source is inside one interior map, but no REQUIRED
# progression can end up stranded behind them (Alaric review 2026-07-18). Two distinct reasons:
#   * STRUCTURAL benign: the key is a free pickup, not behind the door it opens (no self-gate). Once
#     the region Lock is held the key is reachable, so nothing is stranded.
#   * SURFACE-CONDITIONAL benign: the key DOES self-gate (a "progression item" in the strict sense),
#     but everything it gates is OFF the progression_surface, so fill never places progression behind
#     it under the DEFAULT (confined) surface. ⚠ This holds ONLY while the surface stays confined: a
#     seed that WIDENS progression_surface to include those checks -- or plays "no bias" (surface off /
#     progression allowed anywhere) -- turns this into a REAL Gaol-class self-gate softlock. If that
#     mode is ever supported, PROMOTE the surface-conditional keys below to legacy_key_gates (a hard,
#     surface-independent gate) rather than leaving them here.
REVIEWED_BENIGN = {
    # structural (free pickup, no self-gate):
    "Rusty Key": "Stormveil (m10) free corpse pickup; opens the Rampart Tower side door, not its own source",
    # surface-conditional (self-gates, but gates only off-surface content):
    "Storeroom Key": "Belurat (m20); gates only Hornsent Grandam questline content, none of it on "
                     "the progression_surface -- safe while the surface stays confined (see ⚠ above)",
    "Well Depths Key": "Belurat (m20); a self-gating progression item in the strict sense, BUT "
                       "everything it gates is OFF the progression_surface, so no progression lands "
                       "behind it under the default confined surface (see ⚠ above -- promote to "
                       "legacy_key_gates if a 'no bias' / widened-surface mode is ever supported)",
}


def _interior_map(flag):
    """The INTERIOR map mXX a map-lot flag encodes (XX = flag // 1_000_000, for XX in 10..59), or None
    for an overworld (m60/m61 -> billions) / special / global / shop flag -- i.e. NOT a lone interior
    dungeon. This is the reliable, mis-scan-proof signal (see module docstring)."""
    return flag // 1_000_000 if 10_000_000 <= flag < 60_000_000 else None


def _key_sources():
    """{key item name -> [(flag, csv_map), ...]} for every item whose name ends in 'Key' (dungeon /
    door keys; a compound like 'Black-Key Crossbow' is a weapon and is excluded by the endswith).
    Read from region_map.csv, installed beside the package."""
    base = os.path.dirname(_erpkg.__file__)
    csvp = os.path.join(base, "region_map.csv")
    if not os.path.isfile(csvp):
        pytest.skip("region_map.csv not installed beside the package -- run gf_test.py --install-only")
    out = {}
    with open(csvp, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            name = row["item_name"]
            flag = row["flag"]
            if not re.search(r"\bKey$", name) or not flag.lstrip("-").isdigit():
                continue
            out.setdefault(name, []).append((int(flag), row.get("map", "")))
    return out


def _trapped_keys():
    """{name -> (interior_map, sources)} for keys whose EVERY source is in ONE interior map with no
    spare (overworld / global / shop / second interior)."""
    trapped = {}
    for name, sources in _key_sources().items():
        maps = [_interior_map(f) for (f, _m) in sources]
        interiors = [m for m in maps if m is not None]
        spares = [m for m in maps if m is None]
        if interiors and not spares and len(set(interiors)) == 1:
            trapped[name] = (interiors[0], sources)
    return trapped


def _declared_keys():
    return set(_LEGACY_KEYS) | {k for g in _MULTI_KEY_GATES for k in g["keys"]}


def test_no_undeclared_trapped_key():
    """The gate: every trapped key must be either DECLARED in legacy_key_gates (a real gate the model
    enforces) or REVIEWED_BENIGN (a free-pickup key that doesn't self-gate). A new one that is neither
    is a Gaol-class softlock RISK and must be classified before it ships."""
    trapped = _trapped_keys()
    unclassified = sorted(set(trapped) - _declared_keys() - set(REVIEWED_BENIGN))
    assert not unclassified, (
        "trapped-key softlock candidate(s) neither declared in legacy_key_gates nor REVIEWED_BENIGN: "
        + ", ".join(f"{k} (all sources in m{trapped[k][0]}: {trapped[k][1]})" for k in unclassified)
        + " -- confirm via EMEVD whether the key self-gates (add to _LEGACY_KEYS/_MULTI_KEY_GATES) or "
        "is a free pickup (add to REVIEWED_BENIGN with a reason)."
    )


def test_gaol_keys_are_detected_and_declared():
    """The detector actually SEES the known softlock: both Gaol keys are trapped in m41 (keyed on the
    FLAG, so the mis-scanned m18 map column on the Upper key doesn't hide it) and are declared."""
    trapped = _trapped_keys()
    for k in ("Gaol Upper Level Key", "Gaol Lower Level Key"):
        assert k in trapped, f"{k} should read as trapped (its source is inside the gaol)"
        assert trapped[k][0] == 41, f"{k} should key to m41 by flag, not the csv map column"
        assert k in _declared_keys(), f"{k} must be declared in legacy_key_gates"


def test_academy_key_is_not_trapped():
    """The safe inverse: the Academy Glintstone Key has an overworld SPARE (m60) on top of its m14
    source, so it is NOT trapped -- the detector must not flag a key that has a reachable spare."""
    assert "Academy Glintstone Key" not in _trapped_keys()


def test_reviewed_benign_are_actually_trapped():
    """Keep REVIEWED_BENIGN honest: every entry must STILL be a trapped candidate. If a data change
    makes one no longer trapped (e.g. it grew a spare source), it should be pruned from the allowlist
    rather than lingering as a stale exemption."""
    trapped = _trapped_keys()
    stale = sorted(set(REVIEWED_BENIGN) - set(trapped))
    assert not stale, f"REVIEWED_BENIGN entries no longer trapped (prune them): {stale}"
