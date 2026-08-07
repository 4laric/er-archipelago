"""`scaduBlessingCap` — the wire the game-wide Scadutree blessing rides on, and the key that must
never be absent-means-zero.

WHY THIS FILE EXISTS. `global_scadutree_blessing` shipped in 2026-07 with an option help text
asserting the engine gates the blessing to the DLC "so NONE of these modes touch base-game balance".
Nobody had checked it. On 2026-07-29 it was measured in-game and it was TRUE — which meant the
option named "global" had been structurally incapable of being global for its entire life, and both
live modes were silently inert outside the Land of Shadow. The client now applies the blessing
itself (Lever D: clone the ladder rung onto a vetted no-op SpEffect row and make it permanent), and
this key is the seed's half of that: the CEILING for the curve.

THE FAILURE THIS FILE IS AIMED AT is the one the feature already suffered once: a value that reads
as "off" when it is simply absent. `scaduBlessingCap` is emitted only when the mode is on, so an
old client — or a mode-0 seed — sees no key at all. If the client's fallback for an absent cap were
0, every blessing would clamp to 0 and the whole feature would ship inert for the second time. The
client-side half of that contract is pinned in `er-logic/src/upgrades.rs::apply_blessing_cap`
(`cap_absent_means_the_ladder_ceiling_not_zero`); this file pins the world's half — that the key is
emitted exactly when it should be, and carries a value the client can actually use.

See docs/specs/SPEC-global-scadutree-blessing-20260729.md §6 and
docs/specs/IMPL-global-scadutree-blessing-20260729.md.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring import contract  # noqa: E402
from worlds.eldenring.features import scaling as sc  # noqa: E402

KEY = "scaduBlessingCap"


def _contract_key(name):
    for k in contract.CONTRACT:
        if k.name == name:
            return k
    return None


def test_the_key_is_declared_and_optional():
    """Declared so `validate_slot_data` and the client's mirror both know its shape; NOT required,
    because a mode-0 seed must not emit it at all."""
    k = _contract_key(KEY)
    assert k is not None, f"{KEY} is not in the contract — the client's mirror will not know it"
    assert k.shape == "INT"
    assert not k.required, (
        f"{KEY} must be optional: it is absent on every `off` seed, and a required key that an "
        "`off` seed cannot emit would fail validation on the default configuration")


def test_the_contract_entry_names_the_absent_fallback():
    """CONTRIBUTING rule 3 — name the space wherever two components exchange a value. The dangerous
    reading of this key is not its unit but its ABSENCE, so the contract text has to say what absent
    means. A future reader who defaults it to 0 reintroduces the original bug."""
    k = _contract_key(KEY)
    doc = k.doc.lower()
    assert "absent" in doc, "the contract entry must say what an ABSENT cap means"
    assert "20" in doc or "ceiling" in doc, "…and that it falls back to the ladder ceiling, not 0"


def test_there_is_no_ceiling_but_the_game_s_own():
    """CEILING REMOVED 2026-08-06 (Alaric). A cap the base game does not have is a rule the player
    has to be told about, and no seed was telling them. The vanilla ladder is
    `20000100..=20000120` — levels 0..20 at stride 1, confirmed against SpEffectParam — and 20 is
    what an ABSENT `scaduBlessingCap` has always meant on the client side.

    🛑 The 12 that used to live in `scaling.SCADU_BLESSING_CAP` was never a ceiling argument. It was
    a POOL-PRESSURE argument (SCADU_CUM[20]=50 vs [12]=26, all forced-`useful`), so it moved to
    `scadu_supply.SCADU_INJECTION_TARGET`, beside the code it governs. Re-adding a ceiling here
    means re-deciding that, not just restoring a constant."""
    assert not hasattr(sc, "SCADU_BLESSING_CAP"), (
        "SCADU_BLESSING_CAP is back in features/scaling. If a ceiling is genuinely wanted again, it "
        "is a player-visible rule and belongs in the player guide as well as here")
    from worlds.eldenring.features import scadu_supply as ss
    assert 1 <= ss.SCADU_INJECTION_TARGET < len(ss.SCADU_CUM), (
        f"SCADU_INJECTION_TARGET={ss.SCADU_INJECTION_TARGET} is outside the vanilla ladder")


def test_the_legacy_top_level_duplicate_is_gone():
    """RETIRED 2026-07-31. `global_scadutree_blessing` existed twice: as the options echo (which the
    client reads, via `/options/global_scadutree_blessing`) and as a top-level copy nothing ever
    read. Two keys with the same name in different scopes is the same trap the two
    `completion_scaling_floor` keys are annotated for — except this pair had no reason to exist.

    Dropping a key moves CONTRACT_HASH and forces a client update, which is normally a bad trade for
    deleting something unread (see pool_builder.slot_data). It rode along free here because
    `scaduBlessingCap` moved the hash anyway."""
    top_level = [k for k in contract.CONTRACT if k.name == "global_scadutree_blessing"]
    assert top_level == [], (
        "the legacy TOP-LEVEL global_scadutree_blessing is back in the contract; the client reads "
        "options.global_scadutree_blessing and always has")
    # The one that matters is still there, in the options echo.
    assert any(k.name == "global_scadutree_blessing" for k in contract.OPTIONS_SUBKEYS), (
        "options.global_scadutree_blessing is the key the client actually reads — it must stay")


def test_an_off_seed_emits_nothing_new():
    """THE COMPATIBILITY HALF. A mode-0 seed must be byte-identical to one generated before this key
    existed, so no already-released client can trip over it. The default is `off`, so this is what
    almost every real seed looks like.

    Asserted against the fixture's own keyset bookkeeping rather than by generating a fourth world:
    `SlotDataFixtureDefault::test_always_keys_present` already generates a default seed and checks
    ALWAYS_KEYS against it, so the honest statement here is that the cap is NOT in that set."""
    from worlds.eldenring.tests import test_gf_slot_data_fixture as fx
    assert KEY not in fx.ALWAYS_KEYS, f"{KEY} is being demanded of every seed and nothing emits it"
    # 2026-08-06: this used to assert the OPPOSITE — that the key must stay EXPECTED because RICH
    # emitted it. The ceiling was removed, so no mode emits it at all, and the honest statement
    # flipped with the behaviour. The contract entry stays declared (the client still honours a cap
    # from any seed that sends one); what changed is that this world never sends one.
    assert KEY not in fx.EXPECTED_KEYS, (
        f"{KEY} is in EXPECTED_KEYS, but no seed emits a blessing ceiling any more — it belongs in "
        "_CONTRACT_NOT_EMITTED with its justification")


def test_the_option_is_reachable_from_yaml():
    """UNFROZEN 2026-07-31, default still `off`. The freeze had an effect nobody intended: the option
    could not be set from yaml at all, so the feature could never be playtested, so the fact that it
    did nothing outside the DLC went unnoticed for its entire life. A knob that cannot be turned on
    cannot be tested.

    🛑 Re-freezing this makes the whole game-wide blessing unreachable again. If that is ever the
    right call, it should be a deliberate one that also decides what happens to the client's applier
    — hence this test, and hence the failure message."""
    from worlds.eldenring import defaults
    for name in ("global_scadutree_blessing", "scadutree_blessing_scope", "dlc_blessing_catchup"):
        assert name not in defaults.FROZEN_OPTIONS, (
            f"re-freezing {name} makes the game-wide blessing unreachable from yaml and untestable "
            "in-game — the exact condition that hid the DLC-only bug")
    assert sc.Scaling.OPTIONS["global_scadutree_blessing"] is sc.GlobalScadutreeBlessing
    assert sc.Scaling.OPTIONS["scadutree_blessing_scope"] is sc.ScadutreeBlessingScope
    assert sc.Scaling.OPTIONS["dlc_blessing_catchup"] is sc.DlcBlessingCatchup


def test_the_default_is_still_off():
    """Unfreezing is NOT a balance change. The 2026-07-18 call (the DLC floor made the DLC too easy)
    stands as the default; unfreezing only makes the other values reachable.

    🛑 `er-unfreezing-an-option-needs-the-class-default`: a shipped yaml that pins the value MASKS a
    rotted class default, so this pins the DEFAULT rather than the template."""
    assert sc.GlobalScadutreeBlessing.default == 0
    assert sc.GlobalScadutreeBlessing.option_off == 0
    # ...and the replacements default to the same behaviour, so the split is not a balance change
    # smuggled in as a rename.
    assert sc.ScadutreeBlessingScope.default == sc.ScadutreeBlessingScope.option_dlc_only == 0
    assert sc.DlcBlessingCatchup.default == 0


def test_no_mode_emits_a_ceiling_any_more():
    """THE PRODUCER HALF OF THE 2026-08-06 REMOVAL.

    🛑 THIS TEST USED TO ASSERT THE OPPOSITE, and that is the defect it now records. It
    required EXACTLY ONE `out[KEY] = …` line in `Scaling.slot_data`, sitting under
    `if blessing != 0:`. The commit that removed the ceiling deleted that line and left the
    assertion standing, so from then on the suite demanded an emit site that the same change had
    deliberately taken away — `expected exactly one emit site for scaduBlessingCap, found 0`, on a
    file nobody was editing. The ruling was never in doubt (features/scaling.py argues it at
    length, and `test_there_is_no_ceiling_but_the_game_s_own` above pins it); what was missing was
    a test that agreed with it.

    ABSENCE IS THE BEHAVIOUR, not the lack of one. The client's `apply_blessing_cap` falls back to
    the ladder ceiling (20) when the key is missing, so a seed that emits nothing IS a seed saying
    “no extra cap”. The contract entry stays declared — the client still honours a cap from any
    apworld that sends one — which is why `test_the_key_is_declared_and_optional` survives this.

    🛑 Re-adding a ceiling is not a matter of restoring this line. It is a player-visible rule
    (player guide), it needs an OFF_LEDGER row in test_gf_off_means_off.py, and it must be gated on
    the MODE and never on a kept DLC region — gating it on DLC would make it absent on exactly the
    base-game seeds the game-wide blessing was rewritten for."""
    import inspect
    src = inspect.getsource(sc.Scaling.slot_data)
    emit = [ln for ln in src.splitlines() if KEY in ln and "out[" in ln]
    assert emit == [], (
        f"{KEY} has an emit site again in Scaling.slot_data: {emit!r}. See the docstring — a "
        "ceiling needs the player guide and an off-test, not just this line")
    # …and the absence is RECORDED, not a deletion nobody noticed. An unexplained gap is how this
    # key acquired a stale test in the first place (CONTRIBUTING rule 14: the note ships with it).
    assert "NO `scaduBlessingCap`" in src, (
        "features/scaling.py no longer says WHY no ceiling is emitted. Absence with no note reads "
        "as an omission to the next reader, who will 'restore' it")


class ScaduBlessingOffSeed(WorldTestBase):
    """A REAL mode-0 world. `test_an_off_seed_emits_nothing_new` above argues from the fixture's
    bookkeeping sets (ALWAYS_KEYS / EXPECTED_KEYS), which pins the CLASSIFICATION of the key but
    never generates an off world -- so a broken gate in features/scaling.py (emit the cap
    unconditionally) would sail past it AND past the fixture: the key is in EXPECTED_KEYS, so a
    default seed emitting it is not "extra". That is the same hole the 2026-08-04 audit proved for
    the dungeon-sweep keys (finding P1). This class closes it the only way that counts: roll a
    seed with the mode pinned off and assert the keys are ABSENT. Paired in
    test_gf_off_means_off.OFF_LEDGER."""
    game = "Elden Ring"
    options = {"num_regions": 0, "global_scadutree_blessing": "off"}

    def test_the_cap_is_absent_when_the_mode_is_off(self):
        leaked = KEY in self.world.fill_slot_data()
        assert not leaked, (
            "scaduBlessingCap emitted on a mode-0 seed. The compatibility contract is absent-"
            "means-off: every seed would now carry a key its own options say cannot exist -- the "
            "`blessing != 0` gate in features/scaling.py is broken.")

    def test_the_floor_ranges_are_absent_when_the_mode_is_off(self):
        leaked = "dlcScadutreeFloorRanges" in self.world.fill_slot_data()
        assert not leaked, (
            "dlcScadutreeFloorRanges emitted with the blessing off -- its gate is "
            "`blessing == 2 and kept DLC regions` (features/scaling.py) and this seed satisfies "
            "neither conjunct.")
