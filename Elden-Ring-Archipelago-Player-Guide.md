# Elden Ring Archipelago -- Player Guide (v0.2)

You have it installed (if not, see `SETUP.md` -- this guide won't repeat that).
This is about what happens after you press New Game: how the run actually plays,
and the handful of things worth understanding before they confuse you.

## The mental model

Two ideas, and everything else follows from them.

**1. Every item pickup is a "check."** Treasure on corpses, chests, boss drops,
shop slots -- when you pick one up, the item that was there is gone. Instead, an
Archipelago item goes out to whoever it belongs to: maybe you, maybe another
player in the multiworld. Your own items -- weapons, spells, flasks, keys --
arrive the same way, from your checks or from someone else's game entirely.
Playing solo? Same loop, you're just both ends of it.

**2. The world is Shattered.** The open world is carved into major regions,
each sealed behind an item called a **Region Lock** -- "Limgrave Lock," and
so on. You start at Roundtable Hold with one region already open. When a Region Lock
arrives, that region opens and its graces light up on your map, so you can warp
straight in. Explore it, clear its checks, and more Locks come back out of the
multiworld -- opening more regions, until you can reach the goal.

Read that second idea again with vanilla habits switched off, because it is
the part everyone gets wrong at first: **the Lock is the only gate.** Vanilla
routes and key items do not control access to regions here. You do not need
the Rold Medallion to reach the Mountaintops of the Giants -- you never ride
the Grand Lift of Rold; the region's Lock arrives, its graces light, you warp
in. With the DLC enabled, you never fight Mohg or touch Miquella's cocoon --
the Land of Shadow regions unlock exactly like every other region: Lock
arrives, graces light, warp in. And it cuts both ways: get into a region
whose Lock you don't hold, by any route, and the client warps you back out.

Two exceptions echo vanilla, both on by default, and both are IN ADDITION to
the region's own Lock -- never instead of it:

- **Raya Lucaria Academy** also needs the **Academy Glintstone Key**. The key
  is shuffled into the item pool like everything else, and the Academy's
  graces light when the key arrives.
- **Leyndell** also needs **Great Runes** -- two by default
  (`leyndell_runes_required`). The capital's graces light once enough Great
  Runes have arrived.

Neither exception can make a seed unbeatable: the key is always placed
somewhere you can reach, and the rune requirement shrinks automatically if
your seed holds fewer Great Runes.

That second idea is the whole trick: Elden Ring's famously go-anywhere map
becomes a progression puzzle, one region at a time. The `num_regions` option
controls how many regions are kept -- 4 is a tight ~4-hour run, higher is
longer, and 0 (the shipped default) keeps everything in play for the full
Shattering -- 17 regions in the shipped base-game config, 31 with the DLC on.

None of this touches your game files. It's the vanilla game plus a runtime
client; remove the client and Elden Ring is exactly as you left it.

## A run, start to finish

You wake up at Roundtable Hold. One region is open (Limgrave, on the default
`spine` order; set `num_regions_order: rolled` if you'd rather it be random).
Warp in and play Elden Ring: fight, loot, buy things. Every pickup fires off
a check.

Items stream back in through the game's own bottom-center event banner. Most
are gear, consumables, runes. The ones you're really hunting are Region Locks.
Each one that lands opens a new region -- often somewhere you'd never go "next"
in a normal playthrough, and that's the fun of it.

**The goal**, by default, is to hold every Region Lock that's in play
(`ending_condition: region_locks`). Open every kept region and you've won.
The goal region -- Leyndell -- is always among the kept ones, so a seed is
always winnable. The alternative, `ending_condition: great_runes`, asks you
to collect a set number of Great Runes instead.

## Things that will confuse you the first time

**You got kicked out of a region.** You wandered (or warped) into a region you
haven't unlocked, and the client warped you back out. This is the Shattering
working as intended -- sealed means sealed, not honor-system. Come back when
its Lock arrives.

**You received something you can't use yet.** Normal. The multiworld doesn't
care about your timing -- you might get a Great Rune before its region is open,
or a colossal weapon at level 12. It's banked; it'll matter later. (Weapon
stat requirements are waived in v0.2, so gear at least never rots on stat
checks.)

**Enemies are scaled -- and late regions hit harder.** Scaling is always on and
keyed to your progression, not to vanilla's intended order. A region you unlock
late is tuned tougher, even if it's "early" territory like the Weeping
Peninsula. If the Weeping Peninsula is wrecking you, you're probably not
undergeared -- you just unlocked it late. See "Enemy difficulty" below if you
want to reshape that.

**A pickup showed someone else's item name.** That chest held "Progressive
Sword" for a Hollow Knight player three worlds over. You sent it; something of
yours is out there in return. That's the multiworld doing its thing.

**A check gave you a Rune instead of an item.** About 1% of checks pay out a
Rune by design. Separately -- honesty time -- a small class of enemy-drop checks
can currently still hand you the *vanilla* Elden Ring item instead of the
Archipelago one. It cannot strand your run (those spots never hold progression),
but you might miss a filler item. Details in `KNOWN-ISSUES.md`.

**Where do I even stand with my checks?** Press **F6**. The in-game tracker
lists checks by region with done/total counts, dims locked regions, and names
the item that opens each one.

## The options that change how it plays

The yaml's comments document every option; these are the ones that reshape the
run rather than tune it.

- **`num_regions`** -- the size of the Shattering. The one option that turns
  Elden Ring into an Archipelago game. 4 for an evening, 0 (the shipped
  default) for everything.
- **`natural_progression`** -- the Shattering's opposite. Off (default) you get
  Region Locks. On, the whole map is in play from the start and regions open on
  their *real* vanilla keys -- Dectus halves, the Haligtree medallion, boss
  remembrances -- still shuffled into the multiworld, so they can be anywhere
  and anyone's. A few chokepoints are kept (the DLC behind Mohg, Mt. Gelmir
  behind Liurnia and the Academy, Rauh behind Shadow Keep, the capital behind
  Altus and two Great Runes). `num_regions` is ignored when this is on. Pick it
  if you want vanilla's shape with Archipelago's item flow rather than a
  region-lock progression graph.
- **`ending_condition`** -- hold every kept Region Lock (default), or chase
  `goal_great_runes` Great Runes instead.
- **`progression_surface`** -- which categories of location are allowed to
  hold progression items. Shrink the list for a tighter, more predictable
  hunt; widen it to scatter key items further afield.
- **`pool_builder_intensity`** -- how good gear must be to count as juice.
  A HIGHER floor means LESS gear, not better. See "What fills your junk checks".
- **`curated_filler`** -- what fills your junk checks. See "What fills your
  junk checks" below; the short version is that about two fifths of your
  filler is already real gear, and this recipe is the dial.
- **`dungeon_sweep`** -- what killing a dungeon boss hands you. `all` (default)
  sweeps that dungeon's remaining checks so you never crawl back for two chests
  you missed; `bosses` extends it to field bosses; `minidungeons` narrows it;
  `none` turns it off entirely and you collect every check where it lies. The
  boss's *own* reward is a normal check either way -- it is never part of a
  sweep -- so turning this off never costs you an item, only the convenience.
- **`reroll_enemy_drops` / `reroll_infinite_shop_stock`** (both on) -- reroll
  what farmable enemies drop and what unlimited-stock merchants sell. One-time
  drops -- the actual checks -- are untouched; this randomizes the repeatable
  economy around them.
- **`filler_foreign_pct` / `local_item_only`** -- multiworld manners: how much
  of your filler other worlds may draw from, and whether your real vanilla
  items always stay in your own world.
- **`enable_dlc`** -- the Shadow of the Erdtree regions join the region pool
  and behave like any other region: their Lock arrives, their graces light,
  you warp in. You never fight Mohg to get there. Off in the shipped yaml and
  experimental in v0.2; base game is the supported way to play.
  (`dlc_only: true` goes further and seals the whole base game instead -- so
  base-only NPC content is gone even where that NPC's story continues into the
  DLC; e.g. Brother Corhyn's only pooled item, his Bell Bearing, lives in base
  Leyndell and so simply isn't part of a `dlc_only` seed.)
- **`death_link`** -- your deaths are shared with the multiworld, and theirs
  with you. You know whether you want this.

### Enemy difficulty

Three of them, all `0`-`100`, all defaulting to a standard curve, and on all
three **higher is harder**:

```yaml
minimum_enemy_difficulty: 0     # how hard the EASIEST enemies are
maximum_enemy_difficulty: 100   # how hard the TOUGHEST ones get
difficulty_ramp_speed: 0        # how QUICKLY you reach them
```

The game has its own ladder of enemy-strength settings, and the client picks a
rung per region based on how deep that region sits in *your* seed's chain. The
shallowest is roughly vanilla; the deepest is about **7.4x enemy HP**, the
strength vanilla saves for its endgame. Rune rewards never change, at any
setting -- a scaled-up enemy is worth exactly what it was worth before.

- **`minimum_enemy_difficulty`** raises the floor, so nowhere stays a walkover.
  At `50`, nothing in the game sits below roughly 4x enemy HP however early you
  got there. Use it if the opening hours feel like a formality.
- **`maximum_enemy_difficulty`** lowers the top. Worth a thought on a **short
  seed**: with `num_regions: 4` your deepest region arrives fast but is still
  the end of your run, so it's scaled like one -- you can meet endgame-strength
  enemies holding a +6 weapon. Capping keeps the curve's shape and lowers its
  top. (Below `100` this needs an up-to-date client; an older one refuses the
  seed and says so rather than ignoring your cap.)
- **`difficulty_ramp_speed`** changes *when* the climb happens, not how high it
  goes. At `50` you're at maximum from about halfway and everything after is
  equally hard. It compresses the curve rather than steepening it.

They stack. `minimum_enemy_difficulty: 40` with `difficulty_ramp_speed: 60`
starts genuinely dangerous and is at full strength before the midpoint; add
`maximum_enemy_difficulty: 60` and it's a flat, consistently tough run instead
of an escalating one.

> **Renamed in v0.2.12.** These were `completion_scaling_floor` and
> `completion_scaling_ramp`. An older yaml using those names stops generation
> with a message -- it won't silently ignore them. The ramp also **flipped
> direction**: the old `completion_scaling_ramp: 25` is the new
> `difficulty_ramp_speed: 75`.

## What fills your junk checks

Most checks in a seed hand out something forgettable. This is the system that
decides what kind of forgettable -- and by default, a decent chunk of it isn't
forgettable at all.

Every check that would otherwise pay a Rune, plus every check holding a junk
consumable, goes into one pool called the filler tail. One recipe spends that
whole pool: `curated_filler`. The shipped weights:

    juice: 42          # real gear -- weapons, armor, spells, talismans,
                       # Ashes of War, best-first by curated tier
    stones: 29         # Smithing Stones
    somber_stones: 6   # Somber Smithing Stones
    runes: 10          # Golden / Lord's / Hero's / Numen's Runes
    throwables: 6
    pots: 4
    greases: 3
    foods: 2
    boluses: 1

Weights are relative, not percentages -- they need not sum to anything. On the
shipped recipe roughly **two fifths of your filler tail is real gear**, drawn
best-first from a curated PvE tier list. That is the default. You do not turn
it on.

The upgrade economy is paid first. `stones`, `somber_stones` and `runes` are a
reservation taken off the top and never scaled down; everything else splits
what is left. If your seed's tail is too small for that reservation to buy a
useful number of stones, the generation log says so by name -- it does not
refuse to build, so a very small seed ships lean rather than not at all. Most
seeds also place a batch of low-tier smithing stones within reach of the start,
enough for an early +3 (it is clamped to what the pool can spare, so a recipe
with no stones in it has none to place).

Three ways to change the mix:

- **Reweight the recipe.** More gear: raise `juice` -- up to a point, since the
  curated list holds about 1013 items good enough to qualify and the default
  already draws 858 of them; past that the extra slots become junk and the log
  says so. More upgrade materials: raise `stones`. Want your junk to stay junk? Weight `junk`, which means
  "keep whatever the check already paid". An empty recipe is honoured -- and
  warns loudly, because it means no gear and no upgrade economy at all.
- **Steer the gear with `pool_builder_pct_*`.** These decide WHICH gear. They
  are proportions relative to each other, so `{weapons: 3, spells: 1}` and
  `{weapons: 75, spells: 25}` are the same request. **They can never add gear,
  only cost it.** Each category is
  drawn from a curated list with a limited number of items good enough to
  qualify -- spells have the fewest -- and asking for more than a category has
  turns the shortfall into junk. Leaving them all at 0 (the default) fills
  best-first from every category and yields the *most* gear;
  `{weapons: 3, spells: 1}` yields about a quarter less. The generation log
  names any shortfall.
- **Raise the bar with `pool_builder_intensity`.** This decides how GOOD a piece
  of gear has to be before it counts as `juice` at all:

      max     (default)  legendary, rare and the tier below -- 1013 items
      high               legendary and rare -- 536 items
      normal             legendary only -- 149 items

  **Read the direction carefully, because the name points the wrong way: a
  higher floor gives you LESS gear, not better gear.** It shortens the list
  without changing how many gear slots the recipe asks for, so the generator
  runs out and the leftover slots become ordinary junk -- the log says so by
  name when it happens. Measured on one seed: `max` put 1518 catalog-grade
  items in the pool, `high` 872, `normal` 230. `normal` is the connoisseur
  setting and you pay for it in volume everywhere else. If what you want is
  *more* gear, raise `juice` in the recipe; that is the dial for quantity.

Filler gear is marked useful, not progression, and none of these dials can put
a progression item into the tail or take one out of it -- so no amount of recipe
tinkering can make a seed unwinnable. (On a default seed the Region Locks are
the progression items. Under `natural_progression` the real vanilla keys are
instead, and they are placed as progression outside this system.)


A lot of what you might expect to toggle here is simply how v0.2 plays --
fixed, not configurable. Checks pay out real shuffled Elden Ring items. You
start with a Lantern, Torrent, flasks, all map fragments, immediate leveling,
and buyable
Stonesword Keys, because region-hopping out of order breaks the vanilla
drip-feed of those things. And smithing upgrades climb a uniform 2-stone
ladder instead of vanilla's 2/4/6, so leveling a fresh weapon stays cheap;
on top of that, every seed reserves upgrade stones in its item pool and
guarantees a batch of low-tier smithing stones (regular and somber) placed
within reach of your starting area -- enough to take an early weapon to +3.
The bottom of the shipped yaml lists all of these -- don't add them back as
keys. Archipelago warns about an unknown key and then generates without it, so
the option you thought you set simply would not exist.

## When something looks wrong

Check `KNOWN-ISSUES.md` first -- it lists both the active bugs and the
by-design behaviors that get reported as bugs. If it's not there, it's worth
reporting: bring your yaml and the spoiler log.

Now go find out which region the seed decided you deserve first.
