#!/usr/bin/env python3
"""matt_oracle.py -- read-only cross-check of our tables against thefifthmatt/SoulsRandomizers.

WHAT THIS IS. thefifthmatt's Elden Ring randomizer carries a hand-curated item-slot table
(`diste/Base/itemslots.txt`, ~4400 slots) keyed on the same event-flag number space as our
`[fFLAG]` suffix. Independently curated, same game: a disagreement between the two tables is
evidence about the GAME, and it is the only second opinion our generated tables have. Two of the
six discrepancy classes surveyed in the 2026-09 oracle study are tight enough to gate on:

  A. ITEM IDENTITY -- `item_ids.LOCATION_ITEM[ap_id]` vs the vanilla item his DebugText records for
     the same flag. 97.4% agreement over ~4100 comparable rows. Wrong vanilla item is the highest
     blast radius defect we have: it feeds item tier, which feeds logic.
  B. MISSING SLOTS -- his Type-0 (Event-scope) flags that `data.LOCATIONS` has no row for at all.

Everything else (region assignment, missable tagging, shop granularity, DLC membership) is
report-only and lives in `--report`, because the two models differ structurally there rather than
factually.

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


# ---------------------------------------------------------------------------
# A. ITEM IDENTITY -- known disagreements on item_ids.LOCATION_ITEM.
#
# Bare event-flag integers, grouped by CAUSE. Reasons are ours; the flag numbers are game facts.
# A flag listed here that now AGREES is reported as stale (warning, not a failure) so the list
# shrinks as the tables converge.
# ---------------------------------------------------------------------------
# --- CLASS SETS. Every flag below resolves to exactly one reason string via the merges at the end
# of this block. The bulk classes are grouped rather than repeated line-by-line because their reason
# IS the class: 99 copies of the same sentence is not 99 pieces of evidence.

_A_OPEN_DLC_MATERIAL = frozenset({    # 99 flags
    20007060, 20007110, 20007210, 20007250, 20007530,
    20007710, 20017040, 20017490, 20017650, 21007010,
    21007060, 21007100, 21007180, 21007550, 21007580,
    21007590, 21007620, 21017090, 21017400, 21017420,
    21017640, 21017760, 21027200, 21027230, 21027260,
    22007160, 22007170, 22007240, 40007000, 40007050,
    40007080, 40007100, 40017010, 40017030, 40017040,
    40017060, 40017100, 40027000, 40027010, 40027100,
    40027210, 41007260, 41017110, 42007100, 42007110,
    42007130, 42007160, 42007170, 42027020, 42027070,
    42037130, 42037170, 43017000, 43017040, 2044417000,
    2044467060, 2044477000, 2044477050, 2045417030, 2045417040,
    2045427000, 2045457010, 2046387050, 2046397000, 2046407050,
    2046457060, 2046457070, 2046477070, 2047427000, 2047427030,
    2047427040, 2047437020, 2047447020, 2047447070, 2047447080,
    2047447100, 2047447130, 2047457010, 2047457020, 2047457180,
    2047457920, 2048397040, 2048417030, 2048447050, 2048447070,
    2048467030, 2048467060, 2049387060, 2049427010, 2049437330,
    2049437500, 2049437520, 2049437600, 2049447070, 2050447000,
    2050477010, 2051417000, 2051447020, 2052407010,
})

_B_SCOPE_MAP_FRAGMENT = frozenset({    # 24 flags
    62010, 62011, 62012, 62020, 62021, 62022,
    62030, 62031, 62032, 62040, 62041, 62050,
    62051, 62052, 62060, 62061, 62062, 62063,
    62064, 62080, 62081, 62082, 62083, 62084,
})

_B_OPEN = frozenset({    # 45 flags
    60270, 68510, 68520, 68530, 68540,
    68550, 68560, 68830, 400030, 400060,
    400069, 400100, 400102, 400140, 400141,
    400143, 400145, 400150, 400161, 400170,
    400171, 400172, 400181, 400182, 400189,
    400271, 400293, 400294, 400331, 400332,
    400334, 400420, 400421, 400422, 400451,
    400750, 400751, 400752, 400753, 400754,
    400755, 530935, 14007930, 1050567820, 2048467701,
})


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

    # --- OPEN (4). Our LOCATION_ITEM names an armour piece / sorcery where he names a completely
    # different item on the same flag. No modelling difference explains these; they look like OUR
    # rows being wrong. Allowlisted so the gate is green and the debt is VISIBLE, not silent.
    400282: "OPEN: we say All-Knowing Helm, he says an incantation -- our row is likely wrong",
    400283: "OPEN: we say All-Knowing Armor, he says an incantation -- our row is likely wrong",
    400285: "OPEN: we say All-Knowing Greaves, he says an incantation -- our row is likely wrong",
    400358: "OPEN: we say a sorcery, he says a weapon -- our row is likely wrong",
}
# --- OPEN, DLC UPGRADE MATERIAL (99). Same flag, same item lot id, same item FAMILY, different
# TIER (and different stack size): e.g. flag 21007010 -> lot 21000010, ours Smithing Stone [1] x6,
# his Smithing Stone [7] x3. 253 other DLC material rows AGREE, so this is not a uniform offset --
# it is a subset of DLC ItemLotParam rows on which our `greenfield/flag_lots.tsv` (from
# tools/datamine_flag_lots.py) and his table disagree, most likely because one side's regulation
# snapshot predates a DLC retune. Adjudicating it needs a fresh datamine against a known patch,
# which is not a change to a committed generator input, so it stays OPEN rather than "fixed".
ITEM_IDENTITY_KNOWN.update(
    {f: "OPEN: DLC upgrade-material tier/stack disagreement on the same lot (flag_lots.tsv vs his "
        "ItemLotParam read); needs a fresh datamine to adjudicate"
     for f in _A_OPEN_DLC_MATERIAL}
)


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
# --- OPEN (45). Slots he carries and we do not, with no scoping story that covers them: the seven
# Forager Brood Cookbooks (a DLC cookbook line absent from our catalog entirely), ~33 quest/NPC
# reward flags in the 400xxx band (we model much of that band, so "we don't do quest rewards" is not
# the explanation), a second Blessing of Marika, a second Academy Glintstone Key, a Rise talisman,
# and one Furnace Golem drop. These are candidate REAL GAPS in data.LOCATIONS. Allowlisted so the
# gate is green and the debt is visible; each is an open finding on the PR that added this tool.
MISSING_SLOT_KNOWN.update(
    {f: "OPEN: slot he carries that data.LOCATIONS has no row for; candidate real gap"
     for f in _B_OPEN}
)


# Tag vocabulary used as a FILTER (not stored as expectation data). Slots carrying any of these are
# outside the set of checks we model at all, so their absence from data.LOCATIONS is by design:
#   norandom / ignore -- his own "never put a randomized check here" vocabulary
#   tarnished         -- Tarnished-Pack mod content; not vanilla Elden Ring
#   enemy*            -- enemy-drop slots (enemyweapon/enemygem/enemysorcery/... subtypes). Our
#                        enemy_drops table is a stub; a separate derivation, not a gap in LOCATIONS.
# NOTE ON GESTURES: he has no `gesture` tag, because he does not model gestures as slots at all.
# The gesture asymmetry runs the OTHER way (OUR flags he lacks) and is report-only.
EXCLUDED_TAGS = frozenset({"norandom", "ignore", "tarnished"})
EXCLUDED_TAG_PREFIXES = ("enemy",)


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
            "stale_allowlist": [{"list": w, "flag": f} for w, f, _ in stale],
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
