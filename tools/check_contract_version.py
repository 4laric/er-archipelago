#!/usr/bin/env python3
"""
check_contract_version.py -- the contract-bump gate (CONTRIBUTING rule 15).

THE RULE: if the CONTRACT changes, the RELEASE version changes with it.

CONTRACT_HASH is derived from the contract keys, so it moves on its own the moment a
key is added, removed, reshaped, or flips required-ness. APWORLD_VERSION does not move
on its own -- somebody has to remember. This gate is the thing that remembers.

MOTIVATING CASE (rule 11), and it is measured, not hypothetical. Loading contract.py at
every tag in this repo shows that `APWORLD_VERSION = "0.2.0"` shipped FIVE distinct
contract shapes:

    v0.2                36013f63
    v0.2.1 - v0.2.3     03c58b40
    v0.2.4 - v0.2.7     54514b10
    v0.2.8 - v0.2.9     84dd6ab8
    v0.2.10 - v0.2.11   b3739fdf

The handshake in core.rs keys on the hash, so those five are mutually incompatible --
and every one of them introduces itself to the log, and to a bug report, as
"apworld/0.2.0". The version string could not identify the build. That is the whole
defect: not that a mismatch goes undetected (it does not), but that once detected
nobody can say WHICH 0.2.0 the player had.

Reproduce that table yourself -- it is a derivation, not folklore:

    python3 tools/check_contract_version.py --derive-history

WHAT THIS GATE DOES *NOT* CATCH -- read this before trusting it (rule 10):

  * OPTIONS_SUBKEYS is deliberately NOT folded into CONTRACT_HASH (contract.py says why:
    an absent key parses false on an older client, which is the off default, so option
    subkeys are allowed to be younger than the clients that read them). A change confined
    to OPTIONS_SUBKEYS therefore moves NEITHER the hash NOR this gate. That is a real
    blind spot, inherited on purpose. Widening the hash to cover it would invalidate the
    handshake of every released client, so it is a design decision, not a drive-by fix.
  * It cannot see two builds cut from the SAME commit, or a DLL packaged against a
    different client revision than the gitlink pins. The gitlink half is CI's
    `generators` job (AGENTS §7); this gate is the world half only.

Deliberately AP-FREE: contract.py has no Archipelago imports, so it is loaded directly
by path via importlib and nothing else is needed. Runs in the cheap CI job, in the
Linux sandbox, and on a box with no Archipelago checkout.

Usage:
    python3 tools/check_contract_version.py             # gate the working tree
    python3 tools/check_contract_version.py --check     # identical (alias)
    python3 tools/check_contract_version.py --derive-history   # recompute the ledger from tags (needs network)

Exit 0 = clean, 1 = >=1 ERROR, 2 = bad invocation / cannot find what it must read.

CI step:  python3 tools/check_contract_version.py
"""
import importlib.util
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACT = os.path.join(REPO, "greenfield", "eldenring", "contract.py")
NOTES_DIR = "release"
LEDGER = os.path.join(REPO, NOTES_DIR, "CONTRACT-VERSIONS.tsv")
LEDGER_REL = NOTES_DIR + "/CONTRACT-VERSIONS.tsv"

RED = "\033[31m"
GRN = "\033[32m"
OFF = "\033[0m"
if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
    RED = GRN = OFF = ""


def load_contract():
    """Load contract.py by PATH, not by import. It is AP-free, so this works anywhere;
    importing `greenfield.eldenring.contract` would drag the world in behind it."""
    if not os.path.isfile(CONTRACT):
        sys.stderr.write("check_contract_version: cannot find %s\n" % CONTRACT)
        sys.exit(2)
    spec = importlib.util.spec_from_file_location("_er_contract_gate", CONTRACT)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:                                  # noqa: BLE001
        # Rule 1: a derivation that cannot answer must FAIL, not answer.
        sys.stderr.write(
            "check_contract_version: contract.py did not load: %s: %s\n"
            "  This gate cannot compute a hash it cannot execute. Fix the import, do not\n"
            "  let the gate fall back to a textual guess.\n" % (type(exc).__name__, exc))
        sys.exit(2)
    for attr in ("APWORLD_VERSION", "CONTRACT_HASH"):
        if not hasattr(mod, attr):
            sys.stderr.write(
                "check_contract_version: contract.py has no %s -- it was renamed or moved.\n"
                "  Fix this gate; do not let it guess.\n" % attr)
            sys.exit(2)
    return mod.APWORLD_VERSION, mod.CONTRACT_HASH[:8]


def read_ledger():
    """version -> (hash, note), preserving file order. Comments and blanks skipped, and
    COUNTED -- rule 4, a filter with no tally is a lie."""
    if not os.path.isfile(LEDGER):
        sys.stderr.write(
            "check_contract_version: cannot find %s\n"
            "  That file IS the gate's memory. Restore it from git rather than\n"
            "  regenerating it -- see --derive-history.\n" % LEDGER)
        sys.exit(2)
    rows, skipped, malformed = {}, 0, []
    order = []
    with open(LEDGER, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            s = line.rstrip("\n")
            if not s.strip() or s.lstrip().startswith("#"):
                skipped += 1
                continue
            parts = s.split("\t")
            if len(parts) < 2 or not re.match(r"^\d+\.\d+", parts[0].strip()):
                malformed.append((n, s[:60]))
                continue
            ver, h = parts[0].strip(), parts[1].strip()
            note = parts[2].strip() if len(parts) > 2 else ""
            if ver in rows:
                malformed.append((n, "DUPLICATE version %s" % ver))
                continue
            rows[ver] = (h, note)
            order.append(ver)
    return rows, order, skipped, malformed


def main(argv):
    args = [a for a in argv[1:] if a != "--check"]
    if args == ["--derive-history"]:
        return derive_history()
    if args:
        sys.stderr.write(__doc__)
        return 2

    version, chash = load_contract()
    rows, order, skipped, malformed = read_ledger()
    print("check_contract_version: APWORLD_VERSION = %s  CONTRACT_HASH = %s" % (version, chash))
    print("  ledger: %d version rows, %d comment/blank lines skipped" % (len(rows), skipped))

    errs = []
    for n, what in malformed:
        errs.append("%s line %d is malformed and was NOT read: %s\n"
                    "    Every non-comment line must be `version<TAB>hash8<TAB>note`."
                    % (LEDGER_REL, n, what))

    if version not in rows:
        errs.append(
            "APWORLD_VERSION is %s and %s has NO ROW for it.\n"
            "    ADD, as the last line:\n"
            "        %s\t%s\t<what this version is>\n"
            "    A new version needs a new row in the same commit as the bump -- the ledger\n"
            "    is what makes `apworld/%s` in a bug report mean exactly one contract shape."
            % (version, LEDGER_REL, version, chash, version))
    else:
        want, note = rows[version]
        if want != chash:
            errs.append(
                "THE CONTRACT MOVED AND THE VERSION DID NOT.\n"
                "        APWORLD_VERSION   %s\n"
                "        CONTRACT_HASH     %s   (computed from contract.py right now)\n"
                "        ledger says       %s   (%s)\n"
                "\n"
                "    You changed a contract key -- added, removed, reshaped, or flipped\n"
                "    required-ness -- under a version number that has already been used for a\n"
                "    DIFFERENT shape. Two builds would now both introduce themselves as\n"
                "    apworld/%s and nobody could tell them apart from a log.\n"
                "\n"
                "    FIX (one of these, in THIS commit):\n"
                "      1. Bump APWORLD_VERSION in greenfield/eldenring/contract.py, add a row\n"
                "         `<new version>\t%s\t<why>` to %s, and land the\n"
                "         CHANGELOG + blurb with it (rule 14, check_release_notes.py).\n"
                "         The client half bumps in lockstep -- crates/eldenring-archipelago/Cargo.toml\n"
                "         and the regenerated contract_gen.rs -- or the client's own\n"
                "         client_version_matches_the_apworld_it_was_built_against test reds.\n"
                "      2. Or revert the contract change, if the move was accidental.\n"
                "\n"
                "    🛑 NOT a fix: editing the %s row in the ledger to say %s.\n"
                "    That row is a record of what SHIPPED. Rewriting it does not make the two\n"
                "    builds compatible, it just removes the only evidence that they differ."
                % (version, chash, want, note or "no note", version,
                   chash, LEDGER_REL, version, chash))

    for m in errs:
        print("%sERROR%s %s" % (RED, OFF, m))
    if errs:
        print("check_contract_version: %d error(s). If the contract changes, the release\n"
              "version changes with it (CONTRIBUTING rule 15)." % len(errs))
        return 1
    print("%sOK%s check_contract_version: v%s owns contract %s, and the ledger agrees."
          % (GRN, OFF, version, chash))
    return 0


def derive_history():
    """Recompute the whole ledger from the git tags. Network + git required; this is the
    command the ledger header cites, so that its rows are reproducible rather than
    folklore (rule 10)."""
    import subprocess
    import tempfile
    raw = "https://raw.githubusercontent.com/4laric/er-archipelago/%s/greenfield/eldenring/contract.py"
    try:
        out = subprocess.check_output(["git", "ls-remote", "--tags", "--refs", "origin"],
                                      cwd=REPO, text=True)
    except Exception as exc:                                  # noqa: BLE001
        sys.stderr.write("--derive-history needs git + network: %s\n" % exc)
        return 2
    tags = sorted(l.split("refs/tags/")[-1] for l in out.splitlines() if "refs/tags/" in l)
    print("tag\tAPWORLD_VERSION\tCONTRACT_HASH")
    seen = {}
    with tempfile.TemporaryDirectory() as td:
        for t in tags:
            p = os.path.join(td, "c.py")
            if subprocess.call(["curl", "-sfo", p, raw % t]) != 0 or os.path.getsize(p) < 100:
                print("%s\t-\t(no contract.py at this tag)" % t)
                continue
            spec = importlib.util.spec_from_file_location("_h", p)
            m = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(m)
            except Exception as exc:                          # noqa: BLE001
                print("%s\t-\tLOAD FAILED: %s" % (t, type(exc).__name__))
                continue
            print("%s\t%s\t%s" % (t, m.APWORLD_VERSION, m.CONTRACT_HASH[:8]))
            seen.setdefault(m.APWORLD_VERSION, set()).add(m.CONTRACT_HASH[:8])
    print()
    for v, hs in sorted(seen.items()):
        if len(hs) > 1:
            print("%s⚠ VERSION %s NAMES %d DISTINCT CONTRACTS: %s%s"
                  % (RED, v, len(hs), ", ".join(sorted(hs)), OFF))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
