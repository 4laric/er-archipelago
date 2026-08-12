#!/usr/bin/env python3
"""check_wizard_renders.py -- every step of the wizard must actually DRAW something.

WHAT ROTTED, TWICE, IN THE SAME WEEK. Both defects were a page that renders and says nothing:

  * 2026-08-08 (95c628a): the "What are you putting into the multiworld?" card read `item_shuffle`,
    an option frozen off the yaml surface three weeks earlier, so `!!undefined` sent it down its
    "nothing to send" branch on every render. Caught by check_wizard_lint_currency's page audit.
  * 2026-08-08 (9566a4d): `renderSeedSizeTab()` called `paintSeedSize()` before its own tree was
    attached to the document. `paintSeedSize` finds `#ss-head`/`#ss-rest` with
    `document.querySelector`, got null, and returned. THE WHOLE SEED SIZE STEP WAS BLANK on
    arrival -- no size figures, no composition bars, no contribution card -- until the player
    touched a control, because every `refresh()` lives in an event handler and `renderStep` calls
    none. Reported by a human looking at the page, which is the instrument this file replaces.

Neither threw. A DOM lookup that misses returns null, and an empty div renders fine. Every gate we
had reads the page as TEXT -- the metadata is current, the blob is in sync, the lint rules name
live options, the JS maths matches Python -- and not one of them renders it.

So this one runs it: the real `wizard.html`, under `tools/wizard_dom_shim.js`, walking every step
via the step rail's own click handlers, asserting each step draws a non-trivial amount of text and
that the cards we care about are on the steps that own them.

🛑 THE SHIM'S ONE LOAD-BEARING BEHAVIOUR is that `querySelector` resolves a node only when its
parent chain reaches the static HTML. Drop that and this gate goes green on the very bug it was
written for. There is a self-test below that asserts exactly this, so the shim cannot be quietly
loosened.

NEEDS NODE. Exits 4 (SKIP) when node is absent, so a box without it reports honestly. CI has node.

Usage:
    python tools/check_wizard_renders.py           # exit 1 if any step draws nothing
    python tools/check_wizard_renders.py --dump    # print what each step rendered
"""
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIZARD_HTML = os.path.join(ROOT, "wizard", "wizard.html")
SHIM = os.path.join(ROOT, "tools", "wizard_dom_shim.js")

# Every step must draw at least this much text. A blank step measured 0; the thinnest real one
# (DLC & Blessings, five options) measures in the thousands, so this separates "drew nothing" from
# "drew a short tab" with room to spare and without pinning a number that ordinary copy edits move.
MIN_TEXT = 200

# (step title contains, text that must appear on it). The contribution card is asserted on BOTH
# tabs that draw it -- that duplication is the feature, and a gate that checked one of them would
# not notice the other going missing.
REQUIRED = [
    ("Seed size", "How big is this seed?"),
    ("Seed size", "What are you putting into the multiworld?"),
    ("Multiworld", "What are you putting into the multiworld?"),
    ("Seed size", "checks that can hold progression"),
]

HARNESS = r"""
const fs = require("fs");
const path = require("path");
const { El, makeDocument, text, attached, NODES } = require(process.argv[2]);
const html = fs.readFileSync(process.argv[3], "utf8");

// ids present in the STATIC markup -- everything above the first script block
const head = html.split('<script id="wizard-core">')[0];
const staticIds = [...new Set([...head.matchAll(/\bid="([\w-]+)"/g)].map(m => m[1]))];
const doc = makeDocument(staticIds);

// the JSON blobs are read via getElementById(...).textContent
for (const id of ["er-options-metadata", "er-region-census", "er-pool-composition"]){
  const m = html.match(new RegExp('<script id="' + id + '" type="application/json">\\n([\\s\\S]*?)</script>'));
  const node = doc.getElementById(id);
  if (m && node) node.textContent = m[1];
}

const scripts = [...html.matchAll(/<script(?![^>]*type="application\/json")[^>]*>([\s\S]*?)<\/script>/g)]
  .map(m => m[1]);

const sandbox = {
  document: doc, window: { scrollTo(){} },
  navigator: { clipboard: { writeText: async () => {} } },
  location: { protocol: "https:", origin: "https://example.invalid", pathname: "/er/wizard.html" },
  URL, Option: function(t, v){ const e = new El("option"); e.textContent = t; e.value = v; return e; },
  console, JSON, Math, Object, Array, Set, Map, Number, String, Boolean, Date, RegExp, isNaN,
  parseInt, parseFloat, encodeURIComponent, decodeURIComponent, Blob: function(){}, fetch: () => {},
  setTimeout, clearTimeout, module: {},
};
const vm = require("vm");
const ctx = vm.createContext(sandbox);
for (const src of scripts) vm.runInContext(src, ctx, { timeout: 20000 });

// walk the step rail by firing its own click handlers, exactly as a player would
const main = doc.getElementById("main");
const railButtons = () => {
  const nav = main.kids.find(k => k.className === "stepnav");
  return nav ? nav.kids : [];
};
const titles = railButtons().map(b => b.innerHTML);
const out = [];
for (let i = 0; i < titles.length; i++){
  const b = railButtons()[i];
  b.fire("click");
  out.push({ title: titles[i], text: text(main).trim() });
}
console.log(JSON.stringify({ titles, steps: out.map(s => ({ title: s.title, len: s.text.length,
                                                            text: s.text })) }));
"""


def run(html_path):
    harness = os.path.join(ROOT, "wizard", ".render_harness.js")
    with open(harness, "w", encoding="utf-8", newline="\n") as f:
        f.write(HARNESS)
    try:
        p = subprocess.run(["node", harness, SHIM, html_path], capture_output=True, text=True)
    finally:
        os.remove(harness)
    if p.returncode != 0:
        sys.exit("[FAIL] the wizard threw while rendering under the DOM shim:\n"
                 + (p.stderr or "")[-4000:])
    return json.loads(p.stdout)


def selftest():
    """The shim must FAIL the detached-paint bug. Re-introduce it in a temp copy and check.

    A gate whose negative case is not run is a gate that has never been shown to fail -- and this
    one is a shim, i.e. entirely my own model of a browser, so "it passes" is worth nothing on its
    own. The mutation is the exact line from 9566a4d.
    """
    src = open(WIZARD_HTML, "r", encoding="utf-8", newline="").read()
    hit = re.search(r'\n( *)paintSeedSize\(\);\s*// AFTER the append[^\n]*\n', src)
    if not hit:
        return ("could not find the post-append paintSeedSize() call to mutate -- the self-test "
                "cannot run, so this gate is unproven. Update the pattern.")
    broken = src[:hit.start()] + "\n" + src[hit.end():]
    tmp = os.path.join(ROOT, "wizard", ".render_selftest.html")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(broken)
    try:
        data = run(tmp)
    finally:
        os.remove(tmp)
    # 🛑 NOT a length test. The mutated step is NOT empty -- the "Change the answer" control card is
    # built inline and keeps rendering its ten option rows, which is exactly why the blank tab read
    # as a design choice rather than a bug to anyone looking at it. What vanishes is everything
    # `paintSeedSize` draws, so the self-test has to ask for one of those things BY NAME.
    for st in data["steps"]:
        if "Seed size" in st["title"] and "how big is this seed?" not in st["text"].lower():
            return None                      # good: the bug is detectable
    return ("removing the post-append paintSeedSize() call did NOT stop the Seed size step drawing "
            "its size figures, so the shim is not modelling attachment and this gate would have "
            "passed the 2026-08-08 defect it exists for.")


def main(argv):
    if not shutil.which("node"):
        print("[SKIP] node not on PATH -- the wizard's rendering is NOT gated on this box.")
        return 4

    data = run(WIZARD_HTML)
    steps = data["steps"]
    if len(steps) < 4:
        sys.exit("[FAIL] the page rendered only %d step(s); the rail is not being walked."
                 % len(steps))

    if "--dump" in argv:
        for st in steps:
            print("=== %-26s %6d chars" % (st["title"], st["len"]))
            print("    " + st["text"][:300])
        return 0

    problems = []
    for st in steps:
        if st["len"] < MIN_TEXT:
            problems.append("step %r drew %d characters -- it is blank. A step that renders an "
                            "empty div throws nothing and looks like a page that has not loaded."
                            % (st["title"], st["len"]))
    for title_frag, needle in REQUIRED:
        hits = [st for st in steps if title_frag.lower() in st["title"].lower()]
        if not hits:
            problems.append("no step titled like %r -- the tab it asserts on is gone." % title_frag)
            continue
        if not any(needle.lower() in st["text"].lower() for st in hits):
            problems.append("step %r does not contain %r." % (hits[0]["title"], needle))

    bad = selftest()
    if bad:
        problems.append("SELF-TEST: " + bad)

    if problems:
        print("[FAIL] the wizard does not render what it should:")
        for p in problems:
            print("   ", p)
        return 1
    print("[ok] all %d wizard steps render (%d..%d chars); the contribution card is on both the "
          "Seed size and Multiworld tabs; the shim fails the detached-paint mutation"
          % (len(steps), min(s["len"] for s in steps), max(s["len"] for s in steps)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
