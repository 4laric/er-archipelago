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


def test_cap_is_within_the_real_ladder():
    """The vanilla ladder is `20000100..=20000120` — levels 0..20 at stride 1, confirmed against
    SpEffectParam. A cap outside that range is either a no-op or a request for a row that does not
    exist."""
    assert 1 <= sc.SCADU_BLESSING_CAP <= 20, (
        f"SCADU_BLESSING_CAP={sc.SCADU_BLESSING_CAP} is outside the vanilla blessing ladder (1..20)")


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
    assert KEY not in fx.ALWAYS_KEYS, (
        f"{KEY} is being demanded of every seed, but it is emitted only when the mode is on — a "
        "default (off) seed cannot produce it")
    assert KEY in fx.EXPECTED_KEYS, (
        f"{KEY} must still be an EXPECTED key: it is emitted by the RICH fixture, and dropping it "
        "out of the expected set would stop anything from checking it is ever emitted at all")


def test_the_option_is_reachable_from_yaml():
    """UNFROZEN 2026-07-31, default still `off`. The freeze had an effect nobody intended: the option
    could not be set from yaml at all, so the feature could never be playtested, so the fact that it
    did nothing outside the DLC went unnoticed for its entire life. A knob that cannot be turned on
    cannot be tested.

    🛑 Re-freezing this makes the whole game-wide blessing unreachable again. If that is ever the
    right call, it should be a deliberate one that also decides what happens to the client's applier
    — hence this test, and hence the failure message."""
    from worlds.eldenring import defaults
    assert "global_scadutree_blessing" not in defaults.FROZEN_OPTIONS, (
        "re-freezing global_scadutree_blessing makes the game-wide blessing unreachable from yaml "
        "and untestable in-game — the exact condition that hid the DLC-only bug")
    assert sc.Scaling.OPTIONS["global_scadutree_blessing"] is sc.GlobalScadutreeBlessing


def test_the_default_is_still_off():
    """Unfreezing is NOT a balance change. The 2026-07-18 call (the DLC floor made the DLC too easy)
    stands as the default; unfreezing only makes the other values reachable.

    🛑 `er-unfreezing-an-option-needs-the-class-default`: a shipped yaml that pins the value MASKS a
    rotted class default, so this pins the DEFAULT rather than the template."""
    assert sc.GlobalScadutreeBlessing.default == 0
    assert sc.GlobalScadutreeBlessing.option_off == 0


def test_the_emitter_is_gated_on_the_mode_and_not_on_dlc():
    """The blessing floor (`dlcScadutreeFloorRanges`) is correctly DLC-gated — it describes DLC
    regions. The CAP is not: after this change the curve is game-wide, so gating the cap on a kept
    DLC region would make it absent on exactly the seeds this feature was rewritten for. Pinned by
    reading the producer's own condition rather than by generating a DLC-free world, which the
    freeze makes impossible to do with the mode on."""
    import inspect
    src = inspect.getsource(sc.Scaling.slot_data)
    emit = [ln for ln in src.splitlines() if KEY in ln and "out[" in ln]
    assert len(emit) == 1, f"expected exactly one emit site for {KEY}, found {len(emit)}"
    idx = src.splitlines().index(emit[0])
    guard = src.splitlines()[idx - 1].strip()
    assert guard == "if blessing != 0:", (
        f"{KEY} must be gated on the MODE alone, got: {guard!r}. Gating it on DLC regions would "
        "make it absent on base-game seeds — the whole point of the rewrite")
