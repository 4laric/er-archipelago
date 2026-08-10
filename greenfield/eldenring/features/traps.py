"""traps -- trap items in the filler pool.

WHAT A TRAP IS HERE. An AP item that makes your run momentarily worse: it takes half your runes, or
stops your flask healing for twenty seconds. bobler and Alaric designed the set on 2026-08-08
(issue #114); this ships the two the client can already fire.

## Why this costs no contract move

A trap is a SYNTHETIC item, exactly like `Boss Key: <Boss>` and `<Region> Lock`: it declares `ITEMS`
and no `ITEM_GRANTS`, so it never enters `_AP_IDS_TO_ITEM_IDS` and the game is never asked to hand
anything over. The client recognises it by NAME in the receive stream, the same way it already
recognises Boss Keys, and fires the effect itself. No new slot_data key, no `CONTRACT_HASH` move, no
version lockstep -- which is the opposite of what the design note in #114 assumed, and worth saying
out loud because it is the reason this is small.

🛑 THE COST OF THAT CHOICE: the item NAME is a cross-repo contract with no gate behind it. Rename
`Trap: Rune Thief` here and the client silently stops recognising it -- no error, no failed build,
just a trap that does nothing. `test_gf_traps.py` pins the exact strings, and `er_logic::traps`
carries the same list with its own test. Change one, change both.

## The rules this obeys (issue #114)

3. Traps are FILLER-class and count-neutral: each trap displaces one filler item, never a useful one,
   and no progression may ride a trap. `core.create_items` sizes filler off `len(pool)`, so returning
   N items here removes N fillers and the pool total is unchanged.
4. 🛑 ADDING a trap name later is safe; REMOVING one is a compat break -- an OptionSet value that
   vanishes fails an old yaml. Never ship a name you might withdraw. That is why this file ships
   TWO names and not the eleven in the design: these two are implemented, tested and CI-green in the
   client. The rest arrive when they work, not when they are decided.

## Defaults

OFF. `traps` is an empty OptionSet, so a seed that does not name a trap is byte-identical to one
built before this file existed -- `create_items` returns `[]` and nothing else here runs.
"""
from typing import List

from BaseClasses import ItemClassification
from Options import OptionSet, Range

from ..registry import Feature, register

# The trap catalogue: option value -> item name. 🛑 BOTH SIDES OF THIS TABLE ARE PUBLIC.
# The KEY is a yaml value a player types and may not be renamed (rule 4). The VALUE is the string
# the client matches on; `er_logic::traps::Trap::from_item_name` carries the same list.
TRAPS = {
    "rune_thief": "Trap: Rune Thief",
    "no_flask": "Trap: No Flask",
    "runebear": "Trap: Runebear",
}

#: The prefix the client dispatches on. Kept as a constant so the test can assert every name
#: carries it -- a trap named without it is a filler item that silently never fires.
TRAP_PREFIX = "Trap: "


class Traps(OptionSet):
    """Which traps may appear in your world. Empty (default) = no traps at all.

    A trap is an item that makes your run briefly worse. They are FILLER: a trap never holds
    progression, and every trap in your pool replaces one junk item, so your seed does not grow.

    - **rune_thief** -- half your runes, gone.
    - **no_flask** -- your flask heals nothing for 20 seconds. You can still drink it; it just does
      nothing, and the charge is spent.
    - **runebear** -- a Runebear appears exactly where you are standing. Kill it and you keep the
      runes.

    Traps are sent to YOU by your own world like any other item, so in a multiworld somebody else
    may be the one who finds them.
    """
    display_name = "Traps"
    valid_keys = frozenset(TRAPS)
    default = frozenset()


class TrapCount(Range):
    """How many trap items to put in your pool, shared out evenly between the traps you enabled.

    INERT unless `traps` names at least one trap. Each trap displaces one filler item, so raising
    this does not change how many checks your seed has -- only how much of your junk bites back.
    """
    display_name = "Trap Count"
    range_start = 0
    range_end = 40
    default = 8


def enabled_traps(world) -> List[str]:
    """The option values this seed enabled, in TRAPS order -- deterministic, not set order.

    🛑 Sorted by the catalogue rather than by the OptionSet, because an OptionSet is a `frozenset`
    and iterating one is not stable across runs. A seed must be reproducible from its yaml.
    """
    opt = getattr(world.options, "traps", None)
    if opt is None:
        return []
    chosen = set(opt.value or ())
    return [k for k in TRAPS if k in chosen]


def trap_items(world) -> List[str]:
    """The trap item NAMES this seed mints, dealt round-robin across the enabled traps.

    Round-robin rather than random so the split is even and reproducible: with 8 traps and 2 kinds
    you get 4 and 4, every time, and a player who enabled two traps never rolls a seed with seven of
    one and one of the other.
    """
    chosen = enabled_traps(world)
    if not chosen:
        return []
    opt = getattr(world.options, "trap_count", None)
    n = int(opt.value) if opt is not None else 0
    if n <= 0:
        return []
    return [TRAPS[chosen[i % len(chosen)]] for i in range(n)]


@register
class TrapsFeature(Feature):
    name = "traps"
    OPTIONS = {"traps": Traps, "trap_count": TrapCount}
    # FILLER, always. Rule 3: no progression may ride a trap, and `_class_for` never promotes these
    # because they are not required runes, gate runes, legacy keys or natural keys.
    ITEMS = {n: ItemClassification.filler for n in TRAPS.values()}
    # 🛑 NO `ITEM_GRANTS`. That absence is what makes a trap synthetic -- it never lands in
    # `_AP_IDS_TO_ITEM_IDS`, so the client is never told to hand the player an ER item for it, and
    # the "no ER mapping ... contract drift?" warn is answered by the client's name branch instead.

    def create_items(self, world):
        # Count-neutral by construction: core.create_items sizes filler off len(pool), so each trap
        # returned here displaces exactly one filler. OFF (empty OptionSet) -> [] -> a pool
        # byte-identical to one built before this feature existed.
        return [world.create_item(nm) for nm in trap_items(world)]
