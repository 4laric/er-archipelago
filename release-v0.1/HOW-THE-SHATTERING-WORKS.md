# How The Shattering Works

If you've never played an Archipelago randomizer, this is the page to read. It
explains what actually changes about Elden Ring in the flagship mode — no jargon,
one idea at a time.

---

## The one-paragraph version

Normally Elden Ring lets you wander almost anywhere from the start. **The Shattering
breaks the map into a handful of regions and locks them.** You begin at Roundtable
Hold — the hub — with one region already open and everywhere else sealed. To open
another region you need *its key*, and that key is an item somewhere in the multiworld,
found by you or handed over by another player. Get a region's key, fast-travel in,
explore it, and hidden in there are the keys to *more* regions. You chain your way
open, region by region, until you can reach Leyndell and put down Morgott. That's the
run.

---

## What's different from normal Elden Ring

| Normal Elden Ring | The Shattering |
|---|---|
| Open world — go almost anywhere | Only a few regions are unlocked; the rest are sealed |
| Pick items up and keep them | Every pickup is a **check** — it sends an item into the multiworld |
| You find your own gear in order | Your gear arrives as items, sometimes from other players' games |
| Explore freely | You explore to find **keys** that open the next regions |

You're still playing Elden Ring — same combat, same bosses, same map. What changes is
*where you're allowed to go* and *how you get there*.

---

## The pieces, one at a time

### 1. The shatter (`num_regions`)

The world is cut down to a few **major regions**. Everything else is sealed off — you
can't travel there and it holds nothing. `num_regions: 4` means four majors are in
play. You always spawn at **Roundtable Hold** (the between-worlds hub — no lock, always
reachable), you begin with **one random region already open** (your rolled start), and
**Leyndell + Morgott** is always the goal, reached up through **Altus Plateau** (the
road to the capital). The other majors are rolled at random. Raise the number for a
longer run with more regions in the mix.

### 2. Region locks (the keys)

Each sealed region has a **region lock** — a key item, like "Caelid Lock." While that
region is locked, its Sites of Grace are dark and you can't go there. When the
multiworld gives you that region's key, the region **opens**: its graces light up and
you can travel in. That's the heartbeat of the run — *receive a key, a new region
opens.* (Your rolled start region's key is simply handed to you at the beginning.)

### 3. Warping in

Because the open regions aren't next to each other on the map, you don't walk between
them — you **fast-travel** from Roundtable Hold or any lit grace. The moment a region's
key arrives, its graces light and you warp straight in. (One key lights *all* of that
region's graces at once.)

### 4. The goal

Reach **Leyndell** and defeat **Morgott, the Omen King**. Leyndell also wants a couple
of **Great Runes** first (the run guarantees you can get enough). Everything the mode
does is in service of chaining you toward that fight.

---

## Boss sweeps and boss locks (the satisfying part)

Two options make exploring a region feel clean instead of tedious.

### Dungeon sweep

You don't have to comb every catacomb for its last three items. With **dungeon sweep**
on, **beating a dungeon's boss automatically collects and sends every remaining check
in that dungeon.** Clear the boss, the rest sweeps out to the multiworld. (This can
fire off a lot of checks at once — good for you, and it feeds everyone else in the
game too.)

### Boss locks

Here's the neat twist. Some region keys are **boss locks** — the key that opens the
*next* area is dropped by a **boss** rather than sitting in a chest. With the default
placement (**own region**), a region's key is hosted on a boss *inside a region you can
already reach*. So the loop becomes: open a region → fight through it → its boss drops
the key to somewhere new → open that → repeat. Beating bosses literally unlocks the
world.

---

## A run, start to finish (example)

Say your seed's rolled start is Limgrave, and it also keeps Caelid and Altus (plus the
always-there Leyndell goal).

1. **You spawn at Roundtable Hold**, and your start region — Limgrave — is already
   open. You warp in, grabbing checks and sending items out to the multiworld.
2. **A key arrives.** Another player finds "Caelid Lock" in their game and it comes to
   you — *or* you find it on a Limgrave boss. Caelid's graces light up.
3. **You warp to Caelid.** New region, new checks. Somewhere in here — likely on a
   boss — is **Altus Lock**.
4. **You beat that boss, get Altus Lock.** Altus opens. On the way you've been
   receiving gear and upgrades from the multiworld, so you're keeping pace.
5. **Altus leads to Leyndell.** Once you hold the required Great Runes (the sealed rune
   bosses are kept in the mix so you can), Leyndell opens.
6. **You beat Morgott.** Run complete — your slot is finished, and you keep playing to
   help send items to everyone else if the multiworld's still going.

The start region, the rest of the regions, and the order are different every seed —
that's the point.

---

## Common questions

**"A region's grace won't light even though I have the key."** Warp to any grace first;
newly opened graces sometimes need a fast-travel to refresh. The client's `/warp <id>`
command can drop you in directly if needed.

**"I got an item that does nothing."** Some items only matter later (a key for a region
you can't open yet, or gear for a build you're not running). Hold onto it — the logic
guarantees everything you *need* arrives in a workable order.

**"Why did a pile of checks send at once?"** You beat a dungeon boss and it swept the
rest of that dungeon. That's dungeon sweep working as intended.

**"Can I get stuck?"** No. The generator guarantees a path: every key you need to reach
the goal is placed somewhere reachable, in order. You might be *waiting* on another
player to find your next key, but the run is always completable.

**"Where do the keys come from — me or other players?"** Both. In a solo game they're
all in your own world. In a multiworld they're spread across everyone's games, so
someone else might be holding your next region behind one of *their* checks.

---

## The knobs

All of this is set in `EldenRing-Shattering.yaml`, and the comments there explain each
option. The ones that shape the mode:

- `num_regions` — how many regions stay in play (the size of the run).
- `world_logic: region_lock` — turns on the per-region key system.
- `region_access: warp` — a region's own key is enough to travel in.
- `dungeon_sweep: all` — bosses sweep their dungeon's leftover checks.
- `boss_lock_placement: own_region` — region keys ride on in-region bosses.
- `great_runes_required` — how many Great Runes Leyndell asks for.

For what actually gets randomized and what "counts" as progression, see
`CHECKS-AND-PROGRESSION.md`.
