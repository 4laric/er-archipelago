# HANDOFF — Track A: Apworld chain placement

Spec: SPEC-num-regions-chain.md (contract §4 is frozen). Track owner edits ONLY this file + the patch below.
Deliverable: `patch_apworld_num_regions_chain.py`

## Scope (files this track may touch)
- `Archipelago/worlds/eldenring/region_spine.py` — chain-order helper.
- `Archipelago/worlds/eldenring/__init__.py` — num_regions resolution block (the `if self.options.num_regions.value > 0:` region ~L221-258) + `_region_lock_warp_access` (~L2234).
- `Archipelago/worlds/eldenring/options.py` — new `num_regions_chain` toggle.
DO NOT touch `fill_slot_data` (Track B) or any `.cs` (Track C).

## Steps
- [x] options.py: `class NumRegionsChain(Toggle)` + `num_regions_chain` field added (after NumRegions / after the `num_regions` dataclass field).
- [x] region_spine.py: `compute_num_regions_chain_order(rng, kept_locks)` → ordered MIDDLE steps; Altus pinned last; Dragonbarrow kept right after Caelid; rest shuffled. (Limgrave hub + Leyndell terminus are implicit — the helper orders only the rolled middles; the hub/terminus are fixed by the seal.) Plus `NUM_REGIONS_CHAIN_STEP_LOCK` + `NUM_REGIONS_CHAIN_STEP_HOST_REGIONS` data tables and `_kept_middle_steps`.
- [x] __init__.py: (defaults init in generate_early) + (chain-order resolution at end of the num_regions scope block) + (inject=False de-pool of the managed chain locks in the lock-injection block) + new `_num_regions_chain_host` + `pre_fill` (precollects link-1 lock; `place_locked_item`s each later link's lock on the PRIOR link's prominent boss drop). Count-neutral: create_items' existing freed-slot→filler accounting covers the de-pooled locks.
- [~] Capstone tail: Altus pinned last → Altus→Capital Outskirts→Leyndell geography preserved; rune regions are middles so ≥2 runes land in the prefix. NOT runtime-verified (no gen-test in sandbox — needs Windows).

## Contract owned
None emitted. Output guarantee: post-fill `get_spheres()` is a linear 1..N region ladder. (Track B reads it generically.)

## Verify
gen-test; spoiler Playthrough shows N ascending spheres, each region's lock in the PRIOR region's boss, goal reachable. Watch the soft_progression×smithing_bell interaction (SPEC §9).

## Status / notes

**Track A patch written, dry-run-validated, NOT gen-tested** (sandbox can't run AP). Deliverable
`patch_apworld_num_regions_chain.py` at repo root (21010 bytes), 7 byte-spliced inserts, CRLF-safe,
idempotent (re-run = all [skip]), all anchors DISJOINT from Track B's `fill_slot_data`.

### What it does
Adds opt-in `num_regions_chain` (Toggle, default off; meaningful only with num_regions>0 + capital +
region_lock). When on, the kept num_regions middles are forced into a linear lock breadcrumb:
Limgrave is the free sphere-1 hub; the first rolled middle's lock is precollected; every later
middle's lock is `place_locked_item`-ed onto the PRIOR middle's prominent boss drop. Altus is pinned
last (capstone tail → Leyndell, which stays great-rune gated, no lock). Breadcrumbed + precollected
locks are pulled from the random injectable pool (inject=False) so they aren't double-placed/spilled;
the pool stays count-neutral. Result (intended): get_spheres() is a 1..N ladder.

### Anchors (file : after-text → marker)
1. region_spine.py : `return ... sealed_locks, effective` (end of compute_num_regions_scope) → `compute_num_regions_chain_order`
2. options.py : NumRegions `default = 0` → `class NumRegionsChain`
3. options.py : `    num_regions: NumRegions` field → `num_regions_chain: NumRegionsChain`
4. __init__.py : `        self._spine_effective_count = 0` → chain-state defaults
5. __init__.py : num_regions block's `raised to {_eff} ...` warning → chain-order resolution
6. __init__.py : the `self._spine_sealed_locks` inject=False loop → chain-lock de-pool
7. __init__.py : end of `_filler_replacement_name` (`return self.random.choices(...)[0]`) → `_num_regions_chain_host` + `pre_fill` (inserted BEFORE set_rules; anchoring AFTER `def set_rules` would split it from its body — caught + fixed in dry-run)

### Judgment calls / assumptions (need Alaric's Windows gen-test)
- **Breadcrumb host is chosen DYNAMICALLY** (not a hardcoded location string): per chain middle,
  `_num_regions_chain_host` scans that step's host region(s) and prefers a prominent remembrance/
  mainboss drop, then any non-missable boss drop, then any non-missable check. This handles regions
  with NO great-rune remembrance (Weeping / Dragonbarrow / Altus) uniformly. Rationale: Dragonbarrow's
  boss locations are tagged `caelid_boss`, so tag-based attribution is unreliable — region membership
  is the robust key. Verify the chosen hosts in the spoiler are sane (boss drops, not random filler).
- **Dragonbarrow (step 6)** has no own hub warp (absent from REGION_LOCK_ITEM/REGION_GRACE_POINTS) and
  is a geographic child of Caelid. The order helper pins it IMMEDIATELY AFTER Caelid when both are
  kept, so warp→Caelid + walk-in with the Dragonbarrow Lock works. If `compute_num_regions_scope`
  keeps Dragonbarrow WITHOUT Caelid (it doesn't couple them), pre_fill emits a warning and the seed
  may be unreachable under warp — GEN-TEST this combo, and consider excluding Dragonbarrow from the
  chain-eligible middles (or coupling it to Caelid in the SCOPE roll — that's a num_regions change,
  not chain-only, so deferred).
- **No usable host fallback**: if a predecessor has no usable host this seed, pre_fill PRECOLLECTS the
  next lock (loses one sphere of ramp) rather than softlock, and warns. Shouldn't fire for the normal
  middles but is a safety net.
- **`pre_fill` is the AP hook used** for placement (locations exist by then; `place_locked_item`
  removes the host from the fill pool before main fill). The locks are de-pooled in the inject block
  during generate_early. If AP's fill order surprises us, the fallback precollect prevents a hard fail.
- **soft_progression × smithing_bell** (SPEC §9): a chain Capital run still routes through Capital
  Outskirts' bell gate — keep `patch_apworld_softprog_bellgate_fix.py` applied or run smithing_bell off.

### Dry-run result (sandbox, against copies in /tmp)
- 7/7 inserts apply; re-run all [skip] (idempotent).
- CRLF preserved per-file (region_spine.py LF; options.py + __init__.py CRLF; bare-LF counts unchanged
  vs originals).
- region_spine.py + options.py `py_compile` OK (CRLF→LF temp copy).
- __init__.py: the LIVE source already fails to compile on its own — `fill_slot_data` (line ~4540,
  Track B's region) is currently truncated/unclosed on the mount (`slot_data = {` never closed, no
  `return slot_data`). With a synthetic stub closing that dict, the PATCHED file (all Track A inserts
  incl. pre_fill/set_rules boundary) compiles cleanly. **My inserts are valid; the only compile
  blocker is Track B's pre-existing in-flight `fill_slot_data` corruption — outside Track A's scope.**
  Alaric: ensure `fill_slot_data` is complete (Track B) before gen-testing.

### Footgun noted
The patch's PKG auto-resolution falls back to CWD; running the dry-run from inside the repo made it
patch the REAL source once. Reverted byte-identical from session-start copies. When dry-running, run
from a dir with NO region_spine.py on any candidate path (HERE / HERE/Archipelago/worlds/eldenring /
CWD), or point HERE at a throwaway copy.
