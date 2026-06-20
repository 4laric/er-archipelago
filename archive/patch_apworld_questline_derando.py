#!/usr/bin/env python3
r"""
patch_apworld_questline_derando.py

De-randomize long NPC questlines whose chains gate ONLY optional content, so their
dead-weight "progression" link items stop crowding the priority/progression fill (and
stop landing junk-chain keys on important locations). Region/goal-gating quest items are
NEVER cut. No current ER goal (final_boss/elden_beast/all_rem/all_bosses/capital/messmer/
godrick) requires any cut item, so the cut is unconditional.

New option `derandomize_questlines` (Choice, default off):
  off (0)         : unchanged.
  links_only (1)  : lock chain LINK items at vanilla; reward checks stay randomized
                    (good rewards like Dark Moon Greatsword remain shuffled naturally).
  full (2)        : also pull the good terminal rewards to vanilla and re-inject a shuffled
                    copy at the expense of one filler (count-neutral) -- obtainable without
                    grinding the quest.

Touches: worlds/eldenring/{curation.py, options.py, __init__.py}.
Run on Windows from the repo root:  python patch_apworld_questline_derando.py
Idempotent; asserts every anchor (fails loudly rather than corrupting).
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
ER   = os.path.join(ROOT, "Archipelago", "worlds", "eldenring")
INIT = os.path.join(ER, "__init__.py")
OPTS = os.path.join(ER, "options.py")
CUR  = os.path.join(ER, "curation.py")

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

# ---------------- curation.py : append cut-sets ----------------
c = load(CUR); NL = nl_of(c)
if "QUESTLINE_DERANDO" not in c:
    block = NL.join([
"",
"# --- NPC questline de-randomization (SPEC-questline-derando.md) --------------------",
"# UNIQUE quest LINK items that gate only optional locations (never a region or a goal).",
"# Locking these at vanilla satisfies each chain in normal play and pulls dead-weight",
"# progression out of the fill. EXEMPT (region/goal-gating; deliberately NOT listed):",
"#   Drawing-Room Key (Volcano Manor), Haligtree Secret Medallion L/R (Haligtree),",
"#   Hole-Laden Necklace (Cathedral of Manus Metyr).",
"# Multi-location consumables (Starlight Shards, Seedbed Curse, Shabriri Grape, and the",
"# x2 DLC items) are excluded -- a name-keyed cut would also hit their non-quest spots.",
"QUESTLINE_DERANDO = frozenset({",
"    # Sellen",
"    \"Sellen's Primal Glintstone\", \"Sellian Sealbreaker\", \"Academy Glintstone Key (Thops)\",",
"    # Ranni",
"    \"Carian Inverted Statue\", \"Miniature Ranni\", \"Dark Moon Ring\", \"Fingerslayer Blade\",",
"    # Seluvis / Preceptor Seluvis",
"    \"Seluvis's Potion\", \"Amber Draught\", \"Amber Starlight\", \"Dancer's Castanets\",",
"    # Volcano Manor / Rya",
"    \"Rya's Necklace\", \"Serpent's Amnion\", \"Lord of Blood's Favor\",",
"    # Millicent",
"    \"Unalloyed Gold Needle (Broken)\", \"Unalloyed Gold Needle (Fixed)\",",
"    \"Unalloyed Gold Needle (Milicent)\", \"Valkyrie's Prosthesis\",",
"    # Fia / D / Rogier",
"    \"Weathered Dagger\", \"Black Knifeprint\", \"Cursemark of Death\",",
"    # DLC (Hornsent secret rite)",
"    \"Secret Rite Scroll\",",
"})",
"",
"# Good terminal rewards: in 'full' mode their reward LOCATION is also locked at vanilla and",
"# a shuffled copy is re-injected at the expense of one filler (count-neutral), so the item",
"# stays obtainable without grinding the quest.",
"QUESTLINE_REWARD_INJECT = frozenset({",
"    \"Dark Moon Greatsword\",          # Ranni",
"    \"Stars of Ruin\",                 # Sellen",
"    \"Rotten Winged Sword Insignia\",  # Millicent",
"    \"Millicent's Prosthesis\",        # Millicent",
"    \"Inseparable Sword\",             # Fia / D",
"    \"Magic Scorpion Charm\",          # Seluvis",
"    \"Taker's Cameo\",                 # Volcano Manor",
"})",
"",
    ])
    c = c + block
    save(CUR, c); changed = True

# ---------------- options.py : option class + registration ----------------
o = load(OPTS); NL = nl_of(o)
qclass = NL.join([
"class DerandomizeQuestlines(Choice):",
"    \"\"\"De-randomize long NPC questlines whose chains gate only optional content.",
"",
"    Their link items are dead-weight 'progression' that crowds the priority/progression",
"    fill and can drop junk-chain keys onto important locations. Locking the chains at",
"    vanilla frees the fill and keeps important locations holding real progression.",
"    Region- and goal-gating quest items are never touched (Drawing-Room Key, Haligtree",
"    Secret Medallion, Hole-Laden Necklace).",
"",
"    - **Off:** questlines stay randomized.",
"    - **Links Only:** lock the chain LINK items at vanilla; reward checks stay randomized",
"      (good rewards like the Dark Moon Greatsword still appear shuffled). Pure fill relief.",
"    - **Full:** also pull the good terminal rewards to vanilla and re-inject a shuffled",
"      copy at the expense of one filler, so they're obtainable without doing the quest.",
"    See SPEC-questline-derando.md.\"\"\"",
"    display_name = \"De-randomize NPC Questlines\"",
"    option_off = 0",
"    option_links_only = 1",
"    option_full = 2",
"    default = 0",
"",
"",
])
o, ch = once(o, "class PoolBuilder(Toggle):", qclass + "class PoolBuilder(Toggle):",
             "options: insert DerandomizeQuestlines class", "class DerandomizeQuestlines(Choice):")
changed |= ch
o, ch = once(o, "    blessing_option: BlessingOption",
             "    blessing_option: BlessingOption" + NL + "    derandomize_questlines: DerandomizeQuestlines",
             "options: dataclass registration", "    derandomize_questlines: DerandomizeQuestlines")
changed |= ch
o, ch = once(o, "        BlessingOption," + NL + "        LocationPool,",
             "        BlessingOption," + NL + "        DerandomizeQuestlines," + NL + "        LocationPool,",
             "options: option group", "        DerandomizeQuestlines,")
changed |= ch
save(OPTS, o)

# ---------------- __init__.py : import + lock/inject block ----------------
i = load(INIT); NL = nl_of(i)
i, ch = once(i, "UPLIFT_STACKABLE_WEIGHTS, UPLIFT_KEEP_DLC",
             "UPLIFT_STACKABLE_WEIGHTS, UPLIFT_KEEP_DLC, QUESTLINE_DERANDO, QUESTLINE_REWARD_INJECT",
             "init: curation import", "QUESTLINE_DERANDO, QUESTLINE_REWARD_INJECT")
changed |= ch

anchor = "            self._lock_class_at_vanilla(lambda d: d.fragment or d.revered)"
block = NL.join([
"",
"",
"        # NPC questline de-randomization -- lock optional-only quest chains at vanilla so",
"        # they stop crowding the priority/progression fill (link items are dead-weight",
"        # progression). Region/goal-gating quest items are never in the cut set, and no",
"        # current goal requires any cut item. See SPEC-questline-derando.md.",
"        if self.options.derandomize_questlines.value:",
"            self._lock_class_at_vanilla(lambda d: d.default_item_name in QUESTLINE_DERANDO)",
"            if self.options.derandomize_questlines.value == 2:  # full: pull good rewards + reinject",
"                _present = {it.name for it in self.local_itempool} & QUESTLINE_REWARD_INJECT",
"                self._lock_class_at_vanilla(lambda d: d.default_item_name in QUESTLINE_REWARD_INJECT)",
"                for _name in sorted(_present):",
"                    _filler = next((it for it in self.local_itempool",
"                                    if it.classification == ItemClassification.filler), None)",
"                    if _filler is None:",
"                        break",
"                    self.local_itempool.remove(_filler)",
"                    self.local_itempool.append(self.create_item(_name))",
])
i, ch = once(i, anchor, anchor + block, "init: questline lock/inject block",
             "in QUESTLINE_DERANDO)")
changed |= ch
save(INIT, i)

print("[OK] questline de-randomization patch applied." if changed
      else "[OK] already applied -- no changes.")
