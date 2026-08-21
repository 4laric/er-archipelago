"""Spare-row coloring for shop preview goods (issue #937). Pure, stdlib-only, host-tested.

THE PROBLEM. Every foreign/lock/unsellable shop slot needs a spare EquipParamGoods row to carry its
AP name + flower, the datamined pool has ~79 rows, and a seed can have up to ~500 such slots. The old
draw handed out rows first-come until the pool ran dry, then parked every remaining slot on the LAST
row -- whose FMG entry can hold only one string, so the client folded all of them to the shared
"Archipelago Items" label (world #231). Players read shelves of identical labels.

THE FIX IS A SCOPE CHANGE, NOT A BIGGER POOL. A row's name must be unambiguous only among the slots
that can be ON SCREEN TOGETHER -- one shop menu at a time -- and a menu shows exactly the rows in the
(begin, end) range its ESD passes to the opener (shop_data.SHOP_OPEN_SCOPES, from
tools/datamine_shop_open_ranges.py). So:

  * REPAINTABLE slots -- every menu that can show them is an `OpenRegularShop` menu, the one opener
    the client detours (ESD command 22) and repaints names for at shop open -- may SHARE spare rows
    across menus. They only need distinct rows within each single menu: graph coloring, where the
    busiest menu (the Twin Maiden re-sell, 31 checks) bounds the colors needed at ~a third of the
    pool. These are colored FIRST, from the low (describable, redirectable) end of the pool, so the
    class the fix exists for can never be starved by the class it cannot help.
  * PRIVATE slots -- shown by any opener the client does not repaint (Enia's transposition menu,
    Champions/DragonCommunion/Dupe/Puppet shops), or by no harvested scope at all. Their baseline
    label must stand alone, so each needs a row NOBODY else uses: first-come from the remaining pool,
    exactly the old draw's behaviour for exactly the menus the old draw was all we had for.
  * OVERFLOW -- private demand past the pool parks on the reserved LAST row, shared, folding to the
    honest "Archipelago Items" label. Same degradation as before, now confined to non-repaintable
    menus. (A repaintable slot overflows only if one menu holds more slots than the whole pool,
    which no vanilla menu does; the code still degrades rather than crashes.)

Slots whose rows appear in NO harvested scope are bucketed per shop block (row // 100) -- the
same-menu superset -- and treated as private. A slot with rows in BOTH a repaintable and a
non-repaintable scope is private (its Enia appearance cannot be repainted).

Determinism: everything follows the caller's slot order and the scope list order; no hashing, no
randomness. The caller feeds `multiworld.get_locations()` order, same as the old draw.
"""
from collections import OrderedDict

REPAINTABLE_OPENERS = frozenset({"OpenRegularShop"})


def color_spare_rows(slots, scopes, n_colors, repaintable_openers=REPAINTABLE_OPENERS):
    """Assign each slot a pool color (0-based index) so no two slots visible in one menu share one.

    slots:  ordered iterable of (key, row_ids) -- key is opaque (ap-id str), row_ids the slot's
            vanilla ShopLineupParam row id(s) (a flag can sit on several rows; SHOP_ROW_IDS).
    scopes: iterable of (opener, begin, end) display scopes (shop_data.SHOP_OPEN_SCOPES).
    n_colors: pool size available to this call (spares left after the lock head).

    Returns (colors, overflow):
      colors:   OrderedDict key -> color int in [0, n_colors); insertion order = input order.
      overflow: list of keys parked on the shared last color (n_colors - 1), in input order.
    A key appears in exactly one of the two. n_colors <= 0 returns everything as overflow with no
    colors to give (the caller's no-spares case).
    """
    slots = list(slots)
    scopes = list(scopes)
    if n_colors <= 0:
        return OrderedDict(), [k for k, _ in slots]

    # 1. Scope membership + class per slot. A rangeless row gets a per-block pseudo-scope: rows of
    #    one block usually sit on one shelf, and a superset constraint can only over-separate.
    memberships = []  # (key, frozenset(scope_key), repaintable: bool)
    for key, rows in slots:
        mem = set()
        all_repaintable = True
        for r in rows:
            hit = False
            for i, (op, a, b) in enumerate(scopes):
                if a <= r <= b:
                    mem.add(i)
                    hit = True
                    if op not in repaintable_openers:
                        all_repaintable = False
            if not hit:
                mem.add(("blk", r // 100))
                all_repaintable = False
        memberships.append((key, frozenset(mem), all_repaintable and bool(mem)))

    colors = OrderedDict()
    overflow = []
    shared_last = n_colors - 1          # the overflow row; excluded from both passes below
    used_in_scope = {}                  # scope_key -> set of colors taken there

    # 2. Repaintable slots first, smallest free color per menu-conflict set. Low indices are the
    #    described/redirectable end of the pool, and reuse keeps the spent-index watermark (the
    #    requiresClientFeatures trigger upstream) as low as the busiest single menu.
    for key, mem, repaintable in memberships:
        if not repaintable:
            continue
        taken = set()
        for s in mem:
            taken |= used_in_scope.get(s, set())
        c = next((i for i in range(shared_last) if i not in taken), None)
        if c is None:                   # a single menu wider than the pool: degrade, don't crash
            overflow.append(key)
            continue
        colors[key] = c
        for s in mem:
            used_in_scope.setdefault(s, set()).add(c)

    # 3. Private slots: first-come, each a color no one else touches (their label must stand alone
    #    in a menu the client cannot repaint). The ascending cursor skips every repaintable color;
    #    since it only moves forward, a private color can never be handed out twice.
    repaint_used = set(colors.values())
    cursor = 0
    for key, mem, repaintable in memberships:
        if repaintable:
            continue
        while cursor < shared_last and cursor in repaint_used:
            cursor += 1
        if cursor >= shared_last:
            overflow.append(key)
            continue
        colors[key] = cursor
        cursor += 1

    # Re-key colors into input order (passes appended in class order, and callers zip against the
    # slot walk). Overflow keys keep input order for the same reason.
    ordered = OrderedDict()
    over_set = set(overflow)
    overflow = [k for k, _ in slots if k in over_set]
    for k, _ in slots:
        if k in colors:
            ordered[k] = colors[k]
    return ordered, overflow
