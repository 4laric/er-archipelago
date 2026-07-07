# SPEC — Greenfield boss-lock tracker item

*Draft 2026-07-07. Make the boss-lock feature transparent (a visible, trackable AP item) or drop it.
Grounded in `greenfield/eldenring_gf/features/boss_locks.py`, `boss_data.py`, `contract.py`.*

## Problem — the feature is half-built and invisible

Today the boss-lock surface emits three things but produces **no player-visible item**:

- `bossLocations` = `{region: [boss AP location ids]}` — the boss *checks*, for a boss-based goal /
  region-boss tracker feed. This is a location list, not something the player holds or tracks.
- `dungeonSweepFlags` = `{boss_flag: [member ap ids]}` — kill a dungeon boss, client grants that
  dungeon's other checks. A convenience, not a lock.
- `sweepLockGates` = `{sweep trigger flag: '<Region> Lock'}` — *intended* to gate a sweep behind a
  lock. **Emitted empty (`{}`) today.**

The `BossLockPlacement` option ("where boss-lock items are hosted once sweeps land",
own_region/scatter/any_boss) describes items that **are never created** — nothing enters the pool,
so the option is a no-op and the mechanic can't be seen in the AP tracker, the in-client tracker, or
logic. Same legibility trap as the region-lock sentinels (TODO 0b: a synthetic id-99999 item has no
FMG name, so the in-game banner can't name it). Net: a player can't tell boss locks exist. Either
give them a first-class, named, trackable item, or remove the dangling option + empty keys.

## Goal

One synthetic AP **item per gated boss / dungeon sweep**, named and classified so it shows up in the
AP item list and both trackers, and (optionally) acts as the real gate the `BossLockPlacement`
option already promises. Provenance stays matt-free — every boss is already joined to a greenfield
ap-id by vanilla event flag in `boss_data.py` (`REGION_BOSSES[region] = [(ap_id, boss_flag, reward_name)]`).

## Design — the "Boss Lock" item family

Mirror the region-lock pattern in `core.py`:

```
_core_item_ids   = {f"{r} Lock": _ITEM_BASE + i ...}          # existing region locks (progression)
_boss_lock_ids   = {boss_lock_name(b): _BOSS_LOCK_BASE + j}   # NEW, reserved band e.g. 7772000+
```

- **Name** — mode-specific and self-explaining (resolved 2026-07-07): the on-kill trophy is
  `"Felled: <Boss>"` (it's a trophy, not a lock) and the placed gate is `"Boss Key: <Boss>"` (every AP
  player already knows what a Boss Key does — no explanation needed). Avoid `"Seal: <Boss>"`: it's
  ambiguous about whether receiving it seals or unseals. Generate the `<Boss>` label from
  `REGION_BOSSES` (derive it from the reward string or a small boss-name table keyed on `boss_flag`).
- **One item per boss** the seed actually gates (kept regions only, mirroring `_kept()`), so counts
  stay seed-correct and sealed regions never mint an orphan lock.
- **Legibility without an FMG bake** — greenfield is pure-runtime, so the *client* can render the
  notification string from slot_data (the name travels in the contract). This sidesteps TODO 0b
  entirely: no regulation/FMG edit, the client shows "Received: Seal — Dancing Lion". This is the
  clean advantage greenfield has over the matt-lineage world.

### Two modes (compose; A ships v0.2, B ships v0.3)

**A. `Felled: <Boss>` — on-kill trophy (v0.2; pure transparency, zero risk).**
Granted on boss defeat: the client watches `boss_flag` and, on kill, sends/grants the matching
`Felled: <Boss>` item. Classification `useful` (non-logic). The AP tracker + in-client tracker light
up per boss killed — the player sees exactly which bosses are done. No logic/fill impact, nothing can
soft-lock. Reuses the existing `dungeonSweepFlags` P3b flag-watch — the same watch that grants sweep
members also self-sends the trophy. It's a trophy, not a lock, hence the name.

**B. `Boss Key: <Boss>` — deferred-release gate (v0.3; gate the checks, NOT the fight).**
The clever realisation of `BossLockPlacement`. Never block the fight. Instead the boss's AP
location(s) + its dungeon sweep only **send** when `boss_flag && has("Boss Key: <Boss>")`. Kill the
boss without the key and the client banners "Godrick felled — 12 checks sealed, awaiting Boss Key:
Godrick"; when the key arrives it **burst-releases** the stored checks. Why this beats a hard boss
gate:
- **Cannot soft-lock** — the fight is always available; only rewards defer. No impossible-fight trap.
- **Logically sound** — a plain `state.has` rule; fill places the key reachably; winnable by
  construction.
- **Self-communicating** — the pending-check COUNT ("12 checks sealed") turns an invisible mechanic
  into a visible debt being paid down.
- **Reuses what exists** — the `boss_flag` watch (P3b), the vanilla-suppress / collected-set path,
  client-side banners from slot_data. No new detection surface, no memory-write jank.
`Boss Key: <Boss>` is a `progression` item placed per `BossLockPlacement` (own_region / scatter /
any_boss); costs are the usual fill feasibility check (don't gate more keys than early-reachable slots
can host — cf. TODO §A) + a winnability test per placement mode.

A and B compose: a boss with no placed key still emits its `Felled:` trophy (A); a gated boss holds
both its `Boss Key:` (B) and, on kill, its `Felled:` trophy.

**Rejected as the core mechanism (trap-drawer only).** *Hard* boss gates that block the fight — the
"unkillable seal" (client pins boss HP at full → players burn 25 min + all flasks on an impossible
fight; one missed write-frame and the defeat flag fires anyway) and the arena kick-watch (jarring
mid-fog teleport, needs a per-boss engage-flag/bbox enrichment pass, risks weird boss/music state).
Both are more surface than deferred-release for less soundness. Keep them for trap items, not the
boss-lock system.

## Contract change

Add one key (declare in `contract.py` so `validate_slot_data` accepts it — recall it rejects any
undeclared emitted key):

```
bossLockItems = { str(ap_item_id): {"name": str, "boss_flag": i64, "region": str,
                                    "members": [ap_id, ...] } }
```

- Producer: `features/boss_locks.py::slot_data` (kept-region scoped, like `bossLocations`).
- Consumer: `region.rs` / the P3b flag-watch handler — on `boss_flag`, self-send the `Felled:` trophy
  (mode A); for mode B, DEFER the send of the boss checks + sweep `members` until
  `has("Boss Key: <Boss>")`, then burst-release (banner the pending count while sealed).
- `sweepLockGates` stops being empty in mode B (`{sweep_flag: "Boss Key: <Boss>"}` — the predicate the
  deferred release checks); in mode A it stays retired.

## Tracker integration

Both trackers already consume `bossLocations`. Add a **Bosses** group keyed off `bossLockItems`, with
three states: **locked** → **felled** (mode-A `Felled:` trophy received) → **released** (mode-B
`Boss Key:` applied, stored checks burst out). The in-client tracker (region-grouped, F6) gets a
per-region boss line; the PopTracker pack gets a Bosses section.

Pair it with **banners at the moment of relevance**, not just on item receipt: on boss defeat while
sealed → "Godrick felled — 12 checks sealed (Boss Key: Godrick)"; on key receipt → "Unsealed:
Godrick — 12 stored checks released." The live pending-check count is the single biggest legibility
win — it makes the debt, and paying it down, visible.

## Gen / tests

- `test_gf_boss_lock_items.py` — item ids unique + in the reserved band, one-per-kept-boss, names
  legible + collision-free, classification correct; `bossLockItems` shape validates against
  `contract.py`; pool-count neutrality (mode A adds tokens via client grant, not pool fill; mode B is
  count-neutral against filler like the region locks).
- Mode B additionally: WorldTestBase winnability per `BossLockPlacement` value + a feasibility guard
  (forced boss-lock demand ≤ early-reachable slots).
- Client: a replay/semantic-tier test for grant-on-`boss_flag` (mirror the existing `*_replay.rs`
  guards; boss-kill token grant must be once-only / survive save-load + reconnect).

## Region-gate polish — the countdown kick (independent, ship-anytime)

Not boss-specific, but the same "make the gate communicate itself" idea applied to the REGION
kick-watch (`area_locks.py` / `region.rs`). Today an out-of-sphere player is teleported out with no
explanation — the jarring part isn't the kick, it's the *unexplained* kick. Keep the hard gate
(it's the sound one for region pacing) but announce it: on detecting the player in a sealed region,
banner "The seal of Caelid repels you… 10s" **naming the missing `<Region> Lock`**, then kick to the
nearest open grace. Same soundness, ~zero new surface, far less jarring. Cheap enough to ship
independent of the boss work.

Explicitly NOT recommended for v0.2: a "cold region" soft mode (roam freely, checks bank until the
lock arrives). It feels good but silently guts `num_regions` as a *pacing* mechanic (full-clear day
one, then it's a mail-sorting sim) and doubles the mode surface — against the one-sound-mode policy.
Park it as a future `region_gate_style: soft` only if playtests demand it. Scaling-as-gate (sealed
regions run brutal until unlocked) is the most Fromsoft-flavoured but it's a balance project, not a
lock — backlog next to the completion-scaling wire.

## The "drop it" alternative (cheaper; consistent with the one-sound-mode policy)

If we don't want to invest before v0.2: **remove the dangling surface** instead of shipping a no-op
option. Delete `BossLockPlacement`, stop emitting `sweepLockGates` and the empty `dungeonSweeps`, and
keep only `bossLocations` (+ `dungeonSweepFlags` if the sweep-on-kill convenience stays). That leaves
one honest, working behaviour and no option that pretends to do something. Per project policy
(delete unsound/half modes rather than defend them), this is the safe v0.2 move if mode A can't land
and be in-game-confirmed in time.

## Recommendation & phasing

1. **v0.2:** ship **mode A** — `Felled: <Boss>` on-kill trophies. Small, no fill risk, delivers the
   transparency asked for. If it can't be in-game-confirmed in time, take the **drop** path so v0.2
   ships no dead option. Optionally land the **countdown-kick** region polish alongside (independent,
   cheap).
2. **v0.3:** add **mode B** — `Boss Key: <Boss>` **deferred-release** gate (gate the checks, not the
   fight), behind the fill-feasibility guard + winnability tests per `BossLockPlacement`. Never build
   the HP-pin or arena-kick hard gates as the core mechanism.

## Decisions locked (2026-07-07)
- Naming: `Felled: <Boss>` (mode A trophy) + `Boss Key: <Boss>` (mode B gate).
- `<Boss>` label: derive from the `REGION_BOSSES` reward string (no separate boss-name table).
- Scope: **base-game bosses only for v0.2** — DLC bosses (incl. the Land of Shadow set) are OUT of
  v0.2; revisit for a later release. Filter `REGION_BOSSES` to base regions when minting `Felled:`
  items.
