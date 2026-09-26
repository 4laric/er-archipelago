# v0.6.1.5 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes.** `CONTRACT_HASH` is unmoved at `2aa64f43`; any client from the 0.6.1 line (v0.6.1 through v0.6.1.4) keeps working on these seeds, and your save is not touched. Take this one mid-run: it is the first bundle that actually contains the client fixes v0.6.1.4 announced.

## What you need to update

- **Client:** Optional, recommended; it carries the map-pin sync and two other client fixes.
- **APWorld:** No; unchanged apart from its version stamp.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible; no regeneration or save migration required.
- **Profile/assets:** Reinstall or replace both map DLLs from `me3/` (`MapForGoblins.dll` and `MapForGoblins.upstream.dll`). Keep your `MapForGoblins.ini`; 2.1.5 adds its new options itself.

## What is in it so far

**The map is on MapForGoblins 2.1.5.** VirusAlex's latest opens the map faster, fixes the
"require map fragments" setting, and restores icons that had gone missing. Our Archipelago
layer sits on top of his DLL rather than replacing it, so it was re-fitted to the new build and
checked in game: every marker matched, and "reachable according to tracker" narrows the pins
exactly as before.

**The fixes v0.6.1.4 promised are actually in it now.** v0.6.1.4's notes said two players on
one slot would see the same pins. Its zip was built from the client *before* that fix, because
the release job refused the tag and had to be forced through with the old client. This bundle
is built from the current client, so it has the pin sync, the fix that sends capped-consumable
overflow to your storage chest instead of losing it, and a crash-handler fix that stops a
harmless, already-handled memory probe from being reported as a crash.

## What carried over from v0.6.1.4

Owed and paid here: the three client fixes above, which v0.6.1.4's notes listed but its zip did
not contain. The stable promotion to v0.6.1.4 is also paid in this window. Nothing else rolls on.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
