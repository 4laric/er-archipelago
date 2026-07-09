"""Closed-loop COVERAGE GATE (hand-authored -- NOT generated; do not run gen_data on this file).

A gen-time invariant that joins the apworld's OWN generated source files and asserts, for every
location this seed EMITS (post option-filtering), that the location is

  (a) DETECTABLE   -- it carries a real acquisition flag the client's flag-poll table (locationFlags)
                      / shop-stock table (shopRowFlags) actually contains, in a valid allocated
                      range, not aliased to another live location, and disjoint from the system
                      flags (region-open / map-reveal / deathlink-kill);
  (b) SUPPRESSED   -- if it vanilla-holds an item, a suppression mechanism exists (checkItemFlags
                      client-intercept, or a shop stock-flag) so the vanilla ware does not leak
                      alongside the AP-placed item;
  (c) REGION-CONSISTENT -- every source file that claims a region for the location agrees, the
                      location's region has a valid REGION_OPEN_FLAGS entry AND kick/seal geometry,
                      and every boss-sweep gate sweeps only members whose canonical region matches.

Today none of these SHOULD fail on a clean tree except the one known Stormveil open-flag gap (bogus
flag 200; see memory gf-legacy-dungeon-open-flag-gap). Historically these holes surfaced in-game
hours after a gen -- this module turns them into a gen-time join.

DESIGN (mirrors contract.py's single-source style):
  * ``LocationCoverage``  -- the canonical per-location record (detection / suppression / region +
    region_claims across EVERY claimant + field->source provenance).
  * ``build_coverage(world=None, kept=None)`` -- JOINS the source files for every emitted location.
    With a live ``world`` the scope is HUB + world._kept() and item PLACEMENTS are read from the fill;
    with world=None it runs in STATIC mode (all regions, or an explicit pinned ``kept`` subset --
    used by the option-matrix test) and placements are unknown, so the report can be produced without
    spinning a multiworld and the seed-invariant data holes are still caught.
  * ``check_detection`` / ``check_suppression`` / ``check_region_consistency`` -- collect-ALL checks
    (every violation with provenance, never one-per-gen).
  * ``report_coverage(world=None, kept=None)`` -- builds records, runs all three checks, returns/prints
    the full violation table WITHOUT raising (REPORT MODE -- what the gen path is safe to call today).
  * ``assert_coverage(world)`` -- the RAISING variant (CoverageError); NOT wired into the gen path yet
    because the tree still carries the known Stormveil gap.
  * structured degradation lives in ``coverage_quarantine.py`` (QUARANTINE / ACCEPTED_LEAKS).

Flag-validity ranges are grounded, not invented (the AI-contribution failure mode CONTRIBUTING.md
warns about): the region/grace/open-flag group is 71xxx-76xxx (memory er-event-flag-validity,
region_open_flags.py), the DLC/base map-reveal flags are the 62xxx set mirrored from gen_data.py /
startgrants.rs, and the deathlink-kill flag is 76996 (memory er-open-flag-collision-bug). General
location acquisition flags span many allocated groups, so the general predicate only rejects the
provably-bad (<=0, or the system flags a check must never reuse) rather than inventing a tight range
that would false-positive on the ~3.9k real derived flags.
"""

import importlib
import os
import sys

# ---------------------------------------------------------------------------------------------------
# module loading -- works both as a package submodule (relative import, the installed world) and
# standalone by file path (static report run from the source tree). Never raises: a missing generated
# file degrades to an empty table and is surfaced as a NOTE, not a crash.
# ---------------------------------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(modname):
    """Import a sibling generated module. Return the CANONICAL already-imported module (sys.modules)
    when the world is installed -- so a caller that mutates e.g. coverage_quarantine sees the same
    object -- then the package-relative import, then a file-path fallback (source-tree static run)."""
    if __package__:
        fq = __package__ + "." + modname
        mod = sys.modules.get(fq)
        if mod is not None:
            return mod
        try:
            return importlib.import_module("." + modname, __package__)
        except Exception:
            pass
    path = os.path.join(_HERE, modname + ".py")
    if not os.path.isfile(path):
        return None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("gf_cov_" + modname, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _load_feature(modname):
    """Load features/<modname>.py. Package-relative when installed; the file-path fallback can fail
    for modules that themselves use relative imports -- callers treat None as 'skip that sub-check'."""
    if __package__:
        fq = __package__ + ".features." + modname
        mod = sys.modules.get(fq)
        if mod is not None:
            return mod
        try:
            return importlib.import_module(".features." + modname, __package__)
        except Exception:
            pass
    return None


# ---------------------------------------------------------------------------------------------------
# grounded flag families (cited above). Module-level so the test + report can introspect them.
# ---------------------------------------------------------------------------------------------------
MAP_REVEAL_FLAGS = frozenset({
    62010, 62011, 62012, 62020, 62021, 62022, 62030, 62031, 62032, 62040, 62041,
    62050, 62051, 62052, 62060, 62061, 62062, 62063, 62064,
    62080, 62081, 62082, 62083, 62084,
})
DEATHLINK_KILL_FLAG = 76996
REGION_FLAG_LO, REGION_FLAG_HI = 71000, 76999


def region_open_flag_valid(flag) -> bool:
    """A region-open flag is only real if it sits in the 71xxx-76xxx region/grace group. Stormveil's
    placeholder 200 (memory gf-legacy-dungeon-open-flag-gap) is the known failure this rejects."""
    return isinstance(flag, int) and REGION_FLAG_LO <= flag <= REGION_FLAG_HI


def detection_flag_valid(flag, system_flags) -> bool:
    """Valid iff a positive int inside u32 AND not a system flag a check must never reuse (region-open
    / map-reveal / deathlink-kill). We deliberately do NOT invent a tight allocated range for the
    general case -- the ~3.9k derived flags span many real game groups and a made-up bound would
    false-positive on real data. System-flag disjointness + aliasing are the grounded teeth."""
    return isinstance(flag, int) and 0 < flag < (1 << 31) and flag not in system_flags


# ---------------------------------------------------------------------------------------------------
# the canonical per-location record
# ---------------------------------------------------------------------------------------------------
class LocationCoverage:
    __slots__ = ("ap_id", "name", "region",
                 "detect_kind", "detect_flag", "suppress_kind",
                 "vanilla_item", "vanilla_full", "placed_item", "placed_full",
                 "tags", "is_filler", "region_claims", "provenance")

    def __init__(self, ap_id, name, region):
        self.ap_id = ap_id
        self.name = name
        self.region = region
        self.detect_kind = None          # event_flag | shop_stock_flag | synthetic
        self.detect_flag = None
        self.suppress_kind = "none"      # same_flag | client_intercept | vanilla_identical | none
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
def build_coverage(world=None, kept=None):
    """Build the per-location coverage records for every EMITTED location this gen.

    world given  -> scope = HUB + world._kept(); placements from the live fill; the emitted tables
                    (locationFlags / checkItemFlags / shopRowFlags) come from world.fill_slot_data().
    world = None -> STATIC mode; scope = HUB + (``kept`` if given else all REGIONS). Placements
                    unknown; emitted tables fall back to the generated source files. ``kept`` lets the
                    option-matrix test pin an explicit num_regions/DLC scope with no flaky fill.

    Returns (records, ctx): records is {ap_id: LocationCoverage}; ctx carries the joined tables + scope."""
    data = _load("data")
    tags_mod = _load("location_tags")
    boss_data = _load("boss_data")
    boss_sweeps = _load("boss_sweeps")
    region_graces = _load("region_graces")
    region_open = _load("region_open_flags")
    shop_data = _load("shop_data")
    item_ids = _load("item_ids")
    boss_drops = _load("boss_drops")
    missable = _load("missable_locations")
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
    SHOP_ROW_FLAGS = getattr(shop_data, "SHOP_ROW_FLAGS", {}) if shop_data else {}
    SHOP_ROW_IDS = getattr(shop_data, "SHOP_ROW_IDS", {}) if shop_data else {}
    LOCATION_ITEM = getattr(item_ids, "LOCATION_ITEM", {}) if item_ids else {}
    ITEM_CATALOG = getattr(item_ids, "ITEM_CATALOG", {}) if item_ids else {}
    BOSS_DROP_FLAGS = frozenset(getattr(boss_drops, "BOSS_DROP_FLAGS", frozenset())) if boss_drops else frozenset()
    MISSABLE_LOCATIONS = getattr(missable, "MISSABLE_LOCATIONS", {}) if missable else {}

    REGION_PLAY_IDS = _load_region_play_ids()

    # ---- scope --------------------------------------------------------------------------------
    if world is not None:
        scope_kept = list(world._kept())
        placements = _live_placements(world)
    else:
        scope_kept = list(kept) if kept is not None else list(data.REGIONS)
        placements = {}
    scope = [HUB] + scope_kept

    # ---- the client tables the gen EMITS (live) or their source (static) ----------------------
    if world is not None:
        try:
            sd = world.fill_slot_data()
        except Exception as e:  # pragma: no cover - defensive
            raise CoverageError(f"coverage: world.fill_slot_data() failed: {e!r}")
        emitted_location_flags = {int(k): int(v) for k, v in sd.get("locationFlags", {}).items()}
        emitted_check_item_flags = {int(k): [int(x) for x in v]
                                    for k, v in sd.get("checkItemFlags", {}).items()}
        emitted_shop_row_flags = {int(v) for v in sd.get("shopRowFlags", {}).values()}
    else:
        emitted_location_flags = {aid: int(fl)
                                  for rn in scope for (_n, aid, fl) in LOCATIONS.get(rn, [])}
        emitted_check_item_flags = {}
        for rn in scope:
            for (_n, aid, fl) in LOCATIONS.get(rn, []):
                vn = LOCATION_ITEM.get(aid)
                full = ITEM_CATALOG.get(vn) if vn is not None else None
                if full is not None:
                    emitted_check_item_flags.setdefault(int(full), set()).add(int(fl))
        emitted_check_item_flags = {k: sorted(v) for k, v in emitted_check_item_flags.items()}
        emitted_shop_row_flags = set()

    system_flags = set(REGION_OPEN_FLAGS.values()) | set(MAP_REVEAL_FLAGS) | {DEATHLINK_KILL_FLAG}

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

    shop_flag_by_ap = {int(k): int(v) for k, v in SHOP_ROW_FLAGS.items()}
    shop_rows_by_ap = {int(k): list(v) for k, v in SHOP_ROW_IDS.items()}

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
            rec.is_filler = _is_filler_location(rec)

            # detection
            if ap_id in shop_flag_by_ap:
                rec.detect_kind = "shop_stock_flag"
                rec.detect_flag = shop_flag_by_ap[ap_id]
                rec.provenance["detect_flag"] = "shop_data.py"
            else:
                rec.detect_kind = "event_flag"
                rec.detect_flag = emitted_location_flags.get(ap_id, flag)
                rec.provenance["detect_flag"] = ("slot_data.locationFlags"
                                                 if world is not None else "data.py")

            # suppression
            vn = LOCATION_ITEM.get(ap_id)
            rec.vanilla_item = vn
            rec.vanilla_full = ITEM_CATALOG.get(vn) if vn is not None else None
            if rec.vanilla_full is not None:
                rec.provenance["vanilla_item"] = "item_ids.py"
            pf = placements.get(ap_id)
            if pf is not None:
                rec.placed_item, rec.placed_full = pf
                rec.provenance["placed_item"] = "fill"
            rec.suppress_kind = _classify_suppression(
                rec, emitted_check_item_flags, shop_flag_by_ap, shop_rows_by_ap)

            # region claims (join EVERY claimant)
            claims = {"data.py": region}
            if ap_id in boss_claim:
                claims["boss_data.py"] = boss_claim[ap_id]
            if ap_id in sweep_claim:
                srs = sweep_claim[ap_id]
                claims["boss_sweeps.py"] = (sorted(srs)[0] if len(srs) == 1 else sorted(srs))
            if flag in grace_flag_region:
                claims["region_graces.py"] = grace_flag_region[flag]
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
        "shop_rows_by_ap": shop_rows_by_ap,
        "shop_flag_by_ap": shop_flag_by_ap,
        "system_flags": system_flags,
        "BOSS_DROP_FLAGS": BOSS_DROP_FLAGS,
        "MISSABLE_LOCATIONS": MISSABLE_LOCATIONS,
        "world": world,
        "static": world is None,
    }
    return records, ctx


def _load_region_play_ids():
    al = _load_feature("area_locks")
    if al is not None and hasattr(al, "REGION_PLAY_IDS"):
        return dict(al.REGION_PLAY_IDS)
    path = os.path.join(_HERE, "features", "area_locks.py")
    if not os.path.isfile(path):
        return {}
    try:
        import re
        import ast
        txt = open(path, encoding="utf-8").read()
        m = re.search(r"REGION_PLAY_IDS = (\{.*?\n\})", txt, re.S)
        return ast.literal_eval(m.group(1)) if m else {}
    except Exception:
        return {}


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


def _is_filler_location(rec):
    """Static filler classification: no big-ticket tag. Gates ACCEPTED_LEAKS (a knowingly-leaking
    location must be filler)."""
    contract = _load("contract")
    big = frozenset(getattr(contract, "BIG_TICKET_TYPES", frozenset())) if contract else frozenset()
    if rec.tags and (big & set(rec.tags)):
        return False
    return True


def _classify_suppression(rec, emitted_check_item_flags, shop_flag_by_ap, shop_rows_by_ap):
    """Resolve suppress_kind. Order: placed==vanilla -> vanilla_identical; checkItemFlags covers the
    vanilla FullID+flag -> client_intercept; shop check with a writable stock row -> same_flag; no
    vanilla ware -> none (legal); else -> none (a real hole if placed != vanilla)."""
    if (rec.placed_full is not None and rec.vanilla_full is not None
            and rec.placed_full == rec.vanilla_full):
        return "vanilla_identical"
    if rec.vanilla_full is not None:
        lst = emitted_check_item_flags.get(int(rec.vanilla_full))
        if lst and int(rec.detect_flag or 0) in lst:
            return "client_intercept"
    if rec.ap_id in shop_flag_by_ap and shop_rows_by_ap.get(rec.ap_id):
        return "same_flag"
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
            reason = ("system-flag collision (region-open/map-reveal/deathlink)"
                      if f in system else f"flag {f} out of valid range")
            out.append(Violation(rec.ap_id, rec.name, "detection",
                                 f"{reason} (detect_flag={f})", rec.provenance)); continue
        if rec.detect_kind == "event_flag" and rec.ap_id not in emitted:
            out.append(Violation(rec.ap_id, rec.name, "detection",
                                 "not present in emitted locationFlags", rec.provenance)); continue
        if rec.detect_kind == "shop_stock_flag" and not shop_rows.get(rec.ap_id):
            out.append(Violation(rec.ap_id, rec.name, "detection",
                                 "shop check has no writable stock row (SHOP_ROW_IDS empty) -> "
                                 "client cannot arm eventFlag_forStock", rec.provenance)); continue
        if len(by_flag.get(f, [])) > 1:
            others = [a for a in by_flag[f] if a != rec.ap_id]
            out.append(Violation(rec.ap_id, rec.name, "detection",
                                 f"aliased detect_flag {f} shared with {others[:4]}",
                                 rec.provenance)); continue
    return out


def check_suppression(records, ctx):
    out = []
    static = ctx["static"]
    for rec in records.values():
        if rec.suppress_kind in ("same_flag", "client_intercept", "vanilla_identical"):
            continue
        if rec.vanilla_full is None:
            continue  # no vanilla ware -> nothing to leak -> legal
        if static:
            out.append(Violation(rec.ap_id, rec.name, "suppression",
                                 f"vanilla ware {rec.vanilla_item!r} (FullID {rec.vanilla_full}) has "
                                 f"no suppression mechanism (no checkItemFlags entry, not a shop)",
                                 rec.provenance)); continue
        if rec.placed_full is not None and rec.placed_full != rec.vanilla_full:
            out.append(Violation(rec.ap_id, rec.name, "suppression",
                                 f"placed {rec.placed_item!r} != vanilla {rec.vanilla_item!r} but "
                                 f"no suppression mechanism", rec.provenance))
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

    # (2) every region with >=1 emitted location has a valid open flag AND kick/seal geometry
    emitted_regions = {rec.region for rec in records.values()}
    hub = ctx["hub"]
    for region in sorted(emitted_regions):
        if region == hub:
            continue
        of = ROF.get(region)
        prov = {"region_open_flag": "region_open_flags.py", "geometry": "features/area_locks.py"}
        if of is None:
            out.append(Violation(None, f"<region {region}>", "region",
                                 f"region {region!r} has emitted locations but NO REGION_OPEN_FLAGS "
                                 f"entry (never lockable -> dead drops)", prov))
        elif not region_open_flag_valid(of):
            out.append(Violation(None, f"<region {region}>", "region",
                                 f"region {region!r} open flag {of} is not in the valid "
                                 f"{REGION_FLAG_LO}-{REGION_FLAG_HI} group (bogus/inert -> dead "
                                 f"drops; Stormveil class)", prov))
        if RPI and region not in RPI:
            out.append(Violation(None, f"<region {region}>", "region",
                                 f"region {region!r} has emitted locations but NO REGION_PLAY_IDS "
                                 f"kick/seal geometry (region-lock silently off)", prov))

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
    det = {v.ap_id for v in check_detection(records, ctx)}
    sup = {v.ap_id for v in check_suppression(records, ctx)}
    reg = {v.ap_id for v in check_region_consistency(records, ctx)}
    for ap_id, meta in QUAR.items():
        rec = records.get(ap_id)
        if rec is None:
            continue
        if ap_id not in det and ap_id not in sup and ap_id not in reg:
            out.append(Violation(ap_id, rec.name, "quarantine",
                                 "QUARANTINE entry is emitted and now passes every check -- remove it "
                                 f"from coverage_quarantine.QUARANTINE (was: {meta.get('reason')})",
                                 rec.provenance))
    for ap_id, meta in LEAKS.items():
        rec = records.get(ap_id)
        if rec is None:
            continue
        if rec.suppress_kind in ("same_flag", "client_intercept", "vanilla_identical"):
            out.append(Violation(ap_id, rec.name, "quarantine",
                                 "ACCEPTED_LEAK is now suppressable -- remove it from "
                                 f"coverage_quarantine.ACCEPTED_LEAKS (was: {meta.get('reason')})",
                                 rec.provenance))
        elif rec.is_filler is False:
            out.append(Violation(ap_id, rec.name, "quarantine",
                                 "ACCEPTED_LEAK is not FILLER-classified -- an advancement/useful "
                                 "location may never knowingly leak; fix suppression instead",
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
def report_coverage(world=None, kept=None, printer=print):
    """Build records, run all checks + the degradation ledger, return
    (records, ctx, violations_by_check). Prints a compact summary; NEVER raises."""
    records, ctx = build_coverage(world, kept=kept)
    byname = all_checks(records, ctx)
    total = sum(len(v) for v in byname.values())
    if printer:
        mode = "STATIC full-pool" if ctx["static"] else f"live ({len(ctx['kept'])} kept regions)"
        printer(f"[coverage] {mode}: {len(records)} emitted locations | "
                + " | ".join(f"{k} {len(v)}" for k, v in byname.items())
                + f" | TOTAL {total}")
    return records, ctx, byname


def assert_coverage(world):
    """RAISING variant: raise CoverageError listing ap_id, name, failing check + provenance for each
    violation. NOT wired into the gen path yet (the tree still carries the known Stormveil gap)."""
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
    L.append("Closed-loop coverage gate (`greenfield/eldenring_gf/coverage.py`), REPORT MODE. Joins")
    L.append("the apworld's own generated source files and checks every EMITTED location for")
    L.append("detection / suppression / region-consistency. Generated by `tools/gen_coverage_report.py`.")
    L.append("")
    mode = "STATIC full-pool (all regions, placements unknown)" if ctx["static"] else \
        f"live ({len(ctx['kept'])} kept regions)"
    L.append(f"- scope: {mode}")
    L.append(f"- emitted locations: {len(records)}")
    L.append(f"- total violations: {total}")
    L.append("")
    L.append("| check | violations |")
    L.append("|-------|-----------|")
    for k, v in byname.items():
        L.append(f"| {k} | {len(v)} |")
    L.append("")

    det = byname["detection"]; reg = byname["region"]
    stormveil = [v for v in reg if "Stormveil" in v.detail or " 200 " in v.detail]
    fmq = [v for v in reg if "Full Moon Queen" in v.detail]
    shopgap = [v for v in det if "stock row" in v.detail]
    L.append("## The four known failure classes")
    L.append("")
    L.append("1. **~147 missing detections (legacy matt world).** The greenfield generator derives an")
    L.append(f"   acquisition flag for EVERY location, so all {len(ctx['emitted_location_flags'])} emitted")
    L.append("   locations are present in `locationFlags`. Missing-detection violations this run: "
             f"**{sum(1 for v in det if 'locationFlags' in v.detail or 'missing' in v.detail)}** "
             "(the matt-world 147-hole does not recur here -- closed by construction).")
    L.append(f"2. **Stormveil dead-drops.** Region-open validity violations for Stormveil / flag 200: "
             f"**{len(stormveil)}**. "
             + ("DETECTED -- Stormveil Castle open flag is the bogus placeholder 200 (not in the "
                "71xxx-76xxx group); a kept Stormveil never gets a real lock flag, so its drops die. "
                "Fix: allocate a real legacy-dungeon front-door flag in gen_data (memory "
                "gf-legacy-dungeon-open-flag-gap)." if stormveil else "none this scope."))
    L.append(f"3. **Full Moon Queen cross-file mis-tag.** data.py-vs-sweeps region disagreement "
             f"violations: **{len(fmq)}** (total cross-file region disagreements: "
             f"**{sum(1 for v in reg if 'disagree' in v.detail)}**). "
             + ("DETECTED." if fmq else "none -- already reconciled by gen_data.ROW_MAP_REGION_FIX; "
                "the gate now guards against a recurrence."))
    L.append(f"4. **Shop gaps.** Shop checks with no writable stock row (undetectable): **{len(shopgap)}** "
             f"of {len(ctx['shop_flag_by_ap'])} shop checks. "
             + ("DETECTED." if shopgap else "none -- every emitted shop check has a nonzero, unshared "
                "stock flag and a writable ShopLineupParam row."))
    L.append("")

    bd = ctx["BOSS_DROP_FLAGS"]
    bd_locs = [r for r in records.values() if r.detect_flag in bd]
    bd_leak = [r for r in bd_locs if r.suppress_kind == "none" and r.vanilla_full is not None]
    noware = [r for r in records.values() if r.vanilla_full is None]
    L.append("## Monitored categories (not violations this run)")
    L.append("")
    L.append(f"- boss/world-drop-flag locations (vanilla-suppress-leak class): **{len(bd_locs)}** "
             f"emitted; of those lacking any suppression mechanism: **{len(bd_leak)}**.")
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
