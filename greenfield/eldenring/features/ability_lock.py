"""Ability lock (#945, SPEC-ability-lock-mode) -- the apworld half.

The client disables the chosen abilities at the game's LOGICAL action layer
(`CSChrActionRequestModule.disabled_action_inputs`), which is keybind- and device-agnostic and
never touches menus (see the client's ability_lock.rs).

TWO MODES, one set (`locked_abilities`):

* STATIC (default) -- the abilities are off for the whole seed. Pure client behaviour: no item, no
  check, no pool. The set rides `slot_data["options"]["locked_abilities"]` (emitted centrally by
  `core._options_echo`), read by `er-logic/options.rs parse_ability_lock`.

* PROGRESSIVE (#980) -- the same abilities start locked, but each becomes a SYNTHETIC 'Unlock: X'
  item shuffled into the pool; finding it unlocks that ability (`er_logic ability_lock::unlock`).
  This IS a pool contribution: `create_items` mints one useful item per locked ability (count-exact,
  displacing filler like every other contributor), and `slot_data` ships the per-seed
  `abilityUnlockItems` {item_id: ability} map plus `requiresClientFeatures: ["ability_unlock"]` --
  the armorBundles pattern exactly. The item ids are registered at a fixed base in core.py; the
  client never grants them, it resolves them through the map.

WHY THE ITEMS ARE core-REGISTERED, NOT `ITEMS =` HERE. `registry.allocate_item_ids` hands feature
ITEMS sequential ids, so seven names here would renumber every later feature's items. core.py mints
them at contract.ABILITY_UNLOCK_ITEM_BASE instead (the spawn-trap lesson); this module only decides
WHICH get pooled and emits the map.

NOT lockable progression. The unlock items are `useful`, never required by logic -- a seed is always
completable with an ability still locked, so a missing unlock is a harder run, not a dead one.
`crouch -> l3` is the one unverified action map (er-logic). `heal` is the flask option's job.
"""
from Options import Choice, OptionSet
from ..registry import Feature, register
from .. import contract


class LockedAbilities(OptionSet):
    """ABILITIES THE GAME DISABLES. Each named ability is turned off at the character's logical-action
    layer, so the lock survives key/pad rebinds, covers keyboard and mouse, and never affects menus.

    Valid names: jump, crouch, roll, r1, r2, l1, l2. (r1/r2/l1/l2 are the attack inputs; locking one
    also stops casting through it, since a staff or seal casts on the attack button.) Empty = nothing
    locked, the default. `heal` is not lockable here -- that is the flask-charge option's job.

    🛑 crouch is the one UNVERIFIED action: ER has no dedicated crouch action, so the client routes it
    to the stick-click (l3) as a first guess. If a playtest shows that is wrong, the fix is one line
    in er-logic, not here.

    Ability Lock Mode decides whether these stay off all seed (Static) or start off and are unlocked
    by items you find (Progressive). Env-overridable in test builds via ER_ABILITY_LOCK_TEST."""
    display_name = "Locked Abilities"
    default = frozenset()
    valid_keys = frozenset(contract.ABILITY_LOCK_KEYS)



class AbilityLockMode(Choice):
    """HOW the Locked Abilities behave.

    ``static`` -- they are off for the entire seed. No item, no check; a pure client restriction.

    ``progressive`` -- they start off, and each locked ability becomes an "Unlock: X" item shuffled
    into the multiworld. Find it (or receive it from another world) to get that ability back. The
    items are `useful`, never required to finish, so a seed is always completable even if an unlock
    is still out there. Needs a client that understands ability unlocks (declared via
    requiresClientFeatures); older clients would leave the abilities locked, so they are told to
    upgrade rather than play it half-supported.

    No effect when Locked Abilities is empty."""
    display_name = "Ability Lock Mode"
    option_static = 0
    option_progressive = 1
    default = 0


def _locked_keys(world):
    """The abilities this seed locks, as a sorted list of names (empty when unset)."""
    opt = getattr(getattr(world, "options", None), "locked_abilities", None)
    return sorted(getattr(opt, "value", None) or ())


def _progressive_active(world):
    """True when the locked abilities should be POOLED as unlock items rather than held off all seed.

    Requires progressive mode, a non-empty lock set, the item shuffle on, and not vanilla_placement
    (whose premise is that nothing moves -- a synthetic unlock item would violate it). create_items
    and slot_data gate on this SAME predicate so the pool contribution and the map never disagree."""
    mode = getattr(getattr(world, "options", None), "ability_lock_mode", None)
    if mode is None or int(getattr(mode, "value", 0)) != AbilityLockMode.option_progressive:
        return False
    if not _locked_keys(world):
        return False
    from . import vanilla_placement
    return bool(world._shuffle_on()) and not vanilla_placement.is_on(world)


@register
class AbilityLock(Feature):
    name = "ability_lock"
    OPTIONS = {"locked_abilities": LockedAbilities, "ability_lock_mode": AbilityLockMode}
    # No ITEMS: the seven unlock items are minted at a fixed id base in core.py (see module docstring).

    def create_items(self, world):
        # Progressive: one useful 'Unlock: X' per locked ability, appended before the filler tail so
        # the pool stays count-exact (each displaces one filler slot, like every other contributor).
        if not _progressive_active(world):
            return []
        names = dict(contract.ABILITY_UNLOCK_ITEM_NAMES)
        return [world.create_item(names[k]) for k in _locked_keys(world)]

    def slot_data(self, world):
        # Static mode contributes nothing here -- the locked set rides the central options echo.
        # Progressive mode ships the id->ability map (client resolves received ids to unlocks) and
        # the client-feature handshake token.
        if not _progressive_active(world):
            return {}
        names = dict(contract.ABILITY_UNLOCK_ITEM_NAMES)
        return {
            "abilityUnlockItems": {
                str(world.item_name_to_id[names[k]]): k for k in _locked_keys(world)
            },
            "requiresClientFeatures": [contract.ABILITY_UNLOCK_FEATURE],
        }
