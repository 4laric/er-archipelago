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

ONE ATTACK COMES EARLY WHEN ALL FOUR ATTACK INPUTS ARE LOCKED (#1035). A great many checks are
kill-gated -- boss defeats, enemy drops, every defeat-flag sweep trigger -- and logic knows nothing
about the locked set, so a seed that locks r1+r2+l1+l2 can expect kills the player cannot perform.
`create_items` therefore declares `Unlock: R1` to `early_items` in exactly that case, the same seam
Roll uses. Spells are NOT a way out and get no carve-out (Alaric, 2026-08-25: "spells don't count,
you need an L or R button to cast a spell") -- a staff or seal casts on an attack button. Fewer than
four locked forces nothing: an unlocked attack input is a damage source from the start.

NOT lockable progression. The unlock items are `useful`, never required by logic -- a seed is always
completable with an ability still locked, so a missing unlock is a harder run, not a dead one.
`crouch -> l3` is the one unverified action map (er-logic). `heal` is lockable too, but by a
different mechanism: the client re-applies the No Flask SpEffect while it is locked (the flask
heals nothing), since heal owns no action bit.
"""
from Options import Choice, DefaultOnToggle, OptionSet
from ..registry import Feature, register
from .. import contract


class LockedAbilities(OptionSet):
    """ABILITIES THE GAME DISABLES. Each named ability is turned off at the character's logical-action
    layer, so the lock survives key/pad rebinds, covers keyboard and mouse, and never affects menus.

    Valid names: jump, crouch, roll, r1, r2, l1, l2, heal. (r1/r2/l1/l2 are the attack inputs; locking
    one also stops casting through it, since a staff or seal casts on the attack button. `heal` locks
    the flask -- it heals nothing while locked -- via the No Flask SpEffect, not an action mask.)
    Empty = nothing locked, the default.

    🛑 crouch is the one UNVERIFIED action: ER has no dedicated crouch action, so the client routes it
    to the stick-click (l3) as a first guess. If a playtest shows that is wrong, the fix is one line
    in er-logic, not here.

    Locking ALL FOUR attack inputs (r1, r2, l1, l2) in Progressive mode leaves you unable to damage
    anything, and a great many checks are kill-gated -- so that seed forces one attack unlock
    ("Unlock: R1") into an early sphere, wherever in the multiworld it lands. Spells do not count as
    an attack for this: a staff or seal casts on an attack button, so a caster with all four locked
    is just as weaponless. Locking three or fewer forces nothing -- you still have an attack.

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
    items default to `progression` and are REQUIRED to finish (see Ability Unlocks Required) -- so
    a partner holding your "Unlock: Roll" genuinely blocks your goal, which is the whole point of a
    multiworld. Turn Ability Unlocks Required off to make them `useful` and never gate completion.
    Needs a client that understands ability unlocks (declared via
    requiresClientFeatures); older clients would leave the abilities locked, so they are told to
    upgrade rather than play it half-supported.

    No effect when Locked Abilities is empty."""
    display_name = "Ability Lock Mode"
    option_static = 0
    option_progressive = 1
    default = 0


class AbilityUnlocksRequired(DefaultOnToggle):
    """In PROGRESSIVE mode, must you HOLD your unlock items to finish the seed?

    On (default): each pooled "Unlock: X" is `progression` and is added to the goal's held-item
    requirement, exactly like a required Great Rune or Region Lock. Because progression items are
    distributed across the whole multiworld, your abilities can land in a PARTNER's world -- and then
    you cannot complete until they send them back. That mutual dependency is the point of playing in
    an Archipelago rather than solo.

    Off: the unlocks stay `useful` and never gate completion (a seed always finishes even with an
    ability still out). Choose this if you want the ability item-hunt without your ending held hostage
    to another player's progress.

    No effect outside progressive mode, or when Locked Abilities is empty."""
    display_name = "Ability Unlocks Required for Goal"


# The four ATTACK inputs. A seed that locks every one of them leaves the player with no way to
# damage anything -- and spells are not an escape hatch: a staff or seal casts on one of these same
# buttons (Alaric, 2026-08-25: "spells don't count, you need an L or R button to cast a spell").
_ATTACK_KEYS = ("r1", "r2", "l1", "l2")
# Which unlock `create_items` forces early when all four are locked (#1035). Fixed, not drawn: r1 is
# the primary attack input and a constant keeps the guarantee seed-independent.
_FORCED_EARLY_ATTACK = "r1"


def _all_attacks_locked(keys):
    """True when this seed locks EVERY attack input -- the only case that needs a forced attack."""
    have = set(keys)
    return all(k in have for k in _ATTACK_KEYS)


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


def _required_unlock_names(world):
    """The pooled 'Unlock: X' item names this seed's GOAL requires the player to HOLD.

    Empty unless progressive mode is active AND ability_unlocks_required is on (the default). This is
    the ONE source both terminal conditions read: core._class_for upgrades these to `progression`,
    core.set_rules ANDs `state.has_all(...)` over them, and features/goal_locations appends them to
    `goalRequiredItems` -- so the AP-side completion_condition and the client-side Goal gate cannot
    drift, the same 2026-07-30 single-source discipline the Region Locks follow."""
    if not _progressive_active(world):
        return []
    opt = getattr(getattr(world, "options", None), "ability_unlocks_required", None)
    # DefaultOnToggle: absent => on. Only an explicit 0 opts out.
    if opt is not None and not int(getattr(opt, "value", 1)):
        return []
    names = dict(contract.ABILITY_UNLOCK_ITEM_NAMES)
    return [names[k] for k in _locked_keys(world)]


@register
class AbilityLock(Feature):
    name = "ability_lock"
    OPTIONS = {
        "locked_abilities": LockedAbilities,
        "ability_lock_mode": AbilityLockMode,
        "ability_unlocks_required": AbilityUnlocksRequired,
    }
    # No ITEMS: the seven unlock items are minted at a fixed id base in core.py (see module docstring).

    def create_items(self, world):
        # Progressive: one 'Unlock: X' per locked ability, appended before the filler tail so the pool
        # stays count-exact (each displaces one filler slot). create_item -> core._class_for decides
        # useful vs progression from ability_unlocks_required; no classification is baked here.
        if not _progressive_active(world):
            return []
        names = dict(contract.ABILITY_UNLOCK_ITEM_NAMES)
        keys = _locked_keys(world)
        items = [world.create_item(names[k]) for k in keys]
        # ROLL MUST COME EARLY (bobler, playtest): being without the dodge roll for hours is
        # miserable in a way the other locks are not -- and once the unlocks are cross-game
        # progression, Roll can otherwise land deep in a partner's world. Declare it to AP's
        # `early_items` (NOT local_early_items): Fill forces it into an early sphere but leaves it
        # exportable, so it is early WHEREVER it lands -- a partner's early game too. Only Roll, and
        # only when Roll is actually locked; early_items can only place an item the pool holds, which
        # `items` above guarantees. Applies in both required/opt-out modes -- the cripple is the same.
        if "roll" in keys:
            world.multiworld.early_items[world.player][names["roll"]] = 1
        # AN ATTACK MUST COME EARLY WHEN ALL FOUR ATTACK INPUTS ARE LOCKED (#1035, Alaric's ruling
        # 2026-08-25). With r1/r2/l1/l2 all locked the player holds no way to hit anything, and a
        # great many checks are kill-gated (boss defeats, enemy drops, every defeat-flag sweep
        # trigger) -- so the seed can expect kills it has made impossible. The conservative fix is
        # this seam, not a reachability rule: declare ONE attack unlock to `early_items` so a weapon
        # attack is guaranteed early WHEREVER it lands (exportable, exactly like Roll above), while
        # the logic graph is left untouched. #1035 stays open for the full logic-rule half.
        #
        # SPELLS DELIBERATELY DO NOT COUNT. Alaric, 2026-08-25: "spells don't count, you need an L
        # or R button to cast a spell." A staff or seal casts ON an attack input, so a caster with
        # all four locked is exactly as weaponless as anyone else -- there is no caster carve-out,
        # and the L/R unlocks are the only attack path this code recognises.
        #
        # r1 is the deterministic pick: it is the game's primary attack input, every weapon has one,
        # and a fixed choice keeps the declaration seed-independent (no draw to re-measure, no
        # dependence on world.random, and the same yaml always generates the same guarantee).
        # Fewer than four locked needs no forcing: an unlocked attack button is still a damage
        # source at start (fists at worst). Orthogonal to ability_unlocks_required -- the cripple is
        # the same whether the unlocks gate the goal or not, so this fires in both modes, like Roll.
        if _all_attacks_locked(keys):
            world.multiworld.early_items[world.player][names[_FORCED_EARLY_ATTACK]] = 1
        return items

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
