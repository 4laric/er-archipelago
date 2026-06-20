# REFERENCE: unclaimed scrape keys (scraped in-game scopes with no apworld slot)

Source: `SoulsRandomizers/ap_bind_diag_20260613-234625.txt` (DLC-enabled bake, 2026-06-13).
Snapshot: **130** scrape keys with no config slot. Stable across the day's bakes.

## What these are

At bake time the randomizer **scrapes** the game's item lots / shops / event pickups (4,479 non-MODEL
scopes), then binds each to a slot in the apworld's `itemslots.txt` config (4,367 slots; 4,349 bound).
The leftovers split two ways:

- **18 config keys left unbound** — the apworld *defines* a check the scraper never reaches (the
  NPC-gift / Dragon-Communion / `nocrawl` locations covered in the bake-completeness notes).
- **130 scrape keys with no config slot** ← *this file* — in-game scopes the scraper *found* but the
  apworld has **no slot for**. The randomizer leaves each with its **vanilla item**, so they are
  **not AP checks**. Nothing is broken; these are simply **unclaimed candidate locations**. If the
  DLC/base pool ever feels thin, these are the spots you could wire up (by adding `itemslots.txt`
  entries in the apworld) to turn into real checks.

Note: this is **not** DLC-specific — it's the whole bake's leftovers (base + DLC). A DLC-only mode
wouldn't change this list.

## Key format

`category : lotId : shop : flag` (zero-stripped; `-1` = absent). Two shapes appear:

- `0:<lotId>::` — an **item lot** (enemy drop or overworld/map pickup) with a real lot id.
- `7:-1::<flag>` — a **flag-gated scope with no item lot** (item id `-1`): shop lineups / event
  pickups identified purely by event flag.

## The 130 keys

### A. Item lots — 10  (`0:<lotId>::`)
Real droppable/world items left vanilla. Short ids (4006xx/4007xx/5207xx/5308xx) are **enemy-drop**
lots; 10-digit ids are **overworld map** lots.

```
0:400622::      0:400623::      0:400625::      0:400711::      0:400714::
0:520711::      0:530861::
0:1034497010::  0:1037507000::  0:1048387030::
```

### B. Flag-gated scopes — 120  (`7:-1::<flag>`)
No item lot; keyed by event flag. They fall into two tight, systematic flag blocks plus one
outlier — the contiguity strongly suggests each block is a single shop's lineup or one event series
(e.g. a bell-bearing-unlocked merchant's full stock), but the exact identity needs the named dump
(see below).

**B1 — flag block 4,636,500–4,639,500 (33):**
```
4636500 4636600 4636610 4636700 4636800 4636900 4637000 4637100 4637200 4637300
4637400 4637500 4637600 4637700 4637710 4637800 4637900 4638000 4638100 4638200
4638300 4638400 4638500 4638600 4638700 4638800 4638900 4639000 4639100 4639200
4639300 4639400 4639500
```

**B2 — flag block 996,500–999,390 (86):**
```
996500 996510 996530 996540 996560 996570 996600 996800 996810 996820 996830
996840 996850 996870 996900 996910 996960 997100 997200 997210 997220 997230
997300 997400 997500 997510 997530 997600 997610 997700 997750 997800 997950
997960 998000 998010 998020 998100 998110 998120 998200 998250 998300 998310
998400 998410 998420 998450 998500 998520 998550 998600 998610 998620 998630
998640 998650 998670 998700 998710 998720 998730 998740 998750 998770 998790
999200 999210 999220 999230 999240 999250 999260 999270 999280 999290 999300
999310 999320 999330 999340 999350 999360 999370 999380 999390
```

**B3 — outlier (1):** `900002080`

## Making this list self-documenting

The raw keys don't say *what* item/where, because the bind-diag generator
(`RandomizerCommon/AnnotationData.cs`, the `unmatchedScrapeKeys` loop ~L584) only printed the key
string — even though the scrape (`entry.Value`) holds the vanilla item(s) at that scope.

I patched that loop so each unclaimed key is now emitted with its **vanilla item name(s) and
in-game location** appended (`<key> | <DisplayName> [<location keys>]`), the same way the
unbound-config side already resolves names. The change is **diag-only / contract-free** (no slot_data,
no param output). Re-bake and the `== scrape keys with no config slot ==` section of the next
`ap_bind_diag_<ts>.txt` will read e.g. `0:400622:: | Somber Smithing Stone [n] [lot 400622 enemy ...]`
— at which point this file can be regenerated with real names and you can decide which to claim.

## To claim any of these as AP checks
Add matching `itemslots.txt` slot entries in the apworld config (keyed to these scope ids) and a
location in `locations.py`; they then bind on the next bake. That's a **contract change** (new
serialized locations), so it goes through the versioned/contract path, not the bake-polish lane.
