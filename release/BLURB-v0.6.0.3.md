# v0.6.0.3 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes.** Versions are V.R.M.F and this is the 0.6.0 line: a v0.6.0.3 client plays every seed
rolled by any 0.6.0-line apworld, and the older 0.6.0-line clients play v0.6.0.3 seeds. The seed
contract is unchanged. Keep whichever client you have unless a change below names a fix you want.

## What you need to update

- **Client:** Optional — nothing in this window yet changes the client; any 0.6.0-line client
  (v0.6.0, v0.6.0.1, v0.6.0.2) keeps playing every 0.6.0-line seed.
- **APWorld:** Host-only — install v0.6.0.3 when generating a new room once it ships.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — a fixpack never strands a running seed.
- **Profile/assets:** No action — the MapForGoblins build and preset are unchanged from v0.6.0.2.

## What is in it so far

**Generating beside another game got quieter, and fairer.** Everything Elden Ring places in other
players' worlds — the shared progression, another game's keys reserved on your checks, blessing
fragments, the useful items we export — now happens at the moment Archipelago set aside for it,
after every other game has finished placing its own items and after all the sphere-1 items are
down. The two guards shipped in v0.6.0.2 for that (skipping a partner that was still placing its
own keys, and skipping copies a partner wanted early) existed only because we were going first;
they are gone, and the partner now gets its full share of our progression instead of watching it
fall back onto Elden Ring checks. New seeds only; a running seed is unaffected.

## What carried over from v0.6.0.2

Nothing is owed. v0.6.0.2 shipped with its notes complete and its client half landed before the
tag. Client #316 (received Great Runes unequippable at a grace) remains an open known issue, not a
debt of this window. The upstream-core proposal (#1459) is tracked as work, not as a release debt.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
