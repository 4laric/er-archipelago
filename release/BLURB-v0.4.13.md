# v0.4.13 — release blurb

**A boss the game forgot to pay now pays you back.** About 179 Elden Ring checks are corpse-treasure
awards — the loot an EMEVD death event hands over when a specific enemy dies. If that enemy died in a
way the event never witnessed — it fell, despawned, or died during a load — the game marked it dead
but never offered the loot, and on the next reload it force-killed the corpse without re-offering it.
The check was then permanently unpayable in-game (found live when rouqs' Leyndell Ulcerated Tree
Spirit died unpaid). Because the death flag persists in the save, the pair "death flag up, check flag
still down" is a complete signature of the miss. The v0.4.13 client ships a table of those pairs and
sweeps them at connect — so it pays the missed check **retroactively, on any seed old or new**, the
moment you update. No new YAML, no re-roll. The six corpses that legitimately re-offer their loot on
reload are excluded, so a merely-unlooted corpse is never pre-empted.

**Reopening a shop keeps its Archipelago item names.** The shop shelf that learned to show each
slot's real name could lose that repaint if you warped to a merchant and opened it fast — a lagging
load-edge reset was wiping the pending shelf just as the shop drew, leaving you with hints and blank
rows. It survives the fast open now.

**The F6 tracker resizes freely again.** A late-game sweep row could get long enough that the
tracker's anti-clipping floor collided with its own resize ceiling, and horizontal resize silently
died (up/down still worked — exactly the report). The floor now sits below the ceiling, and a window
dragged smaller than its content scrolls instead of clipping.

**And the pickup ding is off unless you want it.** The multiworld-collect cue was the stock Windows
system chime on every single pickup — no game-volume coupling, just the OS asterisk. It defaults to
silent now; `"sound_cue": true` in `apconfig.json` brings it back for anyone who liked it.

## What you need to update

- **Client:** Required — this is the one to update. The contract is unchanged (`dc0dc687`), so it is
  a drop-in even mid-seed; the bundled `update-er-archipelago.ps1` does it in one command. The
  corpse-award sweep and every fix above are client-side and apply to seeds you are already playing.
- **APWorld:** Host-only — the room host or generator installs v0.4.13; joining players only need the
  matching client. A v0.4.12 room keeps working with a v0.4.13 client (the banner notes the mismatch;
  that is it doing its job). Roll new seeds on v0.4.13 when convenient.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — no save migration. Keep a mid-flight seed's APWorld as is and
  update the client; the corpse-award sweep will pay any previously-missed checks in that very save.
- **Profile/assets:** No action.
