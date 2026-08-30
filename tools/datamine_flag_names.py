#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""datamine_flag_names.py -- a HUMAN-READABLE label for an event flag, from FromSoft's own names.

WHY. Every gate corpus in this repo speaks in bare flag ids. `f3708` gates the Stormhill Shack
Golden Seed and there is nothing anywhere that says what f3708 *is*, so reading `questline_dag.tsv`
means holding a dictionary in your head that does not exist. Alaric, 2026-07-28: "any way to resolve
these flag names to something human-readable like 'talk to roderika'".

There is, and it is a game datum rather than a guess. **The flag has no name; the EVENT THAT SETS IT
does.** The decompiled EMEVD carries FromSoft's own developer comment above almost every event --
the Japanese original, plus the English gloss the decompiler produced:

    // NPC311半島砦の城主_キャラ状態遷移 -- NPC311 Peninsula Fort Castle Lord_Character state transition
    $Event(3419, Restart, function() { ... SetEventFlagID(3409, ON); ... }

So f3409 is labelled "NPC311 Peninsula Fort Castle Lord_Character state transition", and f3708/f3709
come back "NPC320 Farnese_Character state transition" -- Farnese being Roderika's internal name, i.e.
exactly the "talk to Roderika" that was asked for.

⭐ THE CORROBORATION, which is what makes the table credible rather than plausible: the label this
derives for f3409 is, word for word, the comment a human hand-wrote into gen_data's
`_NPC_STATE_GATED` months ago after reading the same file by eye. A derivation that re-finds a hand
audit is the argument every other table here rests on.

🛑 THREE THINGS THIS LABEL IS NOT, and each has already produced a wrong reading in review:

  1. **It names the EVENT, not the FLAG.** One event that sets five flags gives all five the same
     label. It is an ATTRIBUTION -- "this is set by the thing called X" -- never a definition. A
     flag set by several events gets several, and the count is emitted so a one-of-many label cannot
     be mistaken for the answer.
  2. **The English is a MACHINE TRANSLATION** carried in the decompiled comment, not a FromSoft
     string. `name_ja` is the datum; `name_en` is a convenience that can be subtly wrong ("Giant pot
     event_raise event end flag" is the Great Jar's duellists). Both are emitted, ja first, and
     anything reasoning about meaning should read the Japanese.
  3. **A missing label means UNNAMED, never "no questline".** 39% of the DAG's source flags have no
     named setter -- they are set by an ESD, or by an unnamed event, or by nothing this scan sees.
     Absence here says the scan could not reach it (CONTRIBUTING: an empty result is a failure, not
     a clean run) and the `source` column says which.

SOURCES, strongest first. Each row records which one it used, because they are not equally good:

    emevd_event   the `SetEventFlagID` / `SetNetworkconnectedEventFlagID` site sits inside an event
                  with a name comment. The strong one.
    emevd_batch   the flag falls inside a `BatchSetEventFlags(lo, hi)` range in a named event.
                  WEAKER: the event names the RANGE's purpose, and a range can be a sweep over
                  flags that have little to do with each other. Ranges wider than 64 are dropped
                  outright rather than labelling hundreds of flags off one comment.
    esd_talk      no EMEVD setter, but `esd_flags.tsv` says an NPC talk ESD sets it. No name -- the
                  talk id and map are the label ("set by talk 102001110 on m11_10"). Weakest, and
                  it is provenance rather than meaning.

INPUT:  the decompiled EMEVD (`elden_ring_artifacts/event/*.emevd.dcx.js`, or `ER_EVENT_DIR`), plus
        committed `greenfield/esd_flags.tsv`.
        ⚠️ TIER 2 (AGENTS §5a): this is a `gen_data`-adjacent INPUT table, emitted by hand. No
        `build.ps1` step regenerates it, and CI cannot -- the EMEVD is licensing-restricted. Re-emit
        it yourself when the corpus changes, and commit the result.
OUTPUT: greenfield/flag_names.tsv

USAGE:
    python tools/datamine_flag_names.py --probe   # counts + samples, writes nothing
    python tools/datamine_flag_names.py --emit    # write greenfield/flag_names.tsv
"""
import argparse
import collections
import csv
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EVT = os.environ.get("ER_EVENT_DIR") or os.path.join(ROOT, "elden_ring_artifacts", "event")
GF = os.path.join(ROOT, "greenfield")
OUT = os.path.join(GF, "flag_names.tsv")

# Measured on the complete 1.17 corpus committed in gen_inputs.db (2026-08-30). These are
# deliberately independent floors: a uniformly truncated event directory can preserve the named
# percentage and the two hand-verified exemplar flags while silently deleting thousands of other
# labels. The writer feeds questline review and must refuse that convincing partial answer.
MIN_EVENT_FILES = 589
MIN_EVENTS = 4893
MIN_LABELLED_FLAGS = 5111

# `// <comment>` immediately above `$Event(<id>, <restart>, function(<params>) {`. The comment is
# OPTIONAL in the regex on purpose: an unnamed event must be COUNTED, not skipped silently.
EVENT_RE = re.compile(
    r"(?:^//[ \t]*(?P<name>.*?)\r?\n)?\$Event\((?P<id>\d+),\s*\w+,\s*function\([^)]*\)\s*\{", re.M)
SET_RE = re.compile(r"\b(?:SetEventFlagID|SetNetworkconnectedEventFlagID)\s*\(\s*(\d+)\s*,")
BATCH_RE = re.compile(
    r"\bBatchSet(?:Networkconnected)?EventFlags\s*\(\s*(\d+)\s*,\s*(\d+)\s*,")
# A range wider than this is a bulk reset/sweep; naming every flag in it off one comment would
# manufacture hundreds of confident labels from a single sentence.
MAX_BATCH = 64
MAP_RE = re.compile(r"^(m\d\d_\d\d_\d\d_\d\d|common(?:_func)?)\.emevd")


def _split_name(raw):
    """`日本語 -- English gloss` -> (ja, en). Either half may be absent.

    The separator is the decompiler's, and it is ` -- `. A comment with no separator is Japanese
    only (untranslated) far more often than it is English, so it lands in `ja` and `en` stays empty
    rather than being guessed at -- an ASCII heuristic here mislabels the many comments that mix
    ASCII ids into Japanese text (`NPC311半島砦の城主_...`).
    """
    raw = " ".join((raw or "").split())
    if " -- " in raw:
        ja, en = raw.split(" -- ", 1)
        return ja.strip(), en.strip()
    return raw, ""


def scan(event_dir=EVT):
    """-> (labels, stats). labels: {flag: [(ja, en, source, event_id, map_id)]}"""
    files = sorted(glob.glob(os.path.join(event_dir, "*.emevd.dcx.js")))
    if not files:
        sys.exit("FATAL: no *.emevd.dcx.js under %s. Set ER_EVENT_DIR, or run "
                 "`python tools/gen_inputs.py --ensure elden_ring_artifacts`. Refusing to emit an "
                 "empty table -- an empty result is a FAILURE, not 'no names found'." % event_dir)
    labels = collections.defaultdict(list)
    st = collections.Counter()
    st["files"] = len(files)
    for path in files:
        base = os.path.basename(path)
        m = MAP_RE.match(base)
        map_id = m.group(1) if m else base.split(".")[0]
        text = open(path, encoding="utf-8", errors="replace").read()
        # A truncated read would quietly shrink the corpus and report a clean, small table.
        if text.count("{") != text.count("}"):
            sys.exit("FATAL: %s has unbalanced braces (%d/%d) -- a truncated read, not a corpus."
                     % (base, text.count("{"), text.count("}")))
        marks = list(EVENT_RE.finditer(text))
        st["events"] += len(marks)
        for i, mk in enumerate(marks):
            raw = mk.group("name")
            eid = int(mk.group("id"))
            body = text[mk.end(): marks[i + 1].start() if i + 1 < len(marks) else len(text)]
            if not raw:
                st["events_unnamed"] += 1
            else:
                st["events_named"] += 1
            ja, en = _split_name(raw)
            for sm in SET_RE.finditer(body):
                st["set_sites"] += 1
                if not raw:
                    st["set_sites_in_unnamed_event"] += 1
                    continue
                labels[int(sm.group(1))].append((ja, en, "emevd_event", eid, map_id))
            for bm in BATCH_RE.finditer(body):
                lo, hi = int(bm.group(1)), int(bm.group(2))
                st["batch_sites"] += 1
                if hi < lo or hi - lo > MAX_BATCH:
                    st["batch_too_wide_dropped"] += 1
                    continue
                if not raw:
                    st["batch_sites_in_unnamed_event"] += 1
                    continue
                for flag in range(lo, hi + 1):
                    labels[flag].append((ja, en, "emevd_batch", eid, map_id))
    return labels, st


def esd_labels():
    """{flag: [(ja, en, source, talk_id, map_id)]} -- provenance, not a name."""
    path = os.path.join(GF, "esd_flags.tsv")
    out = collections.defaultdict(list)
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader((ln for ln in fh if not ln.lstrip().startswith("#")),
                                delimiter="\t"):
            raw = (r.get("flag") or "").strip()
            if raw.isdigit():
                talk = (r.get("talk_id") or "").strip()
                mp = (r.get("map_id") or "").strip()
                out[int(raw)].append(("", "set by NPC talk %s%s" % (talk, " on " + mp if mp else ""),
                                      "esd_talk", talk, mp))
    return out


_SOURCE_RANK = {"emevd_event": 0, "emevd_batch": 1, "esd_talk": 2}


def build(event_dir=EVT):
    labels, st = scan(event_dir)
    for flag, rows in esd_labels().items():
        # ESD is the FALLBACK: it says who sets a flag, not what it is. It never displaces an
        # EMEVD name, and it is only recorded where nothing better exists.
        if flag not in labels:
            labels[flag].extend(rows)
            st["esd_only"] += 1
    out = []
    for flag in sorted(labels):
        rows = labels[flag]
        # Deterministic pick: best source, then lowest event id. `setters` carries the count so a
        # one-of-many label can never be read as "the" name -- an event that sets five flags gives
        # all five the same string, and that is an attribution, not a definition.
        uniq = sorted({r for r in rows}, key=lambda r: (_SOURCE_RANK[r[2]], str(r[3]), r[0], r[1]))
        ja, en, source, eid, map_id = uniq[0]
        out.append({
            "flag": flag, "name_ja": ja, "name_en": en, "source": source,
            "set_by_event": eid, "map_id": map_id, "setters": len(uniq),
        })
        st["labelled:" + source] += 1
    return out, st


_HEADER = """\
# AUTO-GENERATED by tools/datamine_flag_names.py -- DO NOT EDIT, re-emit.
# A human-readable label for an event flag, taken from FromSoft's OWN developer comment on the
# event that SETS it (the decompiled EMEVD carries `// <japanese> -- <english gloss>` above almost
# every event). The flag itself has no name anywhere in the game data.
# 🛑 IT NAMES THE EVENT, NOT THE FLAG. One event setting five flags labels all five identically --
#   an ATTRIBUTION ("set by the thing called X"), never a definition. `setters` is how many distinct
#   named setters were found; >1 means the label shown is one of several.
# 🛑 `name_en` IS A MACHINE TRANSLATION carried in the decompiled comment, not a FromSoft string.
#   `name_ja` is the datum. Read the Japanese before reasoning about meaning.
# 🛑 A FLAG ABSENT HERE IS UNNAMED, not ungated. Absence means this scan could not reach it.
# source: emevd_event (a SetEventFlag site in a NAMED event -- strongest)
#       | emevd_batch (inside a BatchSetEventFlags range in a named event; the comment names the
#                      RANGE's purpose, so it is weaker. Ranges wider than 64 are dropped)
#       | esd_talk    (no EMEVD setter; esd_flags.tsv says a talk ESD sets it. Provenance, no name)
# TIER 2 (AGENTS §5a): a hand-run emit. No build.ps1 step regenerates this and CI cannot -- the
#   EMEVD is licensing-restricted. Re-emit and commit when the corpus changes.
# MEASURED THIS RUN (recomputed on every emit):
"""


def emit(rows, st, path=OUT):
    cols = ["flag", "name_ja", "name_en", "source", "set_by_event", "map_id", "setters"]
    body = [_HEADER]
    for key in ("files", "events", "events_named", "events_unnamed", "set_sites",
                "set_sites_in_unnamed_event", "batch_sites", "batch_too_wide_dropped",
                "batch_sites_in_unnamed_event", "esd_only"):
        if st.get(key):
            body.append("#   %-30s %d\n" % (key, st[key]))
    body.append("#   %-30s %d\n" % ("flags labelled", len(rows)))
    for src in ("emevd_event", "emevd_batch", "esd_talk"):
        body.append("#   %-30s %d\n" % ("  via " + src, st.get("labelled:" + src, 0)))
    body.append("\t".join(cols) + "\n")
    for r in rows:
        body.append("\t".join(str(r[c]).replace("\t", " ") for c in cols) + "\n")
    text = "".join(body)
    if path:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return text


def validate_complete(rows, st):
    """Refuse a partial corpus before the tracked table is opened."""
    measured = (
        ("event files", st.get("files", 0), MIN_EVENT_FILES),
        ("events", st.get("events", 0), MIN_EVENTS),
        ("labelled flags", len(rows), MIN_LABELLED_FLAGS),
    )
    short = [f"{name}={actual} (minimum {floor})"
             for name, actual, floor in measured if actual < floor]
    if short:
        sys.exit(
            "FATAL: flag-name derivation is incomplete: " + ", ".join(short) + ". "
            "Refusing to overwrite greenfield/flag_names.tsv; an incomplete corpus is UNKNOWN, "
            "not evidence that the missing flags have no named setter."
        )


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--probe", action="store_true", help="counts + samples, write nothing")
    ap.add_argument("--emit", action="store_true", help="write greenfield/flag_names.tsv")
    args = ap.parse_args(argv)
    rows, st = build()

    validate_complete(rows, st)

    if st["events"] < 1000:
        sys.exit("FATAL: only %d events parsed -- EVENT_RE does not match this corpus." % st["events"])
    if not rows:
        sys.exit("FATAL: zero flags labelled. An empty table is a FAILURE, not 'no names found'.")
    named_pct = 100.0 * st["events_named"] / max(1, st["events"])
    if named_pct < 40:
        sys.exit("FATAL: only %.0f%% of events carry a name comment (77%% on 2026-07-28). This "
                 "corpus was decompiled without comments, and every label would be missing rather "
                 "than wrong -- which is the harder failure to notice." % named_pct)

    print("files %d | events %d (%d named, %.0f%%) | set sites %d | batch sites %d "
          "(%d dropped as too wide)"
          % (st["files"], st["events"], st["events_named"], named_pct, st["set_sites"],
             st["batch_sites"], st.get("batch_too_wide_dropped", 0)))
    print("flags labelled %d -- emevd_event %d, emevd_batch %d, esd_talk %d"
          % (len(rows), st.get("labelled:emevd_event", 0), st.get("labelled:emevd_batch", 0),
             st.get("labelled:esd_talk", 0)))
    multi = sum(1 for r in rows if r["setters"] > 1)
    print("flags with MORE THAN ONE named setter: %d (%.0f%%) -- for these the label is one of "
          "several, which is why `setters` is a column" % (multi, 100.0 * multi / len(rows)))
    # The known-true cases. If these stop resolving the scan has regressed, and a table of 30k
    # plausible labels is exactly the thing nobody would notice was wrong.
    by_flag = {r["flag"]: r for r in rows}
    print("known cases:")
    for flag, expect in ((3409, "NPC311"), (3708, "NPC320"), (1040530655, "")):
        got = by_flag.get(flag)
        ok = got and (expect in got["name_en"] or expect in got["name_ja"])
        print("   f%-12s %s  %s" % (flag, "ok " if ok else "MISS", got["name_en"] if got else "-"))
    if not all(by_flag.get(f) for f in (3409, 3708)):
        sys.exit("FATAL: the two hand-verified exemplars (f3409 Edgar, f3708 Roderika) no longer "
                 "resolve. Those are what license the other 30k labels.")
    if args.probe:
        print("--probe: nothing written")
        return 0
    if not args.emit:
        print("(pass --emit to write, --probe to look)")
        return 0
    emit(rows, st)
    print("wrote %s (%d rows)" % (os.path.relpath(OUT, ROOT), len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
