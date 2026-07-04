# Changelog

## v0.1 — first public release (2026-07-04)

The first playable public drop of **Elden Ring in Archipelago**: the Lands
Between as a first-class multiworld game, running on a live copy of Elden Ring
through a custom runtime client.

### Headline — The Shattering

The flagship mode. The overworld is broken into a handful of regions and each
region's key becomes a multiworld item. You start in Limgrave, and every other
region — up to Leyndell and Morgott — is sealed until its key arrives. Configured
with `num_regions` (see `EldenRing-Shattering.yaml`), it turns Elden Ring's huge
open map into a real Archipelago progression graph and a tight ~3-4 hour run.

### What's in

- **Pure-runtime architecture.** No baked/redistributed game content — the MIT
  runtime client edits the live game in memory. Vanilla Elden Ring + the apworld
  + the client is the whole install.
- **Region locks, warp-enforced.** Region gating is enforced by the client (not
  honor-system): a region's own key unlocks its graces and lets you warp in.
- **The full multiworld loop** — pickup → check → item grant — confirmed in-game,
  with native-style bottom-center event banners for sends and receives.
- **DeathLink**, validated in both directions.
- **Multiple goals:** Capital (Morgott, the Shattering default), plus base-game
  and DLC variants including a Messmer / Shadow of the Erdtree mini-campaign.
- **Progressive items**, pool building and curation, and a deep options surface
  with presets and a config wizard.
- **Built-in tracker window** (toggle with **F6** or the overlay's **Tracker**
  menu): checks grouped by region with done/total, locked regions dimmed with
  their gate item, current-region highlight, hint marking, big-ticket flags, and
  reachable-only / big-ticket-only filters.
- **PopTracker pack** with auto-tracking, including a DLC-only map variant (an
  optional external alternative to the built-in tracker).

### Known issues

- **Spirit Calling Bell** can be unusable in-game (summoning gated). Does not
  block a solo Shattering run; targeted for a point release.
- **Map fragments granted on connect** — a few map-piece items may arrive the
  instant you connect. Harmless; effectively a small handful of free early checks.
- Some options are newer than others; the Shattering template ships tuned,
  verified-green defaults.
- **Item icons:** AP items currently show the vanilla Telescope icon. The custom
  Archipelago flower icon returns in a point release.
- **DLC (Shadow of the Erdtree):** largely untested in v0.1. Base-game (DLC off) is
  the recommended, supported way to play; DLC seeds are experimental.

### Licensing note

This release is redistributable: the runtime client is **MIT**, the apworld
follows the Archipelago-ecosystem lineage, and the pure-runtime design ships **no
FromSoftware game data**. You bring your own copy of Elden Ring.

---

*Elden Ring and Shadow of the Erdtree are trademarks of FromSoftware / Bandai
Namco. This is an unofficial fan project and ships no game assets.*
