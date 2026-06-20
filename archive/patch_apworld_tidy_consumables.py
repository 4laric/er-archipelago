#!/usr/bin/env python3
r"""
patch_apworld_tidy_consumables.py  (run on Windows from repo root)

New option tidy_fun_consumables (Toggle, default off). Pulls junk "fun consumables" out of the
randomized pool -- progression only by classification, gating ~nothing, crowding the priority/
progression fill:
  - Festering Bloody Finger (x1..x10): PvP invasion items, gate nothing -> just skipped.
  - Starlight Shards: gates the Seluvis puppet shop (needs 3).
  - Seedbed Curse: gates the Dung Eater rewards (needs 5).
Starlight Shards + Seedbed Curse are start-granted at their required counts so the gated checks
stay reachable; their reward checks stay shuffled (Sword of Milos / Mending Rune of the Fell
Curse are worth finding). Mirrors the Deathroot pattern. See SPEC-soft-consumables.md.

Idempotent; asserts anchors.
"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))
ER   = os.path.join(ROOT, "Archipelago", "worlds", "eldenring")
INIT = os.path.join(ER, "__init__.py")
OPTS = os.path.join(ER, "options.py")

def load(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def save(p, s):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(s)
def nl_of(s): return "\r\n" if "\r\n" in s else "\n"
def once(s, old, new, label, marker):
    if marker in s: return s, False
    n = s.count(old)
    if n != 1: raise SystemExit(f"[FAIL] {label}: expected 1 anchor, found {n}")
    return s.replace(old, new, 1), True

changed = False

# ===== options.py =====
o = load(OPTS); NL = nl_of(o)
cls = NL.join([
"class TidyFunConsumables(Toggle):",
"    \"\"\"Pull junk 'fun consumables' out of the randomized pool -- progression only by",
"    classification, gating ~nothing, crowding the priority/progression fill. Festering Bloody",
"    Fingers (PvP, gate nothing) are skipped; Starlight Shards (Seluvis puppets, needs 3) and",
"    Seedbed Curses (Dung Eater, needs 5) are start-granted at their required counts so the gated",
"    checks stay reachable. Reward checks stay shuffled. See SPEC-soft-consumables.md.\"\"\"",
"    display_name = \"Tidy Junk Consumables (Festering/Starlight/Seedbed)\"",
"",
"",
])
o, ch = once(o, "class PoolBuilder(Toggle):", cls + "class PoolBuilder(Toggle):",
             "options: insert TidyFunConsumables", "class TidyFunConsumables(Toggle):"); changed |= ch
o, ch = once(o, "    blessing_option: BlessingOption",
             "    blessing_option: BlessingOption" + NL + "    tidy_fun_consumables: TidyFunConsumables",
             "options: dataclass", "    tidy_fun_consumables: TidyFunConsumables"); changed |= ch
o, ch = once(o, "        BlessingOption,",
             "        BlessingOption," + NL + "        TidyFunConsumables,",
             "options: option group", "        TidyFunConsumables,"); changed |= ch
save(OPTS, o)

# ===== __init__.py =====
i = load(INIT); NL = nl_of(i)

# generate_early: skip the consumables (after merchant-bell block)
mb = (
'        if self.options.merchant_bell_logic.value == 1:' + NL +
'            for _bell in merchant_bell_names(bool(self.options.enable_dlc)):' + NL +
'                item_table[_bell].skip = False' + NL +
'                item_table[_bell].classification = ItemClassification.progression')
ge = NL + NL.join([
"",
"        # Tidy junk 'fun consumables': pull from the pool (progression-classed, gate ~nothing).",
"        # Festering Bloody Fingers gate nothing; Starlight Shards / Seedbed Curses are start-",
"        # granted at their required counts in _fill_local_items so the gated checks stay reachable.",
"        if self.options.tidy_fun_consumables.value:",
"            for _vn in (\"Festering Bloody Finger\", \"Festering Bloody Finger x2\",",
"                        \"Festering Bloody Finger x3\", \"Festering Bloody Finger x5\",",
"                        \"Festering Bloody Finger x6\", \"Festering Bloody Finger x8\",",
"                        \"Festering Bloody Finger x10\", \"Starlight Shards\", \"Seedbed Curse\"):",
"                if _vn in item_table: item_table[_vn].skip = True",
])
i, ch = once(i, mb, mb + ge, "init: tidy skip block", "Tidy junk 'fun consumables': pull from the pool"); changed |= ch

# _fill_local_items: precollect required counts (after fragment/revered lock line)
fr = "            self._lock_class_at_vanilla(lambda d: d.fragment or d.revered)"
pc = NL + NL.join([
"",
"        # Tidy junk consumables: start-grant the required counts so the gated checks (Seluvis",
"        # puppets / Dung Eater) stay reachable after Starlight Shards / Seedbed Curse leave the",
"        # pool (generate_early). Festering gates nothing, so no grant.",
"        if self.options.tidy_fun_consumables.value:",
"            for _ in range(3):",
"                self.multiworld.push_precollected(self.create_item(\"Starlight Shards\"))",
"            for _ in range(5):",
"                self.multiworld.push_precollected(self.create_item(\"Seedbed Curse\"))",
])
i, ch = once(i, fr, fr + pc, "init: tidy precollect block", "Tidy junk consumables: start-grant the required"); changed |= ch
save(INIT, i)

print("[OK] tidy-consumables patch applied." if changed else "[OK] already applied -- no changes.")
