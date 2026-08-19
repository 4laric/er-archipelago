# v0.4.9 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## What is in it so far

The bundle now starts with the files it actually contains. Stable releases tell me3 to load the
authenticated `flower-package`, while development bundles without those assets no longer retain a
dead `ap-package` reference. Packaging stops before publication if a profile names a directory that
is not in the finished bundle, closing the `ReadDir: Path not found` startup failure reported on
Linux.

The boss-sweep tracker also stops asking you to kill Patches after he has surrendered. His normal
encounter never sets the death flag that old seeds displayed as a two-check sweep, so new seeds no
longer arm or advertise that impossible route. Unknown sweeps are not discarded wholesale: the cut
is limited to triggers the project has positively confirmed cannot fire in normal play.

## What carried over from v0.4.8

No player-facing work is carried over. The two post-tag commits corrected the v0.4.8 release prose
and adjusted CI sharding/benchmarks; neither changed a seed or client at runtime.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
