# Changelog

## v0.2 — the provenance-clean rebuild (2026-07-07)

v0.2 replaces the world under the hood. The apworld is now a **from-scratch,
data-derived, provenance-clean rebuild** — its location data comes straight from
vanilla Elden Ring game files (params + MSB + grace/BonfireWarp anchors), with
**no third-party randomizer data or code** in the shipped world. The same MIT
runtime client from v0.1 drives it unchanged.

### Headline — provenance-clean, matt-free

The old world's location set traced upstream through another modder's apworld.
The v0.2 world was rebuilt from the ground up against public game data, with
every rule keyed off **region / map-id / event-flag / item-name** columns from
vanilla params — never off an imported location name. The result ships **no
non-free FromSoftware content and no third-party randomizer config or code**:
just the MIT client, the data-derived apworld, and a static detection table. See
`ATTRIBUTION.md` and the repo's `PROVENANCE.md` / `SPEC-PARITY.md` (constraints
P1–P5).

### Game id CHANGED — `EldenRing` → `Elden Ring`

The AP game id is **`Elden Ring`** (with the space). **This CHANGED from v0.1's `EldenRing`** — a v0.1 yaml will be rejected with *"No world found to handle game EldenRing"*. Update your `game:` line (and the options block header) to `Elden Ring`. Greenfield is promoted to BE the published world, so the old matt-lineage world is retired.

### What's in

- **The Shattering, on a clean base.** `num_regions` — the marquee mode that
  turns Elden Ring's open map into an Archipelago progression graph — is rebuilt
  on the data-derived world. Spawn at Roundtable Hold with one region open; each
  other region's Lock is a multiworld item; the goal region is always kept so the
  seed is always winnable. `num_regions_order` picks a fixed (`spine`) or random
  (`rolled`) set.
- **Real item shuffle.** `item_shuffle` pays out each check's own vanilla ER item,
  shuffled across the checks (~98.9% carry a real item; the rest give a Rune).
- **Great-Rune goal.** `ending_condition: great_runes` requires collecting Great
  Runes (auto-clamped to what's reachable this seed).
- **Dungeon sweeps.** Kill a dungeon's boss and its other checks auto-register
  (`dungeon_sweep`), via the sweep client path.
- **Pool building & varied filler.** `pool_builder` scrubs the Rune tail and
  injects rare/legendary items; `varied_filler` spreads the rest across item types.
- **Grace bundling / rando.** A Region Lock lights all of its graces (bundle), or
  one front-door grace with the rest scattered as items (`grace_rando`).
- **Completion scaling + Scadutree blessing**, quality-of-life start options
  (torch, steed, flasks, maps, early leveling, no weapon requirements), progressive
  flasks / stonesword keys, local-items, and DeathLink.

### Engineering

- **Contract single-source.** A `contract.py` defines every slot_data key's
  shape, producer, and consumer, validated at generation time — so the world and
  the MIT client stay in lockstep with no client fork.
- **Semantic test tiers.** Replay suites + region-correctness gates catch
  wrong-behavior-with-presence bugs (e.g. region/grace mis-bundling), CI-gated.
- **Rides the existing MIT client** via the keyless slot_data path (`locationFlags`
  + `regionOpenFlags` + `apIdsToItemIds`) — no client fork, no client rebuild
  required over v0.1.

### Known issues

Carried forward and current issues are tracked in `KNOWN-ISSUES.md`. Highlights:
Spirit Calling Bell may be unusable in-game; a few map-piece items may arrive on
connect; the DLC Shadow Keep church-basement grace can warp you in pre-drain.
A couple of data-loss fixes (region front-door grace latch, flag-poll new-save
baseline) are wired but pending final in-game confirmation. DLC is experimental —
base game is the recommended, supported way to play.

### Licensing

The project adopts the **upstream Archipelago license (MIT)**. The runtime client
is MIT; the data-derived apworld ships no non-free FromSoftware content and no
third-party randomizer config or code. You bring your own copy of Elden Ring. See
`ATTRIBUTION.md`.

---

*Elden Ring and Shadow of the Erdtree are trademarks of FromSoftware / Bandai
Namco. This is an unofficial fan project and ships no game assets.*
