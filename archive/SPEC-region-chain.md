# SPEC: region keys + bundled grace unlock ("region fusion")

Status: APWORLD HALF DONE, client half pending. (Alaric, 2026-06-13, after playtest 3.)
Goal: turn ER's "everything is sphere 1" open world into real spheres so checks/hints have
shape -- WITHOUT making the player ride Torrent forever.

## What's built (2026-06-13, apworld side)

- **Logic half = the existing `region_lock`.** It already does per-region `.lock` items with
  emergent/shuffled order -- exactly the "per-region key, mix up the order" design. No new
  world_logic value was needed. Made explicit in the sync yaml (`world_logic: region_lock`);
  it was already the default, so the sphere-1 bloat in playtest 3 was the TEST yaml's
  `open_world`, not the sync config.
- **Grace bundle data + contract.** `grace_flags.tsv` graces map cleanly to apworld regions via
  map tile (413/422; 9 edge tiles miss). Generated `worlds/eldenring/grace_data.py`
  (`REGION_LOCK_ITEM` + `REGION_GRACE_FLAGS`, 25 lock items / 210 graces over the locked hub
  regions). `fill_slot_data` now emits **`regionGraces` = {lock_item_name: [grace warp flags]}**
  when region gating is active (`world_logic < 3`). Compiles + JSON-serializable.
- **Remaining = client (next session).** On granting an item whose name is a key in
  `regionGraces`, the C++ client SETS those grace warp-unlock flags (reuse the map-reveal
  flag path). Until then `regionGraces` is inert. Sub-region (cave/catacomb) graces are NOT
  bundled -- only the 25 locked hubs; you walk to sub-graces normally.
- Regenerate `grace_data.py` if regions/graces change (script logic in TODO #13 / chat history).

### How many graces per region? (the `graces_per_region` dial)

"Importance" is NOT a field in the data. The only candidate signal, `placeNameTextId` (a grace
with a distinct named place), is UNRELIABLE: Liurnia 38/39 named but Stormveil 1/10, and
undergrounds/Ashen/Enir Ilim/Shadow Keep show 0 named (legacy/underground graces store names
differently). It's biased to the overworld -- rejected as an importance cut.

What works uniformly is **spatial spread** from the grace coordinates: pick a central hub first,
then farthest-point for coverage. Implemented as the `graces_per_region` option (default 3):
- `0` = all graces (210 total) -- most convenient, least exploration.
- `1` = hub only (29 total) -- warp into each region, ride to the rest.
- `3` = hub + coverage (75 total) -- recommended starting point.
`grace_data.py` now stores `[flag, global_x, global_z]` per grace (overworld tiles offset onto a
256m grid) so the spread runs at gen time -- no regen needed to change the count.

Full hand-curation (THE iconic entry grace per region, e.g. Gatefront for Limgrave) would need
FMG name extraction (SoulsFormats/Yabber on regulation.bin) -- possible later, but the spatial
hub already approximates it. Hand-override specific regions in grace_data.py if a pick is bad.

---
(Original design notes below; kept for the client work + the fallback chain.)

## The fusion (Alaric's key insight)

Each region has a **key item**; getting that key both (a) unlocks the region in logic and
(b) **unlocks that region's Sites of Grace** (fast travel within it). Because access and graces
are bundled into one item, you can NEVER warp somewhere you haven't earned -- which kills the
old objection that "give graces at start" would bypass region locks. And because each unlocked
region is self-contained (you can reach + fast-travel it), the **order doesn't have to be
rigidly linear** -- fill can shuffle which region opens when ("mix it up a little") and travel
stays painless. This supersedes the standalone "graces at start" idea and the strict 7-tier
cumulative chain below.

## Mechanism

- **Per-region key, region_lock-style** (reuse/extend the existing `_region_lock` machinery:
  per-region `.lock` items, injected -- __init__.py:137). Each region entrance requires its key.
  AP fill places the keys logic-respecting, so the *order is emergent / shuffled per seed* (a
  key can't sit behind its own region). This is simpler than a forced cumulative chain.
- **Grace bundle:** when the client grants a region key, it also SETS that region's grace-unlock
  event flags (warp enabled). Data: `elden_ring_artifacts/grace_flags.tsv` (422 graces: flags +
  tiles + region) -> map region key -> [grace flags]; emit in slot_data; client sets them on key
  receipt. (This is SPEC-grace-warp-rando wired to the region keys.)
- **Soft order ("mix up a little"):** mostly free order, but optionally add a few soft
  dependencies (e.g. don't let a tier-6 region open in sphere 1) so difficulty doesn't swing
  wildly. Keep it light -- the graces make a non-linear order tolerable.

### Fallback (if shuffled order proves too swingy): strict 7-tier cumulative chain
1 Limgrave → 2 Liurnia → 3 Caelid → 4 Altus → 5 Mountaintops → 6 Farum → 7 Ashen. Cumulative
keys (tier N requires keys 2..N), item-checks only (NO `_can_go_to` chaining -- that recurses,
per the deathless bug). Pick this only if the shuffled version feels bad.

Ship as a NEW `world_logic` value (e.g. `region_fusion`); don't disturb the existing
`region_lock`.

## The hard part: assigning all 116 base regions to a tier

Only TIER-BOUNDARY entrances need an explicit gate; sub-regions reached *through* a gated parent
inherit it via the connection graph. But ER has back-doors, so several non-obvious regions need
explicit tiering. Proposed assignment (SANITY-CHECK THIS, Alaric):

- **Tier 1 (free):** Limgrave, Stormhill, Stormveil (Start/Castle/Throne), Weeping Peninsula,
  Roundtable Hold, + all their caves/catacombs/tunnels (Coastal, Groveside, Murkwater,
  Stormfoot, Limgrave Tunnels, Fringefolk, Impaler's, Tombsward, Morne, Earthbore, Highroad,
  Deathtouched), Divine Tower of Limgrave, Church of Dragon Communion.
- **Tier 2 (Liurnia key):** Liurnia, Raya Lucaria (all), Caria Manor, Carian Study Hall (+Inv),
  Bellum Highway, Ruin-Strewn Precipice, Liurnia dungeons (Road's End, Black Knife, Cliffbottom,
  Stillwater, Lakeside/Academy Crystal Caves, RL Crystal Tunnel), Four Belfries (the portals).
- **Tier 3 (Caelid key):** Caelid, Dragonbarrow, Redmane/Wailing Dunes, Sellia (Crystal Tunnel,
  Hideaway), Caelid/War-Dead/Minor Erdtree Catacombs, Gaol/Abandoned/Gale/Dragonbarrow Caves,
  Great-Jar, Divine Tower of Caelid.
- **Tier 4 (Altus key):** Altus Plateau, Mt. Gelmir, Volcano Manor (all), Capital Outskirts,
  Leyndell Royal (all), Moonlight Altar, + Altus/Gelmir dungeons (Sainted/Gelmir/Wyndham/Auriza,
  Unsightly, Perfumer's, Sage's, Old Altus/Altus Tunnel, Seethewater/Volcano Cave, Sealed Tunnel),
  Subterranean Shunning-Grounds, Leyndell Catacombs, Divine Towers (East Altus), Frenzied Flame.
- **Tier 5 (Mountaintops key):** Forbidden Lands, Mountaintops of the Giants, Flame Peak,
  Consecrated Snowfield, Haligtree/Elphael, Mohgwyn Palace, + their dungeons (GCHG, Giants'
  Mountaintop Cat., Spiritcaller, Snowfield Cat., Cave of the Forlorn, Yelough Anix).
- **Tier 6 (Farum key):** Farum Azula (+ Main).
- **Tier 7 (Ashen key):** Leyndell Ashen Capital (+ Throne), Erdtree (final boss; already also
  gated by great_runes_final_boss).

### Open questions on the mapping (decide before coding)
- **Undergrounds** (Siofra, Nokron, Ainsel, Deeproot, Lake of Rot): geographically cross-tier.
  Siofra is Limgrave-early; Nokron needs Radahn (tier 3-ish); Ainsel/Deeproot/Lake of Rot are
  Liurnia/Caelid-era. Proposal: Siofra=1, Nokron/Deeproot=3 (post-Radahn), Ainsel/Lake of Rot=2.
  These are the most likely deadlock sources -- verify against the connection graph.
- **DLC** is NOT in the base chain; it keeps its existing gating (Mohg/Radahn rememb. + medal +
  Scadutree). Confirm DLC entrances don't get double-gated by a tier key.
- **Caelid-before-Liurnia:** vanilla lets you reach Caelid from Limgrave directly. The chain
  forces Liurnia first (Caelid=tier3 requires Tier2). That's the intended "pretend you can't".
- **Roundtable Hold** must stay tier 1 (hub) or NPCs/services gate weirdly.

## Work items
1. items.py: add Tier2..Tier7 key items (progression, `.lock`/inject so they enter the pool).
2. options.py: add `region_chain` to WorldLogic.
3. __init__.py: `_region_chain()` -- region->tier dict (above), gate each region on cumulative
   keys; call it from where `_region_lock()` is called when world_logic == region_chain.
4. GEN-TEST: generate several seeds; any "unreachable/unbeatable" = a mis-tiered region (fix the
   dict). Undergrounds first.
5. Pairs with `location_pool: lean` and the great-rune thresholds already in.
