# v0.4.10 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## What you need to update

- **Client:** Required — use the v0.4.10 client with v0.4.10 seeds.
- **APWorld:** Host-only — the room host or generator must install v0.4.10; joining players only
  need the matching client.
- **YAML:** **New YAML optional. Existing YAMLs remain valid.** Generate a fresh template only to
  see and select newly added options such as the Malenia goal.
- **Existing seed/save:** New seed required — finish an active v0.4.9 seed with its matched v0.4.9
  client and APWorld; use a new seed for v0.4.10 features.
- **Profile/assets:** No action — this window does not require a profile or asset reinstall.

## What changed at the table

**Progression is balanced across every game at the table.** By default,
`balance_progression_across_games` makes each partner contribute roughly its 1/N share of eligible
progression to your starred Progression Surface, while every partner game receives its own share
of Elden Ring's Locks, all seven Great Runes when the rune goal is active, and other progression.
It respects items another player kept local, defers to any explicit `cross_game_progression`
percentage you set, and states in the log when capacity caps a share rather than claiming a
quota it could not place. Set it to `false` for ordinary asymmetric fill. The spoiler may still prune a redundant
item from its minimal route.

**Malenia can be the ending now.** Set `goal: malenia` and the seed guarantees the Haligtree, but it
does not hand you Prayer Room or Roots. Once your chosen Great-Rune and region requirements resolve,
you get Haligtree Canopy and play the whole route through Loretta and Elphael; Malenia's own defeat
ends the run. The existing goal axes remain independent, so this works with no Great Runes or any N,
and with held locks, completed regions, or no region requirement.

**Starting Region Pool is additive, and the wizard now shows the cost.** Every candidate you name is
kept; `start_regions` decides how many of them actually open the run. The seed-size preview includes
the resulting extra regions before you generate, and the generation log names them separately from
regions forced by your goal.

**Region-Lock travel has two knobs, and the descriptions now say which is which.**
`progression_bias` decides how many Locks leave their owner; `cross_game_progression` decides how
many travelling Locks are deliberately sent to non-Elden-Ring games. Ordinary fill alone does not
promise that a smaller partner gets most of them. This is a documentation correction, not a seed
behavior change.

## What carried over from v0.4.9

No player-facing work is carried over. The v0.4.9 release tag differs from `main` only by its client
gitlink bump, and this window's v0.4.10 client pin supersedes it.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
