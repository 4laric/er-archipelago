# v0.6.1.7 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes.** This client update keeps existing 0.6.1 / 0.6.1.x seeds and save formats compatible. Equipment changes are paced; players recovering from a crash can disable auto-equip before connecting. The reported crash still needs an in-game acceptance check.

## What you need to update

- **Client:** Required for equipment pacing and the new recovery command; replace the client DLL when this update ships.
- **APWorld:** No. These changes run entirely in the client.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible. No new seed or save migration is required.
- **Profile/assets:** No action beyond replacing the client DLL.

## What is in it so far

A reconnect backlog no longer drains all ready equipment changes in one frame. Weapons, armour, talismans and Physick tears share a 500 ms interval, separate from item delivery. Deferred items retain their stream positions.

If a backlog crashes during auto-equip, launch disconnected and enter `!autoequip off` before connecting. Items still arrive; automatic equipment and spell changes are suppressed for the game session, including reconnects. `!autoequip seed` restores the seed setting. See [Getting unstuck](GETTING-UNSTUCK.md#incoming-items-crash-during-auto-equip).

This closes an unbounded queue-drain path found from Fossils's report. It is not yet a live-verified resolution of that crash.

Idle NPC talk-script polling no longer keeps received goods waiting for minutes before delivering them in a burst. Other talk commands still pause delivery. This change has automated coverage; delivery near Gostoc and during Twin Maiden hand-ins still needs an in-game check.

## What carried over from v0.6.1.6

The auto-equip crash report still needs an in-game acceptance check. These notes do not claim that pacing has reproduced or conclusively resolved the crash.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
