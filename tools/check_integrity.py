#!/usr/bin/env python3
"""
check_integrity.py -- truncation / corruption gate for mounted-FS writes.

Catches the "mount truncation" failure class (silent mid-file cut, NUL-byte
injection, zero-byte redirect, shrinking null-pad, committed truncation) BEFORE
it reaches `git add`, CI, or HEAD -- where the next agent inherits a broken tree.

Usage:
    python3 tools/check_integrity.py FILE [FILE ...]   # explicit files
    python3 tools/check_integrity.py --staged          # git-staged text files
    python3 tools/check_integrity.py --tracked         # all git-tracked text files
    python3 tools/check_integrity.py --staged --strict # warnings also fail

Exit 0 = clean, 1 = >=1 ERROR (or any WARN under --strict), 2 = bad invocation.

Pre-commit hook:  python3 tools/check_integrity.py --staged || exit 1
CI step:          python3 tools/check_integrity.py --tracked
"""
import os
import subprocess
import sys
import tempfile

TEXT_EXTS = {
    ".py", ".rs", ".ps1", ".psm1", ".cs", ".toml", ".yaml", ".yml",
    ".json", ".md", ".sh", ".txt", ".cfg", ".ini", ".csv", ".tsv",
}
CODE_EXTS = {".py", ".rs", ".ps1", ".psm1", ".cs", ".sh"}
# delimiter-balance heuristic only where the string/comment stripper is sound
# (PowerShell here-strings and shell `[ test ]` / glob brackets cause false
# positives; those languages fail loudly at parse/run time anyway).
BALANCE_EXTS = {".py", ".rs", ".cs"}

RED = "\033[31m"
YEL = "\033[33m"
GRN = "\033[32m"
OFF = "\033[0m"
if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
    RED = YEL = GRN = OFF = ""


def ext(path):
    return os.path.splitext(path)[1].lower()


def git_files(mode):
    if mode == "staged":
        cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"]
    else:
        cmd = ["git", "ls-files"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        sys.stderr.write("check_integrity: git failed: " + out.stderr + "\n")
        sys.exit(2)
    return [f for f in out.stdout.splitlines() if f.strip()]


def strip_noise(text, language):
    """Best-effort removal of strings/comments so delimiter counts mean something.
    Heuristic only -- feeds a WARN, never an ERROR."""
    res = []
    i, n = 0, len(text)
    line_comment = "#" if language in ("py", "ps1", "sh") else "//"
    dq_only = language in ("rs", "cs")  # ' is char/lifetime in these -> don't treat as string
    while i < n:
        c = text[i]
        two = text[i:i + 2]
        if two == "/*" and language in ("rs", "cs"):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if text.startswith(line_comment, i):
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == '"' or (c == "'" and not dq_only):
            q = c
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == q:
                    i += 1
                    break
                i += 1
            continue
        res.append(c)
        i += 1
    return "".join(res)


def delimiter_delta(text, language):
    stripped = strip_noise(text, language)
    pairs = {")": "(", "]": "[", "}": "{"}
    opens = {"(": 0, "[": 0, "{": 0}
    for ch in stripped:
        if ch in opens:
            opens[ch] += 1
        elif ch in pairs:
            opens[pairs[ch]] -= 1
    return opens  # nonzero value => imbalance


# Files that are legitimately EMPTY. An empty package marker is normal Python, not a zeroed write --
# flagging it made `--tracked` noisy, and a noisy gate is a gate people switch off.
EMPTY_OK = ("__init__.py", ".gitkeep", ".keep")


def check_one(path):
    if os.path.basename(path) in EMPTY_OK and os.path.getsize(path) == 0:
        return [], []
    errs, warns = [], []
    if not os.path.exists(path):
        return errs, warns  # deleted/renamed staged entry -- nothing on disk
    if ext(path) not in TEXT_EXTS:
        return errs, warns
    try:
        raw = open(path, "rb").read()
    except OSError as e:
        errs.append("cannot read: %s" % e)
        return errs, warns

    if len(raw) == 0:
        errs.append("ZERO BYTES (empty file -- classic `>`-redirect zeroing)")
        return errs, warns

    nul = raw.find(b"\x00")
    if nul != -1:
        errs.append("NUL byte at offset %d (mount write injected nulls)" % nul)

    # trailing null-pad from a shrinking overwrite
    if raw.endswith(b"\x00"):
        errs.append("file ends in NUL padding (shrinking-overwrite null-pad)")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        errs.append("not valid UTF-8: %s" % e)
        return errs, warns

    if not text.endswith("\n"):
        warns.append("no trailing newline (often a truncated tail)")

    lang = ext(path).lstrip(".")
    lang = {"psm1": "ps1"}.get(lang, lang)

    if ext(path) == ".py":
        try:
            compile(text, path, "exec")  # in-memory; writes no .pyc
        except SyntaxError as e:
            lineno = e.lineno or 0
            nlines = text.count("\n") + 1
            tag = "SYNTAX ERROR"
            if lineno and lineno >= nlines - 1:
                tag = "SYNTAX ERROR ON LAST LINE -> LIKELY TRUNCATION"
            errs.append("%s: %s (line %d)" % (tag, e.msg, lineno))
        except ValueError as e:
            errs.append("SYNTAX ERROR: %s" % e)

    if ext(path) in BALANCE_EXTS:
        delta = delimiter_delta(text, lang)
        bad = {k: v for k, v in delta.items() if v != 0}
        if bad:
            warns.append("delimiter imbalance %s (EOF imbalance often = truncation)" % bad)

    return errs, warns



def looks_binary(data):
    """git's own heuristic: a NUL in the first 8k => binary. Cheap and matches what git does when it
    decides to print 'Binary files differ'."""
    return b"\x00" in data[:8000] and not data[:8000].decode("utf-8", "ignore").isprintable() \
        or _nontext_ratio(data[:8000]) > 0.30


def _nontext_ratio(chunk):
    if not chunk:
        return 0.0
    text = bytes(range(32, 127)) + b"\n\r\t\f\b"
    return sum(1 for b in chunk if b not in text) / len(chunk)


def blob_bytes(path):
    """The file's content in HEAD, or None if untracked/new."""
    r = subprocess.run(["git", "cat-file", "-p", "HEAD:%s" % path],
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return r.stdout if r.returncode == 0 else None


def check_truncated_vs_head(path):
    """Detect the MOUNT-TRUNCATION signature: the file on disk is a strict PREFIX of what git has,
    and shorter. That is what a cut-off write looks like, and it is almost never what an edit looks
    like -- a real edit changes bytes, it does not just stop early. (A file that legitimately shrank
    -- deleted a trailing block -- would have to coincidentally be an exact prefix to false-positive,
    which is rare enough to be worth the signal.)

    This is the check that was MISSING on 2026-07-11: writes through the Windows mount silently
    truncated gen_data.py (-553 b), package_release.ps1 (-23 b), tools/check_integrity.py (tail
    mangled) and even .git/HEAD (NUL-padded). None of it was ever committed, so the pre-commit hook
    never got a say -- the damage lived in the WORKING TREE, between commits, where nothing looked.
    """
    try:
        disk = open(path, "rb").read()
    except OSError:
        return [], []
    blob = blob_bytes(path)
    if blob is None:
        return [], []
    if len(disk) < len(blob) and blob.startswith(disk):
        return (["TRUNCATED vs HEAD: %d bytes on disk, %d in git, and the on-disk content is an "
                 "exact PREFIX of git's -- this is a cut-off write, not an edit. "
                 "Restore with: git checkout -- %s" % (len(disk), len(blob), path)], [])
    # NUL bytes only mean corruption in a TEXT file. Decide binary-ness the way git does -- by looking
    # at the bytes -- not by an extension allowlist, which I got wrong first time round (.xlsx is a zip
    # and is legitimately full of NULs).
    if b"\x00" in disk and not looks_binary(disk):
        return (["NUL BYTES in a text file (%d) -- mount write-truncation signature" % disk.count(0)], [])
    return [], []


def self_check():
    """The gate must not be the casualty. On 2026-07-11 check_integrity.py was ITSELF truncated --
    it could not parse, so it could not run, so it could not report that it had been eaten. Verify
    our own source against HEAD before trusting any result we produce."""
    me = os.path.relpath(os.path.abspath(__file__), os.getcwd()).replace(os.sep, "/")
    errs, _ = check_truncated_vs_head(me)
    return errs


def main(argv):
    args = argv[1:]
    strict = "--strict" in args
    args = [a for a in args if a != "--strict"]

    if "--staged" in args:
        files = git_files("staged")
    elif "--tracked" in args:
        files = git_files("tracked")
    elif args:
        files = args
    else:
        sys.stderr.write(__doc__)
        return 2

    n_err = n_warn = 0

    # The gate checks itself FIRST -- a truncated checker cannot be trusted to report anything.
    for m in self_check():
        print("%sERROR%s %s: %s" % (RED, OFF, "tools/check_integrity.py (SELF)", m))
        n_err += 1

    for f in files:
        errs, warns = check_one(f)
        e2, w2 = check_truncated_vs_head(f)      # cut-off-write detector (vs HEAD)
        errs = list(errs) + e2
        warns = list(warns) + w2
        for m in errs:
            print("%sERROR%s %s: %s" % (RED, OFF, f, m))
            n_err += 1
        for m in warns:
            print("%sWARN%s  %s: %s" % (YEL, OFF, f, m))
            n_warn += 1

    checked = len(files)
    if n_err == 0 and n_warn == 0:
        print("%sOK%s check_integrity: %d file(s) clean" % (GRN, OFF, checked))
    else:
        print("check_integrity: %d file(s), %d error(s), %d warning(s)"
              % (checked, n_err, n_warn))
    if n_err or (strict and n_warn):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
