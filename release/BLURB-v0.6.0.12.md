# v0.6.0.12 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes.** `CONTRACT_HASH` is unmoved at `2aa64f43` since v0.6.0.11, so the v0.6.0.12 client and the v0.6.0.11 client are interchangeable on each other's seeds, and the v0.6.0.12 client reads every 0.5.x and 0.6.0.x seed through the audited legacy-contract bridge. Swapping the `.dll` mid-run on any of those puts nothing at risk and needs no reroll. The standing version gates still apply and none are new here: Elden Ring 2.7.1.0 needs a v0.6.0.6 client or newer, Respec needs v0.6.0.7, the trap-replay and main-menu delivery fixes need v0.6.0.8, and a seed rolled on v0.6.0.11 or newer needs a v0.6.0.11-or-newer client.

## What you need to update

- **Client:** Update for the Margit region-lock fix, including existing runs. The contract is unchanged; no seed reroll is needed. Existing minimum-version requirements still apply.
- **APWorld:** Host-only, for newly generated rooms after this version ships.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible; no regeneration or save migration required.
- **Profile/assets:** No action; no map or asset changes.

## What is in it so far

Margit's arena follows the Stormveil lock. Its raw game region previously got collapsed into
Stormhill, so starting in Stormveil could eject you to Roundtable during the fight intro.
The client now preserves that distinction while keeping surrounding Stormhill in Limgrave.
Existing seeds benefit from updating the client; no regeneration is needed.

## What carried over from v0.6.0.11

Nothing is owed. Both v0.6.0.11 release workflows were green before the tag, the v0.6.0.10 stable
row and the KNOWN-ISSUES refresh were paid in #1563 before the cut, and the one thing that went
wrong after the tag -- the open-window workflow reading the moving `dev` tag as the shipped
release -- is fixed in this window's opening commit rather than carried.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
