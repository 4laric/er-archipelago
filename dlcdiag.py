#!/usr/bin/env python3
"""Compact diagnostic for ER multiworld generation (DLC-only and base-game).

Parses a raw Generate.py log and emits a small, timestamped summary so we never
have to scroll a ~10k-line FillError dump. Handles two failure shapes:
  * accessibility "Missing: [...]" (unreachable required locations), and
  * "Not enough filler items for excluded locations" (filler shortage + All Placements).
Pure stdlib; runs anywhere. Usage: python dlcdiag.py <raw_log> <out_txt> [<gen_exit_code>]
"""
import sys
import re
from collections import Counter

raw_path = sys.argv[1]
out_path = sys.argv[2]
gen_exit = sys.argv[3] if len(sys.argv) > 3 else "?"


def _read(path):
    data = open(path, "rb").read()
    for bom, enc in ((b"\xff\xfe", "utf-16-le"), (b"\xfe\xff", "utf-16-be"),
                     (b"\xef\xbb\xbf", "utf-8-sig")):
        if data.startswith(bom):
            return data.decode(enc, errors="replace")
    return data.decode("utf-8", errors="replace")


text = _read(raw_path)

lines = []
def out(s=""):
    lines.append(s)

def first(pat, default=None, flags=0):
    m = re.search(pat, text, flags)
    return m.group(1) if m else default


# --- region-code helpers (module scope: shared by every section below) ----------------
DLC = {"GP", "BTS", "CE", "JP", "CHG", "SA", "RB", "ER", "CC", "FRR", "SCF",
       "SK", "ARR", "HL", "RR", "AW", "MM", "EI", "FRM", "FRD", "FRC", "BV"}

def code(e):
    """Leading region code of a location/entry string (stops at / : ( or space)."""
    m = re.match(r"[^/:( ]+", e.strip())
    return m.group(0) if m else "?"

def tag_of(c):
    return "DLC" if c in DLC else ("mix" if c in {"SV", "RH"} else "base")


out("ER GEN DIAGNOSTIC")
out("raw log : " + raw_path)
out("gen exit: " + str(gen_exit))
out("seed    : " + str(first(r"Seed[: ]+(\d+)")))

er = re.search(r"EldenRing\s*:\s*v\S+\s*\|\s*Items:\s*(\d+)\s*\|\s*Locations:\s*(\d+)", text)
if er:
    out("ER world: items=%s locations=%s  (full table, before pool filtering)" % (er.group(1), er.group(2)))
out("fill    : %s items placed" % first(r"Filling the multiworld with (\d+) items"))

# --- resolved key options (from the apworld's generate_early startup diagnostic) -------
# This line is THE fix for the "6 identical FillErrors, no idea why" trap: it shows what the
# world ACTUALLY resolved (e.g. accessibility silently defaulting to full because the yaml put
# it at the document root instead of under EldenRing:). If this line is MISSING, the gen ran
# stale .pyc bytecode -- invalidate worlds/eldenring/__pycache__ and re-gen.
opt = first(r"ER-(?:FUNDEMOTE|OPTIONS)-DIAG enter generate_early: (.+)")
out("options : " + (opt.strip() if opt else "(sentinel ABSENT -- stale .pyc? edited source not running)"))
dem = first(r"ER-(?:FUNDEMOTE|OPTIONS)-DIAG demoted (\d+) fun-consumable")
if dem:
    out("fun-demote: %s item-defs progression->useful (gated on accessibility==minimal)" % dem)

spills = re.findall(r'Couldn.t add "([^"]+)" to the item pool', text)
out("precollected-to-start (%d): %s" % (len(spills), ", ".join(spills) if spills else "(none)"))

tb = "Traceback (most recent call last)" in text
exc = None
for m in re.finditer(r"^(\w[\w.]*(?:Error|Exception): .*)$", text, re.M):
    exc = m.group(1)
if tb or exc:
    out("RESULT  : FAILED")
    if exc:
        out("exception: " + exc.split(" Missing:")[0][:200])
else:
    out("RESULT  : SUCCESS (no traceback)")

# --- accessibility failure: "Missing: [...]" unreachable required locations -----------
mm = re.search(r"Missing:\s*\[(.*?)\]\s*(?:All Placements:|\Z)", text, re.S)
if mm:
    body = mm.group(1)
    entries = [e.strip() for e in re.split(r",\s+(?=[A-Za-z(][\w()|.]*\s*[/:(])", body) if e.strip()]
    out("")
    out("MISSING (unreachable required locations): %d entries" % len(entries))

    hist = Counter(code(e) for e in entries)
    dlc_n = sum(n for c, n in hist.items() if c in DLC)
    mix_n = sum(n for c, n in hist.items() if c in {"SV", "RH"})
    base_n = len(entries) - dlc_n - mix_n
    out("  approx split: base=%d  dlc=%d  mixed(SV/RH)=%d" % (base_n, dlc_n, mix_n))
    out("  region-code histogram (desc):")
    for c, n in sorted(hist.items(), key=lambda kv: (-kv[1], kv[0])):
        out("    %-9s %5d  [%s]" % (c, n, tag_of(c)))

    sentinels = [
        ("GOAL  EI/GD Circlet of Light",   "EI/GD: Circlet of Light"),
        ("dlc   EI/DGFS mainboss (PCR)",   "EI/DGFS: Remembrance of a God and a Lord"),
        ("dlc   SK/DCE Messmer Kindling",  "SK/DCE: Messmer's Kindling"),
        ("dlc   ARR Saint of the Bud",     "ARR/CBME: Remembrance of the Saint of the Bud"),
        ("dlc   JP/JPS Heart of Bayle",    "JP/JPS: Heart of Bayle"),
        ("dlc-front GP Gravesite map",     "GP/SR: Map: Gravesite Plain"),
        ("base  CL Radahn Great Rune",     "CL/(WD): Radahn's Great Rune"),
        ("base  LRC Morgott Great Rune",   "LRC/QB: Morgott's Great Rune"),
        ("base  LG Dectus Left",           "LG/(FH): Dectus Medallion (Left)"),
    ]
    out("  sentinels (is it in the unreachable Missing list?):")
    for label, needle in sentinels:
        out("    [%s] %s" % ("MISSING" if needle in body else "  ok   ", label))

    out("  sample first 8: " + " | ".join(entries[:8]))
    out("  sample last 4 : " + " | ".join(entries[-4:]))
else:
    out("")
    out("MISSING : (none found -- no accessibility FillError in log)")

# --- balance failure: "Not enough filler items for excluded locations" ----------------
fs = re.search(r"Not enough filler items for excluded locations\.\s*There are (\d+) more "
               r"excluded locations than excludable items", text)
if fs:
    deficit = fs.group(1)
    out("")
    out("FILLER SHORTAGE: %s more excluded locations than excludable (filler) items." % deficit)
    out("  meaning: excluded locations (excluded_location_behavior=forbid_useful) can only take")
    out("           FILLER items, and the pool is %s filler short of covering them. Levers:" % deficit)
    out("    - excluded_location_behavior: allow_useful  (lets useful items sit in excluded spots)")
    out("    - location_pool: keep more filler-item locations (lean/trimmed strip filler -> fewer")
    out("                     excludable items) and/or shrink the excluded set")
    out("    - important_locations / exclude_locations: fewer forced-priority / excluded entries")
    ap = re.search(r"All Placements:\s*\[(.*)\]", text, re.S)
    if ap:
        body = ap.group(1).strip()
        if body.startswith("("):
            body = body[1:]
        if body.endswith(")"):
            body = body[:-1]
        entries = [e for e in re.split(r"\),\s*\(", body) if e.strip()]
        markers = [e for e in entries if "/" not in e.split(",")[0] and ":" not in e.split(",")[0]]
        real = len(entries) - len(markers)
        out("")
        out("  placements before the error: %d  (real checks=%d, region/boss markers=%d)"
            % (len(entries), real, len(markers)))
        hist = Counter(code(e) for e in entries)
        out("  placement region-code histogram (desc, top 15):")
        for c, n in sorted(hist.items(), key=lambda kv: (-kv[1], kv[0]))[:15]:
            out("    %-16s %5d  [%s]" % (c, n, tag_of(c)))

# --- placement failure: "No more spots to place N items" (priority/progression fill) --
ns = re.search(r"No more spots to place (\d+) items\. Remaining locations are invalid", text)
if ns:
    out("")
    out("NO SPOTS: %s items unplaced (priority/progression fill ran out of valid locations)." % ns.group(1))
    ui = text.find("Unplaced items:")
    if ui != -1:
        blob = text[ui:].split("\n")[1] if len(text[ui:].split("\n")) > 1 else ""
        names = []
        for p in blob.split("(Player 1)"):
            nm = re.sub(r"\s+x\d+\s*$", "", re.sub(r"^[,\s]+", "", p)).strip()
            if nm:
                names.append(nm)
        hist = Counter(names)
        out("  distinct unplaced item types: %d  (top 20 by count):" % len(hist))
        for nm, n in hist.most_common(20):
            out("    %3d  %s" % (n, nm))
        out("  levers: 'fun' consumables -> demote in apworld (gated on accessibility==minimal);")
        out("          genuine progression (locks/runes/medallions/remembrances) -> clear")
        out("          important_locations and keep accessibility: minimal so region-gated")
        out("          priority spots aren't force-filled.")

open(out_path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("wrote " + out_path)
