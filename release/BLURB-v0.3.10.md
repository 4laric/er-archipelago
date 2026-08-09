# v0.3.10 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the only moment
anyone remembers why it mattered._

## What is in it so far

### Your DLC-only run ends on Promised Consort Radahn now

If you play `dlc_only` and leave `goal` alone, the run used to end wherever your draw happened to
reach -- for one player this week, on Romina in the Ancient Ruins of Rauh, well before he expected an
ending. Nothing was broken. The base game's finale is guaranteed because the Ashen Capital is not a
region you can roll: it is there on every seed. Enir Ilim is an ordinary DLC region, so Radahn was
the ending only when the draw felt like it.

Enir Ilim is now handled the way the Ashen Capital is. It is taken out of the draw and always kept,
so `num_regions: 3` means three regions to play **plus** the ending. It stays a real region you
explore, with its own checks and its own Lock -- it is a place you play, where the Ashen Capital is
ten checks and a gauntlet.

### ...and it can no longer be where your run STARTS

The region you end in should not be the region you open in. It could be: on the previous build,
14.7% of `num_regions: 6` DLC-only seeds opened on Enir Ilim, and 59.6% at `num_regions: 1`. That is
fixed for `goal: promised_consort` as well as for the default -- whatever your goal keeps, your run
will not begin there.

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
