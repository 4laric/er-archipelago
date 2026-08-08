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

AP-free: it reads the committed metadata JSON and the wizard's own source, and never imports the
world. Runs in the `generators` job.

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


def main(argv):
    keys, pairs, dead_keys, dead_vals = audit()
    if "--list" in argv:
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
    if bad:
        print(FIX)
        return 1
    print("[ok] wizard lint rules are current (%d option(s), %d value comparison(s) checked)"
          % (len(keys), len(pairs)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
