#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""regen_all.py -- THE regen entrypoint. ONE step list, every consumer reads it.

WHY THIS FILE EXISTS (issue #699, 2026-08-15). The regen procedure was written down in three
places and they disagreed:

  * `AGENTS.md` section 5a -- the one humans and agents are TOLD to follow. It stopped at the
    generated `.py` modules and named NONE of the page builders.
  * `.github/workflows/tests.yaml` (`generators` job) -- the complete emitted set, plus
    `gen_area_tiers.py --check`.
  * `build.ps1 -Greenfield` -- the complete emitted set MINUS `gen_area_tiers.py --check`.

MOTIVATING CASE (CONTRIBUTING rule 11). PR #698, 2026-08-15: an agent followed the AGENTS.md
recipe exactly, committed, and `generators` went red with

    apworld generated output is STALE -- regenerate and commit:
     er-archipelago-questline-dag.html | 2 +-

one line -- the page's `inputs_hash` stamp. The three root pages EMBED the stamp, so ANY change
that moves `inputs_hash` (including a comment edit to `gen_data.py`, which is `FILE_INPUTS[0]`)
re-stales all of them. That makes it every data PR's problem, not one agent's mistake, and only
CI's byte-diff notices. `tools/build_questline_dag_page.py` appeared nowhere in AGENTS.md or
CONTRIBUTING.md at all.

So the list lives HERE, once, and the consumers invoke this file instead of enumerating it.
`greenfield/eldenring/tests/test_gf_regen_all.py` is the gate that keeps it honest: it fails if a
stamp-bearing committed artifact, or an output declared by a staleness-checking `tools/build_*.py`,
is not reachable from `STEPS`. The latter is producer-driven -- generated files do not become
invisible merely because they live below `greenfield/` or `wizard/` instead of at the repo root.

WHY A NEW `tools/` SCRIPT AND NOT `gen_data.py --all`. `greenfield/gen_data.py` is
`gen_manifest.FILE_INPUTS[0]` -- its BYTES are hashed into `inputs_hash`. Adding a driver flag to
it would re-stamp every generated module and all three pages on a change that generates nothing,
which is the exact defect class this file exists to stop. A standalone `tools/*.py` with argparse
and a WHY docstring is also the shape the rest of `tools/` already has.

THE ORDER IS LOAD-BEARING -- THE STAMP IS WRITTEN, THEN READ.
`gen_data.py` writes `_GEN_STAMP`; the three pages EMBED it. Build a page before the stamp and it
carries the PREVIOUS one and the CI diff gate is red. `STEPS` is in execution order and the phases
run in `PHASES` order; do not reorder either without reading this paragraph.

PHASES (`--phases`, default all, in this order):

  inputs   materialise gen_data's inputs from the committed bundle (idempotent)
  modules  the datamines -> gen_data.py -> the generated `eldenring/*.py` modules + `_GEN_STAMP`
  tables   the CROSS-REPO tables + repo-side contract and confidence tables
  pages    stamp-embedding readers plus generated wizard payloads

CLIENT-DEPENDENT STEPS ARE GATED HERE, IN ONE PLACE -- and that gate had to be written, because
MEASURED 2026-08-15 in a submodule-less checkout the three client steps fail three DIFFERENT ways:
`gen_contract.py` prints "skip contract_gen.rs (client src dir absent)" and exits 0;
`gen_area_tiers.py --check` prints a reason and exits **4**; `gen_region_locks.py` dies with a bare
`FileNotFoundError` traceback. Rather than "fix" three scripts a Windows build depends on, this
file asks the question once (`crates/` present?) and SKIPS the group loudly. In CI and on the box
the client IS checked out, so nothing is skipped there.

Run:
  python3 tools/regen_all.py                        # everything (the AGENTS.md section 5a recipe)
  python3 tools/regen_all.py --phases tables,pages  # what build.ps1 / the `generators` job need
  python3 tools/regen_all.py --list                 # print the steps, run nothing
  python3 tools/regen_all.py --dry-run
"""
import argparse
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT = os.path.join(REPO, "from-software-archipelago-clients")

INPUTS, MODULES, TABLES, PAGES = "inputs", "modules", "tables", "pages"
PHASES = [INPUTS, MODULES, TABLES, PAGES]


class Step(object):
    """One command, plus what it EMITS -- the emits are what the gate reads."""

    def __init__(self, phase, script, args=(), emits=(), needs_client=False, why=""):
        self.phase = phase
        self.script = script            # repo-relative, POSIX separators
        self.args = list(args)
        self.emits = list(emits)        # repo-relative; `*` allowed (fnmatch)
        self.needs_client = needs_client
        self.why = why

    @property
    def name(self):
        return os.path.basename(self.script)[:-3]

    def argv(self):
        return [sys.executable, os.path.join(REPO, *self.script.split("/"))] + self.args

    def display(self):
        return " ".join(["python", self.script] + self.args)


# ---------------------------------------------------------------------------------------------
# THE LIST. Execution order. Reconciled 2026-08-15 from tests.yaml `generators` + build.ps1
# `-Greenfield`; the one place they disagreed was `gen_area_tiers.py --check` (CI had it,
# build.ps1 did not) and it is KEPT, because CI is the gate that decides whether a tree is green.
# ---------------------------------------------------------------------------------------------
STEPS = [
    Step(INPUTS, "tools/gen_inputs.py", ["--ensure", "elden_ring_artifacts"],
         why="extract the committed input bundle only if it is not already there. `--ensure`, not "
             "`--extract`: idempotent, so re-running the entrypoint is cheap. The DEST matters -- "
             "`--ensure .` scatters event/ msg/ talk/ into the repo root and gen_data then refuses "
             "with '6 DECLARED input(s) are missing'."),

    Step(MODULES, "tools/datamine_boss_drops.py",
         emits=["greenfield/eldenring/boss_drops.py"],
         why="a DECLARED input of the stamp, and gen_data imports it -- so it runs first."),
    Step(MODULES, "tools/datamine_boss_healthbars.py",
         emits=["greenfield/eldenring/boss_healthbars.py"],
         why="same: FILE_INPUTS entry, consumed by gen_data."),
    Step(MODULES, "tools/datamine_achievement_bosses.py",
         emits=["greenfield/achievement_bosses.tsv"],
         why="the MajorBoss roster (#737), read by gen_data. AFTER the two datamines above and "
             "never before them: its classifier IS boss_healthbars + boss_reward_lots, so run out "
             "of order it would emit a roster of mostly kind=collection rows -- a SMALLER default "
             "progression surface, written to a committed table, reported as a clean run."),
    Step(MODULES, "tools/gen_death_award_pairs.py",
         emits=["greenfield/eldenring/death_award_pairs.json"],
         why="the (death flag, check flag) pairs behind EMEVD corpse-treasure awards "
             "(clients#385): a static me3 table the client sweeps so an unwitnessed death "
             "cannot leave a check permanently unpayable. Reads the event corpus, so after "
             "INPUTS; independent of gen_data."),

    Step(MODULES, "tools/datamine_shop_open_ranges.py",
         emits=["greenfield/shop_open_ranges.tsv"],
         why="shop-menu display scopes (issue #937): gen_data REFUSES to emit shop_data.py without "
             "them (a scopeless emit would silently regress the spare-row coloring to the shared-"
             "label draw). Reads the talk corpus, so after INPUTS; before gen_data, which reads "
             "the tsv."),

    Step(MODULES, "greenfield/gen_data.py",
         emits=["greenfield/eldenring/*.py", "greenfield/eldenring/_gen_stamp.json"],
         why="WRITES THE STAMP. Everything below reads it; nothing below may precede it."),
    Step(MODULES, "tools/gen_manifest.py",
         ["--verify", "greenfield/eldenring/_gen_stamp.json"],
         why="prove the stamp on disk equals a fresh manifest -- catches the 'edited a source file "
             "AFTER regenerating' trap, which cost six CI rounds on world PR #481."),

    Step(TABLES, "tools/gen_region_locks.py", needs_client=True,
         why="region_locks.rs -- the THIRD cross-repo table, baked from the region_groups spine."),
    Step(TABLES, "greenfield/gen_contract.py",
         emits=["greenfield/CONTRACT.md", "greenfield/eldenring/contract.json"],
         why="repo-side halves (CONTRACT.md, contract.json) ALWAYS; contract_gen.rs only when the "
             "client is checked out -- it skips that half itself, which is why this step is not "
             "flagged needs_client."),
    Step(TABLES, "tools/gen_area_tiers.py", ["--check"], needs_client=True,
         why="THE STEP build.ps1 WAS MISSING (issue #699). Its DATA half is tier-2 (needs the "
             "MSBs), so this half only CHECKS: red means re-run without --check and commit."),
    Step(TABLES, "tools/derive_sweep_anchor_coords.py",
         emits=["greenfield/sweep_anchor_coords.tsv"],
         why="reads boss_sweeps.py, so ANY change to sweep membership re-stales it -- and it was "
             "outside this entrypoint, which is how #737 shipped a red CI on a table nobody had "
             "been told to regenerate. Its staleness gate lives in a repo-only suite that SKIPS in "
             "the installed-world layout, so a local `gf_test.py` run cannot see it and only the "
             "generators job can. AFTER gen_data (MODULES), which writes the sweeps it reads."),
    Step(TABLES, "tools/build_surface_confidence.py",
         emits=["greenfield/surface_confidence.tsv"],
         why="staleness-gated confidence table over generated location and surface data. It moved "
             "on #701 but regen_all omitted its producer -- the same hole #700 was meant to close."),

    Step(PAGES, "tools/build_check_browser.py",
         emits=["er-archipelago-check-browser.html"],
         why="embeds inputs_hash -> stale on every stamp move."),
    Step(PAGES, "tools/build_desc_triage.py",
         emits=["er-archipelago-desc-triage.html"],
         why="embeds inputs_hash -> stale on every stamp move."),
    Step(PAGES, "tools/build_questline_dag.py",
         emits=["greenfield/questline_dag.tsv"],
         why="the tsv the page reads; a pure join, so a gen_data edit alone can move it."),
    Step(PAGES, "tools/build_questline_model.py",
         emits=["greenfield/questline_model.tsv"],
         why="typed union of the flag-only DAG and revision-pinned CC-wiki evidence; must run "
             "after build_questline_dag.py because the model treats that table as its machine "
             "evidence layer."),
    Step(PAGES, "tools/build_questline_dag_page.py",
         emits=["er-archipelago-questline-dag.html"],
         why="THE PAGE THAT REDDENED #698, and the one that appeared in no doc at all. Mermaid is "
             "fetched at VIEW time, so this is offline-safe and byte-deterministic."),
    Step(PAGES, "tools/build_region_census.py",
         emits=["wizard/region-census.json", "wizard/wizard.html"],
         why="writes both the wizard's external census and its inlined copy. Both are "
             "staleness-gated generated artifacts, so one step deliberately owns both outputs."),
]


def client_present():
    """The same predicate gen_area_tiers.py uses -- `crates/` present, not just the dir."""
    return os.path.isdir(CLIENT) and os.path.isdir(os.path.join(CLIENT, "crates"))


def steps_for(phases):
    return [s for s in STEPS if s.phase in phases]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--phases", default=",".join(PHASES),
                    help="comma-separated subset of: " + ", ".join(PHASES))
    ap.add_argument("--list", action="store_true", help="print the steps and exit")
    ap.add_argument("--dry-run", action="store_true", help="print each command instead of running")
    args = ap.parse_args(argv)

    wanted = [p.strip() for p in args.phases.split(",") if p.strip()]
    unknown = [p for p in wanted if p not in PHASES]
    if unknown:
        print("regen_all: unknown phase(s) %s -- known: %s"
              % (", ".join(unknown), ", ".join(PHASES)), file=sys.stderr)
        return 2
    # Always in PHASES order, whatever order they were typed in: the stamp must precede the pages.
    phases = [p for p in PHASES if p in wanted]
    plan = steps_for(phases)

    if args.list:
        for s in plan:
            print("%-8s %-58s %s" % (s.phase, s.display(),
                                     "[needs client]" if s.needs_client else ""))
        return 0

    have_client = client_present()
    if not have_client:
        print("regen_all: no client checkout at %s (no crates/) -- the cross-repo table steps will "
              "be SKIPPED, not failed. Their output is not regenerable here; a sandbox tree is "
              "still self-consistent without them." % os.path.relpath(CLIENT, REPO))

    ran = skipped = 0
    for s in plan:
        if s.needs_client and not have_client:
            print("regen_all: SKIP  %s (no client checkout)" % s.display())
            skipped += 1
            continue
        print("regen_all: RUN   %s" % s.display())
        if args.dry_run:
            continue
        rc = subprocess.call(s.argv(), cwd=REPO)
        if rc != 0:
            print("regen_all: FAILED at `%s` (exit %d). Nothing after it ran, so the tree is HALF "
                  "regenerated -- fix the cause and re-run the whole entrypoint rather than the "
                  "remaining steps by hand (the stamp order is why)." % (s.display(), rc),
                  file=sys.stderr)
            return rc
        ran += 1

    print("regen_all: OK -- %d step(s) ran, %d skipped, phases: %s"
          % (ran, skipped, ",".join(phases)))
    if not args.dry_run:
        print("regen_all: now `git status --short` -- anything it lists is generated output that "
              "belongs in THIS commit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
