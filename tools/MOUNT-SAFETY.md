# Mount-truncation safety tools

The Cowork sandbox mounts this Windows repo into Linux. Large `Write`/`Edit`/`>`
writes to the mount can **silently truncate mid-file, inject NUL bytes, or
null-pad a shrinking overwrite** -- and the harness `Read` view can show a clean
copy that hides the on-disk damage. Worst case, a truncated file gets committed
and the next agent inherits a broken tree. These two tools make that class of bug
loud instead of silent.

## `tools/check_integrity.py` -- the detector

Cross-platform, zero-dependency. Flags zero-byte files, NUL bytes, trailing NUL
pad, non-UTF-8, missing trailing newline, Python syntax errors (with an "error on
the last line -> likely truncation" tag), and EOF delimiter imbalance for
`.py/.rs/.cs`. Exit 0 = clean, 1 = at least one ERROR (WARNs are advisory unless
`--strict`).

    python tools/check_integrity.py FILE [FILE ...]   # explicit files
    python tools/check_integrity.py --staged          # git-staged text files
    python tools/check_integrity.py --tracked         # all git-tracked text files
    python tools/check_integrity.py --staged --strict # WARNs also fail

Caveat: run it against a **real clone or git blobs**, not sandbox mount paths --
the mount can serve a truncated view and cause a false alarm (that is the bug it
is meant to catch, not a checker error).

## `tools/safe_publish.sh` -- the safe writer (sandbox side)

Publishes a file onto the mount so a truncated result can never land silently:
verifies the source is non-empty and passes `check_integrity`, stages onto the
same filesystem, `cmp`s the staged bytes, then does an **atomic `mv`** (a rename
makes a new inode, which defeats the shrinking null-pad, and rename is one op the
mount allows). Finally it re-checks size + sha256 and prints a receipt.

    tools/safe_publish.sh /tmp/core.py greenfield/eldenring/core.py

Always also confirm the destination with the harness `Read` tool -- bash can serve
a stale mount view even of a just-written file.

## Wiring

**Pre-commit hook (once, cross-platform):**

    git config core.hooksPath tools/hooks

Now every commit runs `check_integrity.py --staged` and blocks a corrupted file.
Bypass with `git commit --no-verify`.

**Linux CI:** `greenfield/ci-linux.sh` runs the INTEGRITY gate first (already
wired).

**Windows CI (`run_ci.ps1`):** add near the top of the gate sequence:

    Write-Host "`n==== INTEGRITY (mount-truncation gate)"
    python tools\check_integrity.py --tracked
    if ($LASTEXITCODE -ne 0) { $script:AnyFail = $true; Write-Host "  INTEGRITY: FAIL" }
    else { Write-Host "  INTEGRITY: PASS" }

(adapt `$script:AnyFail` to whatever failure flag run_ci.ps1 already uses.)
