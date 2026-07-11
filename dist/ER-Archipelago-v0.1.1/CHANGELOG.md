# Changelog

## v0.1.1 — bugfix + balance (2026-07-05)

A point release fixing the biggest playtest papercuts and easing the early game.

### Fixes

- **Torrent on region-lock starts.** On a rolled / `num_regions` start under the
  default bell setting, Melina's mount hand-off was being skipped — you'd get her
  "let's talk" camera pan at a grace but no Melina, no dialogue, and no Spectral
  Steed Whistle, leaving you on foot. You now start with Torrent so the map is
  rideable from the first grace.
- **Reopen the connection form any time.** The overlay menu bar now has a
  **Connection** entry, so you can switch server / slot / password while already
  connected — no more editing or deleting `apconfig.json` to point at a new room.
- **Compressed-websocket warning is labelled.** The red "your client does not
  support compressed websocket connections" line from the server now gets a
  follow-up note saying it's harmless (it is — no effect on play).
- **Rebalanced filler pool.** Less flooded with high-value runes and smithing
  stones, for a less trivial early game.

### Known issues (new / changed)

- **Overlay typing can leak to the game.** While a text field in the overlay is
  focused (the Connection form or the say box), keystrokes still reach the game,
  so a key like `e` can fire an interact/confirm. Workaround: open the
  **Connection** form from a game menu or the main menu — where world inputs don't
  fire — rather than while moving around. A proper input block is coming.
- **Warping into a boss arena before the boss is dead.** You can fast-travel onto
  a boss grace whose boss you haven't beaten and land in an empty arena. Harmless
  for now; being excluded in a future release.

## v0.1 — first public release (2026-07-04)

The first playable public drop of **Elden Ring in Archipelago**: the Lands
Between as a first-class multiworld game, running on a live copy of Elden Ring
through a custom runtime client.

### Headline — The Shattering

The flagship mode. The overworld is broken into a handful of regions and each
region's key becomes a multiworld item. You start at Roundtable Hold with one
region already open, and every other
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
