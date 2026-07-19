"""The apworld <-> client slot_data CONTRACT -- single source of truth (matt-free greenfield).

Every key that flows from the apworld's fill_slot_data into the runtime client is declared here ONCE:
its exact name, its wire SHAPE (tied to the client's parser), whether it is required, which contract
PROFILE(s) use it (greenfield / bedrock / both), which apworld module PRODUCES it, which client
file:fn CONSUMES it, and a one-line semantic. `validate_slot_data()` checks an assembled slot_data
dict against these declarations so a shape/spelling/required drift fails at GEN time (this is what
would have caught the list-vs-scalar `locationFlags` bug). `to_markdown/json/rust` emit the docs and
the language-neutral + Rust-side mirrors so the client validates the SAME contract (two-sided).

STRICT EMISSION (F2 fix, 2026-07-06): validate_slot_data now also REJECTS any emitted key that is
not declared here (top-level and inside the `options` sub-dict). registry.merge_slot_data gates
feature contributions through BY_NAME too, so an undeclared key fails at the merge, not in-game.

NESTED KEYS / OPTIONS ECHO (F1 fix, 2026-07-06): the client's option parsers read
`slot_data["options"][<key>]` (er-logic/src/options.rs parse_bool_option), but features used to emit
their toggles TOP-LEVEL only -- so death_link/enable_dlc/no_weapon_requirements/scaling knobs were
silently dark while "slot_data OK". The `options` ContractKey below declares the sub-dict; each
sub-key is its own ContractKey carried in `subkeys=`. core._options_echo emits it centrally; the
features' top-level emissions remain as harmless legacy duplicates (declared below as such).

`required` is PROFILE-AWARE: it only applies when validating a profile the key belongs to. Keys
tagged (BEDROCK,) are therefore never required (nor shape-checked) for a greenfield gen, and
vice versa.

To add a key: add ONE ContractKey below. To swap to Bedrock compatibility: emit the keys tagged
`bedrock` and validate with profile="bedrock"; the two contracts are diffable in this one file.
"""

# ---------------------------------------------------------------------------------------------------
# SHAPES -- each corresponds to exactly one client-side parser. The python `check` mirrors the Rust
# parser's expectation; `rust` is the generated-mirror variant + the parser it documents.
# ---------------------------------------------------------------------------------------------------
def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _chk_scalar_int_map(v):
    # i64_to_u32_map / i64_map / str_to_u32 : {key: int}  (NOT a list value)
    if not isinstance(v, dict):
        return "expected object {key: int}"
    for k, val in v.items():
        if not _is_int(val):
            return f"value for {k!r} must be int, got {type(val).__name__} ({val!r})"
    return None


def _chk_listval_int_map(v):
    # str_to_u32vec : {key: [int, ...]}
    if not isinstance(v, dict):
        return "expected object {key: [int]}"
    for k, val in v.items():
        if not isinstance(val, (list, tuple)) or not all(_is_int(i) for i in val):
            return f"value for {k!r} must be list[int], got {val!r}"
    return None


def _chk_str_map(v):
    # {key: str}
    if not isinstance(v, dict):
        return "expected object {key: str}"
    for k, val in v.items():
        if not isinstance(val, str):
            return f"value for {k!r} must be str, got {type(val).__name__} ({val!r})"
    return None


def _chk_triple_list(v):
    # parse_triples : [[lo, hi, flag], ...]
    if not isinstance(v, (list, tuple)):
        return "expected [[int,int,int], ...]"
    for t in v:
        if not isinstance(t, (list, tuple)) or len(t) != 3 or not all(_is_int(i) for i in t):
            return f"each entry must be [int,int,int], got {t!r}"
    return None


def _chk_pair_list(v):
    # parse pairs : [[a, b], ...] -- e.g. uniqueStartGrants [[fullId, obtainedFlag], ...]
    if not isinstance(v, (list, tuple)):
        return "expected [[int,int], ...]"
    for t in v:
        if not isinstance(t, (list, tuple)) or len(t) != 2 or not all(_is_int(i) for i in t):
            return f"each entry must be [int,int], got {t!r}"
    return None


def _chk_int_list(v):
    # arr_i32 / arr_u32 : [int, ...]
    if not isinstance(v, (list, tuple)) or not all(_is_int(i) for i in v):
        return "expected [int, ...]"
    return None


def _chk_str_list(v):
    # arr_str : [str, ...] -- item NAMES (goalItems). Names, not ids, because the client already
    # matches received items BY NAME everywhere else (region locks, boss keys), and a name survives an
    # ap-id renumber where a positional id does not.
    if not isinstance(v, (list, tuple)) or not all(isinstance(i, str) for i in v):
        return "expected [str, ...]"
    return None


def _chk_bool(v):
    if not isinstance(v, bool):
        return f"expected bool, got {type(v).__name__}"
    return None


def _chk_bool_or_int(v):
    # parse_death_link / parse_dlc : tolerant bool-or-0/1
    if not (isinstance(v, bool) or (_is_int(v) and v in (0, 1))):
        return "expected bool or 0/1"
    return None


def _chk_int_or_bool(v):
    # parse_bool_option-style toggles that may carry a non-0/1 payload (nonzero = on).
    if not (isinstance(v, bool) or _is_int(v)):
        return f"expected bool or int, got {type(v).__name__}"
    return None


def _chk_int(v):
    if not _is_int(v):
        return f"expected int, got {type(v).__name__}"
    return None


def _chk_number(v):
    # client reads f64; int or float both fine (bool is NOT a number here).
    if not (_is_int(v) or isinstance(v, float)):
        return f"expected number, got {type(v).__name__}"
    return None


def _chk_str(v):
    if not isinstance(v, str):
        return f"expected str, got {type(v).__name__}"
    return None


def _chk_nested_grants(v):
    """progressiveGrants : {name: [{"goods": int, "flags": [int], "consumed": bool}, ...]}

    `consumed` is REQUIRED, and it is required for a reason worth a paragraph.

    The client folds a rung's goods one of two ways: OWNED goods go to `unique_goods`, a SELF-HEALING
    set meaning "the player should have this; if it is missing, grant it" (correct for a stone bell
    bearing -- a key item you keep forever, and one lost to a save-scum should come back). CONSUMED
    goods are ledgered by the copy's stream index and granted exactly ONCE.

    Ship a consumable as OWNED and the game eats itself: a Golden Seed is SPENT at a Site of Grace, so
    the reconciler sees it leave the inventory and hands it straight back -- upgrade, re-grant,
    upgrade, re-grant, unbounded, until flask potency runs past its cap and the game CTDs. That is
    exactly what shipped on 2026-07-12, and it shipped because the field did not exist and the
    dangerous default was the silent one.

    So it is not optional and it does not default. A rung must SAY which it is.
    """
    if not isinstance(v, dict):
        return "expected {name: [{goods:int, flags:[int], consumed:bool}]}"
    for k, lst in v.items():
        if not isinstance(lst, (list, tuple)):
            return f"{k!r} must map to a list"
        for e in lst:
            if not isinstance(e, dict) or not _is_int(e.get("goods")) or \
               not (isinstance(e.get("flags"), (list, tuple)) and all(_is_int(i) for i in e["flags"])):
                return f"{k!r} entry must be {{goods:int, flags:[int], consumed:bool}}, got {e!r}"
            if not isinstance(e.get("consumed"), bool):
                return (f"{k!r} rung is missing `consumed` (bool): {e!r}. A rung must declare whether "
                        f"its goods are SPENT by the player (consumed=true -> granted once, ledgered) "
                        f"or KEPT (consumed=false -> self-healing). Shipping a consumable as kept "
                        f"re-grants it every time the player spends it, and CTDs the game.")
    return None


def _chk_flask_ladder(v):
    """flaskLadder : [{"charges": int, "potency": int}, ...] -- the cumulative flask CHARGE target the
    client reconciles the player's flask to after receiving (i+1) Progressive Flask Upgrade copies (a
    direct write). Charges are a reconciled LEVELED STATE; POTENCY is documentation here -- the client
    sets potency from the consumed Sacred Tears the SAME item grants via progressiveGrants (one tear
    per copy), not from this ladder. So the flask is a HYBRID that rides BOTH wires (charges here,
    potency in progressiveGrants); this is intentional and non-overlapping. (Range/monotonic invariants
    -- charges 2..14, potency 0..12, non-decreasing, charges reaching max at the last rung -- are
    guarded producer-side in features/progressive.py and its tests; the wire shape check here is the
    container + int fields.)"""
    if not isinstance(v, (list, tuple)):
        return "expected [{charges:int, potency:int}, ...]"
    for e in v:
        if not isinstance(e, dict) or not _is_int(e.get("charges")) or not _is_int(e.get("potency")):
            return f"each entry must be {{charges:int, potency:int}}, got {e!r}"
    return None


def _chk_options_dict(v):
    # the `options` sub-dict itself; each declared sub-key is validated by validate_slot_data
    # against its OWN shape (see ContractKey.subkeys), so this only asserts the container.
    if not isinstance(v, dict):
        return "expected object {option: value}"
    return None


def _chk_any(v):
    return None


# name -> (checker, rust_variant, client_parser_doc)
SHAPES = {
    "SCALAR_INT_MAP":  (_chk_scalar_int_map,  "ScalarIntMap",  "i64_to_u32_map / i64_map / str_to_u32"),
    "LISTVAL_INT_MAP": (_chk_listval_int_map, "ListvalIntMap", "str_to_u32vec"),
    "STR_MAP":         (_chk_str_map,         "StrMap",        "{key: str} object"),
    "TRIPLE_LIST":     (_chk_triple_list,     "TripleList",    "parse_triples"),
    "PAIR_LIST":       (_chk_pair_list,       "PairList",      "startgrants.rs pair parse [[a,b]]"),
    "INT_LIST":        (_chk_int_list,        "IntList",       "arr_i32 / arr_u32"),
    "STR_LIST":        (_chk_str_list,        "StrList",       "arr_str (item names)"),
    "BOOL":            (_chk_bool,            "Bool",          "as_bool"),
    "BOOL_OR_INT":     (_chk_bool_or_int,     "BoolOrInt",     "parse_death_link / parse_dlc (0/1)"),
    "INT_OR_BOOL":     (_chk_int_or_bool,     "IntOrBool",     "parse_bool_option (nonzero = on)"),
    "INT":             (_chk_int,             "Int",           "as_i64"),
    "NUMBER":          (_chk_number,          "Number",        "as_f64"),
    "STR":             (_chk_str,             "Str",           "as_str"),
    "NESTED_GRANTS":   (_chk_nested_grants,   "NestedGrants",  "progressive.rs custom"),
    "FLASK_LADDER":    (_chk_flask_ladder,    "FlaskLadder",   "progressive.rs flask reconcile"),
    "OPTIONS_DICT":    (_chk_options_dict,    "OptionsDict",   "options::parse_*_option sub-dict"),
    "ANY":             (_chk_any,             "Any",           "(diagnostic / foreign profile; unvalidated)"),
}

GREENFIELD, BEDROCK, BOTH = "greenfield", "bedrock", "both"


# ---------------------------------------------------------------------------------------------------
# SHARED DERIVED-DATA (single source of truth so the apworld and client CAN'T drift). The PROGRESSION
# SURFACE = the LOCATION_TAGS classes this world's own progression may occupy. ONE definition, both
# sides. (`BIG_TICKET_TYPES` / `is_big_ticket` are RETIRED -- test_gf_progression_surface_contract
# asserts the contract no longer carries them. The name is gone too: it is what let a SECOND selection
# masquerade as a second mechanism.) ONE definition, both sides:
# features/curated_fill.py routes region Locks onto these, and the client's F6 tracker highlights /
# filters them -- via tools/gen_location_regions.py, which imports THIS set to bake the
# er_logic::tracker_regions LOCATION_META on_surface column. So "where the locks go" == "what the
# tracker flags" by construction. Per-location membership is generated from location_tags.py (a
# seed-invariant ~4k-row static table, not slot_data); the DEFINITION lives here in the contract.
# Class vocabulary shared with important_locations (features/important_locations.py imports this).
# (There is no `big_ticket_locations` option; the surface is selected by ProgressionSurface.)
# "EniaShop" is INTERNAL (gen_data tags the remembrance store) and is never user-selectable.
IMPORTANT_LOCATION_TYPES = ["Remembrance", "Seedtree", "Church", "Boss", "Fragment", "Revered",
                            "Basin", "Shop", "ShopNonSpell", "ShopSlot", "Legendary", "GreatRune",
                            "KeyItem", "MajorBoss"]
# ShopNonSpell = every Shop check EXCEPT those sold by a dedicated spell vendor (a ShopLineupParam
# 100-block whose stock is >=50% sorceries/incantations -- measured, not curated, so a general
# merchant who happens to stock a spell stays in). 395 of the 479 shop checks. NOT in the default
# progression surface: shops remain randomized checks, they are just not eligible to HOLD progression
# (479 of them would make ~70% of the surface a merchant). See defaults.FROZEN_OPTIONS.
# ShopSlot = at most ONE row per MERCHANT (the ShopLineupParam 100-block), spell vendors excluded.
# matt's model: a merchant enters the pool ONCE, so however big their stock, they can hold at most ONE
# progression item and cannot dominate by breadth. The pinned row is a MERCHANT-UNIQUE ware -- sold
# under exactly one stock flag game-wide, so "go buy X" names exactly one merchant -- that is also
# start-stocked (release_flag == 0) and region-confident (not DEFAULTED). Merchants with no such row
# are SKIPPED, loudly, at regen (location_tags.SHOP_SLOT_PINS / SHOP_SLOT_SKIPS carry the pins and the
# per-block skip reasons). Prefer this over ShopNonSpell if shops are ever put in the progression
# surface.
# MajorBoss = the ~24 REGION_BOSSES (method=boss_arena remembrance/great-rune arena bosses) UNION a
# curated MAJOR_BOSS_EXTRAS set of hand-picked field/evergaol/dragon bosses that cover the otherwise
# major-less regions (gen_data.py). These are the highest-confidence physical locations (boss-arena /
# boss-defeat flags the client already ships as bossLocations), so the v0.2 progression_surface
# restriction confines this world's own progression (region Locks + required/gate runes + legacy keys)
# to them by default. MajorBoss is a SUBSET of Remembrance/GreatRune (for the boss_arena majors) plus
# Boss/Legendary (for the extras); it is its own tag so the surface can target JUST the majors.
# BIG-TICKET IS RETIRED (2026-07-12, Alaric). It was a SECOND list claiming to define "the important
# checks", and it disagreed with the first: the progression surface (important_locations) is
# {Remembrance, Seedtree, Church, Boss, Fragment, Revered}, while big-ticket targeted {MajorBoss,
# Remembrance, GreatRune}. Their intersection was Remembrance ALONE -- so the client's tracker starred
# MajorBoss/GreatRune checks that progression_surface FORBIDS progression from ever reaching. The
# tracker pointed the player at checks the locks could not be on, by construction, and nothing noticed
# because the two lists had no contract with each other. It surfaced only when a human read a spoiler
# and asked why killing Malenia paid out a Smithing Stone [4].
#
# ONE definition now: the surface. The client is fed it directly (progressionSurfaceLocations), so
# "where the locks may be" and "what the tracker stars" are the same expression, not two lists that
# happen to agree. (Same disease as the three-pass filler tail -- see features/filler_budget.)
#
# EXCLUDE tags survive: a location carrying one is never on the surface. EniaShop = Enia's remembrance
# store (a shop slot holding a rarity-3 item) -- buy-only, so no region Lock and no tracker star even
# when Shop or Legendary is selected.
SURFACE_EXCLUDE_TAGS = frozenset({"EniaShop"})

# The DEFAULT progression surface. It lives HERE, beside has_class, because it has two consumers that
# cannot import each other:
#   * features/progression_surface.ProgressionSurface.default -- the AP option (needs the AP env)
#   * tools/gen_location_regions.py                           -- the tracker's static column (AP-FREE)
# Retiring `is_big_ticket` (20bc529) renamed the predicate but left the SELECTION inlined in the option
# class, where the AP-free generator could not reach it. So the generator kept calling the old name and
# the Windows build died at the tracker-table step. Single-sourcing a predicate is only half the job:
# the SELECTION it is applied to must be single-source too, or the second caller re-invents it.
SURFACE_DEFAULT_CLASSES = frozenset({
    "KeyItem", "MajorBoss", "Remembrance", "GreatRune",
    "Church", "Seedtree", "Fragment", "Revered", "ShopSlot",
})


def has_class(tags, selected) -> bool:
    """Does this location carry one of `selected` classes (and none of SURFACE_EXCLUDE_TAGS)?

    The single tag predicate, used by features/progression_surface (the surface = where this world's
    own progression may go) and features/important_locations. It used to be called `is_big_ticket`,
    which mis-sold it: it was never a concept, just "tags intersect a selection" -- and that name let a
    SECOND selection masquerade as a second mechanism.
    """
    t = set(tags or ())
    return bool(set(selected) & t) and not (SURFACE_EXCLUDE_TAGS & t)


class ContractKey:
    __slots__ = ("name", "shape", "required", "profiles", "producer", "consumer", "doc", "subkeys")

    def __init__(self, name, shape, required, profiles, producer, consumer, doc, subkeys=()):
        assert shape in SHAPES, f"unknown shape {shape} for {name}"
        self.name = name
        self.shape = shape
        self.required = required          # required WITHIN this key's profiles (profile-aware)
        self.profiles = profiles          # tuple of GREENFIELD/BEDROCK (or BOTH)
        self.producer = producer          # apworld module that emits it ("(bedrock apworld)" if N/A)
        self.consumer = consumer          # client file:fn that reads it
        self.doc = doc
        self.subkeys = tuple(subkeys)     # nested ContractKeys (only the `options` sub-dict today)

    def in_profile(self, profile):
        return BOTH in self.profiles or profile in self.profiles


# ---------------------------------------------------------------------------------------------------
# THE `options` SUB-DICT (F1 fix). The client's runtime-option parsers all read
# slot_data["options"][<name>] (er-logic/src/options.rs::parse_bool_option and friends). Every
# sub-key is emitted CENTRALLY by core._options_echo -- features never write into `options`.
# ---------------------------------------------------------------------------------------------------
OPTIONS_SUBKEYS = (
    ContractKey("death_link", "BOOL_OR_INT", True, (GREENFIELD,),
                "core._options_echo", "er-logic/options.rs parse_death_link",
                "shared deaths across the multiworld (world.options.death_link)."),
    ContractKey("enable_dlc", "BOOL_OR_INT", True, (GREENFIELD,),
                "core._options_echo", "er-logic/options.rs parse_dlc",
                "RESOLVED DLC bool (dlc_only implies on); gates DLC map-reveal flags."),
    ContractKey("no_weapon_requirements", "BOOL_OR_INT", True, (GREENFIELD,),
                "core._options_echo", "no_weapon_reqs.rs set_enabled",
                "zero weapon/shield/catalyst + spell stat requirements."),
    ContractKey("completion_scaling", "INT_OR_BOOL", True, (GREENFIELD,),
                "core._options_echo", "er-logic/scaling.rs:146 parse_bool_option",
                "completion scaling on/off + curve id (nonzero = on; 4 = smoothstep)."),
    ContractKey("completion_scaling_floor", "NUMBER", True, (GREENFIELD,),
                "core._options_echo", "er-logic/scaling.rs floor (client reads f64)",
                "minimum scaling tier as percent of max, applied from the start."),
    ContractKey("global_scadutree_blessing", "INT", True, (GREENFIELD,),
                "core._options_echo", "scaling.rs scadutree scope",
                "DLC Scadutree blessing scope Choice value (0 off / 1 player_only / 2 scaled)."),
    ContractKey("auto_upgrade", "INT", True, (GREENFIELD,),
                "core._options_echo (features/upgrades.py)", "upgrades.rs set_auto_upgrade / apply_auto_upgrade",
                "auto-upgrade received weapons: 0 = off; nonzero = raise each received weapon to the "
                "player's highest held level on its smithing track (raise-only, cap +25 normal / +10 somber)."),
    ContractKey("flatten_regular_upgrades", "INT", True, (GREENFIELD,),
                "core._options_echo (features/upgrades.py)", "upgrades client path",
                "standard-weapon stones/level: 0 = off (vanilla 2/4/6), 1..4 = uniform N/level (tuned ~3)."),
)


# ---------------------------------------------------------------------------------------------------
# THE CONTRACT. Order = logical grouping. `required` applies within the key's own profiles.
# ---------------------------------------------------------------------------------------------------
CONTRACT = (
    # --- received-item + location detection (core) ---
    ContractKey("apIdsToItemIds", "SCALAR_INT_MAP", True, (BOTH,),
                "core._base_slot_data", "core.rs:309 i64_map",
                "AP item id (str) -> ER FullID granted on receipt."),
    # GREENFIELD-only and REQUIRED there. NOT required of a foreign apworld: Bedrock emits
    # `locationIdsToKeys` (matt slot keys) instead, and key_resolver.rs derives the flag from token 1
    # of the key. core.rs prefers the derived table and falls back to this one. Requiring BOTH of a
    # foreign world would demand a key it does not have and cannot be asked to add.
    ContractKey("locationFlags", "SCALAR_INT_MAP", True, (GREENFIELD,),
                "core._base_slot_data", "core.rs:517 (key_resolver first, this as fallback)",
                "AP location id (str) -> its ER acquisition event flag; the flag-poll detection table."),
    # GREENFIELD-only. A foreign apworld has NO region lock (Bedrock's is an unbuilt wishlist), and
    # we told him in writing: "when these arguments aren't present, they fall back to vanilla
    # behaviour". Absent => no locks, every region open. Guarded by the foreign_apworld_degrade tests
    # in region.rs. Making this BOTH+required contradicted that promise for months.
    ContractKey("regionOpenFlags", "SCALAR_INT_MAP", True, (GREENFIELD,),
                "core._base_slot_data", "region.rs:111 str_to_u32 (absent => empty => no locks)",
                "'<Region> Lock' -> the region-open event flag set when that lock is received. Keys "
                "MUST be exactly '<Region> Lock' matching the client's COARSE_LOCK_ITEMS names."),
    # --- runtime options echo (F1 fix; the client reads options ONLY through this sub-dict) ---
    ContractKey("options", "OPTIONS_DICT", True, (GREENFIELD,),
                "core._options_echo", "er-logic/options.rs parse_bool_option et al.",
                "runtime option echo sub-dict; every client-read option lives here (features' "
                "top-level copies are legacy duplicates the client ignores).",
                subkeys=OPTIONS_SUBKEYS),
    # --- completion scaling (I2 emits the live values) ---
    ContractKey("regionSphereTargets", "SCALAR_INT_MAP", False, (GREENFIELD,),
                "features/scaling.py (I2; core emits {} transitional)", "er-logic/scaling.rs:148 i32_i32_map",
                "{str(i32 region id): i32 target}; flat per-region scaling targets. Keys must parse "
                "as i32 (region NAMES are silently dropped by the client -- the 2026-07 dark-scaling "
                "bug); ranges (regionSphereTargetRanges) are the live wire."),
    ContractKey("regionSphereTargetRanges", "TRIPLE_LIST", False, (GREENFIELD,),
                "features/scaling.py (I2)", "er-logic/scaling.rs:150-165 range parse",
                "[[lo,hi,target], ...] play_region/100 sub-id ranges -> scaling target; the live "
                "completion-scaling wire (SCALING_WIRE)."),
    ContractKey("dlcScadutreeFloorRanges", "TRIPLE_LIST", False, (GREENFIELD,),
                "features/scaling.py", "eldenring-archipelago/upgrades.rs floor_for_region (mode 2)",
                "[[lo,hi,floor], ...] play_region/100 sub-id ranges -> Scadutree-blessing FLOOR level "
                "(0..20) per DLC region. Emitted ONLY when global_scadutree_blessing==2 and >=1 DLC "
                "region is kept. Client mode-2 writes max(held-fragment level, region floor) so DLC "
                "enemies' blessing assumption is met on arrival; the enemy 70xx sphere scaler is capped "
                "in these buckets to avoid double-counting."),
    ContractKey("completionScalingBasis", "INT", False, (GREENFIELD,),
                "core._base_slot_data", "er-logic/scaling.rs basis parse",
                "scaling basis Choice VALUE (int 1 = sphere); client also tolerates the legacy "
                "string form ('sphere')."),
    # --- region locking / kick-watch ---
    ContractKey("areaLockFlags", "TRIPLE_LIST", False, (BOTH,),
                "(client-derived; folded into regionOpenFlags 2026-07-06)",
                "region.rs derive_area_lock_flags",
                "[lo,hi,open_flag] play_region ranges; locked (kicked) while open_flag is unset. "
                "FOLDED 2026-07-06: no longer emitted -- the client derives these from regionOpenFlags "
                "+ its static REGION_PLAY_IDS geometry (area_locks.py holds the mirror authority + a "
                "kept-region coverage assert; test_gf_data.py guards table drift). A legacy seed that "
                "still sends a non-empty areaLockFlags is honored by the client as-is."),
    ContractKey("lockRevealFlags", "LISTVAL_INT_MAP", False, (BOTH,),
                "(unemitted today; client path LIVE)", "region.rs:121 str_to_u32vec",
                "'<Region> Lock' -> map-reveal/enforcement flags set on lock receipt. The client "
                "consumer is LIVE (region.rs:121); greenfield does not emit it yet."),
    # --- capital-version reconciler (SPEC-capital-reconciler.md; features/capital.py) ---
    # All five travel together, emitted only while `capital_reconciler` is ON -- absent keys are
    # the off-wire (the client logs "capital reconciler INERT" and never touches 9116).
    ContractKey("capitalBurnFlag", "INT", False, (GREENFIELD,),
                "features/capital.py", "region.rs configure_capital / tick_capital",
                "the Leyndell map-version selector, 9116 (OFF = Royal m11_00, ON = Ashen m11_05 "
                "+ Elden Throne m19). The client reconciles it to the player's current/target "
                "capital so the burn never permanently strands the Royal checks."),
    ContractKey("capitalBurnDoneFlag", "INT", False, (GREENFIELD,),
                "features/capital.py", "region.rs configure_capital / tick_capital",
                "the burn-complete latch, 118 (common.emevd $Event(900)'s last step; monotonic). "
                "ARMING GATE: the client never writes 9116 while this reads unset -- the first "
                "burn is 100% the game's own sequence."),
    ContractKey("capitalAshenPlayRegions", "INT_LIST", False, (GREENFIELD,),
                "features/capital.py", "er-logic capital.rs via region.rs tick_capital",
                "measured play_region buckets where 9116 must be held ON (11050 Ashen Capital, "
                "19000 Elden Throne). KICK id space, same /100 reduction as kick_decision."),
    ContractKey("capitalRoyalPlayRegions", "INT_LIST", False, (GREENFIELD,),
                "features/capital.py", "er-logic capital.rs via region.rs tick_capital",
                "measured play_region buckets where 9116 must be held OFF (11000 Royal Capital)."),
    ContractKey("capitalReleaseRows", "TRIPLE_LIST", False, (GREENFIELD,),
                "features/capital.py", "shop_flags.rs run_capital_release",
                "[ShopLineupParam row, expected release flag, replacement] -- shop-check rows "
                "whose eventFlag_forRelease is 9116 itself (Enia's Maliketh armor set) re-key to "
                "the monotonic 118 so the reconciler's OFF-default cannot de-stock them."),
    # --- graces ---
    ContractKey("regionGraces", "LISTVAL_INT_MAP", False, (BOTH,),
                "features/graces.py", "region.rs:122 str_to_u32vec",
                "item_name -> grace warp flags lit when that item is RECEIVED. Keyed by "
                "'<Region> Lock' (bundle: all of the region's graces). A GATED CHILD region "
                "(region_spine.REGION_PARENT -- Raya Lucaria Academy, Leyndell, Sewer) maps to [] "
                "while its vanilla wall is armed in logic: its graces are deliberately NOT granted "
                "(the player walks in past the game's own wall and touches them; gated-children "
                "fix 2026-07-14). Client MUST light on receipt of ANY keyed item, not just Locks, "
                "and MUST treat an empty bundle as intent, not drift."),
    ContractKey("runeGatedGraces", "LISTVAL_INT_MAP", False, (GREENFIELD,),
                "CONTRACT: DEAD (unemitted since 2026-07-14)", "CONTRACT: DEAD (never built)",
                "RETIRED 2026-07-14 (gated-children fix). Was: str(N) -> capital grace flags lit at "
                ">= N received Great Runes. The client half was NEVER built (the key appears in "
                "contract_gen.rs and in no consumer over the client repo's full history), so armed "
                "it could light nothing and disarmed the capital bundle rode the Leyndell Lock past "
                "the 2-rune wall (playtest 2026-07-14, East Capital Rampart 71102). Superseded by "
                "withholding a gated child's bundle outright -- the GAME's own wall is the gate "
                "(features/graces.py). Key kept declared so an old client's parse stays defined."),
    ContractKey("greatRuneItemIds", "INT_LIST", False, (GREENFIELD,),
                "CONTRACT: DEAD (unemitted since 2026-07-14)", "CONTRACT: DEAD (never built)",
                "RETIRED 2026-07-14 with runeGatedGraces (its only reason to exist). The client "
                "counts received runes for the GOAL via great_rune_items instead."),
    # --- start-of-run grants ---
    # GREENFIELD-only: absent => vanilla start (Limgrave; Gravesite under dlc_only). core.rs:716
    # already does `.unwrap_or("")`. Same promise as regionOpenFlags.
    ContractKey("startRegion", "STR", True, (GREENFIELD,),
                "features/start_grace.py", "core.rs:410 as_str",
                "name of the always-kept start region (diagnostic + start anchor)."),
    ContractKey("startGraces", "INT_LIST", False, (BOTH,),
                "features/start_grace.py", "startgrants.rs:58 arr_u32",
                "grace flags lit at spawn so the first warp is possible (front-door of start region)."),
    ContractKey("startItems", "INT_LIST", False, (BOTH,),
                "features/start_items.py", "startgrants.rs:57 arr_i32",
                "FullIDs granted once at game start, REPEATED path -- a duplicate is harmless "
                "(Torch, pot vessels). Unique key items ride uniqueStartGrants instead."),
    ContractKey("uniqueStartGrants", "PAIR_LIST", False, (GREENFIELD,),
                "features/start_items.py", "core.rs unique-grant path (startgrants.rs parse)",
                "[FullID, obtainedFlag] pairs for flag-idempotent UNIQUE start grants (whistle "
                "60100, bell 60110, physick 60020). The client grants the goods ONLY if the flag "
                "is unset, then sets the flag with the grant (er_logic::unique_grants) -- the flag "
                "is the single source of truth for 'has it', so reload/reconnect/pool-pickup can "
                "never double-grant."),
    ContractKey("reveal_all_maps", "BOOL", False, (BOTH,),
                "features/start_grace.py", "startgrants.rs as_bool",
                "reveal the whole world map + underground view (client owns the RE'd flag set)."),
    # --- goal ---
    ContractKey("progressionSurfaceLocations", "INT_LIST", False, (GREENFIELD,),
                "features/progression_surface.py",
                "core.rs tracker star/lock set",
                "AP location ids on THIS seed's progression surface -- the ONLY locations that may "
                "hold this world's own progression (region Locks, required/gate Great Runes, folded "
                "legacy keys). Enia (EniaShop) always excluded. The client stars exactly these, so "
                "'where the locks can be' and 'what the tracker points at' are ONE set. REPLACES "
                "bigTicketLocations, which named a set progression could never reach (MajorBoss and "
                "GreatRune are not on the surface)."),
    ContractKey("goalLocations", "INT_LIST", True, (BOTH,),
                "features/goal_locations.py", "goal.rs parse",
                "AP location ids whose completion == victory; client sends Goal when all are done."),

    # --- vanilla suppression + shops ---
    ContractKey("checkItemFlags", "LISTVAL_INT_MAP", False, (BOTH,),
                "features/check_item_flags.py", "detour.rs CHECK_ITEM_FLAGS<u32,Vec<u32>>",
                "vanilla FullID (str) -> the check flags it belongs to; suppresses the vanilla bag-add."),
    ContractKey("shopRowFlags", "SCALAR_INT_MAP", False, (BOTH,),
                "features/shops.py", "core.rs:359 i64_to_u32_map",
                "ShopLineupParam row id -> eventFlag_forStock written for shop checks."),
    ContractKey("checkLotBlankMap", "LISTVAL_INT_MAP", False, (GREENFIELD,),
                "features/check_lots.py", "check_lots.rs (ItemLotParam_map)",
                "ItemLotParam_MAP lot id -> the GOODS slot indices holding a check's vanilla ware."),
    ContractKey("checkLotBlankEnemy", "LISTVAL_INT_MAP", False, (GREENFIELD,),
                "features/check_lots.py", "check_lots.rs (ItemLotParam_enemy)",
                "Same, for ItemLotParam_ENEMY (boss / enemy one-time drops). SEPARATE on purpose: the "
                "two tables can hold the SAME row id, so a merged dict loses the table and forces the "
                "client to GUESS. It guessed map-first, so every enemy lot colliding with a map id was "
                "never blanked -- a boss that is 'just an enemy' handed out its vanilla drop and fired "
                "no check (playtest 2026-07-12: Unsightly Catacombs duo, enemy lot 30120, while all "
                "five of that map's TREASURE checks randomised correctly)."),
    ContractKey("checkLotBlank", "LISTVAL_INT_MAP", False, (GREENFIELD,),
                "features/check_lots.py", "check_lots.rs configure/run",
                "ItemLotParam lot id (str) -> [goods slot indices] holding a CHECK's vanilla ware. The "
                "client repoints those slots at apPlaceholderGoods so the vanilla ware is never handed "
                "out at a check -- while farmed/mined/bought/crafted copies are left alone."),
    ContractKey("apPlaceholderGoods", "INT", False, (GREENFIELD,),
                "features/check_lots.py", "check_lots.rs / detour.rs unconditional suppress",
                "A spare EquipParamGoods row (8852): exists so the game can grant it, no FMG name, "
                "referenced by no lot/shop/recipe. Suppressed unconditionally -- it is never a real "
                "item, so it can never eat anything legitimate. ONE row suffices because checks are "
                "detected by the FLAG POLL, not by the item id (no synthetic id per location)."),
    ContractKey("enemyDropRoll", "LISTVAL_INT_MAP", False, (GREENFIELD,),
                "features/enemy_drops.py", "enemy_drops.rs configure/run",
                "ItemLotParam_enemy lot id (str) -> FLAT pairs [slot, goodsId, slot, goodsId, ...]. "
                "UNFLAGGED lots only "
                "(a lot with getItemFlagId > 0 IS a check and is never sent). Only GOODS slots are "
                "rerolled; lotItemBasePoint (drop weight) is untouched, so drop RATES stay vanilla."),
    ContractKey("shopInfiniteStock", "LISTVAL_INT_MAP", False, (GREENFIELD,),
                "features/shop_stock.py", "shop_stock.rs configure/run",
                "ShopLineupParam row id (str) -> [goodsId, equipType, price]. The 455 UNLIMITED rows "
                "carry no stock flag so they can never be checks; rerolled per seed to a consumable. "
                "The PRICE rides along because those rows inherit the old ware's cost (gem slots = 1 "
                "rune, 166 armor slots free) -- without it every seed is a free-consumable dispenser."),
    ContractKey("shopPreviewGoods", "SCALAR_INT_MAP", False, (BOTH,),
                "features/shops.py", "core.rs:353 i64_map",
                "AP location id -> preview goods id shown in the shop slot."),
    ContractKey("stoneswordVendorRow", "INT", False, (GREENFIELD,),
                "features/minibaker.py", "minibaker.rs configure/run",
                "MINI-BAKER: reserved ShopLineupParam row id the client repurposes into an infinite, "
                "always-in-stock Stonesword Key vendor (equipId 8000, sellQuantity -1) so imp-statue "
                "checks are never missable. 0/absent = off (row left vanilla). Reserved row is excluded "
                "from shop checks in gen_data. See memory er-minibaker-shoplineup."),
    # --- sweeps / progressive / deathlink / dlc ---
    ContractKey("dungeonSweepFlags", "LISTVAL_INT_MAP", False, (BOTH,),
                "features/boss_sweeps (P3b client patch)", "region.rs:104 as_object",
                "dungeon trigger flag (str) -> the member AP location ids auto-registered on clear."),
    ContractKey("dungeonSweeps", "ANY", False, (BOTH,),
                "features/boss_locks.py ({} today; location-keyed variant)", "region.rs",
                "location-keyed dungeon sweep spec (needs boss-reward-location join); greenfield "
                "emits {} until wired -- flag-keyed dungeonSweepFlags is the live path."),
    ContractKey("sweepLockGates", "STR_MAP", False, (BOTH,),
                "features/boss_locks.py ({} today)", "region.rs sweep gates",
                "{str(i64 sweep trigger flag): '<Region> Lock'} -- gates a dungeon sweep behind "
                "holding the named lock; live client consumer."),
    ContractKey("progressiveGrants", "NESTED_GRANTS", False, (BOTH,),
                "features/progressive.py", "progressive.rs",
                "item name -> ordered [{goods, flags, consumed}] granted on each successive receipt. "
                "`consumed` (REQUIRED bool): true = the player SPENDS these goods, so grant them "
                "exactly once via the ledger; false = the player KEEPS them, so self-heal them "
                "(unique_goods). A consumable shipped as kept is re-granted every time it is "
                "spent -- unbounded flask upgrades, then a CTD (playtest 2026-07-12)."),
    ContractKey("flaskLadder", "FLASK_LADDER", False, (GREENFIELD,),
                "features/progressive.py", "progressive.rs / flask reconcile",
                "ordered cumulative flask target list; entry i (0-based) = {charges 2..14, potency "
                "0..12} for the flask after receiving (i+1) Progressive Flask Upgrade copies. The "
                "client RECONCILES the CHARGE target directly (a leveled state); POTENCY here is "
                "documentation -- the client sets potency from the consumed Sacred Tears the same item "
                "grants via progressiveGrants (one tear per copy). Charges monotonic non-decreasing, "
                "reaching 14 at the last rung; potency = min(rung,12); length == the PROG_FLASK copies "
                "this seed has (substituted Golden Seed / Sacred Tear checks kept, or a fixed 12 "
                "injected when none are kept -- dlc_only). The flask is a HYBRID riding BOTH wires "
                "(charges here, potency in progressiveGrants) -- intentional and non-overlapping. The "
                "charge axis is a leveled state (no spend to heal); the potency axis went back to "
                "granted/ledgered Sacred Tears because the in-place potency item-id swap CTD'd on death "
                "against ER's flask mirrors (playtest 2026-07-19). Emitted only when progressive_flasks "
                "is on."),
    ContractKey("death_link", "BOOL_OR_INT", False, (BOTH,),
                "features/deathlink.py (legacy duplicate of options.death_link)",
                "er-logic/options.rs parse_death_link (reads options.death_link)",
                "legacy top-level copy; the client reads options.death_link -- kept for back-compat."),
    ContractKey("no_weapon_requirements", "BOOL_OR_INT", False, (BOTH,),
                "features/weapon_reqs.py (legacy duplicate of options.no_weapon_requirements)",
                "core.rs:304 no_weapon_reqs::set_enabled (reads options path)",
                "legacy top-level copy; the client reads options.no_weapon_requirements."),
    ContractKey("enable_dlc", "BOOL_OR_INT", False, (BOTH,),
                "core._options_echo (options.enable_dlc; top-level unemitted)",
                "er-logic/options.rs parse_dlc (reads options.enable_dlc)",
                "DLC / Land of Shadow regions active; the LIVE copy is options.enable_dlc."),
    ContractKey("completion_scaling", "INT_OR_BOOL", False, (GREENFIELD,),
                "features/scaling.py (legacy duplicate of options.completion_scaling)",
                "er-logic/scaling.rs:146 (reads options.completion_scaling)",
                "legacy top-level copy of the scaling toggle/curve id (4 = smoothstep)."),
    ContractKey("completion_scaling_floor", "NUMBER", False, (GREENFIELD,),
                "features/scaling.py (legacy duplicate of options.completion_scaling_floor)",
                "(client reads options.completion_scaling_floor)",
                "legacy top-level copy of the scaling floor percent."),
    ContractKey("global_scadutree_blessing", "INT", False, (GREENFIELD,),
                "features/scaling.py (legacy duplicate of options.global_scadutree_blessing)",
                "(client reads options.global_scadutree_blessing)",
                "legacy top-level copy of the Scadutree blessing scope."),
    # --- version handshake ---
    # GREENFIELD-only: core.rs logs a warning and continues when a foreign apworld sends no
    # `versions` ("it predates the version handshake"). Requiring it of everyone was a lie.
    ContractKey("versions", "STR", True, (GREENFIELD,),
                "core._base_slot_data", "eldenring-archipelago core.rs version gate",
                "VERSION HANDSHAKE. 'apworld/<semver> contract/<hash8> data/<inputs_hash16>'. The "
                "client compares the contract hash to the one it was COMPILED against and shouts if "
                "they differ. Required, because the failure it catches is silent: apworld and client "
                "ship as two separate artifacts (apworld off-site, .dll on Nexus), so mixed versions "
                "are not an edge case, they are the norm -- and a stale .dll against a fresh apworld "
                "looks exactly like a bug in the game. Every report carries this string."),
    # --- greenfield diagnostics (no client read; ANY = shape-unvalidated on purpose) ---
    ContractKey("world_logic", "STR", False, (GREENFIELD,),
                "core._base_slot_data", "(diagnostic -- no client read)",
                "logic profile tag, e.g. 'region_lock'."),
    ContractKey("region_count", "ANY", False, (GREENFIELD,),
                "core._base_slot_data", "(diagnostic -- no client read)",
                "len(kept) -- how many regions are in play this seed."),
    ContractKey("ending_condition", "ANY", False, (GREENFIELD,),
                "core._base_slot_data", "(diagnostic -- no client read)",
                "resolved goal tag: 'region_locks' | 'great_runes'."),
    ContractKey("great_runes_required", "ANY", False, (GREENFIELD,),
                "core._base_slot_data", "(diagnostic -- no client read)",
                "EFFECTIVE (clamped) Great Rune requirement for the great_runes ending."),
    ContractKey("great_rune_items", "STR_LIST", False, (GREENFIELD,),
                "core._base_slot_data", "goal.rs parse",
                "Item NAMES the player must HOLD before Goal can fire (the great_runes ending). WAS a "
                "diagnostic with no client read, which is exactly how the bug survived: the client's "
                "goal was the LOCATION of each rune's boss drop -- i.e. KILL Godrick -- while AP's "
                "victory rule was state.has(rune). item_shuffle is frozen ON, so the rune is NOT at the "
                "boss: you could kill every rune boss, hold no rune, and the run would end. A kill is "
                "not a collection. The client now READS this key. Absent/empty adds no requirement."),
    ContractKey("bossLocations", "ANY", False, (GREENFIELD,),
                "features/boss_locks.py", "(diagnostic -- no client read)",
                "{region: [boss AP location ids]} for kept regions."),
    ContractKey("bossLockItems", "ANY", False, (GREENFIELD,),
                "features/boss_locks.py", "er-logic boss_felled / region.rs",
                "{str(boss_flag): {name:'Felled: <Boss>', region, boss_ap_id [, gate:'Boss Key: <Boss>'"
                ", display_key:<vanilla key name>]}}: kept BASE-game bosses always; DLC bosses added "
                "when boss_keys is ON. Client mints the 'Felled:' trophy on boss-defeat (mode A); the "
                "mode-B 'gate' (defer own check until key) and 'display_key' (legible vanilla lock name) "
                "ride the same entry when boss_keys is ON."),
    ContractKey("filler_foreign_localized", "ANY", False, (GREENFIELD,),
                "features/filler_foreign.py", "(diagnostic -- no client read)",
                "count of distinct filler names forced local this seed."),
    ContractKey("pool_builder", "ANY", False, (GREENFIELD,),
                "features/pool_builder.py", "(diagnostic -- no client read)",
                "whether pool curation was enabled this seed."),
    ContractKey("pool_builder_juice_added", "ANY", False, (GREENFIELD,),
                "features/pool_builder.py", "(diagnostic -- no client read)",
                "resolved juice budget added by the pool builder."),
    ContractKey("pool_builder_intensity_floor", "ANY", False, (GREENFIELD,),
                "features/pool_builder.py", "(diagnostic -- no client read)",
                "resolved juice rarity floor (1..3)."),
    ContractKey("pool_builder_juice_candidates", "ANY", False, (GREENFIELD,),
                "features/pool_builder.py", "(diagnostic -- no client read)",
                "size of the juice candidate set at this intensity."),
    ContractKey("pool_builder_juice_pct", "ANY", False, (GREENFIELD,),
                "features/pool_builder.py", "(diagnostic -- no client read)",
                "resolved share (0..100) of the Rune tail replaced with juice."),
    # --- bedrock-profile keys (client reads; greenfield does NOT emit) ---
    # ALL OPTIONAL (2026-07-12). These were marked required=True as the "swap target" -- a
    # description of what a bedrock-compatible seed WOULD send. It was never observed: his real
    # apworld (fswap/archipelago@er) emits apIdsToItemIds + locationIdsToKeys + goal, and NONE
    # of naturalKeyTriggers / lockGrantItems / randomStart* / fogWalls -- those are OUR runtime
    # features, not his. Nothing ever validated profile="bedrock", so the fiction survived.
    # `required` now means what it says: THE CLIENT CANNOT FUNCTION WITHOUT IT. It functions
    # without every one of these (each parse degrades to a vanilla default; region.rs and
    # fogwall.rs have foreign_apworld_degrade tests proving it).
    ContractKey("locationIdsToKeys", "ANY", True, (BEDROCK,),
                "(bedrock apworld)", "key_resolver.rs",
                "matt slot key token per location; client resolves token1 -> flag (bedrock path)."),
    ContractKey("itemCounts", "ANY", False, (BOTH,),
                "core._base_slot_data (greenfield) / bedrock apworld", "core.rs receive.rs itemCounts",
                "per-item quantity map {str(ap_item_id): qty}; client grants full_id x qty. Greenfield "
                "emits stack sizes for throwables (x10) and finished pots (x4) (features/filler_curation)."),
    ContractKey("naturalKeyTriggers", "ANY", False, (BEDROCK,),
                "(bedrock apworld)", "key_resolver.rs / region.rs",
                "bedrock natural key triggers."),
    ContractKey("lockGrantItems", "ANY", False, (BEDROCK,),
                "(bedrock apworld)", "region.rs",
                "items granted on a region lock receipt (bedrock)."),
    ContractKey("randomStartDoneFlag", "ANY", False, (BEDROCK,),
                "(bedrock apworld)", "random start client path",
                "bedrock random-start: flag set when the start warp completed."),
    ContractKey("randomStartWarpFlag", "ANY", False, (BEDROCK,),
                "(bedrock apworld)", "random start client path",
                "bedrock random-start: flag that triggers the start warp."),
    ContractKey("randomStartAreaId", "ANY", False, (BEDROCK,),
                "(bedrock apworld)", "random start client path",
                "bedrock random-start: destination area id."),
    ContractKey("randomStartGraceId", "ANY", False, (BEDROCK,),
                "(bedrock apworld)", "random start client path",
                "bedrock random-start: destination grace id."),
    ContractKey("fogWalls", "ANY", False, (BEDROCK,),
                "(bedrock apworld)", "fog wall client path",
                "bedrock fog-wall spec."),
    ContractKey("fogWallDebug", "ANY", False, (BEDROCK,),
                "(bedrock apworld)", "fog wall client path",
                "bedrock fog-wall debug toggle."),
)

BY_NAME = {k.name: k for k in CONTRACT}
OPTIONS_BY_NAME = {k.name: k for k in OPTIONS_SUBKEYS}

# Module-level name constants (UPPER_SNAKE = "wireName") so emitters never hard-code a string literal.
# OPTIONS_SUBKEYS are included (same-named top-level legacy keys resolve to the identical string).
import re as _re
_g = globals()
for _k in CONTRACT + OPTIONS_SUBKEYS:
    _const = _re.sub(r"(?<!^)(?=[A-Z])", "_", _k.name).upper().replace("__", "_")
    _g[_const] = _k.name
# (e.g. LOCATION_FLAGS = "locationFlags", AREA_LOCK_FLAGS = "areaLockFlags", DEATH_LINK = "death_link")


class ContractError(Exception):
    pass


def validate_slot_data(sd, profile=GREENFIELD, strict=True):
    """Check an assembled slot_data dict against the contract. Returns a list of problem strings.
    With strict=True, raises ContractError on any problem. Checks are PROFILE-AWARE: only keys
    belonging to `profile` are required/shape-checked (bedrock keys are never required for a
    greenfield gen). Three checks per profile key: MISSING (required only), SHAPE, and -- for keys
    with subkeys (the `options` echo) -- the same two per declared sub-key plus UNDECLARED sub-key
    rejection. Finally (F2 fix) any emitted TOP-LEVEL key not declared in the contract AT ALL is
    rejected: an undeclared emission is exactly how features go silently dark, so it fails at gen."""
    problems = []
    for key in CONTRACT:
        if not key.in_profile(profile):
            continue
        if key.name not in sd:
            if key.required:
                problems.append(f"MISSING required key {key.name!r} (producer {key.producer})")
            continue
        val = sd[key.name]
        err = SHAPES[key.shape][0](val)
        if err:
            problems.append(f"SHAPE {key.name!r} ({key.shape}): {err}")
            continue
        if key.subkeys and isinstance(val, dict):
            declared_sub = {s.name for s in key.subkeys}
            for sub in key.subkeys:
                if not sub.in_profile(profile):
                    continue
                if sub.name not in val:
                    if sub.required:
                        problems.append(f"MISSING required sub-key {key.name}.{sub.name} "
                                        f"(producer {sub.producer})")
                    continue
                serr = SHAPES[sub.shape][0](val[sub.name])
                if serr:
                    problems.append(f"SHAPE {key.name}.{sub.name} ({sub.shape}): {serr}")
            for sname in val:
                if sname not in declared_sub:
                    problems.append(f"UNDECLARED sub-key {key.name}.{sname} -- declare it in "
                                    f"contract.py (OPTIONS_SUBKEYS) before emitting")
    for name in sd:
        if name not in BY_NAME:
            problems.append(f"UNDECLARED key {name!r} emitted -- declare it in contract.py "
                            f"(name/shape/profile/producer) before emitting")
    if strict and problems:
        raise ContractError("slot_data contract violation:\n  " + "\n  ".join(problems))
    return problems


# ---------------------------------------------------------------------------------------------------
# GENERATORS -- docs + language-neutral + Rust mirror (so the client validates the SAME contract).
# ---------------------------------------------------------------------------------------------------
def _key_json(k):
    d = {"name": k.name, "shape": k.shape, "required": k.required,
         "profiles": list(k.profiles), "producer": k.producer,
         "consumer": k.consumer, "doc": k.doc}
    if k.subkeys:
        d["subkeys"] = [_key_json(s) for s in k.subkeys]
    return d


def to_json():
    import json
    return json.dumps({
        "shapes": {n: {"rust": SHAPES[n][1], "client_parser": SHAPES[n][2]} for n in SHAPES},
        "keys": [_key_json(k) for k in CONTRACT],
    }, indent=2)


def to_markdown():
    lines = ["# Greenfield ER apworld <-> client slot_data contract",
             "",
             "AUTO-GENERATED from `eldenring/contract.py` (the single source of truth). Do not edit.",
             "",
             "Sub-keys of the `options` echo are listed as `options.<name>` -- the client reads",
             "runtime options ONLY through that sub-dict (er-logic/src/options.rs).",
             "",
             "| key | shape | req | profile | producer | client consumer | meaning |",
             "|-----|-------|-----|---------|----------|-----------------|---------|"]

    def row(k, prefix=""):
        prof = "both" if BOTH in k.profiles else "+".join(k.profiles)
        req = "yes" if k.required else ""
        lines.append(f"| `{prefix}{k.name}` | {k.shape} | {req} | {prof} | {k.producer} "
                     f"| {k.consumer} | {k.doc} |")

    for k in CONTRACT:
        row(k)
        for s in k.subkeys:
            row(s, prefix=f"{k.name}.")
    lines += ["", "## Shapes", "",
              "| shape | client parser |", "|-------|---------------|"]
    for n in SHAPES:
        lines.append(f"| {n} | `{SHAPES[n][2]}` |")
    return "\n".join(lines) + "\n"


def to_rust():
    """Generate contract_gen.rs: Shape enum, the CONTRACT + OPTIONS_SUBKEYS tables, and a
    validate(sd) fn that mirrors validate_slot_data's missing/shape checks on the client side
    (the client does NOT reject unknown keys -- the server may add its own). Pure data + a small
    fixed validator (serde_json)."""
    variants = sorted({SHAPES[n][1] for n in SHAPES})
    _hdr_version = (
        "\n// ---- VERSION HANDSHAKE ----------------------------------------------------------------\n"
        "// The contract hash this client was COMPILED against. The apworld sends its own in slot_data\n"
        "// `versions` (\"apworld/<semver> contract/<hash8> data/<inputs_hash16>\"). If they differ, the\n"
        "// two artifacts were built from different contracts -- which is the NORM, not an edge case:\n"
        "// the apworld ships off-site and the .dll ships on Nexus, so a player can mix them freely.\n"
        "// Derived from the contract itself (gen_contract.py), so it cannot go stale like a hand-bumped\n"
        "// version number would.\n"
        f'pub const CONTRACT_HASH: &str = "{CONTRACT_HASH[:8]}";\n'
        f'pub const APWORLD_VERSION_EXPECTED: &str = "{APWORLD_VERSION}";\n'
    )

    def key_row(k):
        gf = "true" if (BOTH in k.profiles or GREENFIELD in k.profiles) else "false"
        req = "true" if k.required else "false"
        return (f'    ContractKey {{ name: "{k.name}", shape: Shape::{SHAPES[k.shape][1]}, '
                f"required: {req}, greenfield: {gf} }},")

    L = []
    # The `@generated` marker is LOAD-BEARING: the client's rustfmt.toml sets format_generated_files =
    # false, which keys off exactly this token in the first few lines. Without it `cargo fmt` reformats
    # this file, the next regen emits the unformatted form, and CI fails on a file nobody edited.
    L.append("// @generated -- AUTO-GENERATED from eldenring/contract.py. Do not edit by hand.")
    # NOTE: rustfmt honours `@generated` (the client's rustfmt.toml sets format_generated_files=false)
    # but CLIPPY DOES NOT -- a generated file is linted like any other. So the emitted Rust has to be
    # lint-clean AT THE SOURCE: 12 of the client's 44 clippy errors were `map_or(false, ..)` emitted from
    # right here, and hand-fixing contract_gen.rs would have been silently undone by the next regen.
    L.append("// The apworld<->client slot_data contract, mirrored so the client validates the same shapes.")
    L.append("use serde_json::Value;")
    L.append("")
    L.append("#[derive(Clone, Copy, Debug, PartialEq, Eq)]")
    L.append("pub enum Shape {")
    for v in variants:
        L.append(f"    {v},")
    L.append("}")
    L.append("")
    L.append("pub struct ContractKey {")
    L.append("    pub name: &'static str,")
    L.append("    pub shape: Shape,")
    L.append("    pub required: bool,")
    L.append("    pub greenfield: bool,")
    L.append("}")
    L.append("")
    L.append("pub const CONTRACT: &[ContractKey] = &[")
    for k in CONTRACT:
        L.append(key_row(k))
    L.append("];")
    L.append("")
    L.append("/// Declared sub-keys of the top-level `options` echo (validated when `options` is present).")
    L.append("pub const OPTIONS_SUBKEYS: &[ContractKey] = &[")
    for s in OPTIONS_SUBKEYS:
        L.append(key_row(s))
    L.append("];")
    L.append("")
    L.append(_RUST_VALIDATE)
    L.append(_hdr_version)
    return "\n".join(L) + "\n"


_RUST_VALIDATE = r'''fn is_int(v: &Value) -> bool { v.is_i64() || v.is_u64() }

fn shape_ok(shape: Shape, v: &Value) -> bool {
    match shape {
        Shape::ScalarIntMap => v.as_object().is_some_and(|o| o.values().all(is_int)),
        Shape::ListvalIntMap => v.as_object().is_some_and(|o| {
            o.values().all(|x| x.as_array().is_some_and(|a| a.iter().all(is_int)))
        }),
        Shape::StrMap => v.as_object().is_some_and(|o| o.values().all(|x| x.is_string())),
        Shape::TripleList => v.as_array().is_some_and(|a| {
            a.iter().all(|t| t.as_array().is_some_and(|t| t.len() == 3 && t.iter().all(is_int)))
        }),
        Shape::PairList => v.as_array().is_some_and(|a| {
            a.iter().all(|t| t.as_array().is_some_and(|t| t.len() == 2 && t.iter().all(is_int)))
        }),
        Shape::IntList => v.as_array().is_some_and(|a| a.iter().all(is_int)),
        Shape::StrList => v.as_array().is_some_and(|a| a.iter().all(|x| x.is_string())),
        Shape::Bool => v.is_boolean(),
        Shape::BoolOrInt => v.is_boolean() || v.as_i64().is_some_and(|n| n == 0 || n == 1),
        Shape::IntOrBool => v.is_boolean() || is_int(v),
        Shape::Int => is_int(v),
        Shape::Number => v.is_number(),
        Shape::Str => v.is_string(),
        Shape::NestedGrants => v.as_object().is_some_and(|o| {
            o.values().all(|l| l.as_array().is_some_and(|l| l.iter().all(|e| {
                e.get("goods").is_some_and(is_int)
                    && e.get("flags").and_then(|f| f.as_array())
                        .is_some_and(|f| f.iter().all(is_int))
            })))
        }),
        Shape::FlaskLadder => v.as_array().is_some_and(|a| {
            a.iter().all(|e| e.get("charges").is_some_and(is_int)
                && e.get("potency").is_some_and(is_int))
        }),
        Shape::OptionsDict => v.is_object(),
        Shape::Any => true,
    }
}

/// Validate an assembled slot_data object against the greenfield contract. Returns the list of
/// problems (missing-required + shape mismatches, top-level and `options.*`); empty == clean.
/// Mirrors contract.py's missing/shape checks (unknown-key rejection stays gen-side only).
pub fn validate(sd: &Value) -> Vec<String> {
    let mut out = Vec::new();
    for k in CONTRACT {
        if !k.greenfield { continue; }
        match sd.get(k.name) {
            None => if k.required { out.push(format!("MISSING required key '{}'", k.name)); },
            Some(v) => if !shape_ok(k.shape, v) {
                out.push(format!("SHAPE '{}' expected {:?}", k.name, k.shape));
            },
        }
    }
    if let Some(opts) = sd.get("options").and_then(|v| v.as_object()) {
        for k in OPTIONS_SUBKEYS {
            if !k.greenfield { continue; }
            match opts.get(k.name) {
                None => if k.required { out.push(format!("MISSING required sub-key 'options.{}'", k.name)); },
                Some(v) => if !shape_ok(k.shape, v) {
                    out.push(format!("SHAPE 'options.{}' expected {:?}", k.name, k.shape));
                },
            }
        }
    }
    out
}'''



# ---- VERSION HANDSHAKE -----------------------------------------------------------------------------
# CONTRACT_HASH is derived FROM the contract, not maintained beside it: any key added/removed/reshaped
# or any required-ness flip changes it automatically. A hand-bumped version number is a thing people
# forget; a derived one cannot go stale. (Same doctrine as the gen-input stamp.)
import hashlib as _hashlib

APWORLD_VERSION = "0.2.0"

def _contract_hash() -> str:
    _mat = "\n".join(
        "%s|%s|%s|%s" % (k.name, k.shape, k.required, ",".join(sorted(k.profiles)))
        for k in sorted(CONTRACT, key=lambda k: k.name)
    )
    return _hashlib.sha256(_mat.encode("utf-8")).hexdigest()

CONTRACT_HASH = _contract_hash()

def version_string(data_inputs_hash: str = "") -> str:
    """The `versions` slot_data value. Carries all three identities a bug report needs:
    which apworld, which contract shape, and which generated DATA the seed was built from."""
    _d = (data_inputs_hash or "").replace("sha256:", "")[:16] or "unknown"
    return "apworld/%s contract/%s data/%s" % (APWORLD_VERSION, CONTRACT_HASH[:8], _d)
