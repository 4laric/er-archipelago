# SPEC: DLC-only mode

Status: **PROPOSED, not started.** (Claude draft for Alaric, 2026-06-13)

One line: a mode where the AP check pool is **only the Land of Shadow (DLC)**, base game
excluded — the inverse of `enable_dlc`, which *adds* DLC on top of base.

**Decisions locked (Alaric, 2026-06-13):** Access = **Option A** (transit base). Roundtable DLC
checks **included** ⇒ pool target **1,207**. Default goal = **Promised Consort Radahn (PCR)**, but
the goal is **configurable** (see "Goal" — the Messmer-gate variant is pending one clarification).
Scadutree Fragments stay as **normal checks** (not pre-placed).

No prior spec existed for this. `SPEC-scadu-in-base.md` is the opposite direction (DLC scaling
into base) and the DLC enemy-rando work (`TODO.md` #1) is orthogonal (enemies, not the check pool).

---

## Check count (the question)

Measured directly from the live `eldenring.apworld` by executing its `location_tables` against
`region_order_dlc` membership plus the per-location `dlc=True` flag (AP framework imports stubbed;
reproducible).

**1,207 DLC checks**, out of 4,943 total locations (base game = 3,736).

- **1,171** sit inside the 44 Land-of-Shadow region tables.
- **36** are DLC-gated entries that physically live at **Roundtable Hold** (Enia's remembrance
  weapons + the four DLC boss armor sets), flagged `dlc=True` in a base region.

So the count depends on one policy call: **1,171** for a "pure Land of Shadow" pool, or **1,207**
if the Roundtable DLC-remembrance/armor checks are kept in.

### Breakdown of the 1,207

| Category | Count | Notes |
|---|---:|---|
| Scadutree Fragments | 52 | 38 world + 14 enemy — the DLC **power curve** |
| Revered Spirit Ash | 26 | 17 world + 9 enemy — summon power curve |
| Missable | 155 | quest/timing-gated |
| Shops | 74 | Enia, scattered DLC merchants |
| Bosses (tagged) | 15 | region-boss tags |
| Premium | 24 | remembrance-shop / high-value |
| Remembrances | 10 | DLC remembrance drops |
| "cross" (DLC-gated logic) | 13 | |
| Maps | 5 | |
| Forge rewards / Gaol bosses / Gaol keys | 4 / 3 / 2 | |
| **Core (non-shop, non-missable, stable)** | **1,038** | the dependable backbone of the pool |

**Caveat on bake yield:** a bake won't necessarily resolve all 1,207 to in-game item slots.
`build.ps1`'s non-empty floor notes ~3,686 base / ~4,857 base+DLC resolved ⇒ ≈ **1,171 DLC slots**
typically placeable; the Roundtable-36 additionally need Enia reachable. Plan for ~1,170–1,207.

### Per-region (44 regions)

```
157 Scadu Altus            156 Gravesite Plain        69 Enir Ilim
 66 Ancient Ruins of Rauh   53 Belurat                52 Rauh Base
 51 Recluses' River         48 Shadow Keep Storehouse  46 Cerulean Coast
 38 Castle Ensis            25 Shadow Keep             25 Bonny Gaol
 23 Belurat Gaol            22 Stone Coffin Fissure    22 Abyssal Woods
 19 Shadow Keep, Church District Lower   19 Scorpion River Catacombs   19 Jagged Peak Foot
 18 Shadow Keep, West Rampart  18 Fog Rift Catacombs  18 Charo's Hidden Grave
 18 Ellac River             16 Darklight Catacombs    15 Shadow Keep, Church District
 14 Belurat Swamp           14 Shadow Keep Storehouse Back  14 Midra's Manse
 14 Jagged Peak             13 Lamenter's Gaol (Upper) 11 Taylew's Ruined Forge
 11 Hinterland              10 Ruined Forge of Starfall Past  10 Scaduview
  9 Fog Rift Fort            8 Dragon's Pit            7 Rivermouth Cave
  6 Finger Ruins of Miyr     4 Finger Ruins of Rhia    3 Lamenter's Gaol (Lower)
  3 Rauh Ruins Limited       2 Lamenter's Gaol (Entrance)  2 Scadutree Base
  2 Cathedral of Manus Metyr 1 Finger Ruins of Dheo
```
(+ the 36 at Roundtable Hold.)

---

## The access problem (the crux of the design)

The pool change is the easy half. Access is the hard half.

In the apworld graph the DLC entrance is `Mohgwyn Palace → "Go To Gravesite Plain"`, created only
when `enable_dlc` is set, and Gravesite carries an entrance rule (the "Gravesite Lock"). Reaching
Mohgwyn Palace requires base-game progression (Varré's Pureblood Knight's Medal path or the Mohgwyn
portal) plus defeating Mohg and touching Miquella's cocoon. **A literal "only DLC" run cannot begin
inside the DLC without intervention.** Two designs resolve this:

### Option A — "transit base" (logic-safe, recommended to ship first)
Keep base regions in the region graph for **traversal only**; place **no AP checks** in them (base
`location_tables` excluded from the pool). The player still physically walks base game to reach
Mohgwyn → Gravesite, but every check that matters is in the DLC. Vanilla access rules, minimal logic
risk, single-track (apworld only). Downside: it isn't a "skip base" experience — you still cross
Limgrave→…→Mohgwyn, finding base content as locked vanilla.

### Option B — "DLC start" (truest, more work, cross-track)
Start the player directly at Gravesite Plain (`Menu → Gravesite Plain`), bypassing base entirely.
The base randomizer already *has* a "DLC Start" setting, currently **bypassed under AP** (see
`REFERENCE-er-randomizer-gui-under-ap.md`, DLC tab). Requires: un-bypass DLC-start handling in the
bake, a starting kit (flask, a few runes, Roundtable access), and re-rooting the apworld logic so
`Menu` connects to Gravesite. Cleanest experience; needs both apworld logic and bake work.

**Recommendation:** ship **Option A** first (one apworld logic change, no bake DLC-start work), then
offer **Option B** as the "proper" follow-up — same interim/proper split we used for the shop
double-grant (#6).

---

## apworld changes (logic)

- **options.py:** add the mode. Cleanest is a 3-way enum `{base, base_and_dlc, dlc_only}` rather than
  a bare `dlc_only` toggle, so the illegal `dlc_only && !enable_dlc` state can't be expressed.
  `dlc_only` must imply/force `enable_dlc` internally.
- **`create_regions` (__init__.py ~205):** for dlc_only, either skip the `region_order` (base) build
  loop and root the graph at the DLC (Option B), or build both but feed only DLC `location_tables`
  into the pool (Option A). The existing location filters already gate on `data.dlc`
  (`if data.dlc and not enable_dlc: continue` ~2472; `(not data.dlc or enable_dlc)` ~2517) — invert
  the sense for dlc_only.
- **Goal (default PCR):** `ending_condition = final_boss` + `enable_dlc` already completes on
  `EI/GD: Circlet of Light` (after Promised Consort Radahn) — this is the **default**.
  All-remembrances / all-bosses should use the DLC-only `Remembrance DLC` / `Boss Reward DLC` groups
  (already defined).
- **Messmer's Kindling gate (already implemented — reuse, default ON for DLC-only):** the run to PCR
  passes through Enir Ilim, and the apworld already gates `"Enir Ilim"` entrance on Messmer's
  Kindling. The existing options make this a configurable **shard collectathon**:
  `messmer_kindle` (Toggle: split the single Kindling into shards), `messmer_kindle_max` (how many
  shards exist in the pool), `messmer_kindle_required` (how many you need). Wiring is `__init__.py`
  ~946: `_add_entrance_rule("Enir Ilim", state.has("Messmer's Kindling Shard", required))` when on,
  else the single `"Messmer's Kindling"`. For DLC-only this is the natural progression spine — burn
  the tree / reach Enir Ilim (post-Romina) only after gathering N shards. **Recommend defaulting
  `messmer_kindle` ON for dlc_only** so the long pool has a real gate; it's orthogonal to the
  dlc_only flag, so no new code — just a default.
- **Item pool:** 1,207 checks need 1,207 items. Drop base-only progression (base great runes, base
  key items) **except** whatever Option-A transit still requires (kept as locked vanilla). **Keep
  Scadutree Fragments (52) and Revered Ash (26) in pool + logic** — they are the DLC power gates;
  in a 1,207 pool that's only ~6.5% of checks, so fill/progression balancing must scale down from
  the full-seed ratios.

---

## bake / SoulsRandomizers implications

- The bake currently **strips DLC maps** in base-only mode (`ap_diag`: "game.Maps (after DLC
  strip)"). DLC-only is the opposite — it must **not** strip DLC; it may optionally strip base maps,
  but **only under Option B** (Option A still needs base maps loaded for transit).
- **Contract:** a `dlc_only` / mode field is **slot_data** → a **contract change** (new serialized
  field + version-range bump). This is NOT contract-free polish; it routes through the
  `BRIEF-contract-map-reveal`-style serialized-option handling. Flag clearly in any brief.
- Reuse the DLC-unstrip groundwork from the DLC enemy-rando track (`TODO.md` #1): DLC maps are
  already proven loadable under `enable_dlc`.

---

## Open questions for Alaric

All resolved: access = A; Roundtable included (1,207); default goal PCR; Scadu frags = normal
checks; "Messmer shards" = the existing **Messmer's Kindling** shard-gate on Enir Ilim
(`messmer_kindle*` options), default ON for dlc_only. No open questions remain — ready to turn into
a buildable brief.

---

## Pruning to ~500 checks

The pool is overwhelmingly low-value: of 1,207, only **132 are progression (56) or useful (76)** —
and those 132 already include the 52 Scadutree Fragments and 26 Revered Spirit Ashes (both classed
"useful", so they survive any filler cut). The other **1,058 are filler-tier** rewards. That's the
whole story: to reach ~500 you cut filler clutter, not anything that matters for logic or builds.

**Where the bulk is (real counts):**

| Cut candidate | Count | Why it's safe to cut |
|---|---:|---|
| Filler consumables / crafting materials (GOODS) | ~727 | grease, pots, arrows, mushrooms, crafting mats — no decision value |
| Rune drops (currency) | 71 | pure souls; zero gameplay choice |
| Armor **pieces** beyond 1-per-set | ~75 | 100 armor pieces = ~25 sets × 4; collapse 4→1 check |
| Missable (orthogonal axis) | 155 | quest/timing-gated; often excluded in async anyway |

**Recommended recipe (lands ~500), in priority order:**

1. **Keep the backbone untouched:** all 56 progression + 76 useful (= 132, incl. Scadu/Revered), and
   all **unique gear** — 104 weapons, 39 accessories/talismans, 18 ashes of war (= 161). Subtotal **293**.
2. **Collapse armor sets** 4→1: 100 pieces → ~25 checks (**−75**).
3. **Cut rune drops** (**−71**) and the **filler consumable/material GOODS** (~727). Cutting all of
   those overshoots (lands ~400), so **add back the ~80–110 worthwhile materials** you want as
   checks (Smithing/Somber stones, Ghost-Glovewort, etc.).
4. Result ≈ **293 backbone + 25 armor + ~100–180 curated materials/spells ≈ 470–520.** Dial the
   material add-back to hit your exact target.

**Implementation:** this is exactly a DLC-scoped version of the existing `location_pool: lean`
filter — gate on **item classification + category** (drop `filler` GOODS with `runes != None` or
material/consumable item codes; keep `progression`/`useful` and all gear), rather than hand-listing
locations. One filter predicate, tunable by which filler item-codes you whitelist. Optional separate
toggle to also drop `missable` (−155) for a stricter pool.

A blunt one-liner if you don't want curation: **drop all filler-GOODS + rune drops (~798) ⇒ ~409**,
then keep `missable` in and you're at a clean, no-judgement-calls pool of ~410; whitelist ~90
upgrade materials to reach 500.

---

## Appendix — reproducing the count

Executed `eldenring.apworld`'s `locations.py` with `BaseClasses`/items stubbed, counted entries whose
region ∈ `region_order_dlc` plus entries with `dlc=True`. Totals: 4,943 all / 3,736 base / 1,207 DLC
(1,171 region + 36 flag). Re-runnable against any apworld build to track drift.
