# Elden Ring Archipelago -- Player Guide (v0.2)

You are installed and connected -- if not, the [setup guide](SETUP.md) gets you
there in about 15 minutes; this guide won't repeat it. This is about what
happens after you press New Game: how a run actually plays, and the handful of
things worth understanding before they confuse you.

## The mental model

Every meaningful item pickup in the Lands Between -- corpse loot, chests, boss
drops, shop slots -- is a **check**. When you grab one, the item that was there
goes out to whoever it belongs to in the multiworld, and your own items arrive
in your inventory mid-session, from your checks or from someone else's game
entirely. (Solo works the same; you're just both ends of the pipe.) On top of
that, the world is **Shattered**: carved into major regions -- 17 in the base
game, 31 with the DLC -- each sealed behind an Archipelago item called a
**Region Lock**. You start at Roundtable Hold with one region already open, and
the map unfolds as Locks arrive. None of this touches your game files: it's the
vanilla game plus a runtime client.

## Your first ten minutes

You wake up at Roundtable Hold with one region open -- Limgrave on the default
`spine` order, or somewhere random if you set `num_regions_order: rolled`.
Its graces are lit on your map. Warp in.

You start with more than a vanilla Tarnished, on purpose -- region-hopping out
of order breaks the vanilla drip-feed of these things, so v0.2 just hands them
to you:

- **A Lantern** (hands-free pouch light -- it replaced the starting Torch of
  earlier builds), **Torrent**, **flasks**, and the **Whetstone Knife**.
- **All map fragments** -- every kept region is readable from minute one.
- **Immediate leveling** -- no waiting to meet Melina.
- **Buyable Stonesword Keys**, so imp statues never dead-end you.
- **No weapon stat requirements** -- any gear the multiworld sends is usable
  immediately, whatever your stats.
- **A flattened smithing ladder** -- upgrades cost a uniform 2 stones per level
  instead of vanilla's 2/4/6, and every seed guarantees a batch of low-tier
  smithing stones (regular and somber, enough for an early +3) within reach of
  your starting area.

Then just play Elden Ring: fight, loot, buy things. Your first checks are
whatever you touch first in your open region -- every pickup and shop slot
fires one. Received items appear in the game's own bottom-center event banner.

## The core loop

Play your open region and clear its checks. Most of what comes back is gear and
consumables; the ones you're really hunting are **Region Locks**. When one
lands, that region opens: **all of its graces light up on your map, and you
warp in** -- often somewhere you'd never go "next" in a normal playthrough,
which is the fun of it.

Internalize this, because it's the part everyone gets wrong at first: **the
Lock is the only door.** Vanilla routes and vanilla key items gate *nothing*
here. You never need the Rold Medallion to reach the Mountaintops of the
Giants; with the DLC on, you never fight Mohg to enter the Land of Shadow. The
Lock arrives, the graces light, you warp in. And it cuts both ways: walk (or
warp) into a region whose Lock you don't hold, by any route, and the client
warps you back to Roundtable Hold. Sealed means sealed, not honor-system.

### The two exceptions

Two vanilla-flavored gates survive, and both are layered **on top of** the
region's own Lock, never in place of it:

- **Raya Lucaria Academy** also needs the **Academy Glintstone Key**, shuffled
  into the item pool like anything else. The Academy's graces light when the
  key arrives.
- **Leyndell** also needs **Great Runes** -- 2 by default
  (`leyndell_runes_required`), echoing the vanilla capital gate. The capital's
  graces light once enough have arrived.

Neither can strand a seed: the key is always placed reachably, and the rune
requirement is auto-clamped to the Great Runes actually in your seed.

### Reading the tracker

Press **F6** (or use the **Tracker** entry in the overlay menu bar). It lists
your checks grouped by region with done/total counts, highlights your current
region, dims the regions you haven't unlocked, and names the item that opens
each one -- so you always know what you're waiting on. If a grace ever hasn't
lit in a freshly opened region, `/warp <id>` teleports you in directly.

### Dungeon sweeps

Kill a dungeon's boss and its remaining checks register automatically. No
crawling back through a catacomb for the two chests you missed -- the boss
kill sweeps the dungeon.

### Enemy scaling

Progression-based enemy and boss scaling is **always on** -- it's keyed to how
far you've progressed, not to vanilla's intended order. A region you unlock
late is tuned tougher, even if it's "early" territory. If the Weeping Peninsula
is suddenly wrecking you, you're probably not undergeared -- you probably just
unlocked it late. That's the system working.

## DeathLink

Off by default; `death_link: true` in your yaml turns it on. Your deaths are
shared with the multiworld and theirs with you, in both directions. You know
whether you want this. One mercy: a DeathLink death **keeps your Runes** --
you don't drop your held Runes to someone else's mistake, so there's no
bloodstain scramble after a death you didn't cause.

## Goals -- when you win

- **`ending_condition: region_locks`** (default) -- hold every Region Lock in
  play. Open every kept region and you've won.
- **`ending_condition: great_runes`** -- additionally collect
  `goal_great_runes` Great Runes. You must *hold* the runes; killing the boss
  that vanilla-drops one is not enough, because the runes are shuffled. The
  count is clamped to what's reachable this seed.

Run length is **`num_regions`**: `0` (the shipped default) keeps everything in
play -- the full Shattering -- while a small number like `4` seals the rest for
a tight evening run. The goal region, Leyndell, is always among the kept
regions, so a seed is always winnable.

## "That's not a bug"

Things that get reported as bugs but are the mod working as designed. The
authoritative list lives in [Known Issues](KNOWN-ISSUES.md); the ones you'll
actually hit:

- **You got warped back to Roundtable Hold.** You entered a region whose Lock
  you don't hold. Come back when it arrives.
- **A pickup showed someone else's item name.** That chest held another
  player's item; you sent it, and something of yours is out there in return.
  That's the multiworld doing its thing.
- **You received something you can't use yet.** Normal -- the multiworld
  doesn't care about your timing. A Great Rune before its region is open, a
  colossal weapon at level 12 (usable anyway, since stat requirements are
  waived) -- it's banked; it'll matter later.
- **A check gave you a Rune instead of an item.** About 1% of checks pay out a
  Rune by design.
- **A Golden Seed or Sacred Tear check gave a "Progressive Flask Upgrade."**
  That's `progressive_flasks` (on by default): flask upgrades arrive on a
  steady cadence instead of 13 silent flat pickups. You still spend them at a
  grace as usual.
- **Great Runes aren't marked progression.** They're "useful" unless your goal
  is `great_runes`, in which case they become progression and are placed
  reachably.
- **`merchant_bell_logic` does nothing.** It's inert in v0.2 -- registered
  only so configs stay forward-compatible. Leave it off; you lose nothing.

## When something's actually wrong

Check [Known Issues](KNOWN-ISSUES.md) first -- it lists the active bugs (none
of which can strand a base-game run) alongside the by-design behaviors above.
If what you're seeing isn't there, it's worth reporting: bring your yaml and
the spoiler log. One thing not to report: anything from a session where the
client log said `VERSION MISMATCH` -- that means your apworld and client DLL
came from different releases, and nothing from that session is a real bug.
Redownload both from the same release tag first.

## FAQ

**Do I need to know Archipelago to play this?**
No. Connect, play Elden Ring, pick things up. The multiworld plumbing runs
itself; the tracker (F6) tells you where you stand.

**Can this be played solo?**
Yes -- a solo base-game run is the recommended way to play v0.2. Same loop,
you're just both ends of it.

**A region's Lock hasn't shown up. Am I stuck?**
No. Locks are placed by Archipelago logic so the seed is always completable --
keep clearing the checks you *can* reach (the tracker shows what's left), and
the Lock will come out of one of them, or out of another player's world.

**Do I need the DLC?**
Only if you enable the DLC regions (`enable_dlc`). They're experimental in
v0.2 and off by default; base game is the supported way to play. When enabled,
DLC regions unlock exactly like base ones -- Lock arrives, graces light, warp
in. No Mohg fight.

**Can I have randomized enemies or a random starting class too?**
Yes, by stacking thefifthmatt's randomizer on top -- with its *item*
randomization OFF. Full recipe in
[enemy and starting-class randomization](ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md).

**Why can't I toggle item shuffle / dungeon sweeps / the starting gifts?**
They're how v0.2 plays -- fixed, not configurable. The option surface is 19
tunable options; everything else is frozen to one good setting, listed at the
bottom of the shipped `EldenRing.yaml`. Don't add the frozen ones back as yaml
keys: Archipelago ignores unknown keys without an error, so the option you
thought you set simply wouldn't exist.

**Does this touch my saves or game files?**
No files are modified, ever -- it's all runtime. The client uses its own save
(`AP_me3.sl2`), so your normal characters are untouched. Remove the client and
Elden Ring is exactly as you left it.

Now go find out which region the seed decided you deserve first.
