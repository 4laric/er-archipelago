#!/usr/bin/env python3
"""Per-sphere upgrade-curve analyzer for greenfield ER seeds.

Reads GF_SPHERES_*.json dumps (written by core.generate_output under env ER_GF_DUMP_SPHERES) and,
for each fill sphere k, computes the MAX upgrade level reachable from the cumulative multiset of
items placed in spheres 0..k -- count-accurate, against tools/upgrade_costs.py:

    character level (runes)     flask charges (Golden Seeds)     flask potency (Sacred Tears)
    standard weapon (+N)        somber weapon (+N)               Scadutree / Revered blessing

Aggregates each curve across all seeds per sphere index (min / median / max), so you can see whether
a resource is starved early or dumped late, and tune pool density / placement / flatten accordingly.

    python tools/analyze_upgrade_curve.py --dumps 'out/**/GF_SPHERES_*.json'
    python tools/analyze_upgrade_curve.py --dumps out --stones-per-level 1     # simulate flatten
    python tools/analyze_upgrade_curve.py --dumps out --start-level 9 --costs my_costs.json

--stones-per-level mirrors the in-game flatten_regular_upgrades knob: omit for the real 2/4/6 ladder,
pass an int N for N-per-level, or a JSON list (len 3 / 8 / 25) for a custom standard-weapon ladder.
--costs loads a JSON of {table_name: value} overriding any VERIFY-tier constant in upgrade_costs.
"""
import argparse, glob, json, os, statistics, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import upgrade_costs as uc


def load_dumps(spec):
    """spec: a dir (recurses for GF_SPHERES_*.json), a glob, or a file. Returns [(seed, {player:[spheres]})]."""
    paths = []
    if os.path.isdir(spec):
        paths = glob.glob(os.path.join(spec, "**", "GF_SPHERES_*.json"), recursive=True) \
                or glob.glob(os.path.join(spec, "GF_SPHERES_*.json"))
    else:
        paths = glob.glob(spec, recursive=True)
    out = []
    for p in sorted(paths):
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        out.append((d.get("seed", os.path.basename(p)), d.get("spheres", {})))
    return out


def apply_cost_overrides(path):
    if not path:
        return
    over = json.load(open(path, encoding="utf-8"))
    for k, v in over.items():
        if hasattr(uc, k):
            setattr(uc, k, v)
        else:
            print(f"[warn] --costs key {k!r} is not a table in upgrade_costs; ignored", file=sys.stderr)


def curves_for_seed(spheres, stones_per_level, start_level):
    """spheres: list of [item names] per sphere. Returns list (per sphere) of the 7-curve dict on the
    CUMULATIVE multiset through that sphere."""
    cum = Counter()
    rows = []
    for locitems in spheres:
        cum.update(locitems)
        have = dict(cum)
        rows.append({
            "level":    uc.max_character_level(uc.runes_from_items(have), start_level=start_level),
            "flask_charges": uc.max_flask_charges(have.get("Golden Seed", 0)),
            "flask_potency": uc.max_flask_potency(have.get("Sacred Tear", 0)),
            "standard": uc.max_standard_level(have, stones_per_level),
            "somber":   uc.max_somber_level(have),
            "scadutree": uc.max_scadutree(have.get("Scadutree Fragment", 0)),
            "revered":  uc.max_revered(have.get("Revered Spirit Ash", 0)),
        })
    return rows


CURVES = ["level", "standard", "somber", "flask_charges", "flask_potency", "scadutree", "revered"]


def analyze(dumps, player, stones_per_level, start_level):
    """Returns {curve: {sphere_idx: [values across seeds]}} and the max sphere count."""
    agg = {c: {} for c in CURVES}
    max_spheres = 0
    for seed, per_player in dumps:
        names = list(per_player)
        if not names:
            continue
        pl = player if (player and player in per_player) else names[0]
        spheres = per_player[pl]
        max_spheres = max(max_spheres, len(spheres))
        for sidx, row in enumerate(curves_for_seed(spheres, stones_per_level, start_level)):
            for c in CURVES:
                agg[c].setdefault(sidx, []).append(row[c])
    return agg, max_spheres


def analyze_normalized(dumps, player, stones_per_level, start_level, nbins):
    """Bin each seed by COMPLETION FRACTION instead of raw sphere index, so seeds of different depth
    are comparable. Curves are cumulative-monotone within a seed, so a bin at fraction f takes the
    value at the deepest sphere whose fraction i/(S-1) <= f (forward-fill). Every seed contributes to
    every bin -> aggregation is apples-to-apples. Returns {curve: {bin: [values]}}."""
    agg = {c: {b: [] for b in range(nbins)} for c in CURVES}
    for seed, per_player in dumps:
        names = list(per_player)
        if not names:
            continue
        pl = player if (player and player in per_player) else names[0]
        rows = curves_for_seed(per_player[pl], stones_per_level, start_level)
        S = len(rows)
        if S == 0:
            continue
        for b in range(nbins):
            f = b / (nbins - 1) if nbins > 1 else 1.0
            j = 0 if S == 1 else max(i for i in range(S) if i / (S - 1) <= f + 1e-9)
            for c in CURVES:
                agg[c][b].append(rows[j][c])
    return agg


def print_table(agg, max_spheres, nseeds):
    def cell(vals):
        if not vals:
            return "   -   "
        return f"{min(vals):>2}/{int(round(statistics.median(vals))):>2}/{max(vals):>2}"
    hdr = "sphere    n" + "".join(f"{c[:9]:>10}" for c in CURVES)
    print(f"\nper-sphere max upgrade  (min/median/max across up to {nseeds} seed(s); n = seeds deep enough)")
    print(hdr)
    print("-" * len(hdr))
    for s in range(max_spheres):
        n = len(agg["level"].get(s, []))
        line = f"{s:>6} {n:>4} " + "".join(f"{cell(agg[c].get(s, [])):>10}" for c in CURVES)
        print(line)


def smoothstep(f):
    f = max(0.0, min(1.0, f))
    return f * f * (3 - 2 * f)


def target_level(f, mx, floor_frac):
    """Target weapon +level tracking the client's smoothstep difficulty scaling: floor at f=0, mx at
    f=1 (deepest sphere = max weapon). floor_frac lifts the whole curve (mirrors completion_scaling_floor)."""
    return round((floor_frac + (1 - floor_frac) * smoothstep(f)) * mx)


def fit_standard(agg, nbins, target_max=25, target_floor=0.0):
    """Fit of the standard-weapon MEDIAN curve to the smoothstep target across completion bins.
    Returns (mae, bias) where bias = mean(achieved-target) (<0 = undershoot). Lower |mae| = closer."""
    import statistics as _st
    res = []
    for b in range(nbins):
        f = b / (nbins - 1) if nbins > 1 else 1.0
        vals = agg["standard"][b]
        if not vals:
            continue
        med = _st.median(vals)
        res.append(med - target_level(f, target_max, target_floor))
    if not res:
        return (float("inf"), 0.0)
    return (sum(abs(r) for r in res) / len(res), sum(res) / len(res))


def print_norm_table(agg, nbins, nseeds, target=False, target_floor=0.0):
    def cell(vals):
        return "   -   " if not vals else f"{min(vals):>2}/{int(round(statistics.median(vals))):>2}/{max(vals):>2}"
    extra = "  std_tgt  som_tgt" if target else ""
    hdr = "compl%    n" + "".join(f"{c[:9]:>10}" for c in CURVES) + extra
    print(f"\ncompletion-normalized max upgrade  (min/median/max across {nseeds} seed(s), forward-filled)")
    if target:
        print(f"(std_tgt/som_tgt = smoothstep target to +25/+10, floor {target_floor:.0%}; deepest sphere = max)")
    print(hdr)
    print("-" * len(hdr))
    for b in range(nbins):
        f = b / (nbins - 1) if nbins > 1 else 1.0
        pct = round(100 * f)
        n = len(agg["level"][b])
        line = f"{pct:>5}% {n:>4} " + "".join(f"{cell(agg[c][b]):>10}" for c in CURVES)
        if target:
            line += f"  {target_level(f, 25, target_floor):>7}  {target_level(f, 10, target_floor):>7}"
        print(line)


def parse_stones(arg):
    if arg is None:
        return None
    try:
        return int(arg)
    except ValueError:
        v = json.loads(arg)
        if not isinstance(v, list):
            raise SystemExit("--stones-per-level must be an int or a JSON list")
        return v


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dumps", required=True, help="dir, glob, or file of GF_SPHERES_*.json")
    ap.add_argument("--player", default=None, help="player name to analyze (default: first in each dump)")
    ap.add_argument("--stones-per-level", default=None,
                    help="flatten override for standard weapons: int N or JSON list (len 3/8/25)")
    ap.add_argument("--start-level", type=int, default=1, help="character start level (default 1)")
    ap.add_argument("--normalize", type=int, nargs="?", const=11, default=None,
                    metavar="BINS", help="bin by completion %% (default 11 bins) instead of raw sphere")
    ap.add_argument("--costs", default=None, help="JSON overriding VERIFY-tier cost tables")
    ap.add_argument("--target", action="store_true", help="show smoothstep upgrade target (deepest sphere = max)")
    ap.add_argument("--target-floor", type=float, default=0.0, help="target floor fraction 0..1 (default 0)")
    ap.add_argument("--fit", action="store_true", help="print MAE/bias of standard median vs smoothstep target (one line)")
    a = ap.parse_args(argv)
    apply_cost_overrides(a.costs)
    dumps = load_dumps(a.dumps)
    if not dumps:
        raise SystemExit(f"no GF_SPHERES_*.json found under {a.dumps!r}")
    spl = parse_stones(a.stones_per_level)
    if a.normalize:
        agg = analyze_normalized(dumps, a.player, spl, a.start_level, a.normalize)
        if a.fit:
            mae, bias = fit_standard(agg, a.normalize, target_floor=a.target_floor)
            print(f"MAE={mae:5.2f}  bias={bias:+5.2f}  (n_seeds={len(dumps)})")
        else:
            print_norm_table(agg, a.normalize, len(dumps), target=a.target, target_floor=a.target_floor)
    else:
        agg, maxs = analyze(dumps, a.player, spl, a.start_level)
        print_table(agg, maxs, len(dumps))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
