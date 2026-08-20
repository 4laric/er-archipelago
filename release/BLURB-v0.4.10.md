# v0.4.10 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## What changed at the table

**Malenia can be the ending now.** Set `goal: malenia` and the seed guarantees the Haligtree, but it
does not hand you Prayer Room or Roots. Once your chosen Great-Rune and region requirements resolve,
you get Haligtree Canopy and play the whole route through Loretta and Elphael; Malenia's own defeat
ends the run. The existing goal axes remain independent, so this works with no Great Runes or any N,
and with held locks, completed regions, or no region requirement.

**Starting Region Pool is additive, and the wizard now shows the cost.** Every candidate you name is
kept; `start_regions` decides how many of them actually open the run. The seed-size preview includes
the resulting extra regions before you generate, and the generation log names them separately from
regions forced by your goal.

## What carried over from v0.4.9

No player-facing work is carried over. The v0.4.9 release tag differs from `main` only by its client
gitlink bump, and this window's v0.4.10 client pin supersedes it.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
