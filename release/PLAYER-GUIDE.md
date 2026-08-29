> 🛑 **THIS FILE IS NOT SHIPPED, AND NOTHING LINKS TO IT.**
>
> The player guide that reaches players is **`Elden-Ring-Archipelago-Player-Guide.md` in the repo
> root** — `package_release.ps1` marks it `required = $true`, and README / SETUP.md both point at it.
> This file is packaged by nothing and referenced by nothing; the two are forked copies of the same
> document that have diverged.
>
> It cost something already: on 2026-07-27 the entire player-facing writeup of the new difficulty
> options was written *here*, and nobody would have read a word of it. `test_gf_player_guide.py` now
> gates the shipped one — it has no opinion about this file.
>
> **Update the root guide. Deleting or merging this one is Alaric's call, not a drive-by.**

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
game, 28 with the DLC -- each sealed behind an Archipelago item called a
**Region Lock**. You start at Roundtable Hold with one region already open, and
the map unfolds as Locks arrive. None of this touches your game files: it's the
vanilla game plus a runtime client.

## Your first ten minutes

You wake up at Roundtable Hold with one region open. Which one is random, and it
is drawn weighted by size, so the big regions (Liurnia, Altus, Caelid, Limgrave)
come up most often. Its graces are lit on your map. Warp in.

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
  into the item pool like anything else.
- **Leyndell** also needs **Great Runes** -- 2 by default
  (`leyndell_runes_required`), echoing the vanilla capital gate.

🛑 **Neither of these lights its graces for you.** They sit behind a wall the
*game* enforces, so the grace bundle is withheld while that wall is armed --
the Lock arrives and nothing visibly happens. Open them the vanilla way: the
Academy seal with the key, the capital's main gate from Altus with the runes
in hand; then touch the graces yourself. (The Shunning-Grounds sewer is part
of Leyndell since v0.4.10 -- once the capital opens, the well is yours.)

Neither can strand a seed: the key is always placed reachably, and the capital's
rune requirement is FLOORED at the vanilla 2 -- when the seed cannot supply that
many, the pool is topped up rather than the gate lowered.

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

Under the hood the game has its own ladder of enemy-strength settings, and the
client picks a rung per region based on how deep that region sits in *your*
seed's chain. The shallowest is roughly vanilla; the deepest is about **7.4x
enemy HP**. Your rune rewards are never touched, at any setting -- a scaled-up
enemy is worth exactly what it was worth before.

#### Making it harder (or gentler early)

Three yaml knobs, all `0`-`100`, and on all three **higher is harder**:

```yaml
minimum_enemy_difficulty: 0     # how hard the EASIEST enemies are
maximum_enemy_difficulty: 100   # how hard the TOUGHEST ones get
difficulty_ramp_speed: 0        # how QUICKLY you reach them
```

Leave all three alone for the standard experience.

**`minimum_enemy_difficulty`** raises the floor. At `0` your first region is
about as weak as vanilla. At `50` nothing in the game sits below roughly 4x
enemy HP, however early you reached it. At `100` everything is at maximum from
your very first region -- the whole world at endgame strength.

Use it if the early game feels like a formality, or if you keep unlocking
"early" regions late and steamrolling them.

**`difficulty_ramp_speed`** changes *when* the climb happens, not how high it
goes. At `0` the increase is spread evenly across your whole run, so your last
region is the first to hit maximum. At `50` you're at maximum from about
halfway, and everything after that is equally hard. At `100` you're at maximum
almost immediately.

Use it if you like the peak but want to get there sooner. Note it **compresses**
the curve rather than steepening it: the back half of your run flattens out at
full difficulty instead of continuing to climb.

**`maximum_enemy_difficulty`** lowers the top. At `100` your deepest region
reaches the game's own maximum -- roughly 7.4x enemy HP, the strength vanilla
reserves for its endgame. At `50` nothing in the run goes above about 4x.

This one is worth a thought on a **short seed**. With `num_regions: 4`, your
deepest region arrives fast, but it's still "the end of your run" and gets
scaled like one -- so you can meet endgame-strength enemies holding a +6 weapon.
Capping keeps the curve's shape and just lowers its top.

> Setting this below `100` needs an up-to-date client. An older one will refuse
> the seed and tell you why, rather than quietly ignoring your cap.

All three stack. `minimum_enemy_difficulty: 40` with `difficulty_ramp_speed: 60`
is a run that starts genuinely dangerous and is at full strength before the
midpoint; add `maximum_enemy_difficulty: 60` and it's a flatter, consistently
tough run rather than an escalating one. All at their defaults is the standard
experience.

> **Renamed in this build.** These were `completion_scaling_floor` and
> `completion_scaling_ramp`. If you have an older yaml using those names,
> generation will stop and tell you -- it won't silently ignore them. Note that
> the ramp also **flipped direction**: the old `completion_scaling_ramp: 25` is
> the new `difficulty_ramp_speed: 75`.

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
No *game* files are modified -- no regulation, no maps, no scripts, nothing on
disk that Elden Ring ships. It is all runtime. Two honest caveats about saves,
though. The client does write a small identity marker into your character's
save data; that is how a reconnect works out which character it is looking at.
And the separate save file (`AP_me3.sl2`) is the `me3` profile's doing, not
ours -- load our dll through another launcher and your Archipelago character is
created in your ordinary save instead. On first use, me3 creates `AP_me3.sl2`
by copying `ER0000.sl2`, so existing vanilla characters also appear in the AP
menu; they are copies, not shared slots. A new AP character will not appear in
a vanilla launch. Do not load a copied vanilla character while connected. The
shipped profile needs no Alt Saves DLL. Remove the client and Elden Ring plays
exactly as you left it.

Now go find out which region the seed decided you deserve first.
