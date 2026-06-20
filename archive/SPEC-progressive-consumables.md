# SPEC: Progressive consumable-upgrade items (flasks, scadu, revered ash) + glovewort bells

Status: DRAFT (2026-06-17, Alaric). Five items in one family, all modelled on the
already-implemented stone-bell pattern. Related / reused:
`SPEC-progressive-stone-bells.md` (the template), `stone_bells.py` (grant-table shape),
`patch_client_bell_overflow_rune.py` + `[[er-bell-overflow-rune]]` (overflow → Lord's Rune),
`patch_apworld_progbell_count.py` / `patch_apworld_progbell_early.py` (pool/early knobs),
`SPEC-scadu-in-base.md` + `[[er-dlc-only-spec]]` (scadu/revered curves & speffects — do NOT
re-derive, reuse), `patch_scadu_frontload.py` (`scadu_frontload` early-bias, which this
generalises).

The five:

1. **Progressive Sacred Tear** — flask *potency* (Sacred Tears).
2. **Progressive Golden Seed** — flask *charge count* (Golden Seeds).
3. **Progressive Scadutree Fragment** — DLC combat blessing.
4. **Progressive Revered Spirit Ash** — DLC summon + Torrent blessing.
5. **Progressive Glovewort Bell** (the outstanding one) — Grave + Ghost glovewort tiers at
   Roderika's spirit-tuning shop. Direct sibling of the stone-bell spec.

---

## 0. The shared model (read this once, applies to all five)

Each feature takes a pile of **fungible** vanilla consumables/bells and collapses it into a
**single progressive item** (or two, where there are two parallel tracks) with four shared
properties, exactly as the stone bells already do:

1. **Defined meaningful max tier** = the vanilla cap. Copies up to the cap "do something";
   copies past it are handled by overflow (below), never a silent no-op.
2. **Cumulative logic gate** — `state.has(name, self.player, K)`, identical to
   `_bell_bearings_required`. Anything that today needs "N Golden Seeds" / "N fragments"
   reads the progressive count instead.
3. **Overflow → Lord's Rune.** Past the meaningful cap, grant a Lord's Rune (goods `2919`)
   per the existing `patch_client_bell_overflow_rune.py` path (`[[er-bell-overflow-rune]]`).
   This is what lets pool-count exceed the tier count without dead checks — reuse it
   verbatim; it is already the bell's behaviour.
4. **Three tuning knobs**, mirroring `stone_bells.py`: a per-item `*_POOL_COUNT` (how many
   copies seed into the pool), `*_EARLY_COUNT` (copies forced into sphere-1 via
   `early_items`), and a yaml `Range` option for the pool count
   (`patch_apworld_progbell_count.py` shape). One new module per family holds the grant
   table (the `stone_bells.py` "single source of truth" pattern).

### The one axis that splits the five: how the level is *realised* in-game

The stone bells had a clean **Option B**: set `eventFlag_forStock` on a shop row — setting
the flag *is* the unlock, idempotent, client-settable. Whether each of these five can do the
same depends entirely on whether the target state is a **settable shop flag** or a **stored
player-data level the game recomputes on load**:

| Feature | Realisation | Recommended option | Why |
|---|---|---|---|
| Glovewort bells | Roderika shop `eventFlag_forStock` | **B (set flag)** | Identical to stone bells — a real shop row gate. |
| Sacred Tear / Golden Seed | flask potency / charge count (stored player data) | **A (grant consumable)** | No settable flag exists; the count is recomputed/validated. Force-writing it is fragile. |
| Scadutree Fragment / Revered Ash | blessing level (stored, recomputed on map load) | **A in `dlc_only`** (grant goods, revere at a Land-of-Shadow grace); **client speffect (scadu-spec Route A)** only for the base-game-transplant case | Map-load recompute stomps a poked speffect (documented in `SPEC-scadu-in-base.md`). |

Option A's one honest cost: under A the **in-game stat only rises when the player spends the
consumable**, so `state.has(K)` (logic) can lead the actual flask/blessing level until they
turn it in. That's acceptable for a self-buff (no logic *requires* the heal/blessing to be
spent) but must NOT be used to gate progression that assumes the buff is live. It is fine for
all four non-bell items here because none gate access on the buff being active.

> Honesty note on "progressive": Sacred Tears, Golden Seeds, fragments and ashes are
> **fungible** — copy K is identical to copy 1, there is no forced order between them (unlike
> the bells, where +7 before +1 is useless). So for the four consumables the "progressive"
> item is really a **count-cap + overflow + single-name** wrapper, not a true ordered ladder.
> It still earns its keep: the cap retires dead late-game copies into runes, the single name
> is clean for trackers / trimmed pools, and `early_items` biasing is per-item. The glovewort
> bells ARE a genuine ordered ladder, like the stone bells.

---

## 1. Progressive Sacred Tear — flask potency

**Vanilla facts** (Fextralife, base game): **12 Sacred Tears**, each `+1` flask potency,
linear, max potency `+12`. Sacred Tear = goods **`10020`**. Affects both Crimson and Cerulean
flasks. Spent at any Church / minor erdtree site — available from the start, no DLC gate.

- **Meaningful max tier: 12.** Pool copies past 12 → Lord's Rune overflow.
- **Realisation: Option A.** Grant goods `10020`; player turns it in at a church. No flag to
  set; the game owns potency. (Option B would mean writing the stored potency level, which is
  recomputed on rest — fragile, not worth it for a heal buff.)
- **Logic:** none today gates on potency; keep it a `useful` self-buff (matches current
  `Sacred Tear` classification at items.py:1923). Do NOT mark progression.
- **Knobs:** `POOL_COUNT` default ~12 (one full ladder), `EARLY_COUNT` 0–2, yaml
  `progressive_sacred_tear_count` Range 0..20.

## 2. Progressive Golden Seed — flask charge count

**Vanilla facts** (Fextralife): start at 4 charges, max **14**; reached via **10 upgrade
steps** costing a rising number of Golden Seeds — `[1,1,2,2,3,3,4,4,5,5]` seeds per step, so
**30 Golden Seeds total** to max. Golden Seed = goods **`10010`**. Cumulative seeds to reach
charge-step k (k=1..10): `[1, 2, 4, 6, 9, 12, 16, 20, 25, 30]`.

- **Meaningful max tier: 30** (the seed count that maxes charges). Past 30 → Lord's Rune.
- **Realisation: Option A.** Grant goods `10010`; player raises charges at any grace. The
  game already owns the `[1,1,2,2,3,3,4,4,5,5]` cost curve, so the client does **not** need to
  replicate it — that is the whole reason A beats B here. (Embed the cumulative table only if a
  tracker wants to show "charges = f(seeds received)".)
- **Logic:** `useful`, not progression (matches `Golden Seed` at items.py:1922).
- **Knobs:** `POOL_COUNT` default ~30, `EARLY_COUNT` 0–3 (a couple early seeds smooth the
  opening), yaml `progressive_golden_seed_count` Range 0..40.

> Flask combined note: 1 + 2 together turn the flask economy into two clean progressive
> tracks. They compose with `filler_replacement` (`[[er-filler-replacement]]`) and the trimmed
> pool — deliver the flask ladder via these instead of scattering 40+ raw seed/tear checks.

## 3. Progressive Scadutree Fragment — DLC combat blessing

This is the **item-delivery + cap + overflow** layer on top of the already-resolved
`SPEC-scadu-in-base.md`. Do not re-derive curves or speffects; reuse:

**Vanilla facts** (already confirmed in the scadu spec): Scadutree Fragment = goods
**`2010000`** (and `Scadutree Fragment x2`, same id, `count=2`, items.py:2737-2738).
**50 fragments → combat blessing L20.** Combat speffect `20000100 + N`. Cumulative fragments
to REACH level N (21 entries):
`[0,1,3,5,7,9,11,13,15,17,20,23,26,29,32,35,38,41,44,47,50]`.

- **Meaningful max tier: 50.** Past 50 → Lord's Rune.
- **Realisation:**
  - **`dlc_only` (primary use): Option A.** The player IS in the Land of Shadow, so the vanilla
    "Revere Scadutree Fragment" grace ritual works — grant goods `2010000`, player reveres.
    Robust, no map-load stomp. This already overlaps `patch_scadu_frontload.py`; fold
    `scadu_frontload` INTO this item's `EARLY_COUNT` knob (front-loading N fragments into
    sphere 1 is exactly `EARLY_COUNT = N`). Deprecate the standalone option in favour of the
    unified one, or alias it.
  - **base-game transplant case: client-derived speffect (scadu-spec Route A).** Where revering
    is impossible (no Land-of-Shadow grace), the client owns the level from the AP grant count
    via the cumulative table above and applies `20000100 + N_combat` scoped to the
    transplanted-DLC-boss arena. That is `SPEC-scadu-in-base.md` Tier 1 — this progressive item
    is just the grant-count source it reads.
- **Logic:** `useful` (matches items.py:2737). If a future DLC difficulty option wants to
  *require* a minimum blessing for a region, that's where `state.has(..., K)` plugs in — but
  default off.
- **Knobs:** `POOL_COUNT` default ~50, `EARLY_COUNT` default 8 (inherits the current
  `scadu_frontload` default), yaml `progressive_scadu_count` / keep `scadu_frontload` as the
  early alias.

## 4. Progressive Revered Spirit Ash — DLC summon + Torrent blessing

Same layer over the scadu spec, summon track. Revered Spirit Ash = goods **`2010100`** (+ `x2`
variant, items.py:2739-2740). **25 ashes → summon blessing L10.** Drives BOTH the summon
speffect `20000200 + N` AND the Torrent speffect `20000300 + N` off the same level. Cumulative
ashes to REACH level N (11 entries): `[0,1,2,3,5,7,10,13,16,20,25]`.

- **Meaningful max tier: 25.** Past 25 → Lord's Rune.
- **Realisation:** identical structure to §3 — Option A in `dlc_only` (revere at grace),
  client-derived dual speffect (`20000200+N` and `20000300+N`) for the transplant case. The
  scadu spec notes Revered Ashes were left untouched by `scadu_frontload` (combat-only); this
  item adds the missing summon-track early-bias.
- **Knobs:** `POOL_COUNT` default ~25, `EARLY_COUNT` default ~4, yaml
  `progressive_revered_ash_count` Range 0..30.

> §3 + §4 share one new module (`scadu_grants.py` or fold into a `consumable_grants.py`) and,
> in the client, the single speffect-apply path that `SPEC-scadu-in-base.md` already specs.
> This spec contributes only the apworld items, the cap/overflow, and the early-bias knobs.

## 5. Progressive Glovewort Bell — Roderika spirit-tuning shop (THE OUTSTANDING ONE)

Exact sibling of `SPEC-progressive-stone-bells.md`: **Option B (set `eventFlag_forStock`)**,
because the target is a real shop — Roderika's spirit-tuning shop at Roundtable Hold, which
gates Grave / Ghost Glovewort (the Spirit Ash upgrade materials) just as the Twin Maidens gate
smithing stones. Two progressive items, two parallel ladders:

- **Progressive Grave-Glovewort Bell** — 3 copies. Vanilla bells (items.py:1787-1789):
  `Glovewort Picker's Bell Bearing [1]/[2]/[3]` = **8960 / 8961 / 8962**.
- **Progressive Ghost-Glovewort Bell** — 3 copies (items.py:1790-1792):
  `Ghost-Glovewort Picker's Bell Bearing [1]/[2]/[3]` = **8963 / 8964 / 8965**.

Bell → glovewort tier (vanilla, for the cosmetic-goods grant and tier labels):

| Copy | Bell id | Glovewort unlocked |
|---|---|---|
| Grave 1 | 8960 | Grave Glovewort [1]–[3] (goods 10900–10902) |
| Grave 2 | 8961 | Grave Glovewort [4]–[6] (10903–10905) |
| Grave 3 | 8962 | Grave Glovewort [7]–[9] (10906–10908) + Great Grave Glovewort (10909) |
| Ghost 1 | 8963 | Ghost Glovewort [1]–[3] (10910–10912) |
| Ghost 2 | 8964 | Ghost Glovewort [4]–[6] (10913–10915) |
| Ghost 3 | 8965 | Ghost Glovewort [7]–[9] (10916–10918) + Great Ghost Glovewort (10919) |

- **Meaningful max tier: 3 per track.** Past 3 → Lord's Rune (same as stone bells).
- **Realisation: Option B.** On copy K set that rung's `eventFlag_forStock` group on Roderika's
  spirit-tuning shop rows, and grant the cosmetic bell goods (8960+…) for the menu record —
  byte-for-byte the stone-bell flow in `stone_bells.py` + the client receive handler.
- **OUTSTANDING DATA ITEM (the one gap):** the Roderika shop `eventFlag_forStock` groups are
  NOT yet extracted. The stone-bell flags (280080…280280) came from
  `vanilla_er/ShopLineupParam.csv` (Twin Maiden shop IDs 1018xx). Extract the Roderika
  spirit-tuning block the same way and fill a `GLOVEWORT_BELL_GRANTS` table mirroring
  `STONE_BELL_GRANTS`. **Do not guess these flag ids** (`[[er-event-flag-validity]]`,
  `[[verify-files-before-naming]]`) — probe set→readback before shipping.
- **Gating:** like the stone bells, only meaningful when Spirit Ash upgrading matters. Pair
  with `auto_upgrade`-style logic if a future spirit-ash auto-upgrade lands; otherwise it's a
  pure QoL ladder. Roundtable reachable in `dlc_only` (`startGraces` 71190), so usable there.

---

## 6. apworld changes (all five) — LOW effort, mirrors the bells

`items.py` — add the progressive items, all with the existing sentinel er_code **`99998`**
(the routing the stone bells already use, so the receive loop doesn't warn "not in pool"):

```python
ERItemData("Progressive Sacred Tear",        99998, ERItemCategory.GOODS, classification=ItemClassification.useful),
ERItemData("Progressive Golden Seed",        99998, ERItemCategory.GOODS, classification=ItemClassification.useful),
ERItemData("Progressive Scadutree Fragment", 99998, ERItemCategory.GOODS, classification=ItemClassification.useful),
ERItemData("Progressive Revered Spirit Ash", 99998, ERItemCategory.GOODS, classification=ItemClassification.useful),
ERItemData("Progressive Grave-Glovewort Bell", 99998, ERItemCategory.GOODS, classification=ItemClassification.progression),
ERItemData("Progressive Ghost-Glovewort Bell", 99998, ERItemCategory.GOODS, classification=ItemClassification.progression),
```

New grant-table module(s) modelled on `stone_bells.py`:
- `glovewort_bells.py` — `GLOVEWORT_BELL_GRANTS` (goods + flags, flags TBD via §5 extraction),
  `*_POOL_COUNT`, `*_EARLY_COUNT`.
- `consumable_grants.py` — for the four fungible items: per-item `{goods, cap, overflow_goods:
  2919}` + cumulative tables (scadu/revered from the scadu spec; flask tables from §1/§2) +
  `*_POOL_COUNT` / `*_EARLY_COUNT`. (Fungible items need no per-tier flag list — just the goods
  id, the cap, and the overflow.)

`options.py` — one Toggle per family plus the Range count knobs (reuse the
`progressive_stone_bells` / `progbell_count` dataclass shapes):
`progressive_flasks`, `progressive_scadu_blessing`, `progressive_revered_blessing`,
`progressive_glovewort_bells`, and the `*_count` Ranges.

`__init__.py` — for each active feature: drop the discrete vanilla items from the pool
(location stays a check), add the progressive copies to `_all_injectable_items` / the dlc_only
priority-injectable set (so they seat in-world, not spilled to start — same Fix A path the
stone bells use), wire `early_items` from `*_EARLY_COUNT`, and add `state.has(name, K)` rules
only where a feature opts into logic (glovewort if spirit-ash upgrading is gated; none of the
others by default). The rune-skip demand-drop (`[[er-rune-skip-injectable-room]]`) already
frees in-world slots for guaranteed injectables — these ride it.

`fill_slot_data` — emit:
- `progressiveGrants` (extend the existing stone-bell table) for the glovewort bells (flag
  groups, Option B).
- A new `progressiveConsumables` table for the four fungible items: name → `{goods, cap,
  overflowGoods: 2919}` (Option A grant + overflow). Absent ⇒ client no-ops (back-comp). Bump
  the `versions` band in lockstep with the client per the contract note.

## 7. Client changes — reuses existing paths, no new RE

- **Glovewort bells:** zero new code beyond data — they slot into the existing
  `progressiveGrants` consumer + per-item counter + reconnect `last_received_index` handling
  that the stone bells already ship. Just add the `GLOVEWORT_BELL_GRANTS` rows.
- **Sacred Tear / Golden Seed (Option A):** on the Kth copy, if `K <= cap` grant `goods`,
  else grant Lord's Rune `2919` — the overflow branch is literally
  `patch_client_bell_overflow_rune.py`. Counter + reconnect dedup = the same progressive path.
  No flag-set, no speffect.
- **Scadu / Revered:** in `dlc_only`, treat exactly like Sacred Tear/Golden Seed (grant goods
  `2010000` / `2010100`, overflow to rune past cap). The speffect-application path (transplant
  case) is owned by `SPEC-scadu-in-base.md`, not this spec — this spec only supplies the
  grant-count it reads. Reuse the persisted `progressiveCounter` / `progressiveHighIndex`
  index-dedup from `patch_client_progressive_persist.py` (`[[er-progressive-tier-persist]]`) so
  caps and overflow don't desync across reconnects.

## 8. Gating & interactions summary

- **`dlc_only`:** scadu (§3), revered (§4), glovewort (§5) all reachable/usable from load
  (`startGraces` 71190; player in Land of Shadow for revering). Primary home for §3/§4.
- **Trimmed pool** (`[[er-trimmed-curation-impl]]`): cut the raw seed/tear/fragment/glovewort
  checks, deliver the ladders via these items — the same trade the stone bells make.
- **`filler_replacement` / `pool-builder`:** these are count-capped with rune overflow, so they
  compose cleanly with count-neutral filler swaps and the pool-builder ladder.
- **Lord's Rune overflow** is shared across ALL of them and the stone bells — one code path
  (`2919`), already in-tree.

## 9. Effort / risk

- apworld: ~2–3 hrs total (6 items, 2 grant modules, ~4 toggles + count ranges, pool swaps,
  slot_data tables). Mechanically a copy of the stone-bell work.
- Client: glovewort = data-only (hours). Flask/scadu/revered Option A = the overflow branch +
  counter reuse (hours), NO new RE. Scadu/revered transplant speffect = deferred to the scadu
  spec.
- **Main risks:** (a) the un-extracted Roderika shop flags (§5) — probe before shipping;
  (b) Option A's logic-vs-realised lag (§0) — fine for self-buffs, never gate progression on a
  live buff; (c) reconnect counter/overflow desync — de-risked by the persisted index-dedup
  already in `patch_client_progressive_persist.py`.

## 10. Open questions for Alaric

1. **Flask split:** Golden Seeds add a charge the player allocates between Crimson/Cerulean;
   Sacred Tears up both. Under Option A that's automatic (vanilla menu). Confirm you don't want
   the client to force an allocation — leaving it to the player is simplest and vanilla.
2. **Scadu/revered scope:** is the near-term target `dlc_only` (Option A, revere at grace) only,
   or do you also want these wired to the base-game-transplant speffect now? The latter pulls in
   the bulk of `SPEC-scadu-in-base.md`.
3. **`scadu_frontload` fate:** fold it into `Progressive Scadutree Fragment`'s `EARLY_COUNT`
   (deprecate the standalone option), or keep both? Folding is cleaner; keeping avoids touching a
   working knob.
4. **Glovewort logic:** pure QoL ladder, or do you want spirit-ash upgrade tiers actually gated
   in logic (the way the stone bells gate weapon upgrades under `auto_upgrade == 0`)? Gating
   needs a spirit-ash-upgrade analog to exist first.
