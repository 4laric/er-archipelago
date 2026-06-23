#!/usr/bin/env python3
"""Pre-generation guard for the ER Archipelago dev loop. Run BEFORE Generate.py.

Targets the two failure modes that cost the most blind iterations:

  1) STALE BYTECODE. Python reuses worlds/eldenring/__pycache__/*.pyc when the cached
     embedded source-mtime matches the source -- and over the dev mount that match can
     persist even after a real edit, so the gen silently runs OLD code. Symptom: the same
     FillError N times in a row, edits "having no effect". Fix: invalidate the cache before
     every gen so Python must recompile from source.

  2) YAML OPTIONS STRANDED AT THE DOCUMENT ROOT. Archipelago only applies per-game options
     (accessibility, progression_balancing, ...) when they're indented UNDER the game block
     (e.g. `EldenRing:`). At column 0 they're a sibling of the game key and silently ignored,
     so the world runs at the option default. Symptom: a yaml change that "does nothing".

Warn-only (always exits 0); it just prints, so the gen log self-documents what it did.
Usage:  python pregen.py            (run from anywhere; locates the repo via __file__)
"""
import os
import glob

REPO = os.path.dirname(os.path.abspath(__file__))
AP = os.path.join(REPO, "Archipelago")
WORLD = os.path.join(AP, "worlds", "eldenring")

# AP per-game options frequently mis-placed at the document root (silently ignored there).
PER_GAME_OPTIONS = {
    "accessibility", "progression_balancing", "local_items", "non_local_items",
    "start_inventory", "start_inventory_from_pool", "start_hints", "start_location_hints",
    "exclude_locations", "priority_locations", "item_links", "death_link",
}


def invalidate_eldenring_bytecode():
    """Remove (or, if locked, zero the magic of) every eldenring .pyc so the gen recompiles."""
    pycs = glob.glob(os.path.join(WORLD, "**", "*.pyc"), recursive=True)
    n_removed = n_zeroed = n_failed = 0
    for f in pycs:
        try:
            os.remove(f)
            n_removed += 1
        except OSError:
            # Couldn't delete (locked / permission). A 4-byte invalid magic header still forces
            # a recompile -- Python rejects the bad .pyc and rebuilds from the .py.
            try:
                with open(f, "r+b") as h:
                    h.write(b"\x00\x00\x00\x00")
                n_zeroed += 1
            except OSError:
                n_failed += 1
                print("  WARN could not invalidate %s" % f)
    for d in glob.glob(os.path.join(WORLD, "**", "__pycache__"), recursive=True):
        try:
            os.rmdir(d)  # only succeeds if now empty
        except OSError:
            pass
    print("[pregen] eldenring bytecode invalidated: %d removed, %d zeroed, %d failed (of %d) "
          "-- gen will recompile from source" % (n_removed, n_zeroed, n_failed, len(pycs)))


def lint_player_yamls():
    """Warn if a per-game option sits at column 0 (document root) in any Players/*.yaml."""
    warned = 0
    for y in sorted(glob.glob(os.path.join(AP, "Players", "*.yaml"))):
        try:
            lines = open(y, encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            continue
        for i, raw in enumerate(lines, 1):
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            if raw[0].isspace():
                continue  # indented -> inside a block, fine
            key = raw.split(":", 1)[0].strip()
            if key in PER_GAME_OPTIONS:
                print("  WARN %s:%d  per-game option '%s' is at the document ROOT -> Archipelago "
                      "IGNORES it. Indent it under the game block (e.g. 'EldenRing:')."
                      % (os.path.basename(y), i, key))
                warned += 1
    if not warned:
        print("[pregen] yaml lint: no per-game options stranded at the document root")


def run_option_linter():
    """Run the ER option-conflict linter (er_yaml_lint.py) over Players/*.yaml. Warn-only:
    it prints findings but never changes pregen's exit code, so a bad combo can't block a gen."""
    try:
        import er_yaml_lint
    except Exception as e:
        print("[pregen] option linter unavailable (er_yaml_lint.py): %s" % e)
        return
    print("==== option-conflict linter (er_yaml_lint) ====")
    try:
        er_yaml_lint.main([os.path.join(AP, "Players")])
    except Exception as e:
        print("[pregen] option linter error (skipped): %s" % e)


if __name__ == "__main__":
    print("==== pregen guard (stale-bytecode + yaml-root lint) ====")
    if not os.path.isdir(WORLD):
        print("  WARN eldenring world not found at %s -- skipping bytecode step" % WORLD)
    else:
        invalidate_eldenring_bytecode()
    lint_player_yamls()
    run_option_linter()
