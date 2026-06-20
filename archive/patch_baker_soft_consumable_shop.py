#!/usr/bin/env python3
r"""
patch_baker_soft_consumable_shop.py  (run on Windows from the repo root)

Baker half of soft_consumable_shop (apworld half = patch_apworld_soft_consumables.py).
Adds infinite-stock Twin Maiden Husks rows for Stonesword Key (8000 @ 2000 runes) and
Dragon Heart (10060 @ 5000 runes) when the apworld emits soft_consumable_shop=true.

Two edits in SoulsRandomizers/RandomizerCommon:
  ArchipelagoForm.cs   -- map the bool into RandomizerOptions (opt["soft_consumable_shop"]).
  PermutationWriter.cs -- in Write(), clone Twin Maiden goods row 101802 (Spirit Calling Bell,
                          always-stocked) into gap ids 101882/101883 and override item/price/
                          stock. equipType/costType inherited from the template (goods/runes).

Idempotent; asserts every anchor. After running: rebuild SoulsRandomizers (Release) + bake.
VERIFY in-game: the two rows appear in the Twin Maiden shop at 2000 / 5000 and are infinite.
"""
import os
ROOT = os.path.dirname(os.path.abspath(__file__))
RC   = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon")
AF   = os.path.join(RC, "ArchipelagoForm.cs")
PW   = os.path.join(RC, "PermutationWriter.cs")

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

# ---- ArchipelagoForm.cs: map option into opt ----
a = load(AF); NL = nl_of(a)
a, ch = once(a,
    "            return opt;",
    '            opt["soft_consumable_shop"] = archiOptions.GetValueOrDefault("soft_consumable_shop", false);' + NL +
    "            return opt;",
    "ArchipelagoForm: map soft_consumable_shop", 'opt["soft_consumable_shop"] = archiOptions'); changed |= ch
save(AF, a)

# ---- PermutationWriter.cs: inject infinite Twin Maiden rows ----
p = load(PW); NL = nl_of(p)
anchor = "                // End Elden Ring edits"
block = NL.join([
"                // Soft-consumable shop: sell Stonesword Keys + Dragon Hearts in unlimited",
"                // supply at the Twin Maiden Husks (Roundtable). Clone 101802 (Spirit Calling",
"                // Bell -- a goods row that's always stocked) so equipType/costType are correct,",
"                // then override item/price/stock. Pairs with apworld soft_consumable_shop, which",
"                // pulls these from the pool + makes _has_enough_keys/_has_enough_hearts True.",
"                if (opt[\"soft_consumable_shop\"])",
"                {",
"                    void AddTwinMaidenInfinite(int newId, int goodsId, int price)",
"                    {",
"                        PARAM.Row r = game.AddRow(\"ShopLineupParam\", newId, 101802);",
"                        r[\"equipId\"].Value = goodsId;",
"                        r[\"value\"].Value = price;",
"                        r[\"mtrlId\"].Value = -1;                  // no material cost",
"                        r[\"sellQuantity\"].Value = (short)-1;     // -1 = infinite stock",
"                        r[\"eventFlag_forStock\"].Value = (uint)0; // always stocked",
"                        r[\"eventFlag_forRelease\"].Value = (uint)0;",
"                    }",
"                    AddTwinMaidenInfinite(101882, 8000, 2000);    // Stonesword Key @ 2000 runes",
"                    AddTwinMaidenInfinite(101883, 10060, 5000);   // Dragon Heart   @ 5000 runes",
"                }",
"",
])
p, ch = once(p, anchor, block + anchor, "PermutationWriter: inject Twin Maiden rows",
             "AddTwinMaidenInfinite"); changed |= ch
save(PW, p)

print("[OK] baker soft-consumable shop patch applied." if changed else "[OK] already applied -- no changes.")
