# SPEC — Greenfield boss-lock tracker item

*Draft 2026-07-07. Make the boss-lock feature transparent (a visible, trackable AP item) or drop it.
Grounded in `greenfield/eldenring/features/boss_locks.py`, `boss_data.py`, `contract.py`.*

> **Impl status (2026-07-07):** mode A is **built**. apworld emission + contract + test =
> VERIFIED (provision + pytest). er-logic `boss_felled.rs` + countdown-kick = hand-verified drafts
> (cargo unavailable in sandbox). Remaining = Windows glue in `WIRING-boss-locks-v0.2.md`
> (`cargo test`/`build` + game-facing call sites + in-game confirm). Mode B = v0.3.

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

---

## Attunement-release design (2026-07-07) — SUPERSEDES the mode-A/B "approach-gate" phasing above

**Problem.** On region unlock the grace bundle lights all graces incl. the boss arena -> warp-and-kill
skips the region. Dark-set withholding was REJECTED (vanilla dungeons are short entrance-to-boss; it
just relocates the warp point). And "just cut boss locks" does NOT cut the problem: `curated_fill`
routes region Locks onto Boss/Remembrance/GreatRune checks, so bosses are often the progression spine
-> boss-rushing becomes the meta if unaddressed.

**Core reframe: don't gate the KILL, gate the RELEASE — on an IN-REGION predicate** (Mode B's flaw is
its predicate is a foreign key, uncorrelated with the region, so it time-shifts the reward but the
region is still never engaged).

**v0.2 design — three composed pieces, all on existing client primitives:**

1. **Random-start graces.** On lock receipt light `K` seeded-random graces instead of the fixed front
   door. `K = clamp(ceil(n_graces/8), 1, 3)` (Limgrave 3, Stormveil 2, Raya Lucaria 1). Draw from the
   region's graces minus `_BOSS_GATED_GRACE_FLAGS` (proven 37/37 by the EMEVD oracle) + the boss
   antechamber grace (~20 new curation flags, one per boss). Different entry door per seed; ZERO new
   client surface (the lock->light path just receives K flags instead of 1).

2. **Attunement = in-region CHECKS collected** (NOT graces reached — that's the move that kills the
   "short dungeon" objection: checks-collected forces looting and is route-agnostic). Boss payout
   releases when `boss_flag && attuned(region)`, `attuned = |collected ∩ region_ap_ids| >= threshold`.
   Count from the SERVER checked-locations set (authoritative -> survives save-load / reconnect /
   re-snapshot, the exact bug class we keep hitting). `threshold = clamp(0.10 * freely_reachable
   region checks, 5, 20)` computed at gen (exclude boss-gated + missable, per the important_loc
   juice-guard lesson). Dungeon-sweep bursts from OTHER dungeons count toward attunement (side content
   = fuel).

3. **Attunement bloom.** Hitting the threshold lights the region's REMAINING graces (incl. the boss
   antechamber) + banner "Attuned to <Region> — all graces revealed." Reframes the mechanic as a
   REWARD (loot N -> get the region's full warp network + banked boss payout). Kill-before-attuned
   banners the debt: "Godrick felled — 14 checks sealed (attune: 7/12 Stormveil)."

**Boss payout scope.** The payout = the boss's own checks (loc + remembrance/great-rune) AND its
dungeon-sweep members, all gated by attunement TOGETHER. Gating only the 2-3 boss checks while the
sweep fires ungated would leak the whole dungeon -> the entire boss-kill burst must be attunement-gated.

**OPEN QUESTION (playtest) — important_locations in the payout.** Because the payout is the whole
dungeon sweep, important_locations checks in that dungeon ARE delivered by the boss kill once attuned
— you don't have to manually find them. Assessment: probably FINE — important_locations only
guarantees those checks HOLD good items (you still receive them; delivered == obtained),
`dungeon_sweep` is opt-in, and attunement already forced N checks of engagement. DEFAULT: ship as laid
out (important included). LEVER if it feels too skippy: exclude important_locations from the sweep
(they stay manual pickups), or require K important checks inside the attunement count. Decide by
playtest.

**Why it's sound + cheap.** Winnable by construction — attunement is always satisfiable with just the
region Lock (in-region checks need nothing else); NO placed item, NO fill feasibility guard, the boss
location's rule stays `has("<Region> Lock")`. Fill-safe / count-neutral (fold the grace scatter pool
items into the bloom). Pure-runtime on existing primitives (grace lighting + P3b flag-watch + deferred
send/burst-release). One new contract key: `regionAttunement = {region: {threshold, member_ap_ids,
bloom_flags}}`. One replay test: attunement count + banked-boss release survive reconnect.

**Composition — this IS Mode B's deferred-release machinery, shipped a version early.** v0.3 Mode B
(`Boss Key`) becomes an OPTIONAL STRICTER layer: `release = boss_flag && attuned && has(Boss Key)`,
same deferral path. Re-evaluate then whether the key still earns a pool slot — attunement already
delivers the engagement gate, so the key's residual value is multiworld texture, not pacing.

**v0.2 MVP slice** (if time compresses): attunement-release alone with the fixed front door — even
that answers warp-and-kill better than cutting boss locks does. Random-start graces + bloom are the
polish layer on top.
