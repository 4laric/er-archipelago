# SPEC-ashen-capital-lock — the Erdtree burn becomes a synthetic item

**Status: PROPOSED, build-ready except for ONE in-game probe (§ The probe that gates the build).
Not an option — this is the behaviour. Supersedes the `FINALE_REQUIRES` half of
`features/finale.py` and the `elden_beast` row of `GOAL_CHOICES`.**

Written against world `main` @ `441e2cd`, client `main` @ `208df96`.

## Decisions (Alaric, 2026-08-06)

1. **The item model IS the behaviour.** No `capital_burn: vanilla|item` toggle — two shapes to
   support forever, and narrowing a Choice later is a compat break. The reconciler already made
   Royal non-losable, which was the only reason to keep the vanilla one-way burn as a fallback.
2. **The Ashen Capital does NOT become a region.** It stays out of `REGIONS` and `SPINE`, is never
   drawn by `num_regions`, is never counted in the kept set, and can never be the start anchor.
   It is ten checks and a gauntlet, not a place you play. `describe_kept` is untouched.
3. **`goal: auto` = the Elden Beast, always.** The finale is a fixed gauntlet — Gideon into
   Godfrey/Hoarah Loux into Radagon/Elden Beast — and that shape plays well as a capstone under
   rando no matter what the draw kept.

## What this changes, in one paragraph

Today flag 9116 has exactly one setter in the whole game (Maliketh), so the finale can only exist
on seeds that kept Farum Azula *and* Leyndell, and `goal: elden_beast` has to force-keep both —
which is why `num_regions: 1` produced four regions. After this spec, an **Ashen Capital Lock**
item arms the burn state, the finale exists on every base-game seed, `FINALE_REQUIRES` empties,
and Farum Azula stops being mandatory. `num_regions: 1` rolling Mountaintops means you play
Mountaintops, find the Ashen Capital Lock, and warp to the end of the game.

## Ground truth reused — do NOT re-derive

From `SPEC-capital-reconciler.md` (Alaric in-game + EMEVD, 2026-07-14) and this session's reads:

* **9116 is the map-version selector.** OFF → Leyndell, Royal Capital `m11_00` (play_region 11000,
  Morgott + ~152 checks). ON → Ashen Capital `m11_05` + Elden Throne `m19_00` (11050, 19000).
* **Sole vanilla setter of 9116:** `m13_00_00_00.emevd:409`, on Maliketh's death.
* **`common.emevd $Event(900)`** waits solely on 9116 → burn cutscene → warps the player into
  `m11_05` at region 11052010 → `BatchSetEventFlags(71100, 71110, OFF)` (wipes the Royal grace warp
  points) → latches **118** as its last step. 118 is monotonic, is $Event(900)'s own entry check,
  and m13's setter event `13002800` ends itself once 118 is on.
* **Grace sets are disjoint** (BonfireWarpParam): Royal `11001950-11001959`, warp flags
  71100-71109 → bucket 11000. Ashen `11051950-11051955`, warp flags 71120-71125 → 11050. Throne
  `19001950`, warp flag 71900 → 19000.
* **The finale's ten checks** live in `data.LOCATIONS['Ashen Capital']`. The two majors are
  `7770755` (Hoarah Loux, f510070) and `7770764` (Elden Beast, f510230), both tagged
  `Remembrance, MajorBoss, Boss, LegacyBoss`. **Gideon (`7773906`) carries NO tags**, so
  `goalLocations` stays exactly the pair — verified, not assumed.

## The mechanism: pre-latch 118, then let the reconciler own 9116

On **first receipt** of `Ashen Capital Lock` the client sets, in this order:

1. **118 ON.** This does three jobs at once: it arms the reconciler (`tick_capital` returns early
   while `!armed`); it makes `$Event(900)` end itself on its own entry check, so the burn cutscene
   never plays and **the Royal warp flags 71100-71110 are never wiped**; and it disarms m13's
   `13002800`, so a later Maliketh kill can no longer fire a real burn behind the player's back.
2. **The Ashen grace bundle** — 71120-71125 + 71900 (`regionGraces`). These are the warp targets,
   and they are in no bundle today.
3. **The region open flag** — a new synthetic. 76983 is the next free value after Leyndell 76980 /
   Raya 76981 / Sewer 76982, but **let `gen_data`'s band allocator assign it**; do not hand-pick a
   literal into the generated file.
4. **9116 — deliberately NOT set here.** The reconciler owns it: `capital_warp_intercept` writes it
   from the warp target before the load resolves, and `tick_capital` holds it by play_region
   bucket. Setting it at receipt while the player stands in Limgrave would just be written back OFF
   by the next warp anyway.

**Order is load-bearing:** 118 first, or steps 2-3 land while the reconciler is still inert.

**Wire:** this is the existing lock-grant path — `region.rs` already sets `regionGraces` + the open
flag + `lockRevealFlags` on receipt. 118 rides `lockRevealFlags` (a plain "set these flags on open"
list) rather than `regionGraces`, which the bundle-reconcile loop walks and would mis-report. No new
slot_data key is strictly needed; a dedicated `capitalArmFlags` key is one line if we want the log
line to name what it is, which is probably worth it.

## World-side changes

1. **`features/finale.py`** — the region is built unconditionally (base game in play; see §
   dlc_only). Entrance rule changes from `has_all(FINALE_REQUIRES locks)` to
   `has("Ashen Capital Lock")`, and the host moves from Leyndell to `HUB`: you reach the Ashen
   Capital by warping to its own graces, never through the capital's rune gate. The foreign-bar
   `item_rule` block stays exactly as is.
2. **`data.FINALE_REQUIRES` → `()`**, `FINALE_HOST_REGION` → `HUB`. `coverage.py`'s finale scope
   predicate and its `delegation: data.FINALE_REQUIRES` provenance follow.
3. **`region_play_ids`**: `Leyndell: [11000, 11050, 19000]` splits into `Leyndell: [11000]` and
   `Ashen Capital: [11050, 19000]`. 🛑 **The reconciler derives `capitalAshenPlayRegions` /
   `capitalRoyalPlayRegions` by partitioning *Leyndell's* bucket list, and hard-fails gen
   (ContractError) on an unclaimed bucket or an empty side.** Re-point that derivation in the same
   commit or generation dies the moment the split lands.
4. **`region_open_flags` + `region_graces`** gain an `'Ashen Capital'` entry (§ mechanism).
   `core._lockless_host` loses its only member and can go — Ashen now has a real open flag, so the
   KICK enforces it in its own right instead of borrowing Leyndell's.
5. **`core.create_items`**: mint one `Ashen Capital Lock` unconditionally, alongside the per-kept
   region locks and **before `pool_builder`**, so count-exactness holds by construction (the builder
   fills the remainder). It is progression, it is never the precollected anchor.
6. 🛑 **`core.create_items:585` — the `start_regions` clamp must count MINTED LOCKS, not kept
   regions.** It currently reads `if _n_start >= len(kept): raise OptionError(...)`.
   `start_with_region_lock` is frozen ON in `defaults.FROZEN_OPTIONS`, so a `kept == 1` seed at the
   default `start_regions: 1` raises and **Alaric's motivating case — `num_regions: 1` rolls
   Mountaintops — dies at generation.** The clamp has never been wrong because `kept == 1` is
   currently unreachable (auto force-keeps Leyndell, whose parent closure adds Altus, floor 2);
   this spec makes it reachable for the first time.
7. **`features/goal_locations`**: `GOAL_CHOICES['elden_beast'] = ('Ashen Capital', ())` — nothing
   forced. Tier 0 keys on the finale being built rather than on `finale_active(kept)`, and `auto`
   resolves to it unconditionally (decision 3).
8. **`goalRequiredItems`** picks up the Ashen lock via `kept_lock_names()`. Strictly redundant —
   you cannot kill either goal boss without it — but the two terminal conditions are supposed to
   read one list, and a lock missing from that list is exactly the drift the 2026-07-30 alignment
   fixed.

## Where the old ladder still lives: dlc_only

Under `dlc_only` the base game is sealed, so there is no Ashen Capital, no lock, and no tier 0.
The terminus-first spine walk (tiers 1/2, including the 2026-08-05 Bayle fix) is **still the goal
derivation there** and must not be deleted — it just stops being reachable on any seed with the
base game in play.

⚠️ **A vacuous guard to avoid.** `core._resolve_goal_choice` validates a named goal by checking
that `forced_regions(chosen)` are all eligible. With `elden_beast`'s forced set now empty, that
check passes **vacuously** under `dlc_only` and would pin an unbuildable region. The guard has to
become an explicit "base game must be in play" test, not a quantifier over an empty tuple.

## natural_progression

`natural_progression` mints no Lock items at all, so there is nothing to receive and nothing to arm.
Under it, **keep the vanilla burn**: don't pre-latch 118, let Maliketh's death set 9116 the way the
game does. `kept_lock_names()` already returns `[]` there, so `goalRequiredItems` stays omitted.

## Consequences accepted

* Every seed with the base game in play ends on the Elden Beast. Terminal-region variety under
  `auto` is gone by choice.
* The Ashen Capital's ten checks exist on every such seed rather than on the ~fraction that kept
  Farum Azula + Leyndell.
* A player can reach the game's real ending as soon as fill gives them the lock. Under decision 3
  that *is* the goal, so it is not a footgun — but it does mean the Ashen Capital Lock is the single
  most sphere-sensitive item in the pool, and `goalRequiredItems` (hold every kept lock) is the only
  thing stopping a one-lock seed from ending the moment it opens.

## The probe that gates the build (CE, one save, ~10 minutes)

Everything above is worthless if #1 comes back wrong. Do it first.

1. **On a save that has NEVER burned:** set 118, set 9116, warp to 11051950. Does `m11_05` load?
   Do Gideon (510060), Godfrey (510070) and Radagon/the Elden Beast (510230) spawn and progress
   normally with no burn in the save's history? ← **load-bearing**
2. **Are the Ashen graces selectable on the map while 9116 is OFF?** This was wart #3 in
   SPEC-capital-reconciler ("unknown, vanilla can never be in that state") and it was cosmetic
   there because the burn drops you in. Here, warping to an Ashen grace is the ONLY way in, so it
   is load-bearing. **If they are hidden:** fall back to a client-driven warp — `warp_to_grace`
   with the entity id bypasses the map UI entirely, and the region kick already does exactly that.
3. **With 118 pre-set and Maliketh never killed**, confirm `13002800` really is disarmed — no
   surprise burn on a later Maliketh kill.
4. **Royal survives:** warp away, warp back to a Royal grace, Morgott and the ~152 checks live,
   71100-71109 never wiped.
5. **The NPC surface** named in the reconciler spec — `common.emevd:5063, 7268, 7315, 7319, 7403` —
   now has to hold with 9116 toggling *and no burn anywhere in the save's history*. This is a
   widening of the existing unverified assumption, and it is the one item here that cannot be
   cleared in ten minutes.
