# Reference: ER randomizer GUI settings under Archipelago

Indexes every setting in the standalone "Elden Ring Item and Enemy Randomizer" GUI (v0.11.4)
against what actually happens when the randomizer runs in **Archipelago mode**.

## The one thing to understand first

In AP mode you do not configure placement through this GUI. The flow
(`ArchipelagoForm.RandomizeForArchipelago`) is:

1. Read the location->item map AP already decided from `slot_data["apIdsToItemIds"]`.
2. `permutation.Forced(items, ...)` — hard-stamp those assignments.
3. `permutation.Logic(random, opt, null, [INFINITE, INFINITE_SHOP, INFINITE_GEAR,
   INFINITE_CERTAIN, MIXED])` — note the **FINITE silo is excluded**.

Standalone instead calls `perm.Logic(random, opt, preset)` with **no silo restriction**, so
it randomizes FINITE (key items + unique-location items) itself, applying the Bias slider,
important-location targeting, and key-item difficulty.

**Consequence:** everything on the Item Randomizer / Logic tabs that shapes *where finite
items go* is dead under AP — Archipelago's own fill owns that. The randomizer still runs the
INFINITE silos (infinite shop/gear/material entries that are not AP checks) with
`opt.Difficulty` hard-coded to 50, plus the enemy pass and a few baked QoL flags.

`ConvertRandomizerOptions` (ArchipelagoForm.cs:834-927) is the entire list of GUI-equivalent
options that survive into AP — anything not in it is bypassed or baked to a default.

## Status legend

- **AP fill** — placement decided by Archipelago; GUI control has no effect.
- **YAML: `<option>`** — re-implemented as an apworld YAML option (this is your real knob).
- **Hardcoded `<val>`** — forced in `ConvertRandomizerOptions` regardless of GUI.
- **Bypassed** — not wired into AP at all; the GUI checkbox does nothing under AP.
- **Baked** — fixed by the apworld's bake (locations.py / apconfig), not user-tunable.

---

## Item Randomizer tab

| GUI setting | Under Archipelago |
|---|---|
| **Bias** slider (default 20%) | **AP fill.** No effect. AP's fill_restrictive decides finite placement; the closest analogues are the apworld's important-location priority + AP's generic `progression_balancing`. |
| Which locations are important — Vanilla major key item locs / Major bosses / Other bosses / Seed trees & Tear Churches / Merchant shops / Shadow Realm Blessing pickups | **Baked + YAML: `important_locations`.** Which of these *exist as checks* is fixed by locations.py; which ones are forced to hold important items is the `important_locations` list (Remembrance/Seedtree/Map/Basin/Church/Fragment/Cross/Revered/KeyItem). |
| Exclude mini-dungeon locations | **AP fill / `exclude_locations`.** Use AP exclusion + `excluded_location_behavior`, not this box. |
| Major key items randomized? (important / anywhere / No) | **AP fill.** Key items are always in the AP pool; placement is AP's. |
| Flask upgrades randomized? (golden seeds / sacred tears) | **Baked.** They're AP checks per locations.py; the toggle is bypassed. |
| Upgrade Bell Bearings randomized? | **YAML: `smithing_bell_bearing_option`** (randomize / progression / do-not). |
| Shadow Realm Blessings randomized? (Scadu fragments / Revered ashes) | **Baked + `important_locations`** (Fragment / Revered classes). |
| Spell shops still sell spells | **YAML: `spell_shop_spells_only`.** |
| Smithing Stone availability similar to vanilla | **Baked / `smithing_bell_bearing_option`.** |
| Randomize collectible materials like Rowa Fruit | **YAML: `material_rando`** (default on). |
| Add guaranteed copies of random enemy drops | **Bypassed.** |
| Place Shadow Realm Blessings in DLC only | **Baked** (follows `enable_dlc`). |
| Custom item placement | **AP fill.** Bypassed entirely. |

---

## Logic tab

| GUI setting | Under Archipelago |
|---|---|
| Great Runes to access final boss | **YAML-ish.** Final-boss gating is `ending_condition` + great-rune logic, not a direct count knob. |
| Great Runes to enter Leyndell | **YAML: `great_runes_required`** (1-7, default 2). The real knob. |
| Great Runes to enter Mountaintops | **Baked** (apworld region logic). |
| Deathless routing | **Bypassed.** Missable handling is `missable_location_behavior` instead. |
| Hints: purchase markers from Kalé (required areas / exact locations) | **Bypassed.** AP has its own hint system. |
| Early legacy dungeons available early | **YAML: `early_legacy_dungeons`.** |
| Early Mohgwyn Palace | **Bypassed.** |
| Randomize base game and DLC key items separately | **Baked** (handled by `enable_dlc` + DLC logic). |
| Randomize Lamenter's Gaol Keys | **Bypassed.** |
| Total / Required Messmer's Kindling Shards | **YAML: `messmer_kindle` / `messmer_kindle_max` / `messmer_kindle_required`.** |

---

## Enemy Randomizer tab

Whole tab gates on **YAML: `enemy_rando`**. When on, the AP path sets a fixed flag set
(ArchipelagoForm.cs:893-908); the rest of the tab is bypassed.

| GUI setting | Under Archipelago |
|---|---|
| (master) Enemy Randomizer | **YAML: `enemy_rando`.** |
| Scale up/down enemy health/damage | **YAML: `scale_enemies`** -> `opt["scale"]`. |
| Scale multi-phase bosses slightly | **Hardcoded true** (`opt["phasehp"]`). |
| Edit boss names | **Hardcoded true** (`opt["editnames"]`). |
| Randomize boss background music | **Hardcoded true** (`opt["bossbgm"]`). |
| Change boss runes when boss changes | **Bypassed.** |
| Swap bosses between multi-boss fights | **Bypassed.** |
| **Spawn night bosses at all hours** | **Bypassed.** (This is the "night bosses always present" toggle from earlier — confirmed not wired into AP.) |
| Custom enemy placement / Ignore arena size / Impolite enemies | **Bypassed.** |
| "Replacing X: Y" class-pool mappings | **Baked** (each class replaced by same class). |
| Separate enemy seed / reroll separately | **Baked** (apworld supplies the enemy seed/preset). |
| (implicit) Disable Malenia heal-on-hit / Gargoyle poison | **Hardcoded true** (`nerfmalenia`, `nerfgargoyles`) when enemy rando is on. |

---

## DLC tab

Whole tab gates on **YAML: `enable_dlc`**.

| GUI setting | Under Archipelago |
|---|---|
| (master) DLC | **YAML: `enable_dlc`.** |
| Randomize DLC and base game together / separately | **Baked** (DLC key-item separation handled in logic). |
| Upgrade all weapons in DLC to max level | **Bypassed.** |
| Abyssal Woods horse blinders | **Bypassed.** |
| Aging Touchables | **Bypassed.** |
| Randomize spiritspring seals | **Bypassed.** |
| DLC Start (Normal / DLC Start / DLC Start with base game) | **Bypassed** (AP assumes Normal progression). Timing of *needing* the DLC is **YAML: `dlc_timing`** (early/off/late). |
| DLC Start extras (base game shop / care package / rune level / Roundtable) | **Bypassed.** |
| DLC Start upgrades (give flasks / pouches / stones / bell bearings) | **Bypassed.** |

---

## Misc Options tab

| GUI setting | Under Archipelago |
|---|---|
| Randomize starting class loadouts | **YAML: `random_start`** (note: starting-loadout porting to DLC-era CharaInitParam was incomplete — verify it actually applies). |
| ↳ two-handing / one-handable / unwieldable / allow stat changes / DLC-only | **Bypassed** (sub-options not exposed). |
| Randomize starting keepsakes | **Bypassed.** |
| Randomize NPC outfits | **Hardcoded false** (`opt["nooutfits"]=true`). |
| Randomize ambient music | **Bypassed.** |
| Randomize gestures | **Bypassed.** |
| Randomize enemy colors | **Bypassed.** |
| Remove all weapon and spell requirements | **YAML: `no_weapon_requirements`** -> `opt["weaponreqs"]`. |
| Unrestricted item placement for Fog Gate Rando | **Bypassed.** |
| Dungeon Crawl mode | **Bypassed.** |
| Disable upgrading Serpent-Hunter | **Bypassed.** |
| Alternate item placement for RandoMania | **Bypassed.** |
| Unlock all map fragments and icons at start | **YAML: `map_option`** (randomize / give / do-not). |
| Unlock all craftable items in Crafting Kit | **YAML: `crafting_kit_option`** (randomize / early / do-not). |
| Disable Malenia's heal-on-hit | **Hardcoded true** when enemy rando on (`nerfmalenia`). |
| Disable damage tick in Valiant Gargoyles' poison | **Hardcoded true** when enemy rando on (`nerfgargoyles`). |
| Reduce upgrade cost for non-somber weapons | **Hardcoded true** (`opt["sombermode"]=true`). |
| Add shortcuts in Mountaintops | **Bypassed.** |
| Enable RandomizerCrashFix.dll | Used/recommended for AP runs; not an AP-tunable. |
| Enable RandomizerHelper.dll (auto-equip / auto-upgrade) | **YAML: `auto_equip` / `auto_upgrade`.** |

---

## AP-only options (no GUI equivalent)

These exist only in the apworld YAML and have no checkbox in the standalone GUI:

`ending_condition`, `world_logic` (region_lock / region_bosses / region_lock_bosses /
open_world), `region_boss_percent`, `region_boss_type`, `soft_logic`, `royal_access`,
`local_item_option` + `exclude_local_item_only`, `exclude_locations` +
`excluded_location_behavior`, `missable_location_behavior`, `dungeon_sweep`, `death_link`.

## Bottom line on bias

The randomizer's placement bias (the 20% slider, important-location targeting, key-item
difficulty, pool restrictions) is **entirely overwritten under AP** — those only act on the
FINITE silo, which AP excludes. Your real placement controls under AP are the apworld YAML:
`important_locations`, `excluded_location_behavior`, `missable_location_behavior`,
`local_item_option`, plus AP-core `progression_balancing` / `accessibility`. The standalone
randomizer keeps autonomy only over infinite-pool items (at Difficulty 50) and the enemy
pass.
