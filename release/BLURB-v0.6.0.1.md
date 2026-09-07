# v0.6.0.1 — release blurb (draft)

## Can I update the client during a run?

Yes. Versions are now V.R.M.F, and a client on the same V.R.M plays every seed that line
generated: put the v0.6.0.1 client on a room rolled with the v0.6.0 apworld and keep going. A
v0.6.0 client also plays a v0.6.0.1 seed. The seed contract did not change. Everything that
changes how a seed is generated applies to new seeds only; existing rooms keep their checks and
their scaling.

## What you need to update

- **Client:** Optional — a v0.6.0.1 client can replace a v0.6.0 client on a running seed and
  carries the key-item and delivery fixes; a v0.6.0 client still plays v0.6.0.1 seeds.
- **APWorld:** Host-only — install v0.6.0.1 when generating a new room to get the scaling, fill
  and recovered-check changes.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — new checks and the new scaling apply to newly generated
  seeds only.
- **Profile/assets:** Reinstall or replace — use the MapForGoblins build and preset shipped with
  this release; the progression-rings default lives in that preset.

## Enemy scaling on auto

`maximum_enemy_difficulty: auto` now keeps every base-game region at the base game's own top,
about 3.7x enemy HP (vanilla Haligtree), unless the Scadutree Blessing applies everywhere and the
DLC is on so its fragments can enter the pool. DLC regions may still climb the DLC rungs. The
climb itself was recalibrated for shorter runs: about 3.7x at 5 regions, 5.5x at 10, 6.7x at 15,
the full 7.4x on the whole map. The yaml builder shows what any setting resolves to as you move
the slider, and warns when an explicit cap would put DLC-strength enemies in regions with no
blessing to answer them. Explicit percents are untouched and apply to every region.

## Early upgrades

The early Somber stone guarantee could be quietly spent by two pre-fill reservations before
Archipelago placed early items, leaving a 1-region seed with no Somber [2] reachable from the
start. The reserved copies now stay in the pool for that pass.

## Recovered pickups

Four Oathseeker Knight armor pieces and Royal Magic Grease return as checks, backed by Map for
Goblins placement evidence. Briars of Sin is recovered from its actual enemy drop. Seven Somber
stone rewards are restored: six one-time scarabs and the Gravesite Ghostflame Dragon's stone
alongside its Dragon Heart. Silver Scarab is restored in the Hidden Path to the Haligtree.
Eleonora's Poleblade now checks the real invasion reward. Bernahl's Farum Azula Gelmir's Fury
reward and Diallos's Numen's Rune at Jarburg are tracked as separate checks. Existing check IDs
are preserved; new seeds are required to see any of these. Further NPC, enemy-drop and
access-rule investigations remain open under #1437.

## Great Rune inventory detection

The client no longer re-grants Great Runes or other key items that were already held but missed
by the inventory scan after an NPC hand-in. Rune delivery itself is unchanged: the separate
unequippable-rune issue remains tracked in client #316. See KNOWN-ISSUES.md before attempting
rescue commands.
