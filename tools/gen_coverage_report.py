#!/usr/bin/env python3
"""gen_coverage_report.py -- emit the timestamped coverage triage report (hand-authored tool).

Runs the closed-loop coverage gate (greenfield/eldenring/coverage.py) in STATIC full-pool REPORT
MODE (all regions, every emitted location, no AP world / no fill needed) and writes
COVERAGE-REPORT-<UTC-timestamp>.md at the repo root -- the definitive triage list of detection /
suppression / region-consistency holes, with the historically-known failure classes called out
explicitly. Never raises on violations (report mode); it only reports.

    python tools/gen_coverage_report.py            # writes ./COVERAGE-REPORT-<ts>.md
    python tools/gen_coverage_report.py --print    # also echo the report to stdout
"""
import importlib.util
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GF_PKG = os.path.join(REPO, "greenfield", "eldenring")


def _load_coverage():
    """Load coverage.py directly by path so the tool works from the source tree without installing
    the world under Archipelago/worlds (coverage.py itself file-path-loads its sibling data modules)."""
    path = os.path.join(GF_PKG, "coverage.py")
    spec = importlib.util.spec_from_file_location("gf_coverage_report", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv):
    cov = _load_coverage()
    records, ctx, byname = cov.report_coverage(world=None, printer=print)
    ts, md = cov.render_markdown(records, ctx, byname)
    out = os.path.join(REPO, f"COVERAGE-REPORT-{ts}.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[coverage] wrote {out}")
    if "--print" in argv:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
