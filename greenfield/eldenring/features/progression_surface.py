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
from Options import Choice, NamedRange, OptionSet, Range, Removed
import hashlib

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
        default = contract.SURFACE_DEFAULT_CLASSES
        return {
            "keys": surface_class_meta(),
            "families": [{"id": fid, "label": lab} for fid, lab, _ in SURFACE_CLASS_FAMILIES],
            "contains": class_containment(),
            "presets": [
                {"label": "Recommended", "keys": sorted(default)},
                {"label": "Major bosses only", "keys": ["MajorBoss"]},
                {"label": "No sweep payouts", "keys": sorted(default - {"SweepSlot"})},
                {"label": "Buy your progression", "keys": sorted(default | {"ShopNonSpell"})},
                {"label": "Off", "keys": []},
            ],
        }


class ProgressionSurfaceMode(Removed):
    """Retired 2026-08-14. It had been frozen at `strict` since the v0.2 slim-down, so `off` and
    `soft` were unreachable from any yaml -- and both branches were still carried in four places
    here plus three in core, which is how #635 happened (a live docstring citing "when Progression
    Surface Mode is off", a state no seed could be in).

    Strict is now the only regime and is written as such rather than selected. What you probably
    want instead: `progression_surface` chooses WHICH classes may hold progression, and
    `confine_foreign_progression` decides whether other players' progression is held to it too.

    🛑 This is not a Frozen option turned Removed by paperwork -- the off-branches were DELETED. A
    build where the option is merely absent behaves as `off`, which silently disarms the surface and
    ships an empty progressionSurfaceLocations to a client that reads it."""


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


class CrossGameProgression(NamedRange):
    """What share of your travelling Region Locks may land in a NON-Elden-Ring player's world.

    `auto` (the default) is **1 / number of games**: in a two-game multiworld half your travelling
    Locks go to the partner, in a four-game one a quarter each. That is the same 1/N rule the export
    volume is judged by, and it means the answer scales with the table instead of being a number
    someone has to re-pick per seed. `0` keeps every Lock inside Elden Ring, which is the behaviour
    every seed had before this option existed. A number is that share explicitly.

    # Why this option exists at all

    `progression_bias` already releases Locks into the multiworld, and between Elden Ring worlds it
    works -- MEASURED 50-54% travel on 2xER seeds. But `place_released_locks` only ever offered them
    ELDEN RING surfaces, and our surfaces host ~170 checks against at most ~36 Locks, so the spill
    valve that was supposed to feed a partner never had anything to spill. MEASURED across four
    configurations: **0 Locks reached a Hollow Knight slot, ever** -- including a 2xER + 1xHK seed
    where 15 of 28 Locks travelled and all 15 went to the other Elden Ring world.

    `ProgressionBias`'s own docstring promised the opposite ("expect most of your travelling Locks to
    land in the partner game"), so this is the option that makes that sentence true.

    ⚠️ IT PLACES INTO ANOTHER GAME'S LOCATIONS, which is the one thing `place_released_locks` used to
    refuse to do, and the refusal was not arbitrary -- TUNIC's own `stage_pre_fill` raises
    "caused by another world filling TUNIC locations during pre_fill... we cannot recover from this
    issue." We only ever offer locations that are still EMPTY, never force a placement, and put back
    anything unplaced -- but a partner game that objects to being filled at all is a real failure
    mode, and `0` is the escape hatch. Set it to 0 if a seed will not generate.

    No effect in a solo seed, in an all-Elden-Ring multiworld (there is no non-ER world to send to),
    or in the modes that mint no Lock items."""
    display_name = "Cross Game Progression"
    range_start = 0
    range_end = 100
    default = -1
    special_range_names = {"auto": -1, "never": 0}


class ConfineForeignProgression(NamedRange):
    """What share of OTHER players' progression is confined to your Progression Surface, the way
    your own is. A percentage, not a switch.

    100 (`true`) confines all of it: another world's advancement may only be placed on your surface
    locations -- the same high-confidence checks your own progression is curated onto -- never on
    your filler checks. So a foreign key spell lands on a major-boss / remembrance / key-item check
    of yours, not on a random Smithing Stone pickup. 0 (`false`) confines none of it and foreign
    progression scatters across any reachable location of yours, which is standard Archipelago
    behaviour. In between, that share of the foreign advancement you see is held to the surface and
    the rest is free.

    🛑 IT IS NOT ONLY A CURATION KNOB, and this is the reason it stopped being a toggle. The rule is
    about YOUR locations, but it displaces your NEIGHBOUR: barred from your ~3000 filler checks, a
    partner game's progression has nowhere to go but its own locations, which saturates them early
    in the fill -- and Archipelago places the whole `useful` tier before any filler, so by the time
    it reaches what is left of the partner's world only filler remains. MEASURED at 100, three
    seeds, two Elden Ring slots beside two Hollow Knight slots: of 498 Elden Ring items that reached
    Hollow Knight, **zero** were useful -- no weapon, no armour, no talisman, 100% filler -- while
    the other Elden Ring slot got a healthy 43.1% useful. At 0 the same seeds send Hollow Knight
    40.7% useful, which is the pool's own mix. Lower this if you want your gear to be worth
    receiving in a non-Elden-Ring game.

    It is a propensity by ITEM NAME, not a per-copy coin flip: the decision for a given foreign item
    name is fixed for the whole seed, so a name is either surface-only or free, never both.

    No effect in a solo seed, or when Progression Surface Mode is off. It never blocks generation:
    your OWN progression keeps its feasibility-ladder + spill safety valve, and foreign progression
    that will not fit your surface simply lands in its own world instead (only YOUR filler checks
    are barred to it -- other worlds are untouched)."""
    display_name = "Confine Foreign Progression"
    range_start = 0
    range_end = 100
    default = 100
    # 🛑🛑 `on` / `off` USED TO BE HERE AND MUST NEVER COME BACK, and this is not a style note --
    # their presence made the world's own generated template UNLOADABLE. AP's template generator
    # (`Options.generate_yaml_templates` -> `data/options.yaml`, the `range_option` macro) emits
    # weight keys UNQUOTED, `{{ entry }}: {{ default }}`, unlike the Choice/Toggle branch beside it
    # which runs every name through `yaml_dump`. YAML 1.1 resolves `false` AND `off` both to the
    # boolean `False`, and `true` AND `on` both to `True`, so the emitted block carried two pairs of
    # duplicate keys and `Utils.UniqueKeyLoader` raised `KeyError: Duplicate key False found in
    # YAML` on the default template for this game. Under any loader that does NOT check duplicates
    # it is quieter and worse: `on: 0` silently overwrites `true: 50`, so the template ships with
    # its own default weighted to zero. `test_gf_option_template_yaml.py` is the gate.
    #
    # Nothing is lost by their absence, because these names were never the path a player's yaml
    # takes. `true` / `false` / `on` / `off` / `yes` / `no` written unquoted in a yaml are YAML 1.1
    # BOOLEANS -- they arrive as Python `bool` and are answered by the `from_any` override below,
    # which is what actually carries the "every yaml in the wild says `true`" promise. The names
    # kept here are for the quoted spellings and for the weights-dict form. `false` / `true` are
    # kept because they are the words the option was born with; `none` / `all` because a share
    # reads naturally that way and neither is a YAML boolean.
    special_range_names = {"false": 0, "none": 0,
                           "true": 100, "all": 100}

    @classmethod
    def from_any(cls, data):
        """🛑 A yaml `true` arrives here as a Python **bool**, and `bool` is a subclass of `int`, so
        AP's `Range.from_any` would fall through to `cls(int(data))` and read `true` as the integer
        **1** -- i.e. 1%, which is indistinguishable from OFF and would silently invert this option
        for every existing yaml. `from_text` never sees it, because the value is not a string.
        Catch the bool BEFORE the int path. (`Toggle.from_any` had the same shape and did not need
        this only because its range already was 0..1.)"""
        if isinstance(data, bool):
            return cls(cls.range_end if data else cls.range_start)
        return super().from_any(data)


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
    ("bosses", "Bosses", ("Boss", "MajorBoss", "LegacyBoss", "FieldBoss", "MinorDungeonBoss",
                          "Remembrance", "GreatRune")),
    ("collectathon", "Collectathon lines",
     ("Seedtree", "Church", "Basin", "Fragment", "Revered")),
    ("merchants", "Merchants", ("ShopSlot", "ShopNonSpell", "Shop")),
    ("items", "Items", ("KeyItem", "Legendary")),
    ("sweeps", "Dungeon sweeps", ("SweepSlot", "SweepSlotMajor", "SweepSlotMinor")),
)

# key -> (label, hint). The label says what the class IS in the words the game uses; the hint says
# what it costs you to pick it. Kept short on purpose: the option's own docstring carries the essay.
SURFACE_CLASS_LABELS = {
    "SweepSlotMajor": ("One check per MAJOR boss sweep",
                     "The SweepSlot half whose trigger is a major boss -- the same roster the "
                     "MajorBoss class uses, so a demigod's sweep and a cave's are priced apart. "
                     "40 of 218 triggers. A subset of SweepSlot: ticking both adds nothing."),
    "SweepSlotMinor": ("One check per MINOR boss sweep",
                     "The other half -- every sweep whose trigger is not on the major roster. "
                     "178 of 218 triggers, and the breadth is the point: these are the caves, "
                     "catacombs, tunnels and field bosses. A subset of SweepSlot."),
    "SweepSlot":    ("One check per dungeon sweep",
                     "Not a kind of check -- ONE member of every sweep your seed runs, so clearing "
                     "an area can pay out progression. Adds about as many slots as you have sweeps "
                     "(55 in a 4-region seed, ~170 on the full map) and needs Dungeon Sweep on."),
    "Boss":         ("Any boss drop",
                     "Every enemy the game gives a boss healthbar. Contains all the boss classes "
                     "below, so ticking this makes them redundant."),
    "MajorBoss":    ("Major bosses",
                     "Remembrance and great-rune arena bosses, plus curated majors for the regions "
                     "that have none. Contains Remembrances and Great Runes."),
    "LegacyBoss":   ("Legacy dungeon bosses",
                     "Bosses standing inside a legacy dungeon."),
    "MinorDungeonBoss": ("Minor dungeon bosses",
                     "Catacomb, cave, tunnel, gaol and Divine Tower bosses -- the minidungeons. "
                     "NOT the underground REGIONS: Nokron, Nokstella, Siofra and Ainsel are "
                     "overworld-sized and their bosses are elsewhere in this list."),
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
    # ⭐ THE DERIVED CLASSES HAVE NO TAGS, so the loop above cannot see them and the wizard would
    # tell a player that ticking SweepSlot and SweepSlotMajor together buys something. It does not.
    # Still not a typed table: the relation is read off contract.SWEEP_SLOT_CLASS_WANTS -- the same
    # structure the filter uses -- so it cannot disagree with what the surface actually does.
    subs = [c for c, want in contract.SWEEP_SLOT_CLASS_WANTS.items()
            if want is not None and c in vocab]
    if subs and "SweepSlot" in vocab:
        out.setdefault("SweepSlot", []).extend(sorted(subs))
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
    # 🛑 A RUNG IS JUDGED BY WHAT IT ADMITS, NOT BY WHETHER IT SPELLS A NEW CLASS NAME (#733).
    #
    # This used to skip a group only when every class in it was already accumulated. That is the same
    # confusion the default surface had: `Remembrance` and `GreatRune` are strict SUBSETS of
    # `MajorBoss`, so on any surface carrying `MajorBoss` the first widen group adds two names and
    # ZERO locations. While the two also sat in the default the two tests coincided by accident and
    # nothing showed; taking them out of the default made the ladder grow an inert rung, and
    # `test_the_shipped_default_ladder_has_no_inert_rung` caught it.
    #
    # An inert rung is not free: STRICT retries the whole fill on it, on seeds that are already
    # struggling to place their locks. The classes still ACCUMULATE (a later group may combine with
    # them; carrying them costs nothing), we simply do not spend a rung on a set that admits nothing
    # new.
    #
    # Falls back to the old name test when LOCATION_TAGS is absent (pre-regen), so the feature still
    # builds a ladder on an ungenerated tree.
    def _admits(classes):
        if not LOCATION_TAGS:
            return None
        return len(allowed_ap_ids(LOCATION_TAGS, set(classes)))

    seen = _admits(acc)
    for grp in _WIDEN_GROUPS:
        add = [c for c in grp if c not in acc]
        if not add:
            continue
        acc = acc + add
        grew = _admits(acc)
        if seen is not None and grew is not None and grew <= seen:
            continue
        rungs.append(list(acc))
        seen = grew
    return rungs


# The tag the hub-merchant bar reads. Pinned by test_gf_hub_merchant_bar against the tag names the
# generated data actually supplies (#707).
#
# 🛑 `Shop`, NOT `ShopSlot`. The guard was written 2026-07-18 against `ShopSlot`; the 2026-07-24
# ShopSlot rework redefined that tag as "at most ONE progression slot per MERCHANT, pinned to a
# merchant-unique ware" (gen_data.py) and stopped emitting it for hub rows. From that day the guard
# read a tag the hub does not carry and barred ZERO rows -- silently, because a derivation that reads
# a tag the data does not supply looks exactly like a derivation with nothing to do. That is what made
# the docstring's "derived from the generated data ... without a hand-list" a false comfort rather
# than a claim anyone could check. `Shop` is what hub merchant rows carry, and it is a strict SUPERSET
# of `ShopNonSpell`, `EniaShop` and `ShopSlot`, so it needs no companion tag.
_HUB_MERCHANT_TAGS = ("Shop",)


def _roundtable_merchant_aps():
    """Roundtable Hold (the always-open hub) MERCHANT rows -- Enia (remembrance weapons/armor) and
    the Twin Maiden Husks. BARRED from the progression surface (Alaric 2026-07-18): the hub is
    reachable at spawn, so a Lock / key item placed on a hub merchant slot is 'progression' you
    already hold on turn one -- trivial. This rule touches ONLY hub MERCHANT rows; the hub's Golden
    Seed checks (Seedtree, physical pickups) are left to the normal surface/defaulted logic.

    Derived from the generated data, so a regen that adds or moves a hub merchant row is covered
    without a hand-list -- but "derived" is only as good as the tag name being one the data still
    emits, which is the whole of #707. See `_HUB_MERCHANT_TAGS`.

    ONE CAUSE; the union happens at the chokepoint. This returns EVERY hub merchant row, not the
    subset no other bar covers -- of the 184 it returns, 95 are ALSO SHOP_RELEASE_GATED and 58 are
    ALSO DEFAULTED. Subtracting those here would make this bar's answer
    depend on tables that answer different questions, and move it whenever they regenerate (the
    failure `collapsed_lift_aps` documents as "ONE CAUSE AT A TIME"). `allowed_ap_ids` unions the
    bars and is the only place that should mix them."""
    try:
        from ..data import LOCATIONS, HUB
        from ..location_tags import LOCATION_TAGS as _lt
    except Exception:
        return frozenset()
    return frozenset(ap for (_n, ap, _f) in LOCATIONS.get(HUB, ())
                     if any(t in _lt.get(ap, ()) for t in _HUB_MERCHANT_TAGS))


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
    # _SURFACE_EXCLUDE_FLAGS) are barred here too, always, for the same reason. Release-gated shop
    # rows are likewise unconditional: a row absent from the shelf cannot host progression even
    # when its region is known and open (#724).
    try:
        from ..location_tags import SURFACE_EXCLUDE_APS as _sx
    except Exception:
        _sx = frozenset()
    try:
        from ..location_tags import SHOP_RELEASE_GATED_APS as _sg
    except Exception:
        _sg = frozenset()
    barred = (frozenset(defaulted) | _roundtable_merchant_aps()
              | frozenset(_sx) | frozenset(_sg))
    return {ap for ap, tags in tags_map.items()
            if contract.has_class(tags, sel) and ap not in barred}


def sweep_slot_aps(world, classes, tag_ids=frozenset()):
    """The SweepSlot half of the surface: AT MOST ONE member per enabled sweep trigger.

    Empty unless `SweepSlot` is in `classes`, so nothing shipped moves. This is the only surface
    class that is DERIVED rather than tagged (contract.SURFACE_DERIVED_CLASSES) -- gen_data cannot
    bake it, because whether a check is a sweep member is a per-seed answer (the rung) and whether it
    is on the surface is the question we are answering.

    # WHY ONE PER SWEEP, and not all of them

    MEASURED 2026-08-13, one ER slot + DOOM 1993, num_regions 4: a default seed's sweeps grant
    **924 of its 1517 locations (60.9%)**, against a surface of 30 (2.0%). Admitting every member
    would take the surface to ~63% of the seed -- which does fix the intake collapse #631 is about,
    and makes "confined to the surface" mean almost nothing, which is the promise the option exists
    to keep. One member per trigger is 55 here and 218 full-map: it roughly DOUBLES the surface
    without diluting it.

    This is ShopSlot's argument, deliberately: "a merchant enters the pool once, so however large
    their stock they can hold at most one progression item and cannot dominate the surface by
    breadth." A sweep is the same shape -- a trigger with a large membership -- and gets the same
    treatment.

    # WHICH member

    The lowest ap-id NOT already on the tag surface (`tag_ids`), falling back to the lowest overall.
    Two reasons it is not a random draw: `world.random` is consumed a different number of times
    depending on how hard fill works, so drawing here would move the seed for everything downstream
    (the reason `_confine_draw` is a hash); and the choice must be reproducible from the multidata
    for the tracker to star the same check the fill used. Skipping the tag surface matters because
    the six SURFACE-CUTTABLE classes are still in the pre-cut member lists, so a naive `min()` can
    nominate a check the surface already had -- adding a name and no breadth.

    🛑 Reads `boss_locks.rung_sweeps`, NOT `enabled_sweeps`. The latter applies the per-seed surface
    cut, which reads the surface, which is this function -- a cycle. `rung_sweeps` reads only
    `dungeon_sweep`.
    """
    chosen = [c for c in contract.SURFACE_CLASSES
              if c in set(classes or ()) and c in contract.SWEEP_SLOT_CLASS_WANTS]
    if not chosen:
        return frozenset()
    try:
        from .boss_locks import rung_sweeps  # noqa: PLC0415 -- import cycle at module scope
    except Exception:
        return frozenset()
    try:
        from ..location_tags import SURFACE_EXCLUDE_APS as _sx
    except Exception:
        _sx = frozenset()
    barred = (frozenset(_world_barred_aps(world)) | _roundtable_merchant_aps() | frozenset(_sx))
    # 🛑 PASS THE HEALTHBARS EXPLICITLY. `contract.sweep_slot_skips()` can resolve them itself, but
    # only via a package-relative import, and on failure it degrades to the DECLARED skips alone --
    # which would quietly put the unfireable triggers back on the surface and reopen #672. The
    # production path must not depend on an import that is allowed to fail; the census tool, which
    # has no world, keeps the lazy default.
    try:
        from ..boss_healthbars import BOSS_HEALTHBARS  # noqa: PLC0415 -- data leaf
        skips = contract.sweep_slot_skips(healthbars=BOSS_HEALTHBARS)
    except Exception:
        skips = contract.sweep_slot_skips()
    # #703: more members per sweep when there are FEW partners, exactly one when there are many.
    # In a 2-game world the partner's progression saturates its own ~404 locations during
    # fill_restrictive and the useful tier is exhausted before the scan reaches a partner slot; the
    # fix is more slots, not weaker curation -- on-surface stayed 100% across the whole measured
    # curve, which is why this beats lowering `confine_foreign_progression`.
    #
    # 🛑 `players - 1`, i.e. FOREIGN players. A solo seed has nothing to send, `slots_per_sweep`
    # returns 1 there, and a solo generation is byte-unchanged.
    foreign = getattr(getattr(world, "multiworld", None), "players", 1) - 1
    # #734: the class decides WHICH sweeps, `nominate_sweep_slots` still decides which MEMBER. The
    # split is a filter on the trigger set and nothing else -- so a seed selecting plain `SweepSlot`
    # nominates exactly what it did before, byte for byte, and one selecting both subclasses gets
    # the same set by a different route (they partition it; there is no third bucket).
    try:
        from ..boss_sweeps import MAJOR_SWEEP_TRIGGERS  # noqa: PLC0415 -- data leaf
    except Exception:
        # 🛑 DEGRADE TO THE WHOLE SET, NOT TO EMPTY. Without the table the split cannot be honoured;
        # nominating nothing would silently shrink a surface the player asked to widen, and an
        # empty surface is the failure this feature exists to prevent (#631).
        MAJOR_SWEEP_TRIGGERS = frozenset()
        chosen = ["SweepSlot"] if set(chosen) else []
    sweeps = rung_sweeps(world)
    out = set()
    for cls in chosen:
        part = contract.sweeps_for_surface_class(sweeps, cls, MAJOR_SWEEP_TRIGGERS)
        if not part:
            continue
        out |= contract.nominate_sweep_slots(part, barred=barred, prefer_not_in=tag_ids,
                                             skips=skips, slots=contract.slots_per_sweep(foreign))
    return frozenset(out)


def surface_ap_ids(world, classes):
    """THE surface for `classes`: the tagged half plus the derived half, in one expression.

    Every caller that used to say `allowed_ap_ids(LOCATION_TAGS, classes, defaulted=...)` says this
    instead -- the fill's own confinement, the foreign bar, the ladder's open-location scan and the
    slot_data emit. That was already the file's rule for the tag half ("the single surface chokepoint
    both confinements funnel through"); a derived class that reached only three of the four would put
    a progression item somewhere the tracker does not star, or star a check the fill cannot use."""
    ids = allowed_ap_ids(LOCATION_TAGS, classes, defaulted=_world_barred_aps(world))
    extra = sweep_slot_aps(world, classes, ids)
    return (ids | extra) if extra else ids


def is_restricted_progression(item, player):
    """True iff `item` is THIS world's own progression that we confine: advancement, owned by `player`,
    and NOT a Boss Key (those are exempt). Pure over an item-like with .player/.advancement/.name."""
    if getattr(item, "player", None) != player or not getattr(item, "advancement", False):
        return False
    return not str(getattr(item, "name", "")).startswith(_BOSS_KEY_PREFIX)


def _foreign_open_locations(multiworld, er_players):
    """Every location in a NON-Elden-Ring player's world that we may honestly offer a Lock.

    Four filters, and each one is load-bearing:

    * **not ours** -- `er_players` is every slot this hook is running for. An Elden Ring location is
      the other pass's business.
    * **empty** -- `loc.item is None`. A location another world already filled during its own
      `pre_fill` is spoken for; overwriting it is how you corrupt a partner's plando.
    * **not `locked`** -- AP's flag for "this location's content is decided". Event locations carry
      it, and so does anything a world nailed down deliberately.
    * 🛑 **not EXCLUDED** -- `exclude_locations` is the player's promise that nothing REQUIRED will
      be there, and a released Lock is progression. `fill_restrictive` does NOT check
      `progress_type` (`distribute_items_restrictive` filters before calling it), so if we do not
      filter here, nobody does, and a partner's excluded check quietly becomes mandatory.

    Reachability is NOT filtered: `fill_restrictive` walks its own sphere order and that is the one
    judgement it makes better than a predicate can.
    """
    try:
        from BaseClasses import LocationProgressType
        excluded = LocationProgressType.EXCLUDED
    except Exception:      # a BaseClasses without the enum: filter nothing rather than crash
        excluded = object()
    return [
        loc for loc in multiworld.get_locations()
        if loc.player not in er_players
        and loc.item is None
        and not getattr(loc, "locked", False)
        and getattr(loc, "progress_type", None) is not excluded
    ]


def place_released_locks(multiworld, worlds) -> None:
    """`stage_pre_fill`: place every Elden Ring world's travelling progression across every Elden
    Ring world's surface, in ONE pass, and spill whatever does not fit back into the pool.

    # Why this is not an item_rule (er-archipelago#491)

    The first version barred a released Lock from our own non-surface checks and let the general
    fill place it. It worked -- 42-48% travel in a two-slot multiworld with ~90% of Locks still on
    curated checks -- and it had NO SPILL. `apply()` is documented "Never FillErrors" because
    confined Locks get the feasibility ladder AND the return-to-pool valve; a bare item_rule has
    neither, so a seed whose surface is too small simply fails. Three configurations found it --
    a narrowed surface, `num_regions: 1`, and a shifted filler pool -- each missed by a different
    threshold, because capacity is not the constraint: REACHABLE capacity in sphere order is, and no
    count of open slots can see it. A real fill can, because it just tries.

    # Why `stage_pre_fill` and not `pre_fill`

    🛑 `AutoWorld.call_all` walks `multiworld.player_ids` IN PLAYER ORDER, so placing into another
    player's locations from our own `pre_fill` would give player 1 first pick of everyone's surface
    and player 2 the leftovers -- curation that depends on slot number. It is also out of spec:
    TUNIC's own `stage_pre_fill` raises with "caused by another world filling TUNIC locations during
    pre_fill... we cannot recover from this issue." `stage_pre_fill` is the sanctioned hook -- a
    classmethod run ONCE for the whole multiworld, after every per-world `pre_fill` -- and TUNIC uses
    it for this exact shape, gathering items and locations across every slot of its own game.

    🛑 Unlike TUNIC's, our items are PROGRESSION, not filler, so this cannot be a `place_locked_item`
    loop: it needs `fill_restrictive` with a real state, the way `_place` already does.

    # Cross-game (#703)

    Cross-game USED to be deliberately untouched: this hook saw only Elden Ring worlds, and a Lock
    bound for a partner was one it did not place -- it spilled to the general fill. That was the
    design, and the measurement says the valve never opened: our surfaces host ~170 checks against
    at most ~36 Locks, so nothing ever spilled. **0 Locks reached a Hollow Knight slot across four
    configurations**, including a 2xER + 1xHK seed where 15 of 28 Locks travelled and every one went
    to the other Elden Ring world.

    So `cross_game_progression` routes a share of the eligible progression at partner locations
    FIRST, before the ER surfaces get a look. `auto` is 1/n_games -- half in a two-game seed.

    #811: that set used to be `gf_released_lock_items`, so despite the option's name the pass could
    see Region Locks and NOTHING ELSE. Required Great Runes were advancement, but `apply()` removed
    them first and locked them onto their owner's surface. The pass now reads
    `gf_released_progression_items`: released Locks plus every non-Lock advancement item whenever
    this world has a non-zero cross-game share. The remainder still falls through to the same ER
    surface pass, preserving curation and reachability.

    ⚠️ THIS FILLS ANOTHER GAME'S LOCATIONS, which is exactly what the note above warns about: TUNIC
    raises "caused by another world filling TUNIC locations during pre_fill" and cannot recover.
    Three things keep that as narrow as possible -- only EMPTY, unlocked locations are offered, the
    fill is partial so nothing is forced, and the whole pass is caught so our failure can never be
    the thing that breaks a generation. It is still a real risk with a game that objects on
    principle, and `cross_game_progression: 0` is the escape hatch.
    """
    import inspect
    import logging
    from Fill import fill_restrictive

    items, locations, participants = [], [], []
    for w in worlds:
        pending = list(getattr(w, "gf_released_progression_items",
                               getattr(w, "gf_released_lock_items", ())) or ())
        if not pending:
            continue
        participants.append(w)
        items.extend(pending)
        locations.extend(_open_allowed(w, selected_surface(_selection(w))))
    if not items:
        return

    # Out of the pool for the duration: fill_restrictive places from the list we hand it, and an
    # item left in `itempool` as well would be placed twice. Whatever survives goes back below.
    for it in items:
        multiworld.itempool.remove(it)
    n0 = len(items)
    kwargs = {"lock": True}
    if "allow_partial" in inspect.signature(fill_restrictive).parameters:
        kwargs["allow_partial"] = True

    # ---- CROSS-GAME FIRST (#703) --------------------------------------------------------------
    # Offered BEFORE the Elden Ring surfaces, because our surfaces have four times the room they
    # need and would otherwise absorb every progression item -- which is the measured defect.
    cross_offered = cross_placed = 0
    er_players = {w.player for w in worlds}
    n_games = len({w.game for w in getattr(multiworld, "worlds", {}).values()}) or 1
    share = max((cross_game_share(w, n_games) for w in participants), default=0)
    if share > 0:
        foreign = _foreign_open_locations(multiworld, er_players)
        k = (n0 * share + 50) // 100
        if foreign and k > 0:
            # The old list was all Locks, so its stable construction order did not matter. Once
            # required Great Runes joined it, slicing before shuffling would let the leading Locks
            # consume the entire cross-game quota and recreate #811 under a different name.
            multiworld.random.shuffle(items)
            batch, rest = items[:k], items[k:]
            cross_offered = len(batch)
            multiworld.random.shuffle(foreign)
            try:
                fill_restrictive(multiworld, multiworld.get_all_state(False), foreign, batch,
                                 **kwargs)
            except Exception:  # noqa: BLE001 -- see below
                # 🛑 DELIBERATELY BROAD. This pass reaches into another game's locations, so the set
                # of things it can raise is the set of things every OTHER apworld can raise, which is
                # not enumerable from here. Curation is a nice-to-have; a failed generation is not.
                # Swallowing leaves `batch` unplaced, and unplaced Locks fall through to the Elden
                # Ring pass below exactly as they did before #703 existed.
                logging.getLogger("Greenfield").warning(
                    "[greenfield] progression surface: the cross-game progression pass raised and "
                    "was abandoned; its %d item(s) fall back to the Elden Ring surfaces, which is the "
                    "pre-#703 behaviour. Set cross_game_progression: 0 if this recurs",
                    len(batch), exc_info=True)
            cross_placed = cross_offered - len(batch)
            items = batch + rest          # whatever it could not place rejoins the ER pass
            logging.getLogger("Greenfield").info(
                "[greenfield] progression surface: cross-game pass placed %d of %d offered "
                "(%d%% share of %d eligible progression, %d game(s), %d open foreign location(s))",
                cross_placed, cross_offered, share, n0, n_games, len(foreign))

    multiworld.random.shuffle(locations)
    state = multiworld.get_all_state(False)
    # Same access-check override `_place` documents at length: under accessibility:minimal
    # fill_restrictive stops verifying reachability, which would lock a Lock behind its own gate.
    # Forced on for every participating world, restored in `finally` so a raise cannot leak it.
    saved = [(w, getattr(w.options, "accessibility", None)) for w in participants]
    saved = [(w, acc, acc.value) for w, acc in saved if acc is not None]
    try:
        for _w, acc, _v in saved:
            acc.value = 0
        fill_restrictive(multiworld, state, locations, items, **kwargs)
    finally:
        for _w, acc, v in saved:
            acc.value = v

    # THE SPILL, and the whole reason this is a fill rather than a rule: anything the surfaces could
    # not host goes back to the general fill unconstrained. A seed loses CURATION, never generation.
    for it in items:
        multiworld.itempool.append(it)
    logging.getLogger("Greenfield").info(
        "[greenfield] progression surface: placed %d/%d RELEASED Lock(s) (%d abroad) across %d "
        "Elden Ring world(s); %d SPILLED to the general fill%s",
        n0 - len(items), n0, cross_placed, len(participants), len(items),
        (" (curation only -- they still travel, just not onto a curated check): "
         + ", ".join(sorted(it.name for it in items))) if items else "")


def foreign_advancement_barred(item, player):
    """True iff `item` is ANOTHER player's advancement item -- the thing confine_foreign_progression
    keeps off this world's non-surface (filler) checks. Our OWN items (any classification) and any
    non-advancement item pass. Pure over an item-like with .player/.advancement. The core item_rule on
    a non-surface location is `not foreign_advancement_barred(item, self.player)`."""
    return bool(getattr(item, "advancement", False)) and getattr(item, "player", None) != player


def confine_pct(world) -> int:
    """The share of foreign advancement this world confines to its surface, 0-100.

    Absent option -> 100, i.e. the pre-share behaviour. That is the opposite convention from
    `_released_pct`, and deliberately so: both mean "an older or stubbed world behaves exactly as it
    did before the option existed", and before this option existed the bar was unconditional."""
    o = getattr(getattr(world, "options", None), "confine_foreign_progression", None)
    if o is None:
        return 100
    try:
        return max(0, min(100, int(o.value)))
    except (TypeError, ValueError):
        return 100


def _confine_draw(salt: str, item) -> int:
    """A stable 0-99 for a foreign item, from a hash rather than an rng.

    🛑 WHY A HASH AND NOT `world.random`. This is read from inside a LOCATION'S `item_rule`, which
    Archipelago calls an unbounded number of times per item -- once per candidate location, again on
    every swap in `remaining_fill`, again during accessibility corrections. An rng draw there would
    return a different answer on each call (so a name would be confined for one location and free
    for the next, which is not a share of anything), and it would consume the seed's rng stream a
    different number of times depending on how hard fill had to work -- the exact failure
    [[er-fill-slot-data-is-called-more-than-once]] describes. A hash is pure, so the answer is fixed
    for the whole generation and the stream is untouched.

    Keyed on (salt, owning player, item NAME): per-name, matching `filler_foreign_pct`'s documented
    "propensity by distinct item name, not a per-copy rule". The salt carries the multiworld seed and
    OUR player number, so two Elden Ring slots in the same seed confine different names -- otherwise
    every ER world in a multiworld would agree, and a foreign item barred from one would be barred
    from all of them, which is a much harder rule than the percentage claims."""
    key = "%s|%s|%s" % (salt, getattr(item, "player", 0), getattr(item, "name", ""))
    digest = hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") % 100


def _confine_salt(world) -> str:
    """Deterministic per (seed, player). Reads the seed rather than drawing from `world.random`, so
    installing this predicate cannot shift the rng stream for anything downstream of it -- which is
    what keeps the 100 default byte-identical to the toggle it replaced."""
    mw = getattr(world, "multiworld", None)
    return "%s|%s" % (getattr(mw, "seed", 0), getattr(world, "player", 0))


def foreign_bar_for(world):
    """The predicate `core._add_locations` (and the finale's hand-built copy) install on every
    NON-surface location: `not foreign_bar_for(world)(item, player)`.

    At 100 this is `foreign_advancement_barred` itself -- the same object, so the shipped default
    runs the same code path it always did. Below 100 it is a share: still only ever foreign
    advancement, and of that, only the names whose draw falls under the percentage."""
    pct = confine_pct(world)
    if pct >= 100:
        return foreign_advancement_barred
    if pct <= 0:
        # Nothing is confined. Returning a constant-False predicate rather than None keeps core's
        # call shape identical; core also stops installing the rule at all (see confined_surface_ids
        # returning None), so this is belt and braces.
        return lambda item, player: False
    salt = _confine_salt(world)
    def _barred(item, player, _salt=salt, _pct=pct):
        if not foreign_advancement_barred(item, player):
            return False
        return _confine_draw(_salt, item) < _pct
    return _barred


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


def confined_surface_ids(world):
    """The ap-ids of THIS world that MAY host foreign progression, when confine_foreign_progression is
    on -- i.e. the selected surface. Core bars other players' advancement on every own location whose
    ap-id is NOT in this set, confining foreign progression to the same checks the own region Locks use.
    Returns None when the feature is inactive (option off, surface mode off, empty surface, or tags not
    generated), meaning 'apply no foreign bar'. Uses the SAME surface resolution as apply()/slot_data(),
    so where foreign progression may land and where own progression is placed can never disagree."""
    if confine_pct(world) <= 0 or not LOCATION_TAGS:
        return None
    classes = selected_surface(_selection(world))
    if not classes:
        return None
    return surface_ap_ids(world, classes)


def cross_game_share(world, n_games: int) -> int:
    """Percent of a world's travelling Locks that may land in a non-ER game. Pure over the option
    value and the game count.

    `auto` (-1) resolves to **1/n_games** as a percentage -- 2 games is 50, 4 is 25 -- which is the
    same 1/N rule the export-volume side is judged by. Absent option, solo, or a single game means
    0: there is nowhere else to send.
    """
    if n_games <= 1:
        return 0
    opt = getattr(getattr(world, "options", None), "cross_game_progression", None)
    if opt is None:
        return 0                      # older yaml -> behave as before this option existed
    v = int(opt.value)
    if v < 0:
        # auto. HALF-UP, not `round`: Python rounds .5 to even, so a four-game seed would get
        # 100/8 = 12.5 -> 12 while the export-volume side's 1/N cap says 13. A silent one-point
        # disagreement between the two halves of #703 is exactly the class of bug this repo has
        # paid for twice, and `released_locks` already rounds half-up for the same reason.
        return max(0, min(100, (100 + n_games // 2) // n_games))
    return max(0, min(100, v))


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


def travelling_progression(items, released, cross_share):
    """The exact item objects handed from `apply()` to the stage-wide placement pass.

    Released Region Locks always travel, preserving `progression_bias`. With a non-zero
    `cross_game_progression` share, every other restricted advancement item travels too so required
    Great Runes and legacy keys are actually candidates for that share (#811). At zero, non-Locks
    keep the pre-#811 local-surface behaviour.
    """
    out = list(released)
    if cross_share <= 0:
        return out
    seen = {id(it) for it in out}
    out.extend(it for it in items if id(it) not in seen)
    return out


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


def collapsed_site_regions(world):
    """#701 OPTION B -- {ap_id: region} for every hub-COLLAPSED merchant row THIS SEED CAN PLACE.

    A row whose seller stands in more than one region (Patches/Thiollier: Limgrave, Mt. Gelmir,
    Cerulean; the Dragon Communion altars: Caelid, Limgrave) is pinned to no region by gen_data, falls
    onto the always-open hub, and option C (PR #706) bars it from carrying progression for exactly the
    reason Cokeman5 hit: the hub is always kept, so "any of three regions" had become "no requirement
    at all". Option B gives the row a real region instead -- the EARLIEST of its own sites that this
    seed KEPT, in region_spine.SPINE order -- so it can carry progression again, gated behind that
    region's Lock (core._add_locations puts the gate on the location's access_rule).

    ⭐ WHY EARLIEST-KEPT IS SAFE AND NOT MERELY CONVENIENT. The honest rule is a DISJUNCTION: reachable
    if the player holds ANY site. Requiring one NAMED site is STRICTER than that disjunction, so the
    approximation can only ever refuse a placement the player could have reached -- never the reverse,
    which is the direction that strands a seed. It is EXACT when the seed kept exactly one site. The
    real disjunction is #701 option 1 and still needs #320/#502's machinery; it is not this.

    🛑 OPTION B COMPOSES WITH OPTION C, IT DOES NOT REPLACE IT. A row with NO kept site is absent from
    this map, stays in DEFAULTED_REGION_APS, and keeps C's bar -- C's behaviour is B's FALLBACK. A
    `num_regions` draw that keeps none of {Limgrave, Mt. Gelmir, Cerulean} is a legitimate seed, so
    refusing to generate it would be the regression; B NARROWS C's bar to the case where it is still
    true. Both halves are asserted in tests/test_gf_hub_collapsed_merchant_sites.py.

    Cached on the world: called from core._add_locations (once per region) and from the surface math,
    which must give the same answer or the item_rule and the advertised surface drift apart."""
    cached = getattr(world, "_gf_collapsed_site_regions", None)
    if cached is not None:
        return cached
    try:
        from ..location_tags import HUB_COLLAPSED_SITE_APS as _sites
    except Exception:                                   # pre-regen data -> feature inert, C's bar stands
        _sites = {}
    out = {}
    if _sites:
        from ..region_spine import earliest_kept_site
        kept = set(getattr(world, "gf_kept", ()) or ())
        for ap, sites in _sites.items():
            site = earliest_kept_site(sites, kept)
            if site is not None:
                out[int(ap)] = site
    try:
        world._gf_collapsed_site_regions = out
    except Exception:                                   # not a real world (pure callers) -> no cache
        pass
    return out


def collapsed_lift_aps(world):
    """The ap ids whose DEFAULTED bar option B lifts in this seed -- and ONLY that bar.

    🛑 ONE CAUSE AT A TIME. `core._NO_PROGRESSION_APS` is a UNION of three independent reasons, and a
    row can hold more than one: two of the 16 Patches rows (7774847/7774848) are ALSO
    SHOP_RELEASE_GATED (the merchant does not stock them until an unlock fires), and the region being
    open says nothing about the shelf. Subtracting an ap from the union would lift every reason at
    once, so the ones another rule still bars are removed here -- in the ONE place both the item_rule
    and the surface math read, so the two cannot disagree about which rows moved."""
    ids = frozenset(collapsed_site_regions(world))
    if not ids:
        return frozenset()
    try:
        from ..location_tags import ERDTREE_BURN_APS as _b
    except Exception:
        _b = frozenset()
    try:
        from ..location_tags import SHOP_RELEASE_GATED_APS as _g
    except Exception:
        _g = frozenset()
    return ids - frozenset(_b) - frozenset(_g)


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
    try:
        from ..location_tags import SHOP_RELEASE_GATED_APS as _s
    except Exception:
        _s = frozenset()
    # #701 option B: a hub-collapsed merchant row THIS SEED could region to a kept site is no longer a
    # guess -- it is gated behind that region (core._add_locations' access_rule), so it comes OFF the
    # defaulted bar here as well. Subtracted from `_d` alone and never from the union below: the lift
    # answers the GUESSED-REGION cause only, and `collapsed_lift_aps` has already dropped the rows some
    # other rule still bars. Rows with no kept site are not in the lift and keep option C's bar.
    _d = frozenset(_d) - collapsed_lift_aps(world)
    _m = missable_barred_aps(world)
    if getattr(world, "gf_capital_reconciler", False):
        return frozenset(_d) | frozenset(_s) | _m
    try:
        from ..location_tags import ERDTREE_BURN_APS as _b
    except Exception:
        _b = frozenset()
    return frozenset(_d) | frozenset(_b) | frozenset(_s) | _m


def _open_allowed(world, classes):
    """Unfilled locations of this player whose tags put them ON THE SURFACE for `classes`."""
    ids = surface_ap_ids(world, classes)
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
    """core.pre_fill hook. Confine this world's own progression to the selected surface; widen via
    the ladder; return the remainder to the pool. Never FillErrors.

    Always strict since progression_surface_mode was retired -- the soft (mark-and-spill) and off
    regimes were unreachable from any yaml for two releases before they were deleted."""
    if not LOCATION_TAGS:
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
    released = released_locks(to_place, _released_pct(world), world.random)
    n_games = len({w.game for w in getattr(mw, "worlds", {}).values()}) or 1
    travelling = travelling_progression(
        to_place, released, cross_game_share(world, n_games))
    if travelling:
        _rel = {id(it) for it in travelling}
        to_place = [it for it in to_place if id(it) not in _rel]
    world.gf_locks_released = sorted(it.name for it in released)
    # The handle `stage_pre_fill` reads. The ITEMS, not the names: it has to remove these exact
    # objects from the pool and hand them to fill_restrictive.
    world.gf_released_lock_items = list(released)
    world.gf_released_progression_items = list(travelling)
    n0 = len(to_place)
    for it in to_place:
        mw.itempool.remove(it)
    strict = True   # the only regime; see ProgressionSurfaceMode's retirement note
    rungs = build_ladder(surface)
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
    on an internal audit error (never block gen on an audit bug)."""
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
               "confine_foreign_progression": ConfineForeignProgression,
               "cross_game_progression": CrossGameProgression}
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
        `confine_foreign_progression` keeps that share of every OTHER player's advancement on
        exactly this set, and whatever share of your own Locks you chose to keep curated lands here
        too. A star is "something important can be here", not "your key is here". 🛑 At a confine
        share below 100 the star weakens once more: the un-confined share of foreign progression can
        sit on any reachable check of yours, starred or not.

        It REPLACES `bigTicketLocations`, which was a second list of "important checks" naming a set
        progression could never reach: big-ticket targeted {MajorBoss, Remembrance, GreatRune} while
        the surface is {Remembrance, Seedtree, Church, Boss, Fragment, Revered} -- intersection
        Remembrance alone. The client was starring MajorBoss/GreatRune checks that this module FORBIDS
        a region Lock from ever occupying. A tracker pointing at checks the locks cannot be on is worse
        than no tracker: it teaches the player something false.

        Emitting the surface itself makes that drift unrepresentable -- "where progression may be"
        and "what the client stars" are now one expression, evaluated once.
        """
        classes = selected_surface(_selection(world))
        ids = surface_ap_ids(world, classes)
        own = {loc.address for loc in world.multiworld.get_locations(world.player)
               if getattr(loc, "address", None) is not None}
        return {contract.PROGRESSION_SURFACE_LOCATIONS: sorted(i for i in ids if i in own)}
