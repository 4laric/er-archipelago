"""Closed-loop COVERAGE GATE (hand-authored -- NOT generated; do not run gen_data on this file).

A gen-time invariant that joins the apworld's OWN source tables and asserts, for every location
this seed EMITS (post option-filtering), that the location is

  (a) DETECTABLE   -- it carries a real acquisition flag present in the client's flag-poll table
                      (slot_data locationFlags) / shop-stock table (shopRowFlags), valid, not
                      aliased to another live location, and disjoint from the system flags the
                      client itself writes (region-open + grace warp flags, map-reveal flags, the
                      deathlink-kill flag, the underground view flag);
  (b) SUPPRESSED   -- if it vanilla-holds a ware, a suppression mechanism exists so the vanilla
                      ware is not handed out alongside the AP-placed item. Since the 2026-07
                      runtime-param-rewrite suite suppression is STATIC + layered:
                        * GOODS wares are blanked AT THE LOT: the check's flag has an ItemLotParam
                          row in check_lots_table.json map/enemy, whose goods slots the client
                          repoints at AP_PLACEHOLDER_GOODS (features/check_lots.py ->
                          checkLotBlankMap/Enemy; er-logic static_lots.rs for foreign apworlds);
                        * WEAPON/ARMOR/TALISMAN/AoW wares are suppressed BY FullID
                          (check_lots_table.json "items" -> the client's checkItemFlags path);
                        * non-farmable wares are ALSO armed per-seed by
                          features/check_item_flags.py (checkItemFlags), which deliberately skips
                          REPEATABLE_GOODS (suppressing a farmable id eats every legitimate copy);
                        * SHOP checks deliver the vanilla ware as the purchase itself
                          (eventFlag_forStock detection; the AP item rides along).
  (c) REGION-CONSISTENT -- every source file that claims a region for the location agrees
                      (data.py / boss_data.py / boss_sweeps.py / region_graces.py /
                      shop_data.SHOP_LOC_REGION), the location's region has a valid
                      REGION_OPEN_FLAGS entry AND measured REGION_PLAY_IDS kick geometry, and
                      every boss-sweep gate sweeps only members whose canonical region matches
                      (the Full Moon Queen class);
  (d) AWARDED     -- the game can actually SET the flag: a non-shop check's flag must be carried
                      by an ItemLotParam row that hands something out (check_lots_table.json
                      map/enemy/items -- derived from the params, tools/gen_check_lots_table.py).
                      A flag with no awarding lot is unobtainable BY CONSTRUCTION: the flag-poll
                      can never observe it, the seed can never be 100%'d, and a progression item
                      placed there is a multiworld soft-lock (the phantom/synthetic-flag class:
                      177 and 320820, promoted from the monitored FOREIGN-gap 2026-07-14).

DESIGN (mirrors contract.py's single-source style; re-derivation of the orphaned
agent/coverage-gate branch, 12c1727, against the 2026-07-14 tree):
  * ``LocationCoverage``  -- the canonical per-location record (detection / suppression / region +
    region_claims across EVERY claimant + field->source provenance).
  * ``build_coverage(world=None, kept=None)`` -- JOINS the source tables for every emitted
    location. With a live ``world`` the scope is HUB + world._kept() and the emitted tables come
    from world.fill_slot_data(); with world=None it runs in STATIC mode (all regions, or an
    explicit pinned ``kept`` subset) and the tables are re-derived from the generated source
    files, so the seed-invariant data holes are caught without spinning a multiworld.
  * ``check_detection`` / ``check_suppression`` / ``check_region_consistency`` -- collect-ALL
    checks (every violation with provenance, never one-per-gen).
  * ``report_coverage(world=None, kept=None)`` -- runs all checks, returns the violation table
    WITHOUT raising (REPORT MODE -- tools/gen_coverage_report.py and the test tiers).
  * ``assert_coverage(world)`` -- the RAISING variant (CoverageError), WIRED into core.post_fill
    since 2026-07-14 (it debuted in report mode, soaked to a zero baseline, then flipped -- see
    core.py). A violation kills the seed before anything is spent on it.
  * structured degradation lives in ``coverage_quarantine.py`` (QUARANTINE / ACCEPTED_LEAKS),
    self-cleaning via ``_quarantine_violations``.

Flag-validity ranges are grounded, not invented: the region/grace open-flag group is 71xxx-76xxx
(region_open_flags.py; memory er-event-flag-validity), the map-reveal flags are the 62xxx set
mirrored from gen_data.py:132 / startgrants.rs, the deathlink-kill flag is 76996 (region locks
moved OFF it to 7697x, 2026-07; it is deathlink-only now) and the underground view flag is 82001
(features/start_grace.py). General acquisition flags span many allocated groups, so the general
predicate only rejects the provably-bad (<=0, or a system flag a check must never reuse) rather
than inventing a tight range that would false-positive on the ~4.8k real derived flags.
"""

import importlib
import json
import os
import sys

# ---------------------------------------------------------------------------------------------------
# module loading -- works both as a package submodule (relative import, the installed world) and
# standalone by file path (static report run from the source tree). Never raises: a missing generated
# file degrades to an empty table and surfaces as violations, not a crash.
# ---------------------------------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_PATH_CACHE = {}


def _load(modname):
    """Import a sibling module. Prefer the CANONICAL already-imported module (sys.modules) when the
    world is installed -- so a caller that mutates e.g. coverage_quarantine sees the same object --
    then the package-relative import, then a file-path fallback (source-tree static run)."""
    if __package__:
        fq = __package__ + "." + modname
        mod = sys.modules.get(fq)
        if mod is not None:
            return mod
        try:
            return importlib.import_module("." + modname, __package__)
        except Exception:
            pass
    if modname in _PATH_CACHE:
        return _PATH_CACHE[modname]
    path = os.path.join(_HERE, modname + ".py")
    if not os.path.isfile(path):
        return None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("gf_cov_" + modname, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _PATH_CACHE[modname] = mod  # memoized: mutations (ledger tests) see ONE canonical object
        return mod
    except Exception:
        return None


def _load_static_table():
    """check_lots_table.json -- the STATIC suppression authority (tools/gen_check_lots_table.py).
    {"placeholder_goods": 8852,
     "map"/"enemy": {"<flag>": {"lot": <lot>, "slots": [1..8]}},   # GOODS blanked at the lot
     "items":       {"<flag>": [<FullID>, ...]}}                    # weapon/armor/talisman/AoW by id
    Returns ({}, {}, {}) when absent (every ware-bearing location then reports unsuppressed --
    loud, which is correct: without this table the client's static path is INERT)."""
    path = os.path.join(_HERE, "check_lots_table.json")
    try:
        with open(path, encoding="utf-8") as fh:
            t = json.load(fh)
        return ({int(k): v for k, v in t.get("map", {}).items()},
                {int(k): v for k, v in t.get("enemy", {}).items()},
                {int(k): [int(i) for i in v] for k, v in t.get("items", {}).items()})
    except Exception:
        return {}, {}, {}


# ---------------------------------------------------------------------------------------------------
# grounded flag families (cited in the module docstring). Module-level so tests can introspect them.
# ---------------------------------------------------------------------------------------------------
MAP_REVEAL_FLAGS = frozenset({
    62010, 62011, 62012, 62020, 62021, 62022, 62030, 62031, 62032, 62040, 62041,
    62050, 62051, 62052, 62060, 62061, 62062, 62063, 62064,
    62080, 62081, 62082, 62083, 62084,
})
DEATHLINK_KILL_FLAG = 76996
UNDERGROUND_VIEW_FLAG = 82001
REGION_FLAG_LO, REGION_FLAG_HI = 71000, 76999

_GOODS_CATEGORY = 0x40000000
_ROW_ID_MASK = 0x0FFFFFFF

SUPPRESS_KINDS = ("lot_blank_map", "lot_blank_enemy", "static_item_ids",
                  "client_intercept", "shop_stock", "vanilla_identical")


def region_open_flag_valid(flag) -> bool:
    """A region-open flag is only real if it sits in the 71xxx-76xxx region/grace group (the
    Stormveil placeholder-200 class this check exists to reject; the gap itself was fixed when the
    region locks moved off the 76996 collision to real 7697x flags)."""
    return isinstance(flag, int) and REGION_FLAG_LO <= flag <= REGION_FLAG_HI


def detection_flag_valid(flag, system_flags) -> bool:
    """Valid iff a positive int inside u32 AND not a system flag the client itself writes (a check
    keyed on one would fire on region unlock / map reveal / deathlink, not on pickup). We
    deliberately do NOT invent a tight allocated range for the general case -- the ~4.8k derived
    flags span many real game groups and a made-up bound would false-positive on real data."""
    return isinstance(flag, int) and 0 < flag < (1 << 31) and flag not in system_flags


# ---------------------------------------------------------------------------------------------------
# the canonical per-location record
# ---------------------------------------------------------------------------------------------------
class LocationCoverage:
    __slots__ = ("ap_id", "name", "region",
                 "detect_kind", "detect_flag", "suppress_kind", "static_suppress",
                 "vanilla_item", "vanilla_full", "placed_item", "placed_full",
                 "tags", "is_filler", "region_claims", "provenance")

    def __init__(self, ap_id, name, region):
        self.ap_id = ap_id
        self.name = name
        self.region = region
        self.detect_kind = None          # event_flag | shop_stock_flag
        self.detect_flag = None
        self.suppress_kind = "none"      # see SUPPRESS_KINDS
        self.static_suppress = False     # covered by check_lots_table.json alone (the foreign-
                                         # apworld path, er-logic static_lots.rs)? shops count.
        self.vanilla_item = None
        self.vanilla_full = None
        self.placed_item = None          # None in static mode (no live fill)
        self.placed_full = None
        self.tags = ()
        self.is_filler = None
        self.region_claims = {}          # source_file -> claimed_region
        self.provenance = {}             # field -> source_file

    def __repr__(self):
        return (f"LocationCoverage(ap_id={self.ap_id}, region={self.region!r}, "
                f"detect={self.detect_kind}/{self.detect_flag}, suppress={self.suppress_kind})")


class Violation:
    __slots__ = ("ap_id", "name", "check", "detail", "provenance")

    def __init__(self, ap_id, name, check, detail, provenance):
        self.ap_id = ap_id
        self.name = name
        self.check = check               # detection | suppression | region | quarantine
        self.detail = detail
        self.provenance = dict(provenance or {})

    def as_row(self):
        return (self.ap_id, self.name, self.check, self.detail, self.provenance)

    def __repr__(self):
        return f"Violation({self.check}: ap={self.ap_id} {self.detail})"


class CoverageError(Exception):
    pass


# ---------------------------------------------------------------------------------------------------
# the JOIN
# ---------------------------------------------------------------------------------------------------
def build_coverage(world=None, kept=None, _static_table=None):
    """Build the per-location coverage records for every EMITTED location this gen.

    world given  -> scope = HUB + world._kept(); the emitted tables (locationFlags /
                    checkItemFlags / shopRowFlags / checkLotBlankMap+Enemy) come from
                    world.fill_slot_data() and placements from the live fill.
    world = None -> STATIC mode; scope = HUB + (``kept`` if given else all REGIONS). The emitted
                    tables are re-derived from the source files exactly the way the features
                    derive them, so the join needs no AP install. ``kept`` lets the option-matrix
                    test pin an explicit num_regions/DLC scope with no flaky fill.
    _static_table -> test hook: override the (map, enemy, items) triple from
                    check_lots_table.json so the tests can prove the join catches a real hole.

    Returns (records, ctx): records is {ap_id: LocationCoverage}; ctx carries the joined tables."""
    data = _load("data")
    tags_mod = _load("location_tags")
    boss_data = _load("boss_data")
    boss_sweeps = _load("boss_sweeps")
    region_graces = _load("region_graces")
    region_open = _load("region_open_flags")
    region_play = _load("region_play_ids")
    shop_data = _load("shop_data")
    item_ids = _load("item_ids")
    repeatable = _load("repeatable_goods")
    boss_drops = _load("boss_drops")
    missable = _load("missable_locations")
    contract = _load("contract")
    if data is None:
        raise CoverageError("coverage: data.py could not be loaded")

    LOCATIONS = data.LOCATIONS
    HUB = data.HUB
    LOCATION_TAGS = getattr(tags_mod, "LOCATION_TAGS", {}) if tags_mod else {}
    REGION_BOSSES = getattr(boss_data, "REGION_BOSSES", {}) if boss_data else {}
    DUNGEON_SWEEPS = getattr(boss_sweeps, "DUNGEON_SWEEPS", {}) if boss_sweeps else {}
    SWEEP_REGION = getattr(boss_sweeps, "SWEEP_REGION", {}) if boss_sweeps else {}
    REGION_GRACE_POINTS = getattr(region_graces, "REGION_GRACE_POINTS", {}) if region_graces else {}
    REGION_OPEN_FLAGS = getattr(region_open, "REGION_OPEN_FLAGS", {}) if region_open else {}
    REGION_PLAY_IDS = getattr(region_play, "REGION_PLAY_IDS", {}) if region_play else {}
    SHOP_ROW_FLAGS = {int(k): int(v) for k, v in
                      getattr(shop_data, "SHOP_ROW_FLAGS", {}).items()} if shop_data else {}
    SHOP_ROW_IDS = {int(k): list(v) for k, v in
                    getattr(shop_data, "SHOP_ROW_IDS", {}).items()} if shop_data else {}
    SHOP_LOC_REGION = dict(getattr(shop_data, "SHOP_LOC_REGION", {})) if shop_data else {}
    LOCATION_ITEM = getattr(item_ids, "LOCATION_ITEM", {}) if item_ids else {}
    ITEM_CATALOG = getattr(item_ids, "ITEM_CATALOG", {}) if item_ids else {}
    REPEATABLE_GOODS = frozenset(getattr(repeatable, "REPEATABLE_GOODS", frozenset())) \
        if repeatable else frozenset()
    BOSS_DROP_FLAGS = frozenset(getattr(boss_drops, "BOSS_DROP_FLAGS", frozenset())) \
        if boss_drops else frozenset()
    MISSABLE_LOCATIONS = getattr(missable, "MISSABLE_LOCATIONS", {}) if missable else {}

    static_map, static_enemy, static_items = (_static_table if _static_table is not None
                                              else _load_static_table())

    # ---- scope --------------------------------------------------------------------------------
    if world is not None:
        scope_kept = list(world._kept())
        placements = _live_placements(world)
    else:
        scope_kept = list(kept) if kept is not None else list(data.REGIONS)
        placements = {}
    scope = [HUB] + [r for r in scope_kept if r != HUB]

    # ---- the client tables the gen EMITS (live) or their derivation (static) -------------------
    K_LOC = getattr(contract, "LOCATION_FLAGS", "locationFlags") if contract else "locationFlags"
    K_CIF = getattr(contract, "CHECK_ITEM_FLAGS", "checkItemFlags") if contract else "checkItemFlags"
    K_SRF = getattr(contract, "SHOP_ROW_FLAGS", "shopRowFlags") if contract else "shopRowFlags"
    K_CLM = getattr(contract, "CHECK_LOT_BLANK_MAP", "checkLotBlankMap") if contract else "checkLotBlankMap"
    K_CLE = getattr(contract, "CHECK_LOT_BLANK_ENEMY", "checkLotBlankEnemy") if contract else "checkLotBlankEnemy"
    if world is not None:
        try:
            sd = world.fill_slot_data()
        except Exception as e:  # pragma: no cover - defensive
            raise CoverageError(f"coverage: world.fill_slot_data() failed: {e!r}")
        emitted_location_flags = {int(k): int(v) for k, v in sd.get(K_LOC, {}).items()}
        emitted_check_item_flags = {int(k): {int(x) for x in v}
                                    for k, v in sd.get(K_CIF, {}).items()}
        emitted_shop_row_flags = {int(k): int(v) for k, v in sd.get(K_SRF, {}).items()}
        emitted_blank_lots_map = {int(k) for k in sd.get(K_CLM, {})}
        emitted_blank_lots_enemy = {int(k) for k in sd.get(K_CLE, {})}
        flags_src, cif_src = "slot_data." + K_LOC, "slot_data." + K_CIF
    else:
        emitted_location_flags = {aid: int(fl)
                                  for rn in scope for (_n, aid, fl) in LOCATIONS.get(rn, [])}
        # re-derive checkItemFlags the way features/check_item_flags.py does: every resolvable
        # ware, EXCEPT goods with a repeatable (farm/mine/shop/craft) source.
        emitted_check_item_flags = {}
        for rn in scope:
            for (_n, aid, fl) in LOCATIONS.get(rn, []):
                vn = LOCATION_ITEM.get(aid)
                full = ITEM_CATALOG.get(vn) if vn is not None else None
                if full is None:
                    continue
                full = int(full)
                if (full & ~_ROW_ID_MASK) == _GOODS_CATEGORY \
                        and (full & _ROW_ID_MASK) in REPEATABLE_GOODS:
                    continue
                emitted_check_item_flags.setdefault(full, set()).add(int(fl))
        emitted_shop_row_flags = {}
        for aid, fl in SHOP_ROW_FLAGS.items():
            if SHOP_LOC_REGION.get(aid) in set(scope):
                for row in SHOP_ROW_IDS.get(aid, []):
                    emitted_shop_row_flags[int(row)] = fl
        # features/check_lots.py sends EVERY lot (sealed-region lots are inert), from
        # check_lots_data.py CHECK_LOT_SLOTS_MAP/ENEMY.
        cld = _load("check_lots_data")
        emitted_blank_lots_map = {int(k) for k in getattr(cld, "CHECK_LOT_SLOTS_MAP", {})} if cld else set()
        emitted_blank_lots_enemy = {int(k) for k in getattr(cld, "CHECK_LOT_SLOTS_ENEMY", {})} if cld else set()
        flags_src, cif_src = "data.py", "features/check_item_flags.py (derived)"

    # system flags: everything the CLIENT itself writes. Region-open flags ARE front-door grace
    # flags, so fold the whole grace group in (region.rs lights them on Lock receipt).
    system_flags = set(REGION_OPEN_FLAGS.values()) | set(MAP_REVEAL_FLAGS) \
        | {DEATHLINK_KILL_FLAG, UNDERGROUND_VIEW_FLAG}
    for _r, _fls in REGION_GRACE_POINTS.items():
        system_flags.update(int(f) for f in _fls)

    # ---- pre-index region CLAIMANTS keyed by ap_id --------------------------------------------
    boss_claim = {}
    for region, entries in REGION_BOSSES.items():
        for (apid, _flag, _name) in entries:
            boss_claim[apid] = region
    sweep_claim = {}
    for trig, members in DUNGEON_SWEEPS.items():
        sr = SWEEP_REGION.get(trig)
        if sr is None:
            continue
        for apid in members:
            sweep_claim.setdefault(apid, set()).add(sr)
    grace_flag_region = {}
    for region, flags in REGION_GRACE_POINTS.items():
        for f in flags:
            grace_flag_region.setdefault(int(f), region)

    records = {}
    for region in scope:
        for (name, ap_id, flag) in LOCATIONS.get(region, []):
            rec = LocationCoverage(ap_id, name, region)
            rec.provenance["region"] = "data.py"
            rec.provenance["name"] = "data.py"
            flag = int(flag)

            rec.tags = tuple(LOCATION_TAGS.get(ap_id, ()))
            if rec.tags:
                rec.provenance["tags"] = "location_tags.py"
            rec.is_filler = _is_filler_location(rec, contract)

            # detection
            if ap_id in SHOP_ROW_FLAGS:
                rec.detect_kind = "shop_stock_flag"
                rec.detect_flag = SHOP_ROW_FLAGS[ap_id]
                rec.provenance["detect_flag"] = "shop_data.py"
            else:
                rec.detect_kind = "event_flag"
                rec.detect_flag = emitted_location_flags.get(ap_id, flag)
                rec.provenance["detect_flag"] = flags_src

            # vanilla ware + live placement
            vn = LOCATION_ITEM.get(ap_id)
            rec.vanilla_item = vn
            rec.vanilla_full = int(ITEM_CATALOG[vn]) if vn is not None and vn in ITEM_CATALOG else None
            if rec.vanilla_full is not None:
                rec.provenance["vanilla_item"] = "item_ids.py"
            pf = placements.get(ap_id)
            if pf is not None:
                rec.placed_item, rec.placed_full = pf
                rec.provenance["placed_item"] = "fill"

            # suppression (layered; see module docstring)
            rec.suppress_kind = _classify_suppression(
                rec, flag, static_map, static_enemy, static_items,
                emitted_blank_lots_map, emitted_blank_lots_enemy,
                emitted_check_item_flags, SHOP_ROW_FLAGS, SHOP_ROW_IDS, cif_src)
            rec.static_suppress = (flag in static_map or flag in static_enemy
                                   or flag in static_items or ap_id in SHOP_ROW_FLAGS)

            # region claims (join EVERY claimant)
            claims = {"data.py": region}
            if ap_id in boss_claim:
                claims["boss_data.py"] = boss_claim[ap_id]
            if ap_id in sweep_claim:
                srs = sweep_claim[ap_id]
                claims["boss_sweeps.py"] = (sorted(srs)[0] if len(srs) == 1 else sorted(srs))
            if flag in grace_flag_region:
                claims["region_graces.py"] = grace_flag_region[flag]
            if ap_id in SHOP_LOC_REGION:
                claims["shop_data.py"] = SHOP_LOC_REGION[ap_id]
            rec.region_claims = claims

            records[ap_id] = rec

    ctx = {
        "scope": scope, "kept": scope_kept, "hub": HUB,
        "REGION_OPEN_FLAGS": REGION_OPEN_FLAGS,
        "REGION_PLAY_IDS": REGION_PLAY_IDS,
        "DUNGEON_SWEEPS": DUNGEON_SWEEPS, "SWEEP_REGION": SWEEP_REGION,
        "emitted_location_flags": emitted_location_flags,
        "emitted_check_item_flags": emitted_check_item_flags,
        "emitted_shop_row_flags": emitted_shop_row_flags,
        "emitted_blank_lots_map": emitted_blank_lots_map,
        "emitted_blank_lots_enemy": emitted_blank_lots_enemy,
        "static_map": static_map, "static_enemy": static_enemy, "static_items": static_items,
        "shop_flag_by_ap": SHOP_ROW_FLAGS, "shop_rows_by_ap": SHOP_ROW_IDS,
        "system_flags": system_flags,
        "BOSS_DROP_FLAGS": BOSS_DROP_FLAGS,
        "MISSABLE_LOCATIONS": MISSABLE_LOCATIONS,
        "world": world,
        "static": world is None,
    }
    return records, ctx


def _live_placements(world):
    """ap_id -> (item_name, None) for the placed item at each of this player's locations."""
    out = {}
    try:
        p = world.player
        for loc in world.multiworld.get_locations(p):
            if loc.address is None or loc.item is None:
                continue
            out[loc.address] = (loc.item.name, None)
    except Exception:
        return {}
    return out


def _is_filler_location(rec, contract):
    """Static filler classification: carries no important/surface tag. Gates ACCEPTED_LEAKS (a
    knowingly-leaking location must be filler). Grounded in contract.py's own class lists
    (IMPORTANT_LOCATION_TYPES + SURFACE_DEFAULT_CLASSES) -- the sets the tracker/surface care about."""
    important = set()
    if contract is not None:
        important |= set(getattr(contract, "IMPORTANT_LOCATION_TYPES", ()))
        important |= set(getattr(contract, "SURFACE_DEFAULT_CLASSES", frozenset()))
    if rec.tags and (important & set(rec.tags)):
        return False
    return True


def _classify_suppression(rec, flag, static_map, static_enemy, static_items,
                          blank_lots_map, blank_lots_enemy, check_item_flags,
                          shop_flag_by_ap, shop_rows_by_ap, cif_src):
    """Resolve suppress_kind, in mechanism order:
      shop purchase -> lot blank (static flag->lot row AND the lot actually emitted in
      checkLotBlankMap/Enemy) -> static id-keyed (weapon/armor) -> per-seed checkItemFlags
      client intercept -> placed==vanilla -> none (a real hole iff the location has a ware)."""
    if rec.ap_id in shop_flag_by_ap and shop_rows_by_ap.get(rec.ap_id):
        rec.provenance["suppress"] = "shop_data.py (purchase IS the vanilla delivery)"
        return "shop_stock"
    ent = static_map.get(flag)
    if ent is not None and int(ent.get("lot", -1)) in blank_lots_map:
        rec.provenance["suppress"] = "check_lots_table.json[map] + checkLotBlankMap"
        return "lot_blank_map"
    ent = static_enemy.get(flag)
    if ent is not None and int(ent.get("lot", -1)) in blank_lots_enemy:
        rec.provenance["suppress"] = "check_lots_table.json[enemy] + checkLotBlankEnemy"
        return "lot_blank_enemy"
    if flag in static_items:
        rec.provenance["suppress"] = "check_lots_table.json[items] (id-keyed)"
        return "static_item_ids"
    if rec.vanilla_full is not None:
        fls = check_item_flags.get(rec.vanilla_full)
        if fls and flag in fls:
            rec.provenance["suppress"] = cif_src
            return "client_intercept"
    if (rec.placed_full is not None and rec.vanilla_full is not None
            and rec.placed_full == rec.vanilla_full):
        return "vanilla_identical"
    return "none"


# ---------------------------------------------------------------------------------------------------
# the three assertions -- collect ALL violations
# ---------------------------------------------------------------------------------------------------
def check_detection(records, ctx):
    out = []
    system = ctx["system_flags"]
    emitted = ctx["emitted_location_flags"]
    shop_rows = ctx["shop_rows_by_ap"]
    by_flag = {}
    for rec in records.values():
        by_flag.setdefault(rec.detect_flag, []).append(rec.ap_id)
    for rec in records.values():
        f = rec.detect_flag
        if f is None or f == 0:
            out.append(Violation(rec.ap_id, rec.name, "detection",
                                 "detect_flag missing/zero", rec.provenance)); continue
        if not detection_flag_valid(f, system):
            reason = ("system-flag collision (region-open/grace/map-reveal/deathlink/underground)"
                      if f in system else f"flag {f} out of valid range")
            out.append(Violation(rec.ap_id, rec.name, "detection",
                                 f"{reason} (detect_flag={f})", rec.provenance)); continue
        if rec.ap_id not in emitted:
            out.append(Violation(rec.ap_id, rec.name, "detection",
                                 "not present in emitted locationFlags (flag poll will never "
                                 "register this check)", rec.provenance)); continue
        if rec.detect_kind == "shop_stock_flag":
            if not shop_rows.get(rec.ap_id):
                out.append(Violation(rec.ap_id, rec.name, "detection",
                                     "shop check has no writable stock row (SHOP_ROW_IDS empty) -> "
                                     "client cannot arm eventFlag_forStock", rec.provenance)); continue
            if emitted.get(rec.ap_id) != f:
                out.append(Violation(rec.ap_id, rec.name, "detection",
                                     f"shop stock flag {f} disagrees with data.py locationFlags "
                                     f"entry {emitted.get(rec.ap_id)}", rec.provenance)); continue
        if len(by_flag.get(f, [])) > 1:
            others = [a for a in by_flag[f] if a != rec.ap_id]
            out.append(Violation(rec.ap_id, rec.name, "detection",
                                 f"aliased detect_flag {f} shared with {others[:4]}",
                                 rec.provenance)); continue
    return out


def check_award_source(records, ctx):
    """(d) AWARDED -- collect every non-shop location whose detect flag has NO awarding
    ItemLotParam row (absent from check_lots_table.json map/enemy/items).

    The game sets a lot's getItemFlagId when it awards that lot; that is the ONLY way the client's
    flag-poll ever sees a non-shop check fire. So a flag outside the static award join is a check
    the player can hunt forever and never send -- worse than a double-dip. Both shipped instances
    were region_map `synthetic` rows whose invented flag collided with a real id: 177 (its only
    lot, map 10182, awards NOTHING) and 320820 (no lot at all -- the eventFlag_forStock of
    ShopLineupParam 102282, a row the shop pipeline itself excludes). Shop checks are exempt: the
    purchase is the award, and check_detection already validates their stock rows. Deliberately
    NOT subtractable via ACCEPTED_LEAKS -- a leak pays too much; this can never pay at all."""
    out = []
    sm, se, si = ctx["static_map"], ctx["static_enemy"], ctx["static_items"]
    shop_flag_by_ap = ctx["shop_flag_by_ap"]
    for rec in records.values():
        if rec.detect_kind == "shop_stock_flag" or rec.ap_id in shop_flag_by_ap:
            continue
        f = rec.detect_flag
        if f in sm or f in se or f in si:
            continue
        out.append(Violation(rec.ap_id, rec.name, "award",
                             f"flag {f} has NO awarding ItemLotParam row (absent from "
                             f"check_lots_table.json map/enemy/items) -- the game never sets it "
                             f"when handing out an item, so the flag-poll can never observe this "
                             f"check: unobtainable by construction (phantom/synthetic-flag class)",
                             rec.provenance))
    return out


def check_suppression(records, ctx):
    out = []
    for rec in records.values():
        if rec.suppress_kind in SUPPRESS_KINDS:
            continue
        if rec.vanilla_full is None:
            continue  # no resolvable vanilla ware -> nothing to leak -> legal
    # a ware-bearing location with NO mechanism: the vanilla ware is handed out alongside the AP
    # item (double-dip). Two known sub-classes, distinguished in the detail:
    #   * flag absent from check_lots_table.json entirely -> no ItemLotParam row carries it
    #     (EMEVD-award or an unjudged lotItemCategory-0/6 row);
    #   * ware is a REPEATABLE good -> features/check_item_flags.py deliberately declines id-keyed
    #     suppression (arming it would eat every farmed/bought/crafted copy -- the lesser evil).
        raw = rec.vanilla_full & _ROW_ID_MASK
        goods = (rec.vanilla_full & ~_ROW_ID_MASK) == _GOODS_CATEGORY
        why = ("no ItemLotParam row carries this flag (absent from check_lots_table.json: "
               "EMEVD-award or unjudged lot category)")
        if goods:
            why += "; ware is a farmable/repeatable good, so id-keyed suppression is (correctly) not armed" \
                if rec.suppress_kind == "none" and not rec.static_suppress else ""
        out.append(Violation(rec.ap_id, rec.name, "suppression",
                             f"vanilla ware {rec.vanilla_item!r} (FullID 0x{rec.vanilla_full:08x}, "
                             f"raw {raw}) has NO suppression mechanism -- {why} -> the vanilla ware "
                             f"double-dips at this check", rec.provenance))
    return out


def check_region_consistency(records, ctx):
    out = []
    ROF = ctx["REGION_OPEN_FLAGS"]
    RPI = ctx["REGION_PLAY_IDS"]
    DS = ctx["DUNGEON_SWEEPS"]
    SR = ctx["SWEEP_REGION"]

    # (1) cross-file claim agreement
    for rec in records.values():
        vals = []
        for v in rec.region_claims.values():
            vals.extend(v if isinstance(v, list) else [v])
        if len(set(vals)) > 1:
            out.append(Violation(rec.ap_id, rec.name, "region",
                                 "region claims disagree across source files: "
                                 + repr(rec.region_claims), rec.provenance))

    # (2) every region with >=1 emitted location has a valid open flag AND measured kick geometry
    emitted_regions = {rec.region for rec in records.values()}
    hub = ctx["hub"]
    for region in sorted(emitted_regions):
        if region == hub:
            continue
        of = ROF.get(region)
        prov = {"region_open_flag": "region_open_flags.py", "geometry": "region_play_ids.py"}
        if of is None:
            out.append(Violation(None, f"<region {region}>", "region",
                                 f"region {region!r} has emitted locations but NO REGION_OPEN_FLAGS "
                                 f"entry (never lockable -> dead drops)", prov))
        elif not region_open_flag_valid(of):
            out.append(Violation(None, f"<region {region}>", "region",
                                 f"region {region!r} open flag {of} is not in the valid "
                                 f"{REGION_FLAG_LO}-{REGION_FLAG_HI} group (bogus/inert -> dead "
                                 f"drops; the old Stormveil class)", prov))
        if not RPI.get(region):
            out.append(Violation(None, f"<region {region}>", "region",
                                 f"region {region!r} has emitted locations but NO measured "
                                 f"REGION_PLAY_IDS kick geometry (region-lock silently off)", prov))

    # (3) each boss-sweep gate sweeps only members whose canonical region matches
    loc_region = {rec.ap_id: rec.region for rec in records.values()}
    for trig, members in DS.items():
        sr = SR.get(trig)
        if sr is None:
            continue
        for apid in members:
            lr = loc_region.get(apid)
            if lr is not None and lr != sr:
                out.append(Violation(apid, "<swept member>", "region",
                                     f"sweep {trig} (region {sr!r}) sweeps a member whose canonical "
                                     f"region is {lr!r} (Full Moon Queen class)",
                                     {"sweep_region": "boss_sweeps.py", "location_region": "data.py"}))
    return out


# ---------------------------------------------------------------------------------------------------
# degradation ledger integration
# ---------------------------------------------------------------------------------------------------
def _quarantine_violations(records, ctx):
    """Self-cleaning: a QUARANTINE entry still EMITTED and passing every check should be removed; an
    ACCEPTED_LEAK now suppressable (or non-filler) should be removed. Both make the gate say 'remove'."""
    q = _load("coverage_quarantine")
    out = []
    if q is None:
        return out
    QUAR = getattr(q, "QUARANTINE", {})
    LEAKS = getattr(q, "ACCEPTED_LEAKS", {})
    if QUAR or LEAKS:
        det = {v.ap_id for v in check_detection(records, ctx)}
        awd = {v.ap_id for v in check_award_source(records, ctx)}
        sup = {v.ap_id for v in check_suppression(records, ctx)}
        reg = {v.ap_id for v in check_region_consistency(records, ctx)}
    for ap_id, meta in QUAR.items():
        rec = records.get(ap_id)
        if rec is None:
            continue
        if ap_id not in det and ap_id not in awd and ap_id not in sup and ap_id not in reg:
            out.append(Violation(ap_id, rec.name, "quarantine",
                                 "QUARANTINE entry is emitted and now passes every check -- remove it "
                                 f"from coverage_quarantine.QUARANTINE (was: {meta.get('reason')})",
                                 rec.provenance))
    for ap_id, meta in LEAKS.items():
        rec = records.get(ap_id)
        if rec is None:
            continue
        if rec.suppress_kind in SUPPRESS_KINDS:
            out.append(Violation(ap_id, rec.name, "quarantine",
                                 "ACCEPTED_LEAK is now suppressable -- remove it from "
                                 f"coverage_quarantine.ACCEPTED_LEAKS (was: {meta.get('reason')})",
                                 rec.provenance))
        elif rec.is_filler is False:
            out.append(Violation(ap_id, rec.name, "quarantine",
                                 "ACCEPTED_LEAK is not FILLER-classified -- an important location "
                                 "may never knowingly leak; fix suppression instead",
                                 rec.provenance))
    return out


def all_checks(records, ctx):
    """Run every check; return {check_name: [Violation, ...]}. ACCEPTED_LEAKS are subtracted from the
    suppression list (the sanctioned holes) but re-surface via _quarantine_violations if they become
    satisfiable or non-filler."""
    q = _load("coverage_quarantine")
    accepted = set(getattr(q, "ACCEPTED_LEAKS", {})) if q else set()
    supp = [v for v in check_suppression(records, ctx) if v.ap_id not in accepted]
    return {
        "detection": check_detection(records, ctx),
        "award": check_award_source(records, ctx),
        "suppression": supp,
        "region": check_region_consistency(records, ctx),
        "quarantine": _quarantine_violations(records, ctx),
    }


def _flatten(byname):
    out = []
    for lst in byname.values():
        out.extend(lst)
    return out


# ---------------------------------------------------------------------------------------------------
# REPORT MODE (no raise) + the raising variant
# ---------------------------------------------------------------------------------------------------
def report_coverage(world=None, kept=None, printer=print, _static_table=None):
    """Build records, run all checks + the degradation ledger, return
    (records, ctx, violations_by_check). Prints a compact summary; NEVER raises."""
    records, ctx = build_coverage(world, kept=kept, _static_table=_static_table)
    byname = all_checks(records, ctx)
    total = sum(len(v) for v in byname.values())
    if printer:
        mode = "STATIC full-pool" if (ctx["static"] and kept is None) else \
            ("STATIC scoped" if ctx["static"] else f"live") + f" ({len(ctx['kept'])} kept regions)"
        printer(f"[coverage] {mode}: {len(records)} emitted locations | "
                + " | ".join(f"{k} {len(v)}" for k, v in byname.items())
                + f" | TOTAL {total}")
    return records, ctx, byname


def assert_coverage(world):
    """RAISING variant: raise CoverageError listing ap_id, name, failing check + provenance for each
    violation. Wired into core.post_fill (2026-07-14); test_assert_coverage_is_wired_into_the_gen_path
    keeps it that way."""
    records, ctx = build_coverage(world)
    byname = all_checks(records, ctx)
    violations = _flatten(byname)
    if violations:
        lines = [f"coverage gate: {len(violations)} violation(s):"]
        for v in violations:
            lines.append(f"  [{v.check}] ap={v.ap_id} {v.name!r}: {v.detail} | provenance={v.provenance}")
        raise CoverageError("\n".join(lines))
    return records, ctx


# ---------------------------------------------------------------------------------------------------
# timestamped triage report (markdown)
# ---------------------------------------------------------------------------------------------------
def render_markdown(records, ctx, byname):
    import datetime
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    total = sum(len(v) for v in byname.values())
    L = []
    L.append(f"# Coverage report -- {ts}")
    L.append("")
    L.append("Closed-loop coverage gate (`greenfield/eldenring/coverage.py`), REPORT MODE. Joins the")
    L.append("apworld's own source tables and checks every EMITTED location for detection /")
    L.append("suppression / region-consistency. Generated by `tools/gen_coverage_report.py`.")
    L.append("")
    mode = "STATIC full-pool (all regions, placements unknown)" if ctx["static"] else \
        f"live ({len(ctx['kept'])} kept regions)"
    L.append(f"- scope: {mode}")
    L.append(f"- emitted locations: {len(records)} "
             f"(of which shop checks: {sum(1 for r in records.values() if r.detect_kind == 'shop_stock_flag')})")
    L.append(f"- total violations: {total}")
    L.append("")
    L.append("| check | violations |")
    L.append("|-------|-----------|")
    for k, v in byname.items():
        L.append(f"| {k} | {len(v)} |")
    L.append("")

    det, reg, sup = byname["detection"], byname["region"], byname["suppression"]
    awd = byname.get("award", [])
    stormveil = [v for v in reg if "open flag" in v.detail]
    fmq = [v for v in reg if "Full Moon Queen" in v.detail]
    shopgap = [v for v in det if "stock row" in v.detail]
    L.append("## The known failure classes (history: each shipped and bit in-game once)")
    L.append("")
    L.append(f"1. **Missing detections.** Locations absent from `locationFlags` / keyed on a system "
             f"flag this run: **{len(det) - len(shopgap)}** (the matt-world 147-hole class).")
    L.append(f"2. **Bogus region-open flags (dead drops).** Open-flag validity violations: "
             f"**{len(stormveil)}** "
             + ("-- DETECTED; a kept region never gets a real lock flag, its drops die."
                if stormveil else "(the old Stormveil placeholder-200 gap stays closed: region "
                "locks live on real 71xxx-76xxx flags)."))
    L.append(f"3. **Cross-file region mis-tags.** Disagreements across data.py / boss_data.py / "
             f"boss_sweeps.py / region_graces.py / shop_data.py: "
             f"**{sum(1 for v in reg if 'disagree' in v.detail)}**; sweep-membership mismatches "
             f"(Full Moon Queen class): **{len(fmq)}**.")
    L.append(f"4. **Shop gaps.** Shop checks with no writable stock row (undetectable): "
             f"**{len(shopgap)}** of {sum(1 for r in records.values() if r.detect_kind == 'shop_stock_flag')} "
             f"emitted shop checks.")
    L.append(f"5. **Unsuppressed vanilla wares (double-dip).** Ware-bearing locations with NO "
             f"suppression mechanism: **{len(sup)}**. These pay the vanilla ware alongside the AP "
             f"item in-game.")
    L.append(f"6. **Unawardable flags (phantom checks).** Non-shop locations whose flag has NO "
             f"awarding ItemLotParam row: **{len(awd)}** (the synthetic 177/320820 class -- the "
             f"check can NEVER fire; promoted from monitored to raising 2026-07-14).")
    L.append("")

    # monitored categories -- not violations, but the numbers to watch
    noware = [r for r in records.values() if r.vanilla_full is None]
    foreign_gap = [r for r in records.values()
                   if r.vanilla_full is not None and not r.static_suppress]
    bd = ctx["BOSS_DROP_FLAGS"]
    bd_locs = [r for r in records.values() if r.detect_flag in bd]
    bd_unsup = [r for r in bd_locs if r.suppress_kind == "none" and r.vanilla_full is not None]
    kinds = {}
    for r in records.values():
        kinds[r.suppress_kind] = kinds.get(r.suppress_kind, 0) + 1
    L.append("## Monitored categories (not violations this run)")
    L.append("")
    L.append("- suppression mechanism mix: "
             + ", ".join(f"{k} **{v}**" for k, v in sorted(kinds.items())) + ".")
    L.append(f"- FOREIGN-apworld static gap: **{len(foreign_gap)}** ware-bearing locations invisible "
             f"to `check_lots_table.json` alone (er-logic static_lots.rs path -- a foreign seed "
             f"double-dips there even where OUR per-seed checkItemFlags covers it). The no-award "
             f"subset of this gap is now ENFORCED by the raising `award` check above.")
    L.append(f"- boss-drop-flag locations emitted: **{len(bd_locs)}**; of those lacking any "
             f"suppression: **{len(bd_unsup)}** (vanilla-suppress-leak class).")
    L.append(f"- locations with no resolvable vanilla ware (Rune filler / name gaps -- nothing to "
             f"suppress): **{len(noware)}**.")
    L.append("")

    L.append("## Violations")
    L.append("")
    if total == 0:
        L.append("_none_")
    else:
        L.append("| check | ap_id | name | detail | provenance |")
        L.append("|-------|-------|------|--------|------------|")
        for k in byname:
            for v in byname[k]:
                nm = (v.name or "").replace("|", "\\|")
                dt = v.detail.replace("|", "\\|")
                L.append(f"| {k} | {v.ap_id} | {nm} | {dt} | {v.provenance} |")
    L.append("")
    return ts, "\n".join(L) + "\n"
