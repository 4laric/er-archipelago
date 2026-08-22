# v0.4.12 — release blurb

**The shelf un-padlocks.** Buying an Archipelago shop slot hands you a "receipt" item — and it
turned out most of those receipts are hold-cap-1 goods you can neither drop, discard, nor sell,
so after one purchase Elden Ring itself refused every other slot sharing that item's row: "the
number you wish to buy would exceed the maximum able to be held." With v0.4.11's name-sharing
reusing rows across shops, one buy could quietly lock checks at every merchant. The client now
raises the caps on every receipt row it owns, which fixes **every seed ever generated — including
the room you're in right now** — the moment you update. Confirmed in-game by the player who
reported it.

**Quitting the game stops gambling with a crash report.** Quit to menu, quit game — the most
correct exit there is — could abort the process if one of our callbacks read game data mid-
teardown. Every such read now degrades to a log line.

**And the housekeeping from the window:** the release bundle now actually contains the updater
and the matt's-rando installer its notes promise beside the dll; the installer creates the
launcher's dll config on a fresh install instead of citing a dialog that never writes it; an
experimental ability-lock test harness ships off-by-default for wear-testing (#945); and
diagnostics date their own signature mismatches.

## What you need to update

- **Client:** Required — this is the one to update. The contract is unchanged (`dc0dc687`), so
  it is a drop-in even mid-seed; the bundled `update-er-archipelago.ps1` does it in one command.
- **APWorld:** Host-only — and hosts do not need to act for this release: v0.4.11 rooms keep
  working with v0.4.12 clients (the version banner will note the mismatch; that is it doing its
  job). Roll new seeds on v0.4.12 when convenient.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — no save migration; keep a mid-flight seed's apworld as is
  and just update the client.
- **Profile/assets:** No action.
