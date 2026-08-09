"""progression_surface -- CONFINE this world's own progression to a small, high-confidence location
set (v0.2; matt-style "important locations" restriction, not a soft weight).

matt's standalone ER randomizer HARD-RESTRICTS key items to an "important locations" whitelist (major
bosses always, plus opt-in golden-seed trees / sacred-tear churches / shops / other bosses); a separate
"bias slider" only tunes difficulty WITHIN that set. The bedrock AP port only got the SOFT half (mark
PRIORITY, advancement gets first crack -- features/curated_fill here). This feature adds the HARD half:
it pulls this world's OWN progression out of the pool and places it, via Fill.fill_restrictive, ONTO the
selected surface only -- default = MajorBoss (the ~24 boss_arena arena majors + the hand-picked
MAJOR_BOSS_EXTRAS, tagged 'MajorBoss' in location_tags). Everything else lands normally.

WHAT COUNTS AS "OUR PROGRESSION": the region Locks (the region-lock spine's gate items) plus any
conditionally-progression items -- required Great Runes (great_runes goal), Leyndell-gate runes, legacy
dungeon keys. Boss Keys are DELIBERATELY EXEMPT: with boss_keys on there are ~24 of them, they'd swamp
the tiny surface, and features/boss_locks already keeps them reachable in logic.

FEASIBILITY LADDER (never FillError): a surface smaller than the number of locks to place -- or a seed
with no sphere-0 anchor -- can't host every lock. So strict mode WIDENS the allowed surface one grouped
rung at a time, highest-confidence first (MajorBoss -> +Remembrance,GreatRune -> +KeyItem -> +Boss ->
+Legendary -> +Seedtree,Church) and,
for anything still unplaced, RETURNS it to the pool for normal fill. Because the terminal action is
"back to the pool", generation can never hard-fail from this feature: worst case it degrades to v0.1
scatter. (The +Seedtree rung also unlocks the 2 Roundtable-Hold Golden Seeds, an always-reachable
sphere-0 bootstrap, so a no-precollect seed can still seed the lock chain.)

BASE-STATE FIX: reachability during the pre-fill is evaluated from mw.get_all_state(False) AFTER the
restricted items are pulled -- so the rest of the pool (Boss Keys, foreign advancement, any precollected
region Lock) counts as available, and a Boss-Key-gated boss check doesn't look falsely unreachable.
Placed locks are collected (lock=True) so multiworld progression-balancing can't later move them off the
surface. Runs from core.pre_fill; supersedes curated_fill when the mode is soft/strict.
"""
from Options import OptionSet, Choice, DefaultOnToggle, Range
from ..registry import Feature, register
from .. import contract

try:
    from ..location_tags import LOCATION_TAGS
except Exception:  # not yet generated -> feature is a no-op
    LOCATION_TAGS = {}


# Grouped widen order for the feasibility ladder, HIGHEST-CONFIDENCE FIRST. Each group is ADDED to the
# user's base surface in turn. The order is a confidence ranking: Remembrance/GreatRune are the same
# named demigods' guaranteed drops (≈ MajorBoss certainty); KeyItem is a small, hand-reviewable set (~14)
# so it comes BEFORE Legendary, which is a large scattered set (~84) nobody can vouch for from memory;
# Boss (the fixed minor-boss arenas) sits between them; Seedtree/Church (the collectible markers) stay
# last. Shop is intentionally NOT here: it would dump locks onto the hundreds of hub shop slots and
# defeat the restriction -- Shop is only ever in play if the user explicitly selects it in the base.
_WIDEN_GROUPS = [["Remembrance", "GreatRune"], ["KeyItem"], ["Boss"], ["Legendary"], ["Seedtree", "Church"]]
_BOSS_KEY_PREFIX = "Boss Key:"


class ProgressionSurface(OptionSet):
    """WHICH LOCATIONS MAY HOLD PROGRESSION. The location classes allowed to host this world's own
    progression (region Locks, any required/gate Great Runes, legacy keys) -- and, in a multiworld,
    the classes where OTHER players' progression can land in your world.

    Default: the major bosses and remembrances, the great runes, the key items, and the collectathon
    lines -- Sacred Tears (Church), Golden Seeds (Seedtree), Scadutree Fragments and Revered Spirit
    Ashes for the DLC -- plus ShopSlot.

    🛑 NO COUNT HERE ON PURPOSE. This said "193 locations" until 2026-08-02, when the surface that
    could actually HOST an item was 156. 193 was a TAG count: it never subtracted the checks barred
    from carrying progression (guessed region, missable, erdtree-burn, surface-excluded, hub
    merchant). That is the same mistake missable_barred_aps was written to fix for the missable set,
    and it came back because the number lived in prose. It also MOVES -- every in-game region
    confirmation changes it (re-anchoring two Liurnia Golden Seeds shifted the default 154 -> 156 in
    a single commit). So the count lives in ONE place, regenerated and drift-gated:

        greenfield/surface_confidence.tsv   (tools/build_surface_confidence.py)

    which prices every class: tagged, how many each bar costs it, and how many can host. Quote that
    file, never a number typed into a docstring.

    ShopSlot is AT MOST one slot per merchant, never every shop row: a merchant enters the pool once,
    so however large their stock they can hold at most one progression item and cannot dominate the
    surface by breadth. The pinned slot is a ware that merchant ALONE sells (one stock flag game-wide,
    so the location is unambiguous), stocked from the start and with a resolved region; merchants with
    no such ware are skipped at regen (location_tags.SHOP_SLOT_SKIPS lists them with reasons). Use
    `Shop`/`ShopNonSpell` instead if you actually want a merchant-heavy seed -- be aware that is
    roughly three quarters of the surface (see surface_confidence.tsv) and the game becomes "farm
    runes, buy your progression".

    Narrowing is safe: the feasibility ladder widens automatically rather than failing to generate, and
    an EMPTY set turns the confinement off entirely (progression scatters as vanilla AP fill decides).
    Basin = Crystal Tears; Boss = every boss-healthbar drop; Legendary = the param-rarity legendaries."""
    display_name = "Progression Surface"
    # The v0.2 default. This was three classes (33 locations) for one reason: the location DATA could
    # not be trusted, so it was held to what a human could hand-verify. The provenance work (MSB/EMEVD
    # ground truth, the region oracle, the phantom-flag guard) removed that constraint, and the category
    # tags are now derived from what each flag's ItemLotParam lot actually GRANTS -- audited against
    # ground truth: Sacred Tear 13/13, Golden Seed 43/43, Scadutree Fragment 46/46, Revered 23/23.
    # Single-sourced in contract.py: the AP-free tracker generator needs this same selection and
    # cannot import an AP OptionSet. See contract.SURFACE_DEFAULT_CLASSES.
    default = contract.SURFACE_DEFAULT_CLASSES
    valid_keys = frozenset(contract.SURFACE_CLASSES)

    @staticmethod
    def wizard_key_meta():
        """Per-key presentation for the options wizard. Read by tools/dump_options_metadata.py.

        A GENERIC hook (`wizard_key_meta` on any option class), so the dumper never learns this
        option's name and the next set-valued option cannot grow a second, divergent way of doing
        the same thing. `valid_keys` is untouched and stays the authoritative sorted list -- this is
        additive, and a renderer that ignores it still works.

        `contains` is DERIVED from LOCATION_TAGS on every dump, not carried here. The wizard draws
        it to say "you already have these" -- and the one time this lattice was written down by hand
        (a comment in contract.py) it sat INVERTED for months.
        """
        return {
            "keys": surface_class_meta(),
            "families": [{"id": fid, "label": lab} for fid, lab, _ in SURFACE_CLASS_FAMILIES],
            "contains": class_containment(),
        }


class ProgressionSurfaceMode(Choice):
    """How the Progression Surface is enforced. off = v0.1 behavior (curated_fill toggle honored).
    soft = mark-and-spill over the surface (old curated_fill semantics: first crack, leftovers scatter).
    strict = CONFINE this world's progression to the surface, widening only via the feasibility ladder
    when the surface can't host every lock. Default strict."""
    display_name = "Progression Surface Mode"
    option_off = 0
    option_soft = 1
    option_strict = 2
    default = 2


class ProgressionBias(Range):
    """How hard your Region Locks are pulled toward YOUR OWN world. 0 (default) is no pull at all --
    every Lock is an ordinary multiworld item and can end up in another player's game, so you may
    well be waiting on somebody else to find your way into Liurnia. That is Archipelago working as
    intended, and it is the default on purpose. 100 pins every Lock at home.

    It is a share, not a mood: at 40, about 40% of your Locks are reserved for your own Progression
    Surface and the other 60% go into the multiworld pool.

    🛑 A LOCK IN THE POOL IS STILL CURATED. It is held to the same Progression Surface every other
    player's progression is held to -- it just lands on SOMEBODY'S boss or remembrance rather than
    necessarily yours. Lowering this trades away where your keys are, not whether they sit on
    checks worth finding. The knob that trades the curation itself is Confine Foreign Progression,
    and it is deliberately a separate one.

    MEASURED at 0, over 740 generations: in a two-slot Elden Ring multiworld about 45% of Locks
    leave their own world and ~90% of all placed Locks sit on a surface check; four slots pushes
    travel to 60-70%. In a CROSS-GAME multiworld expect most of your travelling Locks to land in the
    partner game rather than spread evenly -- a partner has no surface of its own to compete with
    ours, so it absorbs what our surface will not hold.

    No effect in a solo seed (there is nowhere else for a Lock to go), nor in the modes that mint no
    Lock items at all (natural progression, vanilla placement)."""
    display_name = "Progression Bias"
    range_start = 0
    range_end = 100
    default = 0


class ConfineForeignProgression(DefaultOnToggle):
    """Confine OTHER players' progression to your Progression Surface too, not just your own.

    ON (default): in a multiworld, another world's advancement items may only be placed on your
    surface locations -- the same high-confidence checks your own progression is curated onto --
    never on your filler checks. This is the option that trades the CURATION away; Progression Bias
    only decides WHOSE surface your Locks land on. Turning this off is what lets progression scatter
    onto crafting materials, in both directions. So a foreign key spell lands on a major-boss/remembrance/key-item check of yours,
    not on a random Smithing Stone pickup. OFF: foreign progression scatters across any reachable
    location of yours, which is standard Archipelago behaviour.

    No effect in a solo seed, or when Progression Surface Mode is off. It never blocks generation:
    your OWN progression keeps its feasibility-ladder + spill safety valve, and foreign progression
    that will not fit your surface simply lands in its own world instead (only YOUR filler checks are
    barred to it -- other worlds are untouched)."""
    display_name = "Confine Foreign Progression"


# ---- PRESENTATION: what the OPTIONS WIZARD shows for each class -----------------------------------
# The wizard rendered `valid_keys` as RAW KEYS, SORTED ALPHABETICALLY, with no per-key text. Three
# things were wrong with that and none of them are cosmetic:
#
#   1. THE KEYS DO NOT NAME WHAT THEY SELECT. `Church` is not "church locations", it is the 13 Sacred
#      Tears; `Basin` is Crystal Tears; `Seedtree` is Golden Seeds. A player ticking `Church`
#      reasonably believed they were opening up churches. Worse, the SAME concept had two names in two
#      adjacent fields of the same page: Crystal Tears are `Basin` here and `crystal_tears` in
#      keep_local / exclude_local_item_only.
#   2. ALPHABETICAL SCATTERED THE FAMILIES. Boss / FieldBoss / LegacyBoss / MajorBoss landed in four
#      separate places in the grid, and the three Shop classes in three.
#   3. THE GRID HID THE LATTICE. Most of these classes CONTAIN each other (see class_containment),
#      so ticking a broad class silently makes narrower boxes no-ops -- with no signal at all.
#
# Renaming the KEYS is a compat break: AP 0.6.7 Options.py `VerifyKeys.verify_keys` RAISES OptionError
# on an unknown key, so every yaml in the wild saying `Church` would HARD-FAIL generation, not
# silently drop. So the keys stay and the LABEL is the fix; renaming them (with the old names kept as
# deprecated aliases) is a separate, deliberate change.
#
# DISPLAY ORDER LIVES HERE, not in contract.SURFACE_CLASSES -- that list's order is a determinism
# handle for the ladder and must never be rearranged (see the comment on it).
SURFACE_CLASS_FAMILIES = (
    ("bosses", "Bosses", ("Boss", "MajorBoss", "LegacyBoss", "FieldBoss", "Remembrance", "GreatRune")),
    ("collectathon", "Collectathon lines",
     ("Seedtree", "Church", "Basin", "Fragment", "Revered")),
    ("merchants", "Merchants", ("ShopSlot", "ShopNonSpell", "Shop")),
    ("items", "Items", ("KeyItem", "Legendary")),
)

# key -> (label, hint). The label says what the class IS in the words the game uses; the hint says
# what it costs you to pick it. Kept short on purpose: the option's own docstring carries the essay.
SURFACE_CLASS_LABELS = {
    "Boss":         ("Any boss drop",
                     "Every enemy the game gives a boss healthbar. Contains all the boss classes "
                     "below, so ticking this makes them redundant."),
    "MajorBoss":    ("Major bosses",
                     "Remembrance and great-rune arena bosses, plus curated majors for the regions "
                     "that have none. Contains Remembrances and Great Runes."),
    "LegacyBoss":   ("Legacy dungeon bosses",
                     "Bosses standing inside a legacy dungeon."),
    "FieldBoss":    ("Overworld bosses",
                     "Field, evergaol and dragon bosses out in the open world. The least "
                     "region-confident boss class -- 22 of them sit on a guessed region."),
    "Remembrance":  ("Remembrances",
                     "The Remembrance a great boss drops."),
    "GreatRune":    ("Great Runes",
                     "The seven Great Runes."),
    "Seedtree":     ("Golden Seeds",
                     "The 43 Golden Seed pickups."),
    "Church":       ("Sacred Tears",
                     "The 13 Sacred Tears in the ruined churches -- NOT all church locations."),
    "Basin":        ("Crystal Tears",
                     "Physick tears. The same items keep_local calls `crystal_tears`."),
    "Fragment":     ("Scadutree Fragments",
                     "Shadow of the Erdtree. Ignored in a base-game seed."),
    "Revered":      ("Revered Spirit Ashes",
                     "Shadow of the Erdtree. Ignored in a base-game seed."),
    "ShopSlot":     ("One slot per merchant",
                     "At most ONE ware per merchant, so no shop can dominate the surface by the "
                     "size of its stock. 12 slots."),
    "ShopNonSpell": ("General merchants",
                     "Every merchant slot except a dedicated spell vendor's stock. 442 checks -- "
                     "picking this makes the seed mostly 'farm runes, buy your progression'."),
    "Shop":         ("Every merchant slot",
                     "All 562 shop rows, spell vendors included. Contains the two classes above."),
    "KeyItem":      ("Key items",
                     "The hand-reviewed quest and door keys."),
    "Legendary":    ("Legendary items",
                     "Everything the params rank rarity 3. Enia's buy-only remembrance store is "
                     "excluded from the surface whatever you pick here."),
}


def surface_class_meta(classes=None):
    """Ordered [{key, label, hint, family, family_label}] for the wizard. RAISES on a gap.

    🛑 LOUD, not defaulted. A class added to contract.SURFACE_CLASSES with no label would otherwise
    render as a bare key in a grid of labelled ones -- the exact state this function exists to end,
    reintroduced silently for the newest class. Same for a class that no family claims: it would
    simply not be drawn, and the player would have no way to select something the world offers.
    """
    vocab = list(classes if classes is not None else contract.SURFACE_CLASSES)
    placed = {}
    for fam, fam_label, keys in SURFACE_CLASS_FAMILIES:
        for k in keys:
            if k in placed:
                raise ValueError("surface class %r is in two families (%s, %s)"
                                 % (k, placed[k][0], fam))
            placed[k] = (fam, fam_label)
    missing_family = [c for c in vocab if c not in placed]
    if missing_family:
        raise ValueError("surface classes with no family, so the wizard would never draw them: %s "
                         "-- add them to SURFACE_CLASS_FAMILIES" % ", ".join(missing_family))
    stray = [k for k in placed if k not in vocab]
    if stray:
        raise ValueError("SURFACE_CLASS_FAMILIES names classes outside the vocabulary: %s"
                         % ", ".join(sorted(stray)))
    missing_label = [c for c in vocab if c not in SURFACE_CLASS_LABELS]
    if missing_label:
        raise ValueError("surface classes with no label, which would render as a raw key: %s "
                         "-- add them to SURFACE_CLASS_LABELS" % ", ".join(missing_label))
    out = []
    for fam, fam_label, keys in SURFACE_CLASS_FAMILIES:
        for k in keys:
            if k not in vocab:
                continue
            label, hint = SURFACE_CLASS_LABELS[k]
            out.append({"key": k, "label": label, "hint": hint,
                        "family": fam, "family_label": fam_label})
    return out


def class_containment(tags_map=None, classes=None):
    """{class: [classes it strictly CONTAINS]}, DERIVED from the live tags. Never typed.

    The wizard uses this to tell a player that a box they are about to tick adds nothing, or that
    one they already ticked has swallowed another. Getting it from the data rather than a hand-kept
    table is not a style preference: contract.py carried this lattice as a COMMENT and the comment
    was BACKWARDS for months (it said MajorBoss was a subset of Remembrance/GreatRune; it is their
    superset). A table can be wrong in a way a derivation cannot.

    A class contains another when every tagged check of the narrower one also carries the broader
    tag. Equal sets would contain each OTHER, which is not useful to draw, so only STRICT
    containment is reported. An empty class contains nothing (it is vacuously inside everything --
    true, and useless).
    """
    lt = LOCATION_TAGS if tags_map is None else tags_map
    vocab = list(classes if classes is not None else contract.SURFACE_CLASSES)
    members = {c: {ap for ap, ts in (lt or {}).items() if c in (ts or ())} for c in vocab}
    out = {}
    for outer in vocab:
        inner = [c for c in vocab
                 if c != outer and members[c] and members[c] < members[outer]]
        if inner:
            out[outer] = inner
    return out


# ---- pure, host-testable helpers (no AP import; unit-tested with synthetic tags) ------------------
def selected_surface(sel):
    """Filter a raw selection to the valid vocabulary, in CANONICAL (vocabulary) order.

    DETERMINISM: this option is an OptionSet, and a Python set of strings does NOT have a stable
    iteration order across processes (string hashing is randomised per run). Ordering by the selection
    would therefore make the ladder -- and the fill that follows it -- differ between two runs of the
    SAME seed. So the order comes from the VOCABULARY, never from the caller's container. (This is the
    same class of bug as regionSphereTargetRanges being emitted in set-iteration order, 2026-07-11.)
    Accepts a list or a set; the result is identical either way."""
    chosen = set(sel or ())
    return [c for c in contract.SURFACE_CLASSES if c in chosen]


def build_ladder(selection):
    """Ordered list of allowed-class-sets for the STRICT feasibility ladder, starting from the user's
    base surface and widening by _WIDEN_GROUPS. Pure. Empty selection -> [] (feature no-op)."""
    base = selected_surface(selection)
    if not base:
        return []
    rungs = [list(base)]
    acc = list(base)
    for grp in _WIDEN_GROUPS:
        add = [c for c in grp if c not in acc]
        if add:
            acc = acc + add
            rungs.append(list(acc))
    return rungs


def _roundtable_merchant_aps():
    """Roundtable Hold (the always-open hub) MERCHANT ShopSlots -- Enia (remembrance weapons/armor)
    and the Twin Maiden Husks. BARRED from the progression surface (Alaric 2026-07-18): the hub is
    reachable at spawn, so a Lock / key item placed on a hub merchant slot is 'progression' you already
    hold on turn one -- trivial. This rule touches ONLY hub ShopSlots; the hub's Golden Seed checks
    (Seedtree, physical pickups) are left to the normal surface/defaulted logic. Derived from the
    generated data, so a regen that adds or moves a hub ShopSlot is covered without a hand-list."""
    try:
        from ..data import LOCATIONS, HUB
        from ..location_tags import LOCATION_TAGS as _lt
    except Exception:
        return frozenset()
    return frozenset(ap for (_n, ap, _f) in LOCATIONS.get(HUB, ())
                     if "ShopSlot" in _lt.get(ap, ()))


def allowed_ap_ids(tags_map, classes, defaulted=None):
    """ap-ids whose tags put them ON THE SURFACE for `classes` (Roundtable-Hold merchants -- Enia +
    Twin Maiden Husks -- hard-excluded). Pure.

    Checks in `defaulted` (DEFAULTED_REGION_APS) are BARRED regardless of tags: their region was a
    guess that fell back to the hub, so AP believes them reachable at spawn while the item actually
    spawns wherever it really lives. Fill put a STORMVEIL CASTLE LOCK on one such Golden Seed
    (flag 400220, really in Stormveil) in a Caelid-start seed -- unwinnable. A guessed region may not
    carry progression. See gen_data._region_is_derived(). The hub MERCHANT slots are barred for a
    related reason -- always reachable at spawn -> trivial progression (see _roundtable_merchant_aps)."""
    sel = set(classes)
    if defaulted is None:
        try:
            from ..location_tags import DEFAULTED_REGION_APS as _d
        except Exception:
            _d = frozenset()
        try:
            # m11_00 (normal Leyndell): destroyed when Maliketh dies (the Erdtree burns). Same rule --
            # a check the player can put permanently out of reach may not carry progression.
            from ..location_tags import ERDTREE_BURN_APS as _b
        except Exception:
            _b = frozenset()
        defaulted = frozenset(_d) | frozenset(_b)
    # Hub merchant slots are barred in EVERY path (own + foreign), regardless of how `defaulted` was
    # computed/passed -- this is the single surface chokepoint both confinements funnel through.
    # SURFACE_EXCLUDE_APS (hand-excluded surface-tagged checks, e.g. Secret Rite Scroll -- gen_data
    # _SURFACE_EXCLUDE_FLAGS) are barred here too, always, for the same reason.
    try:
        from ..location_tags import SURFACE_EXCLUDE_APS as _sx
    except Exception:
        _sx = frozenset()
    barred = frozenset(defaulted) | _roundtable_merchant_aps() | frozenset(_sx)
    return {ap for ap, tags in tags_map.items()
            if contract.has_class(tags, sel) and ap not in barred}


def is_restricted_progression(item, player):
    """True iff `item` is THIS world's own progression that we confine: advancement, owned by `player`,
    and NOT a Boss Key (those are exempt). Pure over an item-like with .player/.advancement/.name."""
    if getattr(item, "player", None) != player or not getattr(item, "advancement", False):
        return False
    return not str(getattr(item, "name", "")).startswith(_BOSS_KEY_PREFIX)


SURFACE_HEADROOM = 3
"""How many open surface slots each restricted item needs before the released-Lock bar is kept.

🛑 A HEURISTIC CALIBRATED ON MEASUREMENTS, NOT A PROOF, and it is 3 rather than 1 because bare
sufficiency was tried and was NOT enough. Fuzz case 1717/0012 released 6 Locks onto a
`["Basin", "KeyItem"]` surface that had slots for them and still FillErrored: capacity is not the
whole constraint, REACHABLE capacity in sphere order is. A surface whose every slot sits deep behind
the very lock chain being placed leaves the first Lock no home, and a count cannot see that.

3x is what separates the pathological seeds from the real ones with room to spare: the shipped
default measures ~170 hosting locations against a ceiling of 36 restricted items, which is ~4.7x, so
every seed anyone actually rolls keeps the bar. Raise it if fuzzing finds another shape; the number
is a dial, and the fuzz corpus is how it gets turned.
"""


def surface_can_hold_the_locks(n_restricted, open_surface_slots):
    """May a released Lock be held to the surface, or must the bar yield for this seed?

    THE VALVE. Confined Locks have two of these -- the feasibility ladder widens the class list, and
    the spill returns anything unplaceable to the general pool -- which is why `apply()` is
    documented as "Never FillErrors". A released Lock had NEITHER: `released_lock_barred` is an
    unconditional item_rule, so on a seed whose surface is too small there is simply nowhere for the
    Locks to go and generation fails.

    🛑 FOUND BY FUZZING, TWICE, FROM OPPOSITE DIRECTIONS (er-archipelago#491, 2026-08-09), which is
    why the test is a RATIO rather than a floor on either input:
      * `greenfield/fuzz_gf.py` reached it by NARROWING the surface -- `progression_surface:
        ["Basin"]` -- while leaving the seed full size. Both failing yamls generate clean on `main`.
      * CI reached it by SHRINKING the seed -- `NumRegions1::test_fill`, one kept region, and the one
        item it could not place was `Ashen Capital Lock`.

    The rule: if this seed's surface cannot host every Lock the seed mints, it has no business
    constraining where they go -- the curation promise is already broken at that point, and a
    promise that cannot be kept must degrade rather than fail. In a normal seed this is nowhere near
    close: ~170 hosting locations against a ceiling of 36 Locks, which is the ~4.7x headroom
    measured before any of this existed.

    Compares against EVERY restricted item, not just the released Locks: the confined Locks, the
    required Great Runes and the legacy keys are all placed on the same surface first, so counting
    only the released set would call a surface adequate that the rest is about to fill.
    """
    return open_surface_slots >= n_restricted * SURFACE_HEADROOM


def released_lock_barred(item, player, released):
    """True iff `item` is one of OUR OWN Locks that Progression Bias put in the multiworld pool --
    so it may not sit on one of our NON-surface checks.

    This is what makes a released Lock still curated. Without it, `core._add_locations` bars only
    FOREIGN advancement from a non-surface check, so one of our Locks could occupy any of our ~4931
    reachable locations while every other Elden Ring world offered it only the ~172 on its surface --
    measured consequence, released Locks stayed home ~97% of the time. We contributed 172 progression
    slots to the shared pool and reserved 4931 for ourselves.

    Pure over an item-like with `.player`/`.name`. `released` is the NAME SET `apply()` actually
    drew, NOT "anything that looks like a Lock": a Lock the bias chose to KEEP was pre-placed on the
    surface already, and a kept Lock that somehow reached the fill is a SPILL, which must keep its
    safety valve or it strands.

    🛑 `released` is read LATE, at fill time, because the draw happens in pre_fill -- long after core
    builds these item_rules in create_regions. An empty set (nothing released yet, or bias 100) makes
    this inert, which is exactly right for both."""
    if getattr(item, "player", None) != player:
        return False
    return str(getattr(item, "name", "")) in released


def foreign_advancement_barred(item, player):
    """True iff `item` is ANOTHER player's advancement item -- the thing confine_foreign_progression
    keeps off this world's non-surface (filler) checks. Our OWN items (any classification) and any
    non-advancement item pass. Pure over an item-like with .player/.advancement. The core item_rule on
    a non-surface location is `not foreign_advancement_barred(item, self.player)`."""
    return bool(getattr(item, "advancement", False)) and getattr(item, "player", None) != player


def released_locks(items, pct, rng):
    """The Region Lock items that SKIP the surface and go to the normal multiworld fill.

    Pure over item-likes with `.name` plus an `rng` with `.sample` (pass `world.random`, never the
    module `random` -- a seed must reproduce). Only Locks are eligible: required Great Runes and
    legacy keys keep the surface whatever the percentage says, because the ask this implements was
    about Locks and widening it silently would be a different feature.

    Rounding is `(n*pct + 50) // 100`, half up, in integers. Python's `round()` is banker's rounding
    (`round(0.5) == 0`), so a 50% setting on a 1-Lock seed would release NOTHING and read as the
    feature being broken on exactly the seeds small enough for a player to check by hand.

    The endpoints are exact by construction, not by rounding: 0 releases none, 100 releases all.
    """
    locks = [it for it in items if lock_region_name(getattr(it, "name", "")) is not None]
    if pct <= 0 or not locks:
        return []
    if pct >= 100:
        return list(locks)
    k = (len(locks) * pct + 50) // 100
    if k <= 0:
        return []
    if k >= len(locks):
        return list(locks)
    return rng.sample(locks, k)


def lock_region_name(item_name):
    """'Limgrave Lock' -> 'Limgrave'; None for a non-lock name. Pure."""
    s = str(item_name)
    return s[:-len(" Lock")] if s.endswith(" Lock") else None


def regions_with_major_boss(region_names, tags_map=None, locations=None, barred=None):
    """Subset of `region_names` that HOST at least one MajorBoss location -- the regions eligible to be
    the strict sphere-0 anchor. Pure over the generated LOCATION_TAGS + LOCATIONS maps (defaults to the
    module globals). Empty if tags aren't generated yet (caller then falls back to any region).

    `barred` (the caller's _world_barred_aps) is subtracted, because HOSTING is the question being
    asked and a barred check cannot host. Deeproot Depths is the case that made this matter: its only
    MajorBoss check is the Fortissax reward, which is questline-missable, so counting it made the
    region look eligible on the strength of a check no Lock can ever land on."""
    tm = LOCATION_TAGS if tags_map is None else tags_map
    if locations is None:
        try:
            from ..data import LOCATIONS as locations
        except Exception:
            locations = {}
    locs = locations
    bar = frozenset(barred or ())
    out = set()
    for r in region_names:
        for (_n, ap, _f) in locs.get(r, []):
            if ap not in bar and "MajorBoss" in (tm.get(ap) or ()):
                out.add(r)
                break
    return out


# ---- AP glue --------------------------------------------------------------------------------------
def _selection(world):
    """The classes this world's surface is built from. ONE resolution, read by BOTH apply() (where the
    locks go) and slot_data() (what the client stars). If those two ever computed the surface
    differently we would be back to two lists disagreeing -- which is the bug big-ticket was."""
    opt = getattr(world.options, "progression_surface", None)
    return opt.value if opt is not None else None


def _mode(world):
    o = getattr(world.options, "progression_surface_mode", None)
    return int(o.value) if o is not None else 0


def confined_surface_ids(world):
    """The ap-ids of THIS world that MAY host foreign progression, when confine_foreign_progression is
    on -- i.e. the selected surface. Core bars other players' advancement on every own location whose
    ap-id is NOT in this set, confining foreign progression to the same checks the own region Locks use.
    Returns None when the feature is inactive (option off, surface mode off, empty surface, or tags not
    generated), meaning 'apply no foreign bar'. Uses the SAME surface resolution as apply()/slot_data(),
    so where foreign progression may land and where own progression is placed can never disagree."""
    o = getattr(world.options, "confine_foreign_progression", None)
    if o is None or not int(getattr(o, "value", 0)) or _mode(world) == 0 or not LOCATION_TAGS:
        return None
    classes = selected_surface(_selection(world))
    if not classes:
        return None
    return allowed_ap_ids(LOCATION_TAGS, classes, defaulted=_world_barred_aps(world))


def _released_pct(world) -> int:
    """What share of this world's Region Locks go into the multiworld pool, i.e. `100 - bias`.

    Falls back to 0 (release nothing, the pre-option behaviour) when the option is absent -- an older
    yaml or a stubbed world must not silently start releasing. Note that is the opposite endpoint
    from the option's own default of 0 BIAS: absent means "behave as before", not "behave as default".
    """
    opt = getattr(getattr(world, "options", None), "progression_bias", None)
    if opt is None:
        return 0
    return 100 - int(opt.value)


def _restricted_items(world):
    return [it for it in world.multiworld.itempool
            if is_restricted_progression(it, world.player)]


def missable_barred_aps(world):
    """The missable checks that may not host progression, or empty when the guard is off.

    WHY THIS JOINED THE SURFACE MATH (2026-07-28). features/missable_locations enforces its bar with
    an item_rule, and the surface never knew about it -- so `allowed_ap_ids` counted checks that
    cannot accept an advancement item, and the surface SIZE was a claim about tags rather than about
    hosting. Mostly that is a cosmetic overcount. It stopped being cosmetic when the Fortissax reward
    was tagged: `Deeproot Depths` has exactly ONE surface member and that is it, so the surface said
    the region could host a Lock while the true count was zero -- and `regions_with_major_boss`, which
    decides strict-mode sphere-0 anchor eligibility, said the same thing off the same tags.

    Gated on the option, because turning `protect_missable_locations` OFF is a deliberate choice to
    accept questline requirements ("expert / guaranteed-access play") -- and then these checks really
    can host progression, so the surface should count them again."""
    opt = getattr(getattr(world, "options", None), "protect_missable_locations", None)
    if opt is not None and not opt.value:
        return frozenset()
    try:
        from ..missable_locations import MISSABLE_LOCATIONS
    except Exception:
        return frozenset()
    return frozenset(MISSABLE_LOCATIONS)


def _world_barred_aps(world):
    """The per-world no-progression set for surface math: DEFAULTED_REGION_APS always; the missable
    set while its guard is armed (missable_barred_aps); the ERDTREE_BURN_APS burn-strand bar only
    while the capital reconciler is NOT armed (armed = the client restores m11_00, so the strand those
    APs were barred for cannot happen -- SPEC-capital-reconciler.md). Mirrors core._add_locations'
    item_rule carve-out; the two must agree or the surface would star checks the item_rule forbids
    (or vice versa) -- which is exactly what it did for every missable check until 2026-07-28."""
    try:
        from ..location_tags import DEFAULTED_REGION_APS as _d
    except Exception:
        _d = frozenset()
    _m = missable_barred_aps(world)
    if getattr(world, "gf_capital_reconciler", False):
        return frozenset(_d) | _m
    try:
        from ..location_tags import ERDTREE_BURN_APS as _b
    except Exception:
        _b = frozenset()
    return frozenset(_d) | frozenset(_b) | _m


def _open_allowed(world, classes):
    """Unfilled locations of this player whose tags put them ON THE SURFACE for `classes`."""
    ids = allowed_ap_ids(LOCATION_TAGS, classes, defaulted=_world_barred_aps(world))
    out = []
    for loc in world.multiworld.get_locations(world.player):
        ap = getattr(loc, "address", None)
        if ap is not None and ap in ids and loc.item is None:
            out.append(loc)
    return out


def _place(world, allowed, to_place, lock):
    """One fill_restrictive pass. Base state = get_all_state(False) (the base-state fix): the rest of
    the pool + precollected + already-placed locks count as available, so gated majors look reachable.
    fill_restrictive mutates to_place in place, leaving only the UNPLACED items.

    ACCESS-CHECK FIX (2026-07-24): fill_restrictive only enforces per-item reachability while the game
    is NOT yet beatable in its max-exploration state. Under accessibility:minimal it computes
    ``perform_access_check = not has_beaten_game(maximum_exploration_state)`` -- and that max-exploration
    state re-collects the ENTIRE item_pool (every gate key we are placing), so the goal is ALWAYS
    "beaten" during our pre-fill => the check switches OFF => fill_restrictive stops verifying
    reachability and LOCKS our gate keys into whatever slots remain, including regions sealed behind
    OTHER gate keys. In vanilla-progression mode the full vanilla dependency graph (deep compound / count
    chokepoints, ~30 keys) makes that a routine multi-region cycle -> keys stranded behind their own
    gates -> audit_reachable's unrescuable FillError. We WANT our own spine fully reachable regardless of
    the player's accessibility (that is the entire point of the surface + the audit), so force the check
    ON for the duration of OUR placement by lifting accessibility off minimal, then restore it. Verified
    a no-op for the region-lock spine (its DAG already placed reachably) and the fix for vanilla mode
    (0 spill / 0 rescue where the strand was ~30 keys). The restore is in ``finally`` so a fill raise
    can't leak the override; placement is synchronous and single-threaded per world, so no race."""
    import inspect
    from Fill import fill_restrictive
    mw = world.multiworld
    state = mw.get_all_state(False)
    # Build kwargs by SIGNATURE, not a try/except-TypeError fallback: the old fallback dropped BOTH
    # `lock` and `allow_partial`, so on an AP without allow_partial a strict lock would silently go
    # unlocked (progression-balancing could then move it off the surface) AND, now that we force the
    # access check on below, an over-full surface would raise FillError instead of spilling -- breaking
    # the ladder's "never FillErrors" contract. Gating on the signature keeps `lock` unconditional and
    # only omits allow_partial when the running AP truly lacks it. (Fable review 2026-07-24.)
    kwargs = {"single_player_placement": True, "lock": lock}
    if "allow_partial" in inspect.signature(fill_restrictive).parameters:
        kwargs["allow_partial"] = True
    acc = getattr(world.options, "accessibility", None)
    saved = acc.value if acc is not None else None
    try:
        if acc is not None:
            acc.value = 0  # Accessibility.option_full -> perform_access_check stays True in fill_restrictive
        fill_restrictive(mw, state, allowed, to_place, **kwargs)
    finally:
        if acc is not None:
            acc.value = saved


def apply(world) -> None:
    """core.pre_fill hook (mode soft/strict). Confine this world's own progression to the selected
    surface; widen via the ladder; return the remainder to the pool. Never FillErrors."""
    mode = _mode(world)
    if mode == 0 or not LOCATION_TAGS:
        return
    surface = selected_surface(_selection(world))
    if not surface:
        return
    mw = world.multiworld
    to_place = _restricted_items(world)
    if not to_place:
        return
    try:
        import Fill  # noqa: F401  -- ensure the fill API exists before we disturb the pool
    except Exception:
        return
    # RELEASE (er-archipelago#491). A released Lock is simply never taken out of the itempool, so
    # the normal multiworld fill places it -- which is the only way one can reach another player's
    # world. Measured before this existed: 0 spill in 146 world-instances and 0 of 105 Locks foreign
    # in 8 two-player seeds, because the surface hosts ~170 checks against a ceiling of 36 restricted
    # items. The valve existed; nothing ever came through it.
    #
    # 🛑 The draw happens BEFORE the removal loop and ONCE, recorded on `world`. Drawing it later
    # would mean re-deciding per caller, and an inline rng draw that runs a different number of times
    # in different code paths splits the seed.
    _restricted = list(to_place)   # before the split -- the valve counts EVERY Lock, not the released ones
    released = released_locks(to_place, _released_pct(world), world.random)
    if released:
        _rel = {id(it) for it in released}
        to_place = [it for it in to_place if id(it) not in _rel]
    world.gf_locks_released = sorted(it.name for it in released)
    # THE VALVE (see surface_can_hold_the_locks). Capacity is measured over the WHOLE selected
    # surface, not rung 0, because the ladder may widen into the rest of it -- using the narrow rung
    # would trip this on seeds the ladder would have rescued.
    _n_restricted = len(_restricted)
    _capacity = len(_open_allowed(world, surface))
    world.gf_locks_bar_kept = surface_can_hold_the_locks(_n_restricted, _capacity)
    # The handle core's non-surface item_rule reads at FILL time (see released_lock_barred). A set
    # because that rule is evaluated once per (location, item) candidate pair -- and EMPTY when the
    # valve trips, which is what makes the bar inert without unpicking the release itself. The
    # Locks still travel; they just stop being held to a surface that cannot hold them.
    world.gf_locks_released_set = (frozenset(world.gf_locks_released)
                                   if world.gf_locks_bar_kept else frozenset())
    if not world.gf_locks_bar_kept and released:
        # LOUD. A seed that quietly stopped curating looks exactly like one that never tried, and
        # this is the single path that undoes the whole point of progression_bias.
        import logging as _lg
        _lg.getLogger("Greenfield").warning(
            "[greenfield] progression surface: SURFACE TOO SMALL for this seed's %d restricted "
            "item(s) (%d hosting location(s); %dx headroom wanted) -- the released-Lock bar is "
            "DROPPED for this "
            "seed. The %d released Lock(s) still enter the multiworld pool, but they may land on "
            "ordinary checks rather than curated ones. Widen `progression_surface`, raise "
            "`progression_bias`, or keep more regions to get the curation back.",
            _n_restricted, _capacity, SURFACE_HEADROOM, len(released))
    n0 = len(to_place)
    for it in to_place:
        mw.itempool.remove(it)
    strict = (mode == 2)
    rungs = build_ladder(surface) if strict else [list(surface)]
    resolved = rungs[0] if rungs else list(surface)
    for classes in rungs:
        if not to_place:
            break
        allowed = _open_allowed(world, classes)
        world.random.shuffle(allowed)
        resolved = classes
        _place(world, allowed, to_place, lock=strict)
    # Anything the surface (+ladder) could not host goes back to the pool for normal fill -> winnable.
    for it in to_place:
        mw.itempool.append(it)
    world.gf_prog_surface_resolved = list(resolved)
    world.gf_prog_surface_spilled = len(to_place)
    world.gf_prog_surface_placed = n0 - len(to_place)
    # WHICH items spilled, not just how many. The count alone has lived in the SPOILER since this
    # feature landed -- post-hoc, per-seed, and no gate reads it -- so the one path that silently
    # undoes the confinement was the one path nobody could see. "Tolerance requires telemetry"
    # (CONTRIBUTING, Runtime visibility): a degrade announces itself, with enough detail to act on.
    #
    # 🛑 A SPILL IS NOT A SOFTLOCK, and this log must not be read as one. Winnability is guarded
    # independently and still holds for a spilled item: core._add_locations bars advancement from ANY
    # player on DEFAULTED_REGION_APS / ERDTREE_BURN_APS, features/missable_locations does the same on
    # every missable check, and audit_reachable (post_fill) rescues-or-fails on any own advancement
    # item that ends up unreachable "whatever minted it". What a spill costs is CURATION: the Lock
    # lands on some ordinary reachable check -- possibly in ANOTHER player's world, since
    # local_items deliberately lets region Locks travel -- instead of on a vetted surface check.
    world.gf_prog_surface_spilled_names = sorted(it.name for it in to_place)
    # UNCONDITIONAL. It used to log only when something spilled, which made "no spill" and "no
    # telemetry at all" indistinguishable downstream -- tools/fill_regression could only report the
    # spill distribution as NOT MEASURED and had to say so. "Armed with N entries" is the house
    # pattern (CONTRIBUTING, Runtime visibility): a feature states its status every run, and a ZERO
    # is a measurement, not a silence.
    import logging
    # RELEASED is logged beside SPILLED and is NOT the same thing: released Locks were never offered
    # to the surface (the player asked for that), spilled ones were offered and did not fit (the
    # surface fell short). Folding them into one number would hide a starved surface behind an
    # option, which is the failure the spill telemetry was added to prevent in the first place.
    logging.getLogger("Greenfield").info(
        "[greenfield] progression surface: %d Lock(s) RELEASED to the multiworld pool "
        "(progression_bias %d)%s",
        len(world.gf_locks_released), 100 - _released_pct(world),
        (": " + ", ".join(world.gf_locks_released)) if world.gf_locks_released else "")
    logging.getLogger("Greenfield").info(
        "[greenfield] progression surface: rung %s placed %d/%d; %d SPILLED to normal fill%s",
        resolved, n0 - len(to_place), n0, len(to_place),
        (" (curation only -- winnability is guarded elsewhere): "
         + ", ".join(world.gf_prog_surface_spilled_names)) if to_place else "")

    # D (2026-07-10): break the boss-key <-> region-lock cycle. When boss_keys is on, the default
    # surface IS key-gated boss checks, and `_place` validates against get_all_state (which counts
    # every Boss Key as held), so a region Lock freezes onto a key-gated check while the key itself can
    # land behind that very Lock => softlock (reproduced ~24% under accessibility:minimal). For every
    # Lock we placed on a key-gated check, PRECOLLECT that Boss Key -- making get_all_state's assumption
    # actually true -- and add one filler to stay count-neutral. Independent of accessibility mode /
    # fill order / multiworld. As non-boss premium surfaces are added, fewer keys land here and boss
    # keys regain teeth (Locks stop always landing on boss checks). See boss_locks.key_gate_map.
    try:
        from .boss_locks import key_gate_map
        gate = key_gate_map(world)
    except Exception:
        gate = {}
    precollected = 0
    if gate:
        for loc in mw.get_locations(world.player):
            ap = getattr(loc, "address", None)
            placed = getattr(loc, "item", None)
            if ap not in gate or placed is None:
                continue
            if not is_restricted_progression(placed, world.player):
                continue
            kname = gate[ap]
            kitem = next((it for it in mw.itempool
                          if it.player == world.player and it.name == kname), None)
            if kitem is None:
                continue  # key already precollected (another Lock on the same boss) or not in pool
            mw.itempool.remove(kitem)
            mw.push_precollected(kitem)
            mw.itempool.append(world.create_filler())
            precollected += 1
    world.gf_prog_surface_keys_precollected = precollected


def audit_reachable(world) -> None:
    """post_fill SAFETY NET (F). From a REAL CollectionState (precollected only), verify every own
    advancement item is actually reachable. Any own advancement item at an unreachable location is a
    shipped softlock under accessibility:minimal (AP skips its own full-accessibility check there).

    RESCUE-THEN-FAIL: first try to salvage the seed -- swap each stranded item into a reachable,
    unlocked, filler-holding location of ours (the filler moves to the now-unreachable slot, which is
    harmless). Reachability only grows as progression moves into reachable slots, so we iterate + re-
    sweep until stable. Only raise FillError when a stranded item CANNOT be rescued (its placement is
    locked, or no reachable filler slot remains) -- so a salvageable seed ships instead of dying, and a
    genuinely unwinnable one fails loudly at generation instead of hours into a playthrough. Catches
    any residual boss-key/region-lock cycle or stranded rune/legacy key, whatever minted it. FAIL-OPEN
    on an internal audit error (never block gen on an audit bug). Only guards the surface regime."""
    if _mode(world) == 0:
        return
    try:
        from BaseClasses import CollectionState
        from Fill import FillError, swap_location_item
    except Exception as e:
        import logging
        logging.getLogger("Greenfield").warning("audit_reachable: imports failed (%r)", e)
        return

    mw = world.multiworld
    player = world.player

    def _detail(locs):
        return ", ".join(f"{l.item.name} @ {l.name}" for l in locs[:8])

    def _stranded(state, locs):
        return [l for l in locs if l.item is not None and l.item.player == player
                and l.item.advancement and not l.can_reach(state)]

    try:
        my_locs = list(mw.get_locations(player))
        rescued = 0
        for _ in range(len(my_locs) + 2):
            state = CollectionState(mw)
            state.sweep_for_advancements()
            stranded = _stranded(state, my_locs)
            if not stranded:
                break
            locked = [l for l in stranded if l.locked]
            if locked:  # a locked placement can't be moved -> unrescuable
                raise FillError(f"[greenfield] {len(locked)} own progression item(s) LOCKED & unreachable "
                                f"after fill -- unrescuable soft-lock; regenerate. First: {_detail(locked)}")
            _strand_ids = {id(l) for l in stranded}
            targets = [l for l in my_locs
                       if not l.locked and l.item is not None and not l.item.advancement
                       and id(l) not in _strand_ids and l.can_reach(state)]
            if not targets:
                raise FillError(f"[greenfield] {len(stranded)} own progression item(s) unreachable and no "
                                f"reachable filler slot to rescue into; regenerate. First: {_detail(stranded)}")
            moved = 0
            for sl in stranded:
                if not targets:
                    break
                swap_location_item(sl, targets.pop())  # stranded prog -> reachable slot; filler -> sl
                rescued += 1
                moved += 1
            if moved == 0:
                raise FillError(f"[greenfield] {len(stranded)} own progression item(s) unreachable; rescue "
                                f"made no progress; regenerate. First: {_detail(stranded)}")
        else:  # loop exhausted without converging
            state = CollectionState(mw)
            state.sweep_for_advancements()
            remaining = _stranded(state, my_locs)
            if remaining:
                raise FillError(f"[greenfield] {len(remaining)} own progression item(s) unrescuable after "
                                f"max iterations; regenerate. First: {_detail(remaining)}")
        world.gf_prog_surface_rescued = rescued
    except FillError:
        raise
    except Exception as e:  # audit malfunction must never fail an otherwise-good gen
        import logging
        logging.getLogger("Greenfield").warning(
            "progression_surface.audit_reachable skipped (internal error: %r)", e)


@register
class ProgressionSurfaceFeature(Feature):
    name = "progression_surface"
    OPTIONS = {"progression_surface": ProgressionSurface,
               "progression_surface_mode": ProgressionSurfaceMode,
               "progression_bias": ProgressionBias,
               "confine_foreign_progression": ConfineForeignProgression}
    # Placement runs centrally from core.pre_fill via apply() (locations exist + get_all_state valid).
    # The foreign-progression bar is set in core._add_locations (item_rule), using confined_surface_ids.

    def slot_data(self, world):
        """Ship the surface to the CLIENT. This is the set the tracker stars.

        🛑 WHAT A STAR MEANS, RELAXED 2026-08-09 (Alaric, er-archipelago#491). It used to mean
        "your region Locks are somewhere in here", which `progression_bias` retires: at the default
        of 0 none of your Locks are reserved for YOUR surface, so on a two-slot seed roughly half of
        them are sitting on somebody else's.

        It still confines real progression, so the honest reading is the weaker one:
        **these are the locations that can host progression items -- yours or another world's.**
        `confine_foreign_progression` (default ON) keeps every OTHER player's advancement on exactly
        this set, and whatever share of your own Locks you chose to keep curated lands here too. A
        star is "something important can be here", not "your key is here".

        It REPLACES `bigTicketLocations`, which was a second list of "important checks" naming a set
        progression could never reach: big-ticket targeted {MajorBoss, Remembrance, GreatRune} while
        the surface is {Remembrance, Seedtree, Church, Boss, Fragment, Revered} -- intersection
        Remembrance alone. The client was starring MajorBoss/GreatRune checks that this module FORBIDS
        a region Lock from ever occupying. A tracker pointing at checks the locks cannot be on is worse
        than no tracker: it teaches the player something false.

        Emitting the surface itself makes that drift unrepresentable -- "where progression may be"
        and "what the client stars" are now one expression, evaluated once.
        """
        if _mode(world) == 0:
            return {contract.PROGRESSION_SURFACE_LOCATIONS: []}
        classes = selected_surface(_selection(world))
        ids = allowed_ap_ids(LOCATION_TAGS, classes, defaulted=_world_barred_aps(world))
        own = {loc.address for loc in world.multiworld.get_locations(world.player)
               if getattr(loc, "address", None) is not None}
        return {contract.PROGRESSION_SURFACE_LOCATIONS: sorted(i for i in ids if i in own)}
