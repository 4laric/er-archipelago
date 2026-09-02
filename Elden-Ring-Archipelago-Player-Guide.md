# Elden Ring Archipelago -- Player Guide

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

- **Raya Lucaria Academy** also needs the **Academy Glintstone Key**, shuffled
  into the item pool like everything else.
- **Leyndell** also needs **Great Runes** -- two by default
  (`leyndell_runes_required`).
- **The Shunning-Grounds sewer is part of Leyndell** (merged in v0.4.10): once
  the capital opens, the well is yours, and the sewer's graces arrive with the
  Leyndell bundle.

🛑 **Neither of these lights its graces for you, and this is the single most
common "my Lock is broken" report.** They sit behind a wall the *game* enforces,
so their grace bundle is withheld while that wall is armed -- the Lock arrives
and nothing visibly happens. You open them the vanilla way and touch the graces
yourself: the Academy seal with the key, the capital's main gate walking in from
Altus with your Great Runes. A grace you touch is the warp unlock, and it sticks.

`leyndell_runes_required: 0` is the only setting that changes any of this, and
only for the capital.

None of the three can make a seed unbeatable: the key is always placed somewhere
you can reach, and the capital's rune requirement is floored at the vanilla two
with the pool topped up when a seed cannot supply them.

That second idea is the whole trick: Elden Ring's famously go-anywhere map
becomes a progression puzzle, one region at a time. The `num_regions` option
controls how many regions are kept -- 4 is a tight ~4-hour run, 6 is the
shipped default, higher is longer, and 0 keeps everything in play for the full
Shattering: 16 regions in the shipped base-game config, 28 with the DLC on.

None of this touches your game files. It's the vanilla game plus a runtime
client; remove the client and Elden Ring is exactly as you left it.

## A run, start to finish

You wake up at Roundtable Hold. One region is open to start, and which one it is
is random -- as is the set of regions your seed keeps. Those are two independent
draws: the opening region is picked on its own, not as "the first" of the kept
set. `num_regions_order` chooses between them: `rolled` (the default) draws the
kept regions at random, and `vanilla_order` takes the first N along the region
spine instead, deterministically. Neither decides where you open.
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
to hold Great Runes as well. **Any distinct Great Runes count**: the default
is any four of all seven, and no particular named rune is mandatory. The
client reports the count and the full eligible set when you connect.

**Which boss actually ends it** is a separate knob, `goal`. Left on `auto` it
works itself out: if your seed keeps both Farum Azula and Leyndell you finish
at the real ending -- Godfrey/Hoarah Loux, then the Elden Beast. Otherwise it
is the major bosses of the deepest region you kept. Set `goal:
promised_consort` and the run ends on Promised Consort Radahn instead, and
Enir Ilim is forced into your seed to guarantee he is there -- worth knowing,
because on a full base+DLC seed `auto` always stops at the Elden Beast and
leaves the entire DLC optional.

## Things that will confuse you the first time

**The AP launch shows your vanilla characters.** This is expected the first
time you use the shipped `me3` profile. To create `AP_me3.sl2`, me3 copies your
existing `ER0000.sl2`, including its character list. The files are separate
after that copy: a new character created through `ap.me3` is not visible when
you launch vanilla Elden Ring. Seeing the old character names in both menus
does not mean the two launches still share a save.

Whether that separation happens depends on how you launched, not on the
client. The shipped `me3` profile asks for `AP_me3.sl2`; other loaders do not --
including thefifthmatt's randomizer, which is a supported way to run us -- so
on those the AP character is created in your ordinary Elden Ring save. The Alt
Saves DLL is not needed when launching the shipped `ap.me3` profile.

**If that has happened, do not load your ordinary characters while connected.**
The client cannot tell one of your existing characters from a new Archipelago
one: a character with no Archipelago marker in it reads as *fresh*, and a fresh
character is owed every item the room has sent you so far. Load a real character
with the client connected and it may be granted that backlog. Play the
Archipelago character, and only that one, in the modded launch.

To check the separation, create a disposable character through `ap.me3`, quit
cleanly, then open Elden Ring **normally**, with no mods. The disposable
character should not appear there. To separate another launch path -- and for
a save backup that makes the whole question recoverable -- see
`ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md` in the release folder.

**You got kicked out of a region.** You wandered (or warped) into a region you
haven't unlocked, and the client warped you back out. This is the Shattering
working as intended -- sealed means sealed, not honor-system. Come back when
its Lock arrives.

**You received something you can't use yet.** Normal. The multiworld doesn't
care about your timing -- you might get a Great Rune before its region is open,
or a colossal weapon at level 12. It's banked; it'll matter later. (Weapon
stat requirements are waived, so gear at least never rots on stat
checks.)

**Enemies are scaled -- and late regions hit harder.** Scaling is on by default
(`enemy_scaling: false` turns it off) and keyed to your progression, not to
vanilla's intended order. A region you unlock
late is tuned tougher, even if it's "early" territory like the Weeping
Peninsula. If the Weeping Peninsula is wrecking you, you're probably not
undergeared -- you just unlocked it late. See "Enemy difficulty" below if you
want to reshape that.

**You burned the Erdtree and Leyndell changed.** Elden Ring has two capitals
on the same spot -- Leyndell, Royal Capital before the burn, the Ashen Capital
and the Elden Throne after -- and vanilla only ever goes one way. Under region
locks the Farum Azula Lock can reach Maliketh long before you are done with the
Royal Capital, so this is easy to trip by accident.

You have not lost it. `capital_reconciler` is on by default and keeps that
switch matched to where you are standing, so the Royal Capital comes back. What
the burn *does* take is Leyndell's grace warp points, which means right after it
you cannot fast-travel in even holding the Leyndell Lock.

**Fast-travel somewhere first, then walk in.** The reconciler decides which
capital exists from where you WARP to, so warping anywhere that is not the Ashen
Capital or the Elden Throne is what puts the Royal Capital back -- Roundtable or
any Altus grace. Standing in Altus is not enough on its own; the switch is only
reconsidered on a warp. Then walk to the main gate -- the Great Rune wall works
exactly as before -- and touch a grace to get the warp back. Warping to an Ashen
grace returns you to the finale whenever you want it.

🛑 **Known bug: sometimes one warp is not enough.** The switch is written during
the warp and the write can lose a race with the map load, and nothing retries it
unless you are already inside the capital. If you get to the main gate and it is
still the Ashen Capital, warp again -- each warp is a fresh attempt. If several
warps in a row will not shift it, that is worth a bug report with your client
log attached; grep it for `capital warp intercept` and tell us whether the line
says `STUCK` or `PENDING`.

**A pickup showed someone else's item name.** That chest held "Progressive
Sword" for a Hollow Knight player three worlds over. You sent it; something of
yours is out there in return. That's the multiworld doing its thing.

**A vanilla item you went looking for is nowhere in the seed.** Count the
crystal tears, the sorceries, the Ashes of War, and you will come up short of
vanilla. **The item pool is curated, and that is not a setting you turned on.**
Three separate things are doing it, and none of them is a bug:

- **The junk end of the pool is spent by a recipe.** Every check that would
  have paid a Rune or a junk consumable goes into one pool, and `curated_filler`
  spends the whole thing -- by default about two fifths of it on real gear. The
  vanilla consumable spread is what got traded away to buy that. Full writeup
  in **"What fills your junk checks"** below; that section is where to go before
  you conclude something is missing.
- **Farmable enemy drops were never checks to begin with.** A drop with no
  one-time flag on it cannot be a check in any randomizer, so those slots stay
  outside the pool -- and we reroll their contents per seed. Vanilla rates,
  different consumables.
- **A curated set of tears and bell bearings is force-fed in.** The presence
  floor guarantees those specific ones exist even when their home region is
  sealed. It is a floor, not a promise about everything else.

If an item you want is not in your seed, that is the system working. Bring a
report when a *check* misbehaves, not when the pool is smaller than vanilla's.

**A check gave you a Rune instead of an item.** About 1% of checks pay out a
Rune by design. Separately -- honesty time -- a small class of enemy-drop checks
can currently still hand you the *vanilla* Elden Ring item instead of the
Archipelago one. It cannot strand your run (those spots never hold progression),
but you might miss a filler item. Details in `KNOWN-ISSUES.md`. Note this is a
real defect and the entry above is not -- a wrong item *in a check* is worth
reporting; an item absent from the pool is the curation doing its job.

**Where do I even stand with my checks?** Press **F6**. The in-game tracker
lists checks by region with done/total counts, dims locked regions, and names
the item that opens each one. A check labelled **`(region unconfirmed)`** has
been placed under the best region estimate available, but its exact region has
not yet been verified. It cannot hold a progression item, so an imperfect
estimate there cannot strand your run.

### Region Lock hints

Open the tracker with **F6** when you need help finding your next Region Lock.
Its header shows your Lock-hint balance and the current price in **surface
checks**: progression-surface checks you complete earn that balance. The price
is calculated from the size of the seed's progression surface and the room's
hint-cost setting, so different seeds and rooms can quote different prices.

Choose **Hint next lock** to buy a hint for a still-sealed region whose Lock is
currently obtainable somewhere you have already opened. The button deliberately
does not reveal which Lock it selected until after the purchase; learning that
is what the hint buys. To investigate one particular region instead, expand its
tracker row and use that region's own hint button.

The purchase creates a normal Archipelago hint for the Lock, visible to the
room in its **Hints** tab. It spends the tracker's surface-check balance, not
Archipelago's normal hint points. If no eligible Lock can be found, keep
checking open regions. A Lock in another player's world is outside the
tracker's scout data and cannot use this button; use Archipelago's `!hint`
command for that rare case.

**The overlay is in the way.** Press **F5** to hide the client window, and
again to bring it back (**F6** does the same for the tracker). Both are on the
overlay's menu bar too, as `Hide (F5)` and `Tracker (F6)`. Hiding is only
hiding: the client keeps sending checks and granting items while it is off
screen. Grant notices still appear, deliberately -- for a few items the game
itself cannot announce, such as flask upgrades, that notice is the only sign
you got anything. And F5 does nothing while you are disconnected, so you can
never hide the connect form away from yourself.

## The options that change how it plays

The yaml's comments document every option; these are the ones that reshape the
run rather than tune it.

- **`num_regions`** -- the size of the Shattering. The one option that turns
  Elden Ring into an Archipelago game. 4 for an evening, 6 (the shipped
  default) for a full run you will actually finish, 0 for everything.
- **`natural_progression`** -- the Shattering's opposite. Off (default), you get
  Region Locks. On, the whole map is in play and regions open with their real
  vanilla keys, such as the Dectus halves, Haligtree medallion and boss
  remembrances. Those keys are still shuffled into the multiworld, so anyone
  can find them. A few chokepoints remain: the DLC behind Mohg, Mt. Gelmir
  behind Liurnia and the Academy, Rauh behind Shadow Keep, and the capital
  behind Altus and two Great Runes. This setting ignores `num_regions`. Pick it
  for vanilla's world structure with Archipelago's item flow.
- **`goal`** -- which boss ends the run. `auto` (default) derives it;
  `elden_beast` pins the real ending and forces no regions because the shuffled
  Ashen Capital Lock supplies the burn and finale; `promised_consort` ends on
  PCR and forces Enir Ilim kept; `malenia` forces Haligtree kept and starts you
  at Haligtree Canopy, leaving the full Loretta-to-Malenia route to clear. A
  goal your other options make unreachable fails generation instead of silently
  downgrading.
- **`ending_condition`** -- hold every kept Region Lock (default), or require
  Great Runes as well. `goal_great_runes` sets how many; the seed chooses which
  runes count, and the client names them when it connects (see "The goal"
  above). This combines with `goal`, so you need both the runes and the boss.
- **`progression_surface`** -- which categories of location are allowed to
  hold progression items. Your in-game tracker stars these, and a star means
  "a progression item can be here" -- yours or another player's -- not "your
  key is here". Shrink the list for a tighter, more predictable hunt; widen it
  to scatter key items further afield.
- **`progression_bias`** -- how strongly your Region Locks are pulled toward
  your own world. At 0 (default), every Lock is an ordinary multiworld item and
  can land in someone else's game. You may need another player to find your way
  into Liurnia; that is normal Archipelago progression. At 100, every Lock stays
  home. A value of 40 reserves about 40% for you. Locks still follow the same
  curated placement surface as other progression, keeping them on meaningful
  checks rather than random crafting materials. In a two-slot game, expect
  roughly half your Locks to travel at bias 0; more slots mean more travel.
- **`region_grace_unlock`** -- how many Sites of Grace a region unlock hands
  you. `all` (default) lights every warp point in the region; `entrance` lights
  only the way in and you walk to the rest.
- **`pool_builder_intensity`** -- how good gear must be to count as juice.
  A HIGHER floor means LESS gear, not better. See "What fills your junk checks".
- **`curated_filler`** -- what fills your junk checks. See "What fills your
  junk checks" below; the short version is that about two fifths of your
  filler is already real gear, and this recipe is the dial.
- **`dungeon_sweep`** -- what killing a boss hands you, as a ladder:
  `none` sweeps nothing and you collect every check where it lies;
  `minidungeons` sweeps catacombs, caves, tunnels and minor dungeons (~515
  checks); `all` adds legacy dungeons and castles (~1984); `bosses` (default)
  adds field bosses too (~3197). So `all` is the setting for "sweep the
  dungeons, leave the field alone". The boss's *own* reward is a normal check at
  every setting -- never part of a sweep -- so turning this down costs you
  convenience, not items.
  (Before 2026-07-29 the three non-`none` values were identical; the default is
  named `bosses` now because that is what they all did.)
  A handful of bosses are *fought* in a different region from the one their
  loot lies in -- the Golden Hippopotamus hands over Shadow Keep checks from
  Scadu Altus ground. If your seed keeps one of those regions and not the
  other, that boss's sweep is left out rather than shipped as a payout you
  could never trigger. You collect its checks on foot instead; nothing is
  missing from the seed.
- **`full_area_sweeps`** (off) -- "does killing a boss give me *every* item in
  the area?" Off, bosses sweep ordinary loot but leave your
  `progression_surface` checks in place. With the default surface, you still
  walk to Golden Seeds, Sacred Tears, Scadutree Fragments and Revered Spirit
  Ashes. Turn it on and the whole reachable area arrives, including progression.
  A sweep can then hand you a Region Lock or another player's key early, but it
  cannot make an unreachable check required. Boss rewards, remembrances, Great
  Runes, quest and gate keys, and merchant stock are never swept.
- **`reroll_enemy_drops` / `reroll_infinite_shop_stock` / `reroll_mine_materials`**
  (all on) -- control the repeatable economy: farmable enemy drops, unlimited
  merchant stock, and respawning Smithing/Somber mine deposits. One-time drops
  and all actual checks remain untouched.

  Mine deposits remain respawning non-check pickups. Ancient Dragon capstones
  are excluded, and every deposit of the same original stone tier gets the
  same replacement for the seed. Shop rerolls cover 14 unlimited consumable
  shelves, including Kale's Glass Shards, Iji's Somber Smithing Stones, and the
  throwing-knife and poison-dart racks. Replacement prices follow the new item,
  so a cheap shelf cannot become an unlimited source of something game-breaking.
  **Arrow and bolt shelves are left alone**, preserving ammo supply lines.
- **`merchant_bells_on_talk`** (off) -- open a merchant's shop and their Bell
  Bearing goes to the Twin Maiden Husks, making that merchant's wares available
  at Roundtable Hold. You do not receive the bell itself; it remains a real
  multiworld item worth finding. Buying an item at the Husks fires the same check
  as buying it from the original merchant. This covers roving merchants and
  named vendors, but only their regular buy menus. Ash-of-War, tailoring and
  upgrade counters do not trigger it. Seeds using this option refuse clients
  that do not support it.
- **`keep_local`** -- multiworld manners, by category. List the kinds of item
  you want to stay in your own world and everything else still travels:
  `[consumables, crafting, upgrade_materials, runes]` keeps your crafting
  materials, smithing stones, ghost gloveworts, every consumable and every
  Golden Rune at home while your weapons, armour, talismans, spells, spirit
  ashes and ashes of war go out to other players. The YAML builder at
  <https://peliarch.ca/er/> lists every category. This matters most when your
  slot is much bigger than everyone else's. An Elden Ring seed can contain
  thousands of checks; without this option, a five-player game can turn into
  four people opening Elden Ring consumables.
- **`keep_local_rune_cap`** -- hold back rune items worth this many runes or
  fewer and let the big ones travel. The default, `12500`, keeps everything
  through Numen's Rune at home. `3000` keeps only the small change; `0` turns
  the cap off and allows every rune item to travel.
- **`local_item_only`** -- the blunt version of `keep_local`: every real
  vanilla item stays home. `exclude_local_item_only` lets categories back out
  again.
- **`filler_foreign_pct`** -- how much of your filler other worlds may draw
  from. It picks *which* filler at random per seed, so it can't be aimed;
  `keep_local` is the aimable version and they compose.
- **`confine_foreign_progression`** -- how much of *other* players' progression
  is held to your progression surface. At 100 (default) a foreign key can only
  sit on a starred check; lower it to spread foreign keys across more of your
  world. This setting changes placement only. A separate reservation pass sends
  partner worlds their share of useful Elden Ring gear regardless of this value.

> **The "anything anywhere" recipe.** If you come from classic ER item rando and
> want the old feel -- any check can matter, no curation steering keys onto
> bosses -- three settings do it: widen **`progression_surface`** to every
> category, set **`confine_foreign_progression: 0`** so other players' keys can
> land on any of your checks, and leave **`progression_bias`** at 0 so your own
> Region Locks travel freely. (Asked for on Discord, 2026-08-20 -- the builder's
> defaults are curated on purpose, but nothing about the old style is
> unsupported.)

**How much am I actually sending out?** The *Seed size* tab of the yaml builder
(<https://peliarch.ca/er/>) shows the ceiling as you move those options -- how many of your items are permitted to
leave. The real number needs a finished seed, and it's in the spoiler and the
generation log: `sent 431 of 1266 items into other worlds -- 388 filler, 43
useful`. The two differ a lot, because Archipelago spreads your items over
every world in proportion to open locations, so a big slot keeps most of its
own pool no matter what you set.
- **`enable_dlc`** -- the Shadow of the Erdtree regions join the region pool
  and behave like any other region: their Lock arrives, their graces light,
  you warp in. You never fight Mohg to get there. 🛑 **On in the apworld's own
  defaults and off in the shipped yaml** -- so a yaml that says nothing about it
  gets the DLC. Base game is the better-tested way to play.
  (`dlc_only: true` goes further and seals the whole base game instead -- so
  base-only NPC content is gone even where that NPC's story continues into the
  DLC; e.g. Brother Corhyn's only pooled item, his Bell Bearing, lives in base
  Leyndell and so simply isn't part of a `dlc_only` seed.)
- **`death_link`** -- your deaths are shared with the multiworld, and theirs
  with you. You know whether you want this.

### Enemy difficulty

These three settings run from `0` to `100`. Their defaults reproduce the
standard curve, and **higher is harder** for all three:

```yaml
minimum_enemy_difficulty: 0     # how hard the EASIEST enemies are
maximum_enemy_difficulty: 100   # how hard the TOUGHEST ones get
difficulty_ramp_speed: 0        # how QUICKLY you reach them
```

The game has its own ladder of enemy-strength settings. The client picks a rung
for each region based on its depth in *your* seed's chain. The shallowest is
roughly vanilla. The deepest has about **7.4x enemy HP**, the strength vanilla
saves for its endgame. Scaling never changes rune rewards.

- **`enemy_scaling: false`** turns the whole system off. Every enemy keeps its
  vanilla strength, and the sliders below stop applying. This is not easy mode:
  randomization can still put a late-game area in front of you at level 20.
- **`minimum_enemy_difficulty`** raises the floor, so nowhere stays a walkover.
  At `50`, nothing in the game sits below roughly 4x enemy HP however early you
  got there. Use it if the opening hours feel like a formality.
- **`maximum_enemy_difficulty`** lowers the top. This is especially useful on a
  **short seed**. With `num_regions: 4`, your deepest region arrives quickly but
  is still scaled as the end of the run. A lower cap preserves the curve while
  avoiding endgame-strength enemies when you may still have a +6 weapon. Values
  below `100` require an up-to-date client; older clients refuse the seed rather
  than ignore the cap.
- **`difficulty_ramp_speed`** changes *when* the climb happens, not how high it
  goes. At `50` you're at maximum from about halfway and everything after is
  equally hard. It compresses the curve rather than steepening it.

They stack. `minimum_enemy_difficulty: 40` with `difficulty_ramp_speed: 60`
starts genuinely dangerous and is at full strength before the midpoint; add
`maximum_enemy_difficulty: 60` and it's a flat, consistently tough run instead
of an escalating one.

> **Renamed in v0.2.12.** These were `completion_scaling_floor` and
> `completion_scaling_ramp`. Generation rejects the old names instead of
> silently ignoring them. The ramp also **flipped direction**: the old
> `completion_scaling_ramp: 25` is the new
> `difficulty_ramp_speed: 75`.

### Making yourself stronger instead of the enemies weaker

The difficulty sliders above change the *enemies*.
`global_scadutree_blessing` changes *you*.

```yaml
global_scadutree_blessing: off   # off | player_only | scaled
```

Scadutree Blessing is the Shadow of the Erdtree upgrade track. Collect
Scadutree Fragments and rest at a grace to deal more damage and take less. In
vanilla, it works only inside the Land of Shadow.

- **`player_only`** makes it work **everywhere**, Limgrave included, driven by
  the fragments you're holding. Enemies are untouched, so this is a plain power
  boost -- at the cap you deal about 1.85x and take about 0.54x.
- **`scaled`** adds the per-DLC-region blessing floor on top, so a DLC region you
  unlock without any fragments still meets that area's expected blessing.

The curve is capped at blessing level 12 rather than the full 20: the last eight
levels cost half the total fragments for roughly 11% more damage.

> **Older clients did not apply this outside the DLC.** The current client
> applies the blessing as described above.

### Your weapons keep up on their own

```yaml
auto_upgrade: true   # the default -- this has been every seed's behaviour since v0.2
```

Any weapon the game **adds to your bag** is raised to the highest reinforcement
level you already hold on its smithing track. Normal and somber tracks remain
separate, and the client never downgrades a weapon. This applies to:

- an **AP grant** arriving from the multiworld,
- a **world pickup** -- chests, corpses, drops,
- and anything you **put down and take back**.

The last case is the catch-up move. A weapon received early stays at the level
you had at the time. To bring it to your current tier, drop it with **Leave**
and pick it back up. Do not use Discard; Discard destroys the weapon. Blacksmith
upgrades still work as in vanilla. Auto-upgrade only raises a weapon to a level
you have already reached on that track.

> If a dropped weapon ever seems to **vanish** on pickup instead, the client
> noticed: check the log for a `vanilla-suppress ... Rescue:` line. It names
> the item and the exact `!give` console command that returns it (it comes back
> at your current tier). Please also report it; that line is us hunting a rare
> pickup-identity bug, and a sighting is evidence.

A fully hands-off version, which upgrades weapons already **in your bag** when
your tier rises, is planned as a separate yaml option.

## How much of a region an unlock opens

When a region unlocks, it lights that region's Sites of Grace so you can fast
travel into it. By default it lights **all** of them -- which for Liurnia means
59 warp points at once, Caelid 38, Limgrave 28. That is convenient, and it also
makes a region you have never walked read as already explored.

Two smaller settings:

- **`landmarks`** -- one grace per sub-area, using the warp menu's own grouping.
  Liurnia comes out as Lake-Facing Cliffs, East Raya Lucaria Gate, Moonlight
  Altar and Ruin-Strewn Precipice: you can still cross a big region in a couple
  of hops without it being handed to you whole. About 50 graces across the map.
  It follows the menu rather than region size, so it is uneven on purpose -- a
  few regions (Gravesite, Scadu Altus, Weeping) have one sub-area and behave the
  same as `entrance`.
- **`entrance`** -- only the region's front door. Lake-Facing Cliffs for Liurnia,
  Church of Elleh for Limgrave, Gateside Chamber for Stormveil.

Every other grace is still there and still yours the moment you touch it, the
vanilla way.

This cannot strand you and cannot cost you an item. Region unlocks are still the
only progression, every check stays exactly where it was, and a grace you have
not been handed is reachable on foot. It is purely about pacing. Regions that
sit behind a wall the game itself enforces -- the Academy seal, the capital's
Great Rune gate, the sewer -- hand out nothing under either setting; you walk in
the way the game intends.

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
  "keep whatever the check already paid" -- though if what you actually want is
  the vanilla item spread back, `vanilla_pool: true` is the one switch that does
  all of it, floor included. An empty recipe is honoured -- and
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


A lot of what you might expect to toggle here is simply how this world plays --
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

**You are trapped, a grace did not light, or the map cannot get you out.** Open
`GETTING-UNSTUCK.md`. It walks through the built-in rescue console, including the guaranteed
Roundtable escape, finding a grace by name, restoring a missing grace flag, and locating the right
client log for either me3 or thefifthmatt's randomizer.

**Your checks send, but you never receive anything.** Sending works -- your
friends get your checks, the server shows them arriving -- and yet nothing ever
comes back to you. That one-directional shape is a fingerprint, not a
coincidence, and the rest of it is distinctive too: a check hands you a literal
item called "Archipelago Item" that looks like a spyglass, the game tells you
that you cannot hold more than one of it and that it cannot go to storage, and
you never got Torrent or the rest of your start items.

That is `RandomizerHelper.dll` loaded alongside our client. Both mods want the
same routine -- the one the game uses to put an item in your inventory -- and
whichever gets there first wins. Ours refuses to install rather than patch a
routine it no longer recognises, because guessing wrong in the function that
grants items is how saves get corrupted. Checks keep working because they are
detected a different way entirely, which is exactly why the failure is
one-directional.

**Unload the dll.** Turning off its auto-equip and auto-upgrade options is not
enough on some versions. You are not losing a feature: our side has its own
auto-upgrade, delivered by the client that actually knows which of your items
came from Archipelago.

`ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md` has the long version, including what
does compose safely. If you are seeing this fingerprint *without* that dll
loaded, that is worth a report -- send the client log, and the line to look for
is `AddItemFunc detour install deferred`.

Check `KNOWN-ISSUES.md` for anything else -- it lists both the active bugs and
the by-design behaviors that get reported as bugs. If it's not there, it's worth
reporting: bring your yaml and the spoiler log.

Now go find out which region the seed decided you deserve first.
