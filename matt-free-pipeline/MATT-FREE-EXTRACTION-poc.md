# Can we map items -> flags directly and cut matt's keys? — PROVEN, 98.9%

Tested against the vanilla Smithbox param dump already on disk
(`elden_ring_artifacts/vanilla_er/vanilla_er/*.csv`) vs the apworld's live flag table
(`er_static_detection_table.json`, 4,493 distinct flags in use).

## The mechanism (no keys involved)

Every world pickup is an `ItemLotParam` row that carries its item(s) in `lotItemId01..08` +
`lotItemCategory01..08` **and** the flag that fires when looted in `getItemFlagId`. Shops are
`ShopLineupParam` rows carrying `equipId` + `eventFlag_forStock`. Walk those three tables and each row
hands you `(item, category, flag)` directly. Assign your own AP ids. matt's key strings never appear.

## Coverage measured

Of the 4,493 distinct event flags the apworld actually uses:

| source (vanilla param) | apworld flags matched |
|---|---|
| `ItemLotParam_map.getItemFlagId` | 3,866 |
| `ItemLotParam_enemy.getItemFlagId` (boss/enemy drops) | 169 |
| `ShopLineupParam.eventFlag_forStock` | 414 |
| **total recovered** | **4,442 / 4,493 = 98.9%** |
| unresolved | 51 (1.1%) |

So essentially the entire location->flag table regenerates from vanilla game params. This is the same
data matt's `itemslots.txt` reports in its DebugText (`lot 10010 ... flag 100180`) — he transcribed
it; it's not his. Reading it from the param dump instead removes matt from the equation entirely.

## The 1.1% tail (51 flags)

These aren't tied to a lot's `getItemFlagId` — they're event-script grants: NPC handovers, quest
rewards, a few scripted/DLC placements whose flag is set by EMEVD logic, not a lot. Recoverable from
the decompiled event scripts (`elden_ring_artifacts/event/*.emevd.dcx.js`) or just hand-mapped — it's
50-odd entries. matt's set hand-encoded these too.

## What this means for a matt-free standalone

- **Flags: solved.** 98.9% mechanical from a dump you already have; the tail is a small hand/EMEVD job.
- **The real remaining work is curation, not flags.** `ItemLotParam_map` has 5,565 rows and only 4,537
  carry a flag; you still choose which lots are meaningful randomizer locations (dedup, drop junk/unused,
  mark missable/DLC). ~90% falls out of mechanical rules (has getItemFlagId, real item, reachable map);
  the tail needs playtesting. That selection, derived from your own rules over game facts, is what makes
  it independent — don't transcribe matt's list, generate your own.
- **Client gets simpler:** it already consumes `location -> flag`; drop the `key_resolver` layer.
- **Descriptions:** auto-generate functional names for all (region from map id + item name); hand-author
  real hint text only for big-ticket, exactly your MVP instinct.

## Extractor built + run (`extract_locations.py`, output `candidate_locations.csv`)

Walks the three param CSVs, filters to lots that award a real item with a flag, dedups by flag,
assigns fresh AP ids, and attaches item names from Paramdex. Run result:

```
distinct candidate flags     : 5,318
current apworld flags        : 4,493
  covered (apworld ∩ params) : 4,440  (98.8%)
  unresolved (apworld − params): 51   <- see below
  EXTRA (params − apworld)    : 878   <- in-game lots the apworld deliberately drops
     EXTRA by source: map_lot 523, shop 349, enemy 6
```

**Two distinct piles of "hand work," both small and both YOURS to define:**

1. **The 878 EXTRA** = real game lots the current (matt-derived) set excludes. This is the curation
   layer made visible: infinite/duplicate shop rows, unused or junk lots, crafting-material spam.
   You trim these with your own rules (dedup shop restocks, drop flagless junk, exclude non-pickup
   categories). This is the actual labor of a location set — but it's mechanical filtering over game
   data, not copying matt's choices.

2. **The 51 "unresolved"** — I chased these all the way down. They are NOT event-script mysteries:
   - **49 appear NOWHERE in any param** (or EMEVD literal). Naming them via the apworld's own table
     shows what they are: shop wares that set no purchase flag (Kalé, Nomadic Merchant, Pidia, Twin
     Maiden, Enia — cookbooks/notes/goods), respawnable **enemy drops** (Ghost Glovewort, Rotten
     armor sets), a couple boss drops, and some multi-item corpses. These have **no natural game
     flag**, so *any* apworld — matt's included — must invent a synthetic tracking flag for them.
     Going matt-free just means allocating your **own** ~49 unused flags and having the client set
     them on purchase/pickup detection. That's your flag scheme, fully independent.
   - 2 sit in a secondary param field (recoverable with slightly more param logic).

## Bottom line

The location->flag backbone regenerates ~99% mechanically from params you already have; the entire
residual is **~49 self-defined synthetic flags for flagless checks + a curation pass over 878 excess
lots**. None of it requires matt's keys, descriptions, or choices. The `candidate_locations.csv` is
the first draft of that backbone.

*(Not legal advice. Facts/params aren't matt's; a copied selection list could carry thin compilation
copyright, so derive the selection from rules. Confirm matt's license if it gates release.)*
