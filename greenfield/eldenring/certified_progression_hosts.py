"""Maintainer-adjudicated progression hosts backed by direct boss-drop review.

This is deliberately separate from the generated external-corroboration ledger. Entries here are
explicit gameplay adjudications, not claims that two external source families matched. The finale
lifecycle bar remains authoritative over this allow-list.
"""

# Alaric, 2026-09-02: every Remembrance is dropped by its named boss in the check's region.
CERTIFIED_REMEMBRANCE_APS = frozenset((
    7770007,
    7770653, 7770654, 7770655, 7770656, 7770658, 7770659,
    7770660, 7770661, 7770662, 7770663, 7770664, 7770665, 7770666, 7770667, 7770668,
    7770670, 7770671, 7770672, 7770673, 7770674, 7770675, 7770676, 7770678,
    7770680,
))

# Alaric, 2026-09-02: these Great Runes are direct rewards from the named regional bosses.
CERTIFIED_GREAT_RUNE_APS = frozenset((7770002, 7770004))

# Alaric, 2026-09-02: Messmer drops Messmer's Kindling in Shadow Keep.
CERTIFIED_KEY_ITEM_APS = frozenset((7900002,))

CERTIFIED_PROGRESSION_HOST_APS = (
    CERTIFIED_REMEMBRANCE_APS | CERTIFIED_GREAT_RUNE_APS | CERTIFIED_KEY_ITEM_APS
)
