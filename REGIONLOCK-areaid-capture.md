# Region-lock area-id capture worksheet

**Why:** the bundle "...Caves Lock" items are currently *logic-only* — they have no
`area_ids` in `worlds/eldenring/map_region_data.py`, so the client builds no
`areaLockFlags` range for them and never kicks you out (this is why Groveside let you
walk in). To make them physically enforced we need each dungeon's **play-region id**.

**Key fact (corrected):** the value the client reads is `GetPlayRegionId()` = the
FieldArea **mapNameId** (the area-name banner id), NOT the MSB file number. They are
different id spaces — e.g. Groveside's MSB is `m31_03` but its play-region id is `31000`.
So the ids cannot be derived from the MSB name; they must be read from the log.

**How to capture:** with the client running, walk into each dungeon below. On every area
change the client writes a line to its log:

```
[..] [info] RegionLock: area=NNNNN
```

Copy the `NNNNN` into the "captured id" column (just paste me the raw log lines and I'll
fill it in + wire `map_region_data.py`). Overworld sub-areas log a 7-digit id
(subregion*100); minidungeons log the 5-digit id we want.

---

## limgrave_caves  →  "Limgrave Underground Lock"

| Dungeon | MSB | Captured play-region id |
|---|---|---|
| Groveside Cave | m31_03 | **31030**  ✅ (interior boss fired here; the 31000 seen at the entrance was a different/ambiguous sub-area) |
| Murkwater Cave | m31_00 | |
| Highroad Cave | m31_17 | |
| Coastal Cave | (capture) | **31150**  ✅ (note: 31150 numerically = m31_15, but annotations call m31_15 "Fringefolk Hero's Grave" — so verify Fringefolk separately, the ids are NOT a reliable msb map) |
| Fringefolk Hero's Grave | m31_15 | |
| Church of Dragon Communion | m35_00 | |
| Stormfoot Catacombs | m30_02 | |
| Murkwater Catacombs | m30_04 | **30040**  ✅ |
| Deathtouched Catacombs | m30_11 | |
| Limgrave Tunnels | m32_01 | |

## liurnia_caves  →  "Liurnia Caves Lock"

| Dungeon | MSB | Captured play-region id |
|---|---|---|
| Stillwater Cave | m31_04 | |
| Lakeside Crystal Cave | m31_05 | |
| Academy Crystal Cave | m31_06 | |
| Road's End Catacombs | m30_03 | |
| Black Knife Catacombs | m30_05 | |
| Cliffbottom Catacombs | m30_06 | |
| Raya Lucaria Crystal Tunnel | m32_02 | |
| Ruin-Strewn Precipice | (capture) | |

## altus_caves  →  "Altus Caves Lock"

| Dungeon | MSB | Captured play-region id |
|---|---|---|
| Sainted Hero's Grave | m30_08 | |
| Unsightly Catacombs | m30_12 | |
| Perfumer's Grotto | m31_18 | |
| Sage's Cave | m31_19 | **31190**  ✅ |
| Old Altus Tunnel | m32_04 | |
| Altus Tunnel | m32_05 | |

## mountaintops_caves  →  "Mountaintops Caves Lock"

| Dungeon | MSB | Captured play-region id |
|---|---|---|
| Giant-Conquering Hero's Grave | m30_17 | |
| Giants' Mountaintop Catacombs | m30_18 | |
| Consecrated Snowfield Catacombs | m30_19 | |
| Cave of the Forlorn | m31_12 | |
| Spiritcaller Cave | m31_22 | |
| Yelough Anix Tunnel | m32_11 | |

## castle_morne  →  "Morne Lock"

| Dungeon | MSB | Captured play-region id |
|---|---|---|
| Castle Morne | (capture) | |

---

## After capture — what I'll do

For each dungeon the `map_region_data.py` entry becomes a single-point range:
`"<region>": {"area_ids": [(id, id)], ...}`, all dungeons in a bundle sharing that
bundle's **open flag** (set on receipt via `lockRevealFlags`). That open flag has to be
allocated for these bundles (they don't have one yet) — I'll assign from the same
OPEN_FLAG_BASE block the existing locks use and confirm the bundle lock item sets it.

Open question to resolve during capture: whether all caves in a map prefix share one
play-region id or each reports a distinct one. Two same-region captures (e.g. Murkwater
m31_00 vs Highroad m31_17) will tell us — if they differ, per-dungeon locking works; if
they collide, we lock at bundle granularity only.
