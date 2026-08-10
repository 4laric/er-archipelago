# v0.3.11 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the only moment
anyone remembers why it mattered._

## What is in it so far

Nothing yet. This window was opened at the moment v0.3.10 was tagged, before anything landed in it,
which is the point: a release note written weeks later is a reconstruction, and a reconstruction is
where the interesting half goes missing.

## What is queued for it

A fix for something two players noticed independently -- items whose region label sends you to the
wrong part of the map. If an item said "Cerulean Coast" and you found it in Charo's Hidden Grave,
that was real, and on a seed that kept one of those regions and not the other it was worse than
cosmetic: the check either sat somewhere the game would not let you walk, or never existed at all.

That work is open as a pull request, not merged, so it is not promised here yet.

## For the technically minded

Nothing in the contract moved. A v0.3.10 client and a v0.3.11 seed still speak to each other, and
the reverse holds too -- the version bump exists so that a bug report can name exactly one build.
