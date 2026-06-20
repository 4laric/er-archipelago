#!/usr/bin/env python3
"""Patch dlcdiag.py so the "GROUND TRUTH" options block is tied to THIS gen's seed.

Bug: _emit_options() picked the newest AP_*.zip by mtime and printed its spoiler as
"GROUND TRUTH" for the current run. But AP names the zip with the seed_NAME
(AP_55769....zip) while the spoiler header carries the real `Seed: <num>`, so the
filename never matches the run. On a FAILED gen (no new zip) the newest zip on disk
belongs to a PRIOR run -- so the diag reported one seed on its `seed:` line and a
DIFFERENT seed's options under "GROUND TRUTH" (the "two versions of ground truth").

Fix: look INSIDE each zip newest-first, match the spoiler `Seed:` header to the run
seed parsed from the log, and only print that one. If none matches, say so plainly
instead of printing a stale prior run.

Idempotent: re-running after a successful patch is a no-op (anchor already gone).
Run from the repo root:  python patch_dlcdiag_seed_match.py
"""
import io, os, sys

TARGET = "dlcdiag.py"

OLD = '''    zips = sorted(glob.glob(os.path.join(outdir, "AP_*.zip")), key=os.path.getmtime)
    out("")
    if not zips:
        out("OPTIONS (resolved): (no AP_*.zip in Archipelago/output)")
    else:
        z = zips[-1]
        try:
            zf = zipfile.ZipFile(z)
            spn = [n for n in zf.namelist() if n.endswith("_Spoiler.txt")]
            sp = zf.read(spn[0]).decode("utf-8", "replace").splitlines() if spn else []
        except Exception as e:
            sp = []
            out("OPTIONS (resolved): (spoiler read failed: %s)" % e)
        if sp:
            out("OPTIONS (resolved, from %s -- GROUND TRUTH, not a yaml):" % os.path.basename(z))
            blanks = 0; started = False
            for ln in sp:
                if not ln.strip():
                    blanks += 1
                    if started:
                        break          # end of the settings block
                    continue
                if blanks >= 1:        # past the "Archipelago Version ... Seed:" header line
                    started = True
                    out("  " + ln.rstrip())'''

NEW = '''    # Tie the spoiler we read to THIS gen's seed. AP names the zip with the seed
    # NAME (AP_55769....zip) while the spoiler header carries the real Seed: <num>,
    # so the filename can't be matched -- we must look INSIDE each zip. On a FAILED
    # gen (no new zip) the newest zip on disk is a PRIOR run; printing it as
    # "GROUND TRUTH" was the "two versions of ground truth" bug.
    run_seed = first(r"Seed[: ]+(\\d+)")
    zips = sorted(glob.glob(os.path.join(outdir, "AP_*.zip")), key=os.path.getmtime, reverse=True)
    out("")
    z = None; sp = []
    for cand in zips:
        try:
            zf = zipfile.ZipFile(cand)
            spn = [n for n in zf.namelist() if n.endswith("_Spoiler.txt")]
            if not spn:
                continue
            body = zf.read(spn[0]).decode("utf-8", "replace").splitlines()
        except Exception as e:
            out("OPTIONS (resolved): (spoiler read failed for %s: %s)" % (os.path.basename(cand), e))
            continue
        m = re.search(r"Seed:\\s*(\\d+)", body[0] if body else "")
        if run_seed is not None and m and m.group(1) == run_seed:
            z = cand; sp = body; break
    if not zips:
        out("OPTIONS (resolved): (no AP_*.zip in Archipelago/output)")
    elif z is None:
        out("OPTIONS (resolved): (no spoiler matches this run's seed %s -- "
            "gen produced no new zip; newest on disk %s is a PRIOR run)"
            % (run_seed, os.path.basename(zips[0])))
    if sp:
        out("OPTIONS (resolved, from %s, seed %s -- GROUND TRUTH, not a yaml):"
            % (os.path.basename(z), run_seed))
        blanks = 0; started = False
        for ln in sp:
            if not ln.strip():
                blanks += 1
                if started:
                    break          # end of the settings block
                continue
            if blanks >= 1:        # past the "Archipelago Version ... Seed:" header line
                started = True
                out("  " + ln.rstrip())'''


def main():
    if not os.path.exists(TARGET):
        sys.exit("ERROR: %s not found -- run from the repo root." % TARGET)

    with io.open(TARGET, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    eol = "\r\n" if "\r\n" in content else "\n"
    old = OLD.replace("\n", eol)
    new = NEW.replace("\n", eol)

    if new in content:
        print("Already patched -- no change.")
        return
    n = content.count(old)
    if n != 1:
        sys.exit("ERROR: expected exactly 1 match of the target block, found %d. "
                 "dlcdiag.py may have drifted; not touching it." % n)

    patched = content.replace(old, new)
    with io.open(TARGET, "w", encoding="utf-8", newline="") as f:
        f.write(patched)

    # sanity: file still compiles
    import py_compile
    py_compile.compile(TARGET, doraise=True)
    print("Patched %s (EOL=%s). py_compile OK." % (TARGET, repr(eol)))


if __name__ == "__main__":
    main()
