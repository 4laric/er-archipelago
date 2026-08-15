# v0.4.3 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the only moment
anyone remembers why it mattered._

## What is in it so far

Nothing yet. This window was opened the morning after v0.4.2 shipped, with no commits past the tag,
so there is genuinely nothing here to describe. That is the point of opening it early: every change
that lands from here writes its own line while somebody still knows what it was for, rather than
being reconstructed from a commit log at release time.

If you are reading this at the tag and it still says "nothing yet", the window shipped as pure
version-lockstep and a v0.4.2 seed behaves identically.

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
