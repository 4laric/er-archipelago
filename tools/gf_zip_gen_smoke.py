#!/usr/bin/env python3
"""ZIPPED-APWORLD GENERATION SMOKE TEST -- the CI guard for the custom_worlds crash class.

WHY THIS EXISTS. The unit suite (tools/gf_test.py) installs the world UNPACKED into
`.ap-test/worlds/eldenring` and runs pytest there. That path can NEVER catch a bug that only manifests
when the apworld is a ZIP -- and a released `.apworld` IS a zip. Any code that reads a bundled data
file with `open(os.path.join(os.path.dirname(__file__), name))` works unpacked and raises inside the
archive, because `__file__` then points into the zip and there is no such path on disk.

That is exactly what took down EVERY custom_worlds (Nexus) generation on 2026-07-19: `coverage.py`
read `check_lots_table.json` with a plain `open()`, got a file-not-found inside the zip, swallowed it,
returned an empty table, and the post_fill coverage gate then raised `CoverageError` on ~7100 checks
it now believed were unsuppressed. Not one unpacked test saw it, because the whole suite runs unpacked.

WHAT THIS DOES. Reproduce the real install: zip the built world into
`.ap-test/custom_worlds/eldenring.apworld`, hide the unpacked copy so AP MUST load the zip, and run one
generation from it. If any bundled-resource read is not zip-safe, generation dies HERE -- in CI, before
a release -- instead of on a user's machine. It is deliberately a black-box generation, not a pytest
import: the failure mode is invisible to anything that imports the world unpacked.

RUN:
  python tools/gf_zip_gen_smoke.py                       # CI: zip the world CI just installed, gen
  python tools/gf_zip_gen_smoke.py --apworld PATH.apworld # RELEASE: gen from the EXACT built artifact

The --apworld form is the release gate (package_release.ps1): it generates from the very .apworld about
to be shipped, so a broken artifact can never be published. With no argument it builds the zip itself
from the installed world -- the CI form, testing current source.

Exits 0 on a clean generation, non-zero on any failure (so run_ci.ps1 / package_release.ps1 gate on it).
"""
import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gf_test  # reuse REPO / ap_pin / ensure_ap / install_world -- ONE definition of "the built world"

# A bare, all-defaults solo seed. The crash was option-independent (the coverage gate runs on every
# seed), so the minimal config is the strongest signal: if THIS won't generate from a zip, nothing will.
BASE_YAML = 'name: ZipSmoke\ngame: "Elden Ring"\n"Elden Ring": {}\n'

# ModuleUpdate.update() prompts to pip-install missing deps (interactive) -- neutered so the run is
# non-interactive. AP still skips any *other* world whose deps are absent; Elden Ring only needs what
# gf_test's checkout already has.
RUNNER = (
    "import sys, os\n"
    "sys.path.insert(0, os.getcwd())\n"
    "import ModuleUpdate\n"
    "ModuleUpdate.update = lambda *a, **k: None\n"
    "ModuleUpdate.update_command = lambda *a, **k: None\n"
    "sys.argv = ['Generate.py', '--seed', '1', '--player_files_path', 'Players']\n"
    "import runpy; runpy.run_path('Generate.py', run_name='__main__')\n"
)

# Lines from other games' failed imports (missing optional deps in a minimal checkout) are noise, not
# our failure -- AP just skips those worlds. Filter them out when surfacing a real failure.
_NOISE = ("bsdiff4", "zilliandomizer", "orjson", "pyevermizer", "dolphin", "Could not load world")
_SIGNAL = ("elden", "coverage", "post_fill", "violation", "error", "exception", "traceback",
           "notadirectory", "filenotfound", "no such file", "done. enjoy", "player 1")


def _zip_world(world_dir: Path, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, files in os.walk(world_dir):
            if "__pycache__" in root:
                continue
            for f in files:
                if f.endswith(".pyc"):
                    continue
                full = Path(root) / f
                arc = Path("eldenring") / full.relative_to(world_dir)  # zip root holds the package dir
                z.write(str(full), str(arc))


def main() -> int:
    p = argparse.ArgumentParser(description="Generate one seed from a ZIPPED Elden Ring apworld.")
    p.add_argument("--apworld", metavar="PATH", default=None,
                   help="Generate from THIS prebuilt .apworld (the release artifact). Omit to build the "
                        "zip from the installed world (the CI form).")
    args = p.parse_args()

    ap = Path(gf_test.REPO) / ".ap-test"
    if not (ap / "worlds").is_dir():
        # A usable AP checkout is required either way (Generate.py + the loader). In CI the unit step
        # already bootstrapped it; for a fresh release machine, bootstrap the pinned upstream here.
        gf_test.ensure_ap(ap, gf_test.ap_pin())

    world = ap / "worlds" / "eldenring"
    apworld = ap / "custom_worlds" / "eldenring.apworld"
    hidden = ap / "worlds" / "_eldenring_zipsmoke_hidden"
    runner = ap / "_zipsmoke_run.py"
    players = ap / "Players"
    apworld.parent.mkdir(parents=True, exist_ok=True)

    if args.apworld:
        # RELEASE MODE: gen from the EXACT artifact being shipped -- copy it in as-is, never rebuild.
        src = Path(args.apworld).resolve()
        if not src.is_file():
            print("zip-smoke: --apworld not found: %s" % src)
            return 1
        if apworld.exists():
            apworld.unlink()
        shutil.copy2(str(src), str(apworld))
        print("zip-smoke: testing prebuilt artifact %s (%d bytes)" % (src, apworld.stat().st_size))
    else:
        # CI MODE: zip exactly what CI validated unpacked (fallback-install if none is present).
        if not world.is_dir():
            gf_test.install_world(ap)
        _zip_world(world, apworld)
        print("zip-smoke: built %s (%d bytes)" % (apworld, apworld.stat().st_size))

    # Hide any unpacked copy so AP MUST load the zip from custom_worlds (a fresh bootstrap has none).
    hid = False
    if world.is_dir():
        if hidden.exists():
            shutil.rmtree(hidden)
        shutil.move(str(world), str(hidden))
        hid = True

    try:
        players.mkdir(exist_ok=True)
        for y in players.glob("*.yaml"):
            y.unlink()
        (players / "ZipSmoke.yaml").write_text(BASE_YAML, encoding="utf-8")
        runner.write_text(RUNNER, encoding="utf-8")

        r = subprocess.run([sys.executable, str(runner)], cwd=str(ap),
                           capture_output=True, text=True, timeout=900)
        out = r.stdout + r.stderr
        if "Done. Enjoy" in out and r.returncode == 0:
            print("zip-smoke: OK -- generation from the zipped apworld completed cleanly.")
            return 0
        print("zip-smoke: FAILED -- generation from the zipped apworld did not complete "
              "(exit %s). This is the custom_worlds crash class: a bundled-resource read that is not "
              "zip-safe. Relevant lines:\n" % r.returncode)
        for line in out.splitlines():
            low = line.lower()
            if any(s in low for s in _SIGNAL) and not any(n in line for n in _NOISE):
                print("  " + line)
        return 1
    finally:
        # Restore the unpacked world (only if we hid one) so a following unpacked run is unaffected,
        # and clean up the scratch artifacts.
        if hid:
            if world.exists():
                shutil.rmtree(world)
            shutil.move(str(hidden), str(world))
        runner.unlink(missing_ok=True)
        apworld.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
