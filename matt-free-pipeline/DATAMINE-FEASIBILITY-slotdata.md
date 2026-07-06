# Datamining the item & location tables directly — feasibility

**Question:** how much of the client's two contract tables (`apIdsToItemIds`, `locationFlags`)
can be reconstructed from ER game files, instead of depending on an apworld to emit them in
slot_data? Bearing on the fswap collab: the smaller the mandatory emission, the less Bedrock has
to add and the more apworld-agnostic the client is.

All figures below are measured from the current apworld source
(`Archipelago/worlds/eldenring/`), not estimated.

---

## Item table (AP item id -> ER FullID) — ~100% datamineable

`ERItemData(name, er_code, category)` and the FullID is `er_code | category-nibble`. The `er_code`
**is the ER param row id** (e.g. Dagger = `1000000` in EquipParamWeapon; goods use EquipParamGoods,
armor EquipParamProtector, talismans EquipParamAccessory). Category = which param table it lives in.

So the entire ER item catalogue is reconstructable from `regulation.bin`
(EquipParamWeapon/Goods/Protector/Accessory) + the item name FMGs + the Paramdex defs we already
have. **Nothing about the item side is apworld-invented** except the AP-item-id *numbering* — a thin
convention. A client that reads `er_code`+`category` (from slot_data, or by name lookup against a
datamined catalogue) needs essentially nothing bespoke from the apworld here.

## Location -> flag table (AP loc id -> event flag) — flags ~99% datamineable, *binding* is not

Each `ERLocationData` carries a `key` (matt's static-randomizer location annotation). Classifying all
4,982 keyed locations:

| class | count | share | flag source |
|---|---|---|---|
| world item lot | 4,434 | 89% | `ItemLotParam.getItemFlagId` |
| shop lineup | 548 | 10% | `ShopLineupParam.eventFlag` |
| keyless (events / boss / synthetic) | ~36 | <1% | apworld logic — **not** in regulation.bin |

Both flag sources live in `regulation.bin`. So given a location's **lot/shop identity** (which is
inside the `key`), its event flag is a direct param lookup — fully datamineable. This has, in effect,
already been done once: `er_static_detection_table.json` is a baked
`location_flags` map of **4,886 locations -> 4,493 distinct flags** with a `_meta` note describing the
derivation. The datamine exists; it's just currently keyed by *AP location id*.

**What is NOT datamineable from game files:**

1. **The binding `AP-loc-id -> lot/shop identity`.** The flag value is game data; *which* location an
   AP id refers to is apworld authoring (the `key`). This is the piece that must come from the
   apworld — but it's small and stable.
2. **The synthetic flag layer** the apworld invents on top of raw pickups: 229 shared-flag groups,
   76 boss-sweep flags, region-lock open flags, num_regions constructs. These are *logic*, not
   pickups — they have no getItemFlagId to read. Whoever owns the apworld owns these.

---

## Implication for the fswap client

You do **not** need Bedrock to emit a full flag for every location. If his apworld carries the same
static-rando `key` per location (near-certain — he authored most of that key set), the minimal
mandatory contract shrinks to:

- `AP-loc-id -> key` (or just the lot/shop id), and
- `AP-item-id -> (er_code, category)`

...and the client computes every world/shop flag itself from a datamined `ItemLotParam` /
`ShopLineupParam` table. That makes the client robust to Bedrock renumbering AP ids, and cuts his
emission burden to almost nothing. His *synthetic* flags (his region_lock items) he'd still emit —
but that surface is smaller on his side (no num_regions, boss-sweep branch is stubbed).

**Caveats worth stating honestly:**

- The datamined flag table is a one-time **offline build step** (decrypt `regulation.bin` via
  WitchyBND/Smithbox/soulstruct), re-run per ER patch. `getItemFlagId` is stable across patches, so
  this is low-churn.
- The table is just integers (datamined facts), so shipping it in the client raises no
  redistribution/IP issue — unlike shipping matt's rando.
- The ~99% "datamineable" refers to *flag values*. Without the apworld's `key` binding you can read
  every flag but can't say which AP location each belongs to. So this **reduces** the slot_data
  contract, it doesn't eliminate it.

**Bottom line for the parallel spec:** keep the contract to the *binding + synthetic flags*, and let
the client derive the raw pickup/shop flags from a datamined param table. That's the leanest thing to
ask Bedrock for and the most resilient to his schema.
