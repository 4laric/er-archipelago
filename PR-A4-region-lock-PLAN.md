# PR A4 — region-lock enhancements (decomposition, not one PR)

**Target:** `lBedrockl/Archipelago` (base `main`), path `worlds/eldenring/`
**Files in play:** `__init__.py` (`_region_lock`, `_region_lock_warp_access`, `fill_slot_data`),
`options.py` (WorldLogic + region sub-options), `region_spine.py`, `grace_data.py`,
`map_region_data.py`.

## Reframe (important)
A4 is **not** "introduce region lock." The base mechanism almost certainly already exists upstream:
`WorldLogic` defaults to `region_lock` (option 0), `_region_lock()` wires the lock→entrance rules,
and older options (`RegionBossPercent`, `RegionSoftLogic`, `GreatRunesRequired` — "ignored if Region
Lock is On") read as pre-existing fork core. What **we** added is an enhancement layer, dated in the
code to 2026-06-14/15:
- **Grace bundle / region fusion** — `GracesPerRegion` option, `grace_data.REGION_GRACE_POINTS`,
  spatial `_spread` selection, boss/border grace skip, `regionGraces` + `startGraces` slot_data.
- **RegionAccessLogic** (geographic vs **warp**) — `_region_lock_warp_access()`.
- **RegionCount / Capital spine** — `region_spine.py`, short "reach Morgott" runs.
- **Physical enforcement** — `areaLockFlags`/`lockRevealFlags`/`regionOpenFlags`, `map_region_data.py`.

## DECISION GATE (do this before any region PR)
Diff the region machinery against `lBedrockl/Archipelago@main` to establish the exact upstream
baseline — i.e. which of the above already exists there. This decides, per piece, whether it's a
"new option" PR or an "enhance existing" PR, and whether option enums/defaults collide. Nothing below
should be opened until this diff is in hand. (Issues are disabled on the fork, so there's no issue to
file — capture it as a draft-PR description or a direct note to the maintainer.)

---

## Sub-PRs, ordered by how cleanly they detach from our client/baker

### A4-warp — RegionAccessLogic (geographic | warp)  ← cleanest first region PR
- **Scope:** `options.py` `RegionAccessLogic` + `__init__.py` `_region_lock_warp_access()` (adds a
  direct `Limgrave → region` entrance gated on the region's OWN lock when `region_access == warp`).
- **Why upstreamable:** pure **logic** — it only changes how the fill models *reaching* a region.
  No slot_data, no client dependency, no baker. Self-contained.
- **Caveat:** "warp" is most meaningful alongside the grace bundle (so you can actually fast-travel
  in), but it's logically valid on its own. Frame it as an access-model option; mention the grace
  bundle as a complementary follow-on.
- **Status:** ready after the decision gate + a stock gen-test.

### A4-count — RegionCount / Capital spine
- **Scope:** `region_spine.py` (new, self-contained: pure data + one function, owns no AP types) +
  `options.py` `RegionCount` + the `generate_early` wiring that seals regions past the count.
- **Why upstreamable:** pure logic/fill — seals out-of-scope regions by pulling their lock items and
  locking their checks to vanilla events. No client, no baker. High standalone value (short runs).
- **Caveat:** only engages with `ending_condition == capital` + a lock-based world logic; the caller
  already warns otherwise. Keep our `dlc_only` and trimmed interactions OUT of the PR.
- **Status:** ready after the decision gate + a stock gen-test. Good second region PR.

### A4-grace — Region grace bundle (region fusion)  ← client-coupled
- **Scope:** `options.py` `GracesPerRegion` + `grace_data.py` (`REGION_LOCK_ITEM`,
  `REGION_GRACE_POINTS`) + `fill_slot_data` emit of `regionGraces` / `startGraces` (spatial `_spread`,
  boss/border grace skip).
- **Dependency that blocks a clean solo PR:** the option only does anything with **a client that
  consumes `regionGraces`** (sets the chosen grace flags on lock receipt). Upstreaming it alone ships
  a dead option to anyone on the stock client. Options: (a) pair it with the client PR (Track E), or
  (b) hold until the client side is upstreamed, or (c) ship behind a clearly-documented "requires
  compatible client" note. Recommend **hold-and-pair**, not solo.
- **Status:** blocked on client; do not open standalone.

### A4-enforce — Physical region-lock enforcement  ← EXCLUDE from apworld upstream
- **Scope:** `areaLockFlags`/`lockRevealFlags`/`regionOpenFlags` slot_data + `map_region_data.py`
  (area-id ranges + reveal flags).
- **Why excluded:** enforcement needs the **client** (detect current area, set open flags) AND the
  **baker** EMEVD fog-walls, which live in `SoulsRandomizers` — the licensing-landmine repo we're
  parking. The apworld can emit the slot_data, but with no consumer upstream it's inert and ties the
  world to our toolchain. Leave it out; it's the "fog-wall belongs in the baker" piece.
- **Status:** parked with Track D.

---

## Design-first step (because Issues are disabled on lBedrockl)
Open **A4-warp as a draft PR** with a short design note covering the access-model option and pointing
at the grace-bundle/count follow-ons, and invite the maintainer to weigh in on option naming/enum
values before it's marked ready. That doubles as the "is this wanted / does it collide with upstream
options" conversation that would normally be an issue.

## Net: region-lock upstreaming path
1. Decision gate (diff vs lBedrockl@main).
2. **A4-warp** draft PR (design sign-off) → ready.
3. **A4-count** PR.
4. **A4-grace** only once the client is upstreamed (pair them).
5. **A4-enforce** excluded (Track D / landmine).
