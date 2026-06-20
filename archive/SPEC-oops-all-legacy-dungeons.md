# SPEC: "Oops! All Legacy Dungeons" (legacy-dungeon-only chain)

Status: SPEC DRAFTED, not started. (Alaric, 2026-06-17, brainstorm)
Goal: a mode where the *only* content is legacy dungeons, chained by grace-warp. Delete the
open world — it's most of the physical distance between checks — and keep the dense,
hand-built dungeon interiors. The endgame of the trimmed/check-trim thesis: every check lives
inside a dungeon, so the "remoteness" heuristic goes to zero by construction instead of by
scoring.

Traversal decision (Alaric, 2026-06-17): **grace-warp only**, no stitched fog gates. Clear a
dungeon's boss → receive the next dungeon's grace bundle → fast-travel in. 90% of the feel for
10% of the bake work. Fog-stitching (splicing one dungeon's exit MSB/EMEVD into the next's
entrance) is parked as the "real version" if grace-warp ever feels too loose.

## Why this stack makes it cheap (almost all parts already exist)

- **Node graph = `region_lock`.** A legacy-dungeon chain is just `region_lock` with a
  hand-authored node set where the only locked hubs are legacy dungeons. No new `world_logic`
  internals — this is a *preset/filter over the region graph*, the same shape as the
  godrick/dlc-mini-campaign kept/sealed region presets. See [[er-region-fusion]],
  [[er-godrick-goal]], [[er-dlc-mini-campaign-spec]].
- **Inter-dungeon travel = `regionGraces`.** Already built (SPEC-region-chain): granting a
  region's lock/key item SETS that region's grace warp-unlock flags client-side. So "clear
  boss → next dungeon's grace appears in warp menu" reuses the proven flag-set path. No new
  client primitive.
- **Spine trigger = boss attribution.** `BossAttribution.cs` + `dungeon_sweep:bosses` already
  map every check → a boss DefeatFlag, and the client already polls those flags. So "this
  dungeon is cleared" is a signal we already read. See [[er-boss-attribution-impl]],
  [[er-dungen-sweep]] / SPEC-dungeon-sweep.
- **Pool cut = curation.py.** trimmed already has cut-lists + `_in_location_pool`. "Don't
  scrape the open world" is a coarser, cleaner cut than per-check remoteness scoring — keep
  only checks tagged inside a legacy-dungeon region; drop the rest of the location pool whole.
  See [[er-trimmed-curation-impl]], [[er-check-trim-spec]].

Net: this is mostly an apworld preset + a curation filter. Client and baker changes should be
near-zero if grace-warp and boss attribution are already shipping.

## The node set (the one real design decision)

**Base game (the clean 6):**
1. Stormveil Castle (Godrick)
2. Raya Lucaria Academy (Rennala)
3. Volcano Manor (Abductor / Godskin Noble → Rykard)
4. Leyndell, Royal Capital (Godfrey/Morgott)
5. Crumbling Farum Azula (Maliketh)
6. Elphael, Brace of the Haligtree (Malenia)

**Optional base "mini-legacy" extensions (dilute the concept — gate behind a sub-option):**
Sellia Town of Sorcery, Castle Sol, Castle Morne, Redmane Castle. These are dense-ish but
read as "big dungeon," not legacy. Default OFF.

**DLC nodes (already interior regions with inferred area_ids — see [[er-dlc-area-ids]]):**
Belurat Tower Settlement, Shadow Keep (+ Specimen Storehouse), Enir-Ilim. Stone Coffin /
Bonny / Scadu overworld stays cut (it's open world).

**Ashen Capital is a hazard, not a node.** It's a post-Maliketh world-state swap of Leyndell
(SPEC-grace-warp-rando flags this exact case: granting that grace early = undefined map
layer). Either skip it, or make it the *post-Farum* terminal that the game's own world-state
flip exposes — do NOT hand it a start-able grace.

### Check counts (raw, from live `location_tables`, 2026-06-17)

Counted directly from `worlds/eldenring/locations.py` (non-commented `ERLocationData`
entries, summed over each dungeon's sub-regions). These are RAW — they include shop/missable/
NPC checks; expect ~40-60% survival after the standard cuts (auto_upgrade, filler→runes,
trimmed).

| Legacy dungeon | Raw checks | Sub-regions counted |
|---|---:|---|
| Leyndell, Royal Capital | 156 | Royal + Unmissable + Throne + Divine Bridge |
| Stormveil Castle | 139 | Start (18) + Castle (117) + Throne (4) |
| Raya Lucaria Academy | 110 | Main + Academy + Library + Chest |
| Elphael / Haligtree | 107 | Haligtree (41) + Elphael (66) |
| Crumbling Farum Azula | 102 | Start (44) + Main (58) |
| Volcano Manor | 95 | Entrance + Upper + Drawing Room + Dungeon + Town |
| **Base-6 total** | **709** | |
| Shadow Keep (+Specimen Storehouse) | 139 | Keep + Church (×2) + W. Rampart + Storehouse (×2) |
| Enir-Ilim | 69 | |
| Belurat Tower Settlement | 67 | Belurat (53) + Swamp (14) |
| **Base + DLC total** | **984** | |
| *Leyndell, Ashen Capital (hazard)* | *18* | *thin world-state reskin — not a node* |

Read-outs that matter for design:
- **Distribution is pleasantly even** (95-156 base) — no weak leg in the chain; every node is
  a substantive stop, so the spine has no dead link.
- **Ashen's 18** confirms it's a reskin, not content — another reason to terminal-or-skip it.
- **Base-only ≈ 709 raw / ~350-400 trimmed** across 6 dungeons = a healthy mid-length seed
  with zero overworld riding. Base+DLC ≈ 984 raw is a full-length seed.
- Stormveil's 117-in-castle and Leyndell's 120-in-Royal are the shop/missable-heavy nodes —
  they'll shed the most under trimming, which actually *flattens* the distribution further.

## The spine (default: short linear, soft-shuffled)

Default chain mirrors the `region_chain` fallback but legacy-only:
Stormveil → Raya Lucaria → Volcano Manor → Leyndell → Farum Azula → Haligtree → (Erdtree /
chosen `ending_condition`). DLC, if enabled, splices after Leyndell or as a parallel branch
off a mid-node (Belurat → Shadow Keep → Enir-Ilim).

Like region_fusion, the order does NOT have to be rigidly linear because each unlocked node is
self-contained (warp in, fast-travel within). Fill can soft-shuffle which dungeon opens when,
with light soft-deps so a tier-6 dungeon (Haligtree/Malenia) can't open in sphere 1. Reuse the
region_fusion "mix it up a little" soft-ordering rather than a hard cumulative chain.

Spawn: player starts with dungeon-1's grace + the start kit. `quick_start`-style rune grant
([[er-quick-start-option]]) pairs naturally here since there's no open-world leveling ramp —
the player needs to arrive at each dungeon roughly on-level.

## Pool math (the thing most likely to bite)

### The location cut IS an item cut — injection is mandatory, not a balance nicety

This apworld builds the item pool **from the included locations**: `create_items`
(`__init__.py:949-982`) walks every unfilled location and adds *that location's vanilla
`default_item_name`* to the pool, then placement is shuffled. Locations and items are **two
sides of one coin** — one location in, one item in.

So cutting the overworld doesn't only delete checks; it **deletes the items that vanilla-lived
in those checks**. Any item whose only native home is the open world (overworld-chest weapons,
teardrop-scarab talismans, overworld enemy-drop ashes/sorceries) **never enters the seed** — not
by a rule, but because the slot it came from is gone. A legacy-only pool, left alone, is exactly
"whatever those six dungeons happened to contain," redistributed. That collapses gear variety
and silently drops iconic items the player would expect.

**Therefore an injection pass is required, not optional.** The pool must be (re)composed toward
a desirable target set drawn from the *whole* game, then padded to the exact location count.
This is the same shape as [[er-relevance-uplift]] / [[er-dlc-gear-curation]] (inject curated
items, fund by skipping junk, count-neutral) — but legacy-only needs it as a *first-class
builder*, not a dlc_only-scoped swap. See **SPEC-pool-builder.md** for the general primitive;
this mode is its first real consumer.

### Levers already in the box
- `auto_upgrade` (drop weapon-upgrade pickups, they're computed) — [[er-auto-upgrade-noop]]
- `filler_replacement` → runes (no open world to spend exploration on) — [[er-filler-replacement]]
- trimmed curation cut-lists — [[er-trimmed-curation-impl]]
- demand-drop small Golden Runes when short (rune-skip) — [[er-rune-skip-for-injectable-room]]
- count-neutral curated injection (`dlc_gear_curation`, `relevance_uplift`) — the mechanism
  legacy-only generalizes into a target-size builder.

**Watch the region-lock spill bug:** trimmed dlc_only already spills all region locks to start
on unlucky seeds when the location pool is too tight ([[er-trimmed-lock-spill]]). Legacy-only
is *even tighter* on nodes, so the same precollected-lock blowout is likely. Mitigation is the
same: `location_pool: all` for the lock-fill pass, light soft-deps on the spine, and a
gen-test sweep across seeds. This is the #1 thing to prove before calling it shippable.

## Work items

1. **options.py:** add the mode. Cleanest as a new `ending_condition`-adjacent *preset* (e.g.
   `region_preset: legacy_dungeons`) that selects the kept-node set, rather than a new
   `world_logic` value — it rides existing `region_lock`. Add `legacy_include_minor` (the
   Sellia/Sol/Morne/Redmane extension, default OFF) and DLC inclusion follows `enable_dlc`.
2. **curation.py / `_in_location_pool`:** keep only checks whose region tag ∈ the legacy node
   set; drop the rest of the location pool wholesale. This is the "delete open world" cut.
3. **region graph:** restrict `region_lock` node set to the legacy nodes + their lock items;
   build the soft-shuffled spine (reuse region_fusion soft-deps). Ensure boss DefeatFlags gate
   the next node's lock/grace.
4. **regionGraces emit:** confirm each legacy node's grace bundle is in the slot_data map (it
   already is for the hubs; legacy interiors store grace names oddly — verify warp flags
   resolve, per the region-chain note about underground/legacy graces). Hand-pick the entry
   grace per dungeon.
5. **Ashen Capital handling:** exclude its start-grace; decide skip vs. world-state terminal.
6. **Pool balance pass:** wire the recommended defaults (auto_upgrade on, filler→runes,
   quick_start rune grant) so arrival level tracks the spine.
7. **GEN-TEST (the verification gate):** sweep N seeds with DLC on/off and minor on/off; assert
   beatable, no unreachable node, and **no region-lock spill-to-start** (the [[er-trimmed-lock-spill]]
   failure mode). pct/threshold edge cases if boss-gating is layered.
8. **Client:** expected near-zero — grace-warp flag-set + boss-flag poll already exist. Only
   touch if a legacy interior grace needs a non-standard warp flag.

## Effort guess

Apworld-mostly: a preset + a curation filter + a spine + a gen-test sweep. The genuinely new
work is small; the *time* goes into (a) verifying every legacy-interior grace warp-unlocks
cleanly and (b) the pool-balance / lock-spill gen-test loop. No randomizer-core or client
features required if grace-warp + boss attribution land first — so this is a good thing to
build *after* those two are playtested, not before.

## Open questions

- **Where does the player level?** No open world = no soft grind. Lean on quick_start runes +
  in-dungeon drops, or accept it's a "combat-skill" mode? Decide the intended arrival curve.
- **Roundtable Hold:** keep as the always-available hub (services/NPCs) or also cut? Region-
  chain notes Roundtable must stay tier-1 or NPCs gate weirdly. Probably keep it as a non-node
  hub you can always warp to.
- **DLC Scadutree:** with the overworld cut, where do Scadu fragments come from? Either inject
  them as pool items (like [[er-scadu-in-base]]) or the DLC nodes get tuned for vanilla SL.
- **Minor-dungeon line-drawing:** if `legacy_include_minor` is on, exact list needs a pass —
  Sellia/Sol/Morne/Redmane are the defensible four; everything else is "just a dungeon."
- **Boss-gating overlay:** does this want region_lock_bosses-style "clear X% of node N to open
  N+1" ([[er-region-boss-gating]]), or is reaching+clearing the single legacy boss enough? The
  single-boss-per-node spine is simpler and probably the right default.
