# SPEC — natural-key region triggers (disjunctive)

Goal (Alaric, 2026-06-17, **direction decided 2026-06-19**): where a vanilla key/event naturally
gates a region, fire that region's apparatus (grace bundle → warp, map reveal, open flag, ticker) off
the **real vanilla trigger** instead of a synthetic "X Lock". More diegetic, fewer pool items, revives
items that are currently dead, and — the decided evolution — the trigger is a **full disjunction of the
actual vanilla access conditions** (item-sets OR boss-defeat flags OR route flags), latched once. This
is the old Phase 3 ("multi-part plumbing"), greenlit and generalized.

Supersedes the earlier "logic-only, drop the abstract lock" framing: we now WANT these regions in the
grace/reveal/open-flag systems, so each needs a trigger bundle, not just a logic rule.

## Core mechanism — the disjunctive bloom latch

Each converted region gets a synthetic apparatus key (e.g. `"Mountaintops Lock"`) carrying its
`regionGraces` / `regionOpenFlags` / `lockRevealFlags` / `lockNotifyItems` exactly like a normal lock —
**but no pool item is minted and fill logic is not re-gated on it.** The AP logical access stays on the
existing base rules. The apparatus is purely a client-side bloom bundle.

Client bloom logic (per region):
1. Evaluate a **disjunction** `TRIGGER = clauseA OR clauseB OR …`, where a clause is `has(item)` /
   `has(L) && has(R)` / `getflag(bossDefeatFlag)` / `getflag(routeFlag)`.
2. Re-evaluate on every relevant trigger edge (item received, or a watched flag flips).
3. When `TRIGGER` is true and the region's **open flag** is not yet set: run the bloom (grant the
   region's chosen graces, set open flag, reveal map, pop "Map: <area>" ticker) and **set the open
   flag as the once-latch**. On reconnect/reload the flag is already set → skip.

Reuse the hardening already learned: gate the bloom on `InventoryInstance()!=0` (no title-screen flush —
see `er-grace-flag-flush-too-early`); persist the latch (`er-startitems-grant-loop`); run the poll on
the existing settle-gate (`er-client-load-crash-poll-gate`). Where a vanilla gate/lift already walls the
region physically, **no fog Border is needed** — once warp blooms, traversal is moot anyway.

## Confirmed flags / item IDs (verified against SoulsRandomizers + apworld, 2026-06-19)

| Thing | ID | Source |
|---|---|---|
| Rold Medallion (goods) | `8107` | EquipParamGoods |
| Rold Medallion **obtained-flag** (lift gate) | `400001` | itemevents.txt — set on receipt (see `er-keyitem-obtained-flags`) |
| Morgott DefeatFlag | `11000800` | enemy.txt |
| Dectus Medallion (Left / Right) goods | `8105` / `8106` | EquipParamGoods |
| Haligtree Secret Medallion (Left / Right) goods | `8175` / `8176` | EquipParamGoods (inventory-gated, no obtained-flag needed) |
| Starscourge Radahn DefeatFlag | `1252380800` | enemy.txt |
| Magma Wyrm Makar DefeatFlag | `39200800` | enemy.txt (Ruin-Strewn Precipice → Altus) |
| Black Blade Kindred (Forbidden Lands) DefeatFlag | `1049520800` (`m60_49_52_00`) | enemy.txt — Forbidden Lands sweep target |
| Drawing-Room Key obtained-flag | `400072` | itemevents.txt — Volcano + Altus proxy clause; set on receipt by the Rold-flag patch |
| region open-flag base | `76971` | map_region_data.py (76971–76995 used; Morne=76997, Godrick=76998) |
| open-flags **the patch uses** | `76996` (Mountaintops), `76961` (Snowfield) | Snowfield takes the grace-tail gap `76961` (76998 is Godrick) |

**Resolved (no flag needed):** Rya's-hand / Volcano teleport has **no dedicated EMEVD flag** (it's talk
ESD) → use Drawing-Room Key `400072` as the proxy clause (Rya + Tanith both terminate there). Raya
Lucaria has **no alt-entry flag** — the Academy Glintstone Key is the sole entrance, so Raya is a
**single key, not a disjunct**.
**Still TODO (P3, deferred):** Radahn **Festival** trigger flag(s) — live in the Redmane talk/quest ESD,
not the EMEVD dump; needed to encode `(Altus OR ≥2 runes OR Ranni)`.

## Per-region trigger table (the disjunctions)

| Region | Bloom trigger (disjunction) | Class | Notes |
|---|---|---|---|
| **Mountaintops of the Giants** | `has(Rold) && getflag(11000800)` | strong | Forbidden Lands folds in; open-flag `76996`; FL checks sweep on BBK `1049520800`. Logic already Morgott-gated via soft-logic Leyndell Bosses. |
| **Consecrated Snowfield** | `has(Haligtree L) && has(Haligtree R) && getflag(11000800)` | strong | Secret Rold ascension = both halves + reached the lift (post-Morgott). Pure inventory, **no obtained-flag fix**. Open-flag `76961`. |
| **Altus Plateau** | `(has(Dectus L) && has(Dectus R)) OR getflag(39200800) OR getflag(400072)` | strong | Three vanilla routes: Dectus lift / Makar climb (`39200800`) / Rya→Volcano (no dedicated Rya flag — `400072` Drawing-Room Key is the proxy). Revives the dead Dectus halves as **one sufficient clause** (alive-but-optional). Reuses existing Altus open-flag `76972`. |
| **Raya Lucaria Academy** | `has(Academy Glintstone Key)` (or the `(Thops)` variant) | strong — **single key, not a disjunct** | The Academy Glintstone Key is the *sole* entrance; the only "alt" is the Abductor death-warp, which is an **exit** from Raya to Volcano, not a way in. Base rule already gates on the key (`__init__.py:1851`); just mint apparatus. Self-enforcing seal. |
| **Volcano Manor** | `getflag(400072)` (Drawing-Room Key) `OR has(Academy Glintstone Key)` (Abductor route via Raya) `OR has(Mt. Gelmir Lock)` (walk-down) | **mostly-clean disjunct** | Logic disjunction already built (`__init__.py:1899-1914`: Drawing-Room Key / Raya-Main→Dungeon abduction / Mt.Gelmir walk). Only `400072` is a true obtained-flag key; the Abductor (entities `14012`/`14029`, **no defeat/route flag**) and Gelmir clauses are reachability *proxies*. `400072` already wired (kKeyItemAcquireFlags + Altus clause). **Apparatus must be minted** — Volcano has no grace bundle in `grace_data` today. Rya's hand + Tanith both terminate in `400072`. |
| **Underground (Nokron→Siofra→Ainsel/Deeproot)** | `getflag(1252380800)` (Radahn dead) | strong | The meteor opens Nokron. Base already gates Nokron on the Radahn remembrance (`__init__.py:1859`). **Two-level:** Radahn is itself fightable only once the **Festival** is on. |
| └ Radahn Festival (upstream gate on Radahn) | `<Altus access> OR <≥2 great runes> OR <Ranni-quest flag>` | — | Model of the vanilla festival OR-conditions; exact flags TODO. This gates *fighting Radahn*, which gates the underground bloom. |
| **Castle Morne** | `has(Irina's Letter)` (`400080`) | **squint** | Morne has **no vanilla gate** (walk-in). Flavor-only: keep the existing `Morne Lock` / `castle_morne` as the real gate; Irina's Letter can *also* bloom it but must not be the sole key. |
| **Stormveil** | `has(Rusty Key)` | **squint** | Rusty Key opens an **internal shortcut door**, not the region entry (Margit/Gostoc is the real gate). Prior **false-gate** removal (`er-stormveil-rusty-key-falsegate`) — do **not** make this a hard trigger; flavor-only at most. |
| **Moonlight Altar** | `has(Dark Moon Ring)` *or* `has(Carian Inverted Statue)` | strong | Open decision retained from prior spec — pick the key. |

**Quality gradient (honest read):** the strong set — Dectus→Altus, Rold→Mountaintops, Haligtree→
Snowfield, Academy Key→Raya (a single key, not a disjunct), Radahn→Underground — are true vanilla gates
and convert cleanly. **Volcano Manor** sits just below them: a **mostly-clean disjunct** — one real
obtained-flag key (`400072`) plus two reachability proxies (Abductor via Raya, Mt. Gelmir walk). The two
squints — Irina's Letter→Morne and Rusty Key→Stormveil — are thematic only (no real vanilla region
gate), so they stay **flavor blooms layered on the existing lock**, never the sole trigger.

## Why disjunctions (truest-to-vanilla) and the alive-but-optional call

Mountaintops has one physical route; Altus has three; the underground is boss-gated with an upstream
festival disjunct. Collapsing those to a single synthetic key is what the abstract locks did, at the
cost of making the natural keys dead. The disjunctive trigger restores vanilla fidelity: a region opens
on **whichever real condition the player actually satisfied**. Consequence: a multi-route region's
natural key (Dectus halves; Volcano's Drawing-Room Key) becomes **alive but optional** — collecting it is *a* way in, not
*the* way. Making it mandatory would require suppressing the other routes, which re-creates the
over-gating the abstract lock was avoiding. **Decision: alive-but-optional** (revives the items, zero
soft-lock risk). This matches "we have those problems today" — the multi-route leak already exists; the
disjunction doesn't worsen it, and it's the faithful model.

## Implementation phases

**P1 — Mountaintops + Snowfield (proven vertical slice).** Add the two apparatus bundles + the Rold→
`400001` obtained-flag fix + the disjunctive-latch client handler. No baker change (vanilla lift is the
physical gate). Forbidden Lands graces fold into Mountaintops; wire BBK `1049520800` as the FL sweep.

**P2 — Altus + Raya Lucaria + Volcano Manor.** Altus = additive disjunct on the existing Altus Lock
apparatus (Dectus pair / Makar `39200800` / Drawing-Room Key `400072`) — done in the P1 patch's
`naturalKeyTriggers`, just needs the gen-test. Raya = **single-key** apparatus on the Academy Glintstone
Key (not a disjunct; sole entrance) — mint a Raya grace bundle + open-flag, trigger on the key. Volcano =
**mint a new apparatus** (no grace bundle today) + bloom on `400072` / Academy Key (Abductor) / Mt. Gelmir
Lock; the logic disjunction (`__init__.py:1899-1914`) already exists. Optionally drop the redundant
abstract `Altus Lock` (added ×2 — dedupe) and `Haligtree Lock`; reuse Altus open-flag `76972`.

**P3 — Underground via Radahn.** Bloom the underground regions on Radahn `1252380800`; encode the
festival disjunct (Altus OR ≥2 runes OR Ranni) once its flags are pulled. Highest complexity — do last.

**Flavor (low priority):** Morne/Irina + Stormveil/Rusty as additive blooms only.

## Caves-bundle keys as "Spelunker's" torches

The opt-in minor-dungeon **bundle** locks are a mod invention, not vanilla gates — zero fidelity
constraint — so reskin each bundle key into a distinct, *usable* **torch**. The key is the lamp:
caves are dark in ER, and the key you receive is the exact tool to light what it just unlocked.

**Naming convention: `Spelunker's <Torch>`.** Lands the cave pun, names the item by what you do with
it (signals "this is your cave key *and* your cave light"), and being a custom name it sidesteps
collision with torches that appear as normal pool loot.

Current bundle keys (`_EXTRA_LOCK_KEYS`, `__init__.py:400-403`) → torch mapping (real weapon ids from
EquipParamWeapon):

| Bundle key | Spelunker variant | Base weapon | id |
|---|---|---|---|
| Limgrave Underground Lock | Spelunker's Torch *(or Spelunker's Lantern — hands-free Lantern goods, most spelunk-coded for Siofra)* | Torch | `24000000` |
| Liurnia Caves Lock | Spelunker's Ghostflame Torch | Ghostflame Torch | `24050000` |
| Altus Caves Lock | Spelunker's Steel-Wire Torch | Steel-Wire Torch | `24020000` |
| Mountaintops Caves Lock | Spelunker's Beast-Repellent Torch | Beast-Repellent Torch | `24060000` |
| (DLC catacombs, if used) | **Spelunker's Messmerflame Torch** | Nanaya's Torch (DLC) | `24500000` |
| (spare) | — | Sentry's `24070000`, St. Trina's `24040000`, Torchpole `16080000` | |

**Two names, two effort levels:**
- **AP-side name** (apworld item rename) → shows in the client ticker, spoiler, and AP messages.
  Trivial, no baker. The pun lands in AP-land and you get a real torch in hand.
- **In-game inventory name** (FMG) → to read "Spelunker's …" in the actual ER menu needs a baker FMG
  edit. Renaming the vanilla torch's FMG hits **all** instances (incl. looted ones); a true
  non-colliding variant needs a new EquipParamWeapon row + FMG + icon (baker param work).

**Client:** on bundle-key receipt, grant the mapped torch weapon (real, equippable light source) **and**
fire the existing bundle unlock (graces + open flag + "Map: <area>" ticker). Classification stays
progression (it's the bundle key). Plays nice with `no_weapon_requirements` / `auto_upgrade`.

**MVP for overnight:** AP-side names + grant the vanilla torch weapon — pun in AP-land, real torch
equipped, no baker dependency. Full in-game FMG rename / non-colliding param variant = a follow-up
baker pass.

## Grace-list derivation (still to confirm)

Mountaintops/Forbidden Lands/Snowfield overworld graces are **not** assigned to any lock in
`grace_data.py` (only the `Mountaintops Caves Lock` dungeon bundle `73017/18/19/112/122/211`). Derive
the overworld sets from `elden_ring_artifacts/grace_flags.tsv` (cols: rowId, warpUnlockFlag, mapTile,
pos, placeNameTextId). Anchor confirmed: `placeNameTextId 650000` = Forbidden Lands (`m60_47_51`).
**Open:** confirm the exact derivation grace_data.py used (tile→region assignment) so the patch reuses
it rather than re-guessing place-name clusters. Exclude the 6 Caves-bundle graces; exclude Snowfield/
Haligtree graces from the Mountaintops set (they belong to the Snowfield bloom).

## Carried-over open decisions
- **Moonlight Altar key**: Dark Moon Ring (wired) vs Carian Inverted Statue (more natural).
- **Ruin-Strewn bypass of Altus**: Makar route (`39200800`) is now an explicit Altus clause, so the
  bypass is *modeled* not *leaked*. The Liurnia Caves Lock still closes the physical back route — the
  two reinforce. Confirm that's wanted.
- **Mt. Gelmir / Volcano / Caelid etc.**: no clean natural key — keep abstract locks.

## Related memory
`er-mountaintops-lock-design` (Option B decision), `er-keyitem-obtained-flags` (400001 + 4000xx table),
`er-natural-key-locks`, `er-region-fusion`, `er-stormveil-rusty-key-falsegate`,
`er-region-lock-physical-enforcement`, `er-boss-attribution-spec` (sweep model).
