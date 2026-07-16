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
Peninsula.

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
- **`ending_condition`** -- hold every kept Region Lock (default), or chase
  `goal_great_runes` Great Runes instead.
- **`progression_surface`** -- which categories of location are allowed to
  hold progression items. Shrink the list for a tighter, more predictable
  hunt; widen it to scatter key items further afield.
- **`curated_filler` / `pool_builder_pct_*`** -- shape the junk end of the
  pool. The recipe weights which consumables fill it; the percentages trade
  part of it for real gear (weapons, armor, talismans, spells, Ashes of War),
  best-first by community tier list. Your junk checks are less junky.
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
  (`dlc_only: true` goes further and seals the whole base game instead.)
- **`death_link`** -- your deaths are shared with the multiworld, and theirs
  with you. You know whether you want this.

A lot of what you might expect to toggle here is simply how v0.2 plays --
fixed, not configurable. Checks pay out real shuffled Elden Ring items.
Killing a dungeon's boss sweeps its remaining checks, so there's no crawling
back through a catacomb for two chests you missed. You start with a Torch,
Torrent, flasks, all map fragments, immediate leveling, and buyable
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
