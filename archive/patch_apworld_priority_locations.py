#!/usr/bin/env python3
"""
patch_apworld_priority_locations.py

Priority-location ("important locations") defaults, per Alaric's spec:
  * Default important_locations -> Remembrance, Seedtree, Church, Boss   (Map dropped:
    under map_option=give, map pillars aren't real checks, so Map priority was inert.)
  * DLC on -> Scadutree Fragments + Revered Spirit Ashes become priority
    (BlessingOption default flipped randomize -> to_important; predicates already DLC-gate.)
  * New opt-in "Shop" priority class, scoped to Twin Maiden Husks (Roundtable Hold),
    non-missable only (21 checks) -- NOT all 348 non-missable shop checks. Not in default.

Run on Windows from the repo root:  python patch_apworld_priority_locations.py
Idempotent: re-running is a safe no-op.
"""
import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
INIT = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "__init__.py")
OPTS = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "options.py")

def load(p):
    with open(p, "r", encoding="utf-8", newline="") as f:
        return f.read()

def save(p, s):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)

def nl_of(s):
    return "\r\n" if "\r\n" in s else "\n"

def replace_once(s, old, new, label, already_marker=None):
    if already_marker is not None and already_marker in s:
        return s, False
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"[FAIL] {label}: expected exactly 1 occurrence of anchor, found {n}")
    return s.replace(old, new, 1), True

def main():
    for p in (INIT, OPTS):
        if not os.path.isfile(p):
            raise SystemExit(f"[FAIL] not found: {p}\n  Run from the repo root.")

    changed = False

    # ----- options.py -----
    o = load(OPTS); NL = nl_of(o)

    o, c = replace_once(o,
        '    default = ["Remembrance", "Seedtree", "Map"]',
        '    default = ["Remembrance", "Seedtree", "Church", "Boss"]',
        "important_locations default",
        already_marker='    default = ["Remembrance", "Seedtree", "Church", "Boss"]')
    changed |= c

    o, c = replace_once(o,
        '    valid_keys_casefold = ["Remembrance", "Seedtree", "Basin", "Church", "Map", "Fragment", "Cross", "Revered", "KeyItem", "Boss"]',
        '    valid_keys_casefold = ["Remembrance", "Seedtree", "Basin", "Church", "Map", "Fragment", "Cross", "Revered", "KeyItem", "Boss", "Shop"]',
        "important_locations valid_keys",
        already_marker='"KeyItem", "Boss", "Shop"]')
    changed |= c

    boss_doc = '    - [~52] *Boss*: Major boss drops (broader than Remembrance; can over-constrain).'
    o, c = replace_once(o,
        boss_doc,
        boss_doc + NL +
        '    - [21] *Shop*: Twin Maiden Husks shop (Roundtable Hold), non-missable. Opt-in; not in default.',
        "important_locations Shop doc",
        already_marker='*Shop*: Twin Maiden Husks')
    changed |= c

    blessing_old = (
        '    display_name = "Shadow Realm Blessing Handling"' + NL +
        '    option_randomize = 0' + NL +
        '    option_to_important = 1' + NL +
        '    option_do_not_randomize = 2' + NL +
        '    default = 0')
    blessing_new = (
        '    display_name = "Shadow Realm Blessing Handling"' + NL +
        '    option_randomize = 0' + NL +
        '    option_to_important = 1' + NL +
        '    option_do_not_randomize = 2' + NL +
        '    # default to_important: Scadutree Fragments + Revered Ashes are priority when DLC is on' + NL +
        '    default = 1')
    o, c = replace_once(o, blessing_old, blessing_new,
        "BlessingOption default",
        already_marker='priority when DLC is on')
    changed |= c

    save(OPTS, o)

    # ----- __init__.py -----
    i = load(INIT); NL2 = nl_of(i)
    boss_pred = '            "boss":        lambda loc: loc.boss,'
    shop_pred = '            "shop":        lambda loc: loc.shop and not loc.missable and "twin maiden" in loc.name.lower(),'
    i, c = replace_once(i, boss_pred, boss_pred + NL2 + shop_pred,
        "shop predicate",
        already_marker='"shop":        lambda loc: loc.shop')
    changed |= c
    save(INIT, i)

    print("[OK] priority-location patch applied." if changed
          else "[OK] already applied -- no changes.")

if __name__ == "__main__":
    main()
