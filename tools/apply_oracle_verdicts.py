#!/usr/bin/env python3
"""apply_oracle_verdicts.py -- fold reviewer verdicts back into an oracle review queue.

TWO QUEUES, ONE MECHANISM. `tools/matt_oracle.py` writes two human review queues, and they differ
only in what a row is ABOUT:

    --queue region     greenfield/evidence/oracle-region-queue.tsv
                       "a second source's own partition puts this check in a different region"
                       verdicts: confirmed-ours | moved
    --queue missable   greenfield/evidence/oracle-missable-queue.tsv
                       "a second source tags this check missable, we do not, and OUR OWN
                        questline_conditions.tsv shows a permanently losable gate on it"
                       verdicts: confirmed-not-missable | missable

Everything else -- the file shape, the (flag, ap_id) key, the three hand-edited columns, the
refusals -- is shared, and deliberately so: a second copy of this round trip would be a second
place for a reviewer's work to go missing. See QUEUES below for the whole per-queue difference.

THE ROUND TRIP, AND WHY IT LOOKS LIKE THIS. The player review notebook has no server: a reviewer
works in the browser, their notes live in that browser's IndexedDB, and they share their work by
pressing "Download all notes / backup", which writes an `er-player-notebook-v1` JSON file. That is
the ONLY submission mechanism the notebook has ever had, and inventing a second one for these
queues would mean two ways to lose a reviewer's work instead of one. So this tool reads exactly
that file (and the older single-report `er-player-review-v1` shape, and arrays of either) and
writes the verdicts into the queue tsv:

    <verdict field>  -> status    (blank means "not ruled", and is skipped)
    Reviewer         -> reviewer  (two people work these queues, so an unnamed verdict is REFUSED)
    <note fields>    -> note      (one line, in the reviewer's own words)

🛑 NOTHING IS ADJUDICATED HERE. Recording a verdict does not move a check and does not tag one.
A region `moved` row is fixed in a later change through the normal derivation ladder
(M61_TILE_CURATED, DUNGEON_REGION_CURATED, region_overrides.tsv only as a last resort); a
`missable` row is applied in a later change through the normal missable derivation in
greenfield/gen_data.py, never by editing tables/missable_locations.py. A row that stops
disagreeing then leaves its queue on the next `matt_oracle.py` refresh.

🛑 LICENCE BOUNDARY. Everything written here is the reviewer's own words plus our own ids. Neither
queue carries the second source's area names, tags, prose or Text. See AGENTS.md "MATT ORACLE".

A verdict that disagrees with one already in the file is REFUSED rather than overwritten -- two
reviewers disagreeing is the finding, not a merge conflict to resolve by import order. Re-run with
--force to take the newer one anyway, which records both reviewers in the note.

Run:
    python tools/apply_oracle_verdicts.py notebook.json [more.json ...] [--dry-run]
    python tools/apply_oracle_verdicts.py --queue missable notebook.json
"""
import argparse
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTE_FIELDS = ("LockRegion", "Finding", "Evidence", "RawNotes")


class QueueSpec:
    """One review queue's vocabulary. The MECHANISM is shared; only these fields differ.

    verdict_field / legacy_verdict_key -- the notebook form field, and its alias in the older
        single-report file shape. Two DISTINCT fields (OracleVerdict, OracleMissableVerdict)
        rather than one shared one, because a check can sit in both queues at once and a single
        field would silently make one ruling stand in for the other.
    reason_field / reasons / reason_required_for -- an extra closed-vocabulary control, used by the
        missable queue only. gen_data's MISSABLE_LOCATIONS values are a CLOSED set of mechanism
        labels (deathroot, alt_currency:N, gesture_award, questline, questline_item), so a
        `missable` verdict whose reason does not name a mechanism cannot be applied downstream at
        all. Refusing it here is the difference between an unapplicable verdict and a lost one.
    """

    def __init__(self, name, path, verdict_field, legacy_verdict_key, verdicts,
                 reason_field=None, legacy_reason_key=None, reasons=(), reason_required_for=()):
        self.name = name
        self.path = path
        self.verdict_field = verdict_field
        self.legacy_verdict_key = legacy_verdict_key
        self.verdicts = verdicts
        self.reason_field = reason_field
        self.legacy_reason_key = legacy_reason_key
        self.reasons = reasons
        self.reason_required_for = reason_required_for


QUEUES = {
    "region": QueueSpec(
        name="region",
        path=os.path.join(REPO, "greenfield", "evidence", "oracle-region-queue.tsv"),
        verdict_field="OracleVerdict", legacy_verdict_key="oracle_verdict",
        verdicts=("confirmed-ours", "moved"),
    ),
    "missable": QueueSpec(
        name="missable",
        path=os.path.join(REPO, "greenfield", "evidence", "oracle-missable-queue.tsv"),
        verdict_field="OracleMissableVerdict", legacy_verdict_key="oracle_missable_verdict",
        verdicts=("confirmed-not-missable", "missable"),
        reason_field="OracleMissableReason", legacy_reason_key="oracle_missable_reason",
        # OUR OWN mechanism words, and the gen_data missable class each one maps onto:
        #   limited-consumable  -> deathroot / alt_currency:N (a currency item spent, not regained)
        #   killable-npc        -> gesture_award              (an NPC dialogue award, lost on death)
        #   questline-progress  -> questline / questline_item (a quest step walked past)
        # `confirmed-not-missable` needs no mechanism: it is the claim that NONE of them applies.
        reasons=("limited-consumable", "killable-npc", "questline-progress"),
        reason_required_for=("missable",),
    ),
}

# Kept so the region queue's own callers and tests can still say "the documented verdicts".
VERDICTS = QUEUES["region"].verdicts


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
        form = {
            "Reviewer": payload.get("reviewer", ""),
            "LockRegion": payload.get("region_lock_region", ""),
            "Finding": payload.get("finding", ""),
            "Evidence": payload.get("evidence", ""),
            "RawNotes": payload.get("raw_notes", ""),
        }
        # Every queue's verdict (and reason) rides the SAME legacy record, under its own alias.
        for spec in QUEUES.values():
            form[spec.verdict_field] = payload.get(spec.legacy_verdict_key, "")
            if spec.reason_field:
                form[spec.reason_field] = payload.get(spec.legacy_reason_key, "")
        out.append((payload.get("check_id"), form))
        return out
    raise SystemExit("FATAL: %r is not a player notebook backup or player review file"
                     % (payload.get("schema") or "<no schema>"))


def apply_verdicts(rows, forms, force=False, spec=None):
    """Fold (check_id, form) pairs into the queue rows. Returns (applied, skipped, problems)."""
    spec = spec or QUEUES["region"]
    by_ap = {}
    for row in rows:
        try:
            by_ap[int(row["ap_id"])] = row
        except (KeyError, ValueError, TypeError):
            continue
    applied, skipped, problems = 0, 0, []
    for check_id, form in forms:
        verdict = _one_line(form.get(spec.verdict_field))
        if not verdict:
            skipped += 1
            continue
        try:
            row = by_ap[int(check_id)]
        except (KeyError, ValueError, TypeError):
            problems.append("check %r is not in the %s queue; its verdict was NOT applied"
                            % (check_id, spec.name))
            continue
        if verdict not in spec.verdicts:
            problems.append("check %s: verdict %r is not one of %s"
                            % (check_id, verdict, ", ".join(spec.verdicts)))
            continue
        reviewer = _one_line(form.get("Reviewer"))
        if not reviewer:
            problems.append("check %s: verdict %r has no reviewer name. Two people work this "
                            "queue, so an unattributed verdict is refused." % (check_id, verdict))
            continue
        reason = _one_line(form.get(spec.reason_field)) if spec.reason_field else ""
        if reason and reason not in spec.reasons:
            problems.append("check %s: reason %r is not one of %s. gen_data's missable classes "
                            "are a closed vocabulary, so a reason outside it could never be "
                            "applied." % (check_id, reason, ", ".join(spec.reasons)))
            continue
        if verdict in spec.reason_required_for and not reason:
            problems.append("check %s: a %r verdict must name the mechanism (%s). Without one it "
                            "cannot be mapped onto a gen_data missable class, so it could never "
                            "be applied." % (check_id, verdict, ", ".join(spec.reasons)))
            continue
        note = _one_line(" — ".join(
            x for x in ([reason] + [_one_line(form.get(f)) for f in NOTE_FIELDS]) if x))
        old_status, old_reviewer = row.get("status", "open"), _one_line(row.get("reviewer"))
        if (old_status in spec.verdicts and old_status != verdict
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
    ap.add_argument("--queue", choices=sorted(QUEUES), default="region",
                    help="which review queue to fold into (default: %(default)s)")
    ap.add_argument("--path", default=None,
                    help="the queue tsv (default: the chosen queue's committed file)")
    ap.add_argument("--dry-run", action="store_true", help="report, write nothing")
    ap.add_argument("--force", action="store_true",
                    help="let a newer verdict override a DISAGREEING recorded one")
    args = ap.parse_args(argv)

    spec = QUEUES[args.queue]
    path = args.path or spec.path
    comments, columns, rows = read_queue(path)
    forms = []
    for nb in args.notebooks:
        with open(nb, encoding="utf-8") as fh:
            forms.extend(forms_from(json.load(fh)))
    applied, skipped, problems = apply_verdicts(rows, forms, force=args.force, spec=spec)

    for problem in problems:
        print("WARN: " + problem)
    print("%d verdict(s) applied, %d note(s) carried no %s verdict, %d refused"
          % (applied, skipped, spec.name, len(problems)))
    print("queue now: " + ", ".join(
        "%s %d" % (s, sum(1 for r in rows if (r.get("status") or "open") == s))
        for s in ("open",) + spec.verdicts))
    if args.dry_run:
        print("--dry-run: %s not written" % path)
        return 1 if problems else 0
    write_queue(path, comments, columns, rows)
    print("wrote %s" % path)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
