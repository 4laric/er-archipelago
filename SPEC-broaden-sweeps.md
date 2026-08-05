# SPEC: broaden the sweeps (design 1)

Status: PROPOSED, 2026-08-05. Measured against `main` @ `4a3801d` + PR #378.

Design 1 of the two Alaric named: **keep paying out as you go, and widen what the existing per-boss
sweeps reach.** (Design 2 -- keep per-boss sweeps small and add a region capstone -- is
`SPEC-region-completion-release.md`. Neither is more correct; they are different shapes. This spec
costs design 1 and says how far it actually gets.)

The target is the same population both designs draw on: **940 filler checks in a named region that no
sweep currently grants** (`_filler_only`, HUB excluded).

---

## 0. Answer first

Design 1 reaches **624 of the 940**, in three INDEPENDENT pieces that can ship separately:

| | piece | worth | blocked by |
|---|---|---|---|
| **A** | m61 DLC overworld field pass | **225** ✅ SHIPPED | the tile decode + the field pass's `m60`-only regex |
| **B** | minor-dungeon map-local admission | **150** ✅ SHIPPED | the `_swept` METHOD gate, nothing else |
| **C** | legacy-interior map-local | **270** ✅ SHIPPED | the `_swept` method gate + no legacy map-local pass |

**316 stay out of reach of any boss-attached sweep** (§5). That is the honest ceiling for design 1,
and it is the number to weigh design 2 against -- not zero.

---

## 1. Piece A -- the m61 DLC overworld field pass (+217)

### 🆕 The stated blocker is GONE

`gen_data.py` L136-143 says the DLC overworld gets no convenience sweep because the m61 EMEVDs are
not decompiled: *"no m61_*.js in artifacts yet"*. **That comment is stale.** The input bundle
carries **116 m61 emevd files across 101 distinct tiles** (`gen_inputs.db`, verified 2026-08-05).

### The decode

m61 overworld ids self-encode their tile as `20XXYYLLLL`, the DLC sibling of the base game's
`10XXYYLLLL` / `12XXYYLLLL`. gen_data already anticipated this in the recovered-global scope note:
*"the DLC has its own ('11...' and '20AABB...' forms); admit those here once DLC overworld sweeps
land."*

**All 28 m61 bosses decode to a tile that has a real m61 emevd — 28 / 28.** So the same
two-derivations-must-agree guard PR #378 just landed for `12`-prefix ids works unchanged for `20`:
decode the id, and require the decoded tile to be one an emevd exists for.

### Reach

Simulating the EXISTING nearest-boss partition (Chebyshev cap 2, region-consistent, disjoint) over
the m61 grid:

```
cap 2:  claims 217 of 233   (16 unclaimed, 20 of 28 bosses used)   <- keep the cap
cap 3:  claims 225          (8 unclaimed)
cap 4:  claims 226          (7 unclaimed)
```

Keep the cap at 2. Widening it buys 8 checks and silently changes every m60 sweep too.

By region: Scadu Altus 78, Gravesite 62, Ensis 26, Rauh Base 24, Cerulean 10.

### 🛑 The risk that makes A more than a reclass

The 28 m61 bosses are classed **`legacy`** today, deliberately: `_class` must keep calling the m61
overworld legacy *"or its 28 bosses lose their sweeps entirely (measured: 240 -> 212 triggers)"*.
They are currently **divvy hosts** for their regions, and **268 members hang off them**:

```
Scadu Altus 62 · Shadow Keep 54 · Gravesite 34 · Cerulean 33 · Ancient Ruins 29
Rauh Base 28 · Jagged Peak 12 · Ensis 11 · Abyssal 5
```

A naive `legacy -> field` reclass would leave **five regions with ZERO legacy divvy hosts** --
Gravesite, Ensis, Rauh Base, Cerulean, Jagged Peak -- and the divvy pool there is region filler with
no tile, which a field pass cannot take. Those members would go dark. **Net loss, not gain.**

So A is: **give the m61 bosses a neighbourhood IN ADDITION to their divvy-host role**, not instead of
it. That is a genuine structural change -- today `_class` selects exactly one pass per boss -- and it
is the whole cost of piece A. The dedup already handles the overlap correctly (`_covered` runs the
field pass before the legacy divvy, so a check claimed by a neighbourhood leaves the divvy pool).

**Acceptance test (rule 11):** Gravesite, Ensis, Rauh Base, Cerulean and Jagged Peak each keep >= as
many total swept members as before, AND the m61 payload drops by 217. A test that only checks the
gain would pass while five regions lost their sweeps.

### ✅ SHIPPED 2026-08-05

**+225**, corpus 3476 -> 3701. Nothing lost, no trigger removed, no region flipped, and -- the thing
this piece could have got wrong -- **no region shrank**. The 28 m61 bosses hold 247 -> 476 members.
They stay `legacy` and stay divvy hosts; the neighbourhood is purely ADDITIVE, with `_covered`
keeping the two pools disjoint.

Three things had to be true, and two of them only showed up when the delta was measured:

* **The tile.** All 28 decode `20XXYYLLLL` -> a tile that HAS an m61 emevd, 28/28, guarded by the
  same second derivation as #378.
* **The grid.** `_tile_xy` held a bare `(x, y)`. m60 (44,45) and m61 (44,45) are different places on
  different continents and the distance between them is small and meaningless -- a DLC boss quietly
  claiming base-game checks. Now grid-labelled and guarded by `_near`.
* **The admission.** `_mem_tile` is fed from rows that passed `_swept`, and a `global_filler` on
  m61_46_46 passed none of its branches -- so the first cut of the pass ran over an EMPTY grid and
  claimed **exactly 0 checks while looking perfectly healthy**. Only the delta showed it.

🛑 One test I wrote had to be walked back: asserting the Chebyshev cap for m61 bosses produces FALSE
failures, because a DLC overworld boss holds a neighbourhood slice AND a region-divvy slice and
nothing in the output distinguishes them -- Romina (m61_44_45) legitimately holds Ancient Ruins
checks at distance 3. The grid invariant IS separable and is what the test asserts.

---

## 2. Piece B -- minor-dungeon map-local admission (+127)

The cheapest of the three and fully self-contained.

`_swept` (gen_data L6965) admits a row only if:

```python
method in ("treasure", "emevd") or (method == "flag_prefix" and _is_dungeon(map)) or bool(_rec_tile)
```

127 payload checks sit on a **minor-dungeon map that already hosts a boss with a working map-local
sweep** (`_is_dungeon` = m30/31/32/34/39/40/41/42/43). They are excluded purely because their method
is `global` / `global_filler`, never for a geometry or ownership reason. Their map is known and the
sweep that should hold them already exists.

Split: 46 `global_filler` + 40 `global` on dungeon-class boss maps, 24 on catacomb maps, 9 on cave,
plus tail.

**Change:** admit `global`/`global_filler` into `_mem_map` when the row has a real dungeon map.
**Acceptance test:** `test_dungeon_sweeps_are_map_local` must stay green -- every admitted member's
map must equal the boss's map. That invariant is exactly the one that makes this safe.

### ✅ SHIPPED 2026-08-05 -- what it actually delivered

**+150**, corpus 3056 -> 3206, triggers unchanged at 226, nothing left. 126 map-local (dungeon 87,
catacomb 30, cave 9) plus **24 that fell through to the region divvy** -- rows on a minor-dungeon map
with no boss on it. That second bucket was a predicted side effect of `_mem_region` admission;
measured, kept, and written into the ledger rather than discovered later.

Motivating case: **Ruin-Strewn Precipice** (m39_20) -- Magma Wyrm Makar granted NONE of the 21
pickups you fight past on the way down.

**Two rows were REFUSED**, and the branch carries a filler cut the older ones do not because of them:
a Sacred Tear (ap 7774260, `Church`) and [Incantation] Knight's Lightning Spear (7774285,
`Legendary`). The map path has never applied `_filler_only`; `test_gf_dungeon_sweep_rungs` ratchets
six pre-existing important members and says fixing that wholesale needs its own balance argument.
This change does not touch those six -- it just refuses to grow them. **The ratchet caught it, not
me**: the first cut of this change let both in and the suite went red.

🛑 Also found: `_eff_map`'s dungeon-prefix list in `test_gf_boss_sweeps` had drifted from
`gen_data._is_dungeon` -- missing `34` and `39` -- so the oracle decoded Makar's 21 members as
PENDING and called all 21 non-local. Confirmed against a THIRD table (`check_maps.tsv`: 39207010 ->
m39_20, "decoded from the flag id") before touching the list, because widening a test's vocabulary to
make a failure go away is how a carve-out gets written. Now a single `DUNGEON_LOT_PREFIXES` constant.

---

## 3. Piece C -- legacy-interior admission (+280)

280 payload checks sit on an interior map that **hosts a legacy boss**: Shadow Keep 129,
Leyndell 77, Mohgwyn 25, Deeproot Depths 8, Limgrave 6, tail.

They are excluded because `_is_dungeon` covers minor dungeons only, so a `flag_prefix` row inside
Leyndell or the Shadow Keep never qualifies, and `global_filler` never qualifies anywhere.

Two possible shapes, and this is a real design choice, not a detail:

* **Region divvy** (cheap): admit them to `_mem_region` so the region's legacy bosses divvy them
  round-robin. gen_data currently keeps recovered rows OUT of `_mem_region` -- but read the comment:
  that was scope discipline for the recovered-TILE work ("legacy divvy unchanged"), not a claim that
  the region is untrustworthy.
* **Legacy map-local** (better, more work): members = filler on the legacy boss's OWN map. Kill the
  Shadow Keep's boss, get the Shadow Keep's filler. Far more legible than a round-robin slice of the
  region, and it is the same shape as the dungeon pass.

Recommend map-local, because 129 of the 280 are Shadow Keep and 77 are Leyndell -- both are single
coherent areas where "this boss's building" is a meaningful answer and "1/9th of the region" is not.

### ✅ SHIPPED 2026-08-05 -- map-local, per Alaric's call

**+270**, corpus 3206 -> 3476. Nothing left, nothing granted twice, no sweep region flipped.

Three things the pass had to get right, each caught by measuring the delta rather than by a test:

* **INTERIORS ONLY.** `_class` calls the m61 DLC overworld "legacy", so an unfiltered legacy-map set
  pulls in `m61_XX` BANDS -- and a band spans several fine-regions, which is exactly why those bosses
  needed tile recovery for the divvy. **209 DLC checks walked in** before this was scoped out.
* **GROUPED BY THE BOSS'S REGION**, not the map's majority: a trigger carries one `SWEEP_REGION` and
  a legacy boss also holds a region slice, so map-majority filtering could mis-region the trigger.
  m10_00 is Stormveil 3 / Weeping 2; m12_05 is Mohgwyn 25 / Liurnia 1.
* **`_filler_only`**, which the dungeon map path has never applied. Without it the pass swept **282
  important-tagged checks** the region divvy had always filtered out.

**THE CLAWBACK.** Map-local runs first (a specific boss beats the region major -- the rule the
field/dungeon dedup has always followed), so a region's leftover pool can empty. **Astel** is the
case that forced it: its arena m12_04 is a bare boss room, every "Eternal Cities" check physically
lives in m12_01 and m12_02, and Astel went **33 -> 0**. It did not lose a claim to anything of its
own; it lost a consolation slice of a pool that no longer exists. Dealing the remainder to the
emptiest bosses first (also added) rescued two Shadow Keep bosses 9 -> 1, but Ainsel River's
remainder is genuinely EMPTY. So a starved region major claws back a share from the largest holder in
its own region, re-dealt round-robin: **Astel 26, its donor 27**.

`m19_00` is exempt **by MAP**: Radagon and the Elden Beast are one fight on a map with no filler, and
a convenience grant at the end of the run is not a convenience. Keyed on the map because the first
cut exempted only `19000800` and `19000810` promptly clawed back instead -- an entity-keyed exemption
on a two-head arena protects exactly half of it. Elden Beast 1 -> 0 is the one trigger this removes,
deliberately.

---

## 4. Is the region attribution good enough to grant on?

Yes -- checked by tracing which branch of `region_of` decides each of the 940:

```
465 curated dungeon override   171 m61 tile table    124 MSB ground truth
 38 per-flag override           36 curated global list  33 raw CSV region
 25 cookbook lot map            22 auto-recovered tile  18 gesture   4 finale   2 interior   1 merchant
```

Table-backed, not guesswork, and anything genuinely unknown is already quarantined to HUB -- which
the payload excludes by construction. This holds for design 2 as well.

---

## 5. What stays out of reach (316)

| count | why | reachable by? |
|---|---|---|
| 211 | **no map at all** (PENDING) -- position never recovered | no boss-attached sweep, ever |
| 76 | interior map with **no boss on it** | nothing to attach to |
| 16 | m61 tile with no boss within Chebyshev 2 | only by raising the cap |
| 13 | m60 tile the existing pass already declined | region mismatch or distance |

The 211 are the interesting ones: their REGION is known and trustworthy (§4) but their POSITION is
not, so no spatial or map-local rule can ever claim them. **A region-scoped payout is the only shape
that can** -- which is the honest argument for design 2 surviving alongside design 1, at ~316 checks
rather than the 940 the region spec currently claims.

---

## 6. Invariants that must survive all three pieces

1. **FILLER-ONLY** -- `_filler_only` / `_FIELD_EXCLUDE_TAGS` unchanged. No piece may widen the tag cut.
2. **DISJOINT** -- no check granted by two sweeps (`_covered` dedup; `test_field_sweeps_are_disjoint`).
3. **REGION-CONSISTENT** -- a sweep grants only checks in its own region (`test_all_members_in_sweep_region`).
4. **LOCAL** -- Chebyshev <= 2 for field (`test_field_sweeps_are_local`), same-map for dungeon
   (`test_dungeon_sweeps_are_map_local`).
5. **THE CORPUS LEDGER** -- `test_the_sweep_corpus_did_not_shrink` pins the total and demands the WHY
   in its docstring. Each piece answers it separately; never re-baseline.

## 7. Sequencing

**B, then C, then A.** B is a one-condition change with an existing test that proves it safe. C is
the biggest single win (280) and needs a new pass but no reclass. A is last because it is the only
one that can LOSE coverage if it is got wrong, and its 268-member exposure wants the other two
landed and stable first.

One PR each -- generated conflicts regenerate, never merge, so only one is in flight at a time.

## 8. Open questions

1. **C's shape** -- map-local or region divvy? Map-local is recommended above; it is more work and it
   changes what a legacy boss grants, which is player-visible.
2. **A's structure** -- letting one boss host two passes is new. Worth checking whether it is cleaner
   to split the m61 overworld bosses into a distinct class that the field pass and the divvy BOTH
   consult, rather than special-casing.
3. **Do the 76 boss-less interior maps deserve a look?** Some may be maps whose boss exists but is
   missing from `BOSS_HEALTHBARS` -- the same shape as the m34_15 and 1248550800 findings.
