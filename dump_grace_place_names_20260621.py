#!/usr/bin/env python3
"""
dump_grace_place_names_20260621.py  --  resolve grace warp flag -> real grace name and bake
grace_data.GRACE_PLACE_NAMES, so grace_rando item names (and the AP ticker) read e.g.
"Grace: Godrick the Grafted (Stormveil Castle)" instead of "Grace: <Region> #<flag>".

Source = Paramdex/ER/Names/BonfireWarpParam.txt (rowId -> "[Area] Grace Name"), joined to
elden_ring_artifacts/grace_flags.tsv (rowId <-> warpUnlockFlag). NO game files / FMG / Oodle needed.
(The earlier placeNameTextId->FMG path was wrong: that column mostly mirrors rowId, not a real text id.)

Usage:
    python dump_grace_place_names_20260621.py [--dry]
  --dry : print + write sidecar only; do NOT modify grace_data.py.
Writes grace_place_names_dump.txt (sidecar) and, unless --dry, GRACE_PLACE_NAMES in grace_data.py
(idempotent, CRLF-safe: replaces any existing block).
"""
import os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
GRACE_TSV  = os.path.join(ROOT, "elden_ring_artifacts", "grace_flags.tsv")
GRACE_DATA = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "grace_data.py")
BONFIRE    = os.path.join(ROOT, "Paramdex", "ER", "Names", "BonfireWarpParam.txt")

def read_bonfire_names():
    d = {}
    with open(BONFIRE, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = line.split(" ", 1)
            if len(parts) < 2:
                continue
            try:
                d[int(parts[0])] = parts[1].strip()
            except ValueError:
                continue
    return d

def read_grace_rows():
    rows = []
    with open(GRACE_TSV, encoding="utf-8") as f:
        h = f.readline().rstrip("\n").split("\t")
        ri, wi = h.index("rowId"), h.index("warpUnlockFlag")
        for line in f:
            c = line.rstrip("\n").split("\t")
            if len(c) <= max(ri, wi):
                continue
            try:
                rows.append((int(c[wi]), int(c[ri])))
            except ValueError:
                continue
    return rows

def pretty(name):
    # strip a leading "[Area] " so items.py wraps "Grace: <name> (<region>)" without doubling the area
    m = re.match(r'^\[[^\]]*\]\s*(.+)$', name)
    g = (m.group(1) if m else name).strip()
    return g or name.strip()

def write_grace_data(names):
    with open(GRACE_DATA, "r", encoding="utf-8", newline="") as f:
        text = f.read()
    eol = "\r\n" if "\r\n" in text else "\n"
    out = ["GRACE_PLACE_NAMES = {  # warpUnlockFlag -> grace name (Paramdex BonfireWarpParam; dump_grace_place_names)"]
    for flag in sorted(names):
        nm = names[flag].replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ").strip()
        out.append('    %d: "%s",' % (flag, nm))
    out.append("}")
    block = eol.join(out) + eol
    if "GRACE_PLACE_NAMES" in text:
        text = re.sub(r"GRACE_PLACE_NAMES = \{.*?^\}\r?\n", block, text, count=1, flags=re.S | re.M)
    else:
        if not text.endswith(eol):
            text += eol
        text += eol + block
    with open(GRACE_DATA, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print("Updated %s with GRACE_PLACE_NAMES (%d entries)." % (GRACE_DATA, len(names)))

def main():
    dry = "--dry" in sys.argv[1:]
    bnames = read_bonfire_names()
    rows = read_grace_rows()
    names, miss = {}, []
    for flag, rid in rows:
        raw = bnames.get(rid)
        if raw:
            names[flag] = pretty(raw)
        else:
            miss.append((flag, rid))
    print("Bonfire name rows: %d; grace rows: %d; resolved: %d; unresolved: %d"
          % (len(bnames), len(rows), len(names), len(miss)))
    if miss:
        print("  unresolved (flag,rowId):", ", ".join("%d/%d" % m for m in miss[:10]),
              ("..." if len(miss) > 10 else ""))
    side = os.path.join(ROOT, "grace_place_names_dump.txt")
    with open(side, "w", encoding="utf-8") as o:
        for flag in sorted(names):
            o.write("%d\t%s\n" % (flag, names[flag]))
    print("Wrote sidecar %s" % side)
    if dry:
        print("--dry: grace_data.py NOT modified. Sample:")
        for flag in sorted(names)[:12]:
            print("    %d -> %s" % (flag, names[flag]))
        return
    write_grace_data(names)
    print("Done. Repackage the apworld so items.py picks up GRACE_PLACE_NAMES, then regen.")

if __name__ == "__main__":
    main()
