# v0.6.1.3 — release blurb (draft)

_Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes, trivially.** `CONTRACT_HASH` is unmoved at `2aa64f43`, and nothing in this window touches the client or a contract key. Whatever client you're running keeps working exactly as before.

## What you need to update

- **Client:** No -- nothing in this window touches the client.
- **APWorld:** Host-only, for newly generated rooms (the sweep fix below).
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible; no regeneration or save migration required. A seed already in progress keeps whatever it already generated.
- **Profile/assets:** No action; no map or asset changes.

## What is in it so far

**The matt's-randomizer setup guide had a gap and an unstated assumption.** Two Discord reports
from the same player, same setup session: (1) is `MapForGoblins.dll` supposed to get loaded
alongside our client when launching through matt's, and (2) does `me3` still need setting up per
`SETUP.md` if you're going the matt's-launcher route at all. Both answers were "yes, just the one
DLL" and "no, skip it entirely" -- and neither was written down anywhere.

`ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md` now says so directly: add `MapForGoblins.dll` (not
`MapForGoblins.upstream.dll` -- that one's the `ap.me3`-only fallback build, never loaded on this
path) as a second dll mod right after the client, and `me3` from `SETUP.md` part B just doesn't
apply here at all, because matt's launcher never reads `ap.me3`. The upgrade-by-hand instructions
pick up the same fix: repoint MapForGoblins alongside the client dll, since the helper script only
repoints the client's own path.

Nothing here changes what the tools do. It changes whether a new player reading the guide gets
their DLLs loaded correctly on the first try instead of the second.

**A stuck check at Castle Morne, finally explained.** A player cleared Weeping Peninsula top to
bottom -- every boss down, every sweep fired -- and was left staring at one check that would
never budge: the Grafted Blade Greatsword, Leonine Misbegotten's own drop. Everything else near
that fight paid out fine.

Tracing the actual decompiled game script (not just the region tables) found the reason. Killing
the boss sets its defeat flag immediately and reliably -- that part works, and it's what swept
the other 9 checks around it. But the weapon itself waits on a *second* event in the same map, and
that event opens with a guard whose entire job is "don't replay this cutscene if the boss is
already dead." Harmless in vanilla, where nothing else ever touches that flag early. Not harmless
here, where this project watches that exact flag globally from the moment you connect, for its
own sweep system. If the flag reads true a beat ahead of that one event finishing its own work,
the guard trips, and the weapon's reward -- two more steps down the chain -- never happens. Once
tripped, it never gets a second chance.

The fix doesn't touch that fragile vanilla chain at all. It gives the check a second, direct path:
the same reliable sweep that already pays the other 9 nearby drops now pays this one too. Kill the
boss, get everything, the way region clears are supposed to work. New seeds only -- a seed
already generated with the old table won't retroactively gain the fix.

**This is one instance of a pattern, not a one-off.** The same vanilla event shape -- a scripted
common-event reward, gated behind a guard that assumes nothing else touches its flag early --
covers roughly ninety boss-reward drops across the whole game. Most of them are presumably fine;
this is the one a player actually got stuck on and reported. A proper, general fix (a client-side
reconciler that watches for this class of stall directly, rather than admitting checks into
sweeps one at a time as they're found) is tracked as its own follow-up, not squeezed into this
window.

## What carried over from v0.6.1.2

Nothing is owed on the contract or client side -- this window opened at the v0.6.1.2 tag with
zero commits past it. `release/CHANNELS.tsv` promotes `stable` to v0.6.1.2 in the same commit.
