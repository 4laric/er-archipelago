# NOTES -- legible key-named locks: assessment (options-cleanup workstream)

Decision: **STAGE, do not refactor tonight.** The display-name half already ships behind an
opt-in toggle; making *key-named region locks the mechanism* is a deep change that retires the
synthetic-lock model and touches fill + the client contract. Below is the concrete state and an
implementation plan for Alaric's sign-off.

## What already exists and is WIRED (naming only)
- `greenfield/eldenring/features/legible_keys.py` -- a pure map
  `CAPSTONE_VANILLA_KEYS: {boss_label -> vanilla key display name}` (Academy Glintstone Key,
  Dectus Medallion, Haligtree Secret Medallion, Pureblood Knight's Medal, Fingerslayer Blade,
  Deathroot, Messmer's Kindling, ...). Bosses with no real vanilla capstone key fall back to the
  synthetic `Boss Key: <label>`.
- It is consumed by `features/boss_locks.py`: when the **`boss_keys`** option is ON (default OFF),
  boss_locks emits a `display_key` field per gated boss for those with a vanilla key. This is a
  **display/messaging layer only** -- fill, item allocation, and the gating item all still key on
  the synthetic `Boss Key: <label>` name.
- Covered by `tests/test_gf_legible_keys.py` (every map key joins a real boss label; fallbacks
  hold; inverse resolver round-trips). Deterministic, passing.

So: **legible names for BOSS keys are done and test-covered, gated behind `boss_keys`.** The
kitchen-sink preset turns `boss_keys` on, so it exercises this path.

## What is NOT done (the deep refactor the spec ultimately wants)
`SPEC-region-capstone-model-20260708.md` + `WIRING-region-capstone-v0.2.md` describe making each
region resolve on a **capstone boss gated by a real vanilla key item**, with the synthetic
`<Region> Lock` renamed to that key (Dectus/Rold/Academy Glintstone Key/Two Great Runes/...). That
is materially bigger than the naming layer:

1. **Item catalog + fill.** Region progression today is 21-ish synthetic `<Region> Lock` items
   (`core.create_items`, `_core_item_ids`). Renaming them to vanilla keys means the AP item names,
   `item_name_to_id` ids, and everything that joins on `" Lock"` (tests, curated_fill big-ticket
   tagging, start_with_region_lock precollect, goal `has_all(<Region> Lock)`) must move together.
   Several regions have **no** legible vanilla key (Godrick/Grafted, Dancing Lion, Romina,
   Rellana, ...), so a mixed model (some key-named, some synthetic) or a fabricated key is
   unavoidable -- the model is not uniform, which is exactly the fragile part.
2. **Threshold Rule granularity.** The spec also re-carves regions (fold-in vs legacy-dungeon vs
   ride-along). That changes `region_spine.py` / `region_map.csv` and the generated `data.py`,
   `boss_data.py`, `boss_sweeps.py`. It is a gen_data.py change, not an options change.
3. **Client contract.** The client grants/gates on item names + flags; renamed locks would need a
   contract key or a stable synthetic->display alias so `contract.py` + the Rust client agree, or
   the client silently mis-grants. (See the memory note on contract-subdict dark features.)
4. **Compound / possession gates.** "Two Great Runes" and "N Deathroot" are *count* gates, not a
   single key -- they don't map to one AP progression item cleanly.

## Recommendation
- **Keep tonight's scope to presets + the display layer.** The boss-key legible NAMES already work
  and are the safe, player-visible win; presets that want them just set `boss_keys: true`.
- **Do NOT flip region locks to key-named items now** -- it retires the synthetic-lock mechanism,
  spans gen_data + fill + client contract, and can't be fully test-covered in one pass. It belongs
  with the region-capstone/Threshold-Rule work (its own branch), where `data.py`/`boss_data.py`
  regen and the client contract move together.
- If desired as an incremental step: extend the **display-only** aliasing to region locks too (a
  `display_lock` slot_data field resolved from a region->vanilla-key map, mechanism unchanged),
  mirroring how `display_key` already works for boss keys. That is additive and testable, and does
  not retire the synthetic mechanism. Flagged here as the smallest safe next increment, for
  Alaric's call.

## Not changed by this workstream
No files under `features/legible_keys.py`, `boss_locks.py`, or the generators were modified for
legible locks. The only code edit in this branch is a docstring correction in
`features/start_grace.py` (start_with_region_lock said "On by default"; it is a plain Toggle =
OFF, and the tests assert OFF -- corrected to match).
