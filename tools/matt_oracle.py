#!/usr/bin/env python3
"""matt_oracle.py -- read-only cross-check of our tables against thefifthmatt/SoulsRandomizers.

WHAT THIS IS. thefifthmatt's Elden Ring randomizer carries a hand-curated item-slot table
(`diste/Base/itemslots.txt`, ~4400 slots) keyed on the same event-flag number space as our
`[fFLAG]` suffix. Independently curated, same game: a disagreement between the two tables is
evidence about the GAME, and it is the only second opinion our generated tables have. Two of the
six discrepancy classes surveyed in the 2026-09 oracle study are tight enough to gate on:

  A. ITEM IDENTITY -- `item_ids.LOCATION_ITEM[ap_id]` vs the vanilla item his DebugText records for
     the same flag. 99.8% agreement over ~4100 comparable rows. Wrong vanilla item is the highest
     blast radius defect we have: it feeds item tier, which feeds logic.
  B. MISSING SLOTS -- his Type-0 (Event-scope) flags that `data.LOCATIONS` has no row for at all.

Everything else (region assignment, missable tagging, shop granularity, DLC membership) is
report-only and lives in `--report`, because the two models differ structurally there rather than
factually. `--report` also prints count-only comparisons that gate nothing:

  D. BOSS TAXONOMY -- our per-class boss histogram (`boss_taxonomy.BOSS_CLASS_COUNTS`, derived
     from OUR map tiles / roster / EMEVD) beside the number of HIS SLOTS carrying the equivalent
     tag name. Ours counts bosses, his counts item slots; the point is to notice a MISSING FAMILY.
  E. REACHABILITY COVERAGE -- one line: how many regions and grace-warp groups our logic graph can
     express reaching, against how many areas his graph has. His number is an integer computed at
     run time from his checkout; nothing of his graph is read beyond its length.
  F. MISSABLE -- our `MISSABLE_LOCATIONS` flags against his Event-scope slots tagged `missable`.
     Never a gate: he tags a SLOT ("do not randomize into oblivion"), we tag a CHECK ("may not host
     REQUIRED progression"), so a one-sided flag is a worklist entry, not a disagreement.

🛑 LICENCE BOUNDARY -- NON-NEGOTIABLE. SoulsRandomizers is "mostly all rights reserved" (LICENSE.md,
"SoulsRandomizers License, Version 1.0", Matthew Gruen). Clause 3 licenses viewing and reproducing
his unmodified sources; clause 4 licenses private, non-conveyed local use of files produced from
them. CONVEYANCE is what is forbidden -- so:

  * NOTHING from his tree is committed here. No slot rows, no location `Text` (his prose, explicitly
    copyrighted in the header of itemslots.txt), no area names, no tag strings as expectation data,
    no file copies. The allowlists below are BARE INTEGER EVENT FLAGS with comments we wrote
    ourselves: a flag id is a fact about the game, not an excerpt of his table.
  * Diagnostics print OUR location name / ap_id / flag, and from his side ONLY the flag id and the
    tag names that acted as filter vocabulary. Never his descriptions.
  * The SHIPPED apworld never imports this tool or his data. This is `tools/`, opt-in, dev/CI only,
    reading a LOCAL checkout that the user (or a manual CI job) placed on disk at a pinned commit.
  * There is no CI job on pull_request. A missing checkout must never block a merge -- hence SKIP.

Usage:
    python tools/matt_oracle.py --souls-rando-dir <local SoulsRandomizers checkout>
    SOULS_RANDO_DIR=<checkout> python tools/matt_oracle.py --report
    python tools/matt_oracle.py --json oracle.json      # CI artefact

Exit 0 when every disagreement is allowlisted (or the checkout is absent -- SKIP), 1 otherwise.
Requires PyYAML. AP-free: the tables are loaded as plain modules, never through Archipelago.
"""
import argparse
import importlib.util
import json
import os
import re
import sys
from collections import Counter, defaultdict


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REGION_QUEUE = os.path.join(REPO, "greenfield", "evidence", "oracle-region-queue.tsv")
DEFAULT_MISSABLE_QUEUE = os.path.join(REPO, "greenfield", "evidence", "oracle-missable-queue.tsv")


# ---------------------------------------------------------------------------
# A. ITEM IDENTITY -- known disagreements on item_ids.LOCATION_ITEM.
#
# Bare event-flag integers, grouped by CAUSE. Reasons are ours; the flag numbers are game facts.
# A flag listed here that now AGREES is reported as stale (warning, not a failure) so the list
# shrinks as the tables converge.
# ---------------------------------------------------------------------------
# --- CLASS SETS. Every flag below resolves to exactly one reason string via the merges at the end
# of this block. The bulk classes are grouped rather than repeated line-by-line because their reason
# IS the class: 45 copies of the same sentence is not 45 pieces of evidence. Class A no longer has
# one: `_A_OPEN_DLC_MATERIAL`'s 99 DLC upgrade-material rows were the stale `region_map.csv`
# `item_name` capture, not a datamine question, and gen_data's lot-reconcile pass closed all 99.

_B_SCOPE_MAP_FRAGMENT = frozenset({    # 24 flags
    62010, 62011, 62012, 62020, 62021, 62022,
    62030, 62031, 62032, 62040, 62041, 62050,
    62051, 62052, 62060, 62061, 62062, 62063,
    62064, 62080, 62081, 62082, 62083, 62084,
})

# `_B_OPEN` is GONE, not emptied (roadmap item 3). Every one of its 45 flags is classified
# below; an empty set named OPEN would read as "nothing found yet" instead of "triaged".

# --- SCOPE, FORAGER BROOD GIFTS (13). One NPC-gift family, split across two flag bands. The seven
# cookbook flags are gen_data's `_UNPLACEABLE_DLC_COOKBOOKS`: ESD/scripted gifts that no DLC
# datamine ever places (no MSB treasure, no merchant row, no enemy lot, no EMEVD award), so rather
# than strand them at a guessed Gravesite region or lie to the logic via HUB they stay VANILLA
# pickups. The six 4007xx flags are the MATERIAL half of the same gifts and pair with the cookbook
# lots one-for-one in flag_lots.tsv -- 107501/107511/107521/107531/107541/107551 against cookbook
# lots 107500/107510/107520/107530/107540/107550 -- so they inherit the same ruling; the derivation
# refuses them too ("no evidence in ANY corpus").
_B_SCOPE_FORAGER_BROOD = frozenset({
    68510, 68520, 68530, 68540, 68550, 68560, 68830,
    400750, 400751, 400752, 400753, 400754, 400755,
})

# --- SCOPE, UNPLACED COMMON-EVENT AWARDS (26). region_map.csv files each of these
# `Global / Common-event (unplaced)`, method `global`. A 4xxxxx/5xxxxx flag self-encodes no map, so
# gen_data's `_recover_tile` returns None and `_recover_row_ok` drops the row. The escape hatches
# are a DERIVED tile (tools/datamine_unplaced_globals.py -> unplaced_global_tiles.tsv) or a hand pin
# in gen_data.GLOBAL_RECOVER backed by a concrete game-data or in-game witness. Every one of these
# 26 is a CANDIDATE the derivation examined and REFUSED, by its own three reasons:
#   * talk ESD names only a common bucket, and m60_00_00_00 is not a place (9)
#   * ambiguous across 2-5 maps -- an NPC that relocates, refused rather than guessed (14)
#   * no evidence in ANY corpus (3)
# These are the ONLY residual REAL-GAP debt in class B, and the bar to closing one is a witness, not
# a bin. 530935 already has its witness (boblerrr, 2026-08-07: he collected lots 30935 and 30950 on
# one character and got a check from the first only) and still has no region.
_B_SCOPE_UNPLACED_GLOBAL = frozenset({
    60270, 400030, 400060, 400069, 400100, 400102, 400140, 400141, 400143,
    400145, 400170, 400171, 400172, 400181, 400182, 400189, 400271, 400293,
    400294, 400331, 400332, 400334, 400420, 400421, 400451, 530935,
})

# --- SCOPE, SCATTERED FILLER (3). Filed `Global / Filler (scattered by design)`, method
# `global_filler`: an upgrade stone the game hands out from many sites on one shared flag. Not
# "unplaced" -- unplaced_globals does not even take them as candidates -- and not one site we could
# name. gen_data's SKIP set drops the method by design.
_B_SCOPE_SCATTERED_FILLER = frozenset({400150, 400161, 400422})

# --- SCOPE, RULED NOT-FINDABLE (2). Both already carry a named gen_data ruling with a keeper test:
#   1050567820 Graven-Mass Talisman (Albinauric Rise) -- `_UNREACHABLE_DEAD`, excluded as dead.
#   2048467701 Furnace Visage -- `_WORLDLESS_SINGLES`, the re-derived not-findable census
#              (test_gf_worldless_singles.py rebuilds the class every run).
_B_SCOPE_NOT_FINDABLE = frozenset({1050567820, 2048467701})


ITEM_IDENTITY_KNOWN = {
    # --- BUNDLE (3). His slot is one multi-item item lot and he names a different member of it; we
    # expose the lot's individual awards. Neither side is wrong -- the two models disagree about what
    # a "slot" is. No same-family tier conflict in these three, so nothing to adjudicate.
    400061: "BUNDLE: multi-item lot, he names a different member of the same lot",
    400209: "BUNDLE: multi-item lot, he names a different member of the same lot",
    400309: "BUNDLE: multi-item lot, he names a different member of the same lot",

    # --- KEYING (1). His 177/197 split gives Rennala's Remembrance its own flag; we key both the
    # Remembrance and the Great Rune of the Unborn onto 197. Same pickup, different filing.
    197: "KEYING: his 177/197 split -- we carry both Rennala awards on flag 197",

    # --- BUNDLE (3 more), adjudicated against ItemLotParam 2026-09-08. Read as "our rows are
    # likely wrong" when the tool landed; they are not. Each of these three flags fires TWO map
    # lots -- an incantation AND one All-Knowing armour piece (102820+102861, 102830+102862,
    # 102850+102864). Both members are real awards of the one flag, he names one and we name the
    # other, so this is the same modelling difference as 400061/400209/400309, not a wrong row.
    400282: "BUNDLE: flag fires two map lots (an incantation and an armour piece); he names the "
            "other member -- verified against ItemLotParam_map",
    400283: "BUNDLE: flag fires two map lots (an incantation and an armour piece); he names the "
            "other member -- verified against ItemLotParam_map",
    400285: "BUNDLE: flag fires two map lots (an incantation and an armour piece); he names the "
            "other member -- verified against ItemLotParam_map",

    # --- OPEN (1), narrowed by the same adjudication. Both of this flag's map lots (103500, 103580)
    # award the SAME goods id, and that id is the sorcery our row names -- so OUR side is corroborated
    # by the param and it is HIS row that names something the flag does not award. Left OPEN rather
    # than closed because "his table is wrong" is a claim about HIS data, which this tool is not
    # entitled to make; the disagreement is real and stays visible.
    400358: "OPEN: both of this flag's map lots award the sorcery we name (verified against "
            "ItemLotParam_map); his row names a weapon the flag does not award",
}


MISSING_SLOT_KNOWN = {
    # --- KEYING (7), not a gap. The six Great Rune ACTIVATION flags at the Divine Tower interiors,
    # plus Rennala's Remembrance. We deliver the six Great Runes on the boss-defeat flags 171-176 and
    # Rennala's award on 197, so the pickup exists on our side under a different flag. Rows here
    # would double-count the runes.
    177: "KEYING: Rennala's Remembrance -- we carry this pickup on flag 197",
    191: "KEYING: Godrick Great Rune activation -- we carry the rune on boss flag 171",
    192: "KEYING: Radahn Great Rune activation -- we carry the rune on boss flag 172",
    193: "KEYING: Morgott Great Rune activation -- we carry the rune on boss flag 173",
    194: "KEYING: Rykard Great Rune activation -- we carry the rune on boss flag 174",
    195: "KEYING: Mohg Great Rune activation -- we carry the rune on boss flag 175",
    196: "KEYING: Malenia Great Rune activation -- we carry the rune on boss flag 176",

    # --- SCOPE (4). Auto-granted starting kit, and one gesture. The Spectral Steed Whistle is not a
    # check for us at all -- Torrent is delivered by its own mechanism -- and the two multiplayer
    # consumables are handed to the player at the tutorial. `O Mother` is a gesture; gestures are a
    # class he mostly does not model as slots (see EXCLUDED_TAGS' note), and this one we do not.
    60100: "SCOPE: Spectral Steed Whistle -- Torrent is delivered by its own mechanism, not a check",
    60250: "SCOPE: auto-granted multiplayer starting consumable, not a world pickup",
    60310: "SCOPE: auto-granted multiplayer starting consumable, not a world pickup",
    1032500030: "SCOPE: a gesture; this pickup is not part of our check universe",
}
# --- SCOPE, MAP FRAGMENTS (24). Map fragments are deliberately outside our item pool: gen_data's
# _FILLER_NAME_GUARD lists "Map:" and no `Map:` item exists in ITEM_CATALOG or LOCATION_ITEM at all.
# Their absence from LOCATIONS is the design, not a gap.
MISSING_SLOT_KNOWN.update(
    {f: "SCOPE: map fragment -- gen_data guards `Map:` out of the item pool by design"
     for f in _B_SCOPE_MAP_FRAGMENT}
)
# --- The class-B triage (roadmap item 3). The 45 flags that were `_B_OPEN` resolved to 1 KEYING and
# 44 SCOPE. NONE of them is addable through the derivation ladder today, and the reason is the same
# in every group: gen_data already refuses each one under a NAMED, comment-documented exclusion, or
# the region derivation examined it and refused to guess. Writing a region by hand for any of them
# would be inventing the one fact the ladder says it does not have.
MISSING_SLOT_KNOWN.update(
    {f: "SCOPE: Forager Brood NPC gift -- gen_data._UNPLACEABLE_DLC_COOKBOOKS keeps this family "
        "vanilla; no corpus places it"
     for f in _B_SCOPE_FORAGER_BROOD}
)
MISSING_SLOT_KNOWN.update(
    {f: "SCOPE: unplaced common-event award -- flag encodes no map tile and "
        "datamine_unplaced_globals REFUSES it (common bucket / ambiguous / no evidence); a hand pin "
        "in GLOBAL_RECOVER needs a witness we do not have"
     for f in _B_SCOPE_UNPLACED_GLOBAL}
)
MISSING_SLOT_KNOWN.update(
    {f: "SCOPE: global_filler -- one shared flag scattered across many sites by design; gen_data's "
        "SKIP set drops the method"
     for f in _B_SCOPE_SCATTERED_FILLER}
)
MISSING_SLOT_KNOWN.update(
    {f: "SCOPE: ruled not-findable -- gen_data._UNREACHABLE_DEAD / _WORLDLESS_SINGLES, each with a "
        "keeper test"
     for f in _B_SCOPE_NOT_FINDABLE}
)
# --- KEYING (1). gen_data._SHEET_DROPS: there is exactly ONE Academy Glintstone Key in the game and
# we carry it as the Liurnia overworld pickup on flag 1034457100. The m14 flag is a phantom
# duplicate, dropped so the key stays a singleton -- a row here would make it two.
MISSING_SLOT_KNOWN[14007930] = (
    "KEYING: phantom second Academy Glintstone Key -- we carry the game's only one on flag 1034457100"
)


# Tag vocabulary used as a FILTER (not stored as expectation data). Slots carrying any of these are
# outside the set of checks we model at all, so their absence from data.LOCATIONS is by design:
#   norandom / ignore -- his own "never put a randomized check here" vocabulary
#   tarnished         -- Tarnished-Pack mod content; not vanilla Elden Ring
#   enemy*            -- enemy-drop slots (enemyweapon/enemygem/enemysorcery/... subtypes). A
#                        separate derivation, not a gap in LOCATIONS: ours is
#                        `greenfield/enemy_drops.tsv` (tools/datamine_enemy_drops.py), from
#                        NpcParam/ItemLotParam_enemy. `--report` COUNT-CHECKS the two (class C
#                        below) rather than demanding row equality -- his slot is a randomiser
#                        placement, ours is a param row, and they do not partition the same way.
# NOTE ON GESTURES: he has no `gesture` tag, because he does not model gestures as slots at all.
# The gesture asymmetry runs the OTHER way (OUR flags he lacks) and is report-only.
EXCLUDED_TAGS = frozenset({"norandom", "ignore", "tarnished"})
EXCLUDED_TAG_PREFIXES = ("enemy",)

# ---------------------------------------------------------------------------
# D. BOSS TAXONOMY -- report-only histogram (docs/MATT-ORACLE-ROADMAP.md item 7, second bullet).
#
# OUR class (boss_taxonomy.BOSS_CLASS_COUNTS, derived from our map tiles / roster / EMEVD) beside
# the number of HIS SLOTS carrying the equivalent tag. The tag NAMES are filter vocabulary, exactly
# as EXCLUDED_TAGS above already uses them -- no row, Text or area name of his is read or printed.
#
# 🛑 THE TWO NUMBERS COUNT DIFFERENT THINGS AND THE REPORT SAYS SO. Ours is BOSSES (one row per
# defeat flag). His is ITEM SLOTS carrying the tag, so a boss that drops three tagged items counts
# three times and a boss that drops nothing counts zero. This is a SANITY check on the shape of the
# roster -- "did we miss a whole family" -- and never an equality gate.
BOSS_TAG_FOR_CLASS = {
    "remembrance_main": "remembranceboss",
    "dragon": "dragonboss",
    "furnace_golem": "furnacegolem",
    "evergaol": "evergaol",
    "overworld_field": "overworldboss",
    "legacy_dungeon": None,        # he has no legacy-dungeon tag; his `boss`/`altboss` span both
    "catacomb": "catacombboss",
    "heros_grave": "graveboss",
    "cave": "caveboss",
    "tunnel": "tunnelboss",
    "gaol": "gaolboss",
}
# His umbrella tag over the five mini-dungeon families, kept as one extra line rather than folded
# into any single class: it is the aggregate our cave+catacomb+grave+tunnel+gaol classes answer.
MINIDUNGEON_TAG = "minidungeonboss"

# The fraction of divergence worth a line of prose in the report.
CLASS_DIVERGENCE = 0.10


def boss_tag_counts(rows, tags):
    """tag name -> number of his slots carrying it. Counts only, never his rows."""
    out = Counter()
    for r in rows:
        for t in tags:
            if t in r["tags"]:
                out[t] += 1
    return out


def his_area_count(souls_dir):
    """K -- how many areas his logic graph has, computed at RUN TIME from his checkout.

    🛑 The ONLY thing this oracle takes from his graph. It is an integer, it is never written to a
    file in this repo, and no Req expression or area name is read, adapted or printed. Authoring
    our own logic is the whole point of the roadmap item; the count is a coverage yardstick.
    """
    import yaml

    path = os.path.join(souls_dir, "diste", "Base", "annotations.txt")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    areas = doc.get("Areas") or []
    return len(areas)


def our_reach():
    """(regions, grace-warp groups) our logic graph can express reaching.

    Regions are `region_groups.REGION_GROUPS` -- every node core.py can build and gate, the hub
    included. Grace-warp groups are `region_graces.REGION_GRACE_LANDMARKS` flattened: one warp
    grace per warp-menu sub-area, which is the finest granularity our region locks address.
    """
    rg_path = os.path.join(REPO, "greenfield", "region_groups.py")
    spec = importlib.util.spec_from_file_location("_matt_oracle_region_groups", rg_path)
    rg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rg)
    graces = _load_table(REPO, "region_graces")
    return len(rg.REGION_GROUPS), sum(len(v) for v in graces.REGION_GRACE_LANDMARKS.values())


def _excluded_by_tags(tags):
    if tags & EXCLUDED_TAGS:
        return True
    return any(t.startswith(EXCLUDED_TAG_PREFIXES) for t in tags)


# ---------------------------------------------------------------------------
# His table
# ---------------------------------------------------------------------------
# DebugText lines look like `<Vanilla Item Name> - lot 10010[...]` / `... - shop 100[...]`.
_NAME_RE = re.compile(r"^'?(.+?) - (?:lot|shop) \d+\[")

SCOPE_EVENT = 0        # LocationData.ScopeType.Event -- UniqueID is the item-lot/shop event flag
SCOPE_SHOP_INFINITE = 3


def parse_itemslots(path):
    """Parse his itemslots.txt into plain dicts. Never returns his Text/Area/Comment prose."""
    import yaml

    with open(path, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    rows = []
    for slot in doc["Slots"]:
        # Key is '<sortPrefix>,<Type>:<UniqueID 10-digit>:<ShopIDs csv>:<ModelLots csv>'.
        # LocationData.LocationScope zeroes the id for shop-ONLY slots in ER, so flag 0 means
        # "keyed on shop lineup ids, not on a flag" -- out of scope for both checks here.
        key = slot["Key"].split(",", 1)[1]
        stype, uid, shops, lots = key.split(":")
        names = []
        for line in slot.get("DebugText") or []:
            m = _NAME_RE.match(line.strip())
            if m:
                names.append(m.group(1).strip().strip("'"))
        rows.append(
            {
                "stype": int(stype),
                "flag": int(uid),
                "shop_ids": [int(x) for x in shops.split(",") if x],
                "tags": frozenset((slot.get("Tags") or "").split()),
                "item_names": names,
                # 🛑 `area` is his area TOKEN, held in memory as a PARTITION LABEL only -- the same
                # standing `tags` already has as filter vocabulary. It is never printed, never
                # written to JSON and never written to the queue tsv: check_region_queue folds it
                # away into an opaque cluster id before anything leaves this process. See
                # region_area_map() for why the label itself carries no information we keep.
                "area": (slot.get("Area") or "").strip(),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Our tables
# ---------------------------------------------------------------------------
def _load_table(repo, name):
    path = os.path.join(repo, "greenfield", "eldenring", "tables", name + ".py")
    spec = importlib.util.spec_from_file_location("_matt_oracle_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_missable_flags(repo=REPO, by_flag=None):
    """(flags, n_rows) -- the FLAGS our missable_locations table tags, via data.LOCATIONS.

    MISSABLE_LOCATIONS is keyed on ap_id; the join below is on the flag number space, so map each
    tagged ap_id back to its flag. Rows whose ap_id has no LOCATIONS entry (there should be none)
    are dropped rather than guessed at.
    """
    miss = _load_table(repo, "missable_locations")
    data = _load_table(repo, "data")
    ap_flag = {}
    for entries in data.LOCATIONS.values():
        for _name, ap_id, flag in entries:
            ap_flag[ap_id] = flag
    flags, n_rows = set(), 0
    for ap_id in miss.MISSABLE_LOCATIONS:
        n_rows += 1
        if ap_id in ap_flag:
            flags.add(ap_flag[ap_id])
    return flags, n_rows


# `missable` is used here as FILTER VOCABULARY ONLY -- the same way EXCLUDED_TAGS is. No tag string
# of his is stored as expectation data, and nothing but bare flag integers is printed.
MISSABLE_TAG = "missable"


def check_missable(rows, by_flag, ours_flags):
    """Report-only join: our missable flags vs his Event-scope slots tagged `missable`.

    Structural, not factual: he tags a SLOT, we tag a CHECK, and the two curations were built for
    different jobs (his for "don't randomize this into oblivion", ours for "this may not host
    REQUIRED progression"). So this never gates -- it is a worklist, not an expectation.

    Returns (joinable, agree, his_only, ours_only): joinable is his missable-tagged flags that
    data.LOCATIONS carries a row for; agree is the intersection with ours; his_only / ours_only are
    the two one-sided sets, as sorted flag ids.
    """
    his = {r["flag"] for r in rows
           if r["stype"] == SCOPE_EVENT and r["flag"] and MISSABLE_TAG in r["tags"]}
    joinable = his & set(by_flag)
    agree = joinable & ours_flags
    return (sorted(joinable), sorted(agree), sorted(joinable - ours_flags),
            sorted(ours_flags - agree))


def load_ours(repo=REPO):
    """(by_flag, location_item). by_flag: flag -> [(region, name, ap_id), ...]."""
    data = _load_table(repo, "data")
    item_ids = _load_table(repo, "item_ids")
    by_flag = defaultdict(list)
    for region, entries in data.LOCATIONS.items():
        for name, ap_id, flag in entries:
            by_flag[flag].append((region, name, ap_id))
    return dict(by_flag), dict(item_ids.LOCATION_ITEM)


# ---------------------------------------------------------------------------
# The two checks
# ---------------------------------------------------------------------------
def check_item_identity(rows, by_flag, location_item):
    """Disagreements where both sides name a vanilla item for the same flag.

    Returns (disagreements, agreed, not_comparable). A disagreement is
    {flag, ap_id, region, ours, theirs(list of his item names), known(reason or None)}.
    """
    matt = {r["flag"]: r for r in rows if r["stype"] == SCOPE_EVENT and r["flag"]}
    dis, agreed, nocmp = [], 0, 0
    for flag in sorted(set(matt) & set(by_flag)):
        theirs = set(matt[flag]["item_names"])
        if not theirs:
            nocmp += 1
            continue
        for region, name, ap_id in by_flag[flag]:
            ours = location_item.get(ap_id)
            if not ours:
                nocmp += 1
            elif ours in theirs:
                agreed += 1
            else:
                dis.append(
                    {
                        "flag": flag,
                        "ap_id": ap_id,
                        "region": region,
                        "name": name,
                        "ours": ours,
                        "theirs": sorted(theirs),
                        "known": ITEM_IDENTITY_KNOWN.get(flag),
                    }
                )
    return dis, agreed, nocmp


def check_missing_slots(rows, by_flag):
    """His Event-scope flags with no data.LOCATIONS row, minus the tag-excluded classes.

    Returns (missing, excluded_count). A missing entry is
    {flag, tags(sorted filter vocabulary), known(reason or None)}.
    """
    missing, excluded = [], 0
    seen = set()
    for r in rows:
        if r["stype"] != SCOPE_EVENT or not r["flag"] or r["flag"] in by_flag:
            continue
        if r["flag"] in seen:
            continue
        seen.add(r["flag"])
        known = MISSING_SLOT_KNOWN.get(r["flag"])
        # Allowlist first: an entry we explained by hand stays visible even when a tag would also
        # have hidden it, so it is never silently double-excused and its staleness stays checkable.
        if known is None and _excluded_by_tags(r["tags"]):
            excluded += 1
            continue
        missing.append({"flag": r["flag"], "tags": sorted(r["tags"]), "known": known})
    return sorted(missing, key=lambda m: m["flag"]), excluded


# ---------------------------------------------------------------------------
# G. REGION QUEUE (report-only, and the input to a HUMAN review queue)
#
# The two tables partition the same flags into areas/regions by two different models, so equality
# is not the test and never will be. What IS evidence is a row that falls OUTSIDE its own cluster:
# take his partition as an unlabelled clustering, ask which of OUR regions the rest of the cluster
# sits in, and a row that disagrees with its own neighbours is a row worth a human look.
#
# 🛑 LICENCE BOUNDARY, in the shape of the algorithm. His area label is used as an EQUIVALENCE KEY
# and nothing else -- the mapping it produces is built from OUR regions, and the label is discarded
# before any output. The queue records, per OUR ap_id, only the bare fact "the second source's
# partition disagrees here". No area name, no Text, no tags, no counts of his. A reviewer rules
# from our own evidence (map tile, nearest grace, wiki second opinion), never from his sheet.
# ---------------------------------------------------------------------------
# The two DLC-membership rows: base-game Roundtable Hold on our side, DLC on his. They are queued
# unconditionally so a partition that happens to agree cannot drop them (roadmap item 4).
DLC_MEMBERSHIP_FLAGS = frozenset({520800, 530950})

BASIS_REGION = "second-source-region-disagrees"
BASIS_DLC = "second-source-dlc-membership-disagrees"

QUEUE_STATUSES = ("open", "confirmed-ours", "moved")
QUEUE_COLUMNS = ("flag", "ap_id", "our_region", "basis", "status", "reviewer", "note")


def region_area_map(rows, by_flag):
    """His area key -> the ONE of our regions its joined rows mostly sit in.

    A strict plurality is required: a cluster split evenly between two of our regions says nothing
    about any single row in it, so it maps to nothing and contributes no queue entries.
    """
    votes = defaultdict(Counter)
    for r in rows:
        if r["stype"] != SCOPE_EVENT or not r["flag"] or not r["area"]:
            continue
        for region, _name, _ap in by_flag.get(r["flag"], ()):
            votes[r["area"]][region] += 1
    mapped = {}
    for area, counter in votes.items():
        top = counter.most_common(2)
        if len(top) == 1 or top[0][1] > top[1][1]:
            mapped[area] = top[0][0]
    return mapped, len(votes)


def check_region_queue(rows, by_flag):
    """(queue, joined, areas, mapped_areas). Queue entries are OURS ONLY:
    {flag, ap_id, our_region, basis}."""
    mapped, areas = region_area_map(rows, by_flag)
    seen_area = {}
    for r in rows:
        if r["stype"] == SCOPE_EVENT and r["flag"] and r["area"]:
            seen_area.setdefault(r["flag"], r["area"])
    queue, joined = {}, 0
    for flag, area in seen_area.items():
        theirs = mapped.get(area)
        if theirs is None:
            continue
        for region, _name, ap_id in by_flag.get(flag, ()):
            joined += 1
            if region != theirs:
                queue[(flag, ap_id)] = {"flag": flag, "ap_id": ap_id, "our_region": region,
                                        "basis": BASIS_REGION}
    for flag in sorted(DLC_MEMBERSHIP_FLAGS):
        for region, _name, ap_id in by_flag.get(flag, ()):
            queue[(flag, ap_id)] = {"flag": flag, "ap_id": ap_id, "our_region": region,
                                    "basis": BASIS_DLC}
    return [queue[k] for k in sorted(queue)], joined, areas, len(mapped)


QUEUE_HEADER = """# oracle-region-queue.tsv -- HUMAN REVIEW QUEUE for the checks whose region the second source's
# own partition disagrees with. AUTO-REFRESHED by `tools/matt_oracle.py --region-queue` against a
# LOCAL thefifthmatt/SoulsRandomizers checkout; the status/reviewer/note columns are the only
# hand-edited ones and are carried across a refresh by (flag, ap_id).
#
# 🛑 LICENCE BOUNDARY. Nothing in this file is his. Every column is OUR flag, OUR ap_id, OUR region
# name, or a reviewer's own words. The `basis` column records ONLY that a second source's partition
# disagrees for that flag -- never which area it names, never its Text, never its tags. Rule from
# OUR evidence (map tile, nearest grace and the region that grace maps to, wiki second opinion in
# check_region_second_opinion.tsv), not from his sheet. See AGENTS.md "MATT ORACLE".
#
# THIS FILE IS NOT A DEFECT LIST and not a fix list. A disagreement is a question. `confirmed-ours`
# is as real an outcome as `moved`, and the two DLC-membership rows are queued unconditionally.
#
# status:   open | confirmed-ours | moved
# reviewer: who ruled it (free text; two reviewers work the queue, so say which one)
# note:     the reviewer's own reason, in our words
#
# Ruled rows are FIXED elsewhere: the normal derivation ladder (M61_TILE_CURATED,
# DUNGEON_REGION_CURATED, region_overrides.tsv only as a last resort). Never by editing data.py.
"""


def read_queue(path):
    """Committed queue -> {(flag, ap_id): row}. Missing file is an empty queue, not an error.

    Shared by BOTH review queues: the (flag, ap_id) key and the three hand-edited columns are the
    whole mechanism, and the derived columns in between differ per queue. Reading off the file's
    own header row rather than a constant is what lets one reader serve both.
    """
    out = {}
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8") as fh:
        header = None
        for line in fh:
            if line.startswith("#"):
                continue
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            if header is None:
                header = parts
                continue
            row = dict(zip(header, parts))
            try:
                out[(int(row["flag"]), int(row["ap_id"]))] = row
            except (KeyError, ValueError):
                continue
    return out


# The three HAND-EDITED columns, identical in both queues. Everything before them is derived and
# is overwritten on every refresh; these three are the reviewer's and are carried across by
# (flag, ap_id). Splitting the column list this way is what makes one writer serve both queues.
CARRIED_COLUMNS = ("status", "reviewer", "note")


def write_queue(path, queue, previous, header, columns):
    """Refresh a review queue in place, preserving verdicts. Returns (kept, added, dropped).

    `columns` is the queue's full column order, ending in CARRIED_COLUMNS. Derived cells come from
    the freshly computed `queue` entries; the carried ones come from `previous`, keyed on
    (flag, ap_id), so a reviewer's ruling survives a refresh and a row that stops disagreeing
    simply leaves. A row's verdict is NOT resurrected if it comes back: it returns as `open`,
    because the evidence that produced it was recomputed.
    """
    derived = [c for c in columns if c not in CARRIED_COLUMNS]
    lines = [header.rstrip("\n"), "\t".join(columns)]
    added = 0
    for entry in queue:
        old = previous.get((entry["flag"], entry["ap_id"]))
        if old is None:
            added += 1
        lines.append("\t".join(
            [str(entry[c]) for c in derived]
            + [(old or {}).get("status") or "open",
               (old or {}).get("reviewer", ""),
               (old or {}).get("note", "")]))
    live = {(e["flag"], e["ap_id"]) for e in queue}
    dropped = sorted(k for k in previous if k not in live)
    # newline='\n' so a Windows refresh and a Linux refresh produce the SAME bytes.
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    return len(queue) - added, added, dropped


# Names kept for the region queue's own callers and tests; the mechanism is the pair above.
read_region_queue = read_queue


def write_region_queue(path, queue, previous):
    return write_queue(path, queue, previous, QUEUE_HEADER, QUEUE_COLUMNS)


# ---------------------------------------------------------------------------
# H. MISSABLE QUEUE (report-only, and the input to the SECOND human review queue)
#
# Same mechanism as C, different evidence. `MISSABLE_LOCATIONS` is the set of checks behind which
# gen_data forbids required progression, and getting it WRONG IN EITHER DIRECTION is expensive: a
# missing tag can strand a seed behind a consumable a player already spent, and a spurious one
# permanently narrows the fill for no reason. It has exactly one second opinion -- his `missable`
# tag -- and the two were curated from the same game by different people.
#
# The queue is the intersection of three things, all of which must hold:
#   1. a second source tags the flag missable,   2. OUR MISSABLE_LOCATIONS does not, and
#   3. OUR OWN greenfield/questline_conditions.tsv shows the award gated on a DIALOGUE_STEP,
#      NPC_STATE or ITEM_POSSESSION root -- the three condition classes that describe a gate a
#      player can permanently lose (an NPC's dialogue advanced past it, an NPC dead, an item spent).
#
# Condition 3 is what makes the row a QUESTION rather than noise. Without it, a bare tag
# disagreement is just two models drawing the missable line in different places, of which there are
# ~68; with it, our OWN extraction independently says there is a losable gate here, and the second
# source agrees, and our table does not. That is a disagreement worth a person's time.
#
# 🛑 LICENCE BOUNDARY, again in the shape of the algorithm. His `missable` tag is used as FILTER
# VOCABULARY and nothing else -- the same standing EXCLUDED_TAGS already has. It selects which of
# OUR flags to look at; every column written out is then ours (our flag, our ap_id, our location
# name, our condition classes), and `basis` records only THAT a second source disagrees.
# ---------------------------------------------------------------------------
MISSABLE_TAG = "missable"
BASIS_MISSABLE = "second-source-missable-disagrees"

# The three questline-condition root classes that describe a PERMANENTLY LOSABLE gate. Every other
# root class in questline_conditions.tsv (BOSS_KILL, REGION_ACCESS, FLAG_BAND, ...) describes a
# gate that stays satisfiable, so it says nothing about missability and does not qualify a row.
MISSABLE_CONDITION_CLASSES = ("DIALOGUE_STEP", "ITEM_POSSESSION", "NPC_STATE")

MISSABLE_QUEUE_STATUSES = ("open", "confirmed-not-missable", "missable")
MISSABLE_QUEUE_COLUMNS = ("flag", "ap_id", "our_name", "our_conditions", "basis",
                          "status", "reviewer", "note")


def load_missable_aps(repo=REPO):
    """OUR MISSABLE_LOCATIONS, as a set of ap_ids. Loaded as a plain module, never through AP."""
    return frozenset(_load_table(repo, "missable_locations").MISSABLE_LOCATIONS)


def questline_condition_classes(repo=REPO, classes=MISSABLE_CONDITION_CLASSES):
    """OUR questline_conditions.tsv -> {target flag: (qualifying root classes, sorted)}.

    🛑 A ROW IS A COND ROOT, NOT A VERDICT (that table's own header). A qualifying class means our
    extractor SAW a losable gate on the award site, not that the check is missable -- which is
    exactly why this feeds a review queue and not a derivation.
    """
    wanted, out = frozenset(classes), defaultdict(set)
    path = os.path.join(repo, "greenfield", "questline_conditions.tsv")
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        header = None
        for line in fh:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if header is None:
                header = parts
                continue
            row = dict(zip(header, parts))
            if row.get("root_class") not in wanted:
                continue
            try:
                out[int(row["target_flag"])].add(row["root_class"])
            except (KeyError, ValueError, TypeError):
                continue
    return {flag: tuple(sorted(cls)) for flag, cls in out.items()}


def check_missable_queue(rows, by_flag, repo=REPO, missable_aps=None, conditions=None):
    """(queue, theirs, ours, joinable). Queue entries are OURS ONLY:
    {flag, ap_id, our_name, our_conditions, basis}.

    `missable_aps` / `conditions` are injectable so the tests can drive this without loading the
    real tables; both default to ours on disk.
    """
    if missable_aps is None:
        missable_aps = load_missable_aps(repo)
    if conditions is None:
        conditions = questline_condition_classes(repo)
    theirs = {r["flag"] for r in rows
              if r["stype"] == SCOPE_EVENT and r["flag"] and MISSABLE_TAG in r["tags"]}
    queue, joinable = {}, 0
    for flag in sorted(theirs):
        entries = by_flag.get(flag)
        if not entries:
            continue                      # class B territory (missing slot), not this queue's
        joinable += 1
        # We already call some check on this flag missable: the two models AGREE about the flag,
        # and a per-ap difference here is our own multi-award granularity, not a second opinion.
        if any(ap_id in missable_aps for _region, _name, ap_id in entries):
            continue
        # The qualifying-class rule is applied HERE, not left to whoever built `conditions`.
        # It is part of the membership rule -- "our own extraction sees a permanently losable
        # gate" -- so a caller that hands over a wider table must not be able to widen the queue.
        # sorted() so the cell is a function of the SET, not of the input's iteration order: the
        # tsv is byte-diffed in CI, and a reordered cell would read as a real change.
        classes = tuple(sorted(c for c in conditions.get(flag, ())
                               if c in MISSABLE_CONDITION_CLASSES))
        if not classes:
            continue                      # no losable gate visible on OUR side: nothing to review
        for _region, name, ap_id in entries:
            queue[(flag, ap_id)] = {"flag": flag, "ap_id": ap_id, "our_name": name,
                                    "our_conditions": "+".join(classes), "basis": BASIS_MISSABLE}
    return [queue[k] for k in sorted(queue)], len(theirs), len(missable_aps), joinable


MISSABLE_QUEUE_HEADER = """# oracle-missable-queue.tsv -- HUMAN REVIEW QUEUE for the checks a second source tags MISSABLE,
# ours does not, and OUR OWN questline-condition extraction shows gated on a permanently losable
# root. AUTO-REFRESHED by `tools/matt_oracle.py --missable-queue` against a LOCAL
# thefifthmatt/SoulsRandomizers checkout; the status/reviewer/note columns are the only hand-edited
# ones and are carried across a refresh by (flag, ap_id).
#
# 🛑 LICENCE BOUNDARY. Nothing in this file is his. Every column is OUR flag, OUR ap_id, OUR
# location name, OUR questline-condition root classes, or a reviewer's own words. The `basis`
# column records ONLY that a second source tags this flag missable and we do not -- never its Text,
# never its area, never any other tag it carries. Rule from OUR evidence (the questline_conditions
# rows and what they depend on, the quest features that reference the flag), not from his sheet.
# See AGENTS.md "MATT ORACLE".
#
# THIS FILE IS NOT A DEFECT LIST. Two models drew the missable line in different places; a row here
# is a question. `confirmed-not-missable` is as real an outcome as `missable`.
#
# our_conditions: OUR questline_conditions.tsv root classes on this award site, '+'-joined. A root
#   is a gate our extractor SAW, never a proof that the check is missable -- see that file's header.
# status:   open | confirmed-not-missable | missable
# reviewer: who ruled it (free text; two reviewers work the queue, so say which one)
# note:     the reviewer's own reason. A `missable` verdict must name the MECHANISM in our own
#   words -- limited-consumable / killable-npc / questline-progress -- because gen_data's
#   MISSABLE_LOCATIONS values are a closed vocabulary (deathroot, alt_currency:N, gesture_award,
#   questline, questline_item) and a verdict that does not map onto one cannot be applied.
#
# 🛑 A `missable` verdict is APPLIED ELSEWHERE, in a later change, through the normal missable
# derivation in greenfield/gen_data.py. Never by editing tables/missable_locations.py, and never
# from this file: it is a review record, not a second missable source.
"""


def write_missable_queue(path, queue, previous):
    return write_queue(path, queue, previous, MISSABLE_QUEUE_HEADER, MISSABLE_QUEUE_COLUMNS)


def stale_entries(dis_flags, by_flag):
    """Allowlisted flags that no longer disagree -- warn so the lists shrink over time."""
    stale = []
    for flag, reason in sorted(ITEM_IDENTITY_KNOWN.items()):
        if flag not in dis_flags:
            stale.append(("ITEM_IDENTITY_KNOWN", flag, reason))
    for flag, reason in sorted(MISSING_SLOT_KNOWN.items()):
        # Stale means the GAP CLOSED: we now carry a row on that flag. A tag exclusion does not
        # make the entry stale (the slot is still absent from LOCATIONS, still for the same reason).
        if flag in by_flag:
            stale.append(("MISSING_SLOT_KNOWN", flag, reason))
    return stale


# ---------------------------------------------------------------------------
def report_taxonomy_and_reach(repo, souls_dir, rows):
    """Print D (boss-class histogram) and E (reachability coverage). Returns the JSON payload."""
    taxonomy = _load_table(repo, "boss_taxonomy")
    ours = dict(taxonomy.BOSS_CLASS_COUNTS)
    wanted = [t for t in BOSS_TAG_FOR_CLASS.values() if t] + [MINIDUNGEON_TAG]
    theirs = boss_tag_counts(rows, wanted)

    print("== D. BOSS TAXONOMY (boss_taxonomy.BOSS_CLASS_COUNTS) -- REPORT ONLY ==")
    print("ours = BOSSES (one per defeat flag); his = SLOTS carrying the tag. Not comparable as an")
    print("equality; a whole family missing on either side is what this is looking for.")
    print("  %-17s %6s  %-16s %6s  %s" % ("our class", "bosses", "his tag", "slots", "note"))
    diverged = []
    for cls in taxonomy.BOSS_CLASSES:
        n = ours.get(cls, 0)
        tag = BOSS_TAG_FOR_CLASS.get(cls)
        k = theirs.get(tag) if tag else None
        note = ""
        if cls in taxonomy.UNDERIVED_CLASSES:
            note = "UNDERIVED -- " + taxonomy.UNDERIVED_CLASSES[cls].split(":", 1)[0]
        elif tag is None:
            note = "no equivalent tag"
        elif k is None:
            # The tag exists in his vocabulary but no slot in THIS checkout carries it, so there is
            # no count to diverge from. Say so and render the count as a dash, rather than letting
            # the divergence arithmetic meet a None. Always the case on a synthetic fixture, which
            # is exactly why D must survive it instead of taking E and F down with it.
            note = "n/a -- no slot of his carries the tag"
        elif max(n, k) and abs(n - k) > CLASS_DIVERGENCE * max(n, k):
            note = "DIVERGES >%d%%" % int(CLASS_DIVERGENCE * 100)
            diverged.append((cls, n, tag, k))
        print("  %-17s %6d  %-16s %6s  %s" % (cls, n, tag or "-", "-" if k is None else k, note))
    mini = sum(ours.get(c, 0) for c in ("cave", "catacomb", "heros_grave", "tunnel", "gaol"))
    print("  %-17s %6d  %-16s %6d  our five mini-dungeon classes vs his umbrella tag"
          % ("(mini-dungeon)", mini, MINIDUNGEON_TAG, theirs.get(MINIDUNGEON_TAG, 0)))
    print("  total bosses classified: %d" % sum(ours.values()))
    print()

    print("== E. REACHABILITY COVERAGE -- REPORT ONLY ==")
    regions, groups = our_reach()
    areas = his_area_count(souls_dir)
    print("our graph reaches %d regions / %d grace-warp groups; his reaches %s areas"
          % (regions, groups, "?" if areas is None else areas))
    print("(his count is computed from his checkout at run time and is never committed here; no")
    print(" Req expression or area name of his is read, adapted or stored -- see the LICENCE note.)")
    print()

    return {
        "boss_classes": {c: ours.get(c, 0) for c in taxonomy.BOSS_CLASSES},
        "his_boss_tag_slots": dict(theirs),
        "underived_classes": sorted(taxonomy.UNDERIVED_CLASSES),
        "diverged_classes": [
            {"class": c, "ours": n, "his_tag": t, "his_slots": k} for c, n, t, k in diverged
        ],
        "reach": {"our_regions": regions, "our_grace_warp_groups": groups, "his_areas": areas},
    }


def enemy_drop_counts(rows, repo=REPO):
    """CLASS C -- ENEMY DROPS, REPORT-ONLY COUNT CHECK (roadmap item 7, first bullet).

    OUR side: the ONE-TIME (flagged) rows of `greenfield/enemy_drops.tsv` -- `getItemFlagId > 0` on
    a lot reachable from some `NpcParam.itemLotId_enemy`. HIS side: the slots tagged `enemy*`, the
    same vocabulary `_excluded_by_tags` already filters class B on.

    WHY THIS IS A COUNT AND NOT A GATE. His `enemy` tag marks a slot he chose to treat as an
    enemy drop for randomisation; ours is every param row the game flags one-time. Neither is a
    subset of the other by construction -- he tags event-awarded drops we file under a map lot, and
    we carry flagged NPC lots he never placed. Equality would be noise. What IS signal is the
    magnitude and the flag-join overlap: a large disagreement means one of us is reading the game
    wrong, and it is cheap to look at.

    🛑 LICENCE. Returns COUNTS from his side and OUR flag ids only -- never his flags, rows or
    prose. The `theirs_*` numbers are cardinalities, which are facts about the game, not his table.
    """
    src = os.path.join(repo, "tools", "datamine_enemy_drops.py")
    tsv = os.path.join(repo, "greenfield", "enemy_drops.tsv")
    if not os.path.isfile(src) or not os.path.isfile(tsv):
        return None
    spec = importlib.util.spec_from_file_location("_matt_oracle_enemy_drops", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ours = mod.flagged_flags(tsv)

    theirs_slots = [r for r in rows if any(t.startswith("enemy") for t in r["tags"])]
    theirs_flags = {r["flag"] for r in theirs_slots if r["flag"]}
    return {
        "ours_flags": ours,
        "theirs_slots": len(theirs_slots),
        "theirs_flags": len(theirs_flags),
        "overlap": ours & theirs_flags,
        "ours_only": ours - theirs_flags,
        "theirs_only": len(theirs_flags - ours),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--souls-rando-dir",
        default=os.environ.get("SOULS_RANDO_DIR"),
        help="local thefifthmatt/SoulsRandomizers checkout (default: $SOULS_RANDO_DIR)",
    )
    ap.add_argument("--repo", default=REPO, help="er-archipelago checkout (default: this one)")
    ap.add_argument("--report", action="store_true", help="print every diff, allowlisted or not")
    ap.add_argument("--json", dest="json_out", default=None, help="write a JSON summary here")
    ap.add_argument(
        "--region-queue", dest="region_queue", nargs="?", const=DEFAULT_REGION_QUEUE, default=None,
        metavar="PATH",
        help="refresh the human region-review queue tsv (default: %s). Verdict columns are "
             "preserved by (flag, ap_id)." % os.path.relpath(DEFAULT_REGION_QUEUE, REPO),
    )
    ap.add_argument(
        "--missable-queue", dest="missable_queue", nargs="?", const=DEFAULT_MISSABLE_QUEUE,
        default=None, metavar="PATH",
        help="refresh the human missable-review queue tsv (default: %s). Verdict columns are "
             "preserved by (flag, ap_id)." % os.path.relpath(DEFAULT_MISSABLE_QUEUE, REPO),
    )
    args = ap.parse_args(argv)

    d = args.souls_rando_dir
    slots = os.path.join(d, "diste", "Base", "itemslots.txt") if d else None
    if not d or not os.path.isdir(d) or not os.path.isfile(slots):
        print(
            "SKIP: no SoulsRandomizers checkout (pass --souls-rando-dir or set $SOULS_RANDO_DIR; "
            "expected <dir>/diste/Base/itemslots.txt). This oracle is opt-in and never blocks."
        )
        return 0

    rows = parse_itemslots(slots)
    by_flag, location_item = load_ours(args.repo)

    n_event = sum(1 for r in rows if r["stype"] == SCOPE_EVENT)
    n_shop = sum(1 for r in rows if r["stype"] == SCOPE_SHOP_INFINITE)
    print("matt slots: %d (Event %d, ShopInfinite %d) from %s"
          % (len(rows), n_event, n_shop, slots))
    print("our LOCATIONS: %d rows, %d distinct flags"
          % (sum(len(v) for v in by_flag.values()), len(by_flag)))
    print()

    dis, agreed, nocmp = check_item_identity(rows, by_flag, location_item)
    missing, excluded = check_missing_slots(rows, by_flag)

    unknown_dis = [d_ for d_ in dis if d_["known"] is None]
    unknown_missing = [m for m in missing if m["known"] is None]

    # --- A ---
    print("== A. ITEM IDENTITY (item_ids.LOCATION_ITEM) ==")
    total = agreed + len(dis)
    print("comparable rows %d: agree %d, disagree %d (%.1f%%), not comparable %d"
          % (total, agreed, len(dis), 100.0 * agreed / max(1, total), nocmp))
    print("disagreements: %d allowlisted, %d UNEXPLAINED"
          % (len(dis) - len(unknown_dis), len(unknown_dis)))
    reasons = Counter(d_["known"].split(":", 1)[0] for d_ in dis if d_["known"])
    for cause, n in sorted(reasons.items()):
        print("  allowlisted %-8s %d" % (cause, n))
    for d_ in (dis if args.report else unknown_dis):
        mark = "known(%s)" % d_["known"].split(":", 1)[0] if d_["known"] else "UNEXPLAINED"
        print("  [%s] flag %s ap%s  %s :: %s"
              % (mark, d_["flag"], d_["ap_id"], d_["region"], d_["name"][:70]))
        print("        ours %r vs his %s" % (d_["ours"], ", ".join(repr(t) for t in d_["theirs"][:3])))
    print()

    # --- B ---
    print("== B. MISSING SLOTS (data.LOCATIONS) ==")
    print("his Event-scope flags we lack: %d after excluding %d by tag %s"
          % (len(missing), excluded, sorted(EXCLUDED_TAGS) + [p + "*" for p in EXCLUDED_TAG_PREFIXES]))
    print("  %d allowlisted, %d UNEXPLAINED"
          % (len(missing) - len(unknown_missing), len(unknown_missing)))
    reasons = Counter(m["known"].split(":", 1)[0] for m in missing if m["known"])
    for cause, n in sorted(reasons.items()):
        print("  allowlisted %-8s %d" % (cause, n))
    for m in (missing if args.report else unknown_missing):
        mark = "known(%s)" % m["known"].split(":", 1)[0] if m["known"] else "UNEXPLAINED"
        print("  [%s] flag %s  his tags [%s]" % (mark, m["flag"], " ".join(m["tags"]) or "-"))
    print()

    # --- C (report-only) ---
    ed = enemy_drop_counts(rows) if args.report else None
    if ed is not None:
        print("== C. ENEMY DROPS (greenfield/enemy_drops.tsv) -- REPORT ONLY, never a gate ==")
        print("ours: %d ONE-TIME (flagged) enemy-drop flags from NpcParam/ItemLotParam_enemy"
              % len(ed["ours_flags"]))
        print("his:  %d slots tagged enemy*, over %d distinct Event-scope flags"
              % (ed["theirs_slots"], ed["theirs_flags"]))
        print("flag join: %d in both, %d ours-only, %d his-only"
              % (len(ed["overlap"]), len(ed["ours_only"]), ed["theirs_only"]))
        # OUR flag ids only -- his stay counts (licence boundary, module header).
        print("  ours-only flags: %s"
              % (" ".join(str(f) for f in sorted(ed["ours_only"])) or "-"))
        print()

    # --- D + E: report-only, and only under --report ---
    taxonomy_report = None
    if args.report:
        taxonomy_report = report_taxonomy_and_reach(args.repo, d, rows)

    if args.report:
        ours_flags, n_miss_rows = load_missable_flags(args.repo, by_flag)
        joinable, agree, his_only, ours_only = check_missable(rows, by_flag, ours_flags)
        print("== F. MISSABLE (report-only, no gate) ==")
        print("ours: %d MISSABLE_LOCATIONS row(s), %d distinct flag(s)" % (n_miss_rows, len(ours_flags)))
        print("his `%s`-tagged Event flags that data.LOCATIONS carries a row for: %d joinable"
              % (MISSABLE_TAG, len(joinable)))
        print("  agree     %d" % len(agree))
        print("  his-only  %d (he tags missable, we do not)" % len(his_only))
        print("  ours-only %d (we tag missable, his slot is not tagged)" % len(ours_only))
        print("  his-only flags:  %s" % " ".join(str(f) for f in his_only))
        print("  ours-only flags: %s" % " ".join(str(f) for f in ours_only))
        print("NOTE: the two curations answer different questions (his slot-level 'do not randomize'"
              " vs our check-level 'must not host REQUIRED progression'), so a one-sided flag is a"
              " worklist entry, not a defect. Report-only by design.")
        print()

    # --- G (report-only) ---
    rq, rq_joined, rq_areas, rq_mapped = check_region_queue(rows, by_flag)
    print("== G. REGION (report-only; the human review queue) ==")
    print("joinable rows %d over %d second-source clusters (%d with a single-region plurality): "
          "%d disagree" % (rq_joined, rq_areas, rq_mapped, len(rq)))
    print("  by OUR region: " + ", ".join(
        "%s %d" % (r, n) for r, n in sorted(Counter(e["our_region"] for e in rq).items())))
    print("  🛑 report-only by design: the two models partition differently, so a disagreement is a "
          "QUESTION for a reviewer, not a defect. --region-queue writes it out for review.")
    if args.region_queue:
        previous = read_region_queue(args.region_queue)
        kept, added, droppedq = write_region_queue(args.region_queue, rq, previous)
        print("  wrote %s: %d rows (%d carried over, %d new, %d no longer disagreeing)"
              % (args.region_queue, len(rq), kept, added, len(droppedq)))
        for k in droppedq:
            print("    resolved: flag %d ap%d (was %s)"
                  % (k[0], k[1], previous[k].get("status", "?")))
    print()

    # --- H (report-only) ---
    mq, mq_theirs, mq_ours, mq_joinable = check_missable_queue(rows, by_flag, args.repo)
    print("== H. MISSABLE (report-only; the second human review queue) ==")
    print("his missable-tagged Event flags %d (%d joinable to ours); OUR MISSABLE_LOCATIONS %d "
          "checks: %d queued" % (mq_theirs, mq_joinable, mq_ours, len(mq)))
    print("  by OUR questline-condition classes: " + (", ".join(
        "%s %d" % (c, n) for c, n in sorted(Counter(e["our_conditions"] for e in mq).items()))
        or "-"))
    print("  🛑 a tag disagreement alone is NOT queued: a row is here only when OUR OWN "
          "questline_conditions.tsv also shows a %s root." % "/".join(MISSABLE_CONDITION_CLASSES))
    if args.missable_queue:
        previous = read_queue(args.missable_queue)
        kept, added, droppedq = write_missable_queue(args.missable_queue, mq, previous)
        print("  wrote %s: %d rows (%d carried over, %d new, %d no longer disagreeing)"
              % (args.missable_queue, len(mq), kept, added, len(droppedq)))
        for k in droppedq:
            print("    resolved: flag %d ap%d (was %s)"
                  % (k[0], k[1], previous[k].get("status", "?")))
    print()

    stale = stale_entries({d_["flag"] for d_ in dis}, by_flag)
    for which, flag, reason in stale:
        print("WARN: stale allowlist entry %s[%d] -- now agrees; drop it (%s)"
              % (which, flag, reason))
    if stale:
        print()

    if args.json_out:
        payload = {
            "matt_slots": len(rows),
            "item_identity": {
                "agree": agreed,
                "disagree": len(dis),
                "not_comparable": nocmp,
                "unexplained": [
                    {k: v for k, v in d_.items() if k != "known"} for d_ in unknown_dis
                ],
                "allowlisted": len(dis) - len(unknown_dis),
            },
            "missing_slots": {
                "missing": len(missing),
                "excluded_by_tag": excluded,
                "unexplained": [{"flag": m["flag"], "tags": m["tags"]} for m in unknown_missing],
                "allowlisted": len(missing) - len(unknown_missing),
            },
            "region_queue": {
                "joinable_rows": rq_joined,
                "queued": len(rq),
                # OUR ap ids and OUR region names only -- see the licence note on check_region_queue
                "rows": rq,
            },
            "missable_queue": {
                "theirs_tagged": mq_theirs,
                "joinable": mq_joinable,
                "ours_missable": mq_ours,
                "queued": len(mq),
                # OUR flag/ap_id/name and OUR condition classes only -- see check_missable_queue.
                "rows": mq,
            },
            "stale_allowlist": [{"list": w, "flag": f} for w, f, _ in stale],
        }
        if taxonomy_report is not None:
            payload["boss_taxonomy"] = taxonomy_report
        if ed is not None:
            # counts from his side, OUR flag ids from ours (licence boundary).
            payload["enemy_drops"] = {
                "ours_flags": len(ed["ours_flags"]),
                "theirs_slots": ed["theirs_slots"],
                "theirs_flags": ed["theirs_flags"],
                "overlap": len(ed["overlap"]),
                "ours_only": sorted(ed["ours_only"]),
                "theirs_only": ed["theirs_only"],
            }
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
        print("wrote %s" % args.json_out)

    if unknown_dis or unknown_missing:
        print("FAIL: %d unexplained item-identity disagreement(s), %d unexplained missing slot(s). "
              "Fix the table, or add the flag to the allowlist in this file with a reason."
              % (len(unknown_dis), len(unknown_missing)))
        return 1
    print("OK: every disagreement is accounted for.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
