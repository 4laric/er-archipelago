#!/usr/bin/env python3
r"""
patch_apworld_soft_consumables.py

Two related cleanups for the "fun consumable" progression clutter:

  soft_consumable_shop (Toggle, default off)
    Stonesword Keys + Dragon Hearts become infinitely buyable at the Twin Maiden Husks
    (the baker injects the shop rows -- see patch_baker_soft_consumable_shop). The apworld
    pulls every key/heart variant from the pool and makes _has_enough_keys / _has_enough_hearts
    return True (the shop is always reachable at Roundtable), which ALSO closes the latent
    nokey=True access gap on the imp-statue seals / Caelid Dragon Communion checks.
    NOTE: ship this ONLY together with the baked shop -- removing keys/hearts from the pool
    without the shop would leave seals unopenable in-game. Hearts untouched under dlc_only
    (that path precollects its own 25).

  derandomize_gurranq (Toggle, default off)
    The Gurranq deathroot ladder is 10 MISSABLE rewards behind a blind cumulative gate. Lock
    them all at vanilla, precollect 9 Deathroot so the has(Deathroot,N) rules stay reachable,
    pull Deathroot from the pool, and re-inject the 3 keepers (Clawmark Seal, Beastclaw
    Greathammer, Ancient Dragon Smithing Stone) 1:1 against filler so the good stuff stays
    shuffled instead of missable-Gurranq-only. apworld-only; safe to ship standalone.

Run on Windows from the repo root:  python patch_apworld_soft_consumables.py
Idempotent; asserts every anchor (fails loudly rather than corrupting).
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

# ================= options.py =================
o = load(OPTS); NL = nl_of(o)
qcls = NL.join([
"class SoftConsumableShop(Toggle):",
"    \"\"\"Sell Stonesword Keys and Dragon Hearts in unlimited supply at the Twin Maiden Husks",
"    (Roundtable Hold) instead of scattering them through the world.",
"",
"    They gate imp-statue seals and the Dragon Communion shops but are otherwise 'progression'",
"    only by classification, which drags them into the priority/progression fill. With this on",
"    they leave the randomized pool, the key/heart logic gates are satisfied by the always-",
"    reachable shop, and the latent nokey access gap on those checks is closed. REQUIRES the",
"    baked Twin Maiden shop rows (patch_baker_soft_consumable_shop) -- don't enable without it.\"\"\"",
"    display_name = \"Soft-Consumable Shop (Twin Maiden keys/hearts)\"",
"",
"class DerandomizeGurranq(Toggle):",
"    \"\"\"De-randomize Gurranq's deathroot ladder -- 10 missable rewards behind a blind cumulative",
"    deathroot gate. Locks the ladder at vanilla and re-injects the three keepers (Clawmark Seal,",
"    Beastclaw Greathammer, Ancient Dragon Smithing Stone) into the shuffled pool so the good",
"    rewards stay obtainable (and stop being missable) while Deathroot leaves the pool. The seven",
"    mediocre beast incantations/AoW go vanilla. See SPEC-soft-consumables.md.\"\"\"",
"    display_name = \"De-randomize Gurranq Deathroot Ladder\"",
"",
"",
])
o, ch = once(o, "class PoolBuilder(Toggle):", qcls + "class PoolBuilder(Toggle):",
             "options: insert classes", "class SoftConsumableShop(Toggle):"); changed |= ch
o, ch = once(o, "    blessing_option: BlessingOption",
             "    blessing_option: BlessingOption" + NL +
             "    soft_consumable_shop: SoftConsumableShop" + NL +
             "    derandomize_gurranq: DerandomizeGurranq",
             "options: dataclass", "    soft_consumable_shop: SoftConsumableShop"); changed |= ch
o, ch = once(o, "        BlessingOption,",
             "        BlessingOption," + NL + "        SoftConsumableShop," + NL + "        DerandomizeGurranq,",
             "options: option group", "        SoftConsumableShop,"); changed |= ch
save(OPTS, o)

# ================= __init__.py =================
i = load(INIT); NL = nl_of(i)

# 1) _has_enough_keys -> True when shop on
i, ch = once(i,
    '        return (state.count("Stonesword Key", self.player) + (state.count("Stonesword Key x3", self.player) * 3) + (state.count("Stonesword Key x5", self.player) * 5)) >= req_keys',
    '        if self.options.soft_consumable_shop.value:' + NL + '            return True' + NL +
    '        return (state.count("Stonesword Key", self.player) + (state.count("Stonesword Key x3", self.player) * 3) + (state.count("Stonesword Key x5", self.player) * 5)) >= req_keys',
    "init: _has_enough_keys guard", "soft_consumable_shop.value:" + NL + "            return True" + NL +
    '        return (state.count("Stonesword Key"'); changed |= ch

# 2) _has_enough_hearts -> True when shop on
i, ch = once(i,
    '        return (state.count("Dragon Heart", self.player) + (state.count("Dragon Heart x3", self.player) * 3) + (state.count("Dragon Heart x5", self.player) * 5)) >= req_hearts',
    '        if self.options.soft_consumable_shop.value:' + NL + '            return True' + NL +
    '        return (state.count("Dragon Heart", self.player) + (state.count("Dragon Heart x3", self.player) * 3) + (state.count("Dragon Heart x5", self.player) * 5)) >= req_hearts',
    "init: _has_enough_hearts guard",
    'soft_consumable_shop.value:' + NL + '            return True' + NL + '        return (state.count("Dragon Heart"'); changed |= ch

# 3) generate_early: pool-skip (after merchant-bell block)
mb_anchor = (
'        if self.options.merchant_bell_logic.value == 1:' + NL +
'            for _bell in merchant_bell_names(bool(self.options.enable_dlc)):' + NL +
'                item_table[_bell].skip = False' + NL +
'                item_table[_bell].classification = ItemClassification.progression')
ge_block = NL + NL + NL.join([
"        # Soft-consumable shop / Gurranq de-rando: pull these from the randomized pool BEFORE",
"        # create_items builds it. Keys/hearts become Twin Maiden shop stock; Deathroot is locked",
"        # vanilla at the Gurranq ladder (see _fill_local_items). SPEC-soft-consumables.md.",
"        if self.options.soft_consumable_shop.value:",
"            for _vn in (\"Stonesword Key\", \"Stonesword Key x3\", \"Stonesword Key x5\"):",
"                if _vn in item_table: item_table[_vn].skip = True",
"            if not self.options.dlc_only:  # dlc_only precollects its own 25 hearts",
"                for _vn in (\"Dragon Heart\", \"Dragon Heart x3\", \"Dragon Heart x5\"):",
"                    if _vn in item_table: item_table[_vn].skip = True",
"        if self.options.derandomize_gurranq.value:",
"            if \"Deathroot\" in item_table: item_table[\"Deathroot\"].skip = True",
])
i, ch = once(i, mb_anchor, mb_anchor + ge_block, "init: generate_early pool-skip",
             "Soft-consumable shop / Gurranq de-rando: pull these"); changed |= ch

# 4) _fill_local_items: Gurranq lock + precollect + inject (after the fragment/revered lock line)
fr_anchor = "            self._lock_class_at_vanilla(lambda d: d.fragment or d.revered)"
gur_block = NL + NL.join([
"",
"        # Gurranq deathroot-ladder de-randomization (SPEC-soft-consumables.md). Lock all 10",
"        # reward checks at vanilla, precollect 9 Deathroot so the has(Deathroot,N) rules stay",
"        # reachable (Deathroot left the pool in generate_early), and re-inject the 3 keepers",
"        # 1:1 against filler so they stay shuffled instead of missable Gurranq-only.",
"        if self.options.derandomize_gurranq.value:",
"            _gur_locs = {",
"                \"DB/(BS): Clawmark Seal - Gurranq, deathroot reward 1\",",
"                \"DB/(BS): Beast Eye - Gurranq, deathroot reward 1 or kill Gurranq\",",
"                \"DB/(BS): Bestial Sling - Gurranq, deathroot reward 2\",",
"                \"DB/(BS): Bestial Vitality - Gurranq, deathroot reward 3\",",
"                \"DB/(BS): Ash of War: Beast's Roar - Gurranq, deathroot reward 4\",",
"                \"DB/(BS): Beast Claw - Gurranq, deathroot reward 5\",",
"                \"DB/(BS): Stone of Gurranq - Gurranq, deathroot reward 6\",",
"                \"DB/(BS): Beastclaw Greathammer - Gurranq, deathroot reward 7\",",
"                \"DB/(BS): Gurranq's Beast Claw - Gurranq, deathroot reward 8\",",
"                \"DB/(BS): Ancient Dragon Smithing Stone - Gurranq, deathroot reward 9 or kill Gurranq\",",
"            }",
"            for _ in range(9):",
"                self.multiworld.push_precollected(self.create_item(\"Deathroot\"))",
"            self._lock_class_at_vanilla(lambda d: d.name in _gur_locs)",
"            for _kp in (\"Clawmark Seal\", \"Beastclaw Greathammer\", \"Ancient Dragon Smithing Stone\"):",
"                _filler = next((it for it in self.local_itempool",
"                                if it.classification == ItemClassification.filler), None)",
"                if _filler is None:",
"                    break",
"                self.local_itempool.remove(_filler)",
"                self.local_itempool.append(self.create_item(_kp))",
])
i, ch = once(i, fr_anchor, fr_anchor + gur_block, "init: Gurranq lock/inject block",
             "Gurranq deathroot-ladder de-randomization"); changed |= ch
save(INIT, i)

print("[OK] soft-consumables patch applied." if changed else "[OK] already applied -- no changes.")
