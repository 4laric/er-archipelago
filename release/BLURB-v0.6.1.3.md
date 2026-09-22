# v0.6.1.3 — release blurb (draft)

_Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes, trivially.** `CONTRACT_HASH` is unmoved at `2aa64f43`, and nothing in this window touches the client or a contract key. Whatever client you're running keeps working exactly as before.

## What you need to update

- **Client:** No -- nothing in this window touches the client.
- **APWorld:** No -- unchanged apart from its version stamp.
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

## What carried over from v0.6.1.2

Nothing is owed on the contract or client side -- this window opened at the v0.6.1.2 tag with
zero commits past it. `release/CHANNELS.tsv` promotes `stable` to v0.6.1.2 in the same commit.
