# SPEC — NPC Questline De-randomization

## Problem

Long NPC questlines are the deepest dependency chains in the ER logic graph. Each link
item (e.g. Ranni: Carian Inverted Statue -> Miniature Ranni -> Dark Moon Ring) is classified
`progression`, so the fill must place it into a reachable spot that respects the whole
sequence. Two costs:

1. **Reachability budget.** The constrained-pool `FillError` ("glut of progression has
   nowhere reachable to land", `__init__.py` ~L531) is driven by deep chains, not raw item
   count. Questlines are the worst offenders.
2. **Priority quality.** The priority/important-locations fill grabs *any* progression item;
   it can't tell a Great Rune from "a key that unlocks a chest with a junk talisman." With
   junk-chain keys in the progression pool, important locations (boss/seedtree/etc.) get
   *them*. Pull the junk chains and important locations are left to draw real progression.

Most questlines dead-end in optional rewards, so de-randomizing them -- locking the chain at
vanilla so it's satisfied in normal play -- frees the fill at almost no cost. The reward is
not lost: you still get it by walking the quest. For the few questlines with genuinely good
terminal rewards, a `full` mode pulls the reward to vanilla too and re-injects a shuffled
copy so it stays findable without grinding the quest.

## Mechanism

Existing lever `_lock_class_at_vanilla(predicate)` (`__init__.py` ~L1630): for every
available location matching the predicate, it places the location's vanilla item there
locked and removes that item from `local_itempool` -- count-neutral. It keys on
`location.data`, so a predicate of `d.default_item_name in CUTSET` cuts by item name with
no per-location tagging. Called from `_fill_local_items` (~L1491), invoked inside
`create_items` after `local_itempool` is built -- so the pool is mutable for injection.

## Safety analysis (why these are safe to cut)

- **No goal needs them.** ER goals are final_boss / elden_beast / all_remembrances /
  all_bosses / capital / messmer / godrick. There is **no** frenzied / death / star-ending
  goal, and no `completion_condition` references any cut item. So the cut is unconditional.
  *(If a frenzied/death/star ending goal is ever added, revisit Shabriri Grape, Cursemark of
  Death, Seedbed Curse and the Ranni items -- gate them on the goal then.)*
- **No region depends on them.** Traced every cut item's `has()` references in the logic.
  All cut items gate only `_add_location_rule` checks (optional). The three quest items that
  gate `_add_entrance_rule` (regions) are **exempt** and deliberately excluded:
  - `Drawing-Room Key` -> Volcano Manor (+ Dungeon)
  - `Haligtree Secret Medallion (Left)` (and Right) -> Hidden Path / Gravesite Plain
  - `Hole-Laden Necklace` -> Cathedral of Manus Metyr (DLC)
- **Unique items only.** Multi-location consumables (`Starlight Shards` x28,
  `Seedbed Curse` x6, `Shabriri Grape` x3, and the x2 DLC items) are excluded -- a name-keyed
  cut would also de-randomize their many non-quest spots. Only count==1 location-defaults are
  cut.

## Cut list (`curation.py` -> `QUESTLINE_DERANDO`)

Sellen: Sellen's Primal Glintstone, Sellian Sealbreaker, Academy Glintstone Key (Thops).
Ranni: Carian Inverted Statue, Miniature Ranni, Dark Moon Ring, Fingerslayer Blade.
Seluvis: Seluvis's Potion, Amber Draught, Amber Starlight, Dancer's Castanets.
Volcano Manor / Rya: Rya's Necklace, Serpent's Amnion, Lord of Blood's Favor.
Millicent: Unalloyed Gold Needle (Broken / Fixed / Milicent), Valkyrie's Prosthesis.
Fia / D / Rogier: Weathered Dagger, Black Knifeprint, Cursemark of Death.
DLC: Secret Rite Scroll.

## Good-reward inject set (`QUESTLINE_REWARD_INJECT`, full mode)

Dark Moon Greatsword (Ranni), Stars of Ruin (Sellen), Rotten Winged Sword Insignia +
Millicent's Prosthesis (Millicent), Inseparable Sword (Fia/D), Magic Scorpion Charm
(Seluvis), Taker's Cameo (Volcano Manor). All verified to exist as unique location-defaults.

## Option (`options.py` -> `DerandomizeQuestlines`, default off)

- **off (0)** -- unchanged.
- **links_only (1)** -- lock `QUESTLINE_DERANDO` at vanilla. Reward checks stay randomized;
  good rewards remain shuffled naturally (their locations are untouched, so the item still
  floats in the pool). Pure fill relief; player still claims reward checks by questing.
- **full (2)** -- also lock `QUESTLINE_REWARD_INJECT` locations at vanilla, then for each
  reward actually pulled, swap one filler item in `local_itempool` for a shuffled copy
  (count-neutral). The good item is then obtainable from any check without doing the quest.

## Counts impact

`links_only` removes ~22 link progression items from the supply (the dead-weight) and frees
their chains. Important-locations priority then draws from cleaner progression (runes, locks,
medallions) instead of junk-chain keys. `full` additionally vacates the good-reward checks
and re-injects 7 items 1:1 against filler.

## Testing

1. Apply on Windows: `python patch_apworld_questline_derando.py` (repo root). Idempotent.
2. Gen-test off / links_only / full, DLC on and off.
3. Spoiler checks: links_only -> cut link items sit at vanilla locations; reward items still
   randomized. full -> reward items at vanilla AND a shuffled copy elsewhere; filler count
   down by the number injected.
4. Confirm region access intact: Volcano Manor, Haligtree, Cathedral of Manus Metyr all
   still reachable (their gating keys were exempted).
5. all_bosses / all_remembrances goals still solvable (no cut item gates a required boss).

## Future extensions

- Add DLC questline links once the x2-location items are disambiguated (Thiollier's
  Concoction, Iris of Grace/Occultation, Letter for Freyja).
- `full` mode currently leaves junk reward checks randomized; an optional junk-reward cut
  list could vacate those too once enumerated.
- If a frenzied/death/star ending goal lands, gate the relevant chains on the goal.
