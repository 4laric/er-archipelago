# v0.4.3 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the only moment
anyone remembers why it mattered._

## What is in it so far

**A bad `start_region_pool` now fails like a yaml problem instead of a crash.** If you name fewer
regions in `start_region_pool` than you ask for in `start_regions` -- one region, two starting
regions -- generation used to stop on a Python traceback. Worse, the message buried in it told you
to raise `num_regions`, and that road is closed: `start_region_pool` cuts the pool down to the
regions you named before the starting regions are drawn, so a bigger seed just grows a set the
option shrinks again. A tester followed that advice at `num_regions: 9` and got the same crash back.

The refusal now names both options, both numbers and the regions you actually listed, and offers the
two fixes that work: list more regions, or start in fewer. Nothing about a yaml that already
generated changes -- if your pool is big enough for your count, this is invisible to you.

## What v0.4.3 does not change

`CONTRACT_HASH` is unmoved at `5c2b9bf2`, the same shape the contract has had since v0.3.9. The
client and the apworld handshake on that hash, not on the version number, so a v0.4.2 client
generates and plays a v0.4.3 seed and the other way round. Nothing in your yaml needs to change, no
seed you have already rolled is invalidated, and there is no reason to re-download the client unless
a later entry in this file gives you one.

Three options were retired during the v0.4.2 window -- `local_item_only`,
`exclude_local_item_only` and `progression_surface_mode` -- and that happened in v0.4.2, not here.
If your yaml still names one of them, that is the release to read, not this one.

## If you are upgrading

Take the bundle from the release page as usual. The apworld and the client in it are built from the
same commit, so there is no pairing to check by hand.
