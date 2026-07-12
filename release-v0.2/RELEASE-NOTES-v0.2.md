# Elden Ring for Archipelago -- v0.2

## What this is

Elden Ring as an Archipelago world. Your item pickups, bosses, shops, and
graces become checks in a shared multiworld pool; the items they would have
given you are shuffled out to other players' games, and theirs arrive in yours.

The headline mode is the Shattering (`num_regions`). You choose how many of
the overworld's major regions stay in play. Each of those regions is sealed
behind a "Region Lock" item that another player -- or your own seed -- must
send you. You start at Roundtable Hold with one region open, and the map
unfolds as locks arrive. It turns Elden Ring's open world into an Archipelago
progression graph.

Everything runs at runtime. Your game files are never modified: a vanilla
Elden Ring install, the apworld, and a client `.dll` are the whole setup.

## What's new in v0.2

v0.2 is a from-scratch rebuild of the world. It shares no data or code with
the earlier community randomizer lineage -- the location set, rules, and
options were all rederived from the game's own data. That rebuild is why the
game id and option list changed (see "Upgrading from v0.1" below).

On top of the clean base:

- **The Shattering, rebuilt.** `num_regions` picks how many regions stay in
  play; the goal region is always kept, so every seed is winnable.
  `num_regions_order` keeps either a fixed spine or a random roll.
- **Real item shuffle.** Each check pays out a shuffled vanilla item instead
  of generic Runes. Always on in v0.2 -- it is not a toggle.
- **Configurable goal.** `ending_condition` defaults to holding every kept
  Region Lock; a Great Runes goal is available as an alternative.
- **Dungeon sweeps.** Kill a dungeon's boss and its remaining checks
  register automatically.
- **Pool curation.** The Rune filler tail is scrubbed and rare and legendary
  items injected, with the rest spread across item types -- always on. The
  `curated_filler` recipe and the `pool_builder_pct_*` percentages let you
  shape what fills that tail.
- **Grace bundling.** A Region Lock lights all of its region's graces at
  once, so an arriving Lock means you can warp straight in.
- **Quality-of-life starts, built in.** You begin with a torch, Torrent,
  flasks, revealed maps, and immediate leveling, and any gear the multiworld
  sends is usable regardless of stats. These are how v0.2 plays, not options.
  Completion-based difficulty scaling is likewise always on; DeathLink is
  yours to toggle.
- **A much smaller option surface.** The surface was cut to 19 tunable
  options with sensible defaults; the rest of the old surface is frozen to
  one good setting each. Change `name` in the shipped yaml and you have a
  valid seed.

DLC (Shadow of the Erdtree) is supported but off by default, and is
experimental in v0.2. The base game is the recommended way to play.

## Upgrading from v0.1 -- BREAKING

**The AP game id changed from `EldenRing` to `Elden Ring` (with a space).**
A v0.1 yaml is rejected at generation with:

> No world found to handle game EldenRing. Did you mean 'Elden Ring'?

Do not just fix the `game:` line and keep the rest. The option surface was
cut to 19 tunable options, and Archipelago **silently ignores unknown yaml
options** -- a retrofitted v0.1 yaml can generate a seed you did not actually
configure, with no warning. Start from the shipped `EldenRing.yaml` and
re-apply your preferences there.

The upside of the id change: v0.1 and v0.2 are different worlds as far as
Archipelago is concerned, so they can be installed side by side. If you have
a v0.1 seed in flight, you can finish it on v0.1 and start fresh seeds on
v0.2 without uninstalling anything.

## Known issues

The honest list is in [KNOWN-ISSUES.md](KNOWN-ISSUES.md) -- read it before
filing a report. The main one: a small class of checks can still hand out
the vanilla item instead of the Archipelago one. It cannot strand a run
(those locations never hold progression), but you may miss a filler item.
DLC seeds have additional rough edges.

## The apworld and the client must come from the same release tag

They are a hash-matched pair: the apworld stamps a contract hash into the seed, and the client
checks it on connect. A mismatched pair does **not** fail at the door -- it boots, connects, and
then behaves subtly wrong.

Take both from the same release. If you see `VERSION MISMATCH` in the client log, that is exactly
what has happened. Hosts generating a multiworld need only `eldenring.apworld`, which is attached
to the release separately for that reason -- but it must still come from the same tag as the
players' clients.

See `DISTRIBUTION.md`.

## Requirements and install

- Archipelago 0.6.7
- A PC copy of Elden Ring (plus Shadow of the Erdtree only if you enable DLC)
- The `eldenring.apworld` and the client `.dll` from this release's assets

Install is a two-file drop plus the shipped `EldenRing.yaml`; the full
walkthrough is in `SETUP.md`. No game files are modified.
