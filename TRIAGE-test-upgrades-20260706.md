# Test-upgrade triage — which existing tests were green while a bug shipped (2026-07-06)

Method: not an audit of the test files, but a pass over the **bug ledger**. A test that was
passing while a live bug shipped is, by definition, checking the wrong property. Those are the
only upgrade candidates; everything green that never coincided with a defect is left alone.

Tier legend (from `SPEC-semantic-test-tiers-20260706.md`): **A** = data-value correctness
(gen output vs the world / an independent source), **B** = cross-side contract (gen output vs
client assumptions), **C** = replay (client behaviour over a timeline).

## Findings

| Bug | Covered by | Property asserted | Green while broken? | Needed tier |
|---|---|---|---|---|
| gf-maplot-region-quarantine | none (one-time `--check` only) | NONE — `test_gf_data` checks structure/uniqueness, never region-of correctness | **yes** | **A** |
| gf-dungeon-grace-misbundle | none | NONE — same region-assignment blind spot | **yes** | **A** |
| er-boss-border-grace-skip-list | none (grace tests assert bundle shape/count) | COUNT/SHAPE, not skip-list membership | **yes** | **A** |
| er-boss-drop-suppress-leak | `vanilla_suppress_replay` (mock) | TIMELINE logic — but mocks the detection table, can't see 147 missing locs | **yes** (data-coverage) | **A** |
| gf-contract-options-subdict-gap | `test_gf_slot_data_fixture`, `test_death_link_flag_true` | CROSS-SIDE but shares contract.py's blind spot; asserts TOP-LEVEL `death_link`, not the `options` path the client reads | **yes** (now narrowed — `options` subdict landed in contract.py) | **B** |
| er-numregions-cave-start-graces | none | NONE | **yes** | A/C |
| gf-region-grace-loss-frontdoor-latch | `region_lock_replay` ✓ (wired, committed `4ef89ae`) | TIMELINE | no — now guarded | C ✓ |
| gf-start-item-clobber | `start_grant_replay` ✓ | TIMELINE | no | C ✓ |
| er-flask-double-grant-reconnect | `flask_grant_replay` ✓ | TIMELINE | no | C ✓ |
| er-torrent-regionlock-mountless | `torrent_start_replay` ✓ | TIMELINE | no | C ✓ |
| gf-flagpoll-newsave-default-flags | `flagpoll_baseline_replay` ✓ | TIMELINE | no | C ✓ |
| er-map-pieces / underground-82001 | `map_reveal_replay` ✓ | TIMELINE (regression guard) | no | C ✓ |
| deathlink death_link:0 | `deathlink_gate_replay` ✓ | TIMELINE | no | C ✓ |
| two-watermark reconnect | `receive_watermark_replay` ✓ | TIMELINE | no | C ✓ |
| gf-weapon-shop-slot-guard-unported | `test_gf_weapon_shop_slots.py` | SEMANTIC-VALUE (own-item on weapon slot must be a weapon) | no — shipped with the fix | solid |
| gf-important-locations | `test_gf_important_locations.py` | COUNT + SEMANTIC (item_rule forbids filler) | no | solid |
| gf-missable-locations | `test_gf_missable.py` | COUNT + SEMANTIC (no advancement placed) | no | solid |
| gf-slotdata-contract-completion | `test_gf_slot_data_fixture` keyset | PRESENCE/SHAPE — but LOUD (exact keyset) | no — the loud gate caught it | solid |

## The backlog, in ROI order

**1. Region-of correctness gate (tier A) — one gate, three bugs.** `map_lot` mislabels,
dungeon-grace mis-bundle, and boss/border grace-skip all share the same hole: `test_gf_data`
asserts a region assignment is *well-formed and unique*, never that it is *right*. Add one
SEMANTIC-VALUE invariant: every location/grace's assigned region matches an **independent**
ground truth — the placed-item tile (MSB/ItemLot in `elden_ring_artifacts/`) and `flag_source`
— not a re-run of `gen_data`'s own derivation (or it inherits the bug). This is the highest-value
missing tier and it retires three green-while-broken bugs at once.

**2. Upgrade the contract fixture test to assert client-READ paths (tier B).**
`test_gf_slot_data_fixture` validates against `contract.py`, so it inherits its blind spots, and
`test_death_link_flag_true` asserts the top-level key, not the `sd["options"][...]` path the
client actually reads. The `options` subdict now exists in `contract.py` (committed), so the
immediate leak is closed — but the *test* still gives false confidence. Upgrade: grep the client
for every `sd.get(...)` / `pointer(...)` and assert each path has a producer, so the next
path-mismatch fails a test instead of a playtest.

**3. Detection-table coverage gate (tier A) — the one place our own replay tier lies.**
`vanilla_suppress_replay` proves the suppression *logic* but mocks `mapped_flags`, so it stays
green while `er_static_detection_table.json` is missing 147 locations. Add a data invariant:
every advancement/checkable location has a detection-table entry. A logic replay can never see a
data-coverage hole — this is exactly the A-vs-C distinction.

## Leave alone
`important_locations`, `missable_locations`, gf `weapon_shop_slots`, and the slot_data keyset
test all shipped with proper semantic or loud gates — no upgrade, don't churn them.

## Hygiene flags (memory drift)
- `patch_shop_weapon_slots.py` — **absent from disk**; the gf-side `features/weapon_shop_slots.py`
  (committed, with tests) superseded it. Memory `er-shop-weapon-slot-bugs` is stale.
- `patch_bundle_lock_graces_chain.py` — **absent from disk**; `er-numregions-cave-start-graces`
  is genuinely unwritten, not "FIX WRITTEN / pending" as memory states.

## The one-line takeaway
The replay work closed the timeline (C) class cleanly, and the loud keyset/contract gates cover
much of B. Every remaining green-while-broken bug is a **region/data-value (A)** gap — and the
single region-of correctness oracle is worth more than the rest of the backlog combined.
