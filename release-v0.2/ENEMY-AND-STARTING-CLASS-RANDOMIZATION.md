# Enemy and Starting Class Randomization -- Use matt's Randomizer. They Stack.

The short answer: this project does not randomize enemies or starting
classes, and it has no plans to -- because you can already have both,
**on top of your Archipelago seed**, by running **thefifthmatt's Elden Ring
Randomizer** alongside it. The two tools compose cleanly. You do not have
to choose.

matt's randomizer is excellent and long-established; enemy shuffle and
starting-class randomization are its territory, and it does them better
than we would by duplicating them. So instead of an apology, here is the
recipe.

One rule before anything else, because it is the only way to get this
wrong: **in matt's randomizer, ITEM randomization must be OFF.** Items are
this project's job. Enemies and starting class are matt's.

## The recipe: randomized enemies + starting class + Archipelago

1. **Generate your Archipelago seed** as usual (see
   [SETUP.md](SETUP.md), part A). Nothing about it changes.
2. **Run matt's Elden Ring Randomizer** and configure it:
   - Enemy randomization: **ON** (bosses too, if you like).
   - Starting-class randomization: **ON**, if you want it.
   - Item randomization: **OFF**. This is the critical one -- see the
     settings section below.
3. **Let matt's randomizer write its output** the way its own
   instructions describe. It works by rewriting the game's files
   (`regulation.bin` and friends).
4. **Launch the game with the Archipelago runtime client loaded**
   (see [SETUP.md](SETUP.md), part B) and connect to your seed.
5. **Play.** Enemies and your class come from matt's seed; every item
   pickup is still an Archipelago check, and Region Locks still arrive
   from the multiworld.

## Recommended matt's randomizer settings

In words, precisely:

- **Enemy randomization ON.** Shuffled enemies and bosses are fine; the
  Archipelago client detects checks by item lot, not by which enemy is
  standing there.
- **Starting-class randomization ON**, if you want a random start.
- **Item randomization OFF -- mandatory, not a preference.** If matt's
  item randomizer also shuffles the item lots, both tools are rewriting
  the same checks: pickups will pay out the wrong things and your
  Archipelago seed will be wrong. There is no partial setting that makes
  this safe. Items off, always.

We intend to ship a copy-pasteable options string for matt's randomizer,
preconfigured exactly as above. It is not ready yet:

```
TODO(alaric): paste the matt's-randomizer options string here (enemies ON, starting class ON, ITEM randomization OFF)
```

Until then, set the three points above by hand in matt's UI.

## Why this composes at all

The two tools do different jobs in different places:

- **matt's randomizer** rewrites the game's files on disk --
  `regulation.bin` and related data -- before you play.
- **This project** is pure-runtime. It modifies **no game files**: it
  reads and writes params in memory while the game runs, through the
  runtime client. Remove the client and your install is exactly as
  matt's randomizer left it.

Because we are not fighting over the same bytes on disk, the two coexist
-- with the one overlap being items, which is why matt's item
randomization must stay off. The projects share no code or data; v0.2 is
a from-scratch, data-derived rebuild. We recommend matt's randomizer
because it is good, not because we depend on it.

## "reroll_enemy_drops" is not enemy randomization

One shipped option (on by default) has a misleading name, so let's be
plain about it: **`reroll_enemy_drops` changes what farmable enemies
drop** -- the repeatable farm drops -- not which enemies exist or where
they stand. Their one-time drops, the actual Archipelago checks, are
untouched. No enemy moves, changes, or gets replaced. It reshapes the
farming economy, nothing more.

Relatedly: **enemy and boss scaling is always on** and keyed to your
progression -- a region you unlock late is tuned tougher, even "early"
territory. That is scaling, not randomization; the enemies are still
whatever your game (vanilla or matt-shuffled) puts there.

## What this project randomizes instead

- **The item and check layer.** Every item pickup -- corpse loot, chests,
  boss drops, shop slots -- is a check that pays out a shuffled item,
  possibly another player's, in a multiworld.
- **The progression graph itself, via `num_regions`.** The open world is
  carved into regions sealed behind Region Lock items you must *receive*
  from the multiworld; each Lock that arrives opens a region. This is
  the marquee feature -- it turns Elden Ring's go-anywhere map into an
  Archipelago progression puzzle.

For the full mental model of how a run plays, see the
[Player Guide](Elden-Ring-Archipelago-Player-Guide.md).

## See also

- [SETUP.md](SETUP.md) -- installing and generating a seed.
- [Player Guide](Elden-Ring-Archipelago-Player-Guide.md) -- how a run
  actually plays, start to finish.
- [KNOWN-ISSUES.md](KNOWN-ISSUES.md) -- current issues and by-design
  non-features.
