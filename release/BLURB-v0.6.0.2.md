# v0.6.0.2 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes.** Versions are V.R.M.F and this is the 0.6.0 line: a v0.6.0.2 client plays every seed
rolled by a v0.6.0, v0.6.0.1 or v0.6.0.2 apworld, and the older clients play v0.6.0.2 seeds.
The seed contract is unchanged. Keep whichever client you have unless a change below names a fix
you want.

## What you need to update

- **Client:** Optional — nothing in this window yet changes the client; a v0.6.0.1 client keeps
  playing every 0.6.0-line seed.
- **APWorld:** Host-only — install v0.6.0.2 when generating a new room once it ships.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — a fixpack never strands a running seed.
- **Profile/assets:** No action — the MapForGoblins build and preset are unchanged from v0.6.0.1.

## What is in it so far

**A partner's early item can no longer end up behind a late boss in your world.** With the default
`cross_game_progression: auto`, generation reserves a share of every other game's progression on
your checks before Archipelago's own early-items pass runs. That reservation used to draw from
every copy in the pool, including the ones the other game had asked to see in sphere 1, so a key
another player needed at their start could be locked behind a 10-of-15 Astel with nothing left
for the early pass to place. Those copies now stay in the pool. New seeds only.

**Elden Ring beside Oracle of Seasons (and other keysanity-off games) generates again.** Our
pre-fill was taking a partner's dungeon slots before the partner had placed its own keys, and the
partner's fill failed with "not enough locations". We now leave alone any game that still has its
own pre-fill items to place. New seeds only.

Also pipeline work: the release job no longer refuses to rebuild a tag because the MapForGoblins
fork moved after the tag was cut; the pin recorded in a tag is what that tag ships.

## What carried over from v0.6.0.1

Nothing is owed. v0.6.0.1 shipped with its notes complete and its client half landed; the one
open item at its tag, the MapForGoblins engine build, ran in the release workflow rather than by
hand, which was the point of the pin gate. Client #316 (received Great Runes unequippable at a
grace) remains an open known issue, not a debt of this window.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
