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
    7772445, 7772449,             # Lamenter's Gaol key chests
    7772952,                      # Dectus Medallion (Left), Fort Haight chest
    7773579, 7773654,             # Finger Ruins bell interactions
    7773708,                      # Haligtree Secret Medallion (Right), Albus
    7773750,                      # Hole-Laden Necklace
    7900002,                      # Messmer's Kindling
))

# Data review, 2026-09-02: these are named boss rewards in confirmed regions. Great Wyrm
# Theodorix remains held because its generated region is explicitly unconfirmed.
_CERTIFIED_MAJOR_BOSS_WAVE1_APS = frozenset((
    7773788, 7773790, 7773791, 7773795, 7773800, 7773801, 7773863,
))

# Second data review, 2026-09-02: each row has an exact committed boss-kill award chain and stable
# region: Dragonkin Soldier -> Dragon Halberd (f530620), Golden Hippopotamus -> Aspects of the
# Crucible: Thorns (f510440), and Loretta -> Loretta's War Sickle (f510190). The other seven
# effective MajorBoss losses are finale-lifecycle rows and deliberately remain held.
CERTIFIED_MAJOR_BOSS_WAVE2_APS = frozenset((7770716, 7773797, 7900120))
CERTIFIED_MAJOR_BOSS_APS = (
    _CERTIFIED_MAJOR_BOSS_WAVE1_APS | CERTIFIED_MAJOR_BOSS_WAVE2_APS
)

# Alaric, 2026-08-04: the Golden Seed population was reviewed in game and hand-described. These are
# the 30 generated-HOLD rows whose region and lifecycle bars are otherwise clear. Deliberately omit
# the missable Roderika seed, both pre-burn Leyndell seeds, the two defaulted-region seeds, and the
# separately excluded Mohgwyn seed; those independent bars remain authoritative.
CERTIFIED_SEEDTREE_APS = frozenset((
    7770831, 7770884, 7771048, 7771144, 7771148, 7771484, 7771485, 7771552,
    7772599, 7772629, 7772645, 7772686, 7772741, 7772843, 7772845, 7772846,
    7772848, 7772895, 7772896, 7772951, 7773048, 7773085, 7773181, 7773818,
    7774156, 7774304, 7774471, 7774502, 7774525, 7900003,
))

# The same 2026-08-04 in-game pass named these four generated-HOLD Sacred Tears at their churches.
# f39207170 remains excluded: the review instead reported that it was seemingly not a real check.
CERTIFIED_CHURCH_APS = frozenset((7772708, 7772784, 7772879, 7772915))

# Data review, 2026-09-02: exact Revered Spirit Ash lot rows are joined to their MSB/coordinate
# placement and uniquely matching Samurai Gamers landmark in the generated region. Keep 7771807
# held because its landmark is explicitly after the Dancing Lion fight (a deeper internal gate),
# and 7773210 because region_dispute_worksheet.tsv still records Ancient Ruins|Enir Ilim.
CERTIFIED_REVERED_APS = frozenset((
    7771798, 7771811,             # Belurat: tree statue and bridge shadow-pot
    7771933,                      # Shadow Keep: Storehouse hanging specimen
    7772022,                      # Abyssal: Manse Hall inquisitor
    7773234, 7773399,             # Gravesite: Cliffroad and Ellac River Cave statues
    7773601,                      # Scadu Altus: Village of Flies hill altar
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
