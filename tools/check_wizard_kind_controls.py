#!/usr/bin/env python3
"""check_wizard_kind_controls.py -- every option KIND the dumper can emit has a control to draw it.

WHAT THIS CLOSES (#571). `tools/dump_options_metadata.py:describe()` classifies every option into a
`kind`, and `wizard/wizard.html:controlFor()` branches on that string to build a widget. The branch
list ends in an `else` that makes a plain `<input type="text" value=v>` -- so a kind nobody wrote a
branch for does not fail, it DEGRADES, and it degrades into the one widget that can hold anything.

`curated_filler` is `kind: "dict"`. It fell into that `else`, `value:` coerced the recipe with
`String()`, and the player was shown a text box reading literally `[object Object]`. Worse than the
render: `commit(t.value)` then stored a STRING, and `buildYaml` quoted it, so touching the box
downloaded `curated_filler: "[object Object]"` -- a scalar where the world wants a mapping.

Nothing caught it for the same reason nothing catches any of these: every gate we had asks whether
what IS drawn is correct (`check_wizard_keymeta_js` -- no class missing from the grid;
`check_wizard_lint_currency` -- no rule naming a dead key). None asked whether something was drawn
at all. This one does, and it is the cheap direction: a set difference over two source files.

DELIBERATELY AP-FREE AND IMPORT-FREE, like check_release_notes.py -- both inputs are text in this
repo, so this runs in any job rather than only in the one that can import Archipelago. That matters:
the drift gate that WOULD have shown the empty `valid_keys` (`dump_options_metadata.py --check`)
needs an AP checkout, and a gate that can only run in one job is a gate that gets skipped.

Three assertions:

1. **Every kind the dumper emits is named by a branch in `controlFor`**, except the documented
   fallback (`text`) -- so the `else` may only ever catch the kind it was written for.
2. **No option in the SHIPPED metadata carries an unhandled kind.** Assertion 1 reads the dumper's
   source; this reads what the page will actually load, so a refactor that moves the kind literals
   out of reach of the regex cannot make this file pass vacuously.
3. **A `dict` option declares `valid_keys`.** The dumper fills them from the class; when the class
   never set them the wizard has nothing to enumerate and can only draw the keys the DEFAULT happens
   to use -- for `curated_filler` that is 9 of 16 categories, i.e. a control that cannot express
   something the option accepts. That is how #571 stayed unfixable rather than merely ugly.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUMPER = os.path.join(ROOT, "tools", "dump_options_metadata.py")
WIZARD = os.path.join(ROOT, "wizard", "wizard.html")
META = os.path.join(ROOT, "wizard", "options-metadata.json")

# The one kind the `else` in controlFor is allowed to catch. Named here rather than inferred,
# because "what the fallback is for" is a decision and not something a regex can read; if the
# fallback is ever meant to cover a second kind, that is a review conversation, not a silent pass.
FALLBACK_KINDS = {"text"}

EMITS = re.compile(r'd\["kind"\]\s*=\s*"([a-z_]+)"')
HANDLES = re.compile(r'o\.kind\s*===\s*"([a-z_]+)"')


def read(path):
    if not os.path.exists(path):
        sys.exit("[FAIL] %s not found" % os.path.relpath(path, ROOT))
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def main():
    emitted = set(EMITS.findall(read(DUMPER)))
    handled = set(HANDLES.findall(read(WIZARD)))
    if not emitted:
        sys.exit('[FAIL] no `d["kind"] = "..."` assignments found in '
                 'tools/dump_options_metadata.py -- this gate has stopped reading its own input')
    if not handled:
        sys.exit('[FAIL] no `o.kind === "..."` branches found in wizard/wizard.html -- '
                 'this gate has stopped reading its own input')

    print("check_wizard_kind_controls: dumper emits %d kind(s): %s"
          % (len(emitted), ", ".join(sorted(emitted))))
    print("  controlFor names %d: %s" % (len(handled), ", ".join(sorted(handled))))

    fail = []
    missing = emitted - handled - FALLBACK_KINDS
    if missing:
        fail.append("kind(s) %s are emitted by dump_options_metadata.describe() and have NO branch "
                    "in wizard.html:controlFor(). They would silently render as a text input, and "
                    "editing one writes its string straight into the player's yaml (#571). Add a "
                    "branch, or -- if a text box really is right for it -- add it to FALLBACK_KINDS "
                    "here with the reason." % ", ".join(sorted(missing)))

    stray = handled - emitted
    if stray:
        # Not fatal: a branch for a kind nothing emits is dead code, not a trap for a player.
        print("  note: controlFor branches on %s, which the dumper never emits (dead branch)"
              % ", ".join(sorted(stray)))

    meta = json.loads(read(META))
    opts = meta.get("options", [])
    if not opts:
        sys.exit("[FAIL] wizard/options-metadata.json carries no options")
    bad = sorted({o["key"] for o in opts if o.get("kind") not in handled | FALLBACK_KINDS})
    if bad:
        fail.append("shipped option(s) %s carry a kind with no control: %s"
                    % (", ".join(bad),
                       ", ".join(sorted({o.get("kind") for o in opts if o["key"] in bad}))))

    keyless = sorted(o["key"] for o in opts
                     if o.get("kind") == "dict" and not o.get("valid_keys"))
    if keyless:
        fail.append("dict option(s) %s declare no valid_keys, so the wizard can only draw the keys "
                    "their DEFAULT happens to use and a player cannot reach the rest. Set "
                    "`valid_keys` on the Option class (derive it -- do not retype the list)."
                    % ", ".join(keyless))

    if fail:
        for f in fail:
            print("[FAIL] " + f, file=sys.stderr)
        sys.exit(1)

    n_dict = sum(1 for o in opts if o.get("kind") == "dict")
    print("[ok] every emitted kind has a control; %d shipped option(s), %d dict(s) with valid_keys"
          % (len(opts), n_dict))


if __name__ == "__main__":
    main()
