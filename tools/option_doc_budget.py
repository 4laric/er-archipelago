"""The tooltip budget for option docstrings -- ONE definition, read by the dumper and by the test.

WHY A BUDGET AT ALL. An option's docstring is the text on every built-in Archipelago surface:
  * the Launcher's Options Creator turns every newline into a line break in a tooltip that does NOT
    scroll, so a long docstring simply runs off the screen (a player reported exactly this for Dungeon
    Sweep, Keep Local and Keep Local: Rune Cap -- 3.6k, 3.3k and 3.7k characters, 48-55 lines);
  * the generated template yaml prints it as "# " comment lines above each option, so every line is a
    yaml comment line and 76 docstrings used to run past 88 columns;
  * the WebHost pages show it in a hover tooltip.
Before this module the corpus was 72,079 characters (median 731, 57 options over 450); nothing stopped
it growing back, and every one of those docstrings had been added one reasonable paragraph at a time.

THE NUMBERS. Soft budget 450 characters / 7 lines. A handful of options genuinely have several modes
that a player must be told apart, so they are EXEMPT -- by name, with a ceiling recorded at the
measured size. The ceiling is a RATCHET, not a licence: it may not grow, it may not exceed the hard
cap, and an exempt option that shrinks back under the soft budget must leave the table.
Hard cap 900 characters / 14 lines, for everyone, exemptions included. The 14-line ceiling is
INFERRED -- nobody has yet screenshotted a 14-line tooltip in a real Options Creator window. If one
clips, lower HARD_LINES here and move that option's per-mode lines into the Player Guide.

The rules are a pure function over the metadata's `options` list, so the same code gates the dumper
(hard cap only: it refuses to regenerate over it) and the AP-free test (everything).
"""

SOFT_CHARS = 450
SOFT_LINES = 7
HARD_CHARS = 900
HARD_LINES = 14
MAX_LINE_COLS = 90          # a continuation line keeps its source indent in the Kivy tooltip
SUMMARY_MAX_COLS = 88       # line 1: one plain-language sentence
DISPLAY_NAME_MAX = 50
TOTAL_CEILING = 34340       # ratchet on the whole corpus (33,657 when this landed; 34200 -> 34340
                            # 2026-09-23, region_sweep: one new in-budget option's docstring, 134
                            # chars -- not creep across many, so the ratchet moved instead of the
                            # option shrinking below what the summary sentence needs)
MIN_OPTIONS_WITNESS = 60    # a test that scans nothing passes vacuously

# key -> (max chars, max lines): options allowed past the soft budget. Measured when this landed.
EXEMPT = {
    "keep_out_of_shops": (896, 13),
    "keep_local": (895, 13),
    "progression_surface": (867, 14),
    "dungeon_sweep": (862, 13),
    "traps": (780, 13),
    "goal": (643, 11),
    "region_grace_unlock": (561, 9),
}


def _shape(doc):
    lines = doc.split("\n")
    return len(doc), len(lines), max(len(x) for x in lines)


def hard_violations(options):
    """Only the rules the dumper enforces before writing anything: the hard cap."""
    out = []
    for o in options:
        chars, lines, _ = _shape(o["description"] or "")
        if chars > HARD_CHARS or lines > HARD_LINES:
            out.append("%s: %d chars / %d lines exceeds the hard cap %d / %d" % (
                o["key"], chars, lines, HARD_CHARS, HARD_LINES))
    return out


def violations(options):
    """Every rule, as human-readable strings. Empty list = within budget."""
    out = []
    if len(options) < MIN_OPTIONS_WITNESS:
        out.append("witness: only %d options scanned (< %d) -- the gate would pass vacuously"
                   % (len(options), MIN_OPTIONS_WITNESS))
    keys = {o["key"] for o in options}
    for k in EXEMPT:
        if k not in keys:
            out.append("EXEMPT names %r, which is not an option (stale entry -- remove it)" % k)
    total = 0
    seen = {}
    for o in options:
        k, doc = o["key"], o["description"] or ""
        if not doc.strip():
            out.append("%s: empty description" % k)
            continue
        chars, lines, widest = _shape(doc)
        total += chars
        exempt = EXEMPT.get(k)
        if exempt is None:
            if chars > SOFT_CHARS or lines > SOFT_LINES:
                out.append("%s: %d chars / %d lines is over the soft budget %d / %d -- shorten it, "
                           "or (only if it truly has several modes) add it to EXEMPT"
                           % (k, chars, lines, SOFT_CHARS, SOFT_LINES))
        else:
            if chars > exempt[0] or lines > exempt[1]:
                out.append("%s: %d chars / %d lines grew past its recorded ceiling %d / %d"
                           % (k, chars, lines, exempt[0], exempt[1]))
            if chars <= SOFT_CHARS and lines <= SOFT_LINES:
                out.append("%s: is back under the soft budget -- drop it from EXEMPT" % k)
        if chars > HARD_CHARS or lines > HARD_LINES:
            out.append("%s: %d chars / %d lines exceeds the HARD cap %d / %d (no exemption)"
                       % (k, chars, lines, HARD_CHARS, HARD_LINES))
        if widest > MAX_LINE_COLS:
            out.append("%s: a line is %d columns wide (max %d)" % (k, widest, MAX_LINE_COLS))
        first = doc.split("\n")
        if len(first[0]) > SUMMARY_MAX_COLS or not first[0].endswith("."):
            out.append("%s: line 1 must be ONE sentence <= %d columns ending in a period"
                       % (k, SUMMARY_MAX_COLS))
        if len(first) > 1 and first[1] != "":
            out.append("%s: line 2 must be blank (summary, blank line, then detail)" % k)
        if any(ord(c) > 127 for c in doc):
            out.append("%s: non-ASCII character (write '--' not an em dash; the template yaml and the "
                       "Windows console both mangle it)" % k)
        if "\t" in doc or any(x != x.rstrip() for x in first):
            out.append("%s: tab or trailing space" % k)
        if "*" in doc:
            out.append("%s: contains '*' -- the Kivy tooltip turns *x* into italics" % k)
        name = o.get("display_name") or ""
        if not name or len(name) > DISPLAY_NAME_MAX:
            out.append("%s: display name %r must be 1..%d characters" % (k, name, DISPLAY_NAME_MAX))
        seen.setdefault(name.lower(), []).append(k)
    for name, ks in seen.items():
        if len(ks) > 1:
            out.append("display name %r is used by %s -- two rows would look identical" % (name, ks))
    if total > TOTAL_CEILING:
        out.append("corpus is %d characters, past the ratchet %d -- the docstrings are growing back"
                   % (total, TOTAL_CEILING))
    return out
