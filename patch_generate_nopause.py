#!/usr/bin/env python3
"""Stop `build.ps1 -Generate` from hanging on Enter when a gen ERRORS.

AP's Generate.py registers an atexit handler that runs input("Press enter to close.")
and only UNREGISTERS it on a clean exit. When generation throws, the unregister is
skipped, so at interpreter shutdown input() blocks on stdin -- invisibly, because
build.ps1 redirects stdout to the log -- until you press Enter.

Fix (two edits):
  1. Archipelago/Generate.py -- only arm the pause when interactive; skip it when
     AP_NONINTERACTIVE is set or stdin isn't a tty.
  2. build.ps1 -- set $env:AP_NONINTERACTIVE before the Generate.py call.

Hand-run interactive `python Generate.py` still pauses as before. Idempotent.
Run from the repo root:  python patch_generate_nopause.py
"""
import io, os, sys

EDITS = [
    # (file, old, new)
    ("Archipelago/Generate.py",
     '''    import atexit
    confirmation = atexit.register(input, "Press enter to close.")''',
     '''    import atexit, os, sys
    # Skip the interactive "Press enter to close." pause when run non-interactively
    # (build.ps1 sets AP_NONINTERACTIVE). On a gen ERROR the unregister below never
    # runs, so this atexit input() would otherwise block the build waiting on Enter
    # (invisibly, since stdout is redirected). isatty() also covers piped stdin.
    if os.environ.get("AP_NONINTERACTIVE") or not (sys.stdin and sys.stdin.isatty()):
        confirmation = None
    else:
        confirmation = atexit.register(input, "Press enter to close.")'''),

    ("Archipelago/Generate.py",
     '''    # in case of error-free exit should not need confirmation
    atexit.unregister(confirmation)''',
     '''    # in case of error-free exit should not need confirmation
    if confirmation:
        atexit.unregister(confirmation)'''),

    ("build.ps1",
     '''        # warnings (pkg_resources etc.). Both streams -> raw log; $LASTEXITCODE = python's code.''',
     '''        # warnings (pkg_resources etc.). Both streams -> raw log; $LASTEXITCODE = python's code.
        $env:AP_NONINTERACTIVE = "1"   # suppress Generate.py's atexit "Press enter to close." pause on error'''),
]


def apply(path, old, new):
    if not os.path.exists(path):
        sys.exit("ERROR: %s not found -- run from the repo root." % path)
    with io.open(path, "r", encoding="utf-8", newline="") as f:
        content = f.read()
    eol = "\r\n" if "\r\n" in content else "\n"
    o = old.replace("\n", eol)
    n = new.replace("\n", eol)
    if n in content:
        print("  [skip] %s -- already patched." % path)
        return
    c = content.count(o)
    if c != 1:
        sys.exit("ERROR: %s -- expected 1 match, found %d. File drifted; aborting." % (path, c))
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content.replace(o, n))
    print("  [ok]   %s patched (EOL=%s)." % (path, repr(eol)))


def main():
    for path, old, new in EDITS:
        apply(path, old, new)
    import py_compile
    py_compile.compile("Archipelago/Generate.py", doraise=True)
    print("Done. Generate.py py_compile OK.")


if __name__ == "__main__":
    main()
