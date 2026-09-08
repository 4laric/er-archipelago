#!/usr/bin/env python3
"""apply_oracle_region_verdicts.py -- fold reviewer verdicts back into the region review queue.

THE ROUND TRIP, AND WHY IT LOOKS LIKE THIS. The player review notebook has no server: a reviewer
works in the browser, their notes live in that browser's IndexedDB, and they share their work by
pressing "Download all notes / backup", which writes an `er-player-notebook-v1` JSON file. That is
the ONLY submission mechanism the notebook has ever had, and inventing a second one for this queue
would mean two ways to lose a reviewer's work instead of one. So this tool reads exactly that file
(and the older single-report `er-player-review-v1` shape, and arrays of either) and writes the
verdicts into `greenfield/evidence/oracle-region-queue.tsv`:

    OracleVerdict  -> status    ('confirmed-ours' | 'moved'; blank means "not ruled", and is skipped)
    Reviewer       -> reviewer  (two people work this queue, so an unnamed verdict is REFUSED)
    LockRegion + Finding/Evidence/RawNotes -> note (one line, in the reviewer's own words)

🛑 NOTHING IS ADJUDICATED HERE. Recording a verdict does not move a check. `moved` rows are fixed
in a later change through the normal derivation ladder (M61_TILE_CURATED, DUNGEON_REGION_CURATED,
region_overrides.tsv only as a last resort), and a row that stops disagreeing then leaves the queue
on the next `matt_oracle.py --region-queue` refresh.

🛑 LICENCE BOUNDARY. Everything written here is the reviewer's own words plus our own ids. The
queue never carries the second source's area names, prose or tags. See AGENTS.md "MATT ORACLE".

A verdict that disagrees with one already in the file is REFUSED rather than overwritten -- two
reviewers disagreeing is the finding, not a merge conflict to resolve by import order. Re-run with
--force to take the newer one anyway, which records both reviewers in the note.

Run:
    python tools/apply_oracle_region_verdicts.py notebook.json [more.json ...] [--dry-run]
"""
import argparse
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(REPO, "greenfield", "evidence", "oracle-region-queue.tsv")
VERDICTS = ("confirmed-ours", "moved")
NOTE_FIELDS = ("LockRegion", "Finding", "Evidence", "RawNotes")


def read_queue(path):
    """(header comment lines, column names, [row dicts in file order])."""
    comments, columns, rows = [], None, []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                comments.append(line.rstrip("\n"))
                continue
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            if columns is None:
                columns = parts
                continue
            rows.append(dict(zip(columns, parts)))
    if columns is None:
        raise SystemExit("FATAL: %s has no column header" % path)
    return comments, columns, rows


def write_queue(path, comments, columns, rows):
    lines = list(comments) + ["\t".join(columns)]
    for row in rows:
        lines.append("\t".join((row.get(c, "") or "") for c in columns))
    # newline='\n' so a Windows run and a Linux run produce the SAME bytes.
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


def _one_line(text):
    """A cell is one line: tabs and newlines would break the tsv and silently eat the rest."""
    return " ".join(str(text or "").split())


def forms_from(payload):
    """Every notebook shape the page can produce -> [(check_id, form dict)].

    Accepts the notebook backup (`er-player-notebook-v1`), a single legacy report
    (`er-player-review-v1`), and an array of either -- the same three the notebook's own importer
    takes, because a reviewer should not have to know which button produced their file.
    """
    out = []
    if isinstance(payload, list):
        for item in payload:
            out.extend(forms_from(item))
        return out
    if not isinstance(payload, dict):
        return out
    if payload.get("schema") == "er-player-notebook-v1":
        for review in payload.get("reviews") or []:
            if isinstance(review, dict) and isinstance(review.get("form"), dict):
                out.append((review.get("check_id"), review["form"]))
        return out
    if payload.get("schema") == "er-player-review-v1":
        out.append((payload.get("check_id"), {
            "OracleVerdict": payload.get("oracle_verdict", ""),
            "Reviewer": payload.get("reviewer", ""),
            "LockRegion": payload.get("region_lock_region", ""),
            "Finding": payload.get("finding", ""),
            "Evidence": payload.get("evidence", ""),
            "RawNotes": payload.get("raw_notes", ""),
        }))
        return out
    raise SystemExit("FATAL: %r is not a player notebook backup or player review file"
                     % (payload.get("schema") or "<no schema>"))


def apply_verdicts(rows, forms, force=False):
    """Fold (check_id, form) pairs into the queue rows. Returns (applied, skipped, problems)."""
    by_ap = {}
    for row in rows:
        try:
            by_ap[int(row["ap_id"])] = row
        except (KeyError, ValueError, TypeError):
            continue
    applied, skipped, problems = 0, 0, []
    for check_id, form in forms:
        verdict = _one_line(form.get("OracleVerdict"))
        if not verdict:
            skipped += 1
            continue
        try:
            row = by_ap[int(check_id)]
        except (KeyError, ValueError, TypeError):
            problems.append("check %r is not in the queue; its verdict was NOT applied" % check_id)
            continue
        if verdict not in VERDICTS:
            problems.append("check %s: verdict %r is not one of %s"
                            % (check_id, verdict, ", ".join(VERDICTS)))
            continue
        reviewer = _one_line(form.get("Reviewer"))
        if not reviewer:
            problems.append("check %s: verdict %r has no reviewer name. Two people work this "
                            "queue, so an unattributed verdict is refused." % (check_id, verdict))
            continue
        note = _one_line(" — ".join(
            x for x in (_one_line(form.get(f)) for f in NOTE_FIELDS) if x))
        old_status, old_reviewer = row.get("status", "open"), _one_line(row.get("reviewer"))
        if (old_status in VERDICTS and old_status != verdict
                and old_reviewer and old_reviewer != reviewer):
            if not force:
                problems.append(
                    "check %s: %s already ruled %r and %s says %r. Two reviewers disagreeing IS "
                    "the finding -- adjudicate it, or re-run with --force to take the newer one."
                    % (check_id, old_reviewer, old_status, reviewer, verdict))
                continue
            note = _one_line("%s (overrides %s: %s)" % (note, old_reviewer, old_status))
        if old_reviewer and old_reviewer != reviewer and old_status == verdict:
            reviewer = old_reviewer + ", " + reviewer      # both reviewers agreed: record both
        row["status"], row["reviewer"], row["note"] = verdict, reviewer, note
        applied += 1
    return applied, skipped, problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("notebooks", nargs="+", help="notebook backup / player review JSON file(s)")
    ap.add_argument("--queue", default=QUEUE, help="queue tsv (default: %(default)s)")
    ap.add_argument("--dry-run", action="store_true", help="report, write nothing")
    ap.add_argument("--force", action="store_true",
                    help="let a newer verdict override a DISAGREEING recorded one")
    args = ap.parse_args(argv)

    comments, columns, rows = read_queue(args.queue)
    forms = []
    for path in args.notebooks:
        with open(path, encoding="utf-8") as fh:
            forms.extend(forms_from(json.load(fh)))
    applied, skipped, problems = apply_verdicts(rows, forms, force=args.force)

    for problem in problems:
        print("WARN: " + problem)
    print("%d verdict(s) applied, %d note(s) carried no verdict, %d refused"
          % (applied, skipped, len(problems)))
    print("queue now: " + ", ".join(
        "%s %d" % (s, sum(1 for r in rows if (r.get("status") or "open") == s))
        for s in ("open",) + VERDICTS))
    if args.dry_run:
        print("--dry-run: %s not written" % args.queue)
        return 1 if problems else 0
    write_queue(args.queue, comments, columns, rows)
    print("wrote %s" % args.queue)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
