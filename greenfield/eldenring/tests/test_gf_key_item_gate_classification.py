"""Every item that opens a VANILLA DOOR is classified, and the unknowns are a ratchet.

MOTIVATING CASE (2026-08-01). A player on 0.2.18: *"I had 2 great runes, but couldn't enter leyndell
itself to make progress. Then later I got the raya lucaria key, but this one also didn't give me
acces to raya lucaria itself."* Both are the same shape, and it is a shape we have shipped before:

    the client grants the goods -> the item is in the bag -> the vanilla gate reads an EVENT FLAG
    that a raw grant never trips -> the door stays shut -> nothing tells the player, or us.

Proven once in game already (Rold Medallion / flag 400001, seed 45997544150175068277, 2026-06-19:
lift sealed with the medallion held), and again in a different guise as the whetblade affinity flags
(#240). The client's table -- `crates/eldenring-archipelago/src/keyitems.rs::KEY_ITEM_ACQUIRE_FLAGS`
-- is EIGHT rows, and every one of them was added AFTER somebody hit the wall. It is a whitelist
whose failure mode is silence, and silence is not something a test can observe.

So this gate does not test the client table. It tests that we have an ANSWER, on the record, for
every item our own logic hands the player as a key:

  1. POPULATION, derived from the features -- not a second hand-list that can drift. If a feature
     names an item as the way past a door, that item needs a row in `greenfield/key_item_gates.tsv`.
     Add a gate, forget the file, go red.
  2. SHAPE. obtained_flag rows carry flags; possession rows do not; a confident row cites `in_game`
     or `datamine` evidence. `assumed` is legal ONLY on UNVERIFIED -- you may not reason your way to
     "a plain grant is enough", because that claim is exactly what ships no flag write.
  3. RATCHET. The UNVERIFIED count is pinned and may only fall. This is debt, recorded honestly,
     rather than a green build bought by classifying things we have not measured.

🛑 WHAT THIS DELIBERATELY DOES NOT DO. It does not add flags for the unknown rows. Writing a guessed
flag is not the safe direction -- er-whetblade-flags-are-the-unlock is the case where setting the
"obvious" flag silently collected four live checks. Measure, then classify, then write.
"""
import os

import pytest

pytest.importorskip("worlds.eldenring")
from worlds.eldenring.item_ids import ITEM_CATALOG  # noqa: E402

TABLE = "key_item_gates.tsv"
MECHANISMS = {"obtained_flag", "possession", "not_a_vanilla_gate", "UNVERIFIED"}
TIERS = {"in_game", "datamine", "assumed"}

# The ratchet. Opened 2026-08-01 at 26 (6 classified: Rold, Drawing-Room, the two Dectus halves,
# the two Haligtree halves). Same day: -1 when the EMEVD probe settled the Academy Glintstone Key as
# possession-gated, then -6 when it settled all six Great Runes as flag-gated on 191-196. 26 -> 19 in
# one afternoon, which is what the ratchet is FOR. LOWER THIS when you measure something. Never raise
# it -- a new gate arrives UNVERIFIED and pushes the count over the ceiling, which is the whole point.
# 19 -> 18 on 2026-08-14: the Hole-Laden Necklace settled as POSSESSION off the bell events. Both
# Finger Ruins bell ObjActs are disabled unless PlayerHasItem(ItemType.Goods, 2008008) --
# m61_53_46 $Event(2053462600), m61_50_40 $Event(2050402600) -- so the row is measured, not assumed.
UNVERIFIED_CEILING = 18

# Measured 2026-08-01 (tools/probe_vanilla_gate_predicates.py, 589 files / 4893 events). Pinned here
# because it is the answer to the report that produced this file, and a silent change to it would
# mean somebody edited the table without re-measuring.
#
# 197 joined on 2026-08-16 (Alaric's ruling: seven runes, the Unborn one is a full citizen). It is NOT
# a Divine-Tower restore flag like 191-196 -- there is no tower for the Unborn rune. It is Rennala's
# ACQUISITION flag, and it counts for the same reason the others do: the capital reads
# `CountEventFlags(EventFlag, 190, 199)`, and 197 is inside 190-199. Which is also why the band
# membership below is the assertion that actually matters -- an id outside 190-199 is silently
# uncounted, and the count is the whole gate.
GREAT_RUNE_BAND = range(190, 200)
GREAT_RUNE_FLAGS = {191, 192, 193, 194, 195, 196, 197}


def _table_path():
    """The tsv, in the repo (greenfield/) or beside the installed package (tools/gf_test.py copies
    every greenfield/*.tsv in). Returns None if neither exists, so the test fails loudly rather than
    passing on an empty read."""
    pkg = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [
        os.path.join(pkg, TABLE),                                    # installed: beside the package
        os.path.join(os.path.dirname(pkg), TABLE),                   # repo: greenfield/
        os.path.abspath(os.path.join(here, "..", "..", TABLE)),
    ]
    for c in cands:
        if os.path.exists(c):
            return c
    return None


def _rows():
    path = _table_path()
    assert path, f"{TABLE} not found -- it must ship beside the package (gf_test copies greenfield/*.tsv)"
    out = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            assert len(parts) == 5, f"{TABLE}:{lineno}: expected 5 tab-separated fields, got {len(parts)}"
            item, mech, flags, tier, evidence = (p.strip() for p in parts)
            out.append({"lineno": lineno, "item": item, "mechanism": mech,
                        "flags": flags, "tier": tier, "evidence": evidence})
    return out


def _population():
    """Items our own features hand the player as the way past a vanilla door.

    DERIVED, never hand-listed -- a hand-list is the failure we are guarding against. Restricted to
    names that are REAL catalog items: legible_keys also carries display aliases ("Dectus Medallion")
    that are never granted, so they cannot fail this way.
    """
    from worlds.eldenring.features.natural_progression import GATE_CLAUSES
    from worlds.eldenring.features.legacy_key_gates import _LEGACY_KEYS, _MULTI_KEYS
    from worlds.eldenring.features.leyndell_gate import GREAT_RUNES
    from worlds.eldenring.features.legible_keys import CAPSTONE_VANILLA_KEYS

    names = set()
    for clauses in GATE_CLAUSES.values():
        for clause in clauses:
            names |= set(clause)
    names |= set(_LEGACY_KEYS) | set(_MULTI_KEYS) | set(GREAT_RUNES)
    names |= set(CAPSTONE_VANILLA_KEYS.values())
    return {n for n in names if n in ITEM_CATALOG}


class TestPopulationIsCovered:
    def test_every_derived_gate_item_has_a_row(self):
        rows = {r["item"] for r in _rows()}
        missing = sorted(_population() - rows)
        assert not missing, (
            f"{len(missing)} item(s) open a vanilla door in our logic but have no row in {TABLE}:\n  "
            + "\n  ".join(missing)
            + f"\n\nAdd a row. If you do not know what the game reads, that IS the answer -- write "
              f"UNVERIFIED and raise nothing; the ratchet will tell you the debt grew.")

    def test_no_stale_rows(self):
        """A row for something no feature gates any more is dead weight that inflates the ceiling."""
        pop = _population()
        stale = sorted(r["item"] for r in _rows() if r["item"] not in pop)
        assert not stale, (
            f"{TABLE} classifies item(s) no feature gates on: {stale}. Remove them (and lower "
            f"UNVERIFIED_CEILING if any were UNVERIFIED).")

    def test_items_are_real_catalog_items(self):
        bad = sorted(r["item"] for r in _rows() if r["item"] not in ITEM_CATALOG)
        assert not bad, f"{TABLE} names non-catalog items (typo?): {bad}"

    def test_no_duplicate_rows(self):
        seen, dupes = set(), []
        for r in _rows():
            (dupes.append(r["item"]) if r["item"] in seen else seen.add(r["item"]))
        assert not dupes, f"{TABLE} has duplicate rows: {sorted(set(dupes))}"


class TestRowShape:
    def test_mechanism_and_tier_are_known_values(self):
        for r in _rows():
            assert r["mechanism"] in MECHANISMS, f"{TABLE}:{r['lineno']}: bad mechanism {r['mechanism']!r}"
            assert r["tier"] in TIERS, f"{TABLE}:{r['lineno']}: bad evidence_tier {r['tier']!r}"

    def test_obtained_flag_rows_name_their_flags(self):
        for r in _rows():
            if r["mechanism"] != "obtained_flag":
                continue
            flags = [f for f in r["flags"].split(",") if f.strip()]
            assert flags and r["flags"] != "-", (
                f"{TABLE}:{r['lineno']}: {r['item']!r} is obtained_flag but names no flag -- the "
                f"whole content of that claim is WHICH flag the client must set")
            for f in flags:
                assert f.strip().isdigit(), f"{TABLE}:{r['lineno']}: flag {f!r} is not an id"

    def test_non_flag_rows_carry_no_flags(self):
        for r in _rows():
            if r["mechanism"] in ("obtained_flag",):
                continue
            assert r["flags"] == "-", (
                f"{TABLE}:{r['lineno']}: {r['item']!r} is {r['mechanism']} but lists flags "
                f"{r['flags']!r} -- if a flag matters the mechanism is obtained_flag")

    def test_every_row_cites_evidence(self):
        for r in _rows():
            assert len(r["evidence"]) >= 20, (
                f"{TABLE}:{r['lineno']}: {r['item']!r} has no usable evidence string. A row without "
                f"a reason is a guess with a tidier font.")

    def test_assumed_is_only_legal_on_unverified(self):
        """The rule with the teeth. `possession` means 'ship no flag write' -- you may not reach
        that conclusion by reasoning alone, because being wrong is silent and costs a run."""
        bad = [(r["item"], r["mechanism"]) for r in _rows()
               if r["tier"] == "assumed" and r["mechanism"] != "UNVERIFIED"]
        assert not bad, (
            f"rows claiming a mechanism on `assumed` evidence: {bad}. Either measure it "
            f"(in_game / datamine) or mark it UNVERIFIED.")


class TestUnverifiedRatchet:
    def test_unverified_count_does_not_exceed_the_ceiling(self):
        unverified = sorted(r["item"] for r in _rows() if r["mechanism"] == "UNVERIFIED")
        assert len(unverified) <= UNVERIFIED_CEILING, (
            f"{len(unverified)} UNVERIFIED gate items, ceiling is {UNVERIFIED_CEILING}. A new gate "
            f"arrived without anyone establishing what the game reads for it:\n  "
            + "\n  ".join(unverified))

    def test_ceiling_is_not_slack(self):
        """If the real count has fallen below the ceiling, lower the ceiling in the same commit --
        otherwise the slack silently absorbs the next unmeasured gate."""
        n = sum(1 for r in _rows() if r["mechanism"] == "UNVERIFIED")
        assert n == UNVERIFIED_CEILING, (
            f"UNVERIFIED_CEILING is {UNVERIFIED_CEILING} but the table has {n}. Set the ceiling to "
            f"{n} so the ratchet keeps its grip.")


class TestTheKnownCasesAreRecorded:
    """Rule 11: the cases that produced this gate are the acceptance test.

    These are pinned deliberately. Rold is the one we PROVED in game -- if its row ever softens, the
    evidence that this whole class is real has gone with it. The Academy key and the Great Runes are
    the open player report; they must stay visible as unmeasured until someone measures them.
    """
    def _row(self, name):
        for r in _rows():
            if r["item"] == name:
                return r
        pytest.fail(f"{TABLE} has no row for {name!r}")

    def test_rold_medallion_stays_the_proven_obtained_flag_case(self):
        r = self._row("Rold Medallion")
        assert r["mechanism"] == "obtained_flag"
        assert "400001" in r["flags"]
        assert r["tier"] == "in_game"

    def test_academy_glintstone_key_is_not_quietly_assumed_safe(self):
        """Measured 2026-08-01: possession, on three `PlayerHasItem(ItemType.Goods, 8109)` sites in
        the Crest-warp events and no flag site anywhere. The assertion stays as written -- it is the
        RULE that matters (a reported-shut door may not be classified possession on reasoning
        alone), and it now passes because someone measured it rather than because it was weakened."""
        r = self._row("Academy Glintstone Key")
        assert r["mechanism"] != "possession" or r["tier"] in ("in_game", "datamine"), (
            "the Academy key was reported shut by a player while held; it may not be classified "
            "possession on reasoning alone")
        assert "8109" in r["evidence"], "the possession claim must cite the goods id it was read from"

    def test_great_runes_are_all_present(self):
        from worlds.eldenring.features.leyndell_gate import GREAT_RUNES
        rows = {r["item"] for r in _rows()}
        assert set(GREAT_RUNES) <= rows, sorted(set(GREAT_RUNES) - rows)

    def test_great_runes_are_flag_gated_on_the_measured_band(self):
        """The capital gate is `CountEventFlags(EventFlag, 190, 199) >= 2` (common $Event(720)).
        Six of the seven flags come from the Divine-Tower altar initializers; the seventh (197) is
        Rennala's acquisition flag and counts because it lands in the same band. Nothing gates on
        possession of a rune's goods. If this row set ever drifts, the client's writes stop matching
        the count."""
        from worlds.eldenring.features.leyndell_gate import GREAT_RUNES
        seen = set()
        for name in GREAT_RUNES:
            r = self._row(name)
            assert r["mechanism"] == "obtained_flag", (
                f"{name} is flag-gated (measured); {r['mechanism']!r} would mean we owe no flag write")
            flags = {int(f) for f in r["flags"].split(",") if f.strip()}
            assert len(flags) == 1, f"{name}: expected exactly one restored flag, got {flags}"
            seen |= flags
        # The BAND is the load-bearing property: the gate is a count over 190-199, so an id outside
        # it contributes nothing and no amount of writing it opens the door. Asserted separately
        # from the exact set so a future rune is caught by the rule, not only by the ledger.
        stray = sorted(f for f in seen if f not in GREAT_RUNE_BAND)
        assert not stray, (
            f"rune flags {stray} fall outside the counted band {GREAT_RUNE_BAND} -- the capital "
            f"counts 190-199, so these are written and silently uncounted.")
        assert seen == GREAT_RUNE_FLAGS, (
            f"the rune flags must be exactly {sorted(GREAT_RUNE_FLAGS)} -- got {sorted(seen)}. "
            f"Do not edit this table without re-measuring.")
