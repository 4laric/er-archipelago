"""Maintainer-adjudicated progression hosts backed by direct in-game review.

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
_CERTIFIED_MAJOR_BOSS_WAVE1_APS = frozenset((
    7773790, 7773792, 7773793, 7773797, 7773802, 7773803, 7773865,
))

# Second data review, 2026-09-02: each row has an exact committed boss-kill award chain and stable
# region: Dragonkin Soldier -> Dragon Halberd (f530620), Golden Hippopotamus -> Aspects of the
# Crucible: Thorns (f510440), and Loretta -> Loretta's War Sickle (f510190). The other seven
# effective MajorBoss losses are finale-lifecycle rows and deliberately remain held.
CERTIFIED_MAJOR_BOSS_WAVE2_APS = frozenset((7770716, 7773799, 7900120))
CERTIFIED_MAJOR_BOSS_APS = (
    _CERTIFIED_MAJOR_BOSS_WAVE1_APS | CERTIFIED_MAJOR_BOSS_WAVE2_APS
)

# Alaric, 2026-08-04: the Golden Seed population was reviewed in game and hand-described. These are
# the 30 generated-HOLD rows whose region and lifecycle bars are otherwise clear. Deliberately omit
# the missable Roderika seed, both pre-burn Leyndell seeds, the two defaulted-region seeds, and the
# separately excluded Mohgwyn seed; those independent bars remain authoritative.
CERTIFIED_SEEDTREE_APS = frozenset((
    7770832, 7770885, 7771049, 7771145, 7771149, 7771485, 7771486, 7771553,
    7772601, 7772631, 7772647, 7772688, 7772743, 7772845, 7772847, 7772848,
    7772850, 7772897, 7772898, 7772953, 7773050, 7773087, 7773183, 7773820,
    7774164, 7774314, 7774481, 7774512, 7774535, 7900003,
))

# The same 2026-08-04 in-game pass named these four generated-HOLD Sacred Tears at their churches.
# f39207170 remains excluded: the review instead reported that it was seemingly not a real check.
CERTIFIED_CHURCH_APS = frozenset((7772710, 7772786, 7772881, 7772917))

# Data review, 2026-09-02: exact Revered Spirit Ash lot rows are joined to their MSB/coordinate
# placement and uniquely matching Samurai Gamers landmark in the generated region. Keep 7771808
# held because its landmark is explicitly after the Dancing Lion fight (a deeper internal gate),
# and 7773212 because region_dispute_worksheet.tsv still records Ancient Ruins|Enir Ilim.
CERTIFIED_REVERED_APS = frozenset((
    7771799, 7771812,             # Belurat: tree statue and bridge shadow-pot
    7771934,                      # Shadow Keep: Storehouse hanging specimen
    7772023,                      # Abyssal: Manse Hall inquisitor
    7773236, 7773401,             # Gravesite: Cliffroad and Ellac River Cave statues
    7773603,                      # Scadu Altus: Village of Flies hill altar
))

CERTIFIED_PROGRESSION_HOST_APS = (
    CERTIFIED_REMEMBRANCE_APS
    | CERTIFIED_GREAT_RUNE_APS
    | CERTIFIED_KEY_ITEM_APS
    | CERTIFIED_MAJOR_BOSS_APS
    | CERTIFIED_SEEDTREE_APS
    | CERTIFIED_CHURCH_APS
    | CERTIFIED_REVERED_APS
)
