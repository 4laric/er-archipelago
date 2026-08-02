# Quiz question ledger

Append-only. Newest round at the top. The weekly task reads this to avoid repeating a question
verbatim and to weight in facts never yet quizzed.

> 🛑 **THIS FILE AND `er-project-quiz.html` ARE UNTRACKED AND WERE SWEPT ONCE ALREADY**
> (between 2026-07-31 and 2026-08-02, most likely by a `git clean` during the v0.3.0 release work).
> The HTML is cheap to regenerate; **this ledger is not** — losing it means the weekly task starts
> repeating questions. Commit both, or move them under a tracked path.

---

## 2026-08-02 — round 2 (+16, total 76) — the 2026-08-01 PR pass

Sources: world PRs #253, #254, #261, #263, #264, #270, #271, #277, #279, #280 ·
client PRs #14, #15, #16, #17, #18, #19, #20, #21, #22.

### client
- crash handler: an `int3` on ER's Alt-F4 teardown was banner-ed as a CTD; `code_name` didn't know `0x80000003` either
- reclassify (Fatal/Breakpoint/Benign), do not silence — early return trades a false positive for a false negative
- `shared` was BUILT by CI and never TESTED; the 7 `foreign_blocks.rs` tests ran nowhere
- #248: `grant_full_id` returns true for a grant capped to zero — correct for the LEDGER, catastrophic for a VERIFIER
- the property: never report delivered unless a SUBSEQUENT snapshot contains it; `GrantOutcome {Placed, Capped, NotReady}`
- `record()` is per COPY but `MAX_ATTEMPTS` bounds TICKS — 10 Cracked Pots burned the budget in one tick
- survived only because all forty were NotReady (burns nothing); Capped would have declared failure 3 rounds early
- `owns_*` were pure config reads — config says who SHOULD deliver, not whether the owner exists
- owns := configured && !dry_run && armed && !refused; `armed()` = `DRIVER.get().is_some()`
- FLAGS tier: `SETTLE_MS` distrusts the INVENTORY POINTER, and flags never touch it — `flags_ready() = in_game && player_valid`
- auto_equip: the "further RE target" was already a struct field — `EquipInventoryDataListEntry.gaitem_handle`
- an equip is FOUR coupled reps; writing the handle directly never ACQUIRES a reference (cost a Lordsworn's Greatsword)
- rep 4 is the inventory index in `unk8: [u32; 22]` — omit it and every equipment-menu slot renders EMPTY
- death guard "ONE RULE, FOUR SITES" was FIVE; a miscount in a comment is folklore with syntax highlighting
- DeathLink deliberately NOT unified — two `hp <= 0` tests are different rules wearing the same expression
- possession beats a re-keyed boolean: it cannot go stale, cannot be inherited, survives a reload free

### world / options
- `want = min(want, len(_available_runes()))` — lowering a requirement is NOT always safe
- the capital gate is a fixed two-rune wall that does not clamp with us; `leyndell_runes_required: 1` is selectable
- floor an armed wall at `VANILLA_CAPITAL_GATE_RUNES`; DISARM rather than arm low
- the Leyndell gate is a flag COUNT: `CountEventFlags(EventFlag, 190, 199) >= countThreshold`, ITEM-ARG 0/6
- 191-196 are both restored-goods ids and restored-flag ids — FromSoft parallel numbering, not our error
- a gated child's open flag must not BE a grace; new bits Leyndell 76980 / Raya Lucaria 76981 / Sewer 76982
- core.py and area_locks.py change ZERO lines — fix the table, not four consumers
- 🛑 DO NOT TAG UNPROBED: an unallocated flag no-ops in the STRANDING direction
- Isolated Merchant: bar all SIXTEEN, the gate is on the MERCHANT; identity = name + tile m60_35_45
- two sellers reads as an all-clear and is not — the Husks need the bell bearing, behind the same door
- `SCADU_BLESSING_CAP` bounded an injection that was never built; 1 seed in 40 could reach the cap
- the trigger is a COUNT, not a boolean: `inject = max(0, SCADU_CUM[cap] - natural)`

### process / CI
- rule 13: a spec's acceptance list is a to-do list until something checks it (5 of 10 missing/partial)
- the half of each bullet needing a NEW test tier is the half that did not land — build those FIRST
- every plain startItems entry must be DURABLE; direct-call test because invariants only see passing items
- `Generate.py` ends with `input()`, so a CRASH reports as a HANG; `AP_NONINTERACTIVE` is a local patch that rots
- derive the invoker set — the hand list was 12 audited to 5 and goes stale on the sixth
- the detector lied twice; `_invokers()` returns flags, not 144,000 characters of file text

---

## 2026-07-31 — round 1 (60 q, seeded from MEMORY.md + docs/history)

### geo
- StartDisabled=1 means chest, not gate (162/163 InChest>=1)
- exactly one real cross-region prereq: f580600 Leda <- Messmer
- region_groups.py two tables, two id spaces (ID//100 vs bonfireSubCategoryId)
- warp-subcat x10 does not generalize; kick_decision permissive on unknown bucket
- anchored tiles straddle MORE than graceless (9% vs 5%)
- overworld map id 4th field = [version][lod]; (pitch-256)/2 centring term
- only 9 live checks have an MSB treasure record and no coordinate
- check coords are one-to-many; 1665/4857 gap; merchants multi-spatial
- grace place-name dump keyed by warp/event flag, not map id

### shop
- menu drops a row when value < the ware's own sellValue (relation, not ==0)
- Veteran's Helm proves it is not a rune bug
- shipped fix LOWERS sellValue; synthetic goods refused above 3_780_000
- absence follows the ITEM not the ROW (seed-2 row flips)
- `_RUNE_RE` name whitelist misses 11 DLC money-runes; PR #227 unmerged
- test_gf_rune_shop_price_sanity green by construction (continue on not is_rune_item)
- Twin Maiden Husks / merchant block over-attribution; release-gate fix changed 0 of 548

### client
- FMG CTD faults at X-8 where X is 64KB-aligned, 14/14
- GUARD_BELOW = 0x1000, a full page, not 8 bytes
- try_set_event_flag returns true on singleton resolve, discarding set_flag
- a contested flag is never parked; only a non-sticking write parks
- grant stall precondition is a Great Rune + next world edge; Roundtable falsified
- MAX_GRANT_ATTEMPTS=3 with same-tick read-back; RECONCILE_APPLY=none unblocks
- seed-change path bypassed the marker guard; 229 checks crossed seeds
- em-dash toast drew as `?`; every_toast_is_ascii sweeps the range
- 0.2.17 names two builds; CLIENT_BUILD SHA on the overlay
- whetblade check moved to client-owned adjacent flags 65611+

### opts
- Goal values auto/elden_beast/promised_consort; named goal outranks the ladder
- goalRequiredItems STR_LIST; CONTRACT_HASH d970dd88 -> 00a04676
- 25% of rolled seeds open the goal region second, at both N=6 and N=10
- lock-hint price derives from the host's hint_cost; Unknown, never free
- AP hint cost is structural: 487 pts at 10% over 4879 locations
- data storage append needs Appends(Vec<Value>), not Add(f64)
- shop-open hook exists: cs_ez_state_talk_event_vmt; OPEN_REGULAR_SHOP = 22
- Scadutree cap 12; hash -> 5e8b11c9; row 20012081; SoloParam index 141
- effectEndurance 0.05 is a refresh, not a strip; clone with -1
- boss runes are GameAreaParam.bonusSoul_*, keyed by ARENA
- option renamed to minimum_enemy_difficulty; wire key still completion_scaling_floor
- region_grace_unlock tiers 338/47/27; derive from the lowest 76xxx flag
- num_regions ruling: change the tests, not the defaults

### ci
- assert_coverage called from core.post_fill and RAISES; baseline stays {}
- print in a passing pytest is void; use warnings.warn
- sphere gate runs num_regions 12, MIN_SPHERES 4, MAX_SPHERE0_SHARE 0.50
- contract.py is the single source; 3 mirrors; Python fails, Rust warns
- the 4 cross-side client tests SKIP in CI (no submodules); 10 orphans locally
- can_sell mirror stayed green when _GEM_NIBBLE was removed (found by mutation)
- a fix is a predicate, and production must call it (region_bloom_settled)

### tools
- gen_inputs globs to 239 CSVs; hand-lists kept as a REQUIRED FLOOR
- ItemLotParam category membership 1 Goods / 2 Weapon / 3 Protector / ...
- check browser gate evidence: union 684 across four corpora
- NO_ENTITY_HANDLE is proof of no gating, not unknown
- place-name descriptor idea killed: 80/982 have coords, 17 within 300 m
- ESD verb is AcquireGesture, not AwardGesture (third corpus)
- provenance: reading to cross-check fine, ingesting not; PROVENANCE-OK marker

### proc
- version lives at 4 sites + the client's tracked Cargo.lock; 0.2.12.1 does not parse
- develop into main, cut on demand; the bump belongs to the CUT
- CONTRIBUTING rule 11: the motivating case is the acceptance test
- Godrick's Great Rune and Remembrance are SIBLINGS (tags are on drops)
- the remembrance/great-rune name filter is OURS, not the game's
- "item X is in the pool" is never a seed-independent claim
- the recurring pattern: a green result upstream of the surface is not evidence

---

## Not yet quizzed — candidate pool for future rounds

**From the 08-01 pass, not used:**
- PR #282 boss region routing — a vote TIE and `or HUB`; SWEEP_REGION is not a boss roster
- the v0.3.0 release: CLIENT repo has NO `v0.3.0` tag at the pinned gitlink
- CI checks the client out from MAIN, bypassing the gitlink — `git ls-tree HEAD | grep 160000`
- main RED at `1e9dd643` on one step, `Wizard metadata drift`; every PR inherits it
- I3 reattach: `owns_*` needs an ARMED driver, then a character NONCE
- the marker `identity_hash` is (seed, slot) with NO character component
- #244 grace-skip oracle still RED; flag 76412 grantable behind boss fog
- the Leyndell fogwall is the ONLY hard vanilla boundary — never extend `GAME_NATIVE_GATE`
- `er_logic` test count went 544 -> 559 -> 572 across the day

**Older, still unused:**
- the 91 no-handle gate pairs; absence from _QUESTLINE_GATED is not safety
- d4fc247 has never been swept; 445 checks left the progression surface
- #217/#218 Roderika and the 621 unplaced rows; check_maps.tsv knows 430
- the outputs mount as the workspace; /dev/shm wiped between bash calls
- api.github.com reachable; PAT cannot workflow_dispatch; side-branch push runs NO CI
- gf_test.py is the harness; hand-installing the world gives 10 fake failures
- questline DAG tier 1: 283 edges; esd_flags SETS rather than tests
- boss-healthbar sweep: 249 bosses vs 216 arenas
- foreign progression is already confined; the residual is our own spilled Locks
- shop preview was inert for 5 days; it protects the shared FMG
- don't FILTER a gate's output — run it verbatim; failing AT clippy proves build+test passed
- a BANNER is not an exception code: `0x8…` = TRAP, `0xC…` = fault
