# v0.6.1.8 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes, for existing non-Mario seeds on the 0.6.1 line.** Their contract and save formats are unchanged. Mario mode needs a newly generated seed and Mario's separate save; replacing a client does not convert an existing run into Mario mode.

## What you need to update

- **Client:** Required for experimental Mario seeds; optional for existing non-Mario seeds.
- **APWorld:** Host-only update for generating Mario seeds.
- **YAML:** **New YAML optional. Existing YAMLs remain valid.** Mario mode defaults off.
- **Existing seed/save:** Compatible for existing non-Mario runs. Mario mode needs a new seed and a separate Mario save, with no migration of an existing save.
- **Profile/assets:** Reinstall or replace the Mario DLL with the AP-compatible fork and add both DLLs to Mario's me3 profile; supply your own US SM64 ROM. Ordinary profiles need no change.

## What is in it so far

Mario starts with basic jumping and combat. Two Progressive Jump pickups restore Double Jump and then Triple Jump; Backflip and Side Flip have their own items, alongside Long Jump, Wall Kick, Dive, Ground Pound, Enemy Grab and Boss Swing. Names follow the SM64 APWorld, with progressive jumping as this integration's extension.

Weapon, armor and Ash of War rewards become runes while their pickup locations stay checks. Key progression remains intact. The client waits for the Mario worker to report the exact applied lock mask before processing checks or rewards, and restores earned moves from received-item history on reconnect.

This is an experimental integration, pending live acceptance. Automated tests and compilation do not prove both mods can share an overlay, warp together, enforce region locks or complete every required encounter. The implementation stays in draft until those gates pass. See [the integration spec](../docs/SPEC-er-mario-integration.md).

## What carried over from v0.6.1.7

The reported auto-equip crash and NPC item-delivery fixes from v0.6.1.7 still need their live acceptance checks. Mario integration does not resolve or supersede that validation debt.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
