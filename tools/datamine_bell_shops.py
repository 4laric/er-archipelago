#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""datamine_bell_shops.py -- PROBE: how each merchant Bell Bearing flag is wired in the EMEVD.

WHY
---
The nomadic/roving merchants' Twin-Maiden re-sell is NOT gated by ShopLineupParam.eventFlag_forRelease
(the bell-item flags -- 400049 Kale, 400901+ nomadic/isolated/hermit -- appear nowhere in the param;
the release-gated rows are mostly Enia's remembrance armor behind 9xxx boss flags). So the bell -> shop
link is a runtime EMEVD handover: giving a bell to the Twin Maidens fires an event that enables that
merchant's inventory. This probe finds that event so we can derive bell -> shop-rows (MerchantBellLogic,
multi-region merchant resolution, the auto-hand-in-on-talk QoL).

It does NOT assume the mechanism. It locates every EMEVD reference to a bell-bearing flag and, crucially,
every `$InitializeEvent` / `$InitializeCommonEvent` registration whose args include a bell flag -- the
parameterized-handler pattern (same shape datamine_boss_reward_lots exploits). The registration's OTHER
args are the payload (a shop-lineup range, a release flag it sets, an item lot...). One run reveals the
structure; then the real parser is a targeted regex.

Reads elden_ring_artifacts/event/*.emevd.dcx.js + common.emevd.dcx.js (DarkScript decompile) and reads
bell-bearing flags from greenfield/region_map.csv (item_name contains "Bell Bearing").

USAGE (Windows, artifacts present):
    python tools/datamine_bell_shops.py                 # probe: dump bell-flag EMEVD wiring
    python tools/datamine_bell_shops.py --flags 400901 400909   # only these bell flags
"""
import argparse
import csv
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.abspath(os.path.join(HERE, ".."))
ART = os.path.join(REPO, "elden_ring_artifacts")
EVT = os.path.join(ART, "event")
REGION_MAP = os.path.join(REPO, "greenfield", "region_map.csv")

_INIT_RE = re.compile(r"\$Initialize(?:Common)?Event\(([^)]*)\)")
_EVENT_HDR_RE = re.compile(r"\$Event\((\d+)\s*,")


def bell_flags(override):
    if override:
        return {int(x): f"(cli flag {x})" for x in override}
    out = {}
    if not os.path.isfile(REGION_MAP):
        sys.exit(f"missing {REGION_MAP}")
    with open(REGION_MAP, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if "Bell Bearing" in (r.get("item_name") or ""):
                try:
                    out[int(r["flag"])] = r["item_name"].strip()
                except (KeyError, ValueError, TypeError):
                    pass
    return out


def _event_id_at(src, pos):
    """The $Event(id, ...) whose body encloses byte offset `pos` (nearest preceding header)."""
    last = None
    for m in _EVENT_HDR_RE.finditer(src):
        if m.start() > pos:
            break
        last = m.group(1)
    return last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--flags", nargs="*", type=int, help="only probe these bell flags")
    ap.add_argument("--context", type=int, default=1, help="lines of context around a non-init hit")
    args = ap.parse_args()

    if not os.path.isdir(EVT):
        sys.exit(f"FATAL: {EVT} not found -- need the decompiled EMEVD (event/*.emevd.dcx.js).")

    flags = bell_flags(args.flags)
    if not flags:
        sys.exit("no bell-bearing flags found (region_map.csv item_name ~ 'Bell Bearing').")
    flagset = set(flags)
    print(f"# probing {len(flags)} bell-bearing flag(s) across the EMEVD")

    files = sorted(glob.glob(os.path.join(EVT, "*.emevd.dcx.js")))
    if not files:
        sys.exit(f"no *.emevd.dcx.js under {EVT}")

    # (1) INITIALIZER registrations whose args include a bell flag -- the parameterized handler + payload.
    #     Group by (file, handler_event_id) and show the full arg tuple so bell -> payload is visible.
    inits = []                          # (file, enclosing_event, handler_id, args[])
    other = []                          # (file, line_no, bell_flag, text)
    for fp in files:
        name = os.path.basename(fp).replace(".emevd.dcx.js", "")
        src = open(fp, encoding="utf-8", errors="replace").read()
        for m in _INIT_RE.finditer(src):
            args_txt = m.group(1)
            nums = [int(x) for x in re.findall(r"-?\d+", args_txt)]
            if flagset & set(nums):
                # $Initialize[Common]Event(slot, handlerEventId, arg0, arg1, ...)
                handler = nums[1] if len(nums) >= 2 else None
                enc = _event_id_at(src, m.start())
                inits.append((name, enc, handler, nums))
        # (2) any other reference to a bell flag (line-level), for the ones inits miss.
        for i, line in enumerate(src.splitlines()):
            for fl in flagset:
                if re.search(r"(?<!\d)%d(?!\d)" % fl, line) and "$Initialize" not in line:
                    other.append((name, i + 1, fl, line.strip()[:160]))

    print(f"\n=== {len(inits)} $Initialize*Event registration(s) carrying a bell flag "
          f"(bell -> handler + payload args) ===")
    handlers = set()
    for (name, enc, handler, nums) in inits[:120]:
        bells = sorted(flagset & set(nums))
        print(f"  {name}.emevd  event~{enc}  handler={handler}  bells={bells}  args={nums}")
        if handler is not None:
            handlers.add(handler)
    if len(inits) > 120:
        print(f"  ... and {len(inits) - 120} more")

    # Dump each distinct handler event's BODY once, so what the payload DOES (SetEventFlag / a shop
    # command / an item lot) is visible in the same run -- that is the derivation the parser will target.
    if handlers:
        print(f"\n=== handler event bodies ({len(handlers)}) -- what the payload arg drives ===")
        _seen = set()
        for fp in files:
            src = open(fp, encoding="utf-8", errors="replace").read()
            for h in sorted(handlers):
                if h in _seen:
                    continue
                m = re.search(r"\$Event\(\s*%d\s*,.*?\n\}\);" % h, src, re.S)
                if m:
                    _seen.add(h)
                    body = m.group(0)
                    body = body if len(body) <= 900 else body[:900] + "  …(truncated)"
                    print(f"--- $Event({h}) in {os.path.basename(fp)} ---\n{body}\n")
        missing = sorted(handlers - _seen)
        if missing:
            print(f"  (handler bodies not found for: {missing} -- likely common_func.emevd)")

    print(f"\n=== {len(other)} other EMEVD line(s) referencing a bell flag ===")
    for (name, ln, fl, text) in other[:80]:
        print(f"  {name}.emevd:{ln}  [{fl} = {flags.get(fl,'?')}]  {text}")
    if len(other) > 80:
        print(f"  ... and {len(other) - 80} more")

    if not inits and not other:
        print("\n!! No bell flag appears in the EMEVD at all -- the handover may key off the bell ITEM "
              "(EquipParamGoods / a lot), not its flag. Re-probe with the bell item ids, or check the "
              "Twin-Maiden talk ESD (t?_x for the Roundtable) for the shop-enable path.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
