#!/usr/bin/env python3
r"""probe_minidungeon_boss_drops.py -- WHY do catacomb/cave/tunnel bosses have no drop check?

READ-ONLY. Writes nothing, changes nothing. Run it, paste the output.

THE FACT WE ARE EXPLAINING
--------------------------
datamine_boss_drops.py derives 88 boss drops, and ZERO of them are catacomb/cave/tunnel/dungeon.
Its method: find the common events that (a) call HandleBossDefeatAndDisplayBanner AND (b) take an
`itemLotId` argument -- that discovered 90005860 / 90005861 / 90005880 -- then scan map events for
$InitializeCommonEvent of those handlers to pull (entity, rewardLot) pairs.

boss_healthbars knows 249 bosses: legacy 84, field 84, cave 31, catacomb 26, dungeon 15, tunnel 9.
So 81 MINI-DUNGEON bosses award their drop through some OTHER mechanism, and their reward is
therefore not a check at all -- the game just hands the player the vanilla item and nothing fires.
(Alaric, playtest 2026-07-12: killed the Unsightly Catacombs duo -- m30_12 -- and got the vanilla
Perfumer Tricia ash, while all five of that map's TREASURE checks randomised correctly.)

This probe finds the other mechanism. It does NOT guess: it prints the raw EMEVD lines and lets them
speak.

    python tools/probe_minidungeon_boss_drops.py                 # the whole picture
    python tools/probe_minidungeon_boss_drops.py --map m30_12    # one map, verbose
"""
import argparse
import glob
import os
import re
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.dirname(HERE)
AR = os.path.join(REPO, "elden_ring_artifacts")
EVT = os.path.join(AR, "event")

# Mini-dungeon map prefixes. m30 = catacombs, m31 = caves, m32 = tunnels, m34/m35/m39 = misc dungeons.
MINI = ("m30_", "m31_", "m32_", "m34_", "m35_", "m39_")

# Anything that could hand the player an item. Deliberately broad -- we are LOOKING for the mechanism,
# so a false positive costs one line of output and a false negative costs another round trip.
AWARD = re.compile(
    r"(AwardItemLot|ItemLot|DirectlyGivePlayerItem|AwardRuneItem|GrantItemLot|"
    r"HandleBossDefeat\w*|BossDefeat\w*)",
    re.I,
)
INIT = re.compile(r"\$?InitializeCommonEvent\s*\(\s*(\d+)")
EVENT_DEF = re.compile(r"\$Event\s*\(\s*(\d+)\s*,\s*\w+\s*,\s*function\s*\(([^)]*)\)")


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def common_events():
    """{id: (signature, body)} for every common-func event."""
    out = {}
    for fp in glob.glob(os.path.join(EVT, "common_func*")) + glob.glob(os.path.join(EVT, "common*")):
        txt = read(fp)
        for m in EVENT_DEF.finditer(txt):
            eid, sig = int(m.group(1)), m.group(2)
            end = txt.find("$Event(", m.end())
            out[eid] = (sig, txt[m.end():end if end > 0 else len(txt)])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", help="dump ONE map verbatim (e.g. m30_12 = Unsightly Catacombs)")
    args = ap.parse_args()

    if not os.path.isdir(EVT):
        raise SystemExit(f"elden_ring_artifacts/event not found at {EVT} -- set ER_REPO?")

    files = sorted(glob.glob(os.path.join(EVT, "*")))
    mini_files = [f for f in files if os.path.basename(f).startswith(MINI)]
    print(f"EMEVD files: {len(files)} total, {len(mini_files)} mini-dungeon (m30/31/32/34/35/39)\n")

    # ---- 1) ONE MAP, verbatim. This is the ground truth we actually need. --------------------
    target = args.map or "m30_12"
    hit = [f for f in files if os.path.basename(f).startswith(target)]
    print("=" * 78)
    print(f"  {target}  (Unsightly Catacombs = Perfumer Tricia + Misbegotten Warrior)" if target == "m30_12"
          else f"  {target}")
    print("=" * 78)
    if not hit:
        print(f"  no EMEVD file starting with {target!r}")
    for fp in hit:
        txt = read(fp)
        print(f"\n--- {os.path.basename(fp)} ---")
        print("\n  [A] every InitializeCommonEvent (which handler runs this map's boss?):")
        for cid, n in Counter(int(m.group(1)) for m in INIT.finditer(txt)).most_common():
            print(f"        common {cid:<12} x{n}")
        print("\n  [B] every line mentioning an item lot / boss-defeat handler:")
        for i, line in enumerate(txt.splitlines(), 1):
            if AWARD.search(line):
                print(f"        {i:>6}: {line.strip()[:120]}")
        print("\n  [C] every line naming the boss-defeat flags 30120800 / 30120801:")
        for i, line in enumerate(txt.splitlines(), 1):
            if "3012080" in line:
                print(f"        {i:>6}: {line.strip()[:120]}")

    # ---- 2) WHICH handlers do mini-dungeon bosses use, vs the 3 the datamine knows? ----------
    known = {90005860, 90005861, 90005880}
    ce = common_events()
    print("\n" + "=" * 78)
    print("  WHICH common events do MINI-DUNGEON maps initialise?")
    print("=" * 78)
    used = Counter()
    for fp in mini_files:
        for m in INIT.finditer(read(fp)):
            used[int(m.group(1))] += 1

    print("\n  handlers the datamine ALREADY knows (banner + itemLotId):")
    for cid in sorted(known):
        print(f"     {cid:<12} used {used.get(cid, 0):>5}x by mini-dungeon maps")

    print("\n  OTHER common events these maps use, that LOOK like they award an item"
          "\n  (body mentions an item lot / boss defeat) -- one of these is the mechanism:")
    rows = []
    for cid, n in used.most_common():
        if cid in known or cid not in ce:
            continue
        sig, body = ce[cid]
        if AWARD.search(body):
            has_lot = "itemLot" in sig or "ItemLot" in sig
            rows.append((n, cid, has_lot, " ".join(sig.split())[:70]))
    if not rows:
        print("     (none -- the award is NOT via a common event; see [B] above for the map-local call)")
    for n, cid, has_lot, sig in sorted(rows, reverse=True)[:20]:
        flag = "HAS itemLot arg" if has_lot else "no itemLot arg "
        print(f"     {cid:<12} x{n:<5} {flag}  ({sig})")

    # ---- 3) The scoreboard: how many bosses are we actually missing? --------------------------
    print("\n" + "=" * 78)
    print("  SCOREBOARD")
    print("=" * 78)
    try:
        import sys
        sys.path.insert(0, os.path.join(REPO, "greenfield", "eldenring"))
        import boss_healthbars as bh  # noqa: E402
        from boss_drops import BOSS_DROP_FLAGS  # noqa: E402

        hb = next(v for k, v in vars(bh).items() if k.isupper() and isinstance(v, dict))
        kinds = Counter(t[2] for t in hb.values())
        mini = sum(kinds[k] for k in ("catacomb", "cave", "tunnel", "dungeon"))
        by_kind_map = defaultdict(set)
        for t in hb.values():
            by_kind_map[t[2]].add(t[0])
        print(f"  bosses known (healthbar sweep) : {len(hb)}   {dict(kinds)}")
        print(f"  boss DROPS datamined           : {len(BOSS_DROP_FLAGS)}")
        print(f"  MINI-DUNGEON bosses            : {mini}  <-- drops not modelled: the player is handed")
        print(f"                                        the vanilla item and NO check fires")
    except Exception as e:  # pragma: no cover - diagnostics only
        print(f"  (scoreboard unavailable: {e})")


if __name__ == "__main__":
    main()
