"""Ability lock (#945, SPEC-ability-lock-mode) -- the apworld half: ONE option.

The client disables the chosen abilities at the game's LOGICAL action layer
(`CSChrActionRequestModule.disabled_action_inputs`), which is keybind- and device-agnostic and
never touches menus (see the client's ability_lock.rs). This feature contributes NOTHING to the
item pool, regions, or logic -- a locked ability is not an item and gates no check; it is a pure
per-seed client behaviour. So the whole apworld surface is a single OptionSet whose value the
central `core._options_echo` emits into `slot_data["options"]["locked_abilities"]`, read by
`er-logic/options.rs parse_ability_lock`.

WHY NO SLOT_DATA HOOK HERE. The `options` sub-dict is emitted centrally (contract F1 fix): features
that tried to write their own `options.<key>` copies were the exact bug that left death_link dark
for months. The value rides through `_options_echo` against the STR_LIST contract subkey; this
module only declares the option.

NOT AN UNLOCK. This is a static per-seed lock: what starts locked stays locked for the seed. The
find-to-unlock randomizer (abilities as items you recover) is a separate, larger change -- it mints
item ids, touches the pool, and moves the contract hash. The client already carries the runtime
seam for it (ability_lock::unlock); this option is deliberately just the static placement.
"""
from Options import OptionSet
from ..registry import Feature, register
from .. import contract


class LockedAbilities(OptionSet):
    """ABILITIES THE GAME DISABLES ALL SEED. Each named ability is turned off at the character's
    logical-action layer, so the lock survives key/pad rebinds and covers keyboard and mouse, and
    menu navigation is never affected.

    Valid names: jump, crouch, roll, r1, r2, l1, l2. (r1/r2/l1/l2 are the attack inputs; locking one
    also stops casting through it, since a staff or seal casts on the attack button.) Empty = nothing
    locked, the default. `heal` is not lockable here -- that is the flask-charge option's job.

    🛑 crouch is the one UNVERIFIED action: ER has no dedicated crouch action, so the client routes it
    to the stick-click (l3) as a first guess. If a playtest shows that is wrong, the fix is one line
    in er-logic, not here.

    This is a STATIC lock for the whole seed -- there is no in-run unlock yet (that is the separate
    abilities-as-items feature). It is env-overridable in test builds via ER_ABILITY_LOCK_TEST."""
    display_name = "Locked Abilities"
    default = frozenset()
    valid_keys = frozenset(contract.ABILITY_LOCK_KEYS)

    @staticmethod
    def wizard_key_meta():
        """Per-key presentation for the options wizard (generic hook, read by
        tools/dump_options_metadata.py). Additive -- a renderer that ignores it still works."""
        desc = {
            "jump": "Jumping (and jump attacks).",
            "crouch": "Crouch / stealth (unverified: routed to stick-click).",
            "roll": "Dodge roll and neutral backstep.",
            "r1": "Right light attack (and casting through it).",
            "r2": "Right heavy attack (and its charged cast).",
            "l1": "Left attack / offhand (and casting through it).",
            "l2": "Left trigger: guard / weapon skill / left cast.",
        }
        return {
            "keys": [{"key": k, "label": k.upper(), "description": desc[k]}
                     for k in contract.ABILITY_LOCK_KEYS],
            "default": [],
        }


@register
class AbilityLock(Feature):
    name = "ability_lock"
    OPTIONS = {"locked_abilities": LockedAbilities}
    # No ITEMS / regions / rules / slot_data hook: the value is echoed centrally (see module docstring).
