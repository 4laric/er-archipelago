#!/usr/bin/env python3
"""
check_release_notes.py -- the release-notes gate (CONTRIBUTING rule 14).

Every player-visible change lands its CHANGELOG line in the SAME commit, and the
blurb for the open version is drafted as the window fills. This gate is the thing
that checks it, because a bullet list nobody checks is a to-do list (rule 13).

MOTIVATING CASE (rule 11): v0.3.0 shipped 2026-08-01. By 2026-08-02 main carried five
more player-visible fixes -- two of them straight off Nexus bug reports -- with no
v0.3.1 changelog section and no blurb, and no BLURB-v0.3.0.md either: the blurb series
had stopped dead at v0.2.18 and nothing said so. Rebuilding the notes took a walk of
`v0.3.0..main` plus four commit bodies, and the "why it mattered" in those bodies is
not the "why it mattered" a player needs.

Deliberately AP-FREE and import-FREE: APWORLD_VERSION is parsed out of
greenfield/eldenring/contract.py textually, so this runs in the cheap CI job, in the
Linux sandbox, and on a box with no Archipelago checkout.

Usage:
    python3 tools/check_release_notes.py           # gate the current APWORLD_VERSION
    python3 tools/check_release_notes.py --check   # identical (alias; see below)
    python3 tools/check_release_notes.py --version 0.3.1   # gate some other version
    python3 tools/check_release_notes.py --git-range v0.4.2..v0.4.3  # audit a historical window

`--check` is a no-op alias. Every neighbouring repo-level gate is invoked as
`tools/<x>.py --check` (dump_options_metadata, gen_region_locks, build_questline_dag),
where it means "verify, do not write". This tool never writes, so the flag is
redundant -- but a CI step that passes it should not die on argparse.

Exit 0 = clean, 1 = >=1 ERROR, 2 = bad invocation / cannot find what it must read.

CI step:  python3 tools/check_release_notes.py
"""
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACT = os.path.join(REPO, "greenfield", "eldenring", "contract.py")
NOTES_DIR = "release"
CHANGELOG = os.path.join(REPO, NOTES_DIR, "CHANGELOG.md")

# A changelog section shorter than this is a heading with nothing under it. Rule 2:
# an empty result is a FAILURE, not a clean run -- a gate that accepts `## v0.3.1 —`
# followed by whitespace has been talked into passing by the thing it exists to catch.
# The thinnest section ever shipped (v0.2.10) is 1246 non-whitespace chars, so this
# floor is not a style opinion, it is a liveness check.
MIN_CHANGELOG_CHARS = 120
MIN_CHANGELOG_LINES = 2
# Likewise for the blurb: the thinnest shipped one is ~4.5k non-whitespace chars.
MIN_BLURB_CHARS = 400
UPDATE_HEADING = "What you need to update"
UPDATE_FIELDS = ("Client", "APWorld", "YAML", "Existing seed/save", "Profile/assets")

# ---- RATCHET ---------------------------------------------------------------------
# Versions that predate this gate and cannot be made green retroactively without
# inventing release prose after the fact -- which is precisely the lossy
# reconstruction rule 14 exists to stop. 0.3.0 shipped with a full changelog entry
# and no blurb; it is exempt from the BLURB check only, never the changelog one.
#
# 🛑 THIS SET IS A RATCHET. Nothing may be added to it. If your version is missing a
# blurb, the fix is to write the blurb, not to widen the exemption -- an exemption you
# can extend is a gate you have switched off.
BLURB_EXEMPT = {"0.3.0"}
CLIENT_GITLINK = "from-software-archipelago-clients"
CLIENT_NOTES_EXEMPT_TRAILER = "Client-Gitlink-Notes"
CLIENT_NOTES_EXEMPT_VALUE = "no-player-visible-change"

RED = "\033[31m"
GRN = "\033[32m"
OFF = "\033[0m"
if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
    RED = GRN = OFF = ""


def read_version():
    """APWORLD_VERSION, read TEXTUALLY. Importing contract.py would drag in the world
    (and Archipelago behind it) and confine this gate to a job that has one."""
    if not os.path.isfile(CONTRACT):
        sys.stderr.write("check_release_notes: cannot find %s\n" % CONTRACT)
        sys.exit(2)
    with open(CONTRACT, encoding="utf-8") as fh:
        src = fh.read()
    m = re.search(r'(?m)^APWORLD_VERSION\s*=\s*["\']([^"\']+)["\']', src)
    if not m:
        # Rule 1: a derivation that cannot answer must FAIL, not answer. Guessing a
        # version here would make the gate report on a release that does not exist.
        sys.stderr.write(
            "check_release_notes: no top-level `APWORLD_VERSION = \"...\"` in\n"
            "  greenfield/eldenring/contract.py -- the assignment moved or was renamed.\n"
            "  Fix this parser; do not let the gate guess.\n")
        sys.exit(2)
    return m.group(1)


def nonws(text):
    return len(re.sub(r"\s", "", text))


def changelog_section(version):
    """Return (heading_line, body) for `## v<version> ...`, or (None, None)."""
    with open(CHANGELOG, encoding="utf-8") as fh:
        text = fh.read()
    # 🛑 `## ` WITH THE SPACE. `^##[^\n]*$` also matches `###`, so the body of a section was
    # only the text ABOVE its first subheading -- and a section whose first line is a `###`
    # entry measured as EMPTY and failed this gate. Found 2026-08-15 by writing a changelog
    # entry directly under the heading, which is the natural place to put the newest one.
    # Every earlier section passed only because prose happened to sit above its entries, so
    # the 120-char floor has been applied to a preamble rather than to the notes.
    parts = re.split(r"(?m)^(## [^\n]*)$", text)
    for i in range(1, len(parts), 2):
        head = parts[i]
        if re.match(r"^##\s+v%s(\s|$)" % re.escape(version), head):
            return head, parts[i + 1]
    return None, None


def check_changelog(version, errs):
    today = "YYYY-MM-DD"
    want = "## v%s — %s" % (version, today)
    if not os.path.isfile(CHANGELOG):
        errs.append("%s is MISSING. Create it and add the heading: %s" % (NOTES_DIR + "/CHANGELOG.md", want))
        return
    head, body = changelog_section(version)
    if head is None:
        errs.append(
            "no changelog section for v%s.\n"
            "    CREATE: add this heading to %s/CHANGELOG.md, directly under the intro\n"
            "            paragraph and ABOVE the previous version's section:\n"
            "                %s\n"
            "    ...then write the line for the change you are landing right now, in the\n"
            "    same commit. That is rule 14. Reconstructing it at tag time is the failure."
            % (version, NOTES_DIR, want))
        return
    if not re.match(r"^##\s+v%s\s+—\s+\d{4}-\d{2}-\d{2}\s*$" % re.escape(version), head):
        errs.append(
            "changelog heading for v%s is malformed: %r\n"
            "    EDIT %s/CHANGELOG.md -- the house shape is `## v<version> — <YYYY-MM-DD>`\n"
            "    with an em dash, e.g. %s"
            % (version, head, NOTES_DIR, want))
        return
    lines = [ln for ln in body.splitlines() if ln.strip()]
    if nonws(body) < MIN_CHANGELOG_CHARS or len(lines) < MIN_CHANGELOG_LINES:
        errs.append(
            "the v%s changelog section is EMPTY (%d non-whitespace chars, %d non-blank lines;\n"
            "    floor is %d/%d). A heading with nothing under it is not a release note --\n"
            "    rule 2, an empty result is a failure, not a clean run.\n"
            "    EDIT %s/CHANGELOG.md under `%s` and say what changed and why it mattered."
            % (version, nonws(body), len(lines), MIN_CHANGELOG_CHARS, MIN_CHANGELOG_LINES,
               NOTES_DIR, head))


def check_blurb(version, errs):
    rel = "%s/BLURB-v%s.md" % (NOTES_DIR, version)
    path = os.path.join(REPO, NOTES_DIR, "BLURB-v%s.md" % version)
    if version in BLURB_EXEMPT:
        print("  blurb: EXEMPT (%s predates this gate; ratchet set, do not extend)" % version)
        return
    if not os.path.isfile(path):
        errs.append(
            "no release blurb for v%s.\n"
            "    CREATE: %s\n"
            "    Its first heading must be:  # v%s — release blurb (draft)\n"
            "    Draft it as the release window FILLS, not at tag time -- the moment a fix\n"
            "    lands is the only moment anyone knows why it mattered. Copy the shape from\n"
            "    %s/BLURB-v0.3.1.md." % (version, rel, version, NOTES_DIR))
        return
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if nonws(text) < MIN_BLURB_CHARS:
        errs.append(
            "%s is a STUB (%d non-whitespace chars, floor %d). An empty file passing for a\n"
            "    blurb is the same failure as an empty changelog section, one file over."
            % (rel, nonws(text), MIN_BLURB_CHARS))
    first = next((ln for ln in text.splitlines() if ln.startswith("#")), "")
    if ("v%s" % version) not in first:
        errs.append(
            "%s does not name v%s in its first heading (found: %r).\n"
            "    EDIT it to start:  # v%s — release blurb (draft)\n"
            "    A blurb filed under one version and headed with another is how you ship the\n"
            "    wrong notes -- the filename is not evidence about the contents."
            % (rel, version, first, version))


def _plain(text):
    """Collapse Markdown emphasis/whitespace for fixed-shape status comparisons."""
    return re.sub(r"\s+", " ", text.replace("**", "").strip()).lower()


def _update_status(field, value):
    """Return the player-facing ruling represented by one update line, or None."""
    value = _plain(value)
    choices = {
        "Client": ("required", "optional", "no"),
        "APWorld": ("required", "host-only", "no"),
        "YAML": (
            "no new yaml required. existing yamls remain valid.",
            "new yaml required.",
            "new yaml optional. existing yamls remain valid.",
        ),
        "Existing seed/save": ("compatible", "new seed required", "save migration required"),
        "Profile/assets": ("no action", "reinstall or replace"),
    }
    return next((choice for choice in choices[field] if value.startswith(choice)), None)


def parse_update_guidance(text, level, source):
    """Parse the first player-facing update section from one current release document.

    `level=3` is the first subsection inside a changelog version; `level=2` is the first section
    below a blurb title. The fixed labels make the two documents comparable without requiring
    byte-identical prose.
    """
    errs = []
    marker = "#" * level
    headings = list(re.finditer(r"(?m)^%s\s+(.+?)\s*$" % re.escape(marker), text))
    if not headings:
        return None, [
            "%s has no `%s %s` section; it must be the first player-facing section."
            % (source, marker, UPDATE_HEADING)
        ]
    first = headings[0]
    if first.group(1).strip().lower() != UPDATE_HEADING.lower():
        return None, [
            "%s begins with `%s %s`, not `%s %s`. Put update instructions first."
            % (source, marker, first.group(1).strip(), marker, UPDATE_HEADING)
        ]
    end = headings[1].start() if len(headings) > 1 else len(text)
    block = text[first.end():end]
    if re.search(r"(?i)\bTODO(?:\(open\))?\b|\bTBD\b|<[^>]+>", block):
        errs.append("%s leaves an unresolved placeholder in its update instructions." % source)

    values = {}
    field_rx = "|".join(re.escape(field) for field in UPDATE_FIELDS)
    rows = list(re.finditer(
        r"(?ms)^- \*\*(%s):\*\*\s*(.*?)(?=^- \*\*(?:%s):\*\*|\Z)"
        % (field_rx, field_rx), block))
    for row in rows:
        field, value = row.group(1), row.group(2).strip()
        if field in values:
            errs.append("%s repeats the **%s:** update line." % (source, field))
            continue
        status = _update_status(field, value)
        if status is None:
            errs.append("%s has an unsupported or missing **%s:** ruling: %r"
                        % (source, field, _plain(value)[:100]))
        else:
            values[field] = status
        if field == "YAML" and not value.startswith("**"):
            errs.append("%s must bold the direct YAML yes/no/optional answer." % source)

    missing = [field for field in UPDATE_FIELDS if field not in values]
    if missing:
        errs.append("%s is missing resolved update guidance for: %s."
                    % (source, ", ".join(missing)))
    return (values if not errs else None), errs


def check_update_guidance(version, errs):
    """Require complete, mutually consistent update instructions in both current documents."""
    _, changelog_body = changelog_section(version)
    blurb_rel = "%s/BLURB-v%s.md" % (NOTES_DIR, version)
    blurb_path = os.path.join(REPO, NOTES_DIR, "BLURB-v%s.md" % version)
    if changelog_body is None or not os.path.isfile(blurb_path):
        return  # The ordinary presence checks already provide the actionable error.
    with open(blurb_path, encoding="utf-8") as fh:
        blurb = fh.read()

    changelog_values, changelog_errs = parse_update_guidance(
        changelog_body, 3, "%s/CHANGELOG.md v%s" % (NOTES_DIR, version))
    blurb_values, blurb_errs = parse_update_guidance(blurb, 2, blurb_rel)
    errs.extend(changelog_errs)
    errs.extend(blurb_errs)
    if changelog_values is not None and blurb_values is not None:
        mismatched = [field for field in UPDATE_FIELDS
                      if changelog_values[field] != blurb_values[field]]
        if mismatched:
            detail = ", ".join(
                "%s (%s vs %s)" %
                (field, changelog_values[field], blurb_values[field])
                for field in mismatched)
            errs.append(
                "the changelog and blurb contradict each other about update requirements: %s."
                % detail)



def check_version_is_still_open(version, errs):
    """🛑 THE BLIND SPOT THIS GATE HAD UNTIL 2026-08-04.

    Everything above asks whether the version named by APWORLD_VERSION has a changelog section and a
    blurb. It never asked whether that version ALREADY SHIPPED -- and a released version has both, so
    the gate is at its greenest exactly when it is least useful.

    MOTIVATING CASE, and it is this repo, not a hypothetical: v0.3.3 was tagged on 2026-08-03 while
    APWORLD_VERSION still read "0.3.3". Three commits then landed on main writing their notes into
    the v0.3.3 section, which was already inside the tag. A player reading v0.3.3's notes would see a
    feature that was not in v0.3.3, and v0.3.4's notes would be missing it. Every gate stayed green.
    That is the same shape as the v0.3.0 -> v0.3.1 gap rule 14 was written for, one level up: the
    rule got a gate, and the gate got the same blind spot the rule had.

    The signal is the git tag. `git tag --list v<version>` plus "does main have commits past it".

    ⚠️ A SKIP HERE IS LOUD, NOT SILENT. If git is absent, or the tags were not fetched (a shallow
    `actions/checkout` does not fetch them by default), this check cannot answer -- and a check that
    cannot answer must say so rather than pass quietly (CONTRIBUTING rule 2). It warns and returns;
    it never adds an error it did not verify.
    """
    try:
        tagged = subprocess.run(["git", "tag", "--list", "v%s" % version],
                                cwd=REPO, capture_output=True, text=True, timeout=20)
        anytag = subprocess.run(["git", "tag", "--list", "v*"],
                                cwd=REPO, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        print("  window: UNCHECKED -- git unavailable (%s). This gate cannot tell a shipped "
              "version from an open one without tags." % exc)
        return
    if anytag.returncode != 0 or not anytag.stdout.strip():
        print("  window: UNCHECKED -- no v* tags in this checkout (a shallow clone does not fetch "
              "them; use fetch-depth: 0 or `git fetch --tags`). The shipped-version check did NOT "
              "run, so a green result here says nothing about it.")
        return
    if not tagged.stdout.strip():
        print("  window: v%s is not tagged -- the window is OPEN, which is the state notes are "
              "written in." % version)
        return
    past = subprocess.run(["git", "rev-list", "--count", "v%s..HEAD" % version],
                          cwd=REPO, capture_output=True, text=True, timeout=20)
    n = past.stdout.strip() if past.returncode == 0 else "?"
    if n in ("0", "?"):
        print("  window: v%s is tagged and HEAD is at it -- nothing has landed since." % version)
        return
    errs.append(
        "APWORLD_VERSION names v%s, which is ALREADY TAGGED, and %s commit(s) have landed since.\n"
        "    Every one of them has been writing release notes into a section that already SHIPPED.\n"
        "    A player reading v%s's notes will see changes that were not in v%s, and the next\n"
        "    version's notes will be missing them.\n"
        "    FIX: open the next window -- bump APWORLD_VERSION (and the other version sites;\n"
        "    `python tools/check_version_sites.py` lists them), append a CONTRACT-VERSIONS.tsv row,\n"
        "    add the `## v<next> — <today>` heading, and MOVE the post-tag entries into it."
        % (version, n, version, version))


def _git(repo, *args, input_text=None):
    return subprocess.run(["git", *args], cwd=repo, input=input_text, capture_output=True,
                          text=True, timeout=20)


def client_gitlink_note_failures(repo=REPO, rev_range=None):
    """Return gitlink-moving first-parent commits that carry neither notes nor an exemption.

    First-parent is deliberate. On a PR branch it sees the PR commit; after a merge it sees the merge
    commit's net change against main. Walking every parent would charge the same PR twice and would
    inspect client-side history that is not part of the world's release ledger.
    """
    if rev_range is None:
        tag = _git(repo, "describe", "--tags", "--match", "v[0-9]*", "--abbrev=0", "HEAD")
        if tag.returncode != 0 or not tag.stdout.strip():
            return None, "no reachable v* release tag; fetch tags before trusting this gate"
        rev_range = "%s..HEAD" % tag.stdout.strip()

    commits = _git(repo, "rev-list", "--first-parent", "--reverse", rev_range)
    if commits.returncode != 0:
        return None, "cannot walk %s: %s" % (rev_range, commits.stderr.strip() or "git failed")

    # RULED HISTORICAL BUMPS. A bump commit that cannot carry its note any more (history is
    # immutable) gets a WAIVER here with the ruling -- and a stale waiver (the sha leaves the
    # window) is pruned when the window rolls. Same both-directions shape as RULED_BARE_GROUPS.
    ruled = {
        # #925's merge: Alaric recreated the gitlink bump as a bare commit (4582be8e) re-pinning
        # to the post-clients#332 client main; the paired changelog entry ("the region-lock kick
        # table caught up with the census") had already landed via a18b70d2 one commit earlier on
        # the same branch. The note EXISTS on main; only the commit-granularity pairing is broken,
        # and rewriting main is worse than recording the ruling (2026-08-20).
        "933c7a24e0d07885dbae9b115bdcfb684a285a76",
    }
    failures = []
    bumps = 0
    for commit in commits.stdout.split():
        if commit in ruled:
            bumps += 1
            continue
        # Compare explicitly to parent 1. `diff-tree -m --first-parent` still emits the other-parent
        # view on this Git version, falsely charging unrelated merge commits for paths that exist
        # only on main. Omitting `-m` emits no merge paths at all. The explicit pair has one answer.
        changed = _git(repo, "diff", "--name-only", "%s^1" % commit, commit, "--")
        if changed.returncode != 0:
            return None, "cannot inspect %s: %s" % (commit[:12], changed.stderr.strip())
        paths = set(changed.stdout.splitlines())
        if CLIENT_GITLINK not in paths:
            continue
        bumps += 1
        if "release/CHANGELOG.md" in paths:
            continue

        body = _git(repo, "show", "-s", "--format=%B", commit)
        if body.returncode != 0:
            return None, "cannot read commit message %s" % commit[:12]
        trailers = _git(repo, "interpret-trailers", "--parse", input_text=body.stdout)
        exempt = False
        if trailers.returncode == 0:
            for line in trailers.stdout.splitlines():
                key, sep, value = line.partition(":")
                if (sep and key.strip().lower() == CLIENT_NOTES_EXEMPT_TRAILER.lower()
                        and value.strip() == CLIENT_NOTES_EXEMPT_VALUE):
                    exempt = True
                    break
        if exempt:
            continue
        subject = _git(repo, "show", "-s", "--format=%s", commit).stdout.strip()
        failures.append((commit, subject))
    return {"range": rev_range, "bumps": bumps, "failures": failures}, None


def check_client_gitlink_notes(errs, rev_range=None):
    """Rule #709: every client gitlink bump pays its release note in the same world commit."""
    try:
        result, unchecked = client_gitlink_note_failures(REPO, rev_range)
    except (OSError, subprocess.SubprocessError) as exc:
        result, unchecked = None, "git unavailable (%s)" % exc
    if result is None:
        print("  client notes: UNCHECKED -- %s" % unchecked)
        return
    print("  client notes: checked %d gitlink bump(s) in %s" %
          (result["bumps"], result["range"]))
    if not result["failures"]:
        return
    rows = "\n".join("      %s %s" % (sha[:12], subject)
                     for sha, subject in result["failures"])
    errs.append(
        "%d client gitlink bump(s) carry neither a release/CHANGELOG.md update nor the exact\n"
        "    no-visible-change trailer:\n%s\n"
        "    FIX each bump in the commit that moves the gitlink: add the client-facing changelog\n"
        "    entry, or for a pure version-lockstep/no-behaviour bump add this exact git trailer:\n"
        "        %s: %s\n"
        "    An unchanged changelog and prose saying 'lockstep' are not exemptions (#709)."
        % (len(result["failures"]), rows, CLIENT_NOTES_EXEMPT_TRAILER,
           CLIENT_NOTES_EXEMPT_VALUE))


def main(argv):
    args = [a for a in argv[1:] if a != "--check"]   # --check: accepted, no-op (see docstring)
    version = None
    git_range = None
    while args and args[0] in ("--version", "--git-range"):
        opt = args.pop(0)
        if not args:
            sys.stderr.write("check_release_notes: %s needs a value\n" % opt)
            return 2
        value = args.pop(0)
        if opt == "--version":
            version = value
        else:
            git_range = value
    if args:
        sys.stderr.write(__doc__)
        return 2
    if version is None:
        version = read_version()

    print("check_release_notes: APWORLD_VERSION = %s" % version)
    errs = []
    check_changelog(version, errs)
    check_blurb(version, errs)
    check_update_guidance(version, errs)
    check_version_is_still_open(version, errs)
    check_client_gitlink_notes(errs, git_range)

    for m in errs:
        print("%sERROR%s %s" % (RED, OFF, m))
    if errs:
        print("check_release_notes: %d error(s). The release notes are part of the CHANGE, not\n"
              "part of the release (CONTRIBUTING rule 14)." % len(errs))
        return 1
    print("%sOK%s check_release_notes: v%s has a changelog section%s"
          % (GRN, OFF, version, "" if version in BLURB_EXEMPT else " and a blurb"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
