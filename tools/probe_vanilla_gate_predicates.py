#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_vanilla_gate_predicates.py -- WHAT does the game read when the player opens a vanilla door?

READ-ONLY. Writes nothing, emits no table, changes no data. Run it, paste the output.

WHY THIS EXISTS
---------------
The client grants goods into the inventory. Some vanilla gates do not read the inventory: they read
a dedicated "obtained" event flag that a raw grant never trips. When that happens the player holds
the key, the door stays shut, and NOTHING tells anyone -- not the player, not us. Proven in game
once (Rold Medallion / flag 400001, seed 45997544150175068277, 2026-06-19: the lift stayed sealed
with the medallion in the bag), and again in a different guise as the whetblade affinity flags
(#240).

World issue #276 is the open instance, reported by a player on 0.2.18:

    "I had 2 great runes, but couldn't enter leyndell itself to make progress. Then later I got the
     raya lucaria key, but this one also didn't give me acces to raya lucaria itself."

features/leyndell_gate.py ships the capital with no client half, on the strength of one uncited
clause -- "the runes arrive as AP items and the client's key-item grant makes the game count them".
What the client actually writes is keyitems.rs KEY_ITEM_ACQUIRE_FLAGS -> 191-196, described there as
the RESTORED flags (Divine-Tower common event 90005110) so a rune is usable at an altar. Restored is
not the same predicate as the capital's entry condition, and nobody has read the gate.

🔥 THE SHARPEST REASON TO RUN THIS. 191-196 are ALSO THE GOODS IDS. item_ids.py:863 gives
"Godrick's Great Rune" as 1073742015 = 0x40000000 | 191. So the restored-rune goods id and the
claimed restored-rune flag id are the same six numbers -- either a real coincidence in FromSoft's
data, or the signature of a goods id written into a flag table. `flag_names.tsv` naming 171-177 and
200 while finding nothing for 191-196 leans the wrong way. Section 3 separates the two id spaces by
COUNTING each usage independently, which is the only way to tell them apart.

WHAT IT REPORTS
---------------
  1. CORPUS   -- files, events, and a truncation guard. A short read must not look like a small game.
  2. VOCABULARY -- every call in the corpus whose name mentions item/inventory/goods/possession,
     with counts and a sample argument shape. We do NOT know what the possession verb is called, and
     guessing it is the failure probe_esd_gestures.py was written to avoid: a regex that matches
     nothing returns a confident empty result that reads exactly like "the gate is flag-based".
  3. GREAT RUNES -- for each of 191-196, counted SEPARATELY: sites where it is SET as a flag, READ
     as a flag, and passed to an item/inventory verb. Plus the full body of --rune-event (90005110)
     so its citation can be checked rather than trusted.
  4. ACADEMY KEY -- the same three counts for goods 8109 (Academy Glintstone Key = 1073749933 -
     0x40000000), plus every 4000xx-band flag that co-occurs in an event mentioning it. The Rold
     Medallion (goods 8107 / flag 400001) is scanned alongside as a POSITIVE CONTROL: we know what
     that one does, so if the scan cannot re-find it, the scan is broken and no other line is
     evidence of anything.
  5. ESD -- the same vocabulary pass over ESDLang-decompiled talk scripts, if present. The Academy
     Gate Town seal may be an ESD interaction rather than an EMEVD event, and an EMEVD-only read
     would report a confident nothing.
  6. VERDICT -- one plain sentence per question, and a NEGATIVE is stated as loudly as a positive.
     "Nothing in the corpus reads 191-196" is a real and useful answer: it would mean the client has
     been writing bits that do nothing.

🛑 WHAT THIS DOES NOT DO. It does not classify anything and it does not touch key_item_gates.tsv.
Its output is the evidence a human writes into that table. Do NOT add a flag to keyitems.rs on the
strength of a co-occurrence: #240 is the case where setting the obvious flag silently collected four
live checks.

INPUT
-----
  EMEVD: the DarkScript3-decompiled corpus datamine_flag_names.py already reads --
         elden_ring_artifacts\\event\\*.emevd.dcx.js, or set ER_EVENT_DIR, or --eventdir.
  ESD  : optional, ESDLang-decompiled Python (as datamine_esd_gates.py / probe_esd_gestures.py):
         ESDLang.exe -er -esddir elden_ring_artifacts\\talk -writepy elden_ring_artifacts\\esd_py\\%e.py

USAGE (PowerShell, from the repo root)
--------------------------------------
    python tools\\probe_vanilla_gate_predicates.py
    python tools\\probe_vanilla_gate_predicates.py --pydir elden_ring_artifacts\\esd_py
    python tools\\probe_vanilla_gate_predicates.py --context 3 --max-sites 12
    python tools\\probe_vanilla_gate_predicates.py --selftest     # no corpus needed
"""
from __future__ import annotations

import argparse
import collections
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EVT_DEFAULT = os.environ.get("ER_EVENT_DIR") or os.path.join(ROOT, "elden_ring_artifacts", "event")
PYDIR_DEFAULT = os.path.join(ROOT, "elden_ring_artifacts", "esd_py")

# --- the ids under test. Every one is CITED, none is typed from memory. -------------------------
# Restored Great Rune goods ids: item_ids.py ITEM_CATALOG, AP id 0x40000000 | N (1073742015..20).
GREAT_RUNE_IDS = list(range(191, 197))
# Academy Glintstone Key: item_ids.py:18 'Academy Glintstone Key': 1073749933 -> 1073749933 - 2**30.
ACADEMY_KEY_GOODS = 1073749933 - (1 << 30)
# POSITIVE CONTROL. Rold Medallion goods 8107, gate flag 400001 -- the one case proven in game
# (itemevents.txt f15(400001), "checks for Rold Medallion for Melina purposes").
ROLD_GOODS, ROLD_FLAG = 8107, 400001
# The event keyitems.rs cites for the restored-rune flag writes.
RUNE_EVENT_DEFAULT = 90005110
# Dedicated obtained-flag band for key/quest items (er-keyitem-obtained-flags).
OBTAINED_BAND = (400000, 400100)

# --- corpus grammar. EVENT_RE / SET_RE are datamine_flag_names.py's, deliberately: two readers of
# the same corpus disagreeing about where an event begins is a bug neither of them can see. -------
EVENT_RE = re.compile(
    r"(?:^//[ \t]*(?P<name>.*?)\r?\n)?\$Event\((?P<id>\d+),\s*\w+,\s*function\([^)]*\)\s*\{", re.M)
SET_RE = re.compile(r"\b(?:SetEventFlagID|SetNetworkconnectedEventFlagID)\s*\(\s*(\d+)\s*,")
# A flag READ. DarkScript3 spells these several ways; match the FAMILY, not one spelling, and report
# which spelling was seen so a missing one is visible rather than silently absent.
# 🛑 The negative lookahead is load-bearing: `SetEventFlagID` contains "EventFlag", so a naive
# \w*EventFlag\w* counts every WRITE as a READ -- and "does anything read 191-196?" is the entire
# question this probe exists to answer. Caught by the selftest, which asserts READ(191) == 0 in a
# corpus where 191 is only ever written.
READ_RE = re.compile(r"\b(?!(?:Batch)?Set)(\w*EventFlag\w*)\s*\(\s*([^)]*)\)")
CALL_RE = re.compile(r"\b([A-Z]\w+)\s*\(\s*([^)]*)\)")
# 🛑 RANGE READS. The first run of this probe (2026-08-01) reported ZERO sites for flags 191-196 in a
# 589-file corpus and I nearly read that as "the client writes bits nothing consults". It is not what
# it means. The corpus reads great-rune flags by BAND --
#     CountEventFlags(TargetEventFlagType.EventFlag, 190, 199)
# -- so the only literals on the line are the ENDPOINTS, and an id strictly inside the band appears
# nowhere. datamine_flag_names.py already knew this and expands BatchSetEventFlags; this probe did
# not, and a scan that cannot see the read cannot answer "does anything read it".
RANGE_CALL_RE = re.compile(r"Batch|Range|Count", re.I)
# Wider than this is a bulk sweep, and expanding it would manufacture hundreds of confident hits off
# one line. Same reasoning and same posture as datamine_flag_names.MAX_BATCH.
MAX_BAND = 256
# Common-event INITIALIZERS. $Event(90005110) sets `SetEventFlagID(eventFlagId, ON)` -- a PARAMETER.
# The concrete per-rune flag ids are the literal arguments at the call sites, which carry no
# "EventFlag" in the name and so are invisible to both SET_RE and READ_RE.
INIT_RE = re.compile(r"\b(Initiali[sz]e\w*Event\w*)\s*\(\s*([^)]*)\)")
MAP_RE = re.compile(r"^(m\d\d_\d\d_\d\d_\d\d|common(?:_func)?)\.emevd")
# The vocabulary question: what is a possession check CALLED here? Cast wide on purpose.
ITEMISH = re.compile(r"item|inventory|goods|possess|have|own|count", re.I)
INT_RE = re.compile(r"-?\d+")


class Site:
    __slots__ = ("map_id", "event_id", "event_name", "line", "text")

    def __init__(self, map_id, event_id, event_name, line, text):
        self.map_id, self.event_id, self.event_name = map_id, event_id, event_name
        self.line, self.text = line, text

    def __str__(self):
        name = (self.event_name or "<unnamed>")[:70]
        return "    %-22s $Event(%-9d) %s\n        %s" % (self.map_id, self.event_id, name, self.text)


def load_events(event_dir):
    """-> [(map_id, event_id, event_name, body)]. Fails loudly; an empty corpus is a FAILURE."""
    files = sorted(glob.glob(os.path.join(event_dir, "*.emevd.dcx.js")))
    if not files:
        sys.exit("FATAL: no *.emevd.dcx.js under %s.\n"
                 "Set ER_EVENT_DIR / pass --eventdir, or run\n"
                 "  python tools/gen_inputs.py --ensure elden_ring_artifacts\n"
                 "Refusing to report on an empty corpus -- an empty result is a FAILURE, not "
                 "'the gate does not check anything'." % event_dir)
    out = []
    for path in files:
        base = os.path.basename(path)
        m = MAP_RE.match(base)
        map_id = m.group(1) if m else base.split(".")[0]
        text = open(path, encoding="utf-8", errors="replace").read()
        if text.count("{") != text.count("}"):
            sys.exit("FATAL: %s has unbalanced braces (%d/%d) -- a truncated read, not a corpus."
                     % (base, text.count("{"), text.count("}")))
        marks = list(EVENT_RE.finditer(text))
        for i, mk in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
            out.append((map_id, int(mk.group("id")), (mk.group("name") or "").strip(),
                        text[mk.end():end]))
    return out, len(files)


def _lines(body):
    for n, line in enumerate(body.splitlines(), 1):
        s = line.strip()
        if s:
            yield n, s


def scan(events, ids):
    """Count each id in THREE id spaces, separately. That separation is the whole point: a number
    that is both a goods id and a flag id cannot be told apart by grepping for the number."""
    as_set = collections.defaultdict(list)     # id -> [Site]  flag WRITE
    as_read = collections.defaultdict(list)    # id -> [Site]  flag READ
    as_item = collections.defaultdict(list)    # id -> [Site]  argument to an item-ish call
    vocab = collections.Counter()
    vocab_sample = {}
    read_spellings = collections.Counter()
    st_ranges = collections.Counter()      # (verb, lo, hi) -> sites. The bands, named.
    inits = collections.defaultdict(list)  # common-event id -> [(Site, [literal args])]
    for map_id, eid, name, body in events:
        for lineno, line in _lines(body):
            site = lambda: Site(map_id, eid, name, lineno, line)
            for sm in SET_RE.finditer(line):
                f = int(sm.group(1))
                if f in ids:
                    as_set[f].append(site())
            for rm in READ_RE.finditer(line):
                fn, args = rm.group(1), rm.group(2)
                read_spellings[fn] += 1
                toks = [int(t) for t in INT_RE.findall(args)]
                for tok in toks:
                    if tok in ids:
                        as_read[tok].append(site())
                # A BAND read covers every id between its endpoints, not just the endpoints.
                if RANGE_CALL_RE.search(fn) and len(toks) >= 2:
                    lo, hi = toks[-2], toks[-1]
                    if lo <= hi and hi - lo <= MAX_BAND:
                        st_ranges[(fn, lo, hi)] += 1
                        for i in range(lo, hi + 1):
                            if i in ids and lo < i < hi:      # endpoints already counted above
                                as_read[i].append(site())
            for im in INIT_RE.finditer(line):
                toks = [int(t) for t in INT_RE.findall(im.group(2))]
                for t in toks:
                    inits[t].append((site(), toks))
            for cm in CALL_RE.finditer(line):
                fn, args = cm.group(1), cm.group(2)
                if not ITEMISH.search(fn):
                    continue
                vocab[fn] += 1
                vocab_sample.setdefault(fn, "%s(%s)" % (fn, args.strip()[:90]))
                for tok in INT_RE.findall(args):
                    if int(tok) in ids:
                        as_item[int(tok)].append(site())
    return as_set, as_read, as_item, vocab, vocab_sample, read_spellings, st_ranges, inits


def show(title, ids, as_set, as_read, as_item, max_sites):
    print("\n%s" % title)
    print("  %-10s %8s %8s %8s" % ("id", "SET", "READ", "ITEM-ARG"))
    for i in ids:
        print("  %-10d %8d %8d %8d" % (i, len(as_set[i]), len(as_read[i]), len(as_item[i])))
    for label, bucket in (("SET as a flag", as_set), ("READ as a flag", as_read),
                          ("passed to an item-ish call", as_item)):
        sites = [(i, s) for i in ids for s in bucket[i]]
        if not sites:
            print("  -- no site %s. 🛑 State this in the verdict; it is a finding." % label)
            continue
        print("  -- %d site(s) %s:" % (len(sites), label))
        for i, s in sites[:max_sites]:
            print("   [%d]\n%s" % (i, s))
        if len(sites) > max_sites:
            print("    ... %d more (raise --max-sites)" % (len(sites) - max_sites))


def dump_event(events, want, context):
    hits = [e for e in events if e[1] == want]
    print("\n4. THE CITED EVENT -- $Event(%d), which keyitems.rs names as the source of the "
          "restored-rune flag writes" % want)
    if not hits:
        print("  🛑 NOT FOUND in the corpus. The citation in keyitems.rs cannot be checked, which "
              "is itself the answer to why 191-196 are unnamed in flag_names.tsv.")
        return
    for map_id, eid, name, body in hits:
        print("  %s $Event(%d) // %s" % (map_id, eid, name or "<unnamed>"))
        lines = [l for _, l in _lines(body)]
        for l in lines[:context if context > 0 else len(lines)]:
            print("      %s" % l)
        if 0 < context < len(lines):
            print("      ... %d more lines (raise --context, 0 = whole body)" % (len(lines) - context))


def show_bands(st_ranges, ids, max_rows=25):
    """Every BAND read in the corpus, and which ids under test fall inside one.

    This section exists because its absence produced a wrong reading on the first run: a band read
    puts no literal on the line for the ids it covers, so "0 READ sites" meant "nobody looked in the
    right shape", not "nobody reads this flag"."""
    print("\n3e. BAND READS -- flag ranges the corpus counts/tests wholesale")
    if not st_ranges:
        print("  (none seen -- if that is a surprise, check RANGE_CALL_RE against the verb list in 2)")
        return
    rows = sorted(st_ranges.items(), key=lambda kv: -kv[1])
    for (fn, lo, hi), n in rows[:max_rows]:
        covered = sorted(i for i in ids if lo <= i <= hi)
        mark = ("  <-- COVERS ids under test: %s" % covered) if covered else ""
        print("  %-34s %5d-%-8d %5d site(s)%s" % (fn, lo, hi, n, mark))
    if len(rows) > max_rows:
        print("  ... %d more" % (len(rows) - max_rows))


def show_inits(inits, want, max_rows=20):
    """Literal arguments at every call site that initializes the cited common event.

    $Event(90005110) writes `SetEventFlagID(eventFlagId, ON)` -- a PARAMETER. The concrete per-rune
    flag id is here, at the caller, and nowhere else."""
    print("\n4b. INITIALIZER ARGUMENTS for common event %d -- where the parameter gets its value" % want)
    hits = inits.get(want) or []
    if not hits:
        print("  🛑 no initializer call mentions %d. Either the corpus spells it differently (check\n"
              "  INIT_RE against the verb list) or the event is invoked some other way. Do NOT read\n"
              "  this as 'the flags do not exist'." % want)
        return
    print("  %d call site(s). Each row is the literal arg list; the flag id is one of these." % len(hits))
    for site, toks in hits[:max_rows]:
        print("%s\n        args=%s" % (site, toks))
    if len(hits) > max_rows:
        print("  ... %d more (raise the cap)" % (len(hits) - max_rows))


def scan_esd(pydir, ids):
    print("\n5. ESD (talk scripts) -- the Academy seal may be an interaction, not an event")
    files = sorted(glob.glob(os.path.join(pydir, "*.py")))
    if not files:
        print("  SKIPPED: no *.py under %s. Decompile with ESDLang and re-run with --pydir if the\n"
              "  EMEVD pass above found nothing for the Academy key -- an EMEVD-only read reports a\n"
              "  confident nothing for a gate that lives in ESD." % pydir)
        return
    vocab, sample, hits = collections.Counter(), {}, collections.defaultdict(list)
    for path in files:
        base = os.path.basename(path)
        for n, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
            line = line.strip()
            for cm in CALL_RE.finditer(line):
                fn, args = cm.group(1), cm.group(2)
                if not ITEMISH.search(fn):
                    continue
                vocab[fn] += 1
                sample.setdefault(fn, "%s(%s)" % (fn, args.strip()[:90]))
                for tok in INT_RE.findall(args):
                    if int(tok) in ids:
                        hits[int(tok)].append("    %s:%d  %s" % (base, n, line[:110]))
    print("  files %d; item-ish verbs %d" % (len(files), len(vocab)))
    for fn, n in vocab.most_common(20):
        print("    %-42s %5d   e.g. %s" % (fn, n, sample[fn]))
    if not hits:
        print("  -- no id under test appears in any item-ish ESD call.")
    for i in sorted(hits):
        print("  [%d] %d site(s):" % (i, len(hits[i])))
        for s in hits[i][:6]:
            print(s)


SELFTEST_CORPUS = """\
// テスト_大ルーン修復 -- Test_Great rune restoration
$Event(90005110, Restart, function(X0_4) {
    SetEventFlagID(191, ON);
    SetEventFlagID(192, ON);
});
// 王都大門 -- Capital main gate
$Event(11005500, Default, function() {
    PlayerHasItem(ItemType.Goods, 191);
    flag = EventFlag(400001);
    SetEventFlagID(400072, ON);
    WaitFor(CountEventFlags(TargetEventFlagType.EventFlag, 190, 199) >= 2);
});
// 大ルーン初期化 -- Great rune init
$Event(0, Default, function() {
    InitializeCommonEvent(0, 90005110, 195, 8151, 100, 60210);
});
"""


def selftest():
    """Prove the GRAMMAR works before anyone trusts a number it produced. No corpus needed.

    This exists because the tool was written without access to the real artifacts: a regex that
    silently matches nothing is indistinguishable from a game that checks nothing, and that is
    precisely the confusion this probe was built to end.
    """
    import tempfile
    ok = True
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "common.emevd.dcx.js")
        open(p, "w", encoding="utf-8").write(SELFTEST_CORPUS)
        events, nfiles = load_events(d)
        checks = [
            ("3 events parsed", len(events) == 3),
            ("event ids read", sorted(e[1] for e in events) == [0, 11005500, 90005110]),
            ("comment captured", any("Capital main gate" in (e[2] or "") for e in events)),
        ]
        as_set, as_read, as_item, vocab, _sample, spellings, bands, inits = scan(
            events, set(GREAT_RUNE_IDS) | {ROLD_FLAG, 400072})
        checks += [
            ("flag WRITE found (191)", len(as_set[191]) == 1),
            ("flag READ found (400001)", len(as_read[ROLD_FLAG]) == 1),
            # 400072 is WRITTEN once and sits outside every band, so it isolates the one thing a
            # naive \\w*EventFlag\\w* gets wrong: counting SetEventFlagID as a read.
            ("a WRITE is not counted as a READ", len(as_set[400072]) == 1 and len(as_read[400072]) == 0),
            ("band does not double-count a write", len(as_set[191]) == 1 and len(as_read[191]) == 1),
            ("item-arg found (191)", len(as_item[191]) == 1),
            ("191 counted in BOTH spaces", len(as_set[191]) == 1 and len(as_item[191]) == 1),
            ("item-ish verb discovered", "PlayerHasItem" in vocab),
            # The two regressions from the first live run. 193 appears NOWHERE as a literal; it is
            # only reachable by expanding the 190-199 band and by reading the initializer args.
            ("band read reaches an interior id", len(as_read[193]) == 1),
            ("band recorded with its endpoints", ("CountEventFlags", 190, 199) in bands),
            ("initializer args captured", any(195 in toks for _s, toks in inits.get(90005110, []))),
            ("read spelling recorded", any("EventFlag" in s for s in spellings)),
        ]
    for label, good in checks:
        print("  %-34s %s" % (label, "ok" if good else "FAIL"))
        ok = ok and good
    print("\nselftest: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--eventdir", default=EVT_DEFAULT, help="decompiled EMEVD (*.emevd.dcx.js)")
    ap.add_argument("--pydir", default=PYDIR_DEFAULT, help="ESDLang-decompiled talk scripts (*.py)")
    ap.add_argument("--rune-event", type=int, default=RUNE_EVENT_DEFAULT)
    ap.add_argument("--init-of", type=int, default=None,
                    help="dump initializer args for this common event (default: --rune-event)")
    ap.add_argument("--context", type=int, default=40, help="lines of the cited event to dump (0=all)")
    ap.add_argument("--max-sites", type=int, default=8)
    ap.add_argument("--selftest", action="store_true", help="check the grammar; no corpus needed")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()

    events, nfiles = load_events(a.eventdir)
    ids = set(GREAT_RUNE_IDS) | {ACADEMY_KEY_GOODS, ROLD_GOODS, ROLD_FLAG}
    ids |= set(range(*OBTAINED_BAND))
    as_set, as_read, as_item, vocab, sample, spellings, bands, inits = scan(events, ids)

    print("1. CORPUS")
    print("  files %d   events %d   dir %s" % (nfiles, len(events), a.eventdir))

    print("\n2. VOCABULARY -- what an item/inventory check is CALLED in this corpus")
    if not vocab:
        print("  🛑 NOTHING matched /item|inventory|goods|possess|have|own|count/. Either the corpus\n"
              "  is not what we think it is, or the decompiler names these differently -- do not read\n"
              "  section 3's zero ITEM-ARG counts as 'the gate is flag-based' until this is resolved.")
    for fn, n in vocab.most_common(25):
        print("  %-44s %6d   e.g. %s" % (fn, n, sample[fn]))
    print("  flag-read spellings seen: %s"
          % ", ".join("%s(%d)" % (k, v) for k, v in spellings.most_common(8)) or "(none)")

    show("3a. GREAT RUNES -- goods ids AND claimed restored-flag ids are the same numbers",
         GREAT_RUNE_IDS, as_set, as_read, as_item, a.max_sites)
    print("  🔎 Read the three columns as three id spaces. SET>0 with READ=0 means the client writes\n"
          "     a bit nothing consults. ITEM-ARG>0 with READ=0 means the gate is possession-based and\n"
          "     the flag writes are beside the point.")

    show_bands(bands, ids)
    dump_event(events, a.rune_event, a.context)
    show_inits(inits, a.init_of if a.init_of is not None else a.rune_event)

    show("3b. ACADEMY GLINTSTONE KEY (goods %d)" % ACADEMY_KEY_GOODS,
         [ACADEMY_KEY_GOODS], as_set, as_read, as_item, a.max_sites)
    show("3c. POSITIVE CONTROL -- Rold Medallion goods %d / gate flag %d (known: flag-gated)"
         % (ROLD_GOODS, ROLD_FLAG), [ROLD_GOODS, ROLD_FLAG], as_set, as_read, as_item, a.max_sites)
    if not (as_read[ROLD_FLAG] or as_set[ROLD_FLAG]):
        print("  🛑 THE CONTROL FAILED. We know 400001 gates the Rold lift; a scan that cannot see it\n"
              "     cannot see the two doors we came for either. Stop and fix the scan; nothing above\n"
              "     is evidence.")

    band = [i for i in range(*OBTAINED_BAND) if as_set[i] or as_read[i] or as_item[i]]
    print("\n3d. DEDICATED OBTAINED-FLAG BAND %d-%d -- ids with any site: %s"
          % (OBTAINED_BAND[0], OBTAINED_BAND[1] - 1, band or "(none)"))

    scan_esd(a.pydir, ids)

    print("\n6. VERDICT -- answer each in one sentence, and paste this whole output into #276")
    print("  Q1 do flags 191-196 exist as flags?      SET %d site(s), READ %d site(s)"
          % (sum(len(as_set[i]) for i in GREAT_RUNE_IDS),
             sum(len(as_read[i]) for i in GREAT_RUNE_IDS)))
    print("  Q2 does anything gate on rune POSSESSION? ITEM-ARG %d site(s)"
          % sum(len(as_item[i]) for i in GREAT_RUNE_IDS))
    print("  Q3 the Academy key: flag or possession?   SET %d READ %d ITEM-ARG %d"
          % (len(as_set[ACADEMY_KEY_GOODS]), len(as_read[ACADEMY_KEY_GOODS]),
             len(as_item[ACADEMY_KEY_GOODS])))
    print("  Q4 control (Rold 400001) visible?         SET %d READ %d"
          % (len(as_set[ROLD_FLAG]), len(as_read[ROLD_FLAG])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
