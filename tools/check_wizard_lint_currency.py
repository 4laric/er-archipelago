#!/usr/bin/env python3
"""check_wizard_lint_currency.py -- the wizard's LINT RULES must name options that still exist.

WHAT ROTTED. `wizard/options-metadata.json` is generated from the live `GFOptions` and gated by
`dump_options_metadata.py --check`, so the wizard's option SURFACE cannot drift. Its ~20 hand-written
CONFLICT RULES (`ERW.findings`) are ordinary JavaScript naming option keys and choice values as
string literals, and NOTHING checked those. On 2026-08-08 the shipped wizard told a player:

    WARN num_regions -- Only takes effect with ending_condition: capital.
    WARN num_regions -- Only takes effect with a lock-based World Logic.
    WARN num_regions_rune_source -- Ignored under spine ordering.

`ending_condition: capital` has not been a value for months (it is `region_locks` / `great_runes`),
`world_logic` is not an option at all, and `num_regions_rune_source` was deleted on 2026-07-02. An
audit found **20 dead keys and every value in the goal rules gone** -- the lint layer was describing
a world that no longer exists, in confident prose, to the one audience least able to tell.

WHY IT SURVIVED SO LONG. The rules "self-deactivate if their option keys vanish" -- `has(k)` returns
false and the rule quietly stops firing. That was designed as robustness and is exactly what hid the
rot: a rule that goes silent looks identical to a rule with nothing to say. Worse, the rules keyed on
a *value* (`goal === "capital"`) do not go silent at all; they compare against a string that can
never match, so they are dead code that still reads as live logic.

WHAT THIS GATE ASSERTS, therefore, is the thing the self-deactivation hid:

  1. every option key a rule names exists in the live metadata (or is an AP-core key the wizard
     itself declares), and
  2. every choice value a rule compares against is a real value of that option.

🛑 IT CANNOT CHECK WHETHER A RULE IS *TRUE*. A rule naming live options can still assert a
relationship the world stopped having. This gate makes the CHEAP half of that impossible, which is
the half that actually rotted; the expensive half stays a human review.

SECOND AUDIT, ADDED 2026-08-11: THE PAGE'S OWN OPTION READS, not just the lint rules.

`renderContribution` -- the whole "What are you putting into the multiworld?" card -- opened with

    const shuffle = !!v("item_shuffle");
    if (!shuffle) return <"there are no real items to send">;

`item_shuffle` was FROZEN ON (defaults.FROZEN_OPTIONS) on 2026-07-26, three weeks BEFORE that card
was written on 2026-08-08, so it is not on the yaml surface, `meta.byKey` has no entry, `v()`
returned `undefined`, and `!!undefined` is `false`. **The card never rendered a single number in its
life.** It shipped, it was deployed, and it answered every player with one sentence about a setting
the world no longer has. Nothing was red, because reading a key that does not exist is not an error
in JavaScript -- it is an `undefined` that means whatever the surrounding boolean says it means.

Same disease as the lint rules above (a reference to a dead option going SILENT rather than loud),
and the same disease as the client contract's `required=False` keys, where a key's ABSENCE was read
as its OFF state. So the rule is: **an absent option means its FROZEN value, never `off`.** A frozen
key may still be referenced, but only through a presence test that supplies that value --
`meta.byKey["k"] ? v("k") : <frozen default>` -- never through a bare `v("k")`, and never in a
control list, where it silently renders nothing while still being counted.

AP-free: it reads the committed metadata JSON, the wizard's own source, and `defaults.py` textually,
and never imports the world. Runs in the `generators` job.

Usage:
    python tools/check_wizard_lint_currency.py           # exit 1 on any dead reference
    python tools/check_wizard_lint_currency.py --list    # print what each rule names
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIZARD_HTML = os.path.join(ROOT, "wizard", "wizard.html")
DEFAULTS_PY = os.path.join(ROOT, "greenfield", "eldenring", "defaults.py")

PAGE_FIX = ("fix: an ABSENT option means its FROZEN value, never `off`. Read it as "
            '`meta.byKey["k"] ? ERW.getVal(meta, state, "k") : <the frozen value>`, or drop the '
            "reference. See defaults.FROZEN_OPTIONS for what the value is.")

FIX = ("fix: update or delete the rule in ERW.findings (wizard/wizard.html). A rule that names a "
       "dead option can never fire, and one that compares against a dead VALUE is dead code that "
       "still reads as live logic.")


def _wizard():
    return open(WIZARD_HTML, "r", encoding="utf-8", newline="").read()


def _metadata(html):
    m = re.search(r'<script id="er-options-metadata" type="application/json">\n(.*?)</script>',
                  html, re.S)
    if not m:
        sys.exit("[FAIL] no er-options-metadata blob in wizard.html")
    return json.loads(m.group(1))


def _findings_body(html):
    m = re.search(r'function findings\(meta, state\)\{(.*?)\n  \}\n', html, re.S)
    if not m:
        sys.exit("[FAIL] ERW.findings not found in wizard.html -- this gate is checking nothing.")
    return m.group(1)


def _ap_core_keys(html):
    """The AP-core options the wizard declares itself (accessibility, progression_balancing, ...).
    They are legitimate rule subjects but are not in the ER metadata blob."""
    m = re.search(r'const AP_CORE = \[(.*?)\n  \];', html, re.S)
    return set(re.findall(r'key:\s*"([a-z0-9_]+)"', m.group(1))) if m else set()


def audit():
    html = _wizard()
    meta = _metadata(html)
    body = _findings_body(html)
    by = {o["key"]: o for o in meta["options"]}
    ap_core = _ap_core_keys(html)
    known = set(by) | ap_core

    keys = set(re.findall(r'(?:has|v|set|warn|err|info)\(\s*"([a-z0-9_]+)"', body))
    keys |= set(re.findall(r'byKey\["([a-z0-9_]+)"\]', body))
    for grp in re.findall(r'of\s*\[([^\]]+)\]', body):          # for (const k of ["a","b"])
        keys |= set(re.findall(r'"([a-z0-9_]+)"', grp))

    # value comparisons. Two shapes: through a local alias (`goal === "x"`, assigned from v("k"))
    # and directly (`v("k") !== "x"`).
    aliases = dict(re.findall(r'const\s+(\w+)\s*=\s*has\("([a-z0-9_]+)"\)\s*\?\s*v\("\2"\)', body))
    pairs = set()
    for alias, key in aliases.items():
        for val in re.findall(r'\b%s\s*[!=]==\s*"([a-z0-9_]+)"' % alias, body):
            pairs.add((key, val))
        for grp in re.findall(r'\[([^\]]*)\]\.includes\(%s\)' % alias, body):
            for val in re.findall(r'"([a-z0-9_]+)"', grp):
                pairs.add((key, val))
    for key, val in re.findall(r'v\("([a-z0-9_]+)"\)\s*[!=]==\s*"([a-z0-9_]+)"', body):
        pairs.add((key, val))

    dead_keys = sorted(k for k in keys if k not in known)
    dead_vals = []
    for key, val in sorted(pairs):
        if key not in by:
            continue  # already reported as a dead key
        names = {c["name"] for c in (by[key].get("choices") or [])}
        if names and val not in names:
            dead_vals.append((key, val, sorted(names)))
    return keys, pairs, dead_keys, dead_vals


def _frozen_keys():
    """`defaults.FROZEN_OPTIONS` read TEXTUALLY -- this gate must stay importable without AP.

    Parsed rather than imported for the same reason check_release_notes.py parses APWORLD_VERSION:
    `greenfield.eldenring.defaults` is inside a package whose `__init__` reaches BaseClasses, and
    the `generators` job has no Archipelago.
    """
    if not os.path.isfile(DEFAULTS_PY):
        return None
    src = open(DEFAULTS_PY, "r", encoding="utf-8", newline="").read()
    m = re.search(r"^FROZEN_OPTIONS\s*=\s*\{(.*?)^\}", src, re.S | re.M)
    if not m:
        sys.exit("[FAIL] FROZEN_OPTIONS not found in %s -- this half of the gate is checking "
                 "nothing." % os.path.relpath(DEFAULTS_PY, ROOT))
    return set(re.findall(r'^\s*"([a-z0-9_]+)"\s*:', m.group(1), re.M))


def _function_bodies(body):
    """Every `function name(...){...}` body, plus whatever is left at the top level.

    Brace-matched rather than regexed: an option read and the presence test that protects it have
    to be in the SAME function for the protection to be real, and a regex cannot see a function's
    extent. Nested functions are yielded by their outer one too, which is the forgiving direction --
    a guard in the enclosing scope genuinely does protect a read in a closure below it.
    """
    out = []
    covered = []
    for m in re.finditer(r'\bfunction\s+\w+\s*\(', body):
        i = body.find("{", m.end() - 1)
        if i < 0:
            continue
        depth, j = 0, i
        while j < len(body):
            if body[j] == "{":
                depth += 1
            elif body[j] == "}":
                depth -= 1
                if not depth:
                    break
            j += 1
        out.append(body[i:j + 1])
        covered.append((m.start(), j + 1))
    # the residue: top-level statements and arrow functions, which have no `function` keyword
    top, last = [], 0
    for a, b in sorted(covered):
        if a > last:
            top.append(body[last:a])
        last = max(last, b)
    top.append(body[last:])
    out.append("".join(top))
    return out


def audit_page():
    """Every option key the PAGE reads, classified. Returns (reads, guarded, listed, problems)."""
    html = _wizard()
    meta = _metadata(html)
    live = {o["key"] for o in meta["options"]}
    known = live | _ap_core_keys(html)
    frozen = _frozen_keys()

    # Strip the JSON blobs first: they legitimately contain every key name in the world, and one of
    # them is the metadata this gate is comparing against.
    body = re.sub(r'<script id="[a-z-]+" type="application/json">.*?</script>', "", html, flags=re.S)

    reads, guarded, unguarded = set(), set(), set()
    # PER FUNCTION, not per page. A presence test somewhere else in the file does not protect a
    # bare read here, and scoping this to the whole page is how the first version of this gate
    # passed its own negative test: reverting the fixed line still left the `meta.byKey` lookup on
    # the line above it, and "guarded anywhere" happily excused the bug it was written for.
    for chunk in _function_bodies(body):
        r = set(re.findall(r'(?<![.\w])v\(\s*"([a-z0-9_]+)"\s*\)', chunk))
        r |= set(re.findall(r'ERW\.getVal\(\s*meta,\s*state,\s*"([a-z0-9_]+)"\s*\)', chunk))
        g = set(re.findall(r'meta\.byKey\[\s*"([a-z0-9_]+)"\s*\]', chunk))
        reads |= r
        guarded |= g
        unguarded |= (r - g)
    listed = set()
    for name, grp in re.findall(r'const (SEED_SIZE_OPTIONS|[A-Z_]*OPTIONS) = \[(.*?)\];', body, re.S):
        listed |= set(re.findall(r'"([a-z0-9_]+)"', grp))

    problems = []
    for k in sorted(reads | guarded | listed):
        if k in known:
            continue
        if frozen is not None and k in frozen:
            # GUARDED is the whole distinction. `meta.byKey["k"] ? v("k") : <frozen value>` reads
            # the key AND supplies the frozen value when it is absent, which is correct and is the
            # pattern this gate is steering toward -- so a key that appears in a presence test
            # anywhere on the page is fine, however it is read. What is never fine is reading it
            # with nothing to fall back on.
            if k in unguarded:
                problems.append((k, "read with a bare v()/getVal and no presence test, so it "
                                    "yields `undefined` and reads as OFF -- it is FROZEN, not off"))
            elif k in listed:
                problems.append((k, "listed as a control, but it is FROZEN off the yaml surface, so "
                                    "it renders no row while still being counted in the heading"))
            # guarded-only is the sanctioned way to reference a frozen key: nothing to report.
        else:
            problems.append((k, "is not an option at all -- not on the surface, not Archipelago "
                                "core, and not frozen"))
    return reads, guarded, listed, problems


def main(argv):
    keys, pairs, dead_keys, dead_vals = audit()
    reads, guarded, listed, page_problems = audit_page()
    if "--list" in argv:
        print("option keys read by the page (%d): %s" % (len(reads), ", ".join(sorted(reads))))
        print("read behind a presence test (%d): %s" % (len(guarded), ", ".join(sorted(guarded))))
        print("option keys named by ERW.findings (%d):" % len(keys))
        for k in sorted(keys):
            print("   ", k)
        print("value comparisons (%d):" % len(pairs))
        for k, v in sorted(pairs):
            print("    %s == %r" % (k, v))
        return 0

    if not keys:
        # A refactor that renames the helpers would leave the regexes matching nothing, and this
        # gate would pass while checking zero rules. Fail instead.
        sys.exit("[FAIL] parsed ZERO option references out of ERW.findings -- the gate has stopped "
                 "seeing the rules it exists to check. Update the patterns, do not ignore this.")
    if not reads:
        sys.exit("[FAIL] parsed ZERO option reads out of the wizard page -- the page audit has "
                 "stopped seeing the code it exists to check. Update the patterns.")

    bad = False
    if dead_keys:
        bad = True
        print("[STALE] %d option key(s) named by lint rules no longer exist:" % len(dead_keys))
        for k in dead_keys:
            print("   ", k)
    if dead_vals:
        bad = True
        print("[STALE] %d choice value(s) compared against no longer exist:" % len(dead_vals))
        for k, v, real in dead_vals:
            print("    %s == %r  (real values: %s)" % (k, v, ", ".join(real)))
    if page_problems:
        print("[STALE] %d option key(s) the PAGE references cannot do what the code assumes:"
              % len(page_problems))
        for k, why in page_problems:
            print("    %s -- %s" % (k, why))
        print(PAGE_FIX)
        return 1
    if bad:
        print(FIX)
        return 1
    print("[ok] wizard lint rules are current (%d option(s), %d value comparison(s) checked); "
          "page reads %d option(s), %d behind a presence test"
          % (len(keys), len(pairs), len(reads), len(guarded)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
