# v0.4.9 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## What is in it so far

More of the things you actually pick up are randomized now. Seven merchant Bell Bearings that were
still dropping vanilla, Thops's staff, the Discarded Palace Key, Comet Azur, Stars of Ruin, the
Serpent Crest Shield, the Sacred Tower painting, and several fixed pot and bottle pickups are now
ordinary checks in their real regions. This was the useful residue behind the misleading old “621
unplaced” count: the release carries a row-by-row audit of the actual 30 unique-item suspects, and
leaves relocating-NPC, duplicate, cut, dead, and phantom rows out deliberately instead of guessing
a region for them.

The bundle now starts with the files it actually contains. Stable releases tell me3 to load the
authenticated `flower-package`, while development bundles without those assets no longer retain a
dead `ap-package` reference. Packaging stops before publication if a profile names a directory that
is not in the finished bundle, closing the `ReadDir: Path not found` startup failure reported on
Linux.

## What carried over from v0.4.8

No player-facing work is carried over. The two post-tag commits corrected the v0.4.8 release prose
and adjusted CI sharding/benchmarks; neither changed a seed or client at runtime.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
