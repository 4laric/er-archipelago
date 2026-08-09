# v0.3.10 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the only moment
anyone remembers why it mattered._

## What is in it so far

**Nothing yet.** The window was opened at the v0.3.9 tag rather than waiting for a gate to demand it,
so this file exists before the first change does. That is the intended order: rule 14 asks for the
note in the same commit as the change, and a blurb that does not exist yet cannot receive one.

## What just shipped, for context

v0.3.9 is the release this window follows, and it is worth knowing what a player already has before
adding to it: **Grace Attunement** (a region hands over one Site of Grace on unlock and the rest bloom
once you have touched a few), a progression-surface picker in the options wizard that finally says
what each class actually selects and what ticking it is worth, the `Boss` location class corrected
from 143 checks to 214, the `Shop` umbrella corrected to actually contain its own members, and 29
checks that shipped with no item name getting one.

## Compatibility

`CONTRACT_HASH` is unmoved at `5c2b9bf2`, so v0.3.10 opens version-lockstep with v0.3.9: the version
number moves in step with the client, the wire between them does not, and a v0.3.9 client still
handshakes -- including with a seed that has grace attunement turned on, which was the single
version-sensitive setting v0.3.9 introduced.

If that changes while this window is open, this section is where it gets said, and the ledger row in
`release/CONTRACT-VERSIONS.tsv` is what makes the claim checkable rather than remembered.
