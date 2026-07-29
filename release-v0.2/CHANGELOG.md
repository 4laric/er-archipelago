# Changelog

The narrative — what this project is and what v0.2 brings — lives in
`RELEASE-NOTES-v0.2.md`. This file is the terse per-release delta.

## v0.2.17 — 2026-07-29

### How much of a region an unlock opens

`region_grace_unlock` decides how many Sites of Grace a region unlock lights.

| value | what it lights | total across the map |
|---|---|---|
| `all` (default) | every warp point in the region — Liurnia is 59 at once | 338 |
| `landmarks` | one per sub-area, using the warp menu's own grouping | 47 |
| `entrance` | the region's front door only | 27 |

`landmarks` resolves Liurnia to Lake-Facing Cliffs, East Raya Lucaria Gate, Moonlight Altar and
Ruin-Strewn Precipice — its four real chunks. The partition is the **game's own**
(`BonfireWarpParam.bonfireSubCategoryId`), not a hand list, so it is uneven on purpose: a few
regions (Gravesite, Scadu Altus, Weeping) have a single sub-area and behave the same as `entrance`.

Nothing here can strand you or move an item. Region unlocks are still the only progression, every
check stays where it was, and a grace you were not handed is still reachable on foot and still
unlocks by touching it. Regions behind a wall the game itself enforces — the Academy seal, the
capital's Great Rune gate, the sewer — hand out nothing under any value.

Requested by **dafranky67**.

### Fixed: the tutorial Grafted Scion paid out 36 Stormveil checks

The game buckets `m10_01` — the ruined Chapel of Anticipation intro — under Stormveil, so the
generator counted the intro Grafted Scion as one of Stormveil's legacy bosses and handed it a
round-robin slice of the region's sweep pool. Killing an optional tutorial boss in the first few
minutes therefore paid out three dozen Stormveil Castle checks.

**Scope, honestly: those 36 are all ordinary filler.** Legacy-dungeon sweep pools — which is what
the Scion was wrongly counted into — are filler-only by construction: Remembrances, key items, Great
Runes, boss rewards, legendaries and shop slots are cut before the pool is built, and all 36 of these
carried no important tag at all. So this was an early dump of junk and consumables, not a progression
break. Stormveil's pool is unchanged in total; it now divides
between its two real bosses (Godrick and Margit) instead of three.

The Scion's own drop, the Ornamental Straight Sword, is a normal check and is untouched.

### `dungeon_sweep`'s middle settings now do something

`minidungeons`, `all` and `bosses` were **identical** — the emit checked only "is it off?" and never
filtered by boss class, so all three granted the whole sweep set. The values are real now:

| value | sweeps | checks |
|---|---|---|
| `none` | nothing | 0 |
| `minidungeons` | catacombs, caves, tunnels, minor dungeons | 515 |
| `all` | + legacy dungeons and castles | 1971 |
| `bosses` (default) | + field bosses | 3184 |

**The default moved from `all` to `bosses`, and that is not a change to your seeds** — the full set
is what every non-`none` value already granted, so `bosses` is simply the correct name for what has
been shipping. Leaving it at `all` would have quietly removed field-boss sweeps from every seed.

`all` is now genuinely "dungeons without field bosses", which is the split that was asked for.

### Also

- **The AP flower icon can be built again.** `build_ap_icon.py` was lost in July 2026 and the
  placeholder has worn a vanilla Telescope ever since. The generator is rewritten, the flower art is
  in the repo, `build.ps1` builds the override instead of printing a command, and `package_release`
  now refuses to ship a bundle without it. (No visual change until a build stages the texture.)
- The client re-applies the AP icon after a load. It writes an icon param that loads revert, and it
  was the only such writer that never re-armed — so flowered shop slots fell back to a telescope
  after the first load of a session.

## v0.2.16 — 2026-07-28

### The filler pool is yours to tune

> 📖 Player documentation: [What fills your junk checks](https://github.com/4laric/er-archipelago/blob/main/Elden-Ring-Archipelago-Player-Guide.md#what-fills-your-junk-checks) in the Player Guide.

`curated_filler` is back in the shipped `EldenRing.yaml`, written out with the real default weights
so you can see and edit them. It is the game's main dial for what fills your junk checks — how much
gear (`juice`), how many upgrade stones, how many runes — and a template that hides it hides the
dial. A new gate (`test_gf_shipping_yaml_recipe`) keeps the template's numbers identical to the
code's default, so it can never quietly ship an old economy again. Delete the block to follow the
default automatically.

`pool_builder_intensity` works again. It sets how good a piece of gear has to be to count as `juice`:

| setting | counts as juice | catalog size | gear in the finished pool* |
|---|---|---|---|
| `normal` | legendary only | 149 | 230 |
| `high` | legendary + rare | 536 | 872 |
| `max` (default) | + B-tier | 1013 | 1518 |

\* one seed, and it counts every catalog-grade item in the pool — the vanilla gear that was always
there plus what the recipe injected — not injected gear alone. Injected juice can never exceed the
catalog size in the column to its left.

🛑 **A higher floor means LESS gear, not better gear.** Each level is a strictly smaller catalog while
the `juice` weight is unchanged — so raising the floor asks for the same number of items out of a
shorter list, and the surplus becomes junk. It buys quality by paying quantity. The option had been
frozen and inert since the filler-budget rework; it is a live knob again and the generator now warns
when the catalog cannot fill the allocation.

### Four options retired

`pool_builder`, `pool_builder_scope`, `pool_builder_juice_cap` and `pool_builder_juice_pct` described
a private juice budget that no longer exists — the filler tail has one budget and the `juice` weight
in `curated_filler` is the cap, the share and the on/off switch. They are now `Removed` stubs, so a
yaml naming them **raises** instead of being silently ignored. For no gear at all, set `juice: 0`.

`CONTRACT_HASH` is untouched, so an already-installed client still pairs with this apworld. A default
seed rolls the same juice catalog it did in v0.2.15 — the option's own default was corrected to `max`
in review, because unfreezing it while the class default underneath still said `high` would have
quietly halved the catalog for anyone not using the shipped template.

### Also

- Multiworld coverage in CI: two Elden Rings and two Hollow Knights, asserting items flow both ways
  and that foreign progression lands only on the progression surface. Its first run found a real
  leak — the finale's 10 locations bypassed the location-creation seam and never got the
  confinement rule, so 7 foreign progression items had been placed off-surface. Fixed.
- The player guide now documents `natural_progression`, `dungeon_sweep` and what fills your junk
  checks.

## v0.2.15 — 2026-07-28

Requires **Archipelago 0.6.7**. Regenerate your seed **and** refresh the client — the two must be
updated together this time (the client reads its region list from the seed now; see below).
Location names last changed in v0.2.12.

### Changed — options

- **`dungeon_sweep` is settable again.** It was pinned to `all` in the v0.2 option slim. `none`
  turns sweeps off entirely — every check is picked up where it lies — and `minidungeons` /
  `bosses` are the two middles. Requested by **ShadowTL**.

- **"Can I turn the Shattering off?" — yes, and the option already existed.** `natural_progression:
  true` plays the whole map gated by REAL vanilla keys and boss remembrances (still shuffled, so
  they can be anywhere) in vanilla's own dependency shape, with no synthetic Region Locks;
  `num_regions` is ignored. It has worked since v0.2.9 and was simply never written into the yaml
  template, so the one place a player actually reads never mentioned it. It is documented next to
  `num_regions` now. Also requested by **ShadowTL**.

### Fixed — apworld

- **The Message from Leda could hold something your seed required, and it does not exist until
  Messmer is dead.** It sits near Scaduview Cross, but its container is only enabled after Messmer
  falls — and a region lock lights Belurat's graces, so you warp to the spot and find nothing. It
  can no longer hold required progression. Confirmed in game by Alaric. Found by screening a corpus
  (`treasure_enablers`) that the existing cross-region check had never read; that screen is now
  permanent, so the next one of these fails a test instead of reaching a player.

### Changed — client

- **The tracker's region list now comes from the seed instead of being baked into the `.dll`.**
  It used to be a generated table built from the full region list, which meant that on a
  `num_regions` seed the tracker grouped checks into regions that seed does not contain and marked
  them in logic. It is now read from the seed itself, so it is right for whatever regions you
  actually rolled. **This is why the client and apworld must be updated together** — an old client
  with a new seed is fine, but a new client with an old seed will say so in the log and group
  nothing rather than guess.

### Fixed — release process

- **v0.2.14 shipped stamped `0.2.13`.** The packager checked that the changelog named the right
  version but not that the code did, so every v0.2.14 seed reported itself as v0.2.13 and a bug
  report could not tell the two apart. The packager now refuses to build unless every version site
  agrees with the build.

## v0.2.14 — 2026-07-28

Requires **Archipelago 0.6.7**. Regenerate your seed **and** refresh the client. Location
names last changed in v0.2.12, so an in-flight seed from v0.2.11 or earlier still will not
match a new tracker.

### Fixed — apworld

- **A region lock could land behind Lichdragon Fortissax, and nothing could open that fight.**
  Fortissax is fought inside Fia's Deathbed Dream, which does not exist until she is handed the
  Cursemark of Death. The generator treated his Remembrance as an ordinary boss reward — and
  because it carries the major-boss tag, it was one of the *preferred* places to put a region
  lock. Reported by Nova71288, from three players' spoiler logs. That check can no longer hold
  anything a seed requires. The rest of Fia's chain was already protected; the boss reward at
  the end of it was not, because every screen we have for finding quest-gated checks inspects
  how an ITEM is awarded, and what a questline gates here is whether the FIGHT exists.

- **Key items were being deleted from the item pool.** The filler allocator decided what it
  could overwrite by asking whether an item was a *Goods* item — and in Elden Ring every key
  item is a Goods item, so it could overwrite them, and with the shipped recipe it essentially
  always did. Bell bearings, whetblades, the crafting kit, maps, prayerbooks and scrolls, the
  Dectus and Haligtree medallion halves, the Rold Medallion, Pureblood Knight's Medal and the
  Cursemark of Death were all being removed from seeds. The set is now read from the game's own
  key-item flag (`EquipParamGoods.goodsType`): **108 item names across 270 checks** keep their
  real item. This is a pool-shape change as well as a bug fix — a seed holds more real key items
  and correspondingly less curated filler.

- **35 more checks can no longer be required.** 34 are NPC dialogue handovers — derived from the
  game's own talk scripts rather than found one at a time, and 14 of the 48 the screen lands on
  were already tagged by earlier hand audits, which is the reason to trust it about the rest. The
  ones most likely to be noticed: **Rold Medallion** (Melina, after Morgott), **Drawing-Room
  Key** (Tanith), **Haligtree Secret Medallion (Right)**. Plus the Fortissax reward above.
  Missable checks went 179 → 214. All of them remain randomised and obtainable; they simply
  cannot hold something the seed needs.

### Changed

- **More smithing stones in the filler pool** (`stones` 27 → 29, paid for out of `juice` 44 → 42).
  Every check barred from holding progression displaces the progression that remains into earlier
  slots, and protecting key items shrank the pool that share is measured against. Both squeeze the
  early upgrade economy, which is held to a stated bar — a player who has cleared a realistic
  fraction of what is open to them can afford a **+3 weapon**. At the old share three of nine test
  seeds fell under it.

- **Crafting cookbooks are deliberately NOT protected.** They are key items by the game's
  reckoning, all 96 of them, and holding 96 vanilla cookbooks in the pool instead of curated
  filler is a change to how a seed feels that nobody asked for. Prayerbooks, scrolls and bell
  bearings ARE kept: same family, far fewer, and a missing bell bearing is felt.

- **The progression surface counts only checks that can actually hold progression.** It had been
  counting checks the fill rules already refused. Harmless until the Fortissax reward was tagged,
  at which point Deeproot Depths claimed a place to put a lock while having none — that reward was
  its only surface member.

### Fixed — client

- **The tracker's location table was regenerated** for the 35 newly-unrequirable checks (214
  missable, was 179). Client-side data only; replace the `.dll` so the tracker agrees with the
  apworld.

## v0.2.13 — 2026-07-27

Requires **Archipelago 0.6.7**. Regenerate your seed **and** refresh the client. Location
names changed in v0.2.12, so an in-flight seed from v0.2.11 or earlier will not match a new
tracker — finish old seeds before updating, or reroll.

### Fixed — client

- **Enemy scaling did nothing at all in v0.2.12, and works again now.** A guard added that
  release to avoid touching characters while a map was still loading was far too strict: it
  rejected roughly 99.5% of the game's character slots, so a sweep that should have rescaled
  a few hundred enemies typically rescaled one — the player's horse. Every enemy kept its
  **vanilla** strength, which for a rolled start in a late region (Mohgwyn, the Consecrated
  Snowfield) meant walking out of the first grace into endgame enemies at full power.
  Reported by ShadowTL. The guard is reverted; the settle window that guarded this before
  v0.2.12 is unchanged and is doing the job again. Sweeps now scale 240–280 enemies where
  they were scaling 1–2. **The apworld was never at fault** — it had been sending the correct
  difficulty all along, and the client was discarding it. Client-side fix: replace the `.dll`.

### Changed

- **Version is now `0.2.13` on both halves.** Not `0.2.12.1`: the client crate's version must
  be three-component semver, and a test pins it to the apworld's `APWORLD_VERSION`. The
  contract hash is unchanged, so a v0.2.12 apworld still pairs with a v0.2.13 client without
  reporting a mismatch — only the descriptive version differs.

## v0.2.12 — 2026-07-27

Superseded by v0.2.13 the same day; see the enemy-scaling entry above. Everything below
shipped in v0.2.12 and is still current.

### Fixed — apworld

- **28 checks that can be picked up in two different regions can no longer be required.** A
  check is filed in one region, and the reachability model treats it as available once that
  region opens. Some event-awarded pickups are obtainable in more than one place, and *which*
  place is decided by the order you happen to do things. Fire Knight Queelign is the clearest
  case: he can be fought at the Church of the Crusade **or** in Belurat, and drops the Crusade
  Insignia first and the Prayer Room Key second wherever those two fights land — so half of all
  players get each item in the "wrong" region. A seed could put a required item on one and
  strand a player whose route went the other way. They stay randomised and stay yours; they
  just cannot hold anything the seed *needs* any more. Found by a screen that also re-derived
  seven checks earlier audits had already caught by hand, which is what makes the rest
  credible.

### Changed — apworld

- **24 checks now name a landmark, and five of them said nothing at all before.** A check's
  tracker line ends with the nearest Site of Grace to where the item actually is, and a boss
  **reward** never had one — it is handed over by an event rather than placed in the map, so
  there was no position to measure from. Those rewards now borrow their boss's arena. Five
  bare lines gained a landmark (*Sword of Night*, *Claws of Night*, *Priestess Heart*, and
  Igon's rewards), three stopped showing a raw map id (*Hoslow's Petal Whip* now reads **near
  Consecrated Snowfield Catacombs**), and sixteen got sharper — *Bull-Goat Helm* went from
  "around Ruin-Strewn Precipice" to **near Magma Wyrm Makar**. They are a small set but a
  memorable one: legendary weapons, key items and Deathroot. The landmark is the **boss's**
  location rather than the item's, which is an inference and recorded as one — so where a boss
  can be fought in more than one place it is refused rather than guessed. Fire Knight Queelign
  is fightable at the Church of the Crusade or in Belurat and drops the Crusade Insignia first
  and the Prayer Room Key second wherever those happen, so neither keeps a landmark.

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
