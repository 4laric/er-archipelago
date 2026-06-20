# SPEC: DLC mini-campaign goal (Gravesite → Messmer)

Status: **PROPOSED, not started.** (Claude draft for Alaric, 2026-06-16)

One line: a **short, self-contained Shadow-of-the-Erdtree run** — keep only the front half of the
DLC (Gravesite Plain → Belurat → Castle Ensis → Scadu Altus → Shadow Keep), seal everything past
it, and **end on Messmer the Impaler**. The DLC analogue of the Capital/Morgott goal: a ~700-check
slice (≈400 with Trimmed) that plays like a focused Hollow-Knight-sized seed instead of the full
1,207-check `dlc_only` pool.

Builds directly on `SPEC-dlc-only.md` (the pool/access work) and reuses the
`region_count`/spine-sealing machinery from `SPEC-region-chain.md` + the Capital goal
(`ending_condition = capital`). This spec adds **(a)** a new goal value and **(b)** a DLC-side
region seal, nothing more — the access and pool plumbing already exist.

---

## The slice (what's kept vs sealed)

Partition is by **lock item**, reusing `grace_data.REGION_LOCK_ITEM`. Keep the five front-half
locks (Gravesite is already free in `dlc_only`); seal the rest. Sub-regions with no own lock
inherit their parent hub through the region graph, exactly as today.

**Kept locks (5):** `Gravesite Lock` (free), `Belurat Lock`, `Ensis Lock`, `Scadu Altus Lock`,
`Shadow Keep Lock`.

| Hub (kept) | Lock | Pulls in (sub-regions, via graph) |
|---|---|---|
| Gravesite Plain | Gravesite Lock (free) | Ellac River, Fog Rift Catacombs, Dragon's Pit |
| Belurat | Belurat Lock | Belurat Swamp, Belurat Gaol |
| Castle Ensis | Ensis Lock | Fog Rift Fort |
| Scadu Altus | Scadu Altus Lock | Scaduview, Scorpion River Catacombs, Bonny Gaol, Darklight Catacombs |
| Shadow Keep | Shadow Keep Lock | Church District (+ Lower), West Rampart, Storehouse (+ Back), Taylew's Forge |

**Sealed locks (removed from pool → regions become locked-vanilla):** `Enir Ilim Lock`,
`Ancient Ruins Lock`, `Rauh Base Lock`, `Recluses' Lock`, `Cerulean Lock`, `Stone Coffin Lock`,
`Abyssal Lock`, `Jagged Peak Lock`, `Charo's Lock` (+ their sub-regions: Midra's Manse, Finger
Ruins ×3, Lamenter's Gaol, Hinterland, Cathedral of Manus Metyr, etc.).

Why these five: the vanilla critical path to Messmer is Gravesite → Castle Ensis (Rellana) →
Scadu Altus → Shadow Keep (Messmer), with **Belurat (Dancing Lion) as the one worthwhile side
hub**. All three remembrance bosses of the front half — Dancing Lion, Rellana, Messmer — live
inside the kept set, so the run has real boss texture, not just a beeline. Everything sealed
(Rauh, the finger ruins, Abyssal Woods/Midra, Cerulean, Stone Coffin, Jagged Peak, Enir Ilim) is
post-Messmer or off-spine.

Because `dlc_only` uses `region_lock` (per-region keys, region-fusion graces on receipt), keeping
a lock in the pool means its region is reachable as soon as its key is found — **no physical
chaining required**, so the slice is logically coherent even though Scadu/Shadow Keep sit "deep"
in the vanilla map.

---

## Check count

Estimated **~720–760 AP checks** (incl. the 36 DLC entries at Roundtable Hold), vs 1,207 for full
`dlc_only`. Rough split from the `SPEC-dlc-only.md` per-region table:

```
Gravesite cluster  ~200   (Gravesite Plain 156 + Ellac 18 + Fog Rift Cat. 18 + Dragon's Pit 8)
Belurat cluster     ~90   (Belurat 53 + Swamp 14 + Gaol 23)
Castle Ensis        ~47   (Ensis 38 + Fog Rift Fort 9)
Scadu Altus cluster ~227  (Scadu 157 + Scaduview 10 + Scorpion Cat. 19 + Bonny Gaol 25 + Darklight 16)
Shadow Keep cluster ~160  (Shadow Keep 25 + Church Dist. 15+19 + W.Rampart 18 + Storehouse 48+14 + Taylew 11)
Roundtable DLC       36
                   -----
                   ~760
```

Sub-region membership is approximate — exact count = **sum of all regions whose lock ∈ kept set**,
plus graph-inherited children. Reproduce at gen time the same way `SPEC-dlc-only.md` did: run
`location_tables` and bucket by `REGION_LOCK_ITEM[region]`. **With `location_pool: trimmed` this
roughly halves to ≈ 380–420** — the target HK-sized band.

---

## The goal: end on Messmer

Verified location string (locations.py:3549):
```python
ERLocationData("SK/DCE: Remembrance of the Impaler - mainboss drop", "Remembrance of the Impaler",
    key="210100,0:0000510460::", boss=True, deadend=True, remembrance=True, shadowkeep_boss=True)
```
Defeat flag **0x510460** (5313632). The two gating remembrances also live in the kept set:
Dancing Lion `BTS/SF: Remembrance of the Dancing Lion - mainboss drop` (flag 0x510400,
locations.py:3494) and Rellana `CE/CLC: Remembrance of the Twin Moon Knight - mainboss drop`
(flag 0x510900, locations.py:5987) — useful if a "beat all three front-half remembrances"
variant is ever wanted.

### Wiring (mirrors the Capital/Morgott goal exactly)

`ending_condition` today (options.py:8–22): `final_boss=0, elden_beast=1, all_remembrances=2,
all_bosses=3, capital=4`. Add **`option_messmer = 5`**.

1. **options.py** — add `option_messmer = 5` to `EndingCondition` + a docstring line: *"Messmer:
   short DLC run — reach Shadow Keep and defeat Messmer the Impaler. Pairs with the DLC mini-campaign
   seal; requires `dlc_only`."*

2. **__init__.py ~1598** (completion_condition block) — add:
   ```python
   elif self.options.ending_condition == 5:  # Messmer (DLC mini-campaign)
       self.multiworld.completion_condition[self.player] = \
           lambda state: self._can_get(state, MESSMER_GOAL_LOCATION)
   ```
   where `MESSMER_GOAL_LOCATION = "SK/DCE: Remembrance of the Impaler - mainboss drop"` (define
   alongside `region_spine.MORGOTT_GOAL_LOCATION` for symmetry).

3. **__init__.py ~3400–3408** (client goal-location plumbing — the set the client reads to know what
   "win" is): extend the `ending_condition >= 2` branch with `elif == 5: goal_names = {MESSMER_GOAL_LOCATION}`.
   `ending_condition` is already serialized to slot_data (line ~3598), so the contract field is
   reused — no new slot_data key.

---

## The seal (DLC has no spine — add a fixed kept-set)

The Capital goal seals via `region_spine.compute_region_scope(region_count, …)` over a **base-game-only**
linear `SPINE`. There is **no DLC spine**, and the DLC graph is a tree, not a clean numbered chain — so
don't try to parameterize it with `region_count`. Instead, gate on the goal directly:

- Add `DLC_MINI_KEPT_LOCKS = {"Gravesite Lock", "Belurat Lock", "Ensis Lock", "Scadu Altus Lock",
  "Shadow Keep Lock"}` (a constant — likely in `region_spine.py` next to the base sets, or a small
  `dlc_spine.py`).
- When `ending_condition == 5`: kept_locks = `DLC_MINI_KEPT_LOCKS`; **sealed_locks** = all other DLC
  locks in `REGION_LOCK_ITEM` (Enir Ilim, Ancient Ruins, Rauh Base, Recluses', Cerulean, Stone
  Coffin, Abyssal, Jagged Peak, Charo's). kept_regions = every region whose lock ∈ kept set + graph
  children + `ALWAYS_OPEN_REGIONS` ({Menu, Roundtable Hold}).
- **Reuse the existing seal path verbatim** (__init__.py ~811–814): sealed-region checks become
  `place_locked_item` filler events (locked vanilla, unreachable), and sealed locks are dropped from
  the item pool. This is the same code the Capital goal already exercises — feed it the DLC sealed
  set instead of the spine's.

No new sealing mechanism, no fog-wall/baker change for the seal itself (logical only — see Open
Issues for the physical caveat).

---

## Interplay / required defaults

- **Implies `dlc_only` (and therefore `enable_dlc`).** The goal is a DLC slice; if `dlc_only` is off
  it's ill-defined (base regions would also be open with no base goal). Enforce: `ending_condition ==
  5` ⇒ require `dlc_only`, else hard error at `generate_early` (same place the existing illegal-combo
  guards live).
- **Force `messmer_kindle` OFF.** Messmer's Kindling Shards gate the **Enir Ilim** entrance
  (__init__.py ~946) — and Enir Ilim is sealed here. Leaving the shard-gate on injects progression
  items that gate nothing (dead progression → wasted fill, possible "not enough filler" churn).
  With the Messmer goal, drop the Kindling gate entirely; shards (if present) demote to filler.
- **Reuse Option A "transit base"** from `SPEC-dlc-only.md` unchanged — the player still physically
  walks base to Mohgwyn → Gravesite; base stays locked-vanilla. (Option B "DLC start" remains the
  nicer-but-later path and is orthogonal to this goal.)
- **`location_pool`:** default `trimmed` for this goal to land in the ~400 band; `all` for the
  ~760 version. Pairs cleanly — the seal runs before the pool filter, so they compose.
- **Scadutree Fragments / Revered Ash** stay normal checks and in logic (the DLC power curve); they
  fall inside the kept set, so no special handling.

---

## Open issues

1. **Physical enforcement of the new boundary (the real risk).** The seal is *logical* (item pool).
   In-game, nothing yet stops a player from walking past Scadu Altus into sealed Rauh/Cerulean/Enir
   Ilim and finding locked-vanilla junk — and worse, the DLC overworld is shared `m61` tiles, and
   `Gravesite Plain / Castle Ensis / Scadu Altus` still have **empty `area_ids` (`[]`)** in
   `map_region_data.py` (see `DLC-AREA-ID-CAPTURE.md`). So physical region-lock enforcement for these
   boundaries is currently incomplete regardless of this goal. Ship the logical seal first (it's
   correct and beatable); flag the fog-wall/baker enforcement as a follow-up that depends on the
   DLC area-id capture already on the backlog.
2. **Save-load in m61.** The existing `dlc_only` m61 save-reload crash (`ER DLC save-load crash`,
   flag 12052500 cocoon state) applies here too — this goal doesn't fix or worsen it, but a
   multi-session mini-campaign hits it. Note as a shared dependency.
3. **Is Belurat mandatory or optional?** Currently kept (for the Dancing Lion remembrance). If you'd
   rather a tighter ~620-check spine, drop `Belurat Lock` from the kept set → Belurat seals,
   Dancing Lion goes locked-vanilla. Cheap toggle; left in by default for boss texture.

---

## Work items

1. **options.py** — `option_messmer = 5` + docstring; `generate_early` guard requiring `dlc_only`.
2. **region_spine.py** (or new `dlc_spine.py`) — `DLC_MINI_KEPT_LOCKS` constant + `MESSMER_GOAL_LOCATION`.
3. **__init__.py** — (a) completion_condition branch ~1598; (b) goal-name plumbing ~3405; (c) when
   `ending_condition == 5`, compute kept/sealed DLC lock+region sets and feed the existing seal path
   (~811); (d) force `messmer_kindle` off for this goal.
4. **GEN-TEST (Windows, AP 3.11+):** generate several seeds with `dlc_only + ending_condition:
   messmer`, both `location_pool: all` and `trimmed`. Verify: (i) completion solvable
   (Messmer reachable from the 5 kept locks); (ii) no sealed lock in the item pool / spoiler;
   (iii) check count ~720–760 / ~400; (iv) no "not enough filler" failure (confirms kindling-off
   default). Reuse the `SPEC-dlc-only.md` count-repro to print the realized pool.
5. **Bake + in-game (Windows):** confirm Messmer drop fires the goal, and document the unsealed
   physical boundary (Open Issue 1) — capture place-names for Gravesite/Ensis/Scadu while testing to
   close the `area_ids` gap.

---

## Appendix — verified anchors

- `EndingCondition`: options.py:8–22 (final_boss=0 … capital=4).
- completion_condition wiring: __init__.py:1598–1622; capital uses `region_spine.MORGOTT_GOAL_LOCATION`.
- goal-name client plumbing: __init__.py:3400–3408; `ending_condition` → slot_data: ~3598.
- seal (sealed region → locked filler event): __init__.py:811–814.
- `region_count`/capital guard: __init__.py:252–256.
- DLC locks: `grace_data.REGION_LOCK_ITEM` — Gravesite/Belurat/Ensis(+Fog Rift Fort)/Scadu Altus/
  Shadow Keep kept; Enir Ilim/Ancient Ruins/Rauh Base/Recluses'/Cerulean/Stone Coffin/Abyssal/
  Jagged Peak/Charo's sealed.
- Boss remembrance drops: Messmer locations.py:3549 (flag 0x510460); Dancing Lion :3494 (0x510400);
  Rellana :5987 (0x510900).
- `dlc_only` bootstrap (only Gravesite Lock precollected): __init__.py ~296–330.
