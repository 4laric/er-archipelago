# v0.4.9 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## What is in it so far

The bundle now starts with the files it actually contains. Stable releases tell me3 to load the
authenticated `flower-package`, while development bundles without those assets no longer retain a
dead `ap-package` reference. Packaging stops before publication if a profile names a directory that
is not in the finished bundle, closing the `ReadDir: Path not found` startup failure reported on
Linux.

Shop checks can make you rich again, once. Every finite AP shelf rolls a seeded price from zero to
5000 runes without looking at its reward, so a Lord's Rune on a cheap shelf is the delightful
one-shot flip it used to be rather than a price-derived hint. Unlimited shelves stay economy-safe:
a money rune there costs exactly what it pays out, preventing an endless buy-and-consume loop.

## What carried over from v0.4.8

No player-facing work is carried over. The two post-tag commits corrected the v0.4.8 release prose
and adjusted CI sharding/benchmarks; neither changed a seed or client at runtime.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
