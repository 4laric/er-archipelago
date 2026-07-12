# Known Issues -- v0.2

Everything we currently know about, what it looks like in play, and what (if
anything) to do about it. The short version: nothing on this list can strand a
run on the base game, which is the recommended, supported configuration.

## Active issues

- **A few checks can pay out the vanilla item instead of the Archipelago
  one.** A small class of drops that arrive through the ordinary enemy-drop
  channel can hand you the item the vanilla game would have given, rather than
  the multiworld item. This is contained: those locations are never allowed to
  hold progression items, so it cannot strand a run -- the worst case is that
  you miss a filler item. What to do: nothing; keep playing. A fix is in
  progress for a future release.

- **DLC: the Shadow Keep church-basement grace can warp you in before the
  water is drained.** With the DLC enabled, the region grace bundle can light
  the church-basement grace (Church District Lower / Scadutree Base) before
  the keep is drained, and fast-travelling there can drop you onto lethal
  moving platforms. What to do: avoid warping to that grace until you have
  drained Shadow Keep. The fix (gating the grace on the drain state) is
  pending.

## Wired but pending in-game confirmation

These fixes are in the code but have not yet been confirmed across a full
save-load / reconnect cycle in-game. Each guards against a data-loss
regression. What to do: nothing special -- but if you see either symptom
below, please report it, since that is exactly the confirmation we need.

- **Region front-door grace latch.** Previously, a region's graces could be
  lost when the region-open bloom latched on the front-door open flag. The fix
  is wired (`region_bloom_settled`); we are waiting to confirm that graces
  survive a save-load.

- **Flag-poll new-save baseline.** Previously, reconnecting could re-snapshot
  the flags and eat checks you had already earned (the "picked up a Sacred
  Tear and got nothing" symptom). A once-per-save baseline is now persisted;
  we are waiting to confirm that reconnecting keeps earned checks.

## By-design non-features

These are deliberate v0.2 decisions, not bugs -- listed here so you can tell
them apart from the real thing. No report needed for anything below. (And if
something is *not* on this list and looks wrong, we absolutely want to hear
about it.)

- **Merchant-bell logic** (`merchant_bell_logic`) **is inert in v0.2.**
  The bell-to-shop mapping lives in engine code, not in any param or EMEVD, so
  it cannot be derived from game data. The option is registered so configs stay
  forward-compatible, but no value you set does anything yet. What to do: leave
  it off; you lose nothing.

- **Location-keyed sweeps and sweep-lock gates are empty on purpose.** Only
  flag-keyed dungeon sweeps fire (kill the boss and the dungeon's other checks
  register). Boss-lock sweep-gates are inert for now. What to do: nothing;
  dungeon sweeps themselves work normally.


- **About 1% of checks give a Rune instead of a real item.** A small set of
  checks (item names not present in the game's text tables -- quest notes, a
  source typo, non-item text) fall back to a Rune in the item shuffle. What
  to do: nothing; this is expected.

- **Great Runes are "useful," not progression** -- unless
  `ending_condition: great_runes` requires them, in which case they become
  progression and are placed reachably. What to do: if you want Great Runes to
  matter, set `ending_condition: great_runes`.

## DLC

DLC (Shadow of the Erdtree) is **experimental** in v0.2. `enable_dlc` makes
DLC regions eligible for `num_regions`; `dlc_only` runs only the
Land-of-Shadow regions. What to do: for a smooth run, play the base game (DLC
off) -- that is the recommended, supported configuration. DLC seeds work but
expect rough edges (see the church-basement grace above).

## Fixed since the v0.2 draft (playtested 2026-07-12)

These were on the active list and are now confirmed resolved -- kept here only
so nobody chases them. What to do: nothing; enjoy.

- **Spirit Calling Bell unusable** -- fixed; Spirit Ashes are callable from
  the received item.
- **Map-piece items granted on connect** -- fixed; the reveal fires without
  minting item grants.
- **Flask double-grant on tutorial-death reload** -- fixed.
- **Torrent unavailable on a rolled start** -- fixed; a rolled start can no
  longer leave you mountless.
