#!/usr/bin/env python3
r"""scan_event_award_leaks.py -- CONFIRM which emevd-award checks actually LEAK, to populate
gen_data.EVENT_AWARD_ITEM_FLAGS (consumed by coverage.py). Needs elden_ring_artifacts (emevd + params).

THE LEAK (confirmed on the Shadow Keep Rune Arc, f21017010, 2026-07-21):
  The client suppresses a check's vanilla ware by BLANKING the ItemLotParam lot that check_lots_table
  pins for the check's getItemFlagId. That works when the vanilla item is delivered by OPENING that
  lot. It does NOT work when an EMEVD instruction hands the item out through a DIFFERENT lot -- one the
  client never blanks. Then the blank hits a decoy and the real ware double-dips alongside the AP item.

  gen_check_lots_table pairs flag->lot by EXACT getItemFlagId, so the pinned (blanked) lot is a real,
  honestly-keyed ItemLotParam row -- but a SECOND lot can carry the same getItemFlagId (gen_data notes
  "a getItemFlagId shared by two ItemLotParam lots"), and if the EMEVD awards that second lot, the
  blank of the first suppresses nothing.

DETECTION (principled, no guessing):
  Collect every lot the EMEVD actually AWARDS, two ways --
    (a) direct  : AwardItemLot(N) / AwardItemsIncludingClients(N) literals in any map/common emevd;
    (b) handler : the parameterised award family in common.emevd (auto-discovered, exactly as
                  tools/datamine_boss_reward_lots.py does it) -- $InitializeEvent(slot, H, rewardFlag,
                  lot, lot2, getItemFlagId) registrations of $Event handlers that award a lot.
  For each awarded lot X, its check flag is G = ItemLotParam[X].getItemFlagId (handler registrations
  give G directly as the 5th arg). A check LEAKS iff:
        G is a real check flag (region_map.csv)  AND  X is NOT a lot the client blanks
        (X absent from the check_lots_table blanked-lot set)
  i.e. the game hands out the ware through an unblanked lot. That is EVENT_AWARD_ITEM_FLAGS.

  A check whose ONLY awarded lot IS its blanked lot is CLEAN (the blank catches it). A candidate
  (emevd-source flag already in check_lots_table) with no unblanked award found is CLEARED.

USAGE (run on a box with elden_ring_artifacts present):
    python tools/scan_event_award_leaks.py            # summary + paste-ready EVENT_AWARD_ITEM_FLAGS set
    python tools/scan_event_award_leaks.py --list     # per-check evidence table (flag, item, lots, verdict)
    python tools/scan_event_award_leaks.py --out FILE  # also write the confirmed set to FILE

This tool only READS. It does not edit gen_data. Paste the confirmed set into gen_data's
_EVENT_AWARD_ITEM_FLAGS hand list (importantly, a CONFIRMED collectathon leak -- Golden Seed /
Scadutree Fragment / Revered Spirit Ash -- is is_filler False, so coverage_quarantine.ACCEPTED_LEAKS
will REJECT it: it must be FIXED, not accepted).
"""
import argparse
import csv
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.dirname(HERE)
AR = os.path.join(REPO, "elden_ring_artifacts")
EVT = os.path.join(AR, "event")
GF = os.path.join(REPO, "greenfield")

_AWARD_CALLS = ("AwardItemLot", "AwardItemsIncludingClients")
_HANDLER_SIG = ("eventFlagId", "itemLotId", "itemLotId2", "eventFlagId2")  # the boss-reward family sig


def _read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _find_param_dir():
    """Locate the dir holding ItemLotParam_map.csv under elden_ring_artifacts (layout varies)."""
    hits = glob.glob(os.path.join(AR, "**", "ItemLotParam_map.csv"), recursive=True)
    if not hits:
        raise SystemExit("FATAL: ItemLotParam_map.csv not found under %s -- artifacts required." % AR)
    return os.path.dirname(hits[0])


def load_lot_to_flag(param_dir):
    """{lot_id: getItemFlagId} across map+enemy ItemLotParam (lot id is the first CSV column)."""
    lot2flag = {}
    for fn in ("ItemLotParam_map.csv", "ItemLotParam_enemy.csv"):
        p = os.path.join(param_dir, fn)
        if not os.path.isfile(p):
            continue
        with open(p, newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                try:
                    lot = int(list(r.values())[0])
                    flag = int(r.get("getItemFlagId", 0) or 0)
                except (ValueError, IndexError):
                    continue
                if lot > 0 and flag > 0:
                    lot2flag[lot] = flag
    return lot2flag


def load_check_lots():
    """From greenfield/eldenring/check_lots_table.json: (blanked_lots set, {flag: blanked_lot})."""
    p = os.path.join(GF, "eldenring", "check_lots_table.json")
    d = json.load(open(p, encoding="utf-8"))
    blanked, flag2blank = set(), {}
    for key in ("map", "enemy"):
        for flag, ent in d.get(key, {}).items():
            lot = int(ent.get("lot", -1))
            blanked.add(lot)
            flag2blank[int(flag)] = lot
    return blanked, flag2blank


def load_region_map():
    """{flag: (item, region, method, flag_source)} for every check in region_map.csv."""
    out = {}
    with open(os.path.join(GF, "region_map.csv"), newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            try:
                out[int(r["flag"])] = (r.get("item", ""), r.get("region", ""),
                                       r.get("method", ""), (r.get("flag_source", "") or "").strip())
            except (ValueError, KeyError):
                continue
    return out


def _award_handlers(common_src):
    """{eventId} for common.emevd $Event bodies that award a lot with the boss-reward signature."""
    out = set()
    for m in re.finditer(r"\$Event\((\d+),\s*\w+,\s*function\(([^)]*)\)(.*?)\n\}\);", common_src, re.S):
        eid, params, body = m.group(1), m.group(2), m.group(3)
        if not any(a in body for a in _AWARD_CALLS):
            continue
        if tuple(p.strip() for p in params.split(",")) == _HANDLER_SIG:
            out.add(int(eid))
    return out


def collect_awarded(lot2flag):
    """Return {lot_id: set(provenance str)} for every lot the EMEVD awards.

    direct  -- AwardItemLot(N)/AwardItemsIncludingClients(N) literals in any m*/common emevd.
    handler -- $InitializeEvent(_, H, rewardFlag, lot, lot2, getFlag) registrations of the auto-
               discovered award handlers in common.emevd (the parameterised family).
    """
    awarded = {}

    def note(lot, src):
        if lot in lot2flag or True:   # keep even if not a known lot -- evidence for review
            awarded.setdefault(int(lot), set()).add(src)

    files = glob.glob(os.path.join(EVT, "m*.emevd.dcx.js"))
    common_path = os.path.join(EVT, "common.emevd.dcx.js")
    if os.path.isfile(common_path):
        files.append(common_path)

    # (a) direct literal awards, any file
    call_re = re.compile(r"\b(?:%s)\(\s*(\d+)\s*\)" % "|".join(_AWARD_CALLS))
    for fp in files:
        base = os.path.basename(fp).split(".")[0]
        for mm in call_re.finditer(_read(fp)):
            note(int(mm.group(1)), "direct:%s" % base)

    # (b) handler registrations in common.emevd (lot + lot2 are the awarded lots; 5th arg is getFlag)
    if os.path.isfile(common_path):
        common = _read(common_path)
        handlers = _award_handlers(common)
        for h in sorted(handlers):
            pat = r"\$InitializeEvent\(\s*\d+\s*,\s*%d\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)" % h
            for m in re.finditer(pat, common):
                rf, lot, lot2, gf = (int(x) for x in m.groups())
                # register both awarded lots; the getFlag is authoritative for `lot`
                note(lot, "handler:%d(getFlag=%d)" % (h, gf))
                if lot2 > 0:
                    note(lot2, "handler:%d" % h)
    return awarded


def scan():
    param_dir = _find_param_dir()
    lot2flag = load_lot_to_flag(param_dir)
    blanked, flag2blank = load_check_lots()
    rmap = load_region_map()
    awarded = collect_awarded(lot2flag)

    # candidate set: emevd-source checks already in check_lots_table (what the gate would call lot_blank)
    candidates = {f for f in flag2blank if rmap.get(f, ("", "", "", ""))[3] == "emevd"}

    leaks = {}   # flag -> dict(item, region, blanked_lot, award_lots[list], src)
    for lot, srcs in awarded.items():
        g = lot2flag.get(lot)
        if not g or g not in rmap:
            continue
        if lot in blanked:
            continue                      # emevd awards a lot the client DOES blank -> clean
        # unblanked award of a real check flag's ware -> leak
        item, region, method, fsrc = rmap[g]
        e = leaks.setdefault(g, {"item": item, "region": region, "flag_source": fsrc,
                                 "blanked_lot": flag2blank.get(g), "award_lots": [], "srcs": set()})
        e["award_lots"].append(lot)
        e["srcs"] |= srcs

    cleared = sorted(candidates - set(leaks))
    unexpected = sorted(set(leaks) - candidates)   # leaks whose flag_source wasn't 'emevd' (report)
    return leaks, candidates, cleared, unexpected


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true", help="print the per-check evidence table")
    ap.add_argument("--out", metavar="FILE", help="write the confirmed flag set to FILE")
    a = ap.parse_args(argv)

    leaks, candidates, cleared, unexpected = scan()
    confirmed = sorted(leaks)

    print("emevd-source candidates (in check_lots_table): %d" % len(candidates))
    print("CONFIRMED leaks (emevd awards an unblanked lot): %d" % len(confirmed))
    print("candidates CLEARED (award routes through the blanked lot / no unblanked award): %d" % len(cleared))
    if unexpected:
        print("!! leaks whose region_map flag_source != 'emevd' (review): %s" % unexpected)

    COLLECT = ("Golden Seed", "Sacred Tear", "Scadutree Fragment", "Revered Spirit Ash")
    important = [f for f in confirmed if any(c in (leaks[f]["item"] or "") for c in COLLECT)]
    if important:
        print("\n** IMPORTANT (collectathon) confirmed leaks -- CANNOT be ACCEPTED_LEAKS, must be fixed:")
        for f in important:
            print("   f%d  %s  [%s]" % (f, leaks[f]["item"], leaks[f]["region"]))

    if a.list:
        print("\n%-12s %-26s %-11s %-12s %s" % ("flag", "item", "blanked_lot", "award_lot(s)", "region"))
        for f in confirmed:
            e = leaks[f]
            print("%-12d %-26s %-11s %-12s %s" % (
                f, (e["item"] or "")[:26], e["blanked_lot"],
                ",".join(str(x) for x in sorted(set(e["award_lots"]))), e["region"]))

    body = "(" + ", ".join(str(f) for f in confirmed) + ("," if len(confirmed) == 1 else "") + ")"
    print("\n# paste into gen_data _EVENT_AWARD_ITEM_FLAGS (verify collectathon ones are FIXED, not accepted):")
    print("EVENT_AWARD_ITEM_FLAGS = %s" % body)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write("EVENT_AWARD_ITEM_FLAGS = %s\n" % body)
        print("[scan] wrote %s" % a.out)
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))
