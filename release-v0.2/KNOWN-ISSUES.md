# Known Issues — v0.2

Carried-forward and current issues. None block a solo Shattering run on the base
game (the recommended, supported configuration).

## Active issues

- **Spirit Calling Bell may be unusable in-game.** Summoning can stay gated even
  with the item, so Spirit Ashes may not be callable. Does not block a solo
  Shattering run; targeted for a point release.

- **Map-piece items on connect.** You may receive a few map-fragment items the
  instant you connect. Harmless — effectively a small handful of free early
  reveals. (Under the map-reveal path the fragments' pillar checks no longer leak
  as multiworld checks; the reveal simply fires at spawn.)

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
