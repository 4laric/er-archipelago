#!/usr/bin/env python3
"""sample_pool_composition.py -- how much of a seed is filler, and how much is real gear.

WHY THIS IS SAMPLED AND THE REST OF THE CENSUS IS NOT. `wizard/region-census.json` is EXACT: a
seed's check count and its progression surface are sums over per-region tables, so they can be
computed without building anything. The filler/useful split cannot. `features/filler_budget` and the
pool builder reshape the Rune tail into curated real items at generation time, so the only honest
way to know the ratio is to BUILD WORLDS AND COUNT.

So this tool builds them -- `WorldTestBase` per option set, `ItemClassification` over the pool plus
the pre-placed items -- and writes `wizard/pool-composition.json`, which the wizard's Seed size tab
reads. The alternative was a number typed into a docstring, and this repo already has a whole tool
(`build_surface_confidence.py`) whose reason for existing is that a hand-recorded number is stale the
next time anyone regenerates.

🛑 IT IS A BAND, NOT A FIGURE, AND THE ARTIFACT SAYS SO. Every field is min/median/max over N draws,
because `num_regions` is a draw size: which regions the seed keeps moves the ratio. Anything that
renders this must show the spread. A median presented alone would be the same lie the seed-count
panel exists to avoid.

🛑 NOT DIFF-GATED, deliberately, and this is the honest limitation. The draw is random per build, so
re-running produces different numbers within the band and a `--check` that demanded byte-equality
would be red forever. What IS recorded is provenance: the world commit, the sample count, and the
date, so a reader can tell how old the measurement is and reproduce it. Tightening this into a
determinstic gate means driving `Generate.py --seed N` and classifying the spoiler, which is a
bigger, slower job for the `tests` job -- worth doing, not done here.

Needs an Archipelago checkout with the world installed (same environment as the test suite).

Usage:
    python tools/sample_pool_composition.py --ap-dir .ap-test [--samples 12]
"""
import argparse
import collections
import re
import datetime
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "wizard", "pool-composition.json")
WIZARD_HTML = os.path.join(ROOT, "wizard", "wizard.html")
SCRIPT_ID = "er-pool-composition"

# The option sets the wizard can meaningfully interpolate between. Kept SMALL: every row costs
# `samples` world builds, and the ratio moves far less with num_regions than the check count does.
CASES = [
    {"label": "default", "options": {}},
    {"label": "num_regions=1", "options": {"num_regions": 1}},
    {"label": "num_regions=3", "options": {"num_regions": 3}},
    {"label": "num_regions=12", "options": {"num_regions": 12}},
    {"label": "whole map", "options": {"num_regions": 0}},
    {"label": "base game", "options": {"enable_dlc": False}},
]


def measure(samples):
    from test.bases import WorldTestBase
    from BaseClasses import ItemClassification as IC

    def cls(i):
        if i.classification & IC.progression:
            return "progression"
        if i.classification & IC.useful:
            return "useful"
        return "filler"

    rows = []
    for case in CASES:
        pcts = collections.defaultdict(list)
        for _ in range(samples):
            class _T(WorldTestBase):
                game = "Elden Ring"
                options = dict(case["options"])
                def runTest(self):
                    pass
            t = _T("runTest")
            t.setUp()
            mw = t.multiworld
            locs = [l for l in mw.get_locations(1) if not l.is_event]
            items = [i for i in mw.itempool if i.player == 1] + [l.item for l in locs if l.item]
            c = collections.Counter(cls(i) for i in items)
            n = len(items) or 1
            for k in ("filler", "useful", "progression"):
                pcts[k].append(100.0 * c[k] / n)
            pcts["checks"].append(len(locs))
        row = {"label": case["label"], "options": case["options"]}
        for k, v in pcts.items():
            v = sorted(v)
            q = lambda p: v[int(p * (len(v) - 1))]
            row[k] = [round(q(0), 1), round(q(0.5), 1), round(q(1), 1)]
        rows.append(row)
        print("  %-16s filler %s  useful %s  prog %s"
              % (row["label"], row["filler"], row["useful"], row["progression"]))
    return rows


def world_commit():
    try:
        return subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()[:12]
    except Exception:
        return "unknown"


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--ap-dir", default=os.path.join(ROOT, ".ap-test"))
    p.add_argument("--samples", type=int, default=12)
    args = p.parse_args(argv)

    ap = os.path.abspath(args.ap_dir)
    if not os.path.isdir(ap):
        sys.exit("sample_pool_composition: no AP checkout at %s -- run tools/gf_test.py first." % ap)
    sys.path.insert(0, ap)
    os.chdir(ap)

    print("sampling %d world(s) per case ..." % args.samples)
    rows = measure(args.samples)

    doc = {
        "schema": 1,
        # PROVENANCE, not decoration: this artifact cannot be diff-gated, so the only defence
        # against quoting a stale ratio is being able to see how old it is and re-run it.
        "sampled": True,
        "samples_per_case": args.samples,
        "world_commit": world_commit(),
        "measured_on": datetime.date.today().isoformat(),
        "note": ("min/median/max over independent draws. num_regions is a draw size, so which "
                 "regions a seed keeps moves these ratios -- render the spread, never the median "
                 "alone."),
        "cases": rows,
    }
    text = json.dumps(doc, indent=1).replace("</", "<\\/") + "\n"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("[ok] wrote %s" % os.path.relpath(OUT, ROOT))
    # ALWAYS both copies. dump_options_metadata's docstring records the four commits that landed
    # when writing the file and injecting it were two separate opt-in steps.
    inject(text)
    return 0


def inject(text):
    html = open(WIZARD_HTML, "r", encoding="utf-8", newline="").read()
    blob = ('<script id="%s" type="application/json">\n' % SCRIPT_ID) + text + "</script>"
    pat = re.compile(r'<script id="%s" type="application/json">.*?</script>' % SCRIPT_ID, re.S)
    if not pat.search(html):
        sys.exit('[FAIL] inject: <script id="%s"> placeholder not found in wizard.html' % SCRIPT_ID)
    with open(WIZARD_HTML, "w", encoding="utf-8", newline="") as f:
        f.write(pat.sub(lambda _m: blob, html, count=1))
    print("[ok] injected composition into %s" % os.path.relpath(WIZARD_HTML, ROOT))


if __name__ == "__main__":
    sys.exit(main())
