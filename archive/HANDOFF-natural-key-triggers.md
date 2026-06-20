# HANDOFF — natural-key triggers + Spelunker's torches (overnight build, 2026-06-19)

Spec is the design; this is the apply/verify runbook. **P1 status: applied + gen-test PASSED (2026-06-19).**
Scope landed P1 = Mountaintops + Snowfield + Altus disjunct (additive) + Spelunker's torches + Rold lift fix.
**P2 (this addendum): Raya Lucaria + Volcano Manor apparatus — apworld-only, NO client rebuild.** See the
"## P2 — Raya + Volcano" section below. Deferred: P3 Radahn/underground + festival, in-game FMG torch
names, BBK sweep.

## P2 — Raya + Volcano (apworld-only, applies on top of P1)

One new patch: `patch_apworld_natural_triggers_p2.py` (backup `.bak_naturaltriggersp2`, touches only
__init__.py). It **requires P1 applied first** (asserts the P1 marker; errors out otherwise) and anchors on
P1's end-marker, extending the same `naturalKeyTriggers` + apparatus dicts.

- **No client rebuild** — `EvaluateNaturalKeyTriggers` iterates every entry generically, so new entries +
  apparatus are pure apworld. Apply → **regen + rebake, no `-Client`**.
- **Raya Lucaria Lock** (fresh mint; Raya had no lock): single key — blooms on `Academy Glintstone Key` OR
  the `(Thops)` variant. Open-flag `76962`; graces `71400-71403` (m14 interior); no map reveal (interior).
- **Volcano Lock** (mint the *missing* apparatus): `Volcano Lock` already exists as an active **logic**
  item gating Volcano Manor, but had no grace/open apparatus. P2 adds graces `71601-71607` + open-flag
  `76963`, and a disjunct trigger: `400072` (Drawing-Room Key) OR `Academy Glintstone Key` (Abductor route)
  OR `Mt. Gelmir Lock` (walk). **Additive**, exactly like Altus — the Volcano Lock item still gates fill
  logic; the natural triggers just bloom the warp. (Ripping out the abstract Volcano Lock = same optional
  follow-up as Altus.)

Apply order: `python patch_apworld_natural_triggers_p2.py` after the P1 stack, before regen.

Gen-test: slot_data shows `naturalKeyTriggers` now has `Raya Lucaria Lock` + `Volcano Lock`, and
`regionGraces`/`regionOpenFlags` carry `76962`/`76963`. In-game: `/getflag 76962` after the Academy Key;
`/getflag 76963` after any of Drawing-Room Key / Academy Key / Mt. Gelmir Lock.

**One playtest check (the `71600` call):** Volcano's entrance grace `71600` was **excluded** — it's already
committed to `Spelunker's Torch` (Murkwater Cave shares the m16 container id). If Volcano Manor's first
grace doesn't light on bloom, add `71600` back to the Volcano list in the patch (the overlap is harmless —
both just set the same warp flag).

## P1 files

## Files

| Patch | Side | Touches | Backups |
|---|---|---|---|
| `patch_client_rold_obtainedflag.py` | client (C++) | ArchipelagoInterface.cpp | `.bak_roldflag` |
| `patch_apworld_spelunker_torches.py` | apworld (py) | items.py, grace_data.py, map_region_data.py, __init__.py | `.bak_spelunker` |
| `patch_apworld_natural_triggers.py` | apworld (py) | __init__.py | `.bak_naturaltriggers` |
| `patch_client_natural_triggers.py` | client (C++) | Core.h, Core.cpp, ArchipelagoInterface.cpp | `.bak_naturaltriggers` |

All four: read live source, back up first, string-replace against grep-verified anchors, idempotent
(re-run prints "already applied"). They only edit source — they don't build.

## Apply order

Slot these into your usual stack **after** the existing required patches (pool_builder, progressive_*,
bundle locks, etc. from the run yaml), in this order:

1. `python patch_client_rold_obtainedflag.py`   ← the standalone bugfix; safe to ship alone
2. `python patch_apworld_spelunker_torches.py`
3. `python patch_apworld_natural_triggers.py`
4. `python patch_client_natural_triggers.py`

2 and 3 both edit `__init__.py` but target different names/anchors (caves-bundle names vs the overworld
"Mountaintops/Snowfield Lock"), so order between them is safe; the listed order is cleanest. The two
client patches edit overlapping files but distinct anchors.

## What each does

**rold_obtainedflag** — adds `kKeyItemAcquireFlags { "Rold Medallion":{400001}, "Drawing-Room Key":{400072} }`
firing like the companion-flag handler. Fixes the Grand Lift of Rold staying sealed (lift gates on event
flag `400001`; client granted goods `8107` but never set the flag). Also sets `400072` so the Volcano
Manor / Drawing-Room gate behaves. Independent of everything else.

**spelunker_torches** — reskins each opt-in caves/underground bundle key into a usable torch: renames the
AP item everywhere the name literal appears (items.py / grace_data.py / map_region_data.py / __init__.py),
and flips its `ERItemData` from `GOODS,99999` to `WEAPON,<torch id>`. WEAPON category packs to FullID =
raw weapon id (nibble 0x0), so the existing grant path hands you the real torch while the renamed name
still keys the bundle unlock. Mapping (all five bundles confirmed present):

- Limgrave Underground Lock → **Spelunker's Torch** (`24000000`)
- Liurnia Caves Lock → **Spelunker's Ghostflame Torch** (`24050000`)
- Altus Caves Lock → **Spelunker's Steel-Wire Torch** (`24020000`)
- Mountaintops Caves Lock → **Spelunker's Beast-Repellent Torch** (`24060000`)
- Shadow Catacombs Lock (`dlc_catacombs`) → **Spelunker's Messmerflame Torch** (`24500000`)

MVP = AP-side names only (show in client ticker / spoiler / messages); in-game inventory still shows the
vanilla torch name until the follow-up baker FMG pass.

**natural_triggers (apworld)** — mints apparatus for two no-pool-item regions and emits the
`naturalKeyTriggers` slot_data table:
- `Mountaintops Lock`: open-flag `76996`; graces = Forbidden Lands `76500-76502` + Mountaintops overworld
  `76503-76510,76520-76524`; reveal `62050,62051`; notify `8611`.
- `Snowfield Lock`: open-flag `76961`; graces `76550,76551,76652,76653`; reveal `62052`; notify `8618`.
- `naturalKeyTriggers`: Mountaintops = `Rold && Morgott(11000800)`; Snowfield = `Haligtree L && Haligtree
  R && 11000800`; Altus = `(Dectus L && Dectus R) OR Makar(39200800) OR DrawingRoomKey(400072)`, **additive**
  to Altus Lock's existing item bloom. AP fill logic unchanged.

**natural_triggers (client)** — parses `naturalKeyTriggers` (tolerant; old seeds skip), tracks received
item names, and in the settled `InventoryInstance()!=0` poll runs `EvaluateNaturalKeyTriggers()`: for each
lock, if its open flag isn't set and ANY clause holds (all items received AND all flags set), blooms
`regionGraces+openFlag+lockRevealFlags` and the notify token. The save-persisted open flag is the latch.

## Gen-test (Windows, gen-only first)

`.\build.ps1 -Randomizer -Generate`, then check the spoiler / slot_data:
- Spoiler item names show **"Spelunker's …"** on the caves-bundle keys (not "X Caves Lock").
- slot_data has `regionGraces["Mountaintops Lock"]` / `["Snowfield Lock"]`, `regionOpenFlags` 76996/76961,
  `lockRevealFlags` 62050/62051 & 62052, and a `naturalKeyTriggers` block matching the schema above.
- Gen does NOT place a "Mountaintops Lock"/"Snowfield Lock" item (apparatus-only, no inject).
- If gen fails, peel back `patch_apworld_natural_triggers.py` first, then the torch patch.

Then full enemy-OFF bake **with -Client** (the client patches need a rebuild):
`.\build.ps1 -Randomizer -Generate -Serve -Bake -Deploy -Client -Preflight`

## In-game verification checklist

1. **Rold lift** opens with Rold received + Morgott dead (was the original bug). `/getflag 400001` = 1
   after receipt.
2. **Mountaintops warp bloom**: after Rold + Morgott, Mountaintops graces light for warp and "Map:
   Mountaintops" tickers; `/getflag 76996` = 1.
3. **Snowfield warp bloom**: after both Haligtree halves + Morgott; `/getflag 76961` = 1.
4. **Altus bloom** fires on any of: both Dectus halves / kill Makar (`39200800`) / Drawing-Room Key
   (`400072`) — additive, so the old Altus Lock item still works too.
5. **Torches**: receiving a caves-bundle key grants an equippable torch that lights caves; bundle graces
   still bloom on receipt.

## Known soft spots / risks (eyeball these)

- **Torch rename breadth** — the name is the cross-file key; the patch reports occurrence counts per file.
  If any literal lives outside the four apworld files (a sibling unapplied patch, the baker), that copy
  desyncs. Skim the patch's count output.
- **Weapon-category grant of a former-GOODS lock** — verified FullID form is correct, but confirm the
  torch actually lands in inventory in-game (first torch receipt).
- **auto_upgrade on torches** — torches aren't reinforceable; confirm auto_upgrade doesn't choke on a
  WEAPON it can't upgrade (low risk, but it's a new item class through that path).
- **Forbidden/Mountaintops grace boundary** — `76501/76502` (near the Rold lift, m60_49_53) are assigned
  to Mountaintops; if a place-name capture shows them as Forbidden Lands proper it's cosmetic only.
- **One-tick latch** — bloom flags queue and flush next tick; the open-flag latch flips on the following
  tick. Idempotent SetEventFlag + `graceFlagsSetThisSession` absorb the repeat. No double-bloom expected.
- **receivedItemNames not separately persisted** — rebuilt from the replayed item stream on reconnect
  (items_handling 0b111); the open flag is the durable latch. Fine, but it's why the latch lives on the flag.

## Deferred (next sessions)

- **Raya Lucaria apparatus** — only alt-entry is the death-warp abduction (no flag), so Raya stays
  key-gated; building its grace bundle needs a Raya grace list (not yet derived).
- **P3 Radahn → underground** — bloom underground on Radahn `1252380800`; festival gate `(Altus OR ≥2
  runes OR Ranni)` needs the festival flags pulled from the Redmane talk ESD (not in the EMEVD dump).
- **BBK Forbidden Lands sweep** — `dungeonSweeps` is keyed trigger-addr→location-addr[], not region→
  DefeatFlag, so attributing Forbidden Lands checks to BBK `1049520800` needs the boss-attribution model,
  not this table. Follow-up.
- **In-game FMG torch names** — to read "Spelunker's …" in the ER menu, baker FMG edit or non-colliding
  param variants (renaming vanilla FMG hits looted torches too).
- **Rip out abstract Altus Lock** — currently additive (Dectus alive-but-optional). Making Dectus
  mandatory means removing the Altus Lock item + the `×2` rule and gating logic on the disjunction.
