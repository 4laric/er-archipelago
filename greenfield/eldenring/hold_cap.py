"""The goods hold-ceiling decision (#308) -- pure, AP-free, host-testable.

Separated from `core` on purpose: `core` imports Archipelago, so a test that wanted these two
functions would have to stand up an AP runtime to reach a pair of `dict` lookups. The rule this
repo already applies to the Rust client ("lift the decision into a pure predicate, and make
production CALL it") applies just as well on this side.

The datum behind the ceilings lives in `gen_data.py`, which derives `item_ids.GOODS_HOLD_CAP` from
`EquipParamGoods.maxNum` plus a scan of the three `common.emevd` pot counters. `core.create_items`
is the production caller.
"""


def hold_budget(caps, start_counts):
    """Remaining deliverable copies per item name: the game's stack ceiling MINUS what the start
    loadout already spends of it.

    Both terms draw on ONE finite stack, and neither the pool nor the loadout can see the total on
    its own -- which is exactly how 9 Hefty Cracked Pots came to be granted at spawn on top of 10
    already held, against a ceiling of 10 (Alaric, 2026-08-03). A negative result is kept as
    negative rather than clamped to 0: it means the LOADOUT alone is already over the ceiling,
    which is a different and worse bug than a pool overflow, and flattening it here would hide it.
    """
    return {nm: cap - start_counts.get(nm, 0) for nm, cap in caps.items()}


def hold_slot_available(budget, name):
    """Can one more copy of `name` be delivered? Names with no recorded ceiling are unbounded.

    🛑 Absence from `budget` means "no ceiling to enforce", NOT "ceiling zero". Consumables and
    every non-goods item are deliberately absent (see gen_data.py), so failing closed here would
    clamp the entire pool to nothing -- the loudest possible version of this bug, and the one a
    reflex "be safe by default" would introduce.
    """
    return budget.get(name, 1) > 0
