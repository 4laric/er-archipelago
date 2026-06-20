# SPEC: Target-size pool builder (compose a playable pool from a priority ladder)

Status: SPEC DRAFTED, not started. (Alaric, 2026-06-17)
Goal: a reusable primitive that **composes the item pool to a target size from a ranked ladder
of full-game items + upgrade access + money**, instead of inheriting whatever happened to live
in the included locations. So that as we cut scope or tweak the pool (legacy-dungeons-only,
godrick goal, dlc-mini-campaign, trimmed, dlc_only), we can always reach a *playable* pool —
even when the native contents of the included locations don't add up to a good set, or don't
add up at all.

Motivating problem (Alaric, 2026-06-17): every reduced-scope mode hits the same wall. The pool
is built *from the included locations* (`create_items`, `__init__.py:949-982` — one location's
vanilla `default_item_name` per pool slot). Cut locations → cut items. Overworld-only gear
vanishes; what remains is "whatever those regions held," which can be junk-heavy, gap-ridden, or
simply too few good items to be fun. We keep solving this per-mode (relevance_uplift for
dlc_only, dlc_gear_curation, spell-trim keep, rune-skip). This spec factors out the shared core.

## The reframe: build TO a target, don't inherit FROM locations

Today the pipeline is **inherit-then-tweak**: take native contents → apply count-neutral swaps →
backfill leftover slots with generic filler (`get_filler_item_name()`, `__init__.py:1069`).

The builder inverts it into **compose-to-target**:

1. **Target size N** = number of included (unfilled) locations. Fixed by the location cut. Not
   negotiable — fill requires exactly one item per location.
2. **Mandatory core** (always in, regardless of native contents): progression/key items the
   logic requires — region locks, great runes, medallions, goal items, map tokens. These are
   already injected via `_create_injectable_items`; the builder just guarantees they're seated.
3. **Priority ladder** (fill the rest, best-first, until N is reached): a ranked list of
   *whole-game* items — not limited to what the included locations held. Walk top-down, place
   each per its supply rule, stop when the pool hits N. The ladder is the single tunable that
   every mode shares; modes differ only in which rungs they enable and their weights.
4. **Elastic backfill** (the part that makes N *always* reachable): money (runes), upgrade
   materials, and consumables are infinitely/elastically suppliable, so they absorb whatever
   slack is left between the curated rungs and N. This is why "the native items don't add up to
   one" stops being a failure mode — runes/upgrades/money stretch to fit exactly.

Net: native location contents become *advisory* (a default the builder may keep), not the
source of truth. A mode can keep 100% native (current behavior), inject-and-fund count-neutrally
(relevance_uplift), or fully recompose to a target ladder (legacy-dungeons-only) — all the same
code path with different ladder configs.

## The priority ladder (the shared, tunable core)

Ranked rungs, highest-value first. Each rung has a **supply rule** (once / capped / weighted-
stackable) so we don't flood the pool with one thing. This generalizes the uniques-then-
weighted-stackables structure already drafted in [[er-relevance-uplift]] — promote it from a
dlc_only helper to the builder's backbone.

| Rung | Source | Supply rule |
|---|---|---|
| 1. Mandatory progression | region locks, great runes, medallions, goal/map tokens | exactly as logic requires |
| 2. Iconic uniques | S/A-tier weapons, armor, spells, **Ashes of War**, talismans, top spirit ashes (whole game) | once each (useful) |
| 3. Permanent upgrades | Memory Stones, Talisman Pouches, Crystal/Physick tears | capped at vanilla qty |
| 4. Upgrade ACCESS | Miner's Bell Bearings (full stone ladder at Twin Maidens) | once each (progression-injectable path; gate on `auto_upgrade==OFF`) |
| 5. Flask power | Golden Seeds, Sacred Tears | capped at vanilla qty |
| 6. Money / runes | Numen's/Lord's/Hero's Rune, Golden Rune [10]–[13] | **elastic stackable** — absorbs remaining slack |
| 7. Upgrade material floor | Somber/regular stone floor to a target count | **elastic stackable**, gate on `auto_upgrade==OFF` |
| 8. Misc consumables | boluses, grease, top throwables | weighted stackable |

Rungs 1-5 are finite (curated, capped) → they set the *quality floor*. Rungs 6-8 are elastic →
they guarantee N is hit no matter how thin the finite rungs are. **This is the "build to a size"
guarantee**: as long as rungs 6-7 exist, any target N is fillable with a playable result.

### Tier-data status (rung 2 supply)
- **Weapons / armor / spells** — covered in `item_tiers.tsv` → `ITEM_TIERS`.
- **Ashes of War** — ADDED 2026-06-17. All 105 transferable AoW rated (category `ASHOFWAR`,
  S9/A26/B43/C23/D3/F1; source `ashofwar:pve-curated-2026-06`). S-tier AoW auto-flow into the
  `relevance_uplift` unique injects (the `ITEM_TIERS` S-tier scan at `__init__.py:1268` is NOT
  category-gated), and the trim is unaffected (it's WEAPON/ARMOR-gated at `:3387`). See
  [[er-ashofwar-tiers]].
- **Talismans (ACCESSORY)** — STILL A GAP. `relevance_uplift` uses a hand list
  (`UPLIFT_TALISMANS_S`); fold into the `item_tiers.tsv` pipeline (Phase 2) for the builder.
- **Spirit ashes** — hand list (`UPLIFT_SPIRITS_TOP`); fine as-is, tiering optional.

### Keep some junk on purpose — "bad checks are part of the spirit of AP" (Alaric, 2026-06-17)

The builder should NOT cut every low-tier item. A multiworld where every check is a banger
loses the AP texture where opening a chest and getting a Soiled Loincloth is a real (funny,
deflating) outcome. So the curation cut is a **dial, not a binary**: retain a small,
randomly-sampled fraction of bad-tier items in the pool rather than dropping them wholesale.

- Add a `junk_retention` knob (fraction 0.0–1.0, or an absolute count; default small, e.g.
  0.1–0.15). Before the bad-gear / dlc-filler defer sets are funded-swapped away, randomly
  *spare* `junk_retention ×` of them so they stay live in the pool as deliberately-mediocre
  checks. Cheapest/worst-first ordering is preserved for the rest.
- Interacts cleanly with the elastic backfill: spared junk just occupies slots that runes
  would otherwise fill, so count accounting is unchanged (one spared junk = one fewer rune).
- This is a *philosophy applied to the curation cut*, so it belongs here (and is shared by
  trimmed / dlc_only / legacy-dungeons): the goal is a pool that's mostly great with a
  deliberate seasoning of junk, not a pool scrubbed sterile.

**Funny junk, not just mediocre junk (Alaric, 2026-06-17).** Retention is **weighted toward
comedy**, not uniform-random over all C-tier filler. A boring B-tier longsword is not a funny
bad check; *throwable excrement* is. So `junk_retention` draws from a curated `COMEDY_JUNK`
anchor set first, and only falls back to generic low-tier filler if the comedy budget is
exhausted. Anchors confirmed present in `item_table` (2026-06-17):

- **The Excrement trio** — `Blood-Tainted Excrement`, `Gold-Tinged Excrement`,
  `Horn-Strewn Excrement` (throwables that fling dung; the platonic ideal of a bad check).
- **`Soiled Loincloth`** — the F-tier "you are now naked and worse off" armor piece.
- **`Toxic Mushroom`** — a "consumable" that poisons *you*; trap-item comedy.
- **`Dung Eater Puppet`**, **`Fly Mold`**, **`Raw Meat Dumpling`** — gross-out flavor.
- **`Ash of War: No Skill` (F)`, `Ash of War: Kick` (D)** — now that AoW are tiered
  ([[er-ashofwar-tiers]]), the joke ashes are first-class comedy junk.
- **`Festering Bloody Finger`** — useless invasion item in a solo run; situational comedy.

Implementation: a `COMEDY_JUNK` name set in `curation.py` (hand-curated, exact item_table
names; extend freely). `junk_retention` spares from `COMEDY_JUNK ∩ pool` with high weight,
then generic F/D filler with low weight. Tunable split (default ~70% comedy / 30% generic).
Count-neutral as above (one spared = one fewer rune). Optional flavor: classify retained
comedy junk so the in-game check indicator ([[er-ingame-check-indicators-spec]]) still glows —
the glow promising treasure and delivering excrement is, itself, the joke.

### Comedy-junk INJECTION (the not-naturally-present case) — sketch

Retention only protects comedy junk that's *already in the pool*. But in the two modes that
most want seasoning — `trimmed` and `dlc_only` — the funny items mostly aren't there: their
native locations were cut, so their default-item slots never entered the pool (and base-game
comedy can't appear in a DLC-only location set at all). Retention has nothing to spare. So we
need to **inject** a few, which is the comedy-sized instance of the builder's core "build to a
target" move.

**Funding = divert backfill slots, not displacement.** `create_items` ends with a filler
backfill (`__init__.py:1074-1075`):

```python
# Extra filler items for locations containing skip items
self.local_itempool.extend(self.create_item(self.get_filler_item_name())
                           for _ in range(num_required_extra_items))
```

Those `num_required_extra_items` slots are *already* budgeted filler (runes, under
`filler_replacement`). Injection just makes a few of them comedy items instead — so it is
**count-neutral by construction**, needs no skip/displace, and works even when zero comedy is
naturally present (the budget exists regardless). Thematically perfect under `filler_replacement`:
each injected joke is literally a rune the player *didn't* get.

**Target/floor model.** One knob, an absolute count (percentages don't work when the natural
count is zero):

- `junk_injection` (Range 0–N, default ~4) = guarantee *at least* this many comedy checks.

```python
# inserted just BEFORE the "# Extra filler items" backfill (line ~1074):
target = self.options.junk_injection.value
if target > 0 and num_required_extra_items > 0:
    already = sum(1 for _it in self.local_itempool if _it.name in COMEDY_JUNK)  # natural + retained
    grantable = [n for n in COMEDY_JUNK
                 if n in item_table
                 and (self.options.enable_dlc or not item_table[n].is_dlc)]
    need = min(max(0, target - already), num_required_extra_items)
    for _ in range(need):
        if not grantable:
            break
        _name = self.random.choice(grantable)
        _itm = self.create_item(_name)
        _itm.classification = ItemClassification.filler   # never let a comedy item gate fill
        self.local_itempool.append(_itm)
    num_required_extra_items -= need        # the backfill below now fills the remainder
```

**Edge cases / decisions:**
- **DLC availability** — `enable_dlc or not is_dlc` filters out DLC-only comedy (Horn-Strewn
  Excrement, Fly Mold) when DLC is off. Base-game comedy is always grantable: item *definitions*
  are always registered, so injecting them under `dlc_only` is fine (same fact uplift relies on).
- **Force `filler` classification** — a couple of comedy items aren't default-filler (e.g.
  Festering Bloody Finger); force filler so injection never perturbs progression balancing.
- **Multiworld scatter is a feature** — injected comedy is normal filler, so it travels the
  multiworld: *your* Blood-Tainted Excrement may land in someone else's world. Maximally in the
  spirit of AP; don't force it local.
- **Retention + injection compose** — retention spares what's present; injection tops up to the
  floor. Net contract: "at least `junk_injection` funny checks, plus a `junk_retention` fraction
  of any that occur naturally." Avoid double-counting by computing `already` *after* retention
  has run (retained items are in the pool by then).
- **Budget starvation** — if `num_required_extra_items == 0` (no skip/drop slots this seed),
  injection can't fire without displacing. Rare; acceptable to no-op. If a hard floor is ever
  required, fall back to the count-neutral *swap* pattern (skip one cheapest rune per injected
  joke), but the backfill-divert path is cleaner and almost always sufficient.
- **Weighting** — `self.random.choice` is uniform over the comedy list; swap for a weighted pick
  if you want the Excrement trio to headline. Cheap to add later.

Status: SKETCH only — not in `patch_comedy_junk.py` yet (that patch is the count-neutral
*retention* half). Injection is the first piece that genuinely "builds toward a target," so it's
the natural bridge from this comedy feature to the full ladder builder above.

### Item-source fact this relies on (already proven)
Item *definitions* are always registered (`item_name_to_id` uses the full `item_table`);
`enable_dlc` / region locks govern which *checks* exist, **not** whether an item may be
*granted* or *placed in the pool*. [[er-relevance-uplift]] and `dlc_gear_curation` already
exploit this — injecting base-game items into DLC space and vice-versa. So the ladder may draw
from the whole game regardless of which regions are walled. No new randomizer/baker capability
needed for the *items*; this is apworld pool composition.

## Money & upgrades — the two pillars that make "playable at any size" work

The user's two named requirements, made concrete:

**Money (runes) = the elastic filler.** Replace generic `get_filler_item_name()` backfill with
a rune ladder (Golden [10]→[13] → Hero's → Lord's → Numen's, weighted toward mid). Already
half-done: `filler_replacement` ([[er-filler-replacement]]) swaps filler for runes, and the
rune-skip demand-drop ([[er-rune-skip-for-injectable-room]]) injects small Golden Runes when
short. The builder makes runes the *default* backfill currency, not a toggle — because with no
open world, runes are how the player buys what they can't find.

**Upgrades = make the curated gear usable.** Iconic weapons are worthless without the stone
ladder. Two complementary levers, both already specced:
- **`auto_upgrade` ON** — weapons auto-scale, no stones needed; simplest, and the right default
  for reduced-scope modes ([[er-auto-upgrade-noop]]). When on, rungs 4 & 7 are suppressed.
- **`auto_upgrade` OFF** — supply upgrade *access* (Miner's Bell Bearings → full ladder at the
  Twin Maidens, reachable via Roundtable) + a stone floor (rung 7). Depends on shop-refresh-on-
  unlock ([[er-merchant-bell-bearing-logic]], [[er-qol-patches-shop]]); if that isn't wired,
  fall back to `auto_upgrade` ON.

Together: curated gear (quality) + upgrade access (usability) + runes (elastic fill + buying
power) = a pool that is good *and* exactly size N *and* playable, independent of what the
included locations natively held.

## Where it plugs into create_items

The accounting already exists — generalize it, don't rebuild:
- `num_required_extra_items` already tracks "slots needing backfill." Keep it; it becomes the
  builder's running deficit toward N.
- The three demand-drop fixes (small runes / inject reserve / cheap filler,
  `__init__.py:1003-1032`) already free slots for mandatory injectables. Keep as-is.
- The count-neutral swap blocks (`dlc_gear_curation` `:1047`, `relevance_uplift` `:1059`) become
  **two instances of one generic `_fund_swap(deferred, ladder_names)` helper.**
- The final filler backfill (`:1069`) is the hook to replace: instead of
  `get_filler_item_name() × num_required_extra_items`, call
  `_ladder_backfill(num_required_extra_items)` which draws rungs 6-8 (weighted) — or the full
  ladder when a mode opts into full recomposition.

A mode declares a **pool profile**: `{native_keep: bool, ladder: [rungs], weights, caps,
auto_upgrade_default}`. `open_world` = native_keep all, ladder off (today's behavior, unchanged).
`legacy_dungeons` = native_keep advisory, full ladder on. `dlc_only` = native_keep + funded swap
(today's relevance_uplift). One mechanism, per-mode config.

## Work items

1. **Factor the ladder.** Move the uniques/stackables/caps/weights data from the
   `relevance_uplift` draft into a shared `pool_ladder.py` (or extend `curation.py`): rung
   definitions, supply rules, tier sources (`item_tiers.tsv` for weapons/armor/spells; hand
   lists for talismans/spirits until ACCESSORY tiers land — see [[er-relevance-uplift]] Phase 2).
2. **Generalize the swap.** Replace the two bespoke swap blocks with one `_fund_swap`; verify
   `relevance_uplift` and `dlc_gear_curation` reproduce byte-for-byte (regression).
3. **Ladder backfill.** Replace generic filler backfill with `_ladder_backfill`; default rungs
   6-8 for all modes (so even `open_world` backfill could optionally be runes instead of junk —
   behind a flag, default off to preserve current behavior).
4. **Pool profiles.** Per-mode config object; wire `open_world` / `dlc_only` / `legacy_dungeons`
   / `trimmed` to their profiles. `open_world` profile must be a no-op vs today.
5. **Upgrade pillar.** Wire rungs 4 & 7 to `auto_upgrade==OFF` + the bell-bearing progression-
   injectable path; honor the shop-refresh dependency or fall back.
6. **GEN-TEST.** Per profile: assert pool size == location count exactly; assert mandatory
   progression all seated (no region-lock spill — [[er-trimmed-lock-spill]]); assert no
   `progression` item rode an elastic rung; assert caps respected (≤ vanilla qty for stones/
   pouches/seeds); beatability across seeds on Windows ([[er-dev-environment]]).

## Open questions

- **How much recomposition is too much?** Full-ladder modes risk feeling samey (every seed = the
  same S-tier set + runes). Keep native contents as the *first* source and only recompose the
  deficit? Or weight the ladder with enough breadth (A/B tiers, not just S) to stay varied?
  Lean: native-advisory — keep good native items, recompose only junk + deficit.
- **Per-seed variety caps.** One Mimic Tear is a jackpot; five is silly ([[er-relevance-uplift]]
  open question). Caps belong in the ladder supply rules; pick defaults per rung.
- **`open_world` opt-in.** Should normal seeds be able to opt into rune-backfill instead of junk
  filler? Probably yes as a toggle (`filler_replacement` already gestures at this) — but default
  off to keep vanilla-AP behavior.
- **Relationship to `filler_replacement`.** That option becomes a *special case* of rung 6 (money
  backfill). Decide whether to subsume it or keep it as the user-facing name for the builder's
  money rung.
