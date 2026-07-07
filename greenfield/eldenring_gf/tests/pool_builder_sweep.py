#!/usr/bin/env python3
r"""pool_builder_sweep.py -- scaling harness for the GREENFIELD ER pool_builder.

Matt-free port of worlds/eldenring/tests/pool_builder_sweep.py. Same idea -- run the
apworld's item-pool composition over many pinned seeds and report WHAT the pool builder
generates -- but every matt-derived input is gone:

  * game is "Elden Ring (Greenfield)" (the clean base), not "EldenRing".
  * item quality comes from the param-derived numeric rarity in eldenring_gf/item_tiers.py
    (0 trivial / 1 common / 2 rare / 3 legendary, from the vanilla EquipParam `rarity`
    column), NOT from a hand-curated S/A/B/C/D/F tier list.
  * the knobs swept are greenfield's real options (num_regions, pool_builder_intensity,
    pool_builder_juice_cap, item_shuffle, enable_dlc), not the bedrock world's
    world_logic / junk_retention / curated_fill / filler_upgrade_pct.

WHAT IT DOES
    Runs pool composition (world_setup -> create_items, i.e. everything that decides WHAT
    goes in the pool, but NOT the placement fill) over N pinned seeds, for each N in a
    sweep (default 100, 1000). For every seed it records the pool make-up (class buckets,
    rarity histogram, injected juice) and the wall-time, then aggregates per-N so you can
    watch the numbers converge as N grows and spot seed-to-seed variance.

    It stops before fill on purpose: pool_builder only touches the pool (the LOCATION always
    stays a check, only the item on it changes), so the fill step -- the slow part -- is
    irrelevant to what we're measuring. That's why N=1000 is affordable.

    "Juice" here = catalog equippables whose param rarity is at/above the intensity floor
    (normal>=3, high>=2 [default], max>=1). Greenfield classifies that juice `useful`
    (never progression -- region Locks stay the sole goal), so the headline metric is the
    count of juice-named items in the pool, and (with --compare) the delta vs pool_builder
    OFF is exactly the juice the builder injected. The feature's own accounting
    (pool_builder_juice_added / _candidates from slot_data) is reported alongside it.

RUN (Windows, from the Archipelago root, with your AP python 3.11+, after build.ps1 -Greenfield):
    python worlds/eldenring_gf/tests/pool_builder_sweep.py
    python worlds/eldenring_gf/tests/pool_builder_sweep.py --counts 100,1000,5000
    python worlds/eldenring_gf/tests/pool_builder_sweep.py --intensity max --compare
    python worlds/eldenring_gf/tests/pool_builder_sweep.py --num-regions 3 --tag nr3
    python worlds/eldenring_gf/tests/pool_builder_sweep.py --no-dlc --juice-cap 200

    --counts       comma list of N to sweep (nested: the N=100 seed set is the first 100
                   seeds of N=1000, so convergence is honest).            default 100,1000
    --intensity    pool_builder_intensity: normal / high / max (or 0/1/2). default high
    --num-regions  greenfield's marquee scope knob (0 = full world).      default 0
    --juice-cap    pool_builder_juice_cap (0 = auto-size to the Rune tail).default 120
    --grace-rando  turn grace_rando on (it reserves scatter slots -> shrinks the tail).
    --no-shuffle   turn item_shuffle OFF (pool_builder becomes a no-op; for the null case).
    --no-dlc       enable_dlc off (default follows greenfield: DLC on).
    --compare      ALSO run each seed with pool_builder OFF and report the delta (juice
                   injected vs the native shuffled pool). Doubles the run time.
    --seed-base    RNG base for reproducible seed sampling.               default 20260706
    --tag          label for the output filenames.                        default poolbuild

OUTPUTS (Archipelago root)
    poolbuild_gf_sweep_<tag>_<ts>.csv   one row per (N,seed): every metric + elapsed
    poolbuild_gf_sweep_<tag>_<ts>.md    per-N summary: mean/stdev/min/max + convergence

    Determinism is relative to the greenfield apworld SOURCE (same contract as the CI
    gen sweeps): edit the world and the same seed can move -- that's the point.
"""
import os
import sys
import csv
import time
import random
import argparse
import datetime
import statistics

GAME = "Elden Ring (Greenfield)"

# ER param `rarity`: 0 = trivial/ammo, 1 = common, 2 = rare, 3 = legendary. Label them for the
# histogram (matt-free: these are the vanilla param buckets, not a curated tier scheme).
RARITY_LABEL = {3: "legendary", 2: "rare", 1: "common", 0: "trivial"}
RARITY_KEYS = ("legendary", "rare", "common", "trivial", "none")
INTENSITY_ALIASES = {"0": "normal", "1": "high", "2": "max",
                     "normal": "normal", "high": "high", "max": "max"}


def _find_ap_root():
    """Locate the Archipelago root: the nearest ancestor holding both test/bases.py and
    worlds/eldenring_gf. Checked from this script's dir first (deployed under
    worlds/eldenring_gf/tests/) then from cwd, so the script runs from either place."""
    here = os.path.dirname(os.path.abspath(__file__))
    seeds = [here, os.getcwd()]
    seen = set()
    for start in seeds:
        d = start
        while True:
            if d in seen:
                break
            seen.add(d)
            if (os.path.isfile(os.path.join(d, "test", "bases.py"))
                    and os.path.isdir(os.path.join(d, "worlds", "eldenring_gf"))):
                return d
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
    return None


AP_ROOT = _find_ap_root()
if AP_ROOT is None:
    sys.exit("[pool_builder_sweep] could not find an Archipelago root with worlds/eldenring_gf "
             "on disk. Deploy the greenfield world first (build.ps1 -Greenfield) and run this "
             "from the Archipelago root or from worlds/eldenring_gf/tests/.")
os.chdir(AP_ROOT)
if AP_ROOT not in sys.path:
    sys.path.insert(0, AP_ROOT)

from test.bases import WorldTestBase                                      # noqa: E402
from BaseClasses import ItemClassification                               # noqa: E402
from worlds.eldenring_gf.item_tiers import ITEM_TIERS                    # noqa: E402
from worlds.eldenring_gf.features.pool_builder import (                  # noqa: E402
    PoolBuilderFeature, juice_order_for_floor, INTENSITY_FLOOR,
)


class _Harness(WorldTestBase):
    """Minimal WorldTestBase subclass driven by hand (not via unittest). run_default_tests off
    + auto_construct off so setUp does nothing -- we call world_setup(seed) ourselves per seed."""
    game = GAME
    auto_construct = False
    run_default_tests = False

    def runTest(self):  # noqa: N802  -- satisfies TestCase ctor; never executed
        pass


def _class_bucket(item):
    """Coarse AP classification bucket for one pool item (matt-free -- pure ItemClassification)."""
    if item.advancement:
        return "progression"
    if getattr(item, "trap", False):
        return "trap"
    if item.useful:
        return "useful"
    return "filler"


def _juice_set(world):
    """The pool builder's own per-world juice candidate names (best-first, DLC-filtered) at this
    world's resolved intensity floor. Reuse the feature so the sweep and the world agree exactly."""
    return set(PoolBuilderFeature()._juice_order(world))


def measure_one(seed, options):
    """Compose the pool for one seed; return a flat metrics dict."""
    h = _Harness("runTest")
    h.options = dict(options)
    t0 = time.perf_counter()
    h.world_setup(seed)
    elapsed = time.perf_counter() - t0

    items = [i for i in h.multiworld.itempool if i.player == h.player]
    juice = _juice_set(h.world)
    try:
        sd = h.world.fill_slot_data()
    except Exception:
        sd = {}

    m = {
        "seed": seed,
        "elapsed_s": round(elapsed, 4),
        "total": len(items),
        "progression": 0, "useful": 0, "filler": 0, "trap": 0,
        "juice_in_pool": 0,     # pool items whose name is a juice candidate == what the builder makes
        # the feature's own accounting (matt-free analog of bedrock's pool_builder_local):
        "juice_budget": int(sd.get("pool_builder_juice_added", 0)),
        "juice_candidates": int(sd.get("pool_builder_juice_candidates", len(juice))),
        "intensity_floor": int(sd.get("pool_builder_intensity_floor", 0)),
    }
    for k in RARITY_KEYS:
        m["rarity_" + k] = 0
    for it in items:
        m[_class_bucket(it)] += 1
        if it.name in juice:
            m["juice_in_pool"] += 1
        r = ITEM_TIERS.get(it.name)
        m["rarity_" + (RARITY_LABEL[r] if r in RARITY_LABEL else "none")] += 1
    return m


def sample_seeds(n, base):
    """n reproducible seeds; nested so smaller sweeps are prefixes of larger ones."""
    rng = random.Random(base)
    return [rng.getrandbits(48) for _ in range(n)]


def agg(rows, key):
    vals = [r[key] for r in rows]
    return {
        "mean": statistics.fmean(vals),
        "stdev": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
        "min": min(vals),
        "max": max(vals),
        "median": statistics.median(vals),
    }


def main():
    ap = argparse.ArgumentParser(description="Greenfield ER pool_builder scaling sweep")
    ap.add_argument("--counts", default="100,1000")
    ap.add_argument("--intensity", default="high",
                    help="normal/high/max (or 0/1/2); pool_builder_intensity")
    ap.add_argument("--num-regions", type=int, default=0,
                    help="greenfield scope knob (0 = full world)")
    ap.add_argument("--juice-cap", type=int, default=120,
                    help="pool_builder_juice_cap (0 = auto-size to the Rune tail)")
    ap.add_argument("--grace-rando", action="store_true")
    ap.add_argument("--no-shuffle", action="store_true",
                    help="item_shuffle OFF -> pool_builder no-op (null case)")
    ap.add_argument("--no-dlc", action="store_true", help="enable_dlc off (default: on)")
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--seed-base", type=int, default=20260706)
    ap.add_argument("--tag", default="poolbuild")
    args = ap.parse_args()

    intensity = INTENSITY_ALIASES.get(str(args.intensity).lower())
    if intensity is None:
        ap.error(f"--intensity must be normal/high/max (or 0/1/2), got {args.intensity!r}")

    counts = sorted({int(c) for c in args.counts.split(",") if c.strip()})
    max_n = max(counts)

    base_opts = {
        "item_shuffle": not args.no_shuffle,
        "enable_dlc": not args.no_dlc,
        "num_regions": args.num_regions,
        "grace_rando": bool(args.grace_rando),
    }
    on_opts = dict(base_opts, pool_builder=True,
                   pool_builder_intensity=intensity,
                   pool_builder_juice_cap=args.juice_cap)
    off_opts = dict(base_opts, pool_builder=False)

    seeds = sample_seeds(max_n, args.seed_base)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    csv_path = os.path.join(AP_ROOT, f"poolbuild_gf_sweep_{args.tag}_{ts}.csv")
    md_path = os.path.join(AP_ROOT, f"poolbuild_gf_sweep_{args.tag}_{ts}.md")

    metric_keys = (["elapsed_s", "total", "progression", "useful", "filler", "trap",
                    "juice_in_pool", "juice_budget", "juice_candidates", "intensity_floor"]
                   + ["rarity_" + k for k in RARITY_KEYS])
    if args.compare:
        metric_keys += ["off_juice_in_pool", "juice_injected"]

    all_rows = []       # per (N-bucket, seed) for CSV
    per_n_rows = {}     # N -> list of metric dicts (measured once, reused for nested Ns)
    measured = []       # metrics for the seeds measured so far (index-aligned to seeds)

    print(f"[pool_builder_sweep] game={GAME!r} intensity={intensity} num_regions={args.num_regions} "
          f"juice_cap={args.juice_cap} grace_rando={args.grace_rando} shuffle={not args.no_shuffle} "
          f"dlc={not args.no_dlc} compare={args.compare}")
    print(f"[pool_builder_sweep] sweeping N={counts} (max {max_n} seeds), base={args.seed_base}")

    t_start = time.perf_counter()
    for i, seed in enumerate(seeds):
        m = measure_one(seed, on_opts)
        if args.compare:
            mo = measure_one(seed, off_opts)
            m["off_juice_in_pool"] = mo["juice_in_pool"]
            m["juice_injected"] = m["juice_in_pool"] - mo["juice_in_pool"]
        measured.append(m)
        if (i + 1) % 50 == 0 or (i + 1) == max_n:
            print(f"  {i + 1}/{max_n} seeds  (elapsed {time.perf_counter() - t_start:0.1f}s)")

    for n in counts:
        per_n_rows[n] = measured[:n]
        for r in measured[:n]:
            row = {"N": n}
            row.update(r)
            all_rows.append(row)

    # ---- CSV ----
    fieldnames = ["N", "seed"] + metric_keys
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in all_rows:
            w.writerow(row)

    # ---- MD summary ----
    headline = ["total", "filler", "useful", "progression", "juice_in_pool",
                "juice_budget", "elapsed_s"]
    if args.compare:
        headline.insert(5, "juice_injected")
    lines = []
    lines.append(f"# greenfield pool_builder scaling sweep -- {ts}")
    lines.append("")
    lines.append(f"- game **{GAME}** (matt-free; rarity from vanilla param, not a curated tier list)")
    lines.append(f"- intensity **{intensity}** (floor {INTENSITY_FLOOR[intensity]}), "
                 f"num_regions **{args.num_regions}**, juice_cap **{args.juice_cap}**, "
                 f"grace_rando **{args.grace_rando}**, item_shuffle **{not args.no_shuffle}**, "
                 f"enable_dlc **{not args.no_dlc}**, compare **{args.compare}**")
    lines.append(f"- seed base `{args.seed_base}`, sweep `N={counts}` (nested: N=k is the first k seeds)")
    lines.append(f"- stopped before fill (pool composition only)")
    lines.append("")
    lines.append("## Convergence (mean +/- population stdev across the N seeds)")
    lines.append("")
    header = "| N | " + " | ".join(headline) + " |"
    sep = "|" + "---|" * (len(headline) + 1)
    lines.append(header)
    lines.append(sep)
    for n in counts:
        cells = [str(n)]
        for k in headline:
            a = agg(per_n_rows[n], k)
            if k == "elapsed_s":
                cells.append(f"{a['mean']:.3f} +/- {a['stdev']:.3f}")
            else:
                cells.append(f"{a['mean']:.1f} +/- {a['stdev']:.1f}")
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    # full stat block for the largest N
    lines.append(f"## Full metric spread at N={max_n} (min / median / mean / max, pop-stdev)")
    lines.append("")
    lines.append("| metric | min | median | mean | max | stdev |")
    lines.append("|---|---|---|---|---|---|")
    for k in metric_keys:
        a = agg(per_n_rows[max_n], k)
        fmt = (lambda v: f"{v:.3f}") if k == "elapsed_s" else (lambda v: f"{v:g}")
        lines.append(f"| {k} | {fmt(a['min'])} | {fmt(a['median'])} | "
                     f"{a['mean']:.2f} | {fmt(a['max'])} | {a['stdev']:.2f} |")
    lines.append("")
    total_wall = time.perf_counter() - t_start
    lines.append(f"_Total compose runs: {len(measured)}{' x2 (compare)' if args.compare else ''}; "
                 f"wall {total_wall:0.1f}s._")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\n[pool_builder_sweep] wrote:\n  {csv_path}\n  {md_path}")
    # echo the convergence table to console too
    print("\n".join(lines[lines.index(header):]))


if __name__ == "__main__":
    sys.exit(main())
