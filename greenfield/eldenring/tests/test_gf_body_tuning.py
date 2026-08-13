"""body_tuning -- what the `no_fall_damage` FREEZE is allowed to have changed, which is nothing.

`no_fall_damage` shipped as a yaml option in v0.4.0 (2026-08-08, #478) and was frozen OFF on
2026-08-13: the option surface is a budget and it did not earn its row. It is NOT half-built -- the
capability works, `no_fall_damage.rs` still implements it, and the key is still emitted -- so this
freeze is a presentation decision, and a presentation decision that moves a seed is a bug.

TWO PROPERTIES, and they pull in opposite directions on purpose:

1. The freeze value equals the class default, so no seed moves TODAY and none moves if the option is
   ever unfrozen again. [[er-unfreezing-an-option-needs-the-class-default]] is about the second half
   of that round trip, and the cheapest time to guarantee it is while applying the freeze.
2. The key is STILL EMITTED. Freezing is not deleting: `core._options_echo` reads the Frozen
   stand-in and writes 0, so the client stays wired, the ContractKey stays declared, and
   `test_gf_client_contract_paths` does not need its allowlist entry back. Deleting the option
   instead would have been a three-repo step that re-darkened a working feature.
"""
import dataclasses

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring import contract                                        # noqa: E402
from worlds.eldenring.core import GAME, GFOptions                            # noqa: E402
from worlds.eldenring.defaults import FROZEN_OPTIONS                         # noqa: E402
from worlds.eldenring.features.body_tuning import NoEquipLoad, NoFallDamage  # noqa: E402

_SURFACE = {f.name for f in dataclasses.fields(GFOptions)}


def test_no_fall_damage_is_frozen_and_frozen_at_its_own_default():
    """The freeze moved nothing, in either direction, and that is checkable rather than asserted."""
    assert "no_fall_damage" not in _SURFACE, (
        "no_fall_damage is back on the yaml surface. If that is deliberate, delete this test and "
        "put the option back in core._OPTION_GROUPS and release/EldenRing.yaml -- an ungrouped "
        "option falls back INTO the Advanced accordion, which is the failure PR #554 fixed.")
    assert "no_fall_damage" in FROZEN_OPTIONS, "expected a FROZEN_OPTIONS entry"
    value, key = FROZEN_OPTIONS["no_fall_damage"]
    assert key is None, "NoFallDamage is a Toggle, not a Choice -- it has no current_key"
    assert value == NoFallDamage.default == 0, (
        "the freeze pins no_fall_damage at %r while NoFallDamage.default is %r. They must agree: "
        "if they differ, freezing moved every seed that did not name the option, and unfreezing "
        "later will move them back." % (value, NoFallDamage.default))


def test_its_sibling_is_still_a_real_option():
    """WITNESS for the case above. `no_equip_load` and `no_fall_damage` landed together and are
    read by the same paragraph of the same module docstring, so a change that freezes both by
    accident is entirely plausible -- and the test above would go greener, not redder, for it."""
    assert "no_equip_load" in _SURFACE, (
        "no_equip_load left the yaml surface too. It carries a three-value roll mode and a client "
        "feature handshake; freezing it is a much larger decision than freezing no_fall_damage and "
        "is not something this change did.")
    assert NoEquipLoad.default == 0


class TestTheKeyIsStillOnTheWire(WorldTestBase):
    """FREEZING IS NOT DELETING, and this is the difference stated as a test. The client reads
    `slot_data["options"]["no_fall_damage"]`; if freezing had dropped the key, that read would
    become an absent-key `false` -- the same silent-dark failure features/body_tuning.py was written
    to fix, reintroduced by the tidier-looking option."""

    game = GAME
    options = {"num_regions": 0}

    def test_the_frozen_value_is_emitted_not_omitted(self):
        opts = self.world.fill_slot_data()["options"]
        self.assertIn(
            contract.NO_FALL_DAMAGE, opts,
            "the no_fall_damage key vanished from the options echo. A frozen option must still "
            "emit -- that is the whole reason freezing costs no client churn.")
        self.assertEqual(0, opts[contract.NO_FALL_DAMAGE])
