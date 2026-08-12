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
    ("Seed size", "checks that can hold progression"),
]

# ---------------------------------------------------------------------------------------------
# SECOND AUDIT: the contribution card must REACT to the options it describes.
#
# MOTIVATING CASE (rule 11). Alaric, 2026-08-12, on the shipped card: "it didn't seem responsive to
# the filler local percent, which id assume is the main lever" -- and "seemingly widget went dead
# after i messed with it enough". Both were the same thing seen twice: `filler_foreign_pct` and
# `keep_local_rune_cap` moved a FOOTNOTE and left every figure untouched, so a player working the
# knobs that matter watched a card that never answered. Nothing threw; a fuzz over 1,969 single-
# option states and 700 random multi-option states across every step found no exception at all.
#
# A card that renders is not a card that WORKS, which is the next question after check_renders'.
# The side rail's ORDER is a stated requirement, not a default. The live readout sits directly under
# the yaml because it is what you watch while you turn a knob, and the last card is the one you
# touch once, at the end (Alaric, 2026-08-12). Card order is the kind of thing a later edit
# reshuffles without noticing, and nothing else in the tree records the reason.
#
# 🛑 THE LAST CARD WAS "Generate &amp; host" UNTIL v0.4.0 AND IS NOW "Take your yaml". Hosting was
# scoped out of the site: the wizard no longer POSTs to /generate and no longer starts rooms. This
# line changed because the REQUIREMENT changed, which is the only reason it may ever change --
# editing it to match a wizard that drifted would delete the assertion instead of checking it.
SIDE_ORDER = ["Your yaml", "Into the multiworld", "Seed size", "Checks", "Take your yaml"]

NUMBERS_MOVE = ["filler_foreign_pct", "keep_local", "local_item_only",
                "confine_foreign_progression", "num_regions", "progression_surface"]
# Real effects the card cannot COUNT (the rune cap's share of the runes category depends on which
# rune items a seed contains). They must still change what the card SAYS -- silence is the failure
# mode, not imprecision.
TEXT_MOVES = ["keep_local_rune_cap"]

HARNESS = r"""
const fs = require("fs");
const path = require("path");
const { El, makeDocument, text, textOfClass, attached, NODES } = require(process.argv[2]);
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

let scripts = [...html.matchAll(/<script(?![^>]*type="application\/json")[^>]*>([\s\S]*?)<\/script>/g)]
  .map(m => m[1]);
// The app block is an IIFE, so its closure cannot be reached from outside. Splice an export in
// before its final `})();` -- a PROBE of the shipped source, which is never modified on disk.
scripts = scripts.map(src => {
  const i = src.lastIndexOf("})();");
  if (i < 0 || !src.includes("function renderStep()")) return src;
  return src.slice(0, i) + "\n globalThis.__probe = { meta, state, contributionCard };\n" + src.slice(i);
});

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
// ---- reactivity: does the contribution card answer the knobs it describes? -------------------
// NOT `globalThis.__probe`: the page runs inside vm.createContext(sandbox), so its global is the
// sandbox object, not this file's. Reading the wrong one returns undefined and the whole reactivity
// half of this gate silently checks nothing -- which is the failure mode it exists to forbid, so it
// is asserted below rather than left to be noticed.
const P = sandbox.__probe || {};
const react = {};
if (P.state && P.contributionCard){
  const draw = () => { const c = P.contributionCard(); return c ? text(c).replace(/\s+/g, " ") : ""; };
  /* THE HEADLINE FIGURES ONLY. Matching any digit in the card is not the same question: the
     explanatory prose quotes percentages and item counts of its own, so a mutation that froze the
     headline while leaving a paragraph in place passed the first version of this check twice. The
     `bignums` class marks what a player reads as THE ANSWER. */
  const figures = () => { const c = P.contributionCard();
    return c ? (textOfClass(c, "fig").match(/\d[\d,]*/g) || []).join(" ") : ""; };
  const base = draw(), baseFigures = figures();
  const probe = (key, val) => {
    for (const k of Object.keys(P.state.values)) delete P.state.values[k];
    P.state.values[key] = val;
    return { text: draw() !== base, numbers: figures() !== baseFigures };
  };
  const opt = k => P.meta.options.find(o => o.key === k);
  for (const o of P.meta.options){
    const k = o.key;
    let v;
    if (o.kind === "toggle") v = !o.default;
    else if (o.kind === "choice") v = (o.choices.find(c => c.name !== o.default) || o.choices[0]).name;
    else if (o.kind === "range") v = o.default === o.range.start ? o.range.end : o.range.start;
    else if (o.kind === "set" || o.kind === "list") v = (o.valid_keys || []).slice(0, 2);
    else continue;
    react[k] = probe(k, v);
  }
  for (const k of Object.keys(P.state.values)) delete P.state.values[k];
}

// The side rail's live readout lives OUTSIDE #main, so the step walk above never sees it -- and it
// is the copy that is on screen on every step, i.e. the one a player actually watches.
const side = text(doc.querySelector("#contrib") || {}).replace(/\s+/g, " ").trim();

console.log(JSON.stringify({ titles, react, side, steps: out.map(s => ({ title: s.title, len: s.text.length,
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

    html = open(WIZARD_HTML, "r", encoding="utf-8", newline="").read()
    static = re.sub(r'<script id="[a-z-]+" type="application/json">.*?</script>', "",
                    html.split('<script id="wizard-core">')[0], flags=re.S)
    rail = static[static.index('<div class="side">'):]
    rail = rail[:rail.index("</div>\n  </div>")]
    order = [t.strip() for t in re.findall(r"<h3[^>]*>(.*?)(?:<span|</h3>)", rail)]
    if order != SIDE_ORDER:
        problems.append("the side rail's cards are in the wrong order.\n"
                        "        want: %s\n        got:  %s" % (SIDE_ORDER, order))

    side = (data.get("side") or "").lower()
    if "checks open to a foreign item" not in side:
        problems.append("the side rail's live readout (#contrib) did not render: %r. It is the copy "
                        "that is on screen on EVERY step, so it going quiet is the failure a player "
                        "sees first." % (data.get("side") or "")[:120])

    react = data.get("react") or {}
    if not react:
        problems.append("the reactivity probe returned nothing -- the page's IIFE export spliced in "
                        "no longer matches, so half this gate is checking nothing.")
    for key in NUMBERS_MOVE:
        r = react.get(key)
        if r is None:
            problems.append("%s: not on the option surface any more -- drop it from NUMBERS_MOVE "
                            "or fix the name." % key)
        elif not r["numbers"]:
            problems.append("%s changes NO NUMBER on the contribution card. The card names it as "
                            "something that moves what you send out, so a player works the knob and "
                            "watches a figure that never answers -- which is what 'the widget went "
                            "dead' looked like." % key)
    for key in TEXT_MOVES:
        r = react.get(key)
        if r is None:
            problems.append("%s: not on the option surface any more -- drop it from TEXT_MOVES."
                            % key)
        elif not r["text"]:
            problems.append("%s changes NOTHING the card says. It cannot be counted, but it must "
                            "not be silent." % key)

    bad = selftest()
    if bad:
        problems.append("SELF-TEST: " + bad)

    if problems:
        print("[FAIL] the wizard does not render what it should:")
        for p in problems:
            print("   ", p)
        return 1
    print("[ok] all %d wizard steps render (%d..%d chars); the side readout is live; the "
          "contribution card answers %d option(s) with a number and %d more in prose; the shim "
          "fails the detached-paint mutation"
          % (len(steps), min(s["len"] for s in steps), max(s["len"] for s in steps),
             len(NUMBERS_MOVE), len(TEXT_MOVES)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
