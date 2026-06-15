# Triage: re-expressing randomizer settings as AP-native constructs

A different lens from TRIAGE-rando-settings-for-ap.md. That doc asked "which GUI flags can we
pass through to the static randomizer." This asks the better question: **which settings are
actually Archipelago concepts in disguise** — placement, classification, starting inventory,
or logic — and can be implemented in the apworld with *no randomizer involvement at all*.

Anything answerable AP-side is strictly better: it's multiworld-correct, immune to the fork's
version lag ([[er-ecosystem-upstreams]]), and doesn't touch the restricted randomizer code.

## The boundary (the one rule)

A setting translates to an AP-native construct iff it is about one of:

- (a) **where an existing AP item lands** (placement / priority / vanilla-lock),
- (b) **whether an item is progression / useful / filler** (classification),
- (c) **what's in the starting inventory** (precollected),
- (d) **access logic** (entrance / location rules),
- (e) **whether a location is a check or excluded**.

It does NOT translate when it's about **game-side content the randomizer writes**: enemy
placement/scaling, infinite shop & material realization, param edits, EMEVD events,
cosmetics, or start-state warps. Those can only ever be a passthrough flag (the Tier-A
pattern) and stay subject to the version lag.

## The "early sphere" insight (why Pureblood translates so well)

`dlc_timing=early` ships no special API. It sets the medal to progression (line 148) and adds
a logic rule gating Altus/Caelid on it (line 868). Because AP fill must keep the seed
beatable, gating a major region on an item *forces* that item into an early sphere as a side
effect. **"Early" is emergent from a logic rule, not a placement command.** (AP also offers
`multiworld.early_items` / `local_early_items` for explicit forcing without a logic gate —
either is fine; the apworld currently prefers the logic route.)

## AP primitive toolbox the apworld already uses

| Need | Primitive | Already used at |
|---|---|---|
| Make item required | `item_table[x].classification = progression` | 128-148 (bell bearings, runes, medal) |
| Gate access | `_add_entrance_rule` / `_add_location_rule` | throughout |
| "Don't randomize" / vanilla | `place_locked_item` | 586-593 (kit, bell bearings, maps) |
| Give at start | `multiworld.push_precollected` | 569, 603, 672 |
| Force important | `all_priority_locations` (placed at 443) | 55-111 |
| Local / non-local | `self.options.local_items` | 159-175 |
| Exclude a location | `exclude_locations` + behavior option | options.py |
| Explicit early (unused) | `multiworld.early_items` | — available |
| Custom placement (free) | AP core `plando_items` | — built in |
| Pool add/remove/dupe | `create_items` | item creation |

## Class 1 — translate cleanly (do these AP-side, drop the randomizer dependency)

| Standalone setting | AP construct | Effort |
|---|---|---|
| "Randomize X — **No**" (key items / flask upgrades / bell bearings / blessings) | `place_locked_item` at the vanilla location | Low — pattern exists (587-593) |
| "Randomize X — **to important**" | add the class to `all_priority_locations` | Low |
| "Randomize X — **anywhere**" | leave in normal pool | None (default) |
| Spawn X early (early Mohgwyn / early legacy / kit early / DLC timing) | logic gate on X, or `early_items` | Low — pattern exists (868, 845) |
| Great Runes / region gating thresholds | entrance rules | Done (Tier B) |
| "Make X a progression item" (bell bearing progression) | classification | Done (128-136) |
| Give X at start (maps=give / unlock crafting kit / DLC-start upgrades) | `push_precollected` / `start_inventory` | Low — pattern exists |
| Custom item placement | AP `plando_items` | None — free in AP |
| Exclude mini-dungeon locations | `exclude_locations` + `excluded_location_behavior` | Done |
| Important-locations selection | `all_priority_locations` | Done (`important_locations`) |

These are the real opportunity: most of the Item/Logic-tab "bias" the randomizer GUI exposes
is reproducible (and already partly reproduced) with these five primitives.

**Implemented 2026-06-13:**

- Fixed the `important_locations` priority loop (a stray `break` meant only the FIRST
  selected class applied) and added a `Boss` class (`loc.boss`).
- `bell_physick_option` (start_with / do_not_randomize / randomize) for Spirit Calling Bell
  + Flask of Wondrous Physick.
- `flask_upgrade_option` (Golden Seeds + Sacred Tears) and `blessing_option` (Scadu
  Fragments + Revered Ashes) as randomize / to_important / do_not_randomize tri-states.
  do_not_randomize locks at vanilla via `_lock_class_at_vanilla` (pool-balanced) and is made
  authoritative over `important_locations` for its classes.

Remaining Class-1 item (low value): a "No / vanilla" toggle for **major key items** — they're
always progression in the pool today; locking them to vanilla is the only untranslated state.

## Class 2 — partial (logic/pool is AP-able; realization still needs a bake)

| Setting | AP-able half | Bake-only half |
|---|---|---|
| Spell shops sell spells | which spell locations are checks; spell items progression | the actual in-game shop lineup entries |
| Smithing-stone availability ~ vanilla | bell-bearing items as progression/pool | where infinite stones actually spawn/sell |
| Randomize materials (Rowa etc.) | whether material pickups are checks | the infinite material spawns themselves |
| Guaranteed copies of enemy drops | adding duplicate AP items to the pool *if those drops are AP items* | infinite enemy-drop realization |

For these the apworld can own the logic and pool decisions, but the randomizer must still
write the infinite-silo game content. Split the option: AP handles classification/checks,
randomizer bakes the world side (roughly how `material_rando` / `spell_shop_spells_only`
already straddle both).

## Class 3 — cannot translate (passthrough flag only, version-lag-bound)

No AP concept maps to these; AP's only role is shipping a bool the randomizer reads.

- Enemy randomizer: rando / scale / swap / boss names / bgm / runes / impolite / **night at
  all hours** / ignore arena / custom placement. (Tier A wired the ones that exist in source.)
- Cosmetic: gestures, ambient music, enemy colors, NPC outfits.
- Param/EMEVD QoL: Mountaintop shortcuts, Serpent-Hunter, Aging Touchables, horse blinders,
  Malenia/Gargoyle nerfs, somber-mode upgrade curve.
- DLC start (start in the DLC): game-side start state + warps; heavy, mostly non-AP.

## Recommendation

1. Treat Class 1 as the migration backlog: each is a small apworld change that *removes* a
   randomizer dependency. The "Randomize X — No / important / anywhere" tri-states for flask
   upgrades and blessings are the highest-value untranslated ones (they're pure
   place_locked_item / priority_locations work).
2. Class 2: only split if you want finer control than the c