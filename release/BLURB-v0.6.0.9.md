# v0.6.0.9 — faster maps

The map speedup is here: the bundle now runs MapForGoblins 2.1.3 with our AP filtering and hover adapter. The live test reported that the lag was gone.

## Can I update the client during a run?

**Yes.** Versions are V.R.M.F and this is still the 0.6.0 line: a v0.6.0.9 client plays every seed
rolled by any 0.6.0-line apworld, your run included, and the contract hash has not moved since
v0.6.0.3, so a v0.6.0.3 through v0.6.0.8 client also plays every v0.6.0.9 seed. Your save is not
at risk in either direction. Not about the contract, and all already true before this window: Elden
Ring 2.7.1.0 needs a v0.6.0.6 or newer client, Respec needs v0.6.0.7 or newer, and the trap-replay
and main-menu delivery fixes need v0.6.0.8 or newer.

## What you need to update

- **Client:** Required for the missing-pin fix — update the complete bundle, including `eldenring_archipelago.dll`. Compatible with existing runs.
- **APWorld:** Host-only — install v0.6.0.9 when generating a new room once it ships.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — a fixpack never strands a running seed.
- **Profile/assets:** Reinstall or replace the map files. Keep the two MapForGoblins DLLs and two INI files together in `me3/`.
  Manual swaps replace `MapForGoblins.dll` and `MapForGoblins.ini`, and add
  `MapForGoblins.upstream.dll` and `MapForGoblins.AP.ini`. No launcher or Flower change is needed.

## What is in it so far

**Castle Ensis knows where it ends (#1554).** A playtester walked the castle and said seven of
its checks were filed in the wrong region -- some standing in the Scadu Altus lowland past Rellana,
some standing inside the castle while filed out on the Gravesite plain. Measured one at a time
against the game's own play-region geometry rather than taken on the report: seven moved, six
stayed. If you play with region locks, that is seven fewer checks that could be created and then
fenced off. New rooms only; check IDs are unchanged, so nothing in a running seed shifts.
The older fork renderer has been replaced with the pinned upstream 2.1.3 renderer. Our adapter
preserves AP filtering and hover lookup. Filtering, client timeout fallback, repeated map
close/reopen and underground transitions were exercised in game.

F10 combines AP filter controls with upstream settings. Checks-only and in-logic-only remain
enabled by default. The two INI files still support manual configuration. The adapter also
corrects upstream's ImGui initialization path so native marker attachment hooks are installed.

The AP client fixes missing pins when a seed's location IDs differ from the baked map catalogue.
It joins map lots to the seed's acquisition flags before applying tracker reachability, so valid
checks are no longer discarded because their AP IDs shifted. Logic filtering remains enabled;
closed regions remain out of logic. Existing seeds need no regeneration.

## What carried over from v0.6.0.8

Nothing is owed. Both v0.6.0.8 release workflows succeeded on `f5257eb9`, the window opened at
that tag with no commits past it, every v0.6.0.8 entry sits under its own heading, and this time
the tag was delivered once, so the release page carries a single client bundle.
