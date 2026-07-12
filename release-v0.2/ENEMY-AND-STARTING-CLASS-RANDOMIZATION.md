# Enemy and Starting Class Randomization -- What This Project Does and Doesn't

The short answer, up front:

- **Starting classes are not randomized.** You pick your class at character
  creation, exactly as in vanilla. This is a deliberate v0.2 decision, not a
  bug or an oversight -- there is a written design for it, and it is on hold.
- **Enemies are not randomized.** Every enemy and boss is the vanilla one, in
  its vanilla place. This project does not shuffle enemies around the map.
- What you get instead is something the standalone randomizers cannot do:
  a **multiworld**. Your item pickups send items to other players (or other
  games entirely), theirs come back to you, and the open world itself is
  carved into regions you unlock by *receiving* Region Lock items.

If that trade sounds interesting, read on. If you specifically want enemy
rando, matt's randomizer (below) does it brilliantly, and nothing here will
replace it.

## If you're coming from thefifthmatt's randomizer

Most players find this project after playing **thefifthmatt's Elden Ring Item
& Enemy Randomizer**, and it sets the expectations -- fairly, because it is an
excellent piece of work. But the two projects are different kinds of thing,
not competitors:

- **matt's randomizer** is a solo randomizer. It rewrites the game's files to
  shuffle items, enemies, and bosses within your own game. Enemy
  randomization, boss shuffle, and randomized starting classes are its
  territory, and it does them well.
- **This project** is an **Archipelago world**: multiworld-first. Your checks
  can hold items for a Hollow Knight player three worlds over; your Region
  Locks might arrive from someone else's game. And it modifies **no game
  files at all** -- it is the vanilla game, plus an apworld for seed
  generation, plus a runtime client. Remove the client and Elden Ring is
  exactly as you left it.

The two share no code or data; this is a from-scratch, data-derived rebuild.
They can coexist on the same machine without conflict. (They cannot run on
the same playthrough, though -- this project needs the vanilla game files.)

## What IS randomized here

- **Every item pickup is a "check."** Corpse loot, chests, boss drops, shop
  slots -- each pays out a shuffled item, possibly another player's. See the
  [Player Guide](Elden-Ring-Archipelago-Player-Guide.md) for the full mental
  model.
- **The world itself, via `num_regions`** -- the headline feature. The
  overworld's regions are sealed behind "Region Lock" items you must receive
  from the multiworld; each Lock that arrives opens a region and lights its
  graces. This is what turns Elden Ring's go-anywhere map into an Archipelago
  progression graph. `num_regions: 4` is roughly a tight 4-hour run; the
  shipped default of `0` keeps all 22 regions in play.
- **Farmable enemy drops and merchant stock** are rerolled at runtime -- see
  the next section, because this is the setting people misread.
- **Enemy and boss scaling** is always on and keyed to your *progression*,
  not vanilla's intended order: a region you unlock late is tuned tougher,
  even "early" territory. That is scaling, not randomization -- the enemies
  are still the vanilla ones.

## "reroll_enemy_drops" is not enemy randomization

Two shipped options (both on by default) sound like enemy rando and are not:

- **`reroll_enemy_drops`** changes **what farmable enemies drop** -- the
  repeatable farm drops, not which enemies exist or where they stand. Their
  one-time drops, the actual Archipelago checks, are untouched.
- **`reroll_infinite_shop_stock`** rerolls every unlimited-stock merchant
  slot to a random high-impact consumable, priced to match, so merchants stop
  being a wall of Arrows.

Both reshape the *economy* around vanilla enemies. No enemy moves, changes,
or gets replaced.

## Could starting classes be randomized later?

Plausibly, yes. There is a written design spec (currently a draft, on hold,
not being built). The idea: the seed picks your **starting build** -- the
stat spread and starting equipment a vanilla class defines -- independent of
whatever class you pick in the character-creation menu. You create a
character normally; on first connect to a fresh save, the client respecs you
into the seed's rolled class, deterministically, so everyone on the same seed
and slot gets the same start. The reason it works this way rather than at the
creation screen is an engine constraint: the game reads class definitions
before the client has connected, so the seed cannot exist yet at that moment.

No date, and no promise it will ship. But it is designed, it fits the
architecture, and "why aren't starting classes random?" is the most common
question we get -- so if it lands, this page will be updated first.

## Enemy randomization, for completeness

Unlike starting classes, enemy randomization has no design spec and is not
on the roadmap. Shuffling enemies is a solved problem in matt's randomizer;
if randomized enemies are what you want, play matt's randomizer -- genuinely.

## See also

- [Player Guide](Elden-Ring-Archipelago-Player-Guide.md) -- how a run
  actually plays, start to finish.
- [KNOWN-ISSUES.md](KNOWN-ISSUES.md) -- current issues and by-design
  non-features, so you can tell them apart.
