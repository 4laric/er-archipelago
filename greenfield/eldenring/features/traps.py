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
from ..spawn_trap_data import SPAWN_TRAPS, SPAWN_TRAP_KEYS

#: 🛑 CROSS-REPO CONTRACT with `er_logic::traps::LABEL_CAP`. The client retains a spawn label INLINE
#: so its `SpawnSpec` can stay `Copy`, and REFUSES a longer one rather than truncating -- a
#: truncated label would silently rename the creature in the one line the player ever reads.
#: `tools/datamine_spawn_traps.py` asserts the same ceiling when it emits the table; this pins it on
#: the consuming side too, because the tsv can be hand-edited.
LABEL_CAP = 24


#: The prefix the client dispatches on. Kept as a constant so the test can assert every name
#: carries it -- a trap named without it is a filler item that silently never fires.
TRAP_PREFIX = "Trap: "


def spawn_item_name(chr_id: int) -> str:
    """The item name a spawn trap for `chr_id` mints. THE PAYLOAD IS IN THE NAME.

    `Trap: Basilisk x3 (4150/41500060)` -- label, horde size, then the two ids the client cannot
    derive for itself.

    ⭐ THE THINK ROW IS NOT IN THE NAME, and its absence is proved rather than assumed. A model only
    enters this table if `NpcThinkParam` has a row at exactly `<chr>0000` -- that IS the eligibility
    rule -- so `think == chr_id * 10000` for all 390 rows, and the client derives it.
    `test_gf_spawn_traps` holds that premise against the real table; if it ever fails, the name can
    no longer express reality and the field has to come back. The npc row is NOT derivable (300 of
    390 differ from the template), so it stays.

    ⭐ THE PAYLOAD IS LAST, and the count sits with the label, because Archipelago fuzzy-matches item
    names in `!getitem` / `/send` (`Utils.get_intended_text`, 75% threshold). With 389 uncurated
    names shaped `Trap: cNNNN ...` they are near-identical to EACH OTHER, and a payload in the
    middle pushed the only distinguishing text past where the matcher weighs it. Leading with
    `Trap: c4630 x1` gives the match something to bite on.

    🛑 THE FORMAT IS ONLY FREE TO CHANGE UNTIL A TAG. Nothing has shipped it yet (the v0.3.12 window
    is open), so this reshaping costs nothing. After a release it is a compat break for every seed
    in flight, and the client refuses -- loudly, by design -- anything it cannot parse.

    🛑 WHY THE NAME AND NOT slot_data. A spawn trap is a SYNTHETIC item like every other trap: it
    declares `ITEMS` and no `ITEM_GRANTS`, and the client recognises it by NAME. Putting the ids in
    slot_data instead would be a CONTRACT MOVE -- a new key, both repos in lockstep, `CONTRACT_HASH`
    moving, a version bump -- to carry three integers the name can carry for free.

    🛑 THE COST, stated plainly: this name is a promise to another repository with nothing enforcing
    it. `er_logic::traps::SpawnSpec::from_item_name` parses exactly this shape and REFUSES anything
    else. `test_gf_spawn_traps` pins the format; the client pins its own parser. Change one, change
    both -- the failure mode is an item that arrives, is filler, and does nothing forever.
    """
    label, npc, _think, count = SPAWN_TRAPS[chr_id]
    return "%s%s x%d (%d/%d)" % (TRAP_PREFIX, label, count, chr_id, npc)

# The trap catalogue: option value -> item name. 🛑 BOTH SIDES OF THIS TABLE ARE PUBLIC.
# The KEY is a yaml value a player types and may not be renamed (rule 4). The VALUE is the string
# the client matches on; `er_logic::traps::Trap::from_item_name` carries the same list.
TRAPS = {
    "rune_thief": "Trap: Rune Thief",
    "no_flask": "Trap: No Flask",
    "runebear": "Trap: Runebear",
}



class Traps(OptionSet):
    """Which traps may appear in your world. Empty (default) = no traps at all.

    A trap is an item that makes your run briefly worse. They are FILLER: a trap never holds
    progression, and every trap in your pool replaces one junk item, so your seed does not grow.

    - **rune_thief** -- half your runes, gone.
    - **no_flask** -- your flask heals nothing for 20 seconds. You can still drink it; it just does
      nothing, and the charge is spent.
    - **runebear** -- a Runebear appears exactly where you are standing. Kill it and you keep the
      runes.
    - **basilisk** -- THREE basilisks appear where you are standing. One is a joke; three is the
      Death Blight mist, which kills outright. Killing you sends a DeathLink.

    Traps are sent to YOU by your own world like any other item, so in a multiworld somebody else
    may be the one who finds them.

    For any other enemy in the game, see `spawn_traps`.
    """
    display_name = "Traps"
    # 🛑 The union, not `TRAPS` alone: a curated spawn key is a yaml value exactly like a fixed
    # trap's, and leaving it out would make `traps: [basilisk]` an unknown-key error.
    valid_keys = frozenset(TRAPS) | frozenset(SPAWN_TRAP_KEYS)
    default = frozenset()


class SpawnTraps(OptionSet):
    """Extra enemies to drop on your own head, named by character model id (e.g. `4150`).

    THE ESCAPE HATCH. `traps` carries the enemies we curated and named; this takes any of the 390
    spawnable models in the game by raw id, for anyone who wants something specific standing on top
    of them. One appears where you are; the curated ones may come in numbers.

    Empty by default, and inert unless `trap_count` is above zero. An id that is not spawnable is a
    yaml error rather than an item that silently never fires -- 26 models are excluded because they
    have no AI row or no body (props like the Walking Mausoleum), and refusing them at generation is
    the point.

    Naming the same enemy here and in `traps` is harmless: it is one item either way.
    """
    display_name = "Spawn Traps"
    # Strings, because a yaml list of bare ints is easy to write and an OptionSet keys on str.
    # 🛑 `valid_keys` IS the validation. It is what turns `spawn_traps: [9999]` into a yaml error
    # instead of a filler item that arrives in-game and does nothing forever.
    valid_keys = frozenset(str(c) for c in SPAWN_TRAPS)
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


def _chosen(world, option: str) -> set:
    opt = getattr(world.options, option, None)
    return set(opt.value or ()) if opt is not None else set()


def enabled_traps(world) -> List[str]:
    """The `traps` option values this seed enabled, in catalogue order -- deterministic.

    🛑 Sorted by the catalogue rather than by the OptionSet, because an OptionSet is a `frozenset`
    and iterating one is not stable across runs. A seed must be reproducible from its yaml.
    """
    chosen = _chosen(world, "traps")
    return [k for k in TRAPS if k in chosen] + [k for k in sorted(SPAWN_TRAP_KEYS) if k in chosen]


def enabled_trap_names(world) -> List[str]:
    """Every distinct trap item NAME this seed may mint, in a deterministic order.

    Three sources feed one list: the fixed traps, the curated spawn keys, and raw model ids from
    `spawn_traps`. All three are walked in CATALOGUE order (never OptionSet order) so the result is
    a function of the yaml and not of frozenset iteration.

    🛑 DEDUPLICATED, order-preserving. `traps: [basilisk]` and `spawn_traps: ["4150"]` name the same
    creature and mint the same string; without this the round-robin would deal that one trap twice
    as often as the others, which is a silent weighting bug rather than a visible one.
    """
    names = []
    chosen = _chosen(world, "traps")
    for k in TRAPS:
        if k in chosen:
            names.append(TRAPS[k])
    for k in sorted(SPAWN_TRAP_KEYS):
        if k in chosen:
            names.append(spawn_item_name(SPAWN_TRAP_KEYS[k]))
    raw = _chosen(world, "spawn_traps")
    for c in sorted(SPAWN_TRAPS):
        if str(c) in raw:
            names.append(spawn_item_name(c))
    return list(dict.fromkeys(names))


def trap_items(world) -> List[str]:
    """The trap item NAMES this seed mints, dealt round-robin across everything enabled.

    Round-robin rather than random so the split is even and reproducible: with 8 traps and 2 kinds
    you get 4 and 4, every time, and a player who enabled two traps never rolls a seed with seven of
    one and one of the other.
    """
    chosen = enabled_trap_names(world)
    if not chosen:
        return []
    opt = getattr(world.options, "trap_count", None)
    n = int(opt.value) if opt is not None else 0
    if n <= 0:
        return []
    return [chosen[i % len(chosen)] for i in range(n)]


@register
class TrapsFeature(Feature):
    name = "traps"
    OPTIONS = {"traps": Traps, "trap_count": TrapCount, "spawn_traps": SpawnTraps}
    # FILLER, always. Rule 3: no progression may ride a trap, and `_class_for` never promotes these
    # because they are not required runes, gate runes, legacy keys or natural keys.
    #
    # 🛑 THE 390 SPAWN NAMES ARE DELIBERATELY ABSENT. `registry.allocate_item_ids` walks features in
    # import order handing out SEQUENTIAL ids, so declaring 390 names here would shift the AP id of
    # every feature-minted item registered after this one -- the exact renumbering `core.py` goes out
    # of its way to avoid for ASHEN_LOCK ("appending here leaves every existing id exactly where they
    # were"). They are registered in `core.py` instead, in their own block, at an id ARITHMETIC in
    # the chr model, so adding or removing a family renumbers nothing at all.
    ITEMS = {n: ItemClassification.filler for n in TRAPS.values()}
    # 🛑 NO `ITEM_GRANTS`. That absence is what makes a trap synthetic -- it never lands in
    # `_AP_IDS_TO_ITEM_IDS`, so the client is never told to hand the player an ER item for it, and
    # the "no ER mapping ... contract drift?" warn is answered by the client's name branch instead.

    def create_items(self, world):
        # Count-neutral by construction: core.create_items sizes filler off len(pool), so each trap
        # returned here displaces exactly one filler. OFF (empty OptionSet) -> [] -> a pool
        # byte-identical to one built before this feature existed.
        return [world.create_item(nm) for nm in trap_items(world)]
