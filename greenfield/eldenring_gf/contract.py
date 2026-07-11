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


def _chk_int_list(v):
    # arr_i32 / arr_u32 : [int, ...]
    if not isinstance(v, (list, tuple)) or not all(_is_int(i) for i in v):
        return "expected [int, ...]"
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
    # progressiveGrants : {name: [{"goods": int, "flags": [int]}, ...]}
    if not isinstance(v, dict):
        return "expected {name: [{goods:int, flags:[int]}]}"
    for k, lst in v.items():
        if not isinstance(lst, (list, tuple)):
            return f"{k!r} must map to a list"
        for e in lst:
            if not isinstance(e, dict) or not _is_int(e.get("goods")) or \
               not (isinstance(e.get("flags"), (list, tuple)) and all(_is_int(i) for i in e["flags"])):
                return f"{k!r} entry must be {{goods:int, flags:[int]}}, got {e!r}"
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
    "INT_LIST":        (_chk_int_list,        "IntList",       "arr_i32 / arr_u32"),
    "BOOL":            (_chk_bool,            "Bool",          "as_bool"),
    "BOOL_OR_INT":     (_chk_bool_or_int,     "BoolOrInt",     "parse_death_link / parse_dlc (0/1)"),
    "INT_OR_BOOL":     (_chk_int_or_bool,     "IntOrBool",     "parse_bool_option (nonzero = on)"),
    "INT":             (_chk_int,             "Int",           "as_i64"),
    "NUMBER":          (_chk_number,          "Number",        "as_f64"),
    "STR":             (_chk_str,             "Str",           "as_str"),
    "NESTED_GRANTS":   (_chk_nested_grants,   "NestedGrants",  "progressive.rs custom"),
    "OPTIONS_DICT":    (_chk_options_dict,    "OptionsDict",   "options::parse_*_option sub-dict"),
    "ANY":             (_chk_any,             "Any",           "(diagnostic / foreign profile; unvalidated)"),
}

GREENFIELD, BEDROCK, BOTH = "greenfield", "bedrock", "both"


# ---------------------------------------------------------------------------------------------------
# SHARED DERIVED-DATA (single source of truth so the apworld and client CAN'T drift). BIG_TICKET_TYPES
# = the LOCATION_TAGS types that count as a prominent/"big-ticket" check. ONE definition, both sides:
# features/curated_fill.py routes region Locks onto these, and the client's F6 tracker highlights /
# filters them -- via tools/gen_location_regions.py, which imports THIS set to bake the
# er_logic::tracker_regions LOCATION_META big_ticket column. So "where the locks go" == "what the
# tracker flags" by construction. Per-location membership is generated from location_tags.py (a
# seed-invariant ~4k-row static table, not slot_data); the DEFINITION lives here in the contract.
# Class vocabulary shared with important_locations (features/important_locations.py imports this).
# The big_ticket_locations option draws from the SAME set. "EniaShop" is INTERNAL (gen_data tags the
# remembrance store) and is never user-selectable.
IMPORTANT_LOCATION_TYPES = ["Remembrance", "Seedtree", "Church", "Boss", "Fragment", "Revered",
                            "Basin", "Shop", "Legendary", "GreatRune", "KeyItem", "MajorBoss"]
# MajorBoss = the ~24 REGION_BOSSES (method=boss_arena remembrance/great-rune arena bosses) UNION a
# curated MAJOR_BOSS_EXTRAS set of hand-picked field/evergaol/dragon bosses that cover the otherwise
# major-less regions (gen_data.py). These are the highest-confidence physical locations (boss-arena /
# boss-defeat flags the client already ships as bossLocations), so the v0.2 progression_surface
# restriction confines this world's own progression (region Locks + required/gate runes + legacy keys)
# to them by default. MajorBoss is a SUBSET of Remembrance/GreatRune (for the boss_arena majors) plus
# Boss/Legendary (for the extras); it is its own tag so the surface can target JUST the majors.
# big_ticket_locations option DEFAULT = the historical hardcoded set (backward-compatible: same 73).
BIG_TICKET_DEFAULT_LIST = ["Boss", "Remembrance", "Legendary", "GreatRune", "KeyItem"]
BIG_TICKET_TYPES = frozenset(BIG_TICKET_DEFAULT_LIST)
# A location carrying any EXCLUDE tag is NEVER big-ticket, whatever is selected. EniaShop = Enia's
# remembrance store (gen_data: a shop slot holding a rarity-3 item) -- buy-only, so no region Lock and
# no tracker star even when Shop or Legendary is selected. This is why Shop can be a normal selectable
# class ("turn on some shops") without dragging Enia in.
BIG_TICKET_EXCLUDE_TAGS = frozenset({"EniaShop"})


def is_big_ticket(tags, selected=None) -> bool:
    """Single source for "is this a prominent/big-ticket check", used by features/curated_fill (lock
    placement), features/big_ticket_locations (the slot_data id list the F6 tracker reads) AND
    tools/gen_location_regions (the static fallback column) so none of them can drift. True iff the
    location's LOCATION_TAGS include a SELECTED class and NONE of BIG_TICKET_EXCLUDE_TAGS. `selected`
    defaults to BIG_TICKET_TYPES (the option default); pass world.options.big_ticket_locations.value
    for a seed. The underlying tags are untouched -- important_locations / display still see them."""
    t = set(tags or ())
    sel = BIG_TICKET_TYPES if selected is None else set(selected)
    return bool(sel & t) and not (BIG_TICKET_EXCLUDE_TAGS & t)


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
    ContractKey("locationFlags", "SCALAR_INT_MAP", True, (BOTH,),
                "core._base_slot_data", "core.rs:330 i64_to_u32_map",
                "AP location id (str) -> its ER acquisition event flag; the flag-poll detection table."),
    ContractKey("regionOpenFlags", "SCALAR_INT_MAP", True, (BOTH,),
                "core._base_slot_data", "region.rs:120 str_to_u32",
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
    # --- graces ---
    ContractKey("regionGraces", "LISTVAL_INT_MAP", False, (BOTH,),
                "features/graces.py", "region.rs:122 str_to_u32vec",
                "item_name -> grace warp flags lit when that item is RECEIVED. Usually keyed by "
                "'<Region> Lock' (bundle: all of the region's graces), but grace GATES also key a "
                "sub-area's graces on a KEY ITEM instead of the region Lock -- e.g. Raya Lucaria's "
                "graces key on 'Academy Glintstone Key' so they light on key receipt, not on the "
                "Liurnia Lock. Client MUST light on receipt of ANY keyed item, not just Locks."),
    ContractKey("runeGatedGraces", "LISTVAL_INT_MAP", False, (GREENFIELD,),
                "features/graces.py", "region.rs (NEW -- rune-count gate)",
                "str(N) -> grace warp flags lit only once the player has RECEIVED at least N Great "
                "Runes (any of greatRuneItemIds). Used for the Leyndell capital graces (folded into "
                "Altus) which vanilla gates behind 2 Great Runes; those graces are pulled from the "
                "Altus Lock bundle and moved here. Absent/empty when leyndell_runes_required = 0."),
    ContractKey("greatRuneItemIds", "INT_LIST", False, (GREENFIELD,),
                "features/graces.py", "region.rs (NEW -- rune-count gate)",
                "FullIDs of every Great Rune item in this seed's pool -- the set the client counts "
                "RECEIVED items against to satisfy runeGatedGraces. Emitted only with runeGatedGraces."),
    # --- start-of-run grants ---
    ContractKey("startRegion", "STR", True, (BOTH,),
                "features/start_grace.py", "core.rs:410 as_str",
                "name of the always-kept start region (diagnostic + start anchor)."),
    ContractKey("startGraces", "INT_LIST", False, (BOTH,),
                "features/start_grace.py", "startgrants.rs:58 arr_u32",
                "grace flags lit at spawn so the first warp is possible (front-door of start region)."),
    ContractKey("startItems", "INT_LIST", False, (BOTH,),
                "features/start_items.py", "startgrants.rs:57 arr_i32",
                "FullIDs granted once at game start (Torch, Spectral Steed Whistle, ...)."),
    ContractKey("reveal_all_maps", "BOOL", False, (BOTH,),
                "features/start_grace.py", "startgrants.rs as_bool",
                "reveal the whole world map + underground view (client owns the RE'd flag set)."),
    # --- goal ---
    ContractKey("bigTicketLocations", "INT_LIST", False, (GREENFIELD,),
                "features/big_ticket_locations.py",
                "core.rs self.big_ticket (fallback tracker_regions::big_ticket_set)",
                "AP location ids that are big-ticket THIS seed = is_big_ticket(tags, "
                "big_ticket_locations); Enia (EniaShop) always excluded. Client stars/locks these; "
                "absent -> client falls back to the static default table."),
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
                "item name -> ordered [{goods, flags}] granted on each successive receipt."),
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
    ContractKey("versions", "STR", False, (BOTH,),
                "(optional; unemitted today)", "core.rs version gate",
                "apworld semver for the client version gate; emission optional."),
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
    ContractKey("great_rune_items", "ANY", False, (GREENFIELD,),
                "core._base_slot_data", "(diagnostic -- no client read)",
                "required Great Rune item names this seed."),
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
    # --- bedrock-profile keys (client reads; greenfield does NOT emit) -- the swap target ---
    # required=True here means required when validating profile="bedrock" ONLY (profile-aware).
    ContractKey("locationIdsToKeys", "ANY", True, (BEDROCK,),
                "(bedrock apworld)", "key_resolver.rs",
                "matt slot key token per location; client resolves token1 -> flag (bedrock path)."),
    ContractKey("itemCounts", "ANY", True, (BOTH,),
                "core._base_slot_data (greenfield) / bedrock apworld", "core.rs receive.rs itemCounts",
                "per-item quantity map {str(ap_item_id): qty}; client grants full_id x qty. Greenfield "
                "emits stack sizes for throwables (x10) and finished pots (x4) (features/filler_curation)."),
    ContractKey("naturalKeyTriggers", "ANY", True, (BEDROCK,),
                "(bedrock apworld)", "key_resolver.rs / region.rs",
                "bedrock natural key triggers."),
    ContractKey("lockGrantItems", "ANY", True, (BEDROCK,),
                "(bedrock apworld)", "region.rs",
                "items granted on a region lock receipt (bedrock)."),
    ContractKey("randomStartDoneFlag", "ANY", True, (BEDROCK,),
                "(bedrock apworld)", "random start client path",
                "bedrock random-start: flag set when the start warp completed."),
    ContractKey("randomStartWarpFlag", "ANY", True, (BEDROCK,),
                "(bedrock apworld)", "random start client path",
                "bedrock random-start: flag that triggers the start warp."),
    ContractKey("randomStartAreaId", "ANY", True, (BEDROCK,),
                "(bedrock apworld)", "random start client path",
                "bedrock random-start: destination area id."),
    ContractKey("randomStartGraceId", "ANY", True, (BEDROCK,),
                "(bedrock apworld)", "random start client path",
                "bedrock random-start: destination grace id."),
    ContractKey("fogWalls", "ANY", True, (BEDROCK,),
                "(bedrock apworld)", "fog wall client path",
                "bedrock fog-wall spec."),
    ContractKey("fogWallDebug", "ANY", True, (BEDROCK,),
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
             "AUTO-GENERATED from `eldenring_gf/contract.py` (the single source of truth). Do not edit.",
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

    def key_row(k):
        gf = "true" if (BOTH in k.profiles or GREENFIELD in k.profiles) else "false"
        req = "true" if k.required else "false"
        return (f'    ContractKey {{ name: "{k.name}", shape: Shape::{SHAPES[k.shape][1]}, '
                f"required: {req}, greenfield: {gf} }},")

    L = []
    L.append("// AUTO-GENERATED from eldenring_gf/contract.py -- do not edit by hand.")
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
    return "\n".join(L) + "\n"


_RUST_VALIDATE = r'''fn is_int(v: &Value) -> bool { v.is_i64() || v.is_u64() }

fn shape_ok(shape: Shape, v: &Value) -> bool {
    match shape {
        Shape::ScalarIntMap => v.as_object().map_or(false, |o| o.values().all(is_int)),
        Shape::ListvalIntMap => v.as_object().map_or(false, |o| {
            o.values().all(|x| x.as_array().map_or(false, |a| a.iter().all(is_int)))
        }),
        Shape::StrMap => v.as_object().map_or(false, |o| o.values().all(|x| x.is_string())),
        Shape::TripleList => v.as_array().map_or(false, |a| {
            a.iter().all(|t| t.as_array().map_or(false, |t| t.len() == 3 && t.iter().all(is_int)))
        }),
        Shape::IntList => v.as_array().map_or(false, |a| a.iter().all(is_int)),
        Shape::Bool => v.is_boolean(),
        Shape::BoolOrInt => v.is_boolean() || v.as_i64().map_or(false, |n| n == 0 || n == 1),
        Shape::IntOrBool => v.is_boolean() || is_int(v),
        Shape::Int => is_int(v),
        Shape::Number => v.is_number(),
        Shape::Str => v.is_string(),
        Shape::NestedGrants => v.as_object().map_or(false, |o| {
            o.values().all(|l| l.as_array().map_or(false, |l| l.iter().all(|e| {
                e.get("goods").map_or(false, is_int)
                    && e.get("flags").and_then(|f| f.as_array())
                        .map_or(false, |f| f.iter().all(is_int))
            })))
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
