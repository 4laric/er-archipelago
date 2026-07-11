#!/usr/bin/env python3
"""
fuzz_gf.py -- greenfield yaml-fuzz orchestrator + scorer for the CONTRIBUTING
headline gate: "any yaml option combo -> clean gen OR graceful reject
(OptionError); never a FillError / traceback / hang".

Pipeline:
  1. generate a batch of random greenfield yamls via gen_fuzz_gf_yamls (which
     reuses the game-agnostic samplers in ../gen_fuzz_yamls.py).
  2. for EACH yaml, run AP Generate.py single-player (AP_NONINTERACTIVE=1) with
     that one yaml in a temp player dir and a temp --outputpath, then classify
     from exit code + captured output:
        SUCCESS   exit 0 (a seed generated)                     -> PASS
        REJECT    output contains an OptionError (graceful)     -> PASS
        FILLERROR output contains a FillError                   -> FAIL
        HANG      timed out                                     -> FAIL
        CRASH     any other non-zero / traceback (incl. a
                  contract-violation ValueError from the wired
                  fill_slot_data validator)                     -> FAIL
     The AP world autoloader prints many UNRELATED "Could not load world ...
     ModuleNotFoundError: bsdiff4/orjson/requests/zilliandomizer" lines for
     OTHER games -- those are IGNORED; classification keys only on the
     greenfield/Generate outcome (exit code + Fill/Option/greenfield markers).
  3. print ONE summary line and, for any failure, the reproducer yaml + options.
  4. exit 0 if (SUCCESS + REJECT) / N * 100 >= --pass-pct, else exit 1.

CLI (the CI gates call this VERBATIM):
    python greenfield/fuzz_gf.py --count N --pass-pct P \
        [--fuzz-seed S] [--out DIR] [--ap AP_DIR]

Reproducible via --fuzz-seed (passed straight through to the emitter).
"""
from __future__ import annotations
import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
GEN_TIMEOUT = 90  # seconds per Generate.py (batch<=20; keeps CI honest without false HANGs)

# --- classification markers -------------------------------------------------------------------
# OTHER games' autoloader noise to strip before scanning for real Fill/traceback markers, so a
# stray "ModuleNotFoundError: orjson" from some unrelated world never mis-classifies a greenfield
# gen as a CRASH. Matched case-insensitively on the (module-not-found) autoload lines only.
_AUTOLOAD_NOISE = re.compile(
    r"(could not load world|no module named|modulenotfounderror).*"
    r"(bsdiff4|orjson|requests|zilliandomizer|kivy|pymem|"
    r"could not load world)",
    re.IGNORECASE,
)
_OPTIONERROR = re.compile(r"\bOptionError\b")
_FILLERROR = re.compile(r"\bFillError\b")
_TRACEBACK = re.compile(r"Traceback \(most recent call last\)")


def _denoise(text):
    """Drop the unrelated-world autoloader lines so real markers stand alone."""
    return "\n".join(ln for ln in text.splitlines() if not _AUTOLOAD_NOISE.search(ln))


def classify(returncode, out, timed_out):
    """-> (label, is_pass). Order matters: HANG > OptionError(REJECT) > FillError > SUCCESS >
    CRASH. OptionError is checked BEFORE FillError/traceback: a graceful reject may still print a
    Python traceback for the OptionError itself, and that's still a PASS."""
    if timed_out:
        return ("HANG", False)
    clean = _denoise(out)
    if _OPTIONERROR.search(clean):
        return ("REJECT", True)
    if _FILLERROR.search(clean):
        return ("FILLERROR", False)
    if returncode == 0:
        return ("SUCCESS", True)
    # non-zero and not a graceful OptionError: a real crash (contract-violation ValueError from
    # the wired validator lands here too -- that's a genuine greenfield find, not masked).
    return ("CRASH", False)


def run_one(ap_dir, py, yaml_path):
    """Generate a single-player seed from ONE yaml in an isolated temp tree.
    -> (label, is_pass, combined_output)."""
    tmp = tempfile.mkdtemp(prefix="gffuzz_")
    players = os.path.join(tmp, "Players")
    out = os.path.join(tmp, "output")
    os.makedirs(players, exist_ok=True)
    os.makedirs(out, exist_ok=True)
    shutil.copy(yaml_path, os.path.join(players, os.path.basename(yaml_path)))
    env = dict(os.environ)
    env["AP_NONINTERACTIVE"] = "1"
    env["SKIP_REQUIREMENTS_UPDATE"] = "1"
    cmd = [py, "Generate.py", "--player_files_path", players, "--outputpath", out]
    timed_out = False
    try:
        p = subprocess.run(
            cmd, cwd=ap_dir, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=GEN_TIMEOUT,
        )
        rc = p.returncode
        text = p.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired as e:
        timed_out = True
        rc = -1
        text = (e.stdout or b"").decode("utf-8", "replace") if e.stdout else ""
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    label, is_pass = classify(rc, text, timed_out)
    return label, is_pass, text


def read_manifest_options(out_dir, fname):
    """Best-effort: pull the 'options_set' cell for a yaml from manifest.csv."""
    man = os.path.join(out_dir, "manifest.csv")
    if not os.path.isfile(man):
        return ""
    try:
        with open(man, encoding="utf-8") as f:
            for line in f:
                if line.startswith(fname + ","):
                    # last CSV field is the quoted options blob
                    q = line.find('"')
                    return line[q + 1:].rstrip().rstrip('"') if q >= 0 else ""
    except Exception:
        pass
    return ""


def save_failures_to_disk(fail_dir, failures, fuzz_seed):
    """Persist each failure's yaml + the FULL captured Generate.py output (which contains the
    FillError / traceback) to a durable dir, so a reproducer can be recovered long after the console
    scrollback is gone. This is what makes fuzz finds actionable after the fact. Returns the written
    log paths. One SUMMARY.txt indexes the batch."""
    os.makedirs(fail_dir, exist_ok=True)
    written = []
    summary = ["# GF-FUZZ failures  (fuzz-seed %s, %s)"
               % (fuzz_seed, datetime.datetime.now().isoformat(timespec="seconds")), ""]
    for label, yp, opts, text in failures:
        base = os.path.splitext(os.path.basename(yp))[0]
        # copy the exact input yaml so it survives temp cleanup (the yaml alone reproduces the find).
        try:
            shutil.copy(yp, os.path.join(fail_dir, base + ".yaml"))
        except Exception:
            pass
        log_path = os.path.join(fail_dir, base + "." + label + ".log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("label   : " + label + "\n")
            f.write("yaml    : " + yp + "\n")
            f.write("options : " + (opts or "(see yaml)") + "\n")
            f.write("=" * 72 + "\n")
            f.write("FULL captured Generate.py output (stdout+stderr, autoload-noise stripped):\n")
            f.write("=" * 72 + "\n")
            f.write(_denoise(text))
            f.write("\n")
        written.append(log_path)
        summary.append("[%s] %s.yaml -> %s" % (label, base, os.path.basename(log_path)))
        summary.append("    options: " + (opts or "(see yaml)"))
    with open(os.path.join(fail_dir, "SUMMARY.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary) + "\n")
    return written


def main(argv=None):
    ap = argparse.ArgumentParser(description="greenfield yaml-fuzz orchestrator + scorer")
    ap.add_argument("--count", type=int, required=True, help="number of fuzz yamls")
    ap.add_argument("--pass-pct", type=float, required=True,
                    help="min clean %% (SUCCESS+REJECT) to exit 0")
    ap.add_argument("--fuzz-seed", type=int, default=0, help="batch seed (0 = roll + print)")
    ap.add_argument("--out", default="", help="yaml/output dir (default temp)")
    ap.add_argument("--ap", default="", help="Archipelago checkout dir (default <repo>/Archipelago)")
    ap.add_argument("--fail-dir", default="",
                    help="dir for persisted failure artifacts "
                         "(default <repo>/gen-test/gf-fuzz-failures/<timestamp>)")
    ap.add_argument("--no-save-failures", action="store_true",
                    help="do NOT persist failing yaml + full gen output to --fail-dir "
                         "(saving is ON by default so FillError tracebacks are always recoverable)")
    args = ap.parse_args(argv)

    ap_dir = args.ap or os.path.join(REPO_ROOT, "Archipelago")
    if not os.path.isfile(os.path.join(ap_dir, "Generate.py")):
        sys.exit("fuzz_gf: no Generate.py under AP dir " + ap_dir + " (pass --ap)")
    py = sys.executable

    out_dir = args.out or tempfile.mkdtemp(prefix="gf-fuzz-yamls-")
    os.makedirs(out_dir, exist_ok=True)

    # (1) emit the batch. Import the emitter with the AP dir on sys.path so it can read GFOptions.
    sys.path.insert(0, ap_dir)
    sys.path.insert(0, HERE)
    import gen_fuzz_gf_yamls as emit  # noqa: E402
    emit_argv = ["--count", str(args.count), "--out", out_dir, "--density", "0.4"]
    if args.fuzz_seed:
        emit_argv += ["--fuzz-seed", str(args.fuzz_seed)]
    rc = emit.main(emit_argv)
    if rc != 0:
        sys.exit("fuzz_gf: yaml emitter failed")

    yamls = sorted(
        os.path.join(out_dir, f) for f in os.listdir(out_dir)
        if f.endswith(".yaml")
    )
    if not yamls:
        sys.exit("fuzz_gf: no yamls emitted")

    counts = {"SUCCESS": 0, "REJECT": 0, "FILLERROR": 0, "CRASH": 0, "HANG": 0}
    failures = []
    for yp in yamls:
        label, is_pass, text = run_one(ap_dir, py, yp)
        counts[label] = counts.get(label, 0) + 1
        tag = "PASS" if is_pass else "FAIL"
        print("  [" + tag + "] " + label + "  " + os.path.basename(yp), flush=True)
        if not is_pass:
            opts = read_manifest_options(out_dir, os.path.basename(yp))
            failures.append((label, yp, opts, text))

    n = len(yamls)
    clean = counts["SUCCESS"] + counts["REJECT"]
    pct = (clean / n * 100.0) if n else 0.0
    print(
        "GF-FUZZ: %.1f%% clean (%d/%d) | FILLERROR %d CRASH %d HANG %d"
        % (pct, clean, n, counts["FILLERROR"], counts["CRASH"], counts["HANG"])
    )
    print("         SUCCESS %d  REJECT %d  (yamls in %s)" % (counts["SUCCESS"], counts["REJECT"], out_dir))

    # Persist failures to a durable dir by default (recoverable long after this run). The temp trees
    # run_one uses are deleted, and out_dir may be an OS temp dir, so without this the FillError
    # traceback is lost when the console scrollback rolls -- the whole point of this change.
    if failures and not args.no_save_failures:
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        fail_dir = args.fail_dir or os.path.join(REPO_ROOT, "gen-test", "gf-fuzz-failures", ts)
        written = save_failures_to_disk(fail_dir, failures, args.fuzz_seed)
        print("\nGF-FUZZ: saved %d failure artifact(s) to %s" % (len(written), fail_dir))
        print("         (each: <yaml> + <yaml>.<LABEL>.log with the FULL traceback; SUMMARY.txt indexes them)")

    for label, yp, opts, text in failures:
        print("\n---- REPRODUCER (" + label + ") ----")
        print("  yaml   : " + yp)
        print("  options: " + (opts or "(see yaml)"))
        tail = "\n".join(_denoise(text).splitlines()[-25:])
        print("  --- tail of gen output ---")
        for ln in tail.splitlines():
            print("  | " + ln)

    ok = pct >= args.pass_pct
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
