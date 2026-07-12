# Known Issues — v0.2

Carried-forward and current issues. None block a solo Shattering run on the base
game (the recommended, supported configuration).

## Active issues

- **A few checks may still hand you the vanilla item.** A small class of drops that come
  through the ordinary enemy-drop channel can pay out their vanilla item instead of the
  Archipelago one. It is **contained**: it cannot strand a run, because these locations are
  never allowed to hold progression. You may simply miss a filler item. A fix is in and
  awaiting playtest confirmation.

- **DLC Shadow Keep church-basement grace warps in pre-drain.** With the DLC
  enabled, the region grace bundle can light the Shadow Keep church-basement grace
  (Church District Lower / Scadutree Base) *before the water is drained*, so
  fast-travelling there can drop you onto lethal moving platforms. Avoid warping to
  that grace until you've drained the keep. Fix (flag-gate the grace on the drain
  state) is pending.

## Wired but pending in-game confirmation

These fixes are in the code but not yet confirmed across a save-load / reconnect
in-game. Each guards against a data-loss regression:

- **Region front-door grace latch.** Region graces could be lost when the
  region-open bloom latched on the front-door open flag. Fix is wired
  (`region_bloom_settled`); pending confirmation that graces survive a save-load.

- **Flag-poll new-save baseline.** On reconnect, a re-snapshot could eat already
  earned checks (the "Sacred Tear got nothing" symptom). A once-per-save baseline
  is now persisted; pending confirmation that reconnect keeps earned checks.

## By-design non-features (do not report)

- **Merchant-bell logic** (`merchant_bell_logic: logic_only`) is a **no-op**. The
  bell→shop mapping lives in engine code, not in any param/EMEVD, so it isn't
  derivable. The option ships inert; leave it off.

- **Location-keyed sweeps / sweep-lock gates are empty by design.** Only
  flag-keyed dungeon sweeps fire (kill the boss → the dungeon's other checks
  register). `boss_lock_placement` sweep-gates are inert for now.

- **Boss Keys (`boss_keys`) are off and hidden for v0.2.** The option is fully
  inert when off (no keys minted, no gates, no slot_data), so it ships hidden from
  the template to avoid confusion. (The deferred-release boss-key mode works and its
  fill-cycle safety net is in place, but it's held until it has its own non-boss
  premium check surfaces — otherwise every region Lock just lands on a boss check.)

- **~1% of checks give a Rune instead of a real item.** A small set of checks
  (item names not present in the game's text tables — quest notes, a source typo,
  non-item text) fall back to a Rune under `item_shuffle`. Expected.

- **Great Runes are "useful," not progression** — unless
  `ending_condition: great_runes` requires them, in which case they become
  progression and are placed reachably.

## DLC

DLC (Shadow of the Erdtree) is **experimental** in v0.2. `enable_dlc` makes DLC
regions eligible for `num_regions`; `dlc_only` runs only the Land-of-Shadow
regions. Base game (DLC off) is the recommended, supported way to play — expect
rough edges on DLC seeds (see the church-basement grace above).

## Fixed since the v0.2 draft (playtested 2026-07-12)

These were on the active list and are **resolved** — reported here only so nobody chases them:

- **Spirit Calling Bell unusable** — fixed; Spirit Ashes are callable from the received item.
- **Map-piece items granted on connect** — fixed; the reveal fires without minting item grants.
- **Flask double-grant on tutorial-death reload** — fixed.
- **Torrent unavailable on a rolled start** — fixed; a rolled start can no longer leave you mountless.
