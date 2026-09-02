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

# Data review, 2026-09-02: these stable, region-confirmed checks are the acquisition points for
# their named keys. The two Finger Ruins ObjActs and both Lamenter's Gaol door tiers are also
# represented by exact access claims in v060-current/evidence.tsv. Questline-missable checks,
# Secret Rite Scroll's explicit surface exclusion, and every unresolved predicate stay out.
CERTIFIED_KEY_ITEM_APS = frozenset((
    7772446, 7772450,             # Lamenter's Gaol key chests
    7772954,                      # Dectus Medallion (Left), Fort Haight chest
    7773581, 7773656,             # Finger Ruins bell interactions
    7773710,                      # Haligtree Secret Medallion (Right), Albus
    7773752,                      # Hole-Laden Necklace
    7900002,                      # Messmer's Kindling
))

# Data review, 2026-09-02: these are named boss rewards in confirmed regions. Great Wyrm
# Theodorix remains held because its generated region is explicitly unconfirmed.
CERTIFIED_MAJOR_BOSS_APS = frozenset((
    7773790, 7773792, 7773793, 7773797, 7773802, 7773803, 7773865,
))

CERTIFIED_PROGRESSION_HOST_APS = (
    CERTIFIED_REMEMBRANCE_APS | CERTIFIED_GREAT_RUNE_APS | CERTIFIED_KEY_ITEM_APS
    | CERTIFIED_MAJOR_BOSS_APS
)
