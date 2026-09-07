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

Only pipeline work. The release job no longer refuses to rebuild a tag because the MapForGoblins
fork moved after the tag was cut; the pin recorded in a tag is what that tag ships. Nothing here
changes a seed or a client yet.

## What carried over from v0.6.0.1

Nothing is owed. v0.6.0.1 shipped with its notes complete and its client half landed; the one
open item at its tag, the MapForGoblins engine build, ran in the release workflow rather than by
hand, which was the point of the pin gate. Client #316 (received Great Runes unequippable at a
grace) remains an open known issue, not a debt of this window.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
