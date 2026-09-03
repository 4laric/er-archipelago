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

    A rung must carry non-empty goods and/or flags. When goods are present, `consumed` is REQUIRED,
    and it is required for a reason worth a paragraph. A flags-only rung has nothing to reconcile
    in inventory, so `consumed` is neither meaningful nor emitted (#804 stone-bell fix).

    The client folds a rung's goods one of two ways: OWNED goods go to `unique_goods`, a SELF-HEALING
    set meaning "the player should have this; if it is missing, grant it". CONSUMED goods are
    ledgered by the copy's stream index and granted exactly ONCE.

    Ship a consumable as OWNED and the game eats itself: a Golden Seed is SPENT at a Site of Grace, so
    the reconciler sees it leave the inventory and hands it straight back -- upgrade, re-grant,
    upgrade, re-grant, unbounded, until flask potency runs past its cap and the game CTDs. That is
    exactly what shipped on 2026-07-12, and it shipped because the field did not exist and the
    dangerous default was the silent one.

    So it is not optional and it does not default. A rung must SAY which it is.
    """
    if not isinstance(v, dict):
        return "expected {name: [{goods?:int, flags:[int], consumed?:bool}]}"
    for k, lst in v.items():
        if not isinstance(lst, (list, tuple)):
            return f"{k!r} must map to a list"
        for e in lst:
            noop = isinstance(e, dict) and e.get("noop") is True and len(e) == 1
            flags_ok = (isinstance(e, dict) and isinstance(e.get("flags"), (list, tuple))
                        and all(_is_int(i) for i in e["flags"]))
            goods_present = isinstance(e, dict) and "goods" in e
            invalid_effect = (not flags_ok or
                              (goods_present and not _is_int(e.get("goods"))) or
                              (not goods_present and
                               (not isinstance(e, dict) or not e.get("flags"))))
            if not noop and invalid_effect:
                return (f"{k!r} entry must carry goods:int and/or non-empty flags:[int], "
                        f"got {e!r}")
            if noop:
                continue
            if goods_present and not isinstance(e.get("consumed"), bool):
                return (f"{k!r} rung is missing `consumed` (bool): {e!r}. A rung must declare whether "
                        f"its goods are SPENT by the player (consumed=true -> granted once, ledgered) "
                        f"or KEPT (consumed=false -> self-healing). Shipping a consumable as kept "
                        f"re-grants it every time the player spends it, and CTDs the game.")
            if not goods_present and "consumed" in e:
                return f"{k!r} flags-only rung must not declare meaningless `consumed`: {e!r}"
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


def _chk_lock_hint_placements(v):
    """Lock item name -> the foreign-safe AP coordinate of its post-fill placement."""
    if not isinstance(v, dict):
        return "expected {lock_name: {player:int, location:int}}"
    for name, placement in v.items():
        if (not isinstance(name, str) or not name or not isinstance(placement, dict)
                or set(placement) != {"player", "location"}
                or not _is_int(placement["player"]) or placement["player"] <= 0
                or not _is_int(placement["location"]) or placement["location"] <= 0):
            return f"invalid lock placement {name!r}: {placement!r}"
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
    "LOCK_PLACEMENTS": (_chk_lock_hint_placements, "LockPlacements", "lock_hint_economy::parse_placements"),
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
# filters them -- via slot_data `progressionSurfaceLocations`, emitted from THIS set. So "where the
# locks go" == "what the tracker flags" by construction, and it is now true PER SEED rather than per
# corpus. (Until 2026-07-28 the client half came from tools/gen_location_regions.py baking an
# on_surface column into er_logic::tracker_regions -- both the tool and that table are retired; the
# tracker's region model ships in slot_data.) The DEFINITION lives here in the contract.
# The location-CLASS vocabulary. Consumed by features/progression_surface (valid_keys + the widen
# ladder) and coverage.py.
# 🛑 THIS ORDER IS A DETERMINISM HANDLE, NOT A DISPLAY ORDER. `selected_surface()` filters a
# player's set THROUGH this list precisely because a Python set of strings has no stable iteration
# order across processes, so reordering it would change the ladder -- and the fill behind it --
# between two runs of the same seed. It reads as historical accretion because it IS: append here,
# never rearrange. The wizard's grid is grouped by FAMILY instead, from a separate presentation
# order in features/progression_surface.SURFACE_CLASS_FAMILIES.
# (There is no `big_ticket_locations` option; the surface is selected by ProgressionSurface.)
# "EniaShop" is INTERNAL (gen_data tags the remembrance store) and is never user-selectable.
# RENAMED 2026-08-08: was `IMPORTANT_LOCATION_TYPES`, a name that outlived its option
# (features/important_locations was deleted 2026-08-02). This list is purely the PROGRESSION
# SURFACE vocabulary now -- features/progression_surface.valid_keys + the widen ladder, coverage.py
# -- and it is not in contract.json, so the rename cost no client churn.
# 🛑 The rename had one real hazard, and it was not the call sites that FAIL loudly: two readers
# used `getattr(contract, "IMPORTANT_LOCATION_TYPES", ())` WITH A DEFAULT. coverage.py would have
# silently classified every location as filler, and test_gf_boss_sweeps'
# test_field_exclude_matches_contract would have compared FIELD_EXCLUDE against an EMPTY set and
# passed VACUOUSLY -- a green parity gate over nothing. Both are direct attribute access now: if
# this constant is ever renamed again, they must break.
# "LegacyBoss" ABSORBED into MajorBoss 2026-08-20 (Alaric): a boss standing in a legacy dungeon
# is a major by any player's reading, and the split earned nothing but a wizard row. The yaml
# spelling stays ACCEPTED -- ProgressionSurface.from_any normalizes it to MajorBoss (the
# limgrave_caves alias precedent) -- so no wild yaml breaks; only the vocabulary shrank.
# 🛑 The TAG "LegacyBoss" is still baked (SURFACE_INTERNAL_TAGS): the MajorBoss tag doubles as
# roster identity for goal/anchor/roster consumers, so the absorption is done at has_class via
# SURFACE_CLASS_EXTRA_TAGS rather than by retagging the data.
# The lockable abilities (#945). The AUTHORITATIVE name list is er-logic's Ability enum
# (crates/er-logic/src/ability_lock.rs parse_set); this mirror exists so the OptionSet's valid_keys
# and the wizard can enumerate them without importing Rust. Order matches the enum. `heal` is NOT
# here -- its mechanism is the flask-charge clamp, not an action lock. Keep the two in sync: a name
# added here that er-logic does not know is silently dropped by parse_ability_lock (tolerant), and
# one er-logic knows that is missing here simply cannot be selected in yaml.
ABILITY_LOCK_KEYS = ("jump", "crouch", "roll", "r1", "r2", "l1", "l2", "heal")

# Progressive ability lock (#945 / #980): the locked abilities can instead be SYNTHETIC UNLOCK ITEMS
# shuffled into the pool -- start locked, unlock the one you find. The item is synthetic (never a
# real EquipParamGoods; the game hands over nothing), recognised by the client through the per-seed
# abilityUnlockItems map, exactly like armorBundles. Display label per ability key.
_ABILITY_LABEL = {"jump": "Jump", "crouch": "Crouch", "roll": "Roll",
                  "r1": "R1", "r2": "R2", "l1": "L1", "l2": "L2", "heal": "Heal"}
# key -> synthetic item NAME, in ABILITY_LOCK_KEYS order. The client learns the id->ability binding
# from slot_data (abilityUnlockItems), so these ids need not be arithmetically stable across seeds --
# but they are allocated at a FIXED BASE (core.py) rather than through a feature's ITEMS anyway, so
# adding them renumbers no other feature's item ids (the spawn-trap lesson).
ABILITY_UNLOCK_ITEM_NAMES = tuple((k, f"Unlock: {_ABILITY_LABEL[k]}") for k in ABILITY_LOCK_KEYS)
# Fixed id block for the seven. 7800000 is the spawn-trap base (10000 wide); 7900000 clears it and
# stays under the next round base. test_gf_ability_unlock asserts the disjointness.
ABILITY_UNLOCK_ITEM_BASE = 7900000
# The er-logic client_features.rs SUPPORTED tag a progressive seed declares, so a client too old to
# turn unlock items back into abilities reports incompatible instead of leaving the player locked.
ABILITY_UNLOCK_FEATURE = "ability_unlock"

SURFACE_CLASSES = ["Remembrance", "Seedtree", "Church", "Boss", "Fragment", "Revered",
                   "Basin", "Shop", "ShopNonSpell", "ShopSlot", "Legendary", "GreatRune",
                   "KeyItem", "MajorBoss", "FieldBoss", "MinorDungeonBoss",
                   "SweepSlot", "SweepSlotMajor", "SweepSlotMinor"]
# 🛑 SweepSlot is NOT A LOCATION TAG. Every other member of this list names a tag that gen_data
# writes onto a check; SweepSlot is DERIVED at world-build time from that seed's own enabled sweeps
# (features/progression_surface.sweep_slot_aps) -- at most one member per sweep trigger, the way
# ShopSlot is at most one row per merchant. It is therefore in NEITHER half of the sweep partition:
# a class that IS a sweep member by definition cannot be "cut from the sweep" without deleting
# itself. See SURFACE_DERIVED_CLASSES below and tools/check_sweep_cut_partition.py, which reads it.
SURFACE_DERIVED_CLASSES = frozenset({"SweepSlot", "SweepSlotMajor", "SweepSlotMinor"})

# ---- The SweepSlot split (#734) ------------------------------------------------------------------
# Alaric, 2026-08-16: "we should maybe be drawing a distinction between major boss sweep slot and
# minor/all boss sweep slot." A sweep payout off a legacy-dungeon boss and one off a cave boss are
# different bargains and plain `SweepSlot` prices them the same.
#
# 🛑 "MAJOR" MEANS THE `MajorBoss` CLASS, NOT `legacy`. That is the ruling, and the two are not close:
# measured over the 218 triggers, 41 legacy triggers are NOT major (both Tree Sentinels, all three
# Scadutree Avatar heads, Esgar) and 5 majors are not legacy (Magma Wyrm Makar, Commander Niall,
# Elemer of the Briar, Leonine Misbegotten, Royal Knight Loretta). `legacy` was the cheap answer and
# it disagrees with the class it is standing in for 46 ways.
#
# The membership itself is NOT decided here -- `boss_sweeps.MAJOR_SWEEP_TRIGGERS` is emitted by
# gen_data, where `MajorBoss` is derived from all four of its sources. Re-deriving it world-side from
# location_tags + boss_reward_lots reaches half the triggers and drops Promised Consort Radahn,
# Starscourge Radahn and the Fire Giant. This file only says which CLASS asks for which half.
#
# ⭐ PER-TRIGGER, NOT PER-ARENA, and that is measured rather than assumed. #363's worry is that a
# dungeon with two triggers could land its heads in different subclasses and pay out a player only
# half a dungeon. Of the 16 maps whose triggers straddle major/minor, ZERO are map-local classes
# (catacomb/cave/tunnel/dungeon) -- every one is a legacy or field map, whose sweeps are region-divvy
# or per-tile and never promised a whole map anyway. There is no partial dungeon to prevent.
SWEEP_SLOT_CLASS_WANTS = {
    "SweepSlot": None,          # every enabled sweep -- unchanged, and still the default
    "SweepSlotMajor": True,     # only those whose trigger boss is a MajorBoss
    "SweepSlotMinor": False,    # only those whose trigger boss is NOT
}


def sweeps_for_surface_class(sweeps, cls, majors):
    """`{trigger: members}` narrowed to the half `cls` asks for. Pure; `majors` is the emitted set.

    🛑 AN UNKNOWN CLASS RETURNS NOTHING, loudly-empty rather than everything. The alternative --
    falling back to the whole map -- would make a typo in the vocabulary silently select every sweep,
    which is the direction that puts foreign progression somewhere the player did not agree to.
    """
    want = SWEEP_SLOT_CLASS_WANTS.get(cls, "unknown")
    if want == "unknown":
        return {}
    if want is None:
        return dict(sweeps or {})
    majors = frozenset(majors or ())
    return {t: m for t, m in (sweeps or {}).items() if (t in majors) is want}
# LegacyBoss / FieldBoss (2026-08-02) split the 134-strong `Boss` class by WHERE the boss stands:
# 30 legacy-dungeon drops, 84 overworld. Both are SUBSETS of Boss, so selecting Boss still selects
# everything. There is no `Underground`: 81 catacomb/cave/tunnel/minor-dungeon bosses exist but only
# THREE drop an AP-tracked check, so the class would be noise (see gen_data's note).
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
# MajorBoss = THE GAME'S OWN ROSTER (#737): the 29 achievement bosses -- every call site of
# common.emevd's trophy event $Event(9300), joined to the boss whose DEFEAT FLAG it fires on
# (greenfield/achievement_bosses.tsv) -- UNION Remembrance/GreatRune, UNION the boss_arena
# REGION_BOSSES, UNION four MAJOR_BOSS_EXTRAS region anchors for the regions the roster does not
# reach at all (Limgrave, Gravesite, Jagged Peak, Rauh Base). It was a hand-curated list until
# 2026-08-16 and was wrong in both directions against matt's published roster; the achievement table
# is the same set he means and nobody has to vote on it. These are the highest-confidence physical
# locations (boss-arena / boss-defeat flags the client already ships as bossLocations), so the v0.2
# progression_surface restriction confines this world's own progression (region Locks +
# required/gate runes + legacy keys) to them by default.
# 🛑 CONTAINMENT, CORRECTED 2026-08-08 -- this comment had it BACKWARDS. It read "MajorBoss is a
# SUBSET of Remembrance/GreatRune"; measured over LOCATION_TAGS the relation is the REVERSE, and it
# matters for what the wizard can tell a player:
#   Remembrance (25) and GreatRune (7) are SUBSETS of MajorBoss (52)  <- not the other way round
#   MajorBoss is itself a SUBSET of Boss (266), as are LegacyBoss (52) and FieldBoss (110)
#   MajorBoss n Legendary = 2; neither contains the other
# Counts re-measured over LOCATION_TAGS 2026-08-16, and MajorBoss moved TWICE that day for two
# unrelated reasons, which is worth keeping straight:
#   52 -> 43  (#737 direction 1) a roster entry is keyed on a boss's acquisition FLAG, and the
#             sibling lots that flag also drives -- two DLC bosses' entire ARMOUR SETS -- were
#             inheriting the tag. One check per boss.
#   43 -> 51  (#737 direction 2) the roster stopped being a hand list and became the game's own
#             achievement table: +11 achievement bosses that had no MajorBoss check, -3 hand anchors
#             whose regions the roster now covers.
# `Boss` did not move on either (266). Margit is an achievement boss with NO check anywhere in our
# data and is ledgered as such in gen_data._ACH_NO_CHECK rather than counted here.
# So ticking MajorBoss in the default surface already covers every Remembrance and GreatRune check:
# those two boxes select NOTHING further, and ticking Boss makes all three redundant. The lattice is
# DERIVED at wizard-build time (features/progression_surface.class_containment) rather than typed
# here, because a typed copy is what let this comment sit inverted. It is its own tag so the surface
# can target JUST the majors.
# BIG-TICKET IS RETIRED (2026-07-12, Alaric). It was a SECOND list claiming to define "the important
# checks", and it disagreed with the first: the progression surface is
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

# INTERNAL tags: present in LOCATION_TAGS, deliberately NOT in SURFACE_CLASSES (not user-selectable)
# and NOT excluding. "LegacyBoss" survives as a tag because goal_locations / anchor eligibility /
# the roster-uniqueness law read the raw MajorBoss tag as ROSTER identity; only the CLASS was
# absorbed (2026-08-20, Alaric). Matched onto the MajorBoss selection via SURFACE_CLASS_EXTRA_TAGS.
SURFACE_INTERNAL_TAGS = frozenset({"LegacyBoss"})

# CLASS -> extra internal tags that selection also matches. THE absorption seam: has_class and
# features/progression_surface.class_containment both read it, so the surface and the wizard's
# covered-by lattice cannot disagree about what a class covers.
SURFACE_CLASS_EXTRA_TAGS = {"MajorBoss": frozenset({"LegacyBoss"})}

# The DEFAULT progression surface. It lives HERE, beside has_class, because it has two consumers that
# cannot import each other:
#   * features/progression_surface.ProgressionSurface.default -- the AP option (needs the AP env)
#   * [RETIRED 2026-07-28] tools/gen_location_regions.py      -- baked the tracker's static column;
#     the surface now reaches the client as slot_data progressionSurfaceLocations instead
# Retiring `is_big_ticket` (20bc529) renamed the predicate but left the SELECTION inlined in the option
# class, where the AP-free generator could not reach it. So the generator kept calling the old name and
# the Windows build died at the tracker-table step. Single-sourcing a predicate is only half the job:
# the SELECTION it is applied to must be single-source too, or the second caller re-invents it.
# 🛑 `Remembrance` AND `GreatRune` LEFT THIS SET 2026-08-16 (#733) AND THE SURFACE DID NOT MOVE.
# Both are STRICT SUBSETS of `MajorBoss`, measured over the generated LOCATION_TAGS:
#
#     Remembrance 25 | GreatRune 7 | MajorBoss 43
#     Remembrance ⊂ MajorBoss   GreatRune ⊂ MajorBoss   Remembrance ∩ GreatRune = 0
#     allowed_ap_ids(defaults) == allowed_ap_ids(defaults - {Remembrance, GreatRune})  -- 199 == 199
#
# So while `MajorBoss` is in this set the two entries admit not one location, and the wizard drew them
# as two live knobs a player could reason about. They are not MERGEABLE either (disjoint: a demigod
# arena yields two separate checks, the Remembrance by method tag and the Great Rune by item name), so
# the redundancy is real and the tidy-up is not.
#
# 🛑 THEY STAY IN `SURFACE_CLASSES` AND IN `valid_keys`. `OptionSet` raises on an unknown key, so
# dropping them would make every existing yaml that names one fail outright, and `Options.Removed` is
# per-OPTION, not per-KEY -- there is no migration. A player who selects them still gets exactly what
# they ask for; they are simply no longer ON by default, because on-by-default implied they did
# something. Pinned by test_gf_progression_surface_contract, which asserts the identity above rather
# than the membership, so re-adding them is caught by MEANING and not by a name list.
SURFACE_DEFAULT_CLASSES = frozenset({
    "KeyItem", "MajorBoss",
    "Church", "Seedtree", "Fragment", "Revered", "ShopSlot",
    # 🛑 SweepSlot JOINED THE DEFAULT 2026-08-13 (Alaric's ruling on #631). THIS CHANGES EVERY SEED,
    # deliberately, and it is stated here rather than left to be discovered.
    #
    # WHY. The surface is ~30 locations on a 4-region seed against ~1500 checks, and
    # `confine_foreign_progression` (default 100) may place another world's progression ONLY there.
    # Measured: a slot received 7 of the 60 foreign key items it would have received at confine 0 --
    # the other 53 stayed in their own world and the checks were backfilled with our own items. One
    # member per enabled sweep roughly TRIPLES the surface and takes intake to 18 (DOOM), 44 (Hollow
    # Knight), 28 (Bumper Stickers), while `confine`'s promise stays exactly kept (nothing foreign
    # lands off-surface). It also relieves the small-surface case: at num_regions 1 with a
    # [MajorBoss] surface the feasibility ladder was spilling our OWN Locks off a two-location
    # surface, and this takes that spill to zero.
    #
    # WHAT IT COSTS. A sweep can now pay out progression in a default seed -- kill the boss, and one
    # of the checks it hands over may hold a key. That was already true at `confine 0` or an empty
    # surface (63% of foreign progression landed on sweep members, exactly the base rate), and it is
    # not a logic hazard: a member's access rule is its REGION, so the sweep only makes the check
    # earlier, never reachable-only-that-way. It IS a texture change, and it is the ruling.
    "SweepSlot",
})


# Which boss CLASSES each dungeon_sweep rung sweeps. boss_healthbars classifies every boss as one of
# catacomb/cave/tunnel/dungeon (the minidungeons), legacy (legacy dungeons + castles) or field.
# LIVES HERE, not in features/boss_locks, for the reason SURFACE_DEFAULT_CLASSES lives here: two
# AP-FREE readers need it -- tools/build_region_census.py has to price a SweepSlot box the wizard
# draws, and it cannot import a module that imports Options.
SWEEP_MINI_CLASSES = frozenset({"catacomb", "cave", "tunnel", "dungeon"})
SWEEP_RUNGS = {
    "none": frozenset(),
    "minidungeons": SWEEP_MINI_CLASSES,
    "all": SWEEP_MINI_CLASSES | {"legacy"},
    "bosses": SWEEP_MINI_CLASSES | {"legacy", "field"},
}


# Sweeps that may NOT contribute a SweepSlot surface entry, {trigger flag: reason}.
#
# 🛑 THE RULE, borrowed verbatim from ShopSlot, whose SHOP_SLOT_SKIPS reason strings already say it:
# "a slot we cannot ASSERT is reachable may not be REQUIRED." A sweep is the same shape one step
# over -- **a member we cannot assert is SWEPT may not be required.** SweepSlot's whole premise is
# that progression only lands where a trigger will hand it over; a trigger we cannot vouch for
# turns that promise into a coincidence.
#
# MOTIVATING CASE (bobler, 2026-08-14, er-archipelago#672). Progression restricted to boss sweeps.
# He cleared 19/19 Limgrave bosses and finished with two progression checks still open:
#   * `Limgrave :: Warming Stone - near Limgrave Tower Bridge [f34107000]`, swept by 34100800 --
#     BOSS_HEALTHBARS records ('m34_10', 'm34_10', 'dungeon', ''), an EMPTY name. The Divine Tower
#     of Limgrave has no boss; arena_graces.tsv's own header already lists 34100800 under
#     `# unresolved_bosses`. There was never anything to kill.
#   * `Limgrave :: Mushroom - treasure - Murkwater Cave [f31007000]`, swept by 31000850 -- Patches,
#     who YIELDS rather than dying, so the defeat flag is not reached in normal play.
#
# 🛑🛑 Patches is the reason this cannot be derived from the data alone, and the reason his case is
# listed by hand. His tracker entry read "Patches ✅" the whole time -- but that is the check his
# ENCOUNTER grants, not the sweep's defeat flag. The usual rule (a boss's identity is the check its
# death grants) is exactly what comes apart here, so no join over the shipped tables can see it.
# The non-lethal class needs enumerating rather than special-casing; this is the one confirmed member.
_RUNTIME_SWEEP_SKIP_REASONS = {
    31000800: "non-lethal trigger: Patches yields instead of dying, so his defeat flag is not "
              "reached in normal play -- the sweep cannot fire (bobler 2026-08-14, #672)",
    31000850: "non-lethal trigger: Patches yields instead of dying, so his defeat flag is not "
              "reached in normal play -- the sweep cannot fire (bobler 2026-08-14, #672)",
}


def runtime_sweep_skips():
    """{trigger flag: reason} for sweeps known not to fire in normal play.

    This is deliberately NARROWER than :func:`sweep_slot_skips`. An unnamed trigger or a trigger
    whose arena has not been audited is unsafe as a REQUIRED progression host, but may still be a
    working convenience sweep. Only a positive fireability ruling belongs here and disappears from
    seed slot data, the client tracker, boss-key gates, and the generated ``may be sweep-granted by`` text.

    Return a copy so callers cannot mutate the contract's ruling for the rest of generation.
    """
    return dict(_RUNTIME_SWEEP_SKIP_REASONS)

_UNNAMED_TRIGGER_REASON = (
    "unnamed trigger: BOSS_HEALTHBARS records no boss name for this sweep, so we cannot name a "
    "boss to kill and cannot assert the sweep can ever fire"
)

_UNAUDITED_TRIGGER_REASON = (
    "unaudited arena: SWEEP_ARENA_REGION has no authoritative region for this trigger, so its "
    "members cannot be asserted reachable and may not be required (#671)"
)

_SPLIT_TRIGGER_REASON = (
    "arena/members split: SWEEP_ARENA_REGION and SWEEP_REGION disagree, so the trigger boss is "
    "fought in a different region from the members it grants -- a SweepSlot here would place "
    "progression behind a boss the seed's region selection may exclude, or hand it over before the "
    "members' region opens (#523, Margit 2026-08-17). A curated arena override that co-regions the "
    "two (gen_data _ARENA_REGION_CURATED) removes the trigger from this set so a corrected boss "
    "keeps its slot"
)


def sweep_slot_skips(healthbars=None, arena_regions=None, member_regions=None, triggers=None):
    """{trigger flag: reason} -- the sweeps SweepSlot must not nominate from. ShopSlot's
    `location_tags.SHOP_SLOT_SKIPS`, one feature over, and deliberately the same shape: a dict
    keyed by the thing excluded, valued by WHY, so the exclusion is auditable rather than a silent
    filter.

    Three sources, and the split is the point:

    * DERIVED -- a trigger `BOSS_HEALTHBARS` cannot name (absent, or a blank name field). This is
      the honest gate: it does not claim the dungeon has no boss, only that we cannot vouch for one,
      which is the same standard ShopSlot holds a merchant to.
    * DECLARED -- `runtime_sweep_skips()`, for triggers that ARE named and still cannot fire.
      Patches is the confirmed case and cannot be derived; see that dict's comment.
    * AUDIT -- when `arena_regions` is supplied, every trigger absent from that authoritative table.
      The sweep may still pay ordinary members, but it cannot make one of them REQUIRED until the
      arena is audited (#671). `triggers` narrows this to the actual sweep universe; when omitted,
      the healthbar keys are the best available trigger corpus.

    `healthbars` is injectable so the gate is testable without the data module, and so
    tools/build_region_census.py can price the wizard's SweepSlot checkbox off the same expression
    the seed uses -- the single-source rule `nominate_sweep_slots` already documents.

    🛑 If the healthbar table is unavailable we skip only the DECLARED set. Skipping on absence
    would silently empty the surface, and a feature that disables itself when a lookup fails is
    worse than one that stays on: the ladder would widen and nobody would know why.
    """
    skips = runtime_sweep_skips()
    if healthbars is None:
        try:
            from .boss_healthbars import BOSS_HEALTHBARS as _bh  # noqa: PLC0415 -- data leaf
            healthbars = _bh
        except Exception:
            healthbars = None
    if not healthbars:
        return skips
    for flag, info in healthbars.items():
        name = (info[3] if isinstance(info, (tuple, list)) and len(info) > 3 else "") or ""
        if not str(name).strip():
            skips.setdefault(flag, _UNNAMED_TRIGGER_REASON)
    if arena_regions is not None:
        audit_scope = healthbars.keys() if triggers is None else triggers
        for flag in audit_scope:
            if flag not in arena_regions:
                skips.setdefault(flag, _UNAUDITED_TRIGGER_REASON)
    # SPLIT -- when BOTH the arena region and the members' region are known and DISAGREE, the sweep
    # cannot host a SweepSlot: the candidate is a member (members' region), but the trigger boss is
    # fought elsewhere. Ranked last, and it fires only when a caller supplies member_regions, so the
    # narrower gates above still stand alone.
    if arena_regions is not None and member_regions is not None:
        split_scope = healthbars.keys() if triggers is None else triggers
        for flag in split_scope:
            _a = arena_regions.get(flag)
            _m = member_regions.get(flag)
            if _a is not None and _m is not None and _a != _m:
                skips.setdefault(flag, _SPLIT_TRIGGER_REASON)
    return skips


#: The most SweepSlot members one trigger may nominate, reached at a single foreign partner.
#:
#: Measured on #703 (1xER + 1xHK, apworld 0.4.3, 2 seeds per cell, only this knob varying):
#:
#:   N=1  9.6% useful to the partner, 212 nominations, 87 foreign progression absorbed
#:   N=2 14.8%                        422                107
#:   N=4 25.5%                        827                147
#:   N=8 34.3%                       1503                175
#:
#: ⭐ THE FILLER RATE IS FLAT ACROSS THAT SWEEP (10.8 -> 11.4) while useful goes 1.4% -> 7.5%. This
#: is the useful tier being unblocked, not simply more traffic -- and ON-SURFACE STAYS 100% AT EVERY
#: N, so the recovery costs no curation. That is the whole argument for this knob over lowering
#: `confine_foreign_progression`: N=8/confine=100 gives the same useful recovery as N=1/confine=50
#: at FOUR TIMES the curation (34.3% at 100% on-surface vs 35.1% at 23.9%).
#:
#: 🛑 NO PLATEAU BY N=8, so this ceiling is a judgement and not a measured optimum. It is 8 because
#: the curve was measured to 8 and Alaric ruled on that range; raising it further is a new
#: measurement, not a tuning change. The knob also self-saturates -- N=8 yields 1503 nominations
#: rather than 8x212, because many sweeps have fewer than 8 eligible members.
MAX_SLOTS_PER_SWEEP = 8


def slots_per_sweep(n_foreign_players: int) -> int:
    """How many members one sweep may nominate, given how many OTHER players are in the multiworld.

    More slots when there are few partners, exactly one when there are many (#703).

    # The problem this solves

    In a 2-game world the partner holds ~269 progression items and has nowhere to put them but its
    own ~404 locations, so they saturate during `fill_restrictive` and the useful tier is exhausted
    before the scan reaches a partner slot. Our surface is player-agnostic already
    (`foreign_advancement_barred` asks only "is this someone else's progression?"), so the lever is
    not permission -- it is HOW MANY SLOTS EXIST. In an 8-game world that pressure is spread and
    one-per-sweep is right.

    🛑 PURE, AND DELIBERATELY NOT RANDOM. `nominate_sweep_slots`'s own docstring forbids drawing
    here: `world.random` is consumed a different number of times depending on how hard fill works, so
    a draw would move the seed for everything downstream -- and the census must reproduce the
    selection outside a generation at all. This is arithmetic on a count, nothing else.

    🛑 SOLO IS ONE. A lone player has nowhere to send anything, so widening the surface buys nothing
    and would change a solo seed for no reason. `n_foreign_players <= 0` is that case, and it also
    keeps the expression away from a division by zero.

    ⭐ AND MANY-PLAYER SEEDS ARE BYTE-UNCHANGED BY CONSTRUCTION. At `n >= MAX_SLOTS_PER_SWEEP` this
    returns exactly 1, which is the shipped value, so `nominate_sweep_slots` takes the identical
    branch it always did. That is asserted directly rather than left to a seed diff.
    """
    if n_foreign_players <= 0:
        return 1
    return max(1, min(MAX_SLOTS_PER_SWEEP, MAX_SLOTS_PER_SWEEP // n_foreign_players))


def nominate_sweep_slots(sweeps, barred=(), prefer_not_in=(), skips=None, slots=1):
    """{trigger flag: [member ap ids]} -> the set of ap-ids SweepSlot puts on the surface: at most
    `slots` per trigger (1 by default, the shipped behaviour). Pure, AP-free, and THE definition --
    both the world (features/progression_surface.sweep_slot_aps) and the wizard's census tool call
    this.

    `slots` comes from [`slots_per_sweep`] at the world call site (#703). The census cannot know the
    partner count -- it prices the checkbox BEFORE a multiworld exists -- so it asks for both ends
    and the wizard shows the range, the same way it already treats `num_regions` as a draw size
    rather than a final count.

    🛑 SINGLE-SOURCED ON PURPOSE. The second caller is tools/build_region_census.py, which prices the
    SweepSlot checkbox the wizard draws. A re-implementation there would be a number the player reads
    that disagrees with the seed they get -- and this repo has already paid for that class of bug
    twice (the tracker's static surface column, gen_location_regions re-inventing the selection).

    🛑 Triggers in [`sweep_slot_skips`] nominate NOTHING. SweepSlot's premise is that progression
    only lands where a sweep hands it over, so a sweep that cannot fire must not put a check on the
    surface -- bobler cleared 19/19 Limgrave bosses in a boss-sweeps-only seed and still had two
    progression checks open behind triggers that do not exist (#672).

    THE RULE: the lowest ap-id that is not barred and, where possible, not already on the tag surface
    (`prefer_not_in`). Lowest rather than random because `world.random` is consumed a different
    number of times depending on how hard fill works, so drawing here would move the seed for
    everything downstream; and because the pick must be reproducible outside a generation at all --
    the census does exactly that. Skipping the tag surface matters because the six SURFACE-CUTTABLE
    classes are still in the pre-cut member lists, so a naive minimum can nominate a check the
    surface already had, adding a name and no breadth."""
    barred = frozenset(barred)
    prefer_not_in = frozenset(prefer_not_in)
    skips = sweep_slot_skips() if skips is None else dict(skips)
    out = set()
    for _flag, members in sorted((sweeps or {}).items()):
        if _flag in skips:
            # A trigger we cannot assert will fire cannot justify a placement -- see sweep_slot_skips.
            continue
        eligible = sorted(ap for ap in members if ap not in barred)
        if not eligible:
            continue
        fresh = [ap for ap in eligible if ap not in prefer_not_in]
        # Fresh first, then top up from `eligible` -- the tag surface is skipped where possible for
        # the same reason as before (a naive minimum adds a name and no breadth), but a sweep with
        # fewer fresh members than slots still fills them rather than silently under-nominating.
        # Both lists are sorted, so the pick stays lowest-first and reproducible.
        want = max(1, int(slots))
        picked = fresh[:want]
        if len(picked) < want:
            seen = set(picked)
            picked += [ap for ap in eligible if ap not in seen][: want - len(picked)]
        out.update(picked)
    return frozenset(out)


def has_class(tags, selected) -> bool:
    """Does this location carry one of `selected` classes (and none of SURFACE_EXCLUDE_TAGS)?

    The single tag predicate, used by features/progression_surface (the surface = where this world's
    own progression may go). It used to be called `is_big_ticket`,
    which mis-sold it: it was never a concept, just "tags intersect a selection" -- and that name let a
    SECOND selection masquerade as a second mechanism.
    """
    t = set(tags or ())
    sel = set(selected)
    for _cls, _extra in SURFACE_CLASS_EXTRA_TAGS.items():
        if _cls in sel:
            sel = sel | _extra   # the LegacyBoss absorption (see SURFACE_CLASS_EXTRA_TAGS)
    return bool(sel & t) and not (SURFACE_EXCLUDE_TAGS & t)


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
    ContractKey("death_link_amnesty_inbound", "INT", False, (GREENFIELD,),
                "core._options_echo", "er-logic/options.rs parse_death_link_amnesty",
                "one-in-N gate for received DeathLinks; 1 applies every incoming link."),
    ContractKey("death_link_amnesty_outbound", "INT", False, (GREENFIELD,),
                "core._options_echo", "er-logic/options.rs parse_death_link_amnesty",
                "one-in-N gate for local deaths broadcast to the multiworld; 1 sends every death."),
    ContractKey("trap_link", "BOOL_OR_INT", False, (GREENFIELD,),
                "core._options_echo", "er-logic/options.rs parse_trap_link",
                "nonzero = advertise TrapLink after slot-data parse, send locally received trap "
                "items once, and queue compatible inbound linked traps without echoing them."),
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
                "core._options_echo (unit-converted by features/scaling.floor_multiplier)",
                "er-logic/scaling.rs:225 floor_tier_from_multiplier (client reads f64)",
                "minimum enemy-scaling tier, as the HP MULTIPLIER of that tier's ladder rung -- NOT "
                "the option's percent. 0 = no floor; 1.141..3.703 spans the ladder. The client picks "
                "the first tier whose hp >= this value, so sending the raw percent would floor at the "
                "TOP tier. The player-facing percent rides in the top-level legacy copy."),
    ContractKey("completion_scaling_ceiling", "NUMBER", False, (GREENFIELD,),
                "core._options_echo (unit-converted by scaling_ladder.ceiling_multiplier)",
                "er-logic/scaling.rs ceiling_tier_from_multiplier",
                "maximum enemy-scaling tier, as the HP MULTIPLIER of that tier's ladder rung -- the "
                "MIRROR of completion_scaling_floor (last rung NO STRONGER than this, vs the floor's "
                "first rung at least this strong). The top rung (7.422) means uncapped, which is the "
                "default. NOT required: an older client simply never reads it and scales uncapped, "
                "which is why a seed that actually caps also sends requiresClientFeatures."),
    ContractKey("global_scadutree_blessing", "INT", True, (GREENFIELD,),
                "core._options_echo", "scaling.rs scadutree scope",
                "Scadutree blessing MODE, DERIVED from scadutree_blessing_scope + dlc_blessing_catchup (the single global_scadutree_blessing Choice was split 2026-08-06 and is now a deprecated alias). 0 = off. 1 = anywhere. 2 = anywhere + DLC catch-up floor. 3 = dlc_only + catch-up -- vanilla scope, but a DLC area never runs under its expected blessing. 3 is the ONLY new value; a client that predates it falls through `mode != 1 && mode != 2` and writes nothing, which is why a mode-3 seed declares requiresClientFeatures ['dlc_blessing_catchup']."),
    ContractKey("auto_upgrade", "INT", True, (GREENFIELD,),
                "core._options_echo (features/upgrades.py)", "upgrades.rs set_auto_upgrade / apply_auto_upgrade",
                "auto-upgrade received weapons: 0 = off; nonzero = raise each received weapon to the "
                "player's highest held level on its smithing track (raise-only, cap +25 normal / +10 somber)."),
    ContractKey("auto_equip", "BOOL_OR_INT", False, (GREENFIELD,),
                "core._options_echo (features/auto_equip.py)", "er-logic/options.rs parse_auto_equip",
                "\"use what you get\": nonzero = the client equips every RECEIVED weapon / armour piece "
                "the moment it lands in the bag, clobbering the slot (auto_equip.rs enqueue + tick). "
                "NOT required: this key is younger than the released clients that read it, and an "
                "absent key parses false, which is exactly the off default. That silence is also why "
                "a seed with it ON emits requiresClientFeatures [\"auto_equip\"] -- OPTIONS_SUBKEYS is "
                "not folded into CONTRACT_HASH, so an older client would report VERSION: OK and then "
                "never see this key at all."),
    ContractKey("reveal_sweep_boss_names", "BOOL_OR_INT", False, (GREENFIELD,),
                "core._options_echo", "core.rs tracker sweep presentation",
                "default-off presentation preference: allow the tracker to name sweep bosses whose "
                "rows would otherwise be hidden behind a locked region. Does not change sweep "
                "membership, firing, placement, or logic; opted-in seeds require the matching "
                "client feature tag."),
    ContractKey("goal_region_unlock_policy", "INT", False, (GREENFIELD,),
                "core._options_echo (features/progression_surface.py)",
                "eldenring-archipelago/core.rs -> region completion goal gate",
                "0 = preserve the possession-based goal-region unlock; 1 = wait until every "
                "progression-surface check in every required non-goal region is checked, with "
                "visible shop rows additionally satisfied by the server-backed viewed-shop ledger; "
                "2 = impose no region-side goal requirement. This is independent of the Great "
                "Rune requirement. "
                "A seed selecting 1 emits requiresClientFeatures "
                "['region_completion_goal_gate']; OPTIONS_SUBKEYS is not folded into CONTRACT_HASH."),
    ContractKey("no_equip_load", "INT_OR_BOOL", False, (GREENFIELD,),
                "core._options_echo (features/body_tuning.py)", "no_equip_load.rs set_enabled",
                "ROLL MODE, not a plain toggle (widened 2026-08-12, #548): 0 = off, 1 = light "
                "(equipment weighs nothing, always light roll), 2 = medium (ceiling raised enough "
                "that no real kit fat-rolls, but armour still costs you). The client multiplies the "
                "WEIGHT side with a silent permanent SpEffect because max equip load is recomputed "
                "every frame from Endurance; er-logic/equip_load.rs RollMode owns the multipliers. "
                "1 is what the legacy Toggle's `true` put on the wire, which is why light is 1. "
                "NOT required, and the asymmetry is deliberate: the capability is OLDER than every "
                "released client, an absent key parses false, and 0/1 are read CORRECTLY by an old "
                "client -- so tagging them would refuse the connect on clients that already "
                "implement the feature. 2 is different: parse_bool_option turns it into a nonzero "
                "and the player silently gets LIGHT, the stronger setting they did not ask for, so "
                "a seed choosing 2 -- and only 2 -- emits requiresClientFeatures "
                "[\"no_equip_load_roll\"]."),
    ContractKey("no_fall_damage", "BOOL_OR_INT", False, (GREENFIELD,),
                "core._options_echo (features/body_tuning.py)", "no_fall_damage.rs set_enabled",
                "nonzero = falling deals no damage (leaving the map still kills). Same age and same "
                "no-tag reasoning as no_equip_load above."),
    ContractKey("merchant_bells_on_talk", "BOOL_OR_INT", False, (GREENFIELD,),
                "core._options_echo (features/merchant_bells.py)",
                "er-logic/options.rs parse_merchant_bells_on_talk -> merchant_bells.rs on_shop_open",
                "nonzero = opening a merchant's regular buy menu sets the event flag the Twin "
                "Maiden Husks would have set had you handed them that merchant's Bell Bearing, so "
                "their wares are on sale at the hub from then on. The bell ITEM is untouched and "
                "stays in the pool -- the range a shop-open reports is the merchant's OWN "
                "ShopLineupParam block, and a hand-in adds a menu entry rather than releasing or "
                "copying stock, so every shop check keeps its own eventFlag_forStock and fires "
                "identically whichever counter it was bought at. The (range -> flag) table is "
                "static game data baked into the client by tools/gen_merchant_bells.py, NOT sent. "
                "NOT required: an absent key parses false, which is the off default. A seed with "
                "it ON emits requiresClientFeatures [\"merchant_bells_on_talk\"] -- "
                "OPTIONS_SUBKEYS is not folded into CONTRACT_HASH, so an older client would report "
                "VERSION: OK and then never see this key at all."),
    ContractKey("flatten_regular_upgrades", "INT", True, (GREENFIELD,),
                "core._options_echo (features/upgrades.py)", "upgrades client path",
                "standard-weapon stones/level: 0 = off (vanilla 2/4/6), 1..4 = uniform N/level (tuned ~3)."),
    ContractKey("locked_abilities", "STR_LIST", False, (GREENFIELD,),
                "core._options_echo (features/ability_lock.py)", "er-logic/options.rs parse_ability_lock",
                "abilities the seed disables at the game's LOGICAL action layer "
                "(CSChrActionRequestModule.disabled_action_inputs): any of jump, crouch, roll, r1, "
                "r2, l1, l2. Keybind- and device-agnostic; menus unaffected. Emitted as a sorted "
                "name list (empty = nothing locked). NOT required: an absent key parses to the empty "
                "set, which is the off default -- OPTIONS_SUBKEYS is not folded into CONTRACT_HASH, "
                "so this key adds no version pairing and an older client simply never reads it."),
    ContractKey("coop_difficulty", "INT", False, (GREENFIELD,),
                "core._options_echo (features/scaling.py)",
                "er-logic/options.rs parse_coop_difficulty -> scaling.rs coop_tier_bump",
                "seamless-co-op difficulty: extra enemy-scaling TIERS added per co-op partner in the "
                "world, on top of the region's own tier (#993). 0 (default) = off. Seamless raises "
                "enemy HP but leaves enemy DAMAGE at the host default, so a partner halves incoming "
                "threat without enemies hitting harder; a higher tier carries both HP and attack, "
                "restoring it. Each client counts its own phantom census and applies this "
                "identically -- every player is on its own AP slot reading the same world, so no host "
                "arbitration. NOT required: an absent key parses 0 (off), and OPTIONS_SUBKEYS is not "
                "folded into CONTRACT_HASH, so this adds no version pairing and an older client "
                "simply never reads it -- it also needs no requiresClientFeatures, because a client "
                "that ignores it merely plays at the un-bumped (current) co-op difficulty."),
    ContractKey("scale_rune_rewards", "INT", False, (GREENFIELD,),
                "core._options_echo (features/scaling.py)",
                "er-logic/options.rs parse_bool_option -> rune_rewards.rs",
                "opt-in direct rune payout scaling (#1091): NpcParam.getSoul and GameAreaParam "
                "boss rewards follow the current sphere tier. 0 (default) = vanilla payouts. "
                "Golden Rune goods are never in scope. An enabled seed declares "
                "requiresClientFeatures [\"rune_reward_scaling\"] so an older client refuses "
                "instead of silently ignoring the economy setting."),
    ContractKey("region_sync", "BOOL_OR_INT", False, (GREENFIELD,),
                "core._options_echo (features/region_sync.py)",
                "er-logic/options.rs parse_region_sync -> region_sync.rs apply_pending",
                "seamless-co-op region sharing (#1005): nonzero = advertise the RegionSync link "
                "tag, broadcast this slot's region-OPENS to that group, and apply everyone else's "
                "by setting the region's regionOpenFlags value and lighting its graces -- the same "
                "write a locally received Lock makes, and exactly what the console's `!setflag "
                "<region open flag> 1` does today. ACCESS ONLY: it does NOT grant the AP region-Lock "
                "ITEM to anyone (Fill's placement is untouched), does not move the receive "
                "watermark, sends no check, and changes no logic or goal state -- so generation is "
                "identical whether it is on or off. NOT required: an absent key parses false, which "
                "is the off default. A seed with it ON emits requiresClientFeatures "
                "[\"region_sync\"], because OPTIONS_SUBKEYS is not folded into CONTRACT_HASH and an "
                "older client would report VERSION: OK and then leave its player region-kicked out "
                "from under the party -- which reads as a broken seed, not an old client."),
)


# ---------------------------------------------------------------------------------------------------
# THE CONTRACT. Order = logical grouping. `required` applies within the key's own profiles.
# ---------------------------------------------------------------------------------------------------
CONTRACT = (
    # --- received-item + location detection (core) ---
    ContractKey("apIdsToItemIds", "SCALAR_INT_MAP", True, (BOTH,),
                "core._base_slot_data", "core.rs:309 i64_map",
                "AP item id (str) -> ER FullID granted on receipt."),
    ContractKey("abilityUnlockItems", "STR_MAP", False, (GREENFIELD,),
                "features/ability_lock.py (progressive mode)", "er-logic ability_lock receive path",
                "synthetic AP item id (str) -> ability name (jump/crouch/roll/r1/r2/l1/l2). Present "
                "only under ability_lock_mode: progressive: the abilities start locked (options."
                "locked_abilities) and each rides one shuffled 'Unlock: X' item; receiving that item "
                "id unlocks the ability (er_logic ability_lock::unlock). Same shape as armorBundles -- "
                "the game is never asked to grant these, the client resolves them by this map. A seed "
                "that emits it also emits requiresClientFeatures ['ability_unlock']."),
    ContractKey("armorBundles", "LISTVAL_INT_MAP", False, (GREENFIELD,),
                "features/armor_bundles.py", "core.rs armor-bundle receive reconciler",
                "synthetic armor-set AP item id (str) -> every protector FullID in its generated family."),
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
                "MUST be exactly '<Region> Lock' matching the coarse lock-item names the client "
                "derives from regionCoarseKeys. Usually the region's front-door GRACE, so the Lock "
                "lights the way in; for a gated child (region_spine.REGION_PARENT) it is a SYNTHETIC "
                "client-owned flag instead, because there the same write must disarm the kick "
                "WITHOUT lighting a warp target past the vanilla wall (#278)."),
    ContractKey("lockHintPlacements", "LOCK_PLACEMENTS", False, (GREENFIELD,),
                "core.fill_slot_data (post-fill)", "lock_hint_economy::parse_placements",
                "Lock item NAME -> {player, location}, where player owns the world containing the "
                "location. Emitted after fill for this receiving slot's placed region Locks only. "
                "This narrow coordinate disclosure lets the custom F6 economy call CreateHints for "
                "a Lock in another game without spending normal AP hint points. Missing for old "
                "seeds degrades to the client's Spilled/use-!hint fallback."),
    # --- the tracker's region model, SENT rather than BAKED (2026-07-28) -------------------------
    # These two replace er-logic's generated `tracker_regions.rs`, and the reason is correctness
    # before convenience. That table was built from data.LOCATIONS at GENERATOR time, so it
    # described the DEFAULT seed -- but `_base_slot_data` scopes locationFlags and regionOpenFlags
    # to `kept`, and under num_regions the kept set is a per-seed subset. A baked table is a CORPUS
    # fact standing in for a SEED fact, which is the same shape as the num_regions bug that voided
    # "the item exists" claims. Sent, it is right for every seed; baked, it was right for one.
    # (It also retires a class of client commit: every apworld region/tag change used to require a
    # regenerated .rs pushed to the client repo, and the world CI's cross-repo diff gate to notice
    # when it had not been.)
    ContractKey("locationRegions", "LISTVAL_INT_MAP", False, (GREENFIELD,),
                "core._base_slot_data", "er-logic tracker_tables::location_region_table",
                "fine region NAME -> [AP location ids in it]. The tracker's grouping. Scoped to "
                "THIS seed's kept regions + the hub, exactly like locationFlags -- a location "
                "absent here is not in this seed. Sent region->ids rather than id->region because "
                "the id list is the bulk and the names repeat (~43 KB vs ~180 KB)."),
    ContractKey("regionCoarseKeys", "STR_MAP", False, (GREENFIELD,),
                "core._base_slot_data", "er-logic tracker_tables::coarse_table",
                "fine region NAME -> COARSE key: the region whose lock decides in-logic. \"\" means "
                "ALWAYS ACCESSIBLE (the hub). Usually the region itself; it differs only for a "
                "LOCKLESS region whose physical space is gated by another region's lock (the finale "
                "-> its host). 🛑 SENT, not derived client-side: which region hosts a lockless one "
                "is OUR design decision, and re-deriving it in Rust would be a second copy of a "
                "convention free to drift from this one."),
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
    ContractKey("scaduBlessingCap", "INT", False, (GREENFIELD,),
                "features/scaling.py", "er-logic/upgrades.rs apply_blessing_cap",
                "Ceiling (0..20) for the Scadutree-blessing curve. Emitted only when "
                "the blessing mode != 0. 🛑 ABSENT MEANS 'no extra cap' -> the client falls "
                "back to the ladder ceiling (20), NOT to 0: a key that read as the floor when absent "
                "would ship the whole feature inert, which is the exact bug this option already had "
                "once. Exists so the client never has to re-derive the seed's tier model."),
    ContractKey("dlcScadutreeFloorRanges", "TRIPLE_LIST", False, (GREENFIELD,),
                "features/scaling.py", "eldenring-archipelago/upgrades.rs floor_for_region (mode 2)",
                "[[lo,hi,floor], ...] play_region/100 sub-id ranges -> Scadutree-blessing FLOOR level "
                "(0..20) per DLC region. Emitted ONLY when the blessing mode is 2 or 3 (dlc_blessing_catchup on) and >=1 DLC "
                "region is kept. Client mode-2 writes max(held-fragment level, region floor) so DLC "
                "enemies' blessing assumption is met on arrival. "
                "🛑 This key is NOT a DLC-region marker -- use dlcRegionBuckets. The client used to "
                "infer DLC-ness from its presence, which is false on every default seed (blessing has "
                "defaulted to `off` since 2026-07-18). (The old claim that 'the enemy 70xx sphere "
                "scaler is capped in these buckets' was also stale: DLC_ENEMY_TIER_CAP was removed "
                "2026-07-15 and DLC now scales by sphere exactly like base game.)"),
    ContractKey("requiresClientFeatures", "STR_LIST", False, (GREENFIELD,),
                "features/*.slot_data (only when a feature is actually USED)",
                "er-logic/client_features.rs unsupported() -> core.rs connect refusal",
                "feature tags this SEED depends on the client understanding. Absent/[] = connects to "
                "anything. THE GAP IT CLOSES: the `versions` contract-hash check folds in CONTRACT "
                "but NOT OPTIONS_SUBKEYS, so adding a client-consumed OPTION does not move the hash "
                "-- an older client reports 'VERSION: OK' and then silently cannot see the key, and a "
                "setting the player chose evaporates. Hashing the options sub-dict instead would "
                "fire on every harmless addition and train people to ignore it, so a seed declares "
                "only what it USES. Add a tag to er-logic SUPPORTED in the same change as the "
                "behaviour, never before."),
    ContractKey("dlcRegionBuckets", "INT_LIST", False, (GREENFIELD,),
                "features/scaling.dlc_region_buckets", "er-logic/scaling.rs is_dlc_bucket",
                "sorted play_region/100 sub-ids belonging to KEPT DLC regions -- a pure membership "
                "set, derived from the region set and independent of every option. Absent when no "
                "DLC region is in play. This is the ONLY correct 'is this bucket DLC?' signal; it "
                "exists because the previous proxy (dlcScadutreeFloorRanges) is empty by default."),
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
                "features/area_locks.py", "region.rs:121 str_to_u32vec",
                "'<Region> Lock' -> map-reveal/enforcement flags set on lock receipt, IN WIRE "
                "ORDER (both client application sites iterate the parsed Vec in order). Emitted "
                "for the DLC map pieces and, since SPEC-ashen-capital-lock, for the Ashen Capital "
                "Lock's Erdtree-burn world state -- where the ORDER IS LOAD-BEARING: the burn-done "
                "latch must be LAST, because it is common.emevd $Event(900)'s own entry check and "
                "setting it first makes the event skip the body that places the Elden Beast's "
                "arena. A partial grant must therefore leave it unset, so the reconnect replay "
                "can finish the job."),
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
    # SPEC-ashen-capital-lock (2026-08-06): the WORLD-STATE half of $Event(900). Independently
    # optional -- a client that does not know these keys still gets the burn, because the same
    # flags ride lockRevealFlags and simply latch instead of being held by position.
    ContractKey("capitalWorldBurnFlag", "INT", False, (GREENFIELD,),
                "features/capital.py", "er-logic capital.rs via region.rs tick_capital",
                "the world's post-burn state flag, 300 -- common.emevd:1293 is its SOLE setter in "
                "all 589 EMEVD, and it is READ in five maps plus the Roundtable Hold. Measured in "
                "game 2026-08-06: without it the Elden Beast's arena in m19_00 is a VOID the "
                "player falls into and dies in; with it, the hub is in its burnt state. Held by "
                "POSITION alongside capitalBurnFlag (ON in the ashen buckets, OFF elsewhere) so "
                "the rest of the world stays vanilla -- it is reversible, measured, not one-way."),
    ContractKey("capitalPreBurnFlag", "INT", False, (GREENFIELD,),
                "features/capital.py", "er-logic capital.rs via region.rs tick_capital",
                "the OPPOSITE world state, 302 -- set by $Event(901) (the Melina/Forge ceremony, "
                "alongside flag 110) and cleared by the burn's own body. Written OFF only where "
                "the burn state is written ON; never touched elsewhere."),
    ContractKey("capitalReleaseRows", "TRIPLE_LIST", False, (GREENFIELD,),
                "features/capital.py", "shop_flags.rs run_capital_release",
                "[ShopLineupParam row, expected release flag, replacement] -- shop-check rows "
                "whose eventFlag_forRelease is 9116 itself (Enia's Maliketh armor set) re-key to "
                "the monotonic 118 so the reconciler's OFF-default cannot de-stock them."),
    # --- graces ---
    ContractKey("graceAttunement", "ANY", False, (GREENFIELD,),
                "features/graces.py", "region.rs parse_grace_attunement / tick_grace_attunement",
                "'<Region> Lock' -> {threshold, members, bloom}: touch `threshold` of `members` "
                "(the region's grace warp flags minus the one its Lock already lit) and `bloom` "
                "lights. ABSENT for every region the apworld chose not to gate -- the off default "
                "(grace_attunement 0) and the small-region skip (members <= threshold), both of "
                "which keep the whole-bundle behaviour regionGraces has always had. A seed that "
                "emits this also emits requiresClientFeatures ['grace_attunement']: unread, the key "
                "leaves the player ONE grace per region with the rest never lighting, which reads "
                "as a broken seed rather than an ignored setting."),
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
    ContractKey("goalRequiredItems", "STR_LIST", False, (GREENFIELD,),
                "features/goal_locations.py", "goal.rs parse -> item_goals",
                "Item names the player must HOLD before Goal may be sent -- this seed's kept Region "
                "Locks, minus the precollected start anchor. THE POINT: core.set_rules already tells "
                "Archipelago the slot completes on has_all(kept locks), but goal.rs is_met() used to "
                "check the goal BOSS FLAGS ALONE, and the client's send is what actually ends the "
                "run. Because region_access is warp (every kept region sits at sphere ~1), fill may "
                "legitimately place the terminal region's Lock in sphere 0 -- measured 2026-07-30: on "
                "25% of rolled draws the goal region was the SECOND region opened, so the run ended "
                "there while the world still claimed every lock was required. This key makes the two "
                "terminal conditions ONE. Absent under natural_progression, which mints no Lock items "
                "at all (its regionOpenFlags keys are '<Region> Lock' NAMES with no item behind them "
                "-- deriving this client-side from those keys would deadlock np seeds)."),

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
    ContractKey("checkLotZeroMap", "LISTVAL_INT_MAP", False, (GREENFIELD,),
                "features/check_lots.py", "check_lots.rs (ItemLotParam_map, non-goods repoint)",
                "ItemLotParam_MAP lot id (str) -> the NON-GOODS slot indices (weapon/armor/talisman/gem) "
                "holding a check's vanilla ware. The client REPOINTS these slots at apPlaceholderGoods, "
                "writing the slot's lotItemCategory (=1, goods) alongside the id -- which is what makes a "
                "GOODS row legal where a weapon sat, and is why the old 'category mismatch' objection no "
                "longer holds. Suppressing at the source is grant-path- and flag-timing-independent, "
                "closing the leak the id-keyed suppressor left on enemy/scarab/scripted overworld drops. "
                "ONE-TIME (flagged) lots only, so it never eats a farmable source. "
                "KEY NAME IS HISTORICAL: these slots were once ZEROED (lotItemId=0, lotItemNum=0). That "
                "removed the pickup, and the pickup IS the check, so it silently killed every gear chest, "
                "scarab drop and boss drop. Fixed client-side 1121d93, confirmed in-game 2026-07-24. The "
                "key is not renamed because that would break connect for a seed rolled on an older "
                "apworld; do NOT restore the zeroing this name implies."),
    ContractKey("checkLotZeroEnemy", "LISTVAL_INT_MAP", False, (GREENFIELD,),
                "features/check_lots.py", "check_lots.rs (ItemLotParam_enemy, zero)",
                "Same as checkLotZeroMap for ItemLotParam_ENEMY (boss / enemy one-time drops). SEPARATE "
                "table for the same reason as checkLotBlankEnemy: a lot id can live in both tables."),
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
    ContractKey("mineMaterialRoll", "SCALAR_INT_MAP", False, (GREENFIELD,),
                "features/mine_materials.py", "mine_materials.rs configure/run",
                "Unflagged repeatable ItemLotParam_map lot id (str) -> replacement GOODS row id. "
                "Only the 11 placed ordinary mine-material templates are eligible. Slot quantity, "
                "pickup/respawn behavior, flags, AP location count, and capstones remain untouched."),
    ContractKey("shopInfiniteStock", "LISTVAL_INT_MAP", False, (GREENFIELD,),
                "features/shop_stock.py", "shop_stock.rs configure/run",
                "ShopLineupParam row id (str) -> [goodsId, equipType(=3), price]. The browsable "
                "UNLIMITED goods shelves (mtrlId -1, costType 0, sellQuantity -1, ungated, "
                "stock-flagged) -- 14 rows since 2026-07-29, rerolled per seed to a consumable. The "
                "previous 455-row set was the Alter-Garments / AoW-duplication / debug rows, which are "
                "MENUS, not shelves, and rerolling them corrupted those menus. The PRICE rides along, "
                "derived from the item itself, or a cheap shelf becomes an infinite dispenser. "
                "Absent/empty = shelves stay vanilla."),
    ContractKey("shopRunePrices", "SCALAR_INT_MAP", False, (GREENFIELD,),
                "features/rune_pricing.py", "shop_prices.rs configure/run",
                "ShopLineupParam row id (str) -> price override. Alt-currency altar rows always map "
                "to 1, preserving their costType while preventing random rewards from demanding an "
                "absurd number of Dragon/Bayle Hearts. Other entries are CHECK rows whose reward is a rune "
                "item (Golden/Numen's/Hero's/Lord's Rune). A shop check keeps the price of the ware "
                "it USED to sell, so a slot that cost 3500 can end up selling a Golden Rune [1] worth "
                "~200 -- the reward is randomised but its cost is not, which makes the slot strictly "
                "bad rather than a gamble. Rolled per seed in [0, 2x the rune's own derived worth] "
                "(GOODS_PRICE, the same basicPrice/sellValue*10 chain shop_stock prices its rerolls "
                "with), so buying one is sometimes free and sometimes a bad trade. Absent/empty = "
                "every row keeps its vanilla price."),
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
                "features/scaling.py (NOT a duplicate: this is the player-facing PERCENT)",
                "(no client consumer; the client reads options.completion_scaling_floor)",
                "the raw yaml PERCENT (0..100) the player set -- a different UNIT SPACE from the "
                "same-named options.* key, which carries the HP multiplier the client parses. "
                "Informational / spoiler-side only. Do not 'unify' the two without reading "
                "features/scaling.floor_multiplier first."),
    # RETIRED 2026-07-31: the top-level `global_scadutree_blessing` duplicate. Nothing ever read it
    # -- the only consumer, client core.rs, goes through `/options/global_scadutree_blessing` -- and
    # a second key with the same name in a different scope is exactly the trap the two
    # `completion_scaling_floor` keys above are annotated to avoid. Removed here, in scaling.py's
    # emitter, and from the client's slot_data fixture in the same change. CONTRACT_HASH moves; it
    # was moving anyway for scaduBlessingCap, so the removal rides along for free.
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
                "core._base_slot_data", "goal.rs parse",
                "EFFECTIVE (clamped) Great Rune requirement for the great_runes ending."),
    ContractKey("great_rune_items", "STR_LIST", False, (GREENFIELD,),
                "core._base_slot_data", "goal.rs parse",
                "Eligible Great Rune item NAMES; goal.rs requires great_runes_required distinct names "
                "from this set before Goal can fire. WAS a "
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
    L.append(_RUST_TESTS)
    return "\n".join(L) + "\n"


_RUST_VALIDATE = r'''fn is_int(v: &Value) -> bool { v.is_i64() || v.is_u64() }

fn nested_grant_ok(e: &Value) -> bool {
    let Some(o) = e.as_object() else { return false };
    if o.len() == 1 && o.get("noop").is_some_and(|v| v.as_bool() == Some(true)) {
        return true;
    }

    let flags = o.get("flags").and_then(|v| v.as_array());
    let flags_ok = flags.is_some_and(|v| v.iter().all(is_int));
    let goods = o.get("goods");
    match goods {
        Some(goods) => {
            flags_ok && is_int(goods) && o.get("consumed").is_some_and(Value::is_boolean)
        }
        None => {
            flags.is_some_and(|v| !v.is_empty()) && !o.contains_key("consumed")
        }
    }
}

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
            o.values().all(|l| l.as_array().is_some_and(|l| l.iter().all(nested_grant_ok)))
        }),
        Shape::FlaskLadder => v.as_array().is_some_and(|a| {
            a.iter().all(|e| e.get("charges").is_some_and(is_int)
                && e.get("potency").is_some_and(is_int))
        }),
        Shape::OptionsDict => v.is_object(),
        Shape::LockPlacements => v.as_object().is_some_and(|o| o.iter().all(|(name, p)| {
            !name.is_empty() && p.as_object().is_some_and(|p| {
                p.len() == 2
                    && p.get("player").and_then(Value::as_u64).is_some_and(|n| n > 0)
                    && p.get("location").and_then(Value::as_i64).is_some_and(|n| n > 0)
            })
        })),
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


_RUST_TESTS = r'''#[cfg(test)]
mod nested_grants_tests {
    use super::*;
    use serde_json::json;

    fn valid(v: Value) -> bool { shape_ok(Shape::NestedGrants, &v) }

    #[test]
    fn accepts_every_wire_shape_the_world_emits() {
        assert!(valid(json!({"Flask": [{"noop": true}]})));
        assert!(valid(json!({"Bell": [{"flags": [280080]}]})));
        assert!(valid(json!({"Flask": [{"goods": 10020, "flags": [], "consumed": true}]})));
        assert!(valid(json!({"Bell": [{"goods": 8101, "flags": [280080], "consumed": false}]})));
    }

    #[test]
    fn rejects_partial_or_ambiguous_effect_rungs() {
        assert!(!valid(json!({"Flask": [{"goods": 10020, "flags": []}]})),
                "goods must explicitly say whether they are consumed");
        assert!(!valid(json!({"Bell": [{"flags": []}]})),
                "an empty flags-only rung has no effect");
        assert!(!valid(json!({"Bell": [{"flags": [280080], "consumed": false}]})),
                "consumed is meaningless without goods");
        assert!(!valid(json!({"Flask": [{"noop": true, "flags": []}]})),
                "noop is an exact one-field sentinel");
    }
}'''



# ---- VERSION HANDSHAKE -----------------------------------------------------------------------------
# CONTRACT_HASH is derived FROM the contract, not maintained beside it: any key added/removed/reshaped
# or any required-ness flip changes it automatically. A hand-bumped version number is a thing people
# forget; a derived one cannot go stale. (Same doctrine as the gen-input stamp.)
import hashlib as _hashlib

APWORLD_VERSION = "0.6.0"

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
