# Changelog

The narrative — what this project is and what v0.2 brings — lives in
`RELEASE-NOTES-v0.2.md`. This file is the terse per-release delta.

## v0.2.11 — 2026-07-26

Requires **Archipelago 0.6.7**. Regenerate your seed **and** refresh the client. Location
names changed in this release, so an in-flight seed will not match a new tracker — finish
old seeds before updating, or reroll.

### Changed — apworld

- **`Boss` now means every boss.** The `Boss` location type was silently excluding the
  remembrance and great-rune bosses, so `important_locations: [Boss]` gave you 95 checks
  with **Godrick, Rennala, Radahn, Rykard, Mohg and Malenia all absent**. The cause was a
  filter that discarded any boss whose reward is *named* after a remembrance or a great
  rune — our rule, not the game's, and a leaky one: Agheel and a couple of others kept
  their tag purely because their drop is named something else. `Boss` is now 134 checks and
  a major boss is guaranteed to be one. If you play with this option, expect more of them.
- **A guessed region says so.** 506 checks sit on ground we cannot pin exactly — usually a
  border tile, where the nearest landmark is across a region line. They now read
  `(region unconfirmed)` instead of stating a region we do not actually know. Nothing about
  where they are has changed; they were already barred from holding progression. Only the
  label was overconfident. The example that prompted it: the Tibia Mariner's Deathroot at
  Summonwater, which sits on the Limgrave side of a tile whose other checks are Caelid.
- **Shop checks name the merchant who actually sells it.** Turning in a bell bearing moves
  a merchant's stock to the Twin Maiden Husks, so the Husks were being listed as a second
  seller on **377 wares they do not stock until you have found that bearing** — reading as
  an early alternative that does not exist. They are dropped from those notes and kept
  where they genuinely are the seller.
- **Eight more questline-gated checks are marked missable.** Each sits in one region but
  does not exist until a questline advances somewhere else — most visibly the **Golden Seed
  at Stormhill Shack**, which is not there until you have progressed past the Roundtable.
  They stay randomised and stay yours if you do the questline; a seed just cannot put
  anything *required* on them any more. The others: Varré's Lord of Blood's Favor, the
  Witch's Glintstone Crown, Patches' Murkwater Cave drops, the Wise Man's Mask, and three
  Volcano Manor invasion rewards.

### Fixed — apworld

- **A missable check could be forced to hold something good, and then hold nothing at all.**
  `important_locations` says a tagged check must reject filler; a missable check must reject
  progression. A location under both accepted *nothing*, and generation had no legal item
  for it. Missable now wins — a check you can lose permanently is never forced to carry
  something worth losing.

## v0.2.10 — 2026-07-26

Requires **Archipelago 0.6.7**. Regenerate your seed **and** refresh the client. Mostly
about knowing where a check actually is, and about questline pickups no longer being
thrown away.

### Added — apworld

- **Seven NPC and quest gestures are checks now.** Questline rewards used to be out of
  scope; they are in, randomised, and marked missable so a seed never *requires* one.
- **Check descriptions got a lot less bare** — 608 checks with no description down to 126.
  482 shop checks now name the merchant who sells the ware, six unnamed dungeons were
  filled in, and a batch of checks that were described by the wrong map tile now use the
  right one.

### Changed — apworld

- **Questline-gated checks are randomised and missable, not excluded.** An earlier attempt
  removed eight pickups from the pool entirely to guarantee a property the missable rule
  already provides. They are back in, marked instead.
- **Patches' chest pair and Edgar's five Revenger's Shack pickups are marked missable** —
  they are switched off until an NPC state changes, which nothing had noticed.

### Fixed — apworld

- **1189 checks that had no position at all now have a map**, and merchant checks inherit
  the merchant's own position — closing the coordinate gap from 34.3% to 19.4%.

### Fixed — packaging

- **The build freshness gate could never pass.** It compared timestamps against a file the
  script itself rewrote, then against commit time, which is always *after* the build. It
  now stamps the build with a content hash.

## v0.2.9 — 2026-07-24

Requires **Archipelago 0.6.7**. Regenerate your seed **and** refresh the client — they
ship together. Shop and merchant fixes on the apworld side, and on the client a crash,
three classes of check that gave you nothing, and shop purchases that handed over the
vanilla item.

### Fixed — apworld

- **Dragon Communion purchases could be asked to carry progression.** Incantations
  bought at a Dragon Communion altar cost Dragon Hearts — a limited consumable — so
  spending one closes off the others. Those checks are meant to be marked missable and
  barred from holding anything required. The rule only matched one of the game's cost
  types, so **eleven alt-currency checks were unmarked**, including every ware at the
  DLC's Grand Altar of Dragon Communion. A seed could place a required item behind a
  purchase you no longer had the hearts to make. Now any purchase not paid in Runes is
  marked, and each cost type is tracked separately.
- **Merchant hints named one shop when several sell the ware.** The tracker would say
  "Nomadic Warrior's Cookbook [1] — Kalé, Church of Elleh", you'd buy out Kalé's stock,
  and the check wouldn't fire — because four different merchants sell that row and the
  note named one of them. **496 of the game's 709 shop-check rows have more than one
  seller.** Five hand-written seller notes are removed, and generation now refuses to
  build if one comes back.
- **The one progression-eligible slot per merchant now really belongs to that
  merchant.** Each merchant contributes at most one slot that can hold progression.
  That slot was picked on a test that couldn't tell "one shop sells this" from "one
  price tag exists for it", so eight of the ten picks were sold by two to seven
  merchants apiece, and one was filed in a region where **no seller stands at all**.
  Slots are now chosen per physical merchant, must be a ware only that merchant sells
  out in the world, and must sit in the region the check claims. Fewer slots qualify,
  and the ones that do are findable.

*(The Twin Maiden Husks re-sell a merchant's stock after you hand in their bell
bearing; that mirror is no longer counted as a second seller, since you can only reach
it by killing the merchant first.)*

### Fixed — client

The apworld and the client ship together; refresh both.

- **Crash a few seconds after a boss sweep.** Felling a boss that pays out a batch of
  nearby checks could take the game down with an access violation. The client kept a
  pointer to your inventory that it captured once and reused forever; a map load frees
  that memory, so every grant after your first load was handing the game a dead
  reference. It now retires the pointer at every load and re-acquires it before the
  next grant.
- **Chests, scarab Ash-of-War drops and boss drops that gave you nothing.** Suppressing
  the vanilla item at a check is the same act as detecting it — both hang off the
  pickup. For weapons, armour, talismans and Ashes of War the client was emptying the
  slot outright, so there was nothing to pick up: no item, no popup, and the check
  never registered. Leonine Misbegotten's drop went unclaimed for a four-hour session
  this way.
- **Swept checks left dead pickups lying around.** When a boss sweep claimed the checks
  near its arena, the world was never told: the chests and corpses stayed put, opened
  on nothing, and gave no sign they had already been collected. The sweep now marks
  each one, retrying until the game confirms it.
- **Shop purchases that delivered the vanilla ware.** After the first map load, every
  rewritten shop row quietly reverted to selling its vanilla item while the client
  still believed it had been handed over — so you bought the check, got the ordinary
  item, and the multiworld item never arrived. Both halves are fixed: rows are
  re-armed on every load, and delivery is now re-proved against the live shop row
  rather than assumed.
- **Progressive Flask Upgrades that appeared to do nothing.** The flask has two axes:
  Sacred Tears raise potency, charges are reconciled against a ladder. The early rungs
  of that ladder ask for fewer charges than a fresh character already has, so the first
  few upgrades legitimately added none — silently. The client now says so, and
  announces a charge increase when one actually happens.

### Added — client

- **On-screen notices for grants that have no item.** Anything the client applies
  directly — flask charges today — now announces itself in the overlay, so an effect
  with no inventory item is no longer indistinguishable from a broken feature.
- **Crash reports.** A native crash now writes `crash-<pid>.txt` next to the client
  with the fault address and a stack. If the game goes down, that file is the single
  most useful thing to attach to a bug report.

### Changed

- **Some checks may hand you a duplicate vanilla item.** Stopping the dead-pickup bug
  above means the vanilla ware stays on the shelf for weapons, armour, talismans and
  Ashes of War, so you can receive both it and the multiworld item. This is deliberate
  and temporary: a duplicate is cosmetic, while the alternative was a check that never
  fired at all. The proper fix — swapping those slots for the Archipelago placeholder
  rather than emptying them — is in progress.

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
