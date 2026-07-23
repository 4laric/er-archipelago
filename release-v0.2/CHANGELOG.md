# Changelog

The narrative — what this project is and what v0.2 brings — lives in
`RELEASE-NOTES-v0.2.md`. This file is the terse per-release delta.

## v0.2.8 — 2026-07-23

Requires **Archipelago 0.6.7**. Hotfix-heavy; regenerate your seed and refresh the
client. Headline: a class of shop/merchant checks that handed out the vanilla item
(or fired nothing) in `num_regions` seeds.

### Fixed

- **Merchant checks sealed in the wrong region.** A shop check inherited its region
  from its ShopLineupParam *block*, but a block can hold two merchants in two
  regions — so the Altus Hermit Merchant's stock (Prophet set, Perfume Bottle,
  Sentry's Torch, Golden Sunflower, Distinguished Greatshield, …) was tagged Liurnia
  and got sealed out whenever Liurnia was rolled away. You'd buy from him in kept
  Altus and get the plain vanilla item with nothing sent. Region is now derived from
  the *physical merchant* (talk-ESD `OpenRegularShop` range → MSB placement), fixing
  the whole nomadic/roving-merchant class and the mirror **softlock** (a merchant in
  a sealed region whose check the world thought was reachable).
- **Foreign shop slots showed as the vanilla ware** instead of being flowered with
  the AP telescope; every foreign / region-lock slot now flowers, and a wider spare-
  good pool gives more of them a distinct name.
- **Cross-region "near <grace>" descriptions.** A guard stops a check being labelled
  by a Site of Grace in a different region (Roundtable Memory Stone no longer reads
  "near South Raya Lucaria Gate").
- **Ornamental Straight Sword** (tutorial Grafted Scion drop) → Limgrave, off the
  progression surface (a missable one-time fight can't gate a Lock).
- **Capital Rampart grace** no longer force-lit by its region Lock — it's unlocked by
  the Draconic Tree Sentinel.
- **Belurat Scadutree fragment** (needs Enir Ilim access) off the progression surface
  so a Belurat Lock can't strand on it.

### Added

- Interior checks read by **dungeon name** ("treasure — Sellia Crystal Tunnel")
  instead of a raw map tile.
- **Spirit Ashes** tiered into the juice pool (25, S/A-weighted); **Messmerfire
  Grease** added to filler.
- **`datamine_merchant_shops`** (talk-ESD + MSB → `merchant_shops.tsv`): ground-truth
  shop-check regions. A guard now hard-errors on any region override the derivation
  already reproduces, so redundant hand-pins can't accumulate.
- Client: all clippy warnings cleared (style only).

### Known

- **Non-goods double-dip** persists this build: weapons / armor / talismans / ashes
  can still hand out their vanilla copy alongside the AP item at enemy / scarab /
  scripted drops (e.g. Ash of War: Lightning Ram). The apworld now ships the data to
  blank these at the source; it goes live once the client's zero-slot handler lands.

## v0.2 — 2026-07-12

Requires **Archipelago 0.6.7**. A from-scratch, provenance-clean rebuild of the
Elden Ring world (`PROVENANCE.md`); pure-runtime (vanilla game on disk, the
client does everything live).

### Breaking

- **Game id is now `Elden Ring`** (was `EldenRing`). A v0.1 yaml is rejected at
  generation (`No world found to handle game EldenRing`). Upside: v0.1 and v0.2
  install side by side.
- **Option surface shrank to 19 tunable options**; the rest are frozen to
  defaults and no longer appear in the yaml. **Do not retrofit a v0.1 yaml** —
  Archipelago warns on each unknown option but then generates on defaults
  anyway, so you get a seed you did not configure. Start from the shipped
  `EldenRing.yaml`.

### Added

- **The Shattering (`num_regions`)** on the clean base: spawn at Roundtable Hold,
  each region's Lock is a multiworld item, the goal region is always kept.
  `num_regions_order` = `spine` (fixed) or `rolled` (random).
- **Real item shuffle** — each check pays out its own vanilla ER item, shuffled.
- **Great-Rune goal** (`ending_condition: great_runes`), auto-clamped to what is
  reachable.
- **Dungeon sweeps**, **pool building + varied filler**, **grace bundling** (a
  Lock lights all of its region's graces at once).
- **Scaling & QoL** — completion scaling, Scadutree blessing scope, start
  torch/steed/flasks, all maps revealed, early leveling, no weapon requirements,
  buyable Stonesword Keys, flattened smithing ladder, DeathLink.

### Fixed (playtested 2026-07-12)

- Spirit Calling Bell now usable from the received item.
- Map-piece items no longer minted on connect; the reveal fires without grants.
- Flasks no longer double-granted after a tutorial-death reload.
- A rolled start can no longer leave you without Torrent.

### Known issues

See `KNOWN-ISSUES.md`. Headline: a few checks can still pay the vanilla item
(contained — cannot strand a run); DLC seeds are experimental; base game is the
supported config.

### Licensing

Upstream Archipelago license (MIT); the runtime client is MIT and the
data-derived apworld ships no FromSoftware content or third-party randomizer
code. See `ATTRIBUTION.md`.

---

*Elden Ring and Shadow of the Erdtree are trademarks of FromSoftware / Bandai
Namco. This is an unofficial fan project and ships no game assets.*
