#!/usr/bin/env python3
"""Make `build.ps1 -Bake` close the baker by itself instead of waiting on a click.

On a normal -Bake, build.ps1 launches the randomizer GUI with `/gui autoconnect`
(NOT headless). ArchipelagoForm pops MessageBox.Show("Archipelago config loaded
successfully!") on success -- you must click OK before the window closes and the
script continues. The exe already supports a `headless` arg (used by -LoopTest):
it skips that dialog, sets the process exit code (0 ok / 1 fail), and Close()s the
form automatically -- on success AND on failure. So this is a build.ps1-only fix;
no randomizer rebuild needed.

Two edits:
  1. add "headless" to the -Bake launch args.
  2. capture $LASTEXITCODE and throw on a failed bake, so a headless auto-close on
     failure can't silently fall through to -Deploy (the bake error is in
     ap_bake_*.log / ap_error.txt under the randomizer dir).

Idempotent. Run from the repo root:  python patch_build_bake_headless.py
"""
import io, os, sys

TARGET = "build.ps1"

EDITS = [
    ('        $bakeArgs = @("/gui", "autoconnect"); if ($Enemies) { $bakeArgs += "enemies" }',
     '        $bakeArgs = @("/gui", "autoconnect", "headless"); if ($Enemies) { $bakeArgs += "enemies" }'),

    ('        & $RandoExe @bakeArgs | Out-Default   # blocks until the randomizer window closes\n'
     '    } finally { Pop-Location }',
     '        & $RandoExe @bakeArgs | Out-Default   # window auto-closes on completion (headless); no click needed\n'
     '        $bakeExit = $LASTEXITCODE\n'
     '    } finally { Pop-Location }\n'
     '    if ($bakeExit -ne 0) { throw ("bake FAILED (exit {0}) -- see ap_bake_*.log / ap_error.txt in {1}" -f $bakeExit, $RandoDir) }'),
]


def main():
    if not os.path.exists(TARGET):
        sys.exit("ERROR: %s not found -- run from the repo root." % TARGET)
    with io.open(TARGET, "r", encoding="utf-8", newline="") as f:
        content = f.read()
    eol = "\r\n" if "\r\n" in content else "\n"

    changed = False
    for old, new in EDITS:
        o = old.replace("\n", eol)
        n = new.replace("\n", eol)
        if n in content:
            print("  [skip] already patched: %s" % old.splitlines()[0].strip())
            continue
        c = content.count(o)
        if c != 1:
            sys.exit("ERROR: expected 1 match, found %d for:\n%s" % (c, old))
        content = content.replace(o, n)
        changed = True
        print("  [ok]   patched: %s" % old.splitlines()[0].strip())

    if changed:
        with io.open(TARGET, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        print("Wrote %s (EOL=%s)." % (TARGET, repr(eol)))
    else:
        print("No changes.")


if __name__ == "__main__":
    main()
