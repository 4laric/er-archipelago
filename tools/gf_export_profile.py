#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gf_export_profile.py -- WHAT, not how much, we send to other worlds.

WHY THIS EXISTS (2026-08-10, er-archipelago#510). `gf_multiworld_smoke.py` proves the cross-world
PATH works: our items reach other players, including a non-Elden-Ring game. It counts them. It never
reads what they ARE -- and for the whole life of that check, every single item we sent to a non-ER
partner was FILLER. 498 placements into Hollow Knight across three seeds: no weapon, no armour, no
talisman, while a second Elden Ring slot in the same seeds received 43.1% useful. A player noticed
before any gate did.

So this is the measuring instrument that check was missing. It generates real multiworlds and
histograms every Elden Ring item that lands in somebody else's world by AP ItemClassification and by
our own item category, split by destination GAME -- because "we export a healthy mix" and "we export
a healthy mix TO ANOTHER ELDEN RING" are different sentences and the first one was false.

🛑 IT READS THE MULTIDATA, NOT THE SPOILER. The spoiler names items and owners; it cannot say whether
an item is progression, useful or filler. `locations[holder] = {loc_id: (item_id, item_player,
flags)}` carries the classification bitfield the server itself runs on. Any measurement of this
question built on item NAMES is a heuristic, and a heuristic is what would have missed the defect.

It is a MEASURING TOOL, not a gate: it prints, it never exits non-zero on a distribution. The
assertion that belongs in CI lives in `gf_multiworld_smoke.check_gear_reaches_the_partner`.

USAGE
    python tools/gf_export_profile.py --ap-dir <ap> --seeds 3 --er-slots 2 --partners hk,hk
    python tools/gf_export_profile.py --ap-dir <ap> --seeds 3 --er-slots 1 --partners hk,bumpstik,doom
    python tools/gf_export_profile.py --ap-dir <ap> --seeds 2 --extra "confine_foreign_progression=50"

`--extra` rewrites `key=value` lines in the shipped `release/EldenRing.yaml` and HARD-FAILS on a key
that is not there, so a sweep cannot silently measure the default while claiming to measure a knob.

MEASURED WITH THIS TOOL, 2 seeds a cell, 2xER + 2xHollow Knight, only the yaml varying:

    confine   ER->HK n   useful%   foreign prog into ER   of that, on-surface
    100            332       0.0                     82               100.0%
     95            376       0.0                    132                58.3%
     90            444       5.2                    201                35.8%
     75            551      23.2                    309                16.8%
     50            686      38.3                    445                 7.4%
     25            712      40.6                    472                 6.1%
      0            713      40.7                    473                 6.1%

Read it as a trade with no free point: the gear only starts travelling below ~90, and the curation
is gone well before the gear is fully back. The on-surface column decays as slot COUNTS predict --
a released name may use ~3000 of our checks against a surface of ~170 -- so even a small release
means most incoming foreign progression is no longer on a starred check.
"""
import argparse, collections, glob, os, re, subprocess, sys, tempfile, zipfile, zlib, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADV, USEFUL, TRAP = 0b001, 0b010, 0b100


def er_yaml(name, nreg, extra=""):
    s = open(os.path.join(ROOT, "release", "EldenRing.yaml"), encoding="utf-8").read()
    s = re.sub(r"^name:.*$", "name: %s" % name, s, count=1, flags=re.M)
    s = re.sub(r"^(\s*)num_regions:\s*\d+\s*$", r"\g<1>num_regions: %d" % nreg, s, count=1, flags=re.M)
    for kv in [x for x in extra.split(";") if x]:
        k, v = kv.split("=", 1)
        # 🛑 Count the SUBSTITUTION, not whether the text moved. Asserting `s2 != s` looked like the
        # same check and was not: setting a key to the value it already holds is a no-op edit, so a
        # sweep whose cell happens to be the shipped default would blow up claiming the key does not
        # exist. What must be true is that the key was FOUND.
        s, n = re.subn(r"^(\s*)%s:.*$" % re.escape(k), r"\g<1>%s: %s" % (k, v), s, count=1,
                       flags=re.M)
        assert n == 1, ("no `%s:` line in release/EldenRing.yaml -- this sweep would have measured "
                        "the default while reporting it as %s=%s" % (k, k, v))
    return s


PARTNERS = {
 "hk": """name: Hallownest%d
game: Hollow Knight
description: partner
Hollow Knight:
  progression_balancing: 0
  accessibility: full
  RandomizeDreamers: true
  RandomizeSkills: true
  RandomizeCharms: true
  RandomizeKeys: true
  RandomizeGeoChests: false
  RandomizeMaps: false
""",
 "bumpstik": """name: Bumpstik%d
game: Bumper Stickers
description: partner
Bumper Stickers:
  progression_balancing: 0
  accessibility: full
""",
 "doom": """name: Doomguy%d
game: DOOM 1993
description: partner
DOOM 1993:
  progression_balancing: 0
  accessibility: full
""",
}


def gen(ap, players, out, seed):
    env = dict(os.environ, AP_NONINTERACTIVE="1", SKIP_REQUIREMENTS_UPDATE="1")
    p = subprocess.run([sys.executable, "Generate.py", "--player_files_path", players,
                        "--outputpath", out, "--spoiler", "1", "--seed", str(seed)],
                       cwd=ap, env=env, stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        print("\n".join(p.stdout.strip().split("\n")[-30:]))
        raise SystemExit("gen failed %d" % p.returncode)
    return glob.glob(os.path.join(out, "*.zip"))[0]


def multidata(zp):
    import Utils
    z = zipfile.ZipFile(zp)
    n = [x for x in z.namelist() if x.endswith(".archipelago")][0]
    raw = z.read(n)
    return Utils.restricted_loads(zlib.decompress(raw[1:]))


def main():
    ap_arg = argparse.ArgumentParser()
    ap_arg.add_argument("--ap-dir", required=True)
    ap_arg.add_argument("--seeds", type=int, default=3)
    ap_arg.add_argument("--num-regions", type=int, default=6)
    ap_arg.add_argument("--extra", default="")
    ap_arg.add_argument("--label", default="default")
    ap_arg.add_argument("--er-slots", type=int, default=2)
    ap_arg.add_argument("--partners", default="hk,hk")
    a = ap_arg.parse_args()
    sys.path.insert(0, a.ap_dir)
    os.chdir(a.ap_dir)

    from worlds.eldenring.core import item_name_to_id  # noqa
    from worlds.eldenring import item_ids as II
    from worlds.eldenring import item_categories as IC
    id2name = {v: k for k, v in item_name_to_id.items()}

    def category(nm):
        if nm.endswith(" Lock"):
            return "region lock"
        if nm.startswith("Progressive "):
            return "progressive"
        if nm == "Rune":
            return "generic Rune"
        try:
            return IC.category_of(nm) or "other"
        except Exception:
            return "other"

    tot = collections.Counter()
    by_class = collections.Counter()
    by_cat = collections.Counter()
    by_dest = collections.Counter()
    xtab = collections.Counter()
    dest_pool = collections.Counter()
    names = collections.Counter()
    pool_class = collections.Counter()
    cur = collections.Counter()
    seeds_done = 0
    for s in range(a.seeds):
        with tempfile.TemporaryDirectory() as td:
            pd, od = os.path.join(td, "p"), os.path.join(td, "o")
            os.makedirs(pd); os.makedirs(od)
            for i in range(a.er_slots):
                open(os.path.join(pd, "er%d.yaml" % i), "w", encoding="utf-8").write(
                    er_yaml("ER%d" % (i + 1), a.num_regions, a.extra))
            for i, pk in enumerate(x for x in a.partners.split(",") if x):
                open(os.path.join(pd, "pt%d.yaml" % i), "w", encoding="utf-8").write(PARTNERS[pk] % (i + 1))
            md = multidata(gen(a.ap_dir, pd, od, 20260810 + s))
        si = md["slot_info"]
        _lc = {si[p].game: 0 for p in si}
        for p, rows in md["locations"].items():
            _lc[si[p].game] = _lc.get(si[p].game, 0) + len(rows)
        print("   locations by game: %s" % _lc)
        er = {p for p, i in si.items() if i.game == "Elden Ring"}
        # CURATION SIDE: foreign advancement landing in an ER world -- how much of it sits on that
        # world's progression surface? That is what confine buys, and what lowering it spends.
        sd = md.get("slot_data", {})
        for holder in er:
            surf = set((sd.get(holder) or {}).get("progressionSurfaceLocations") or ())
            if not surf:
                continue
            for lid, (iid, ip, fl) in (md["locations"].get(holder) or {}).items():
                if ip == holder or not (fl & ADV):
                    continue
                cur["foreign prog into ER"] += 1
                if lid in surf:
                    cur["... on surface"] += 1
        for holder, rows in md["locations"].items():
            for lid, (iid, ip, fl) in rows.items():
                if ip not in er:
                    continue
                nm = id2name.get(iid, "?%d" % iid)
                pool_class["progression" if fl & ADV else ("useful" if fl & USEFUL else
                           ("trap" if fl & TRAP else "filler"))] += 1
                tot["all ER items placed"] += 1
                if holder == ip:
                    continue
                tot["exported"] += 1
                by_class["progression" if fl & ADV else ("useful" if fl & USEFUL else
                         ("trap" if fl & TRAP else "filler"))] += 1
                by_cat[category(nm)] += 1
                by_dest[si[holder].game] += 1
                xtab[(si[holder].game, "progression" if fl & ADV else ("useful" if fl & USEFUL else ("trap" if fl & TRAP else "filler")))] += 1
                dest_pool[si[holder].game] += 1
                names[nm] += 1
        seeds_done += 1

    n = seeds_done
    print("\n===== %s | %d seeds | %dx Elden Ring + partners[%s] | num_regions=%d" % (a.label, n, a.er_slots, a.partners, a.num_regions))
    print("ER items placed: %d   exported to a foreign world: %d  (%.1f%%)"
          % (tot["all ER items placed"], tot["exported"], 100.0 * tot["exported"] / max(tot["all ER items placed"], 1)))
    print("\n-- ER POOL by classification (all placements) --")
    for k in ("progression", "useful", "filler", "trap"):
        v = pool_class[k]
        print("  %-12s %7d  %5.1f%%" % (k, v, 100.0 * v / max(sum(pool_class.values()), 1)))
    print("\n-- EXPORTED by classification --")
    for k in ("progression", "useful", "filler", "trap"):
        v = by_class[k]
        print("  %-12s %7d  %5.1f%% of exports   (export rate for that class: %.1f%%)"
              % (k, v, 100.0 * v / max(sum(by_class.values()), 1),
                 100.0 * v / max(pool_class[k], 1)))
    print("\n-- EXPORTED by ER category --")
    for k, v in by_cat.most_common():
        print("  %-20s %7d  %5.1f%%" % (k, v, 100.0 * v / max(sum(by_cat.values()), 1)))
    print("\n-- EXPORT destination --")
    for k, v in by_dest.most_common():
        print("  %-20s %7d  %5.1f%%" % (k, v, 100.0 * v / max(sum(by_dest.values()), 1)))
    print("\n-- destination x classification (share of that destination's ER imports) --")
    for g in sorted({k[0] for k in xtab}):
        tot_g = dest_pool[g]
        row = "  %-18s n=%-6d " % (g, tot_g)
        for c in ("progression", "useful", "filler", "trap"):
            row += "%s %5.1f%%  " % (c, 100.0 * xtab[(g, c)] / max(tot_g, 1))
        print(row)
    fp = cur["foreign prog into ER"]
    print("\n-- CURATION: foreign advancement placed in an ER world: %d, on-surface %d (%.1f%%) --"
          % (fp, cur["... on surface"], 100.0 * cur["... on surface"] / max(fp, 1)))
    print("\n-- top 15 exported item names --")
    for k, v in names.most_common(15):
        print("  %-40s %5d" % (k, v))


main()
