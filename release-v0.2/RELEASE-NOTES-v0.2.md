# Elden Ring x Archipelago — v0.2

*Draft release notes for GitHub / Nexus. Not for Discord. Trim the feature list to whatever's
confirmed working at tag time.*

---

v0.2 is a full rewrite. The world is rebuilt from the game's own data — params, map layout, event
flags — instead of being layered on top of another randomizer. Nothing from any other Elden Ring
rando ships here: no borrowed config, no borrowed code. If you're coming from v0.1, your yaml's
`game: EldenRing` line is **unchanged** — the AP game id stays **`EldenRing`**; greenfield is
promoted to BE that world, so the old matt-lineage world is retired (both can't claim `EldenRing`
at once). The world internals and options changed, so v0.2 seeds and rooms still differ from v0.1 —
but that's not a game-id change.

## The mode

The headline is the Shattering (`num_regions`). The Lands Between starts sealed into regions, and
each region opens when you receive its lock as an item from the multiworld. So where you can go, and
in what order, depends on what everyone else's games send you — the whole map, gated. Checks are tied
to the game's own event flags (a few thousand of them), so world pickups, bosses, shops and graces
all report back. Region locks are enforced by the client, not the honor system.

## What's in it

- The full pickup → check → item-grant loop, live in-game
- Region locks (warp-enforced) with grace bundling on receipt
- Item send/receive on the native ticker; DeathLink both directions
- In-client tracker — region-grouped checks, filters, hint marking
- Shattering (`num_regions`), item shuffle, pool curation, scaling, grace rando, important/missable
  location tagging

## Install

Grab the client `.dll` and `eldenring_gf.apworld` from the assets below and follow `SETUP.md`. Short
version: drop the two files in place, point the client at your room, connect. Variants and the full
option list are in the `release-v0.2` docs.

## Provenance

This is the whole point of v0.2. The world is derived entirely from vanilla game data, so it ships no
non-free FromSoftware content and nothing from another author's randomizer. It runs on Archipelago
(MIT) and the client is MIT. Details in `ATTRIBUTION.md`.

Thanks to nex3 and vswarte.

## Known issues

Read `KNOWN-ISSUES.md` before filing anything.

---

### Short version (Nexus page blurb)

> Play Elden Ring as part of an Archipelago multiworld — your checks get shuffled into a shared pool
> with everyone else's games, and their items show up in yours. The map starts locked into regions;
> you open each one by receiving its key from the multiworld, so your route depends on what your
> friends' games send you. Bosses, shops, graces and world pickups all count as checks.
>
> This is a from-scratch build derived from the game's own data — it doesn't include or require any
> other Elden Ring randomizer. Built on Archipelago (MIT). Thanks to nex3 and vswarte. Requires a PC
> copy of Elden Ring and ModEngine; install is a two-file drop and a connect (see the SETUP guide).
