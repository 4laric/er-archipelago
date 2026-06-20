# Moore shop collapse — root cause + fix spec (2026-06-16)

Status: **diagnosed from the deployed apconfig + scrape; fix is C# (needs Windows build).**
Author note: written without a compile/test env, so the *exact* merge line is flagged "TO CONFIRM"
below — everything above it is verified from data in the repo.

## Symptom
- In-game: Moore's shop sells **vanilla** items (no `[Placeholder]`), and a purchase mis-reports.
- Deployed `apconfig_*.json` `location_flags`: Moore's **13 grocery checks all map to game flag 320500**,
  his **12 Thiollier/poison checks all map to 320700**. 25 AP checks riding on 2 flags.

## Confirmed mechanism
1. **Per-row identity exists at the param level.** `vanilla_er/vanilla_er/ShopLineupParam.csv`:
   row `102250 -> eventFlag_forStock 320500`, `102260 -> 320600`, `102270 -> 320700`, … all distinct.
2. **The scraper makes a per-row ItemScope.** `EldenLocationDataScraper.cs` shop loop (~L318-467) reads each
   row's `eventFlag_forStock` (L337) and builds `new ItemScope(EVENT, stockFlag)` per row (L454). Good so far.
3. **A later step MERGES Moore's rows into one "unique location."** `diste/Base/itemslots.txt` has exactly
   **one** Key for the 13 grocery rows: `'614542,0:0000000000:102250:'` with 13 item sub-lines, and
   DebugText "Unique location in […m61_45_42 (Belurat Main Gate Cross)…]". `614542` == Moore's map tile
   m61_45_42. The merged `LocationScope` serializes (LocationData.cs L219-225, `OnlyShops -> id=0`, keyed by
   `ShopIds`) with `ShopIds = {102250}` (representative row only). The poison block is the second Key
   `'614542,0:0000000000:102250,102270,2045429330:'` (12 rows).
4. **The apworld mirrors the merge.** `locations.py` gives all 13 grocery `ERLocationData` the same key
   `'614542,0:0000000000:102250:'`, and all 12 poison ones the `…:102250,102270,2045429330:` key.
5. **So `ArchipelagoForm` binds all 13 AP locations to the ONE scope**, `writer.Write` fills its single
   representative row (102250, flag 320500), the other 12 rows keep vanilla, and `ApLocationFlags` stamps all
   13 with 320500. Same for the 12 poison → 320700.
6. **More ShopIds does NOT fix it** — the poison block already has 3 ShopIds (`102250,102270,2045429330`) and
   still collapses 12→320700. Multiple ShopIds are treated as quest-state *mirrors* of one slot, not N slots.

Net: a shop **scope = one writable slot**. Moore has 25 AP checks on 2 slots → 23 are structurally dead.

## TO CONFIRM in the build env (decides the exact diff)
Where exactly the per-row ItemScopes (step 2) get merged into the one tile-keyed `LocationScope` (step 3).
Run the scraper with a debug print of `LocationScope -> member shopIDs` for shopIDs `102250..102266`:
- If they land in **one** merged scope → the merge is in C# (the "unique location"/`OnlyShops` grouping that
  forms `LocationScope`s from `ItemScope`+`LocationKey`). → **Option A** below.
- If they're actually **distinct** scrape scopes and only the apworld shares the key → the fix is apworld
  per-row keys (no C# build). itemslots showing a single Key argues against this, but the print settles it.

## Fix options

### Option A — scraper (correct, general; needs C# build + itemslots regen)
Stop merging shop rows at the same NPC/tile into one `LocationScope`. Each row already has its own
`ItemScope(EVENT, stockFlag)` (L454); keep them as distinct location scopes (one shop slot = one check).
- Files: `EldenLocationDataScraper.cs` (the unique-location/`OnlyShops` grouping that builds the final
  `LocationScope`s) and `LocationData.cs` L219-225 (the `OnlyShops -> id=0, key=ShopIds` collapse).
- Ripple: regenerates `diste/Base/itemslots.txt` with **per-row** shop keys; `apworld locations.py` shop keys
  must be regenerated to match (otherwise they unbind). Affects every shop (Kalé, nomads, Twin Maidens, Enia).
- Re-verify base-game seeds bind cleanly (`ap_bind_diag` unbound count).

### Option B — AP layer (contained, shops-only; still C#)
In `ArchipelagoForm.cs` (~L472, the `foreach (info in locations)` that builds `items`): when >1 AP location
resolves to the same shop scope, fan them out across the scope's sibling rows instead of stacking under one
`SlotKey`. The sibling rows + their stock flags are recoverable from the scrape's per-item row list (each
itemslots item line names its `shop NNNNN`), even though the merged scope only carries `ShopIds={102250}`.
- Pro: no itemslots/apworld-key regen, shops-only blast radius.
- Con: you re-derive per-row membership the merge discarded; ApLocationFlags must stamp each with its own row
  `eventFlag_forStock` (320500, 320600, …) so the client polls them independently.

**Recommendation:** Option A is the right long-term fix (every shop becomes correct), but bigger blast
radius. If you want Moore (and shops) un-broken in one contained pass first, do Option B.

## Verification (either option)
- Re-gen + rebake. In the new `apconfig`, Moore's items map to ~25 **distinct** event flags — no 13→320500 /
  12→320700 cluster. (Re-run the `location_flags` value-collision check.)
- `ap_bind_diag`: no new unbound keys.
- In-game: Moore's stock shows `[Placeholder]` items; buying each reports its own check exactly once.

## Related
- Bell Bearing `skip=True` already removed (items.py:2665) — gives the Roundtable Twin-Maidens route, but it
  pulls the SAME rows, so it only matters once this collapse is fixed.
- Memory: `er-moore-shop-rando-idea`.
