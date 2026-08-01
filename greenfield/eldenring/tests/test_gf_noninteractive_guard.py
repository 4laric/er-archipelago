"""Every real `Generate.py` invoker closes stdin -- #193.

Stock `Generate.py` ends with `input("Press enter to close.")`. On a CRASH that call blocks on
inherited stdin, so the failure reports as a HANG: no traceback, no exit code, just a harness that
never returns (2026-07-24). A crash costs an hour; a crash wearing a hang's clothes costs an
afternoon and gets misfiled as flakiness.

Two guards, and the order matters:

  * `AP_NONINTERACTIVE=1` is a LOCAL patch to our AP checkout. An AP re-checkout drops it silently,
    which makes it the half that rots (greenfield/ci-linux.sh:127).
  * Closing stdin (`</dev/null`, `stdin=subprocess.DEVNULL`) is stock behaviour and cannot rot --
    `input()` on a closed stdin raises instantly. This is the half that actually holds.

So this gate requires the STDIN half and merely notes the env half.

🛑 WHY IT SCANS FOR INVOKERS RATHER THAN TAKING A LIST. #193 was found by hand-auditing 12 files
that mention `Generate.py` and finding that only 5 invoke it and 4 were guarded. A hardcoded list of
5 would go stale the first time someone adds a sixth, and would do so silently -- the exact
"absence is invisible" failure the repo keeps paying for. Derive the set.
"""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:  # direct/unittest fallback
    sys.path.insert(0, HERE)
    from _util import find_repo_root, REPO_ONLY_REASON

_ROOT = find_repo_root(HERE)

# Directories that can hold a harness. Scanned recursively; `.git` and caches excluded.
_SCAN_DIRS = ("tools", "greenfield")
_SCAN_ROOT_FILES = ("build.ps1", "gen_fuzz.ps1", "gen_sweep.ps1", "run_ci.ps1", "pregen.py")
_EXT = (".py", ".ps1", ".sh")

# INVOKING Generate.py, as opposed to mentioning it in prose. Matched PER LINE, and the horizontal
# whitespace is `[ \t]`, NOT `\s`.
#
# 🛑 This detector already lied once, exactly the way CONTRIBUTING rule 8 warns a guard will. The
# first version used `\s` and scanned the whole file, so `#!/usr/bin/env python3` on line 1 joined
# across the newline to the docstring on line 2 -- "Run BEFORE Generate.py" -- and `pregen.py`, which
# only MENTIONS Generate.py, was reported as an unguarded invoker. A guard that manufactures
# offenders is as useless as one that misses them, and this one did it while looking authoritative.
_INVOKE = re.compile(
    r"""runpy\.run_path\([ \t]*['"]Generate\.py"""
    r"""|['"]Generate\.py['"][ \t]*,"""
    r"""|(?<![\w/])(?:python|python3|\$PY|"\$PY"|\$\{PY\}|sys\.executable)[ \t][^\n]{0,80}?Generate\.py"""
    r"""|(?<![\w/-])Generate\.py[ \t]+--"""
)
# The two guards. `AP_NONINTERACTIVE` is the repo's established convention; closing stdin is the
# half that survives an AP re-checkout (greenfield/ci-linux.sh:127).
_ENV_GUARD = re.compile(r"AP_NONINTERACTIVE")
# `< NUL` is cmd.exe's `</dev/null` and the PowerShell harnesses use it -- omitting it under-credited
# two files that were already correct, which is the same detector-lies failure in the other direction.
_STDIN_CLOSED = re.compile(r"</dev/null|<[ \t]*NUL\b|stdin[ \t]*=[ \t]*subprocess\.DEVNULL"
                           r"|stdin[ \t]*=[ \t]*DEVNULL|-RedirectStandardInput", re.IGNORECASE)


def _invoking_lines(text):
    """Lines that actually invoke Generate.py. Line-scoped so a shebang cannot bleed into prose."""
    return [ln for ln in text.splitlines() if _INVOKE.search(ln)]


def _candidate_files(root):
    for rel in _SCAN_ROOT_FILES:
        p = os.path.join(root, rel)
        if os.path.isfile(p):
            yield p
    for d in _SCAN_DIRS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(root, d)):
            dirnames[:] = [x for x in dirnames
                           if x not in ("__pycache__", ".git", "node_modules", "_ap")]
            for name in sorted(filenames):
                if name.endswith(_EXT):
                    yield os.path.join(dirpath, name)


@unittest.skipUnless(_ROOT is not None, REPO_ONLY_REASON)
class GenerateInvokersAreNonInteractive(unittest.TestCase):

    def _invokers(self):
        """-> (files_scanned, {relpath: {"env": bool, "stdin": bool}}).

        🛑 Returns FLAGS, never file text. The first version mapped path -> full source, so a
        failing `assertIn` printed the whole container: a 144,000-character failure message that
        buries the one path you need. A gate whose red output cannot be read in CI is barely a
        gate."""
        found = {}
        scanned = 0
        for path in _candidate_files(_ROOT):
            try:
                with open(path, encoding="utf-8") as f:
                    text = f.read()
            except (OSError, UnicodeDecodeError):
                continue
            scanned += 1
            if _invoking_lines(text):
                rel = os.path.relpath(path, _ROOT).replace("\\", "/")
                found[rel] = {"env": bool(_ENV_GUARD.search(text)),
                              "stdin": bool(_STDIN_CLOSED.search(text))}
        return scanned, found

    def test_the_sweep_actually_sees_the_tree(self):
        """Rule 2: an empty result is a FAILURE, not a clean run. A regex that silently stops
        matching would report a green 'all invokers guarded' over zero invokers."""
        scanned, found = self._invokers()
        self.assertGreater(scanned, 30, f"only {scanned} harness files scanned")
        self.assertGreaterEqual(
            len(found), 4,
            "the invoker sweep found %d files; #193 audited FIVE real invokers. A drop means the "
            "detector broke, not that the invokers went away: %s" % (len(found), sorted(found)))

    def test_every_generate_invoker_is_guarded(self):
        """HARD gate: the repo's convention is `AP_NONINTERACTIVE`, and closing stdin also counts.
        A file with NEITHER is #193's bug."""
        _, found = self._invokers()
        unguarded = sorted(p for p, g in found.items()
                           if not (g["env"] or g["stdin"]))
        self.assertEqual(
            unguarded, [],
            "these invoke Generate.py with no non-interactive guard, so a CRASHED gen parks on "
            "input('Press enter to close.') and reports as a hang (#193). Set AP_NONINTERACTIVE=1 "
            "and close stdin (`stdin=subprocess.DEVNULL`, or `</dev/null` in shell):\n  "
            + "\n  ".join(unguarded))

    def test_every_invoker_closes_stdin_not_just_the_env(self):
        """The half that CANNOT rot. `AP_NONINTERACTIVE` is a local patch to our AP checkout and a
        re-checkout drops it silently; `input()` on a closed stdin raises whatever AP does.

        This started as a soft floor (4 of 9 invokers were env-only) and is a HARD gate because the
        gap turned out to be two `.ps1` files whose own siblings already did it right --
        `gen_fuzz.ps1` and `gen_sweep.ps1` pass `< NUL`, `build.ps1` and `gen-greenfield.ps1` did
        not. A ratchet you can close today should not ship as a number to be justified later.
        """
        _, found = self._invokers()
        env_only = sorted(p for p, g in found.items() if not g["stdin"])
        self.assertEqual(
            env_only, [],
            "these invoke Generate.py relying on AP_NONINTERACTIVE alone, which an AP re-checkout "
            "drops. Add `< NUL` (cmd/PowerShell), `</dev/null` (sh) or `stdin=subprocess.DEVNULL`:"
            "\n  " + "\n  ".join(env_only))

    def test_the_motivating_case_is_covered_end_to_end(self):
        """Rule 11: the case that motivated the gate is the acceptance test, asserted BY NAME
        through the finished pipeline -- not the detector in isolation, not the fix in isolation.
        `gf_zip_gen_smoke.py` is the file #193 was filed about; it must be seen as an invoker AND
        come out guarded."""
        _, found = self._invokers()
        self.assertIn(
            "tools/gf_zip_gen_smoke.py", found,
            "the invoker detector no longer recognises the file #193 was about -- the gate would "
            "pass while blind to its own motivating case. Detected invokers: %s"
            % sorted(found))
        self.assertTrue(
            found["tools/gf_zip_gen_smoke.py"]["stdin"],
            "the file #193 was filed about is detected but does not close stdin")


if __name__ == "__main__":
    unittest.main()
