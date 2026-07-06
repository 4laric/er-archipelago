"""The apworld <-> client slot_data CONTRACT -- single source of truth (matt-free greenfield).

Every key that flows from the apworld's fill_slot_data into the runtime client is declared here ONCE:
its exact name, its wire SHAPE (tied to the client's parser), whether it is required, which contract
PROFILE(s) use it (greenfield / bedrock / both), which apworld module PRODUCES it, which client
file:fn CONSUMES it, and a one-line semantic. `validate_slot_data()` checks an assembled slot_data
dict against these declarations so a shape/spelling/required drift fails at GEN time (this is what
would have caught the list-vs-scalar `locationFlags` bug). `to_markdown/json/rust` emit the docs and
the language-neutral + Rust-side mirrors so the client validates the SAME contract (two-sided).

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


def _chk_any(v):
    return None


# name -> (checker, rust_variant, client_parser_doc)
SHAPES = {
    "SCALAR_INT_MAP":  (_chk_scalar_int_map,  "ScalarIntMap",  "i64_to_u32_map / i64_map / str_to_u32"),
    "LISTVAL_INT_MAP": (_chk_listval_int_map, "ListvalIntMap", "str_to_u32vec"),
    "TRIPLE_LIST":     (_chk_triple_list,     "TripleList",    "parse_triples"),
    "INT_LIST":        (_chk_int_list,        "IntList",       "arr_i32 / arr_u32"),
    "BOOL":            (_chk_bool,            "Bool",          "as_bool"),
    "BOOL_OR_INT":     (_chk_bool_or_int,     "BoolOrInt",     "parse_death_link / parse_dlc"),
    "STR":             (_chk_str,             "Str",           "as_str"),
    "NESTED_GRANTS":   (_chk_nested_grants,   "NestedGrants",  "progressive.rs custom"),
    "ANY":             (_chk_any,             "Any",           "(bedrock; not greenfield-validated)"),
}

GREENFIELD, BEDROCK, BOTH = "greenfield", "bedrock", "both"


class ContractKey:
    __slots__ = ("name", "shape", "required", "profiles", "producer", "consumer", "doc")

    def __init__(self, name, shape, required, profiles, producer, consumer, doc):
        assert shape in SHAPES, f"unknown shape {shape} for {name}"
        self.name = name
        self.shape = shape
        self.required = required          # required for the greenfield profile
        self.profiles = profiles          # tuple of GREENFIELD/BEDROCK (or BOTH)
        self.producer = producer          # apworld module that emits it ("(bedrock apworld)" if N/A)
        self.consumer = consumer          # client file:fn that reads it
        self.doc = doc

    def in_profile(self, profile):
        return BOTH in self.profiles or profile in self.profiles


# ---------------------------------------------------------------------------------------------------
# THE CONTRACT. Order = logical grouping. `required` is for the greenfield profile.
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
                "'<Region> Lock' -> the region-open event flag set when that lock is received."),
    ContractKey("regionSphereTargets", "ANY", False, (GREENFIELD,),
                "core._base_slot_data", "(informational)",
                "region -> sphere target [0..1] for completion scaling; not enforced by the client."),
    # --- region locking / kick-watch ---
    ContractKey("areaLockFlags", "TRIPLE_LIST", True, (BOTH,),
                "features/area_locks.py", "region.rs:103 parse_triples",
                "[lo,hi,open_flag] play_region ranges; locked (kicked) while open_flag is unset."),
    ContractKey("lockRevealFlags", "LISTVAL_INT_MAP", False, (BOTH,),
                "(future) per-region map reveal", "region.rs:121 str_to_u32vec",
                "'<Region> Lock' -> map-reveal/enforcement flags set on lock receipt."),
    # --- graces ---
    ContractKey("regionGraces", "LISTVAL_INT_MAP", False, (BOTH,),
                "features/grace_rando.py", "region.rs:122 str_to_u32vec",
                "'<Region> Lock' -> grace warp flags lit on lock receipt (bundle=all, freebie=front door)."),
    ContractKey("graceItems", "SCALAR_INT_MAP", False, (GREENFIELD,),
                "features/grace_rando.py", "region.rs:123 str_to_u32",
                "scatter grace item name -> the single grace flag it lights when received."),
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
    # --- sweeps / progressive / deathlink / dlc ---
    ContractKey("dungeonSweepFlags", "LISTVAL_INT_MAP", False, (BOTH,),
                "features/boss_sweeps (P3b client patch)", "region.rs:104 as_object",
                "dungeon trigger flag (str) -> the member AP location ids auto-registered on clear."),
    ContractKey("progressiveGrants", "NESTED_GRANTS", False, (BOTH,),
                "features/progressive.py", "progressive.rs",
                "item name -> ordered [{goods, flags}] granted on each successive receipt."),
    ContractKey("death_link", "BOOL_OR_INT", False, (BOTH,),
                "features/deathlink.py", "options::parse_death_link",
                "shared deaths across the multiworld."),
    ContractKey("enable_dlc", "BOOL_OR_INT", False, (BOTH,),
                "core (options echo)", "options::parse_dlc",
                "DLC / Land of Shadow regions active; gates the DLC map-reveal flags."),
    ContractKey("world_logic", "STR", False, (GREENFIELD,),
                "core._base_slot_data", "(informational)",
                "logic profile tag, e.g. 'region_lock'."),
    # --- bedrock-profile keys (client reads; greenfield does NOT emit) -- the swap target ---
    ContractKey("locationIdsToKeys", "ANY", False, (BEDROCK,),
                "(bedrock apworld)", "key_resolver.rs",
                "matt slot key token per location; client resolves token1 -> flag (bedrock path)."),
    ContractKey("naturalKeyTriggers", "ANY", False, (BEDROCK,),
                "(bedrock apworld)", "key_resolver.rs / region.rs",
                "bedrock natural key triggers."),
    ContractKey("lockGrantItems", "ANY", False, (BEDROCK,),
                "(bedrock apworld)", "region.rs",
                "items granted on a region lock receipt (bedrock)."),
    ContractKey("dungeonSweeps", "ANY", False, (BEDROCK,),
                "(bedrock apworld)", "region.rs",
                "bedrock dungeon sweep spec (greenfield uses dungeonSweepFlags)."),
    ContractKey("itemCounts", "ANY", False, (BEDROCK,),
                "(bedrock apworld)", "core.rs",
                "per-item quantity map."),
)

BY_NAME = {k.name: k for k in CONTRACT}

# Module-level name constants (UPPER_SNAKE = "wireName") so emitters never hard-code a string literal.
import re as _re
_g = globals()
for _k in CONTRACT:
    _const = _re.sub(r"(?<!^)(?=[A-Z])", "_", _k.name).upper().replace("__", "_")
    _g[_const] = _k.name
# (e.g. LOCATION_FLAGS = "locationFlags", AREA_LOCK_FLAGS = "areaLockFlags", DEATH_LINK = "death_link")


class ContractError(Exception):
    pass


def validate_slot_data(sd, profile=GREENFIELD, strict=True):
    """Check an assembled slot_data dict against the contract. Returns a list of problem strings.
    With strict=True, raises ContractError if any REQUIRED key is missing or any present contract key
    has the wrong shape. Unknown keys (option echoes AP adds automatically) are ignored, not errors."""
    problems = []
    for key in CONTRACT:
        if not key.in_profile(profile):
            continue
        if key.name not in sd:
            if key.required:
                problems.append(f"MISSING required key {key.name!r} (producer {key.producer})")
            continue
        checker = SHAPES[key.shape][0]
        err = checker(sd[key.name])
        if err:
            problems.append(f"SHAPE {key.name!r} ({key.shape}): {err}")
    if strict and problems:
        raise ContractError("slot_data contract violation:\n  " + "\n  ".join(problems))
    return problems


# ---------------------------------------------------------------------------------------------------
# GENERATORS -- docs + language-neutral + Rust mirror (so the client validates the SAME contract).
# ---------------------------------------------------------------------------------------------------
def to_json():
    import json
    return json.dumps({
        "shapes": {n: {"rust": SHAPES[n][1], "client_parser": SHAPES[n][2]} for n in SHAPES},
        "keys": [{"name": k.name, "shape": k.shape, "required": k.required,
                  "profiles": list(k.profiles), "producer": k.producer,
                  "consumer": k.consumer, "doc": k.doc} for k in CONTRACT],
    }, indent=2)


def to_markdown():
    lines = ["# Greenfield ER apworld <-> client slot_data contract",
             "",
             "AUTO-GENERATED from `eldenring_gf/contract.py` (the single source of truth). Do not edit.",
             "",
             "| key | shape | req | profile | producer | client consumer | meaning |",
             "|-----|-------|-----|---------|----------|-----------------|---------|"]
    for k in CONTRACT:
        prof = "both" if BOTH in k.profiles else "+".join(k.profiles)
        req = "yes" if k.required else ""
        lines.append(f"| `{k.name}` | {k.shape} | {req} | {prof} | {k.producer} | {k.consumer} | {k.doc} |")
    lines += ["", "## Shapes", "",
              "| shape | client parser |", "|-------|---------------|"]
    for n in SHAPES:
        lines.append(f"| {n} | `{SHAPES[n][2]}` |")
    return "\n".join(lines) + "\n"


def to_rust():
    """Generate contract_gen.rs: Shape enum, the CONTRACT table, and a validate(sd) fn that mirrors
    validate_slot_data on the client side. Pure data + a small fixed validator (serde_json)."""
    variants = sorted({SHAPES[n][1] for n in SHAPES})
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
        gf = "true" if (BOTH in k.profiles or GREENFIELD in k.profiles) else "false"
        req = "true" if k.required else "false"
        L.append(f'    ContractKey {{ name: "{k.name}", shape: Shape::{SHAPES[k.shape][1]}, '
                 f"required: {req}, greenfield: {gf} }},")
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
        Shape::TripleList => v.as_array().map_or(false, |a| {
            a.iter().all(|t| t.as_array().map_or(false, |t| t.len() == 3 && t.iter().all(is_int)))
        }),
        Shape::IntList => v.as_array().map_or(false, |a| a.iter().all(is_int)),
        Shape::Bool => v.is_boolean(),
        Shape::BoolOrInt => v.is_boolean() || v.as_i64().map_or(false, |n| n == 0 || n == 1),
        Shape::Str => v.is_string(),
        Shape::NestedGrants => v.as_object().map_or(false, |o| {
            o.values().all(|l| l.as_array().map_or(false, |l| l.iter().all(|e| {
                e.get("goods").map_or(false, is_int)
                    && e.get("flags").and_then(|f| f.as_array())
                        .map_or(false, |f| f.iter().all(is_int))
            })))
        }),
        Shape::Any => true,
    }
}

/// Validate an assembled slot_data object against the greenfield contract. Returns the list of
/// problems (missing-required + shape mismatches); empty == clean. Mirrors contract.py.
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
    out
}'''
