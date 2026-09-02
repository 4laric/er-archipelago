# Changelog

The narrative — what this project is and what v0.2 brings — lives in
`RELEASE-NOTES-v0.2.md`. This file is the terse per-release delta.

## v0.5.6 — 2026-08-31

### What you need to update

- **Client:** Required — use the v0.5.6 client with v0.5.6 seeds.
- **APWorld:** Host-only — the room host or generator must install the matching APWorld.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible when kept on its matching client/APWorld pair.
- **Profile/assets:** No action.

The contract remains `8397a952`; this window moves only the exact-version handshake. The matching
client half is clients#559 and its merge commit is pinned by the gitlink in this change.

Entries arrive below as they merge.

- **The external evidence browser now indexes 1,499 Redmaw checklist bindings (#1273).** The
  deterministic intake records exact item labels, sheet sections, checkbox anchors, and wiki.gg
  targets from a pinned source commit. All results remain discovery-only and claim no access logic.

- **All nine Deathroot checks now have exact external acquisition leads (#1273).** A pinned,
  CC BY-SA Eldenpedia revision binds each repeated item by unique boss, dungeon, or site anchors.
  The leads remain discovery-only and expose the Wyndham Altus/Mt. Gelmir boundary difference
  without silently changing region or access logic.

- **All three Shabriri Grape checks now have exact external acquisition leads (#1273).** Unique
  anchors in a pinned Eldenpedia revision are cross-checked against committed ItemLot identities;
  the results remain discovery-only and preserve region and quest-boundary differences for review.

- **Merchant context resolves 157 formerly ambiguous external leads (#1273).** Exact merchant
  sections, AP flags/shop rows, the physical-merchant datamine, and 491 pinned wiki.gg item
  revisions identify those checks; another 135 ambiguous or shared-shop labels are refused.

- **The obsolete PopTracker pack has been removed (#1308).** It was no longer supported and its
  presence suggested otherwise. The original map inputs still used by repository audit pages now
  live under `greenfield/maps`; the supported player tracker remains the in-client F6 tracker.

- **Fog Rift Catacombs rewards no longer point players to Auriza Side Tomb (#1305).** Both
  rewards sharing `f520700` now name their EMEVD-proven dungeon while remaining correctly assigned
  to Gravesite.

- **The player guide now explains Region Lock hints (#1309).** Its stable
  `#region-lock-hints` section covers the F6 tracker, surface-check balance,
  frontier selection, aimed hints, and where the resulting Archipelago hint
  appears.

- **Discarded Palace Key logic follows the Baleful Shadow chain (#1317).** When vanilla items are
  shuffled, Miniature Ranni is progression and must be received before the key check enters logic;
  vanilla Ranni steps absent from the v1.17 appearance predicate are not over-required.

- **Chapel of Anticipation return checks now require their real Four Belfries route (#1303).**
  The Stormhawk ashes join the Scion rewards in Liurnia, and all four checks require an Imbued
  Sword Key when legacy key gates are enabled. Stormveil alone can no longer put unreachable
  Chapel checks in logic.

## v0.5.5 — 2026-08-31

### What you need to update

- **Client:** Required — use the v0.5.5 client with v0.5.5 seeds.
- **APWorld:** Host-only — the room host or generator must install the matching APWorld.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.** `reroll_mine_materials`
  defaults on; set it to `false` to retain vanilla mine rewards.
- **Existing seed/save:** Compatible when kept on its matching client/APWorld pair. The new option
  affects newly generated seeds only.
- **Profile/assets:** No action.

Window opened during the unreleased v0.5.4 development window. The contract moves from `13db0b3a`
to `8397a952` for the new `mineMaterialRoll` seed table; the matching client half is clients#493,
and its merge commit is pinned by the gitlink in this change.

Entries arrive below as they merge.

- **Patches' Missionary's Cookbook [2] now follows his other shared-shop checks (#557).** Its stale
  Limgrave override is gone; the cookbook uses the same Roundtable/defaulted fallback and
  Patches/Thiollier site set as the rest of their multi-region inventory.

- **Brother Corhyn's 29 shop checks no longer disappear with Liurnia (#331).** His wandering
  inventory now uses the honest Roundtable/defaulted fallback instead of inheriting Seluvis's
  Liurnia label from their shared shop block. A seed that keeps Leyndell may gate them there;
  otherwise they remain available as conservative filler-only hub checks.

- **The Shadow Realm Rune [2] by Castle Ensis now belongs to Scadu Altus (#1054).** Both copies
  of its treasure placement sit inside the Scadu Altus play-region volume; the old Gravesite label
  came from a nearest-grace guess across the regional seam.

- **Greater Potentate's Cookbook [7] now belongs to Gravesite (#1054).** Its exact pickup point
  and nearest grace both place it at Pillar Path Cross; Scadu Altus no longer creates a check on
  ground that its lock does not own.

- **Pinned the latest green client build (clients#538, #542-#547, #554-#556).** Elden Ring's
  bounded sustain-delivery path can no longer deadlock ordinary AP items, and teardown/signature
  failures now capture the evidence needed to diagnose the next live report. The shared bundle also
  carries Bloodborne's GUI-v2, live-save identity, Rescue panel, compact pickup toasts, contextual
  guidance, and passive research probes.

- **Enemy and boss rune payouts can follow sphere difficulty (#1091, clients#536).** The new
  default-off `scale_rune_rewards` option keeps direct runes-per-effort steadier when randomized
  progression moves an early enemy late or a late boss early. Golden Rune inventory items are
  never changed. Loaded regulation values are the immutable baseline, so the runtime pass does not
  compound Matt's randomizer rewards across region changes.
  
- **Jagged Peak's Summit grace now unlocks with its region (#370).** Exact map positions place it
  outside and well above Bayle's arena anchor; Bayle's separate post-fight grace remains withheld.

- **Pinned the fix for Leyndell's eastern exit grace leak (#323).** Forbidden Lands stays with
  Mountaintops, while both Divine Tower of East Altus graces stay with Altus.

- **Boss-gated grace provenance is now generated from game events (#358).** The 49 graces hidden
  behind common event 9005810 now ship with their map, asset, and gate flag instead of living only
  as an unexplained hand-copied skip set. Generation refuses a truncated derivation; grant behavior
  is unchanged.

- **Locked sweep boss names can be revealed without exposing their regions (#1184).** A new default-off YAML option lets the tracker name bosses whose sweep payouts are held behind unopened region locks, while the locked region and pending payout count remain hidden.

- **Mine-stone deposits are rerolled into useful consumables per seed (#1095).** The 133 verified
  repeatable deposits remain ordinary non-check pickups, but their 11 shared reward templates no
  longer provide fixed tiers that bypass progressive bell bearings. Quantities, respawn behavior,
  AP location count, inventory, and Ancient Dragon capstones remain unchanged. Disable
  `reroll_mine_materials` to retain vanilla mine rewards.
- **Progressive Flask Upgrades can be confined to important checks (#1090).** The new
  `flask_upgrades_on_progression_surface` option defaults off. When enabled it starts with the
  selected Progression Surface and widens through the existing reviewed fallback ladder only when
  needed to fit every copy; flask upgrades remain useful and never become logic or victory gates.
- **Morgott's randomized arena boss now opens the two post-Morgott golden seals (#1100).** The
  Morgott sweep credits Melina's post-boss Rold Medallion check and restores its vanilla acquisition
  flag, opening both the Cathedral bottom seal and the Divine Tower approach without granting the
  randomized medallion item directly.
- **Fia's Mending Rune can no longer hold its own Cursemark prerequisite (#1085).** The placement
  rule now follows the extracted handover, NPC-state, Fortissax, and corpse-award chain and rejects
  a same-player Cursemark of Death at that dependent check.
- **The Tonic of Forgetfulness stays suppressed across all of its known grant lots (#957).** Both
  shared-flag map lots are pinned to the source-neutralisation table, covering the Rya/Patches ESD
  gift and alternate world-pickup paths without suppressing unrelated copies by item ID.
- **The Cave of Knowledge Dragon Communion Seal no longer double-pays (#999).** Its Ulcerated Tree
  Spirit reward is pinned as a weapon slot in the enemy-lot neutralisation table, rather than the
  unrelated map or goods tables with the same row-shaped data.
- **Ruin-Strewn Precipice's three Golden Rune [6] drops remain randomized checks (#950).** Their
  concrete MSB entities, generated locations, enemy lots, and emitted source-neutralisation rows
  are now pinned together so a later phantom-location cull cannot silently restore vanilla drops.
- **Shop-preview spare rows now record and prefer their vanilla inventory caps (#965).** The
  datamine emits `maxNum` and `maxRepositoryNum`, and rows with generous caps are spent first within
  each FMG capability tier, reducing cap-one purchase failures on older compatible clients.

## v0.5.4 — 2026-08-29

### What you need to update

- **Client:** Required — use the v0.5.4 client with v0.5.4 seeds.
- **APWorld:** Host-only — the room host or generator must install the matching APWorld.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — keep an active seed on its matching client/APWorld pair;
  there is no save migration.
- **Profile/assets:** No action.

Window opened 1 commit(s) PAST the v0.5.3 tag.

`CONTRACT_HASH` remains `13db0b3a`, verified by loading `contract.py`; the slot-data shape is
unchanged, while the exact-version handshake advances to 0.5.4.

Client half: clients#477. Its merged commit is pinned by the gitlink in this same change because
`contract_gen.rs` embeds the exact APWorld version even when the contract hash does not move.

`release/CHANNELS.tsv` promotes `stable` to v0.5.3 in this same commit.

Entries arrive below as they merge (rule 14: the release notes are part of the change, not part of the release).

- **Mt. Gelmir's landmark graces now reach Seethewater (#1136).** The warp menu groups the lower
  basin with areas above cliffs that cannot be climbed, so granting only Volcano Manor and Bridge
  of Iniquity could let an Altus Lock land behind Altus itself. Seethewater River is now an explicit
  landmark, independent of Academy access or Patches quest state.
- **Version-mismatch warnings can be acknowledged after reading (#1133, clients#480).** The
  full-width banner then collapses for the current connection while a persistent menu indicator
  and the full tracker/log details remain. Reconnecting shows the banner again, and acknowledgement
  never marks an unsafe client/seed pairing safe.
- **DeathLink can grant separate incoming and outgoing amnesty (#1051, clients#487).** Two new
  opt-in one-in-N controls let a seed pardon received DeathLinks and local deaths at different
  rates. Both default to one, preserving normal DeathLink; their session counters restart when the
  client reconnects.
- **The setup guide now states its upgrade and save-file rules more directly (#1160).** It keeps
  the same verified behavior and warnings while making the current-YAML recovery and the
  `ap.me3`-versus-Matt save distinction easier to scan.
- **Lansseax's final Rampartside kill now pays her sweep (#1164).** The generated owner was her
  earlier Abandoned Coffin apparition, so defeating her at the real final encounter could leave
  every Lansseax-labelled tracker check unpaid. The retreat encounter no longer pays early.
- **Progressive upgrade bells now cover spirit ashes as well as weapons (#850).** Enabling the
  existing option replaces the three Grave and three Ghost Glovewort Picker bearings with two new
  progressive ladders. One copy of each of the four upgrade ladders is placed early; Great
  Gloveworts and both Ancient Dragon stone capstones remain discrete.

## v0.5.3 — 2026-08-28

### What you need to update

- **Client:** Required — development builds and seeds use the matching v0.5.3 pair.
- **APWorld:** Host-only — the room host or generator must install the matching APWorld.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — finish an active v0.5.2 seed with its matched v0.5.2
  pair. No save migration; do not mix versions.
- **Profile/assets:** No action.

Window opened at the v0.5.2 tag. `CONTRACT_HASH` remains `13db0b3a`; the slot-data shape is
unchanged, but the exact-version handshake moves to 0.5.3. Client half: clients#469.

Entries arrive below as they merge (rule 14: the release notes are part of the change, not part
of the release).

- **The pinned client can run audited v0.4.13 seeds after a game/client update.** Compatibility is
  limited to the exact historical `dc0dc687` contract; every other version/contract mismatch keeps
  the existing warning and refusal behavior. This lets players whose game updated mid-seed finish
  without weakening the general paired-version boundary.
- **Five worldless Shaded Castle lots are no longer advertised as checks (#1077).** Their item-lot
  rows exist, but the complete map/coordinate/script corpus contains no way to acquire them. They
  stay vanilla instead of becoming tracker entries that can never fire.
- **Thirteen Seethewater/Campsite checks now belong to Mt. Gelmir (#1076).** Their warp anchors
  stand on Mt. Gelmir ground, so they no longer enter logic with Altus alone. The existing Wyndham
  Catacombs carve remains Altus; this is a targeted grace-cluster correction, not a tile-wide move.
- **Untagged checks defaulted to Roundtable Hold can no longer carry progression (#1021).** The
  generated 1.17 corpus has 53 hub-filed rows with neither a trustworthy region derivation nor a
  location-class tag, including Rennala's Balled Up gesture and several quest awards. They remain
  ordinary checks, but now join the permanent filler-only bar instead of looking reachable from
  the always-open hub to general fill.
- **The Forbidden Lands pickup trio now agrees on Mountaintops (#1075).** Golden Rune [7] and
  Dragonwound Grease join the adjacent Drawstring Fire Grease behind the Rold gate instead of
  remaining in Altus logic. The correction is per flag because play-region 63003 is also reused by
  unrelated East Altus Divine Tower and Hidden Path graces.
- **The me3 save-separation docs now explain the initial copy.** When
  `AP_me3.sl2` does not exist, me3 creates it by copying `ER0000.sl2`, so seeing
  vanilla character names in the AP menu is expected; subsequent saves are
  separate. The guides now give a direct verification, warn against loading a
  copied vanilla character while connected, and make clear that the shipped
  profile does not require the Alt Saves DLL.
- **The #1085 questline-DAG regen now replaces its TSV atomically on Windows (#1110).** The
  generator no longer opens and truncates the existing destination directly, avoiding the observed
  `OSError: [Errno 22] Invalid argument` and ensuring a failed write cannot leave a partial table.
- **The website update verdict is now reviewed and CI-gated.** `release/latest.json` lives in the
  repo as a generated projection of `CHANNELS.tsv` and `CONTRACT-VERSIONS.tsv`. The deploy installs
  those exact bytes only after verifying their stable version, contract hash, and release URL, so a
  stale projection fails closed instead of being silently composed on the host.
- **Tarnished Pack equipment can now enter the randomized pool (#1096).** A new default-off
  ownership toggle admits the eight verified player weapons/shields and all 18 pieces from the four
  new armor families. Each starts as honorary S tier in the pool builder. The two NPC-only weapon
  bases and three Spectral Steed unlock goods remain excluded; this slice adds items, not locations.
- **Tarnished Pack merchants now contribute 11 checks when that ownership toggle is enabled
  (#1096).** The verified limited-stock purchases for the Hefty Scimitar, Steel set, Silver Grooved
  Shield and set, and Reverse-Bladed Sword join the seed alongside the pack gear. They remain absent
  by default, and are deliberately separate from the Shadow of the Erdtree ownership gate.
- **Three Tarnished Pack corpse pickups now join enabled seeds (#1096).** Idus Sword near Liurnia
  Lake Shore, Ritual Thrusting Shield near the Isolated Merchant's Shack, and Reed Great Katana near
  Fort Faroth are backed by their live 1.17 lot, asset, map, and position joins. Existing merchant
  check IDs remain unchanged; these checks append to the optional Tarnished Pack suffix.
- **The unobtainable Stormveil Neutralizing Boluses check is removed (#1111).** The complete ESD
  corpus confirms its only award branch requires flag 10009335, while the combined ESD, EMEVD, and
  parameter inputs contain no setter or default for that flag. The vanilla lot remains untouched;
  it is now explicitly ledgered as an unused ESD award instead of entering the randomized pool.
- **Matt's randomizer can restore Torrent on Elden Ring 1.17.** Its current `regulation.bin`
  replaces the complete `RideParam` table with the older four-row version, so Torrent stops
  answering the whistle. `tools/install_into_matts_rando.py --with-torrent-repair` restores only the four
  verified vanilla 1.17 rows after randomization; rerun it whenever Matt generates a new seed. The
  same focused patcher is published independently as `torrent-repair-v1.0.0`.
- **Sellia's Secret cannot contain its own consumed Unalloyed Gold Needle (#1085).** The questline
  extractor proves Gowry consumes the Needle before the route opens, and logic now requires that
  item for the Sellia's Secret checks instead of allowing it to be placed behind itself.
- **The F6 tracker explains the deliberately withheld finale-region Lock (#1128).** It identifies
  the Lock as automatic and absent from the pool, lists the authoritative outstanding goal-gate
  requirements, and confirms when the region opens. This explanation remains visible even when
  the paid Lock-hint economy is unavailable.
- **F6 shows both halves of Leyndell's compound gate (#1130).** The line reports
  `Leyndell Lock` held/missing, AP Great Runes received/required using the resolved seed threshold,
  and the resulting open/closed state. It is omitted for lockless and zero-threshold seeds and
  changes no enforcement behavior.
- **Client gitlink -> `7e18a819` (clients#473, #475, #476).** This is the release candidate after
  the v0.5.3 window-opening client: the audited v0.4.13 bridge plus the finale-Lock and Leyndell
  tracker explanations. The historical bridge accepts only v0.4.13's exact `dc0dc687` contract;
  arbitrary mismatches remain refused.

## v0.5.2 — 2026-08-27

### What you need to update

- **Client:** Required — use the v0.5.2 client with v0.5.2 seeds; the exact-version handshake
  moves even though the slot-data shape does not.
- **APWorld:** Host-only — the room host or generator must install v0.5.2; joining players only
  need the matching client.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — finish an active v0.5.1 seed with its matched v0.5.1
  pair. No save migration; do not mix versions.
- **Profile/assets:** No action.

Window opened AT the v0.5.1 tag with zero commits past it, in the promotion change; nothing is
carried over.

`CONTRACT_HASH` remains `13db0b3a`, verified by loading `contract.py` after the bump. The
slot-data shape is unchanged — `abilityUnlockItems` is still the newest key — but the
exact-version handshake still moves to 0.5.2.

Client half: clients#459, merged as `0f359e19`. Its merge commit is pinned by the gitlink in this same change.

`release/CHANNELS.tsv` promotes `stable` to v0.5.1 in this same change, at its tag.

Entries arrive below as they merge (rule 14: the release notes are part of the change, not part of the release).

- **Yura reward check f400163 is now labelled as Nagakiba with Piercing Fang (#1082).** Its category-6 custom-weapon lot was previously overridden by the colliding goods id for Tibia Summons; the location now names the actual weapon while preserving Nagakiba as the shuffled catalog item.

- **Leyndell Golden Seed descriptions now identify the correct checks (#972).** The sapling pickup near East Capital Rampart and the Ulcerated Tree Spirit death award had each others descriptions; the two labels are now swapped back without changing their AP ids or rewards.

- 🛑 **82% of location names change wording: a sweep clause now states ELIGIBILITY, never a grant (#936).** 4,063 of the 4,948 shipped location names carried a baked `, also granted by BOSS (tile)` clause; all 4,063 now read `, may be sweep-granted by BOSS (tile)`. **No AP id moves and no location is added or removed** -- the regen diff is 4,063 name strings and the generation stamp, with the 4,948 `(ap id, flag)` pairs byte-identical, `gen_contract` 3/3 unchanged (`CONTRACT_HASH` still `13db0b3a`) and `gen_region_locks` "up to date" at the pinned gitlink. **Why:** a location name rides the STATIC AP datapackage, minted once for the whole corpus, so it cannot see a seed. What a seed actually pays out is the `dungeon_sweep` rung narrowed by the progression-surface cut -- and for a `dungeon_sweep: none` seed that is *no* sweep at all, which made every one of those 4,063 clauses false. Three players read the promise and reported it: Haraldwyrm, 2026-08-20, *"some items say they are granted as sweep rewards when they are not, like golden seeds and crystal tears"*; then colombius, 2026-08-27, on `Mountaintops of the Giants :: Golden Seed - near Foot of the Forge, by two snow trolls, also granted by Fire Giant (m60_52_52) [f1052537800]` -- ap 7773183, a `Seedtree`, which his seed's surface cut had correctly taken back out of the Fire Giant sweep. Generation was right every time; the **name** was the liar. Alaric's ruling, 2026-08-27: *"when we are leaving them off sweeps, we shouldn't say they're granted by the sweep."* Eligibility is the fact the corpus actually knows, so the new wording is true in every seed, and #670's answer to *"so idk what boss to kill?"* survives where it can be checked: a reader holding the seed -- the F6 tracker, via slot_data `dungeonSweepFlags` -- still narrows the clause to a definite grant or strips it (clients#348, shipped v0.5.0), and our check browser, which has no seed at all, renders it as eligibility (#1083). What changed here is the half we could not otherwise reach: the spoiler log, server `!hint`, text clients and third-party trackers all resolve names from that static datapackage and will now read an honest one. `desc_sources.sweep_clause` is the single writer and `SWEEP_CLAUSE_OPENER` beside it is the single opener every reader cuts on, so this was one edit plus a regen. 🛑 The clause keeps its SHAPE -- a `", "`-opened tail whose only parenthesis is the tile, sitting last before `[fNNNN]` -- because every reader strips it back off by that shape, and folding boss and tile into one parenthesis would NEST for a boss whose own name has parens (`Night's Cavalry (Glaive)`).

- **Client gitlink -> `d4c549b` (clients#460 + #461).** #460 is this rename's client half: the
  tracker's sweep-clause stripper reads BOTH the old and new wording, so v0.5.1 seeds keep
  working. #461 is the Tarnished client: Elden Ring 2.7.0.0 AND the Japanese 2.7.0.1 supported
  on upstream's real address tables (fromsoftware-rs `0b44ede3` + our fork re-adding the
  2.6.2 arms upstream dropped) -- all four game versions live in one build. The v0.5.1 client's
  derived candidate table matched upstream's real one 93/93 and is retired.
  - 🛑 **Compat, the same shape as the Enia id shift:** a v0.5.1-and-earlier seed's names are frozen in the server's datapackage and are never reworded, so **spoiler logs, hints and trackers from seeds generated before v0.5.2 keep the old "also granted by" wording** -- as do any notes, screenshots or issue reports quoting them. Nothing breaks: the v0.5.2 client recognises **both** openers (clients#460) and filters either against seed truth, so an older seed played with the newer client is fixed exactly as it was before. Only third-party tooling that string-matches the old clause needs the new one, and matching `may be sweep-granted by` alongside it is the whole change.

## v0.5.1 — 2026-08-24

### What you need to update

- **Client:** Required — use the v0.5.1 client with v0.5.1 seeds; the exact-version handshake
  moves even though the slot-data shape does not.
- **APWorld:** Host-only — the room host or generator must install v0.5.1; joining players only
  need the matching client.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — finish an active v0.5.0 seed with its matched v0.5.0
  pair. No save migration; do not mix versions.
- **Profile/assets:** No action.
- 🛑 **AP ids moved.** Enia's 100 shop checks left the pool (#1013), so `locations` goes
  5048 -> 4948 and every id after hers shifts down by 100. A v0.5.0 spoiler log or external
  tracker will name the wrong check; an in-flight seed is unaffected on its matched v0.5.0 pair.

Window opened AT the v0.5.0 tag with zero commits past it, in the promotion change; nothing is
carried over.

`CONTRACT_HASH` remains `13db0b3a`, verified by loading `contract.py` after the bump. The
slot-data shape is unchanged — `abilityUnlockItems` is still the newest key — but the
exact-version handshake still moves to 0.5.1.

Client half: clients#414. Its merge commit is pinned by the gitlink in this same change.

`release/CHANNELS.tsv` promotes `stable` to v0.5.0 in this same change — the first stable
promotion since v0.4.13, and the one the v0.5.0 window deliberately deferred until its tag.

Entries arrive below as they merge (rule 14: the release notes are part of the change, not part of the release).

### Added

- **Report a check from the check browser, and land on an issue form that already knows which check it is.** Asked for by **Alaric** (2026-08-27). Every check's detail pane now offers *report a problem with this check* beside the existing *just the region is wrong* link. It opens `.github/ISSUE_TEMPLATE/check-report.yml` with the check's identity and the browser's evidence already filled in: name, AP id, event flag, assigned region, nearest grace, map tile(s), tags, how the region was decided, and the other regions sharing that tile. The player supplies the half only they have — what actually happened (never fired / gave the vanilla item / gave vanilla *and* the Archipelago item / could not reach it / wrong region / something else), the F6 build banner, the yaml, and the log. 🛑 **No backend and no new request.** A static page cannot POST; the link is a plain `<a href>` navigation to `github.com/.../issues/new?template=…&title=…&check=…&facts=…`, so the page still fetches nothing at load and works from a file, from peliarch and offline alike. Prefill keys on the field `id`, and **only `input` and `textarea` fields prefill from a URL** — which is why `symptom` is a dropdown the player picks and not a guess the page makes; the browser does not know what happened to you, and a page that guessed would be claiming a verdict it has no business claiming. Gated by `ReportAProblemLink` in `test_gf_check_browser.py`: the link is in the template *and* in the shipped page, the page still contains no `fetch`/`XMLHttpRequest`/`WebSocket`, and the URL is evaluated **under node from the shipped page's own builder** — not a python rewrite of it, which would only agree with itself — then parsed with `urllib.parse` and checked round-trip over the first row, the last row and 60 rows whose names carry `&`, `#`, `+`, `%`, quotes, commas or an en-dash. Every prefilled parameter is asserted to name a real text field in the form, because GitHub ignores an unknown key silently and the form would simply open empty.

- **The front page said 4,931 checks. The world defines 4,948, and had since v0.5.1.** Enia's 100 shop checks left the pool in #1013 (`locations` 5048 -> 4948) and `wizard/landing.html` — a hand-written page with no build step, deployed straight from main by `deploy_wizard.sh --site` — kept its old number through that window and every regen since. Nothing anywhere could notice, which is the actual defect. Both occurrences are now marked `data-derived="checks-catalogued"` and gated by `LandingNumbersAreCurrent` in `test_gf_publish_channels.py`, a `generators` suite: every marked number must equal the count the world defines, **two independent derivations of that count must agree** (`wizard/region-census.json`'s per-region sum and the shipped check browser's payload length, built by different tools from the same data — if they ever disagree the page's number is unanswerable and red is the right answer), and a catalogued-check count written into the prose *without* the marker fails too, since that is exactly how it drifted the first time. The page stays static: this is a marker plus a gate, not a build step, because being on the `--site` fast path is the whole point of that file.

- **`spawn_traps` takes enemy NAMES now, not only model ids.** Asked for by **SwiftyTaco** on
  Discord (2026-08-26) — *"Am I supposed to put in ids, or the name of the enemy?"* — after writing
  character model ids into `traps`, the option next to it, which takes words. Both halves of that
  confusion are answered. `spawn_traps: [Basilisk, Runebear]` now means exactly what
  `spawn_traps: ["4150", "4630"]` means, case and accents ignored (`Merchant Kale` finds
  `Merchant Kalé`), and a model id written into `traps` no longer gets the stock
  `Found unexpected key 4150 … Allowed keys: frozenset({…})` — it gets a sentence saying ids go in
  `spawn_traps`, which takes ids *and* names. A misspelled name is still a generation-time error,
  never a silent skip, but the error names its nearest matches: `'Basilsk' — did you mean
  Basilisk?`. 🛑 **35 of the 390 spawnable models have a name, and the other 355 cannot get one
  here.** Elden Ring never writes an enemy's name on screen: outside `NpcName.fmg.xml` — reached
  through `NpcParam.nameId`, set on 31 of these models — there is no name in the game data to use,
  and the `Name` column of both `NpcParam` and `AtkParam_Npc` is empty in all 7039 / 12855 rows. The
  wiki names everyone thinks of are not the game's, and this project does not invent data, so the
  rest stay reachable by id exactly as before. The four extra names are ones already published here
  (`Runebear`, `Basilisk`, `Malenia (Phase 1)`, `Aging Untouchable`). The table is
  `greenfield/eldenring/enemy_names.py`, datamined by `tools/datamine_enemy_names.py --check`; a
  name two models share (Latenna, Smithing Master Hewg, Rennala — one NPC, two bodies) resolves to
  the lowest model id, recorded in the table itself. **No client change and no contract change:**
  names are resolved to ids at generation, the minted item name is byte-identical whichever
  spelling you wrote, and `CONTRACT_HASH` stays `13db0b3a` (pinned by a test). The wizard's
  free-text box takes names too — it splits on commas and newlines rather than on every non-word
  character, so a name with spaces survives being typed — and `release/EldenRing.yaml`, the wizard
  metadata and `wizard.html` are regenerated. (#1063)

- **SPEC-map-for-goblins.md.** Integration spec for the Map For Goblins DLL Edition v2.1.2
  (bobler's link): phase A ships it as an opt-in companion native -- its `live_loot_flags`
  mode already hides markers on our check flags and `anonymous_loot` gives a spoiler-free
  check map -- gated on one Windows acceptance session; phase C (native map icons for the
  non-lot corpus + tracker coloring) stays the roadmap. Supersedes the K3 recon, which
  analyzed the 2024 file-based edition.

- **Client gitlink -> `3e62e09` (clients#419-#434).** Rode in with the regenerated
  `grace_ground.tsv` (`b131d034`). All Bloodborne-client work (native attach/reconnect, grant
  observation, backend enum) plus the console/`--log-file` tee (clients#426); no Elden Ring
  gameplay change. This entry pays the bump's rule-14 note after the fact -- the commit itself
  landed without one and redded main.

- **The PlayArea scan now RULES the region audit, and the worksheet says which rows it ruled.** Developer tool, no player-facing change; no check's region moves in this change. `greenfield/item_play_regions.tsv` (5,295 placement rows over 4,086 flags) landed on main; step 5 of `docs/PLAYAREA-ITEM-SCAN.md` is now wired. `tools/msb_region_vote.py` prefers it: where a flag has an EXACT answer the nearest-grace vote is REPLACED (`vote_note=PLAYAREA-CONFIRMED`, no anchor, no distance -- a ruling has no hop to disbelieve), and where it does not, the heuristic stands untouched with its existing notes. 🛑 **EXACT means `volume:`/`interior-vol:`/`seam:`/`interior-seam:` and nothing else.** `tile-default`/`interior-map` are the SAME tile-wide guess the vote already is -- letting one confirm would relabel the guess as geometry and the row would stop being adjudicated, because a fallback agreeing with a fallback cannot fail; `none` is not evidence about the region at all. 746 flags earn a ruling repo-wide, 17 of them inside the 305-row audit set. The audit's settled/manual split moves to **230 heuristic-agree + 16 ruled-agree + 1 ruled-DISAGREE + 21 heuristic-disagree + 37 not votable**; `cast` rises 260 -> 268 because a ruling is keyed by FLAG and needs no coordinate row of its own. The worksheet page renders a ruling in its own class (`vote-ruled`, badged `RULING:`) and the header calibration caveat now says in as many words that it DOES NOT APPLY to those rows. The calibration itself was re-measured, not edited: **92.9% on a 2,169-check control set**, with the 518 ruled rows EXCLUDED from the control population rather than flattering the number. Two operational repairs ride along, both of which had already destroyed data once in this session: `audit_region_second_opinion.py --revote` refreshes ONLY the vote columns of the committed report (plain `--offline` on a box with no wiki cache silently rewrites `verdict`/`external_regions` as NO-DATA, throwing away a rate-limited crawl), and `--revote` re-reads `our_region` from `check_region_triage.tsv` instead of carrying the crawl's copy, because data.py moves under this file and a fresh vote compared against a stale region invents disagreements and hides real ones. Gated by 47 tests in `test_gf_region_second_opinion.py` (exact-beats-heuristic AND its mirror, a synthetic scan table pinning that every fallback source, every unowned bucket and every two-region answer is REFUSED, a ruling standing with no coords row, the live table's rulings all traced to exact sources, and the re-measured counts) and 35 in `test_gf_region_second_opinion_page.py` (the ruling class exists, is exempt from the caveat, has no anchor, and is not an unfired guard).

  🛑 **What the scan did NOT settle, which is the finding the runbook's step 4 asked for.** Step 4 predicted the exact answer would disagree with the vote on roughly one row in ten and named three clusters it would settle. It settles almost none of them: of the 305 audit flags, **17 got an exact answer, 10 answered from a tile default, 241 answered `none`, and 37 have no scan row at all.** All **19** Yelough Anix Tunnel rows (`SUSPECT-ANCHOR`, the Mountaintops/Consecrated Snowfield block) answer `none` -- no volume, no seam, and no `PlayRegionParam` default for their tiles -- so the scan settles them in NEITHER direction. So do both Weeping rows anchored on 76113 Seaside Ruins (`1042347000`, `1042347030`), and two of the three Bestial Sanctum `CROSS-TILE-MSB` rows (the third, `1051417030`, answers `tile-default`, which does not confirm). Absence of an answer is not evidence about the region, and those rows stay on the heuristic and stay unadjudicated. The scan is decisive where it is decisive: 679 checks repo-wide carry an exact answer and 114 of those disagree with the region data.py gives them today -- but a large share of the disagreements are NPC-relocation artifacts (Patches/Thiollier/Moore/Bernahl shop rows whose coordinate is where the NPC ENDED UP, not where the check is), so that list is a candidate queue for `region_overrides.tsv`, not a bulk move. #1046's 35 `Rauh Base ::` rows are the worked example: only 5 have an exact answer -- `2045467050` -> 69410 and `2045477020` -> 69400 (both Ancient Ruins, confirming 255's report), `2046457000` -> 68100 (Gravesite), and two confirming Rauh Base -- with the other 86 Rauh rows split 33 tile-default / 28 `none` / 25 with no scan row.

- **The PlayArea calibration gate and `grace_ground.tsv` now read the grace population out of ONE generator.** Developer tool, no player-facing change, no committed output moves. `datamine_item_play_regions.py --graces` is the gate that decides whether the item scan has earned an opinion about check regions: it re-derives all 421 warp graces and diffs them against the committed `greenfield/grace_ground.tsv`. #1050 made the two tools share ONE ladder (`derive_ground`) so they judge a point the same way; they were still two separate readers of `BonfireWarpParam`, and the copies had drifted. Both derive from the grace's BWP **spawn position** (`posX/posY/posZ`) -- the point the player materialises at, and therefore the point the client's kick-watch evaluates `play_region` at on warp-in, which is the whole reason this table is trustworthy -- but a row whose spawn position does not PARSE was emitted with a map-default fallback by `datamine_grace_ground` and silently `continue`d past by the gate. A grace the gate never compares is not a grace the gate blessed, and the gate's population being quietly smaller than the table's is exactly the "a partial census read as complete" failure this file's refusals exist for. `datamine_grace_ground.grace_rows()` is now the single generator of that population -- flag, map id, authored tile, spawn-derived ids, source, with the `MEASURED_GROUND` in-game override applied once inside it -- and the gate's own `grace_rows` is a projection of it, so the two tools can no more read different POINTS than they can run different ladders. 🛑 The distinction the runbook now states in one line: the spawn position is **not** the grace ASSET coordinate that `greenfield/item_grace_coords.tsv` carries under the same flag. The two are metres apart at some graces, and a gate that judged one against the other would report `seam:`/`none` deltas that are artifacts of comparing two different points rather than findings about the corpus -- the failure mode a fixture grace now pins against permanently. This is a PURE REFACTOR of `datamine_grace_ground`'s own output, asserted byte-for-byte against the pre-refactor emitted table over the synthetic MSB corpus, so the runbook's step-3 regen expectations (the three seam upgrades, the two source upgrades, the TAB-in-a-name repair) are unchanged. Gated by four new tests in `test_gf_item_play_regions.py`: the unparseable-spawn grace must be COMPARED (RED on the previous gate, which skipped it), the two `grace_rows` must be the same rows (RED on the previous pair), the emitted table must be byte-identical to the pre-refactor golden, and a fixture grace whose asset coordinate and spawn position straddle `SEAM_SLACK` must be answered from the SPAWN point -- alongside the existing one-function-object assertion for the ladder.

- **PlayArea scan volume floor measured, not guessed (box run, 255's region reports).** The item
  play-region scan's `VOL_FLOOR = 1000` FATAL'd Alaric's comprehensive witchy export (1,346 msb-dcx
  dirs) because the true overworld PlayArea count is 497 -- volumes exist at play-region boundaries,
  not per tile. Floor re-pinned at 400 against the measurement; the `--graces` calibration diff
  remains the decisive partial-export catch. Runbook updated to the measured expectation.

- **`full_area_sweeps` -- an opt-in "the boss hands you the WHOLE area" (#1033).** Asked for by siffrin ("does killing a boss give me every item in the area? i only have 1 region and i already killed loreta and malenia and im not sure what else to check") and previously by bobler. Off by default, and off is byte-identical to v0.5.0: a sweep still pays out the area's ordinary loot and still leaves the classes on your `progression_surface` where they lie, because that is where the seed hid its Locks. Turn it on and the per-seed surface cut stops running: **+113 member links at the default surface (4101 -> 4214)** -- Scadutree Fragments 40, Golden Seeds 38, Revered Spirit Ashes 22, Sacred Tears 13 -- up to +215 for a seed that puts all six of the collectathon/rarity classes on its surface, and exactly zero for a seed with an empty surface (an empty surface claims nothing, so there is nothing to restore). The trigger set does not move: 211 groups before and after. It widens MEMBERSHIP only -- `dungeon_sweep` still decides which bosses sweep, and the #445 arena-reachability drop, the region-consistency invariant and the HUB quarantine are untouched, because a check swept into the wrong region is permanently unobtainable and no option may override that. It also does NOT lift the permanent floor: another boss's reward, remembrance or Great Rune, quest/gate key items and merchant stock are cut when the sweep is BUILT and no yaml restores them. A seed with it on can be handed its own region Locks (and, at the default `confine_foreign_progression`, another player's items) on a boss kill -- that is the feature, and it cannot strand anyone, because a sweep member's access rule is its own region and the trigger boss stands in a region the seed kept, so the sweep only makes a reachable check arrive earlier. Missable checks are unaffected in either direction: they have never been filtered from sweeps (170 of the 289 are members today), so a sweep already rescues most of them. **No client change and no contract change** -- membership rides in per-seed slot data (`dungeonSweepFlags`), so a widened list is just a bigger list on the wire and an older client follows it without knowing the option exists; `CONTRACT_HASH` does not move and no `requiresClientFeatures` is emitted. For the record, what stays UNSWEPT after the option is on is mostly not sweepable at all: on a Liurnia seed the remaining 142 are 105 merchant rows, 22 boss rewards and 15 checks whose position was never recovered from the game data (the last group is issue #852's shape, not this one's).

- **`--path <artifacts-root>` on every datamine tool that reads the extracted corpus.** Developer tool, no player-facing change. `elden_ring_artifacts/` is licensing-restricted and never committed, so it lives wherever its owner keeps it -- and it moved, which until now meant editing nine tools that each hardcoded `<repo>/elden_ring_artifacts`. They now share ONE flag and ONE implementation (`tools/artifacts_root.py`): `datamine_grace_ground`, `datamine_item_grace_coords`, `datamine_item_play_regions`, `datamine_msb_item_regions`, `datamine_arena_graces`, `datamine_merchant_shops`, `datamine_dungeon_regions`, `datamine_msb_gated_treasures` (where `--path DIR` means `--root DIR/mapstudio`, and `--root` still wins) and `probe_msb_mapversions` (where it moves where auto-detection looks). The default is unchanged -- absent the flag every tool reads `elden_ring_artifacts/` beside the repo root, byte for byte as before -- and the three tools that already shipped `--artifacts` keep it as an ALIAS of `--path`, so every command in `docs/PLAYAREA-ITEM-SCAN.md` still works verbatim. There is deliberately NO environment-variable fallback: an invisible input is how a scan reads a stale corpus and writes a plausible table, and `ER_EVENT_DIR` already costs us that on the EMEVD side. 🛑 The dangerous half is not parsing the flag, it is a tool that parses it and keeps reading the old root -- two of these built module-level caches AT IMPORT off the old root (`datamine_arena_graces`'s boss/NPC names, `datamine_merchant_shops`'s NpcName FMG list), so their seams REBUILD those rather than only moving path strings. Gated by `test_gf_artifacts_path.py` (8 tests: the helper's default and its refusal of a non-directory, the no-env-var invariant asserted against the source, a census that pins which tools must expose `--path` and which must still accept `--artifacts`, and -- the load-bearing one -- every seam CALLED and every named input asserted to have moved under the new root and to have defaulted under the old one), plus `--path`/`--artifacts` run to byte-identical rows over the synthetic MSB fixtures in `test_gf_item_play_regions.py`. The runbook shows the flag on each command.

- **The witchy'd MSBs are FOUND under the artifacts root now, not assumed to be in `map/`.** Developer tool, no player-facing change. `--path` said WHERE the corpus is; it never said where the unpacked MSBs sit INSIDE it, and each tool answered that privately -- `datamine_grace_ground` read `map/` only, `datamine_arena_graces` read `map/` + `mapstudio/`, `datamine_merchant_shops` read `mapstudio/` + `map/mapstudio/`, `datamine_msb_item_regions` read `mapstudio/` + the root, `datamine_item_grace_coords` read all three, `datamine_msb_gated_treasures` hardcoded `<path>/mapstudio`, and `probe_msb_mapversions` guessed six names. So a WitchyBND export whose maps landed FLAT under `<root>/mapstudio/` -- which is the shape Alaric's export actually has -- ran the same corpus two ways: some tools read it and `datamine_grace_ground.py --path <root>` said `FATAL: no witchy'd m60/m61 MSBs under <root>/map`. That is N copies of one decision disagreeing, which is the exact class of bug `--path` itself was written to kill. There is now ONE candidate list in `tools/artifacts_root.py` -- `<root>/map`, `<root>/mapstudio`, `<root>/map/mapstudio`, then `<root>` itself -- and every MSB-reading tool resolves through it: the one-dir scanners take the first hit, the several-dir scanners (whose reason is real: in 2026-07 `mapstudio/` held 66 of the 118 boss maps while `map/` held all of them) take every hit in the same order. 🛑 A hit is DEMONSTRATED, never assumed: a candidate counts only when it DIRECTLY contains `m??_??_??_??-msb-dcx` children, which is what makes the bare-root layout safe -- a corpus root full of `_pilot`, `breakgeom`, `m00`..`m61` siblings is not mistaken for an MSB dir, and an EMPTY `map/` no longer shadows a populated `mapstudio/`. The narrower flags still win outright (`--root` on `datamine_msb_gated_treasures` and `probe_msb_mapversions`), the defaults do not move, and NO committed output changes -- this is discovery only, asserted byte-identical over the synthetic MSB fixtures. Every FATAL now names every location tried, because a message that names one path teaches the reader the wrong layout. Gated by seven new tests in `test_gf_artifacts_path.py` (the three layouts; `map/` still winning over `mapstudio/`; noise siblings not faking a flat root; an empty `map/` not shadowing; the FATAL naming every candidate; and the motivating case -- a tree shaped exactly like Alaric's resolving for all seven tools off plain `--path <root>`) plus one in `test_gf_item_play_regions.py` running the same fixture corpus from `map/`, `mapstudio/` and the bare root to byte-identical rows.

- **Second-opinion region audit (`tools/audit_region_second_opinion.py`).** Developer tool, no player-facing change. The 305 checks whose names still say `(region unconfirmed)` got their region from a nearest-neighbour hop that cannot fail, so nothing in this repo can tell us which of them are wrong. The tool asks an independent corpus -- Eldenpedia (eldenring.wiki.gg, CC BY-SA 4.0), with the Fandom Elden Ring Wiki (CC BY-SA 3.0) as fallback -- where each check's vanilla item is found, maps the answer into our region vocabulary through a hand-written table, and prints AGREE / DISAGREE / AMBIGUOUS / NO-DATA per check. ERDB (MIT) was evaluated and is not used as a location source: its datamined params carry no placement field. Fextralife is deliberately not consulted. First run over all 305: 51 AGREE, 16 DISAGREE, 3 AMBIGUOUS, 26 NO-DATA, 209 AMBIGUOUS-GENERIC (an item with many vanilla copies cannot name one placement, so the tool refuses those without a request). Output is `greenfield/check_region_second_opinion.tsv` and `greenfield/CHECK-REGION-SECOND-OPINION.md` -- verdicts, region names and page titles only; no wiki prose is committed and the response cache is off-repo. It is a CANDIDATE list for hand-adjudication, never a cull list: NO-DATA means "not readable there", not "the check is fine".
- **Region second-opinion worksheet page (`er-archipelago-region-second-opinion.html`).** Developer tool, no player-facing change. The audit above produced 305 rows and no ruling; this is the offline page for making the rulings. Same self-contained shape as the check browser -- one file, no server, no CDN, nothing fetched at view time -- with the rows grouped DISAGREE (12 units) -> AMBIGUOUS (3) -> NO-DATA (23) -> AGREE (42), and the 209 generic-name rows collapsed and unrendered until asked for, because a reader who scrolls into 209 sourceless rows starts adjudicating noise. Each row carries our region, the wiki's, the item, the tile, how the region was decided (`check_region_triage.tsv`), and a LINK to the source page; per row there are four rulings -- ours right / wiki right / needs MSB look / generic collision -- plus a free-text note, held client-side only and exported as a paste-ready `flag / ap_ids / audit_verdict / adjudication / note` TSV into both the clipboard and a textarea (a `file://` page cannot hand over a download). 🛑 The adjudication unit is the FLAG, not the tsv row: eight flags carry several ap ids (the Scaled set is one flag with four) and `region_of` decides per flag, so they merge into one row listing every id it speaks for. Adjacent m60 tiles are badged as clusters -- a HINT that a run of checks shared one nearest-neighbour hop, not evidence that the hop was wrong. Built by `tools/build_region_second_opinion_page.py`, wired into `tools/regen_all.py`, and gated by `test_gf_region_second_opinion_page.py` (24 tests: totality against the tsv, the flag-is-the-unit invariant, NO-DATA-is-not-AGREE, the export contract, no external request, byte-identical regen).
- **An MSB nearest-grace VOTE beside the wiki verdict, and the runbook for the exact answer.** Developer tool, no player-facing change. The second-opinion audit could only speak about 96 of the 305 unconfirmed checks -- its join key is the ITEM NAME, and 209 rows are items like `Smithing Stone [1]` that one wiki page covers everywhere in the game. `tools/msb_region_vote.py` asks a different question of data we already own: fold the check's committed MSB coordinates into the overworld frame (through `tools/overworld_fold.py`, the single shared fold) and vote the region of the NEAREST region-attributed Site of Grace, out of 338 graces attributed via `grace_region_map.tsv` + `grace_ground.tsv` + `REGION_PLAY_IDS`. It votes on 260 of the 305: 241 back our region, 19 do not. `check_region_second_opinion.tsv` gains five columns (`msb_vote_region`, `vote_distance_m`, `vote_unanimous`, `vote_anchor_grace`, `vote_note`) and the worksheet page gains a colour-coded vote column -- backs us / backs the wiki / backs NEITHER / no vote -- with a filter for each and the anchor grace and distance always beside the region. 🛑 IT IS 91.4% ACCURATE AND IT IS NOT INDEPENDENT OF US: `--calibrate` re-derives that figure over 2607 control checks, and it is the same nearest-neighbour shape as the hop that gave these checks their regions, so a vote that AGREES corroborates nothing. That sentence is in the tsv header and across the top of the page, because a number that travels without its caveat becomes an authority. Rows whose anchoring grace got its OWN region from a tile-default row are badged `SUSPECT-ANCHOR`: 17 of the 19 votes-against ride ONE such grace (73211, Yelough Anix Tunnel) and flip Mountaintops rows to Consecrated Snowfield as a block -- a cluster to explain, not 17 defects. `vote_note` also carries `NO-COORDS` (45 rows), `CROSS-TILE-MSB` (3 Bestial Sanctum checks labelled m60_51_41 whose coords are authored in m60_51_43), `COARSE-LOD` and `MULTI-PLACEMENT`. The decisive instrument is not this: `docs/PLAYAREA-ITEM-SCAN.md` is the runbook for pointing `datamine_grace_ground.py`'s Box/Cylinder/Sphere/Composite point-in-volume machinery at item coordinates instead of the 421 graces, which reads the exact runtime `PlayRegionID` the client's kick-watch reads. It needs the extracted MSB corpus, so it runs on Alaric's box; when it has run, its answers REPLACE the votes (`vote_note=PLAYAREA-CONFIRMED`) rather than averaging with them. Gated by 41 tests in `test_gf_region_second_opinion.py` (the vote geometry on synthetic fixtures -- nearer-grace-wins AND its mirror, the LOD1/2 fold pinned against `overworld_fold`, every note, and the calibration re-derived rather than remembered) and 34 in `test_gf_region_second_opinion_page.py` (vote column, side classification, SUSPECT-ANCHOR badge, the disagrees filter, no vote without its distance and anchor).

- **A seed that locks every attack now hands you one attack back, early.** With
  `ability_lock_mode: progressive` and all four attack inputs locked
  (`locked_abilities: [r1, r2, l1, l2]`), you started the seed unable to damage anything -- and a
  great many checks are kill-gated: boss defeats, enemy drops, and every dungeon sweep that pays
  out on a defeat flag. Logic knows nothing about the locked set, so all four `Unlock:` items could
  sit behind checks that need a kill. Now, in exactly that case, `Unlock: R1` is declared to
  Archipelago's `early_items` -- the same seam Roll has used since v0.4.x -- so it is forced into an
  early sphere and stays exportable, meaning it is early wherever in the multiworld it lands. R1 is
  a fixed pick, not a draw: the same yaml always forces the same unlock. Lock three or fewer attacks
  and nothing is forced; you still have an attack button (fists at worst). **Spells deliberately do
  not count as an attack** -- "spells don't count, you need an L or R button to cast a spell" -- a
  staff or seal casts on an attack input, so a caster with all four locked is exactly as weaponless
  as anyone else, and there is no caster carve-out. This is the conservative mitigation, not a logic
  rule: the reachability graph is untouched, and #1035 stays open for whether a real in-logic
  "you need an attack to kill things" rule is still wanted on top. (#1035)
- **The PlayArea item scan (`tools/datamine_item_play_regions.py`).** Developer tool, no player-facing change. `docs/PLAYAREA-ITEM-SCAN.md` step 2 specified the instrument that RULES on a check's region -- the point-in-volume test against MSB `Region/PlayArea`, which reads the exact `<PlayRegionID>` the client's kick-watch reads -- and until now it existed only as prose. It exists now, and Alaric's box run is mechanical. Per item placement in `item_grace_coords.tsv` it folds the point through `tools/overworld_fold.py::world_xz` (fold FIRST, test second: an unfolded LOD2 row lands kilometres outside its own volume and answers `tile-default`, which looks like a result -- issue #338 all over again), tests it against every m60/m61 volume, falls to the interior map's own MSB, then a seam snap within `SEAM_SLACK`, then the PlayRegionParam default for the tile the FOLDED point lands on, then `-`; a `source` column names which of those answered, because a row that cannot say how it was decided is not falsifiable. Output is `greenfield/item_play_regions.tsv` (`flag / map_id / play_region_ids / buckets / source`, one row per placement -- 442 flags are placed twice and collapsing them would pick a winner by file order). NOTHING GEOMETRIC IS RE-IMPLEMENTED: `Vol`, `Vol.contains`, `_shape`, `_load_msb_playareas`, `load_volumes`, `load_interior_volumes`, `_nearest_face`, `SEAM_SLACK` and `MEASURED_GROUND` are imported from `datamine_grace_ground.py`, which gains a shared `load_play_region_defaults()` and an `--artifacts`-style `_set_artifacts_root`. `--graces` is the runbook's step 3, the calibration gate: it runs the SAME pipeline over the warp graces and diffs against the committed `grace_ground.tsv` -- the table calibrated against two in-game kick measurements -- exiting non-zero on a bucket mismatch. Run it before trusting one item answer. Two refusals, neither bypassable except by a `--force` whose help text warns against it: a degenerate scan (fewer than 1000 volumes = a partial witchy export) and a shrinking table (fewer derived rows than the committed one, or than 2000 on a first run). 11 tests in `test_gf_item_play_regions.py` -- the first suite in the repo to witness a datamine tool's GEOMETRY rather than its committed output: a hand-built witchy-style MSB tree with a yaw-rotated Box, a Cylinder, a Sphere and a Composite, the seam and its past-the-slack mirror, the tile-default fallthrough, a cross-tile row that must answer from its `map_id` and not its label, the LOD2 fold as a RED/GREEN PAIR, both refusals, and `--graces` clean against a fixture ground plus its falsifier. It does NOT change any check's region: a confirmed answer is a candidate for `region_overrides.tsv`, adjudicated through the worksheet like every other row.

- **The Chapel of Anticipation return is Liurnia now, not Limgrave.** The Grafted Scion's drops --
  Ornamental Straight Sword and Golden Beast Crest Shield -- sat under Limgrave on the strength of
  the prologue fight, which the game expects you to lose. The chapel floor has no Site of Grace of
  its own, so nothing the Limgrave Lock lights puts you back on it; the route that does is the Four
  Belfries -> Chapel warp, and the Belfries are Liurnia's (their Imbued Sword Key chest became a
  Liurnia check in v0.4.11, #940). Both checks now read `Liurnia ::`, and stay barred from hosting
  progression as before. Nothing else moved: the Cave of Knowledge tutorial pickups and the
  Fringefolk Hero's Grave rewards below the Stranded Graveyard -- including the Erdtree Greatbow,
  which the chariot pays out, not a chapel chest -- are all walkable from Limgrave and stay there.
  Reported by 255. (#1023)
### Added

- **Region Sync (#1005).** New `region_sync` toggle (default off) for seamless co-op: the party
  shares one physical world, so when any Elden Ring player with it on unlocks a region, every other
  opted-in ER slot's door opens too — the region-open flag is set and its graces light, the same
  write a locally received Lock makes. ACCESS ONLY: nobody is granted the region-Lock ITEM,
  fill/logic/goal are untouched, and generation is identical on or off. Rides the options echo
  (OPTIONS_SUBKEYS, so `CONTRACT_HASH` does not move); a seed with it ON emits
  `requiresClientFeatures ["region_sync"]` so an older client refuses the seed instead of leaving
  its player region-kicked out from under the party. Client half clients#417; the gitlink moves to
  its merge (`3967d512`).

- **The player guide says what `(region unconfirmed)` means and what it costs you.** 305 check names
  still carry that hedge, it shows up on the F6 tracker, and until now nothing told a player how to
  read it. `release/PLAYER-GUIDE.md` defines it: the check exists and is obtainable, the REGION label
  beside it is a derivation nobody has walked in game, so an unconfirmed check is barred from hosting
  progression -- it can hold filler and it can hold your own useful items, and the logic will never
  require you to reach it to finish. Reported by 255 while reading the tracker. (#1024)

### Changed

- **Ability Lock Mode now defaults to `progressive`, not `static` (Alaric's 2026-08-25 ruling).**
  If you name abilities in `locked_abilities`, they now start locked and each one comes back as an
  "Unlock: X" item shuffled into the multiworld, instead of being off for the whole seed. Static is
  still there as the explicit opt-out (`ability_lock_mode: static`) and behaves exactly as before.
  🛑 **This changes what an existing YAML generates.** A YAML written before today that sets
  `locked_abilities` but does NOT set `ability_lock_mode` used to produce a permanent lock and now
  produces a progressive one: unlock items enter the pool (displacing filler, count-exact), the seed
  emits `abilityUnlockItems` plus `requiresClientFeatures ["ability_unlock"]` so an older client
  refuses it rather than leaving the abilities dark, and — because `ability_unlocks_required`
  defaults ON — those unlocks are `progression` and are ANDed into the goal's held-item
  requirement, so in a multiworld a partner can be holding your Roll. That is the intent of the
  ruling; set `ability_lock_mode: static`, or `ability_unlocks_required: false`, to opt out of
  either half. A YAML that locks NOTHING is completely unaffected: `locked_abilities` still defaults
  empty and the whole axis stays inert whatever the mode says. No client change and no contract
  change — `abilityUnlockItems` and the mode's wiring have shipped since v0.5.0, and the mode is not
  a slot-data key at all (the client reads the emitted map, never a mode string), so `CONTRACT_HASH`
  does not move. `release/EldenRing.yaml`, the wizard metadata and `wizard.html` are regenerated.
- **Finger Reader Enia's shop is vanilla again, and every AP id after it shifts down by 100 (#1013).**
  Her 100 stock rows are excluded from randomization at generation, a rule the project had, lost, and
  now restores by construction. The reason is in the ledger beside every excluded row: her armor rows
  release on ceremony flags and her trades on holding the remembrance, so her checks read sphere-1 in
  the spoiler while her menu is empty at the start of a run -- a check the tracker calls open and the
  game will not sell you. The exclusion is DERIVED rather than typed (`merchant_shops.tsv` col 3 ==
  `Finger Reader Enia` -> `shop_rows.tsv` col 5, a FATAL generation error if that derivation ever comes
  up empty) and ledgered as `enia_vanilla=100`. Her shelves are the game's own wares now.
  🛑 **`locations` goes 5048 -> 4948, and removing her block renumbers every later AP id by exactly
  100.** An external tracker or a spoiler log carried over from a v0.5.0 seed will read the wrong
  check; an in-flight seed stays on its matched v0.5.0 pair, which the exact-version handshake already
  enforces. Everything that named an id by number is re-pinned by FLAG with its reason written beside
  it: the four `goal_choice` finales, `goal_locations.MALENIA_GOAL_LOCATION` (7770762 -> 7770662), the
  capital reconciler, the academy pocket, the isolated merchant, the sweep rungs, the tutorial-boss
  digest (`0681fe15c878a761` / 4101) and the coverage-gate baselines (4948 / 462, hub bar 83 / 20).
  Her rows still count as DLC-gated shop **rows** -- the raw set stays pinned at 36, all hers -- they
  stop being **checks**, so `DLC_GATED_SHOP_CHECK_FLAGS` is empty and the no-DLC filter test asserts
  against the raw set. Two knock-ons ruled rather than papered over: losing 100 sphere-0/1 purchase
  slots leaves a thin seed shorter of filler, so `EARLY_SAMPLE_MAX_UNDER` goes 2 -> 4 (the median seed
  is unaffected at 27 >= 24); and the Scadutree level-12 blessing floor, until now a comment, is
  enforced in code -- on a degenerate one-DLC-region pool the injector breaches `MAX_POOL_SHARE`
  loudly ("cannot reach its target") instead of shipping a silent shortfall. 🛑 The 8 remaining
  `EniaShop`-tagged locations are NOT hers (Gowry, Corhyn, Miriel, the Dragon Communion legendary
  slots); the tag is a misnomer now, and renaming it is churn for another change. (#1013)

### Fixed

- **Client gitlink -> `d99d81d` (clients#455, clients#467, clients#468).** Bloodborne location
  checks no longer disappear when a silently dead socket accepts the local write but the server
  never receives it. The client keeps a server-confirmed checked-location view separate from
  archipelago-rs's optimistic local cache and resends until `RoomUpdate` acknowledges the check.
  Retries are per-location and bounded in frequency -- immediate, then 1/2/4/8/16/30 seconds,
  staying at 30 seconds until confirmation -- with an immediate attempt after reconnect. There is
  deliberately no terminal attempt count, because one would recreate the lost-check failure after
  the limit. No Elden Ring gameplay behavior changes in this client bump.

- **Valid progressive no-op and flags-only rungs no longer produce a false client contract warning
  (#465).** The world already accepted the exact `{noop: true}` sentinel used to preserve flask copy
  ordinals and non-empty flags-only bell rungs, while the generated Rust validator required every
  rung to carry both `goods` and `flags`. The generated predicate now mirrors the authoritative
  Python checker: no-op is an exact one-field shape, flags-only effects must be non-empty, and a
  goods effect must explicitly declare boolean `consumed`. Positive and negative Rust tests are
  generated beside it so this validator drift cannot silently return. Client gitlink -> `6131252`
  (clients#466); no slot-data or contract-hash change, and existing valid seeds stop logging
  `contract: SHAPE 'progressiveGrants' expected NestedGrants`.

- **Demi-Human Queen Marigga and the Jagged Peak Drake stopped promising Gravesite payouts for fights Gravesite cannot reach (#1066).** J reported it on Discord 2026-08-26: "It says that the Demi-Human Queen Marigga and Jagged Peak Drake are in logic but i cant really get to either area without it kicking me out." The kick was correct and the tracker was wrong. Both bosses were already ruled in game by Alaric on 2026-08-10 -- Marigga is on the **Cerulean Coast**, the Drake is on the **Jagged Peak** (`boss_verdict_tiles.tsv`), and the PlayArea scan agrees (her tile `m61_46_40` buckets 68300/68400 = Cerulean; the Drake's nearest scanned tile `m61_49_38` answers 68410 = Jagged Peak). Neither has a `PlayRegionParam` boss-area row, and `boss_arena_rulings.tsv` -- the table that holds exactly this ruling -- was loaded AFTER the sweep host derivation had already run, so a ruling could only relabel `SWEEP_ARENA_REGION` while the members stayed dealt out of the tile-decode region. That is the arena/members split #1059 forbids, which is why the obvious one-line fix hard-failed gen. **The fix is at the host derivation, exactly as #1059 fixed Jori:** the rulings table now loads beside the measured `BOSS_AREA_REGION` and is ranked between it and the tile decode, so ONE answer feeds both the host region and the arena label and a ruling **re-homes** a boss instead of tearing it in half. Marigga becomes a Cerulean divvy host (9 members) and the Drake a Jagged Peak one (15); their Gravesite-measured members fall back into the Gravesite pool and are re-dealt to Gravesite's own hosts by the existing machinery -- 44 member links move host, **every one of them staying inside its own region**, and the Knight of the Solitary Gaol goes 27 -> 66 members while Rellana goes 41 -> 46. Three checks change region with them: `530845` Star-Lined Sword and `530850` Dragon Heart are the two bosses' OWN DROPS, which had fallen to the tile decode for want of a boss-area row and so filed in Gravesite an item obtainable only by winning a fight on foreign ground (J's symptom, one layer down), and `68750` Mad Craftsman's Cookbook [1] is the separable misfile #1066 named -- the scan answers it EXACTLY at bucket 68600 = Abyssal. Census delta is those three and nothing else: Gravesite 225 -> 222, Cerulean 104 -> 105, Jagged Peak 37 -> 38, Abyssal 23 -> 24. **No AP id moves** (4,663 flag->id pairs identical) and no location is added or removed. 🛑 The two drops are pinned per-flag in `FLAG_REGION_OVERRIDE` rather than by teaching the boss-drop branch to read the rulings table wholesale: that would move drops for all 62 ruled triggers at once, unmeasured, and the note beside `_ARENA_REGION_CURATED` says why a sweep ruling must not be folded into `BOSS_AREA_REGION` -- it would take Margit's drop out of Limgrave. Acceptance test (rule 11) is J's seed: a seed keeping Gravesite without Cerulean or Jagged Peak now lists neither boss's rows, and no Gravesite check reads `also granted by Demi-Human Queen Marigga` / `also granted by Jagged Peak Drake`. The #1059 containment gate is GREEN with the new rulings in place, which is the point of the shape: arena coverage rises 185 -> 187 of 211 triggers and the split set stays 0.

- **The Roundtable Golden Seed is a Stormveil check, and the ground audit is at zero pinned mismatches (#445).** One check moves: `Roundtable Hold :: Golden Seed (region unconfirmed)` becomes `Stormveil :: Golden Seed - around Lake-Facing Cliffs`. The Hold was never a derivation for f400220 -- its legacy attribution row reads `map=PENDING, method=global_filler`, and `location_descriptions.tsv` records that Alaric's 2026-08-04 pass over all 43 Golden Seeds left this one blank because nobody could say where it is. The full-census coordinate refresh answered it: its only lot (112200) is placed on three MSB enemies, `m10_00` -- Stormveil, play_region bucket 10000, the tile that carries 127 other Stormveil checks -- and the play_region-less Limgrave tiles `m60_45_38` / `m60_46_36`. **Why this mattered rather than being a label:** the HUB is in scope in EVERY seed, so the Hold filing CREATED this check unconditionally while its only witnessed ground sat behind the Stormveil lock -- a live check on the progression surface standing on ground the seed can forbid you to walk to (#680's shape). The nearest-grace join independently agrees now that the region does: the descriptor resolves to Lake-Facing Cliffs, and the check loses its `(region unconfirmed)` hedge. `region_overrides.tsv` and `gen_data.FLAG_REGION_OVERRIDE[400220]` carry the reason. 🛑 **The move settles where the check is FILED and nothing else.** It keeps its progression bar and its `(region unconfirmed)` hedge — it is in `_REGION_OVERRIDE_UNCONFIRMED_FLAGS` beside the Snowfield tears, because it has three placements, only one of which any table can resolve to a play_region, and its exact pickup ground has never been witnessed in game. This is the check that softlocked `AP_55352390472076588352` (`test_gf_defaulted_region_guard` is named after it), so it is the last one to promote to a progression host on a derivation alone; that promotion is a separate step and wants an in-game witness.

  The other three rows the audit raised this session were ruled, not moved. **f400036** (`Mohgwyn :: Festering Bloody Finger`) keeps Mohgwyn and is now excused as SWEEP-ANCHORED: its award site is Mohg's own m12_05 grant, which has no MSB coordinate for the join to see, so the only coordinates it has are two placements of the shared lot 110301 on invader NPCs standing in Limgrave; killing Mohg grants it, so Mohgwyn alone always suffices -- and since #1059 made member/arena co-region a gate, moving it onto the accusing ground would BREAK that gate. Mohg's trigger enters `RULED_SWEEP_ANCHORS` with that ruling written out, the way that table requires. **f400175** (Farum Azula) and **f400349** (Roundtable Hold) leave the pinned list in the other direction: both were pinned when their only coordinate was a foreign one, and the refresh added the site that was missing -- `m13_00` (Crumbling Farum Azula, bucket 13000) and `m11_10` (the Hold itself, bucket 11100). Their attributions were right all along; the corpus could not witness them. 🛑 An empty pin is not a clean bill: the audit still resolves 2,628 of 4,912 checks, so it means "nothing the join can see", never "nothing is wrong".

- **A lean-seed test was a 1-in-4 lottery, and the draw is pinned now.** Developer gate, no player-facing change. `test_gf_filler_economy_floor::test_thin_stone_reservation_is_warned` asserts that a seed too small for its recipe's stone weight SAYS SO rather than shipping quietly — but its fixture never guaranteed the smallness: `num_regions: 1` draws *which* region at random, and a big enough draw affords the ladder honestly and rightly says nothing. Measured over seeds 1000–1011: 9 warn, 3 do not. The identical 9/12, the same three seeds, reproduces against `origin/main`'s generated modules, so this was inherited and unrelated to the region move that happened to roll it. The draw is pinned to a seed the fixture's own premise holds on, so the guarded sin — a thin reservation shipping in silence — is exercised on every run instead of three runs in four.

- **One skip was unledgered from the moment #1059 merged, and nothing said so.** Developer gate, no player-facing change. `test_gf_sweep_arena_reachability`'s severity loop loud-skips because #1059 drove the arena/members split set to zero at the source, and its sibling asserts that emptiness — a deliberate skip, but not a *ledgered* one, so the CI skip census was owed a family and never got one. It stayed invisible because main's union-verdict job was aborting on a red shard before the census ran: an aborting gate hides every gate below it. Ledgered now, count 1, with the note that reaching 0 means a split came back and is to be diagnosed rather than rebaselined.

- **Client gitlink -> `b5a2d21` (clients#441-#447).** One Elden Ring fix rides in: the grant-stall guard now re-arms on the **world epoch** instead of on any unstable tick (clients#442, from TechnoForge's v0.5.0 log forensics on clients#439) -- a stalled delivery no longer re-parks and re-announces itself every tick, so the park/retry popup flood is bounded per epoch instead of repeating for as long as the world stays unstable. The rest of the bump is Bloodborne-client work with no Elden Ring effect: the attach-wait freshness floor resets when shadPS4 truncates its log (clients#441), a concurrent inventory pickup during a delta grant is scored as a completion rather than a park (clients#444), and passive per-grant delivery diagnostics accumulate from ordinary play (clients#447).

- **Ten checks moved to the region they physically stand in, measured by the PlayArea scan (#1054, #1046).** The scan built in this same window reads the exact runtime `PlayRegionID` the client's kick-watch reads, and it disagreed with 114 of the 679 checks it can answer exactly. Ten of those are ground-placed pickups -- the population the instrument actually rules on -- and only those ten moved. **Five Ancient Snow Valley Ruins pickups** (Warming Stone, Invigorating White Cured Meat, Smithing Stone [7], the Traveling Maiden set, Golden Rune [13]) were filed Consecrated Snowfield but stand in PlayArea volume `6501000`, which is **Mountaintops of the Giants**; a sixth in the same cluster answers `65030` and correctly stays Consecrated Snowfield, which is why these are five per-flag pins rather than one tile pin -- that tile straddles the Grand Lift of Rold. **Five Rauh pickups** move on 255's report that the upper Ancient Ruins are reachable on the Rauh Base Lock alone: Shadow Realm Rune [7] and Flight Pinion go Rauh Base -> **Ancient Ruins**, the Two-Headed Turtle Talisman goes Rauh Base -> **Gravesite**, and -- the half the report did not predict -- Grave Glovewort [5] and a Larval Tear go Ancient Ruins -> **Rauh Base**. Two of five moving the OTHER way is the point: a queue that only ever moved rows in the reported direction would be the instrument agreeing with the reporter instead of measuring. Census: Consecrated Snowfield 151 -> 143, Mountaintops 191 -> 199, Gravesite 224 -> 225, Rauh Base 91 -> 90; the location total is unchanged at 5048 and **no ap id renumbered**, so an in-flight seed's ids still mean what they meant. The NPC-relocation families in the same queue were deliberately NOT applied -- 16 Roundtable rows and 13 Limgrave Ash-of-War rows answer Mt. Gelmir because Patches and Bernahl are standing at Volcano Manor, and 24 "from Moore" rows answer Scadu Altus because Moore relocates. For a shop or grant flag the scanned point is where the NPC ended up, not where the check is. Each move carries its own `region_overrides.tsv` row citing its scan answer, and `test_gf_playarea_region_moves.py` pins the movers, the carve-outs and the ap ids.

- **Yelough Anix Tunnel is Consecrated Snowfield -- and already was (Alaric's ruling, 2026-08-26).** Recorded as a deliberate NO-OP. The audit worksheet flagged 19 Yelough-anchored checks as Mountaintops-vs-Consecrated-Snowfield candidates riding one `SUSPECT-ANCHOR` grace (73211), and the PlayArea scan answers `none` for every one of them -- no volume, no seam, no tile default -- so the instrument cannot settle them and Alaric ruled them from the wiki instead. Checking the shipped data against the ruling rather than against the worksheet: grace 73211 files under play_region `65002`, which is Consecrated Snowfield; its ground bucket `32110` is Consecrated Snowfield; 73211 already rides the Consecrated Snowfield grace bundle; and all 25 Yelough-labelled checks already present as Consecrated Snowfield. **The Mountaintops premise came from a stale `our_region` column** in `check_region_second_opinion.tsv`, written before the regen that moved them -- the same staleness #1054 records for `check_region_triage.tsv`. Nothing moves, and the ruling is now pinned by `test_gf_playarea_region_moves.py` and recorded in `region_overrides.tsv` **labelled as a wiki ruling, explicitly not scan evidence**, so a future flip back to Mountaintops fails a written decision instead of passing quietly.


- **A boss can no longer hand you checks in a region you never had to enter (#1059).** Reported on Discord 2026-08-26 by **NovahDango**, who screenshotted five `Abyssal ::` checks -- Clarifying Boluses, Frenzyflame Perfume Bottle, Scadutree Fragment, Shadow Realm Rune [7], Swollen Grape -- each reading "also granted by Jori, Elder Inquisitor". Jori is fought in **Scadu Altus**: `PlayRegionParam` puts his arena in bucket `40020` and Alaric walked it in game on 2026-08-10. Alaric's ruling: *"there shouldn't be any, or cross-region boss sweeps in general."* Two causes, both fixed at the source. **(1)** `boss_area_regions.tsv`'s `region` column is a generated snapshot of what the bucket->region spine said the day it was emitted, and the spine moves -- six of its 120 rows were stale, still filing `11050` under Leyndell after the Ashen Capital split, `34100` under Limgrave after the #202 Divine Tower ruling, and two rows naming **"Sewer"**, a region deleted outright by the 2026-08-20 Shunning-Grounds merge. Generation now re-folds the BUCKET through `region_groups.py` and ignores the column, and errors out rather than falling back if a bucket has no owner. That alone removed 17 of the 22 cross-region member links. **(2)** A legacy boss's host region ranked the nearest-neighbour tile decode -- the same machinery that regions the CHECKS -- above its measured arena, so the boss inherited its members' region by construction and the disagreement was invisible. The measured arena now wins. **Nothing was dropped: the five Abyssal checks were re-HOSTED**, and Midra, Lord of Frenzied Flame -- Abyssal's own major -- picked them up. 47 checks changed which boss grants them, all within their own region; the trigger count (211) and the member-link total (4101) are unchanged, and zero checks lost a granter. Margit keeps his #523 Stormveil ruling, now applied where it also moves his members instead of only his label. Lilith's report in the same conversation -- `Belurat :: Message from Leda`, granted by the Divine Beast Dancing Lion, physically in Shadow Keep -- is **not** this bug and is not changed: `m20_00` is Belurat, so that sweep is contained; f580600 has fourteen placements across three maps and belongs to the disjunct-multisite question (#320/#502). Until now the repo could only observe such a split and hope the seed hid it -- the arena-reachability drop fires only when a seed keeps the members' region *without* the arena's, so a seed holding both paid the grant out in full. **The invariant is now a hard generation failure and a ledgered gate** (`test_gf_sweep_region_containment.py`), stated against the measured arena region rather than the members' own -- the earlier "0 cross-region members" measurement was true and meaningless, because that number was derived from the members and could not disagree with them.
- **30 checks were filed in the wrong region, and the PlayArea scan can say so exactly.** Ground you stand on is measured now, not guessed: `greenfield/item_play_regions.tsv` reads the play_region VOLUME each pickup physically sits inside -- the same id the client's kick-watch evaluates -- while the region a check has carried until now comes from the NEAREST GRACE, a distance heuristic that is wrong wherever a region border runs closer than the nearest lit grace. #1054 measured 679 checks with an exact scan answer and found 114 disagreeing with `data.py`. 🛑 THEY MUST NOT BE BULK-APPLIED, and that is the finding as much as the count: a large share are NPC-RELOCATION ARTIFACTS, where `item_grace_coords.tsv` carries a PLACEMENT and for a shop or award flag the placement is where the NPC ENDED UP -- 16 `Roundtable Hold ::` rows and 13 `Limgrave ::` Ash-of-War rows answer Mt. Gelmir because Patches and Bernahl are at Volcano Manor; 24 `Gravesite ::` rows "from Moore" answer Scadu Altus because Moore relocates. The scan is right about the POINT and wrong about the CHECK for every one of them, so they are withheld and stay in #1054, along with the two deliberate carves the scan also flags (the #885 Hippo ruling into Shadow Keep, and the Leyndell/Ashen-Capital finale sub-carve). What moves is 30 GROUND-PLACED PICKUPS, each pinned individually in `gen_data.FLAG_REGION_OVERRIDE` with its scan row and excused to the independent provenance oracle in `greenfield/region_overrides.tsv`: five Ancient Snow Valley Ruins rows Consecrated Snowfield → **Mountaintops of the Giants** (bucket 65010; the sixth, `1050567600`, answers 65030 and correctly stays Snowfield); five Rauh rows resolving 255's report in #1046 -- the upper Ancient Ruins are their own region with their own Lock, so `2045467050` and `2045477020` go Rauh Base → **Ancient Ruins**, `2046457000` Rauh Base → **Gravesite**, and `2045457010` and `2046467800` run the other way, Ancient Ruins → **Rauh Base**; `1047517000` Altus → **Mountaintops of the Giants** at the Forbidden Lands, independently corroborated by this same regen moving grace 76500 the same way; three South Raya Lucaria Gate rows Liurnia → **Raya Lucaria Academy**; three Bower of Bounty / Bridge of Iniquity rows Mt. Gelmir → **Altus**; four Cerulean Coast rows Gravesite → **Cerulean**; four Ellac River / Fort of Reprimand rows Jagged Peak → **Gravesite**; four Church Ruins / Woodland Trail rows into **Abyssal**; and `f580600` "Message from Leda" Belurat → **Scadu Altus**, which Lilith reported the same day ("this one is in Shadow Keep, not in Belurat") and the scan answers exactly as bucket 69000 -- player and scan agree it is not Belurat, and the exact answer is taken over the prose. Per-region census delta: Mountaintops +9, Abyssal +4, Cerulean +4, Altus +3, Raya Lucaria +3, Gravesite +1; Consecrated Snowfield −8, Jagged Peak −6, Mt. Gelmir −4, Liurnia −3, Belurat −1, Rauh Base −1, Scadu Altus −1. Total `locations` is unchanged at 5048 and **not one ap id renumbers**, moved rows included (#952's rule, verified by diffing every flag's id across the regen). 🛑 THE YELOUGH ANIX RULING MINTS NO PIN. Alaric ruled Yelough Anix Tunnel into Consecrated Snowfield on 2026-08-26, and all 17 `SUSPECT-ANCHOR` rows the nearest-grace vote anchored on grace 73211 ALREADY derive Consecrated Snowfield, as does the grace itself (`region_graces.py`; `grace_region_map.tsv` 73211 → 65002, the Snowfield grace group). The `our_region` column of `check_region_second_opinion.tsv` still reads Mountaintops for them because that table is STALE against `data.py` -- #1054's own "separate finding" -- not because the checks are; pinning them would be a redundant manual override, which CONTRIBUTING makes a failure. The ruling is recorded in `gen_data.py` beside the pins that did move, naming all 17 flags. (#1054, #1046)

- **The overworld seam step was missing from `datamine_grace_ground`, so three graces answered `none` where the item scan answered the ground under their feet.** Developer tool, no player-facing change. With the tile frame fixed (above), Alaric's box run of `--graces` left exactly one delta class: three BUCKET MISMATCHes and two source deltas, every one of them a grace sitting a few metres OUTSIDE a PlayArea volume. `datamine_item_play_regions` applies the `_nearest_face` / `SEAM_SLACK = 8.0` seam snap on the OVERWORLD; `datamine_grace_ground` only applied it to INTERIORS and fell straight to the tile default outdoors. That was the last semantic split between the two tools, and it was the item scan that was right: the engine's containment tolerance does not stop applying because the point is outdoors, and a grace 1.7 m from a face answering `none` is the less correct answer. 🛑 The gate was NOT softened to accept none-vs-seam — `--graces` keeps its strict bucket semantics; the fix went into the derivation. `datamine_grace_ground.derive_ground()` now owns the whole `volume -> seam -> tile-default -> none` ladder for BOTH the overworld and the interiors, and `datamine_item_play_regions.derive` is an ALIAS of that function (`derive = gg.derive_ground`), not a copy — so a third divergence cannot be written, only imported. `grace_ground.tsv` must be REGENERATED on the box for this to land (the MSBs are deliberately not in `gen_inputs.db`, so it cannot be regenerated in CI or in a sandbox and was deliberately not hand-forged): expect three rows to gain a bucket via a seam — 76214 Main Caria Manor Gate → `62000` @1.7 m, 76453 Fort Faroth → `64020` @6.3 m, 76500 Forbidden Lands → `65000` @3.6 m — and two source upgrades at 76230 (@7.4 m) and 76402 (@0.9 m) whose buckets do not move. Measured against a simulated regen in-sandbox, what that lands downstream is: **grace 76500 "Forbidden Lands" moves from Altus to Mountaintops of the Giants** in the generated `region_graces.py` (with both regions' landmark lists shifting), which is the correction rather than a side effect — the Forbidden Lands grace stands on Mountaintops ground; the GRACE-GROUND GATE stays green with `locations` still 5048 and no region losing its overworld face; and `msb_region_vote`'s anchor coverage rises 340 → 342 graces with `SUSPECT-ANCHOR` unchanged at 24 (a `seam:` row is correctly not suspect — that badge is for `tile-default`, a tile-wide guess, and a volume face is real geometry). One more thing the run exposed: an MSB volume name can contain a literal **TAB** (`m60_39_54`'s `プレイ領域 6300030<TAB>高山_地図断片８_閉込ボス領域１`), which had CORRUPTED grace 76322's committed row — the tab split the tab-separated `source` column and pushed `tile` off the end, so that row's tile column holds the second half of a volume name, and `--graces` reported a phantom source delta purely because the reader truncated the committed source at the tab. `_srcname()` collapses whitespace where a name becomes a source string; the regen repairs the row and its bucket (63000) does not move. Gated by 11 new tests in `test_gf_item_play_regions.py` — an overworld grace 4 m from a face now answering `seam:` (RED on the old code, verified by reverting the step), its past-the-slack mirror still answering `tile-default`, the interior ladder unchanged, containment still outranking the seam, the tab-in-a-name row shape, the ladder asserted to be ONE function object, and the decisive one: both tools' whole pipelines run over the same fixture grace corpus and their per-grace `(buckets, source)` answers diffed, because sharing a function proves nothing if one caller builds a different map id. `test_gf_grace_tile_frame.py`'s selection predicate now skips `seam:` alongside `volume:`/`measured:` — a seam answer comes from a face and is not re-derivable from the params alone — so it stays green against the committed tsv AND against the regenerated one (verified both ways in-sandbox).

- **The overworld tile frame is centre-origin, and the PlayArea scan had been reading the tile next door.** Developer tool, no player-facing change. The item scan's calibration gate (`--graces`, the runbook's step 3) REFUSED on Alaric's box with bucket mismatches that pointed in opposite directions — grace 76416 committed `none` but derived `64010`, grace 76420 committed `64000` but derived `none` — and no volume was involved in either: both were pure PlayRegionParam lookups, disagreeing only about WHICH tile's row governs the point. `datamine_grace_ground` used the grace's AUTHORED `(gridXNo, gridZNo)`; `datamine_item_play_regions._fine_tile` recomputed one as `floor(world / 256)`. 🛑 `floor` was the bug, and it was wrong for **2053 of the 2768 overworld item placements** — never by more than one tile index, which is exactly why a whole table of wrong answers looked plausible. The overworld tile's local coordinate frame is centred on the tile, not cornered on it: of BonfireWarpParam's 450 overworld grace local axis values, 438 (97.3%) lie in `[-128, 128)` while only 227 (50.4%) lie in `[0, 256)` — and **222 are negative**, which a corner origin cannot produce; `item_grace_coords.tsv` agrees at 4732/5010 (94.5%). So tile `t` owns `[t*256 - 128, t*256 + 128)` and the attribution ROUNDS. There is now ONE implementation, `overworld_fold.fine_tile`, next to `world_xz` and for the same reason (#338), and BOTH tools call it — `datamine_grace_ground` stops looking up the authored tile, so the two derivations cannot drift again. Round-tripping every grace through fold-then-attribute returns its own authored tile for **214 of 225** (under `floor`: 53), and the 11 that still move are genuine SPILLERS whose local coordinate runs past ±128 — they physically stand on the neighbour, and the neighbour's row is what the engine reads. Five committed `grace_ground.tsv` rows move as a result (76214 → `-`, 76236 → 62000, 76304 → 63000, 76905 → 69020, 76936 → 69300); all five had `tile-default`/`none` as their source, i.e. no volume ruled on them, so the new value follows from the params alone. Neither in-game kick anchor is touched: 76841 and 72102 are volume- and `MEASURED_GROUND`-decided respectively, and the region grace-ground gate stays green. Gated by `test_gf_grace_tile_frame.py` (5 tests, and it needs NO MSB corpus — the centred-vs-cornered premise MEASURED rather than asserted, the round-vs-floor round-trip as one comparison, 76416/76420 pinned by name as the motivating case, the five spillers pinned so a regen cannot quietly revert them, and the whole committed tile-default population re-derived from `gen_inputs.db`, so the pure-table-lookup half of `--graces` now reds in CI instead of on Alaric's box) plus a red/green pair in `test_gf_item_play_regions.py`'s synthetic fixtures at local −110 and +140.

- **The wizard's `curated_filler` share column now re-shares when you edit a weight.** The
  `{category: weight}` grid draws a `%` of the tail beside every weight and a footer naming the
  total those percentages are shares of — and both were computed once, when the row was built, and
  written in as text nothing ever touched again. You typed juice 63 → 20, the yaml moved correctly,
  and all seventeen percentages plus the footer's "a share of 103" went on describing the recipe you
  had *before* the edit. Worse at the bottom of the range: zeroing every weight commits the EMPTY
  recipe — no gear and no upgrade economy — while the grid kept quoting the shipped default's
  shares and the footer kept promising 103 points of filler. The column and the footer now track the
  weights live, per keystroke, and an all-zero recipe reads `--` with the empty-recipe warning
  instead of a stale percentage. Reported by NovahDango. (#1031)

- **Client gitlink -> `f5b9187` (clients#456, clients#458).** Both riders are Elden Ring, and both are
  about Tarnished Edition. 🛑 **The 2.7.0.0 support that rides in here has never been run in a game.**
  clients#456 adds a `Ww270` arm to the version gate on offsets derived entirely offline -- 93 in the
  pinned `eldenring` crate and 8 of the client's own, now dispatched through a new `rva_table` module
  instead of being constants baked to 2.6.2.0 -- so a 2.7.0.0 player gets a build that can find out
  rather than the panic the old gate had waiting for them. PE detection happens once and is cached, so
  the crate's table and ours cannot disagree about which executable is running, and attach logs a
  warning on the 2.7.0.0 path saying in as many words that the addresses are unverified. The JP
  Tarnished exe is NOT supported and the rejection text says so: its binary was never available to
  derive a table from. Both git deps point at `4laric/fromsoftware-rs` @ `63a0c372` for now, a fork of
  the previously pinned `8c67a84f` whose only delta is the added `Ww270` arm -- TEMPORARY, and it goes
  back to upstream the moment upstream ships its own generated arm. 2.6.2.0 and 2.6.2.1 keep working
  unchanged; the arms coexist. clients#458 is the first smoke run's two findings: `fmg_repo` is the one
  client RVA that is READ and never CALLED, so no prologue guard covers it and a range test any
  pointer-shaped word passes was the entire screen -- it now validates the FMG STRUCTURE at first use
  (ordered, disjoint group spans; an entry count in band and consistent with them; every known-vanilla
  probe id resolving to well-formed text), and a rejection turns the FMG layer off for the session with
  one ASCII log line instead of crashing or painting garbage item names. That guard is deliberately
  language-independent -- it never compares the text to English words. And the `spell_slot_length`
  oracle, which exists to spot a stacked `regulation.bin`, was accusing vanilla 2.7.0.0 of being modded
  on every session because its "expected 25" was a 2.6.2.0 figure; the expectation is per-build now,
  off the same detection `rva_table` dispatches on (vanilla 2.7.0.0 measures 105 of 317 rows).

- **Groundwork: two CI flakes killed at the fixture, and the generator input stamps stop depending on
  where the artifacts came from.** Developer gates, no player-facing change. The chandelier dedup
  pool-cardinality assertion drew at random and the merchant bell pool witness could draw a seed whose
  D and Rogier awards had no sealed merchant region, so both sometimes asserted against a world that
  did not hold their premise; both now use a deterministic draw and a DLC-only fixture (#1065, #975).
  Artifact identity for the deterministic generator stamps is derived from the committed
  `gen_inputs.db` manifest rather than from extraction context, which also covers leftovers and
  unextracted bundles, and that suite is registered in the generators ledger so the workflow actually
  runs it -- a repo-only suite that no job executes is the exact shape of dark test this ledger exists
  to catch (#1010).

## v0.5.0 — 2026-08-22

Ability lock: restrict abilities for a run, or start locked and find them back as items.

### What you need to update

- **Client:** Required for a progressive seed (the `ability_unlock` handshake) and for any seed once you upgrade the host — the version handshake moves to 0.5.0. A 0.4.x client can still play a plain 0.4.x seed.
- **APWorld:** Required for the host to generate 0.5.0 seeds.
- **YAML:** **New YAML optional. Existing YAMLs remain valid.** `locked_abilities` and `ability_lock_mode` are new and default to off/empty, so nothing you already wrote changes.
- **Existing seed/save:** Compatible — a seed that sets neither option behaves exactly as it did on 0.4.x; the new keys are simply absent (= off) for older clients.
- **Profile/assets:** No action.

This window was cut as a `v0.5` integration branch off v0.4.14 and merged to `main` on 2026-08-24 (#982) after the ability-lock client build checked out in play. `stable` stays on v0.4.13 until this window is tagged — no promotion yet.

`CONTRACT_HASH` is `13db0b3a`, read by loading contract.py — **MOVED** from `dc0dc687` (the armorBundles shape that stood from v0.4.8). `abilityUnlockItems` is the new key. An older client reports incompatible for a progressive seed rather than leaving abilities locked, via `requiresClientFeatures: ["ability_unlock"]`; a static-lock seed rides the always-declared options echo and needs no new key.

The version moved, so a client half is required: `contract_gen.rs` embeds the version string and the hash. Client half is `from-software-archipelago-clients` at `3797563` (client main; `d4f23eb` at the branch cut), pinned by the gitlink in the same commit as these notes (AGENTS §7).

### Added

- **Co-op difficulty (#993).** New `coop_difficulty` option (0-9, default 0 = off) for seamless co-op. Seamless raises enemy HP but leaves enemy DAMAGE at the host default, so a partner roughly halves the incoming threat without enemies hitting harder -- the "too easy in co-op" report. Each extra point adds that many enemy-scaling tiers per co-op partner in your world; a higher tier carries both HP and attack, restoring the missing threat. Every player is on their own AP slot reading one shared world, so each client counts the party and applies the same bump -- no host. Needs `enemy_scaling` on; a tier adds HP too, so pair a non-zero value with Seamless's own HP knob turned down. Off by default, so nothing changes for solo or existing seeds.
- **Remove merchant checks (#994).** New `shop_checks` option (default on). Off makes no merchant purchase slot an AP check -- the ~562 shop rows (184 in the hub alone) stop being locations, so nothing you or another player wants can be gated behind a purchase, and the seed shrinks accordingly. Merchants still sell their vanilla wares.
- **Ability lock (#945).** A new option axis: `locked_abilities` disables any of jump / crouch / roll / r1 / r2 / l1 / l2 at the game's logical-action layer — keybind- and device-agnostic (rebinds, keyboard and mouse all covered) and menu-safe. `ability_lock_mode` chooses `static` (off for the whole seed) or `progressive`.
- **Heal is lockable too (#945).** `heal` joins the ability lock; because it owns no action bit it
  disables the flask instead (the No Flask SpEffect, re-applied while locked), so the flask heals
  nothing until it is unlocked.
- **Log cleanups.** A heal-locked seed no longer repeats the flask-param "not loaded yet" line every
  frame; the client now says ONCE when a Progressive Flask Upgrade lands on a seed with no flask
  ladder (progressive_flasks off, #988); and the `auto_upgrade` log states that the normal and somber
  smithing tracks are separate and a level never crosses (#989).
- **Progressive ability lock (#980).** In progressive mode each locked ability becomes a synthetic `Unlock: X` item shuffled into the multiworld; find it (or receive it from another world) to get that ability back. The unlock is reconnect-safe — recomputed from the whole received stream on every connect.
- **Ability unlocks are goal-required by default (#980).** New `ability_unlocks_required` (default on): in progressive mode each `Unlock: X` is now `progression` and is added to the goal's held-item requirement, exactly like a required Great Rune. Because progression is distributed across the whole multiworld — and these are deliberately exempt from Elden Ring's local progression confinement — your abilities can land in a PARTNER's world, and then you cannot finish until they send them back. That mutual dependency is the point of playing in an Archipelago. Turn it off to keep the old behavior: the unlocks stay `useful` and never gate completion. No client change — the client's existing Goal gate enforces the requirement (`goalRequiredItems`), and the player-visible goal line lists the unlocks it still needs.

- **Fix: chandelier Academy Glintstone Key no longer hands out a free duplicate key (#1001).** The Church of the Cuckoo chandelier copy grants a *duplicate* goods id (8174) of the Academy Glintstone Key; it was excluded from checks (so the key stays a pool singleton) but its vanilla lot was left live, cheesing the Raya Lucaria gate for free with no AP check. Its lot is now neutralized at the source (a duplicate-lot goods-blank), so it drops nothing while the key remains a singleton.
- **`!check <name>` rescue console command (#1008).** Look up a check's acquisition flag by name -- for enemy/boss/NPC death drops and offline pickups that "did not fire" (e.g. under enemy rando). Prints each match's flag, whether it is set, and a ready `!setflag` to send it on the next poll. Documented in GETTING-UNSTUCK.md.
- **Sweep-flush burst telemetry (#1006).** Client-only diagnostics: the sweep-flush path now logs the per-tick shared-flag write time and, per sweep, the ms-to-confirm + peak flag count. Measure-before-optimize for the seamless-co-op "flood gate" (boss sweeps paying out on the defeat flag + SC flag-sync latency) -- no behavior change.
- **Roll unlocks early (#980, bobler).** In progressive mode the `Unlock: Roll` item is declared to Archipelago's `early_items`, so Fill forces it into an early sphere -- you are never stuck without the dodge roll for hours. It stays exportable (not `local_early_items`), so it can still reach a partner's world, just early there too. Only Roll is forced early; the other abilities place freely.
- **Fix: Leyndell's capital gate no longer fights itself (clients#409).** The two fog-wall
  prerequisite flags (105 and 182) were routed through `seal_flags`, whose contract is "hold FALSE
  while owned" — so the reconciler cleared them every tick while the key-item backstop re-set them,
  and the capital wall stayed shut with two Great Runes received (Otakuu, 08-24). They now ride a new
  `prereq_set_flags` class: desired-SET, never cleared.
- **Fix: Great Runes from boss drops are delivered as-sent (clients#393).** The delivery path
  rewrote a boss-drop rune row to its restored form on the way in, which could leave a received rune
  inert; the rewrite is gone and the row lands exactly as the server sent it.
- **Fix: the two Dryleaf Dane sweeps key on their EMEVD defeat flags (#1015).** The Scadu Altus Dane
  fights' sweeps were keyed on entity-id-derived flags (2049440710/2050430710); they now key on the
  flags the EMEVD defeat handlers set (2049440800/2050430800) — 41 checks (24 + 17) change trigger.
- **Stacked armor sets are a YAML option now (#986).** `armor_bundles` (default on) was hardcoded
  since #849; off restores the classic pool where every helm, chest, gauntlet and greave is its own
  item. An off seed emits no `armorBundles` slot-data key, so an older client accepts it.
- **129 more checks pay out from the corpse-award sweep (#984).** `death_award_pairs.json` grows
  179 → 308 pairs, covering the common `$Event(1100)`/`$Event(1200)` boss-award latch family.
  Retroactive on existing seeds — no yaml or apworld change, the client just reads the bigger table.
- **GETTING-UNSTUCK grew Leyndell-gate and unsent-check walkthroughs (#1007).** How to force the
  capital fog wall by its two flags, and how to chase a check that never sent down to its
  acquisition flag with `!check`/`!setflag`.
- **Updater errors name the URL (#978).** A failed `latest.json` fetch prints the URL it tried and
  the likely cause instead of a bare error.
- **Groundwork, no player effect yet:** the enemy-drop EntityID table and its generator (#1004,
  #1012 — feeds a client module nothing calls yet), the Tarnished patch-day baseline doc plus a
  fourth watched SpEffect row (#1011), a census of every sweep trigger key refuting #987's premise
  (#1016), and the Leyndell wall derivation corrected to the 170-179 possession band, comments only
  (#983).
## v0.4.14 — 2026-08-22

### What you need to update

- **Client:** Required — use the v0.4.14 client with v0.4.14 seeds; the exact-version handshake
  moves even though the slot-data shape does not.
- **APWorld:** Host-only — the room host or generator must install v0.4.14; joining players only
  need the matching client.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — finish an active v0.4.13 seed with its matched v0.4.13
  pair. No save migration; do not mix versions.
- **Profile/assets:** No action.

Window opened AT the v0.4.13 tag with zero commits past it, in the promotion change; nothing is
carried over.

`CONTRACT_HASH` remains `dc0dc687`, verified by loading `contract.py` after the bump. The
slot-data shape is unchanged, but the exact-version handshake still moves to 0.4.14.

Client half: clients#390. Its commit is pinned by the gitlink in this same change.

`release/CHANNELS.tsv` promotes `stable` to v0.4.13 in this same change.

Entries arrive below as they merge (rule 14: the release notes are part of the change, not part of the release).

## v0.4.13 — 2026-08-22

### What you need to update

- **Client:** Required — use the v0.4.13 client with v0.4.13 seeds; the exact-version handshake
  moves even though the slot-data shape does not.
- **APWorld:** Host-only — the room host or generator must install v0.4.13; joining players only
  need the matching client.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — finish an active v0.4.12 seed with its matched v0.4.12
  pair. No save migration; do not mix versions.
- **Profile/assets:** No action.

Window opened the same day as the v0.4.12 hotfix tag, in the promotion commit; nothing is
carried over.

`CONTRACT_HASH` remains `dc0dc687`, verified by loading `contract.py` after the bump. The
slot-data shape is unchanged, but the exact-version handshake still moves to 0.4.13.

Client half: clients#382. Its commit is pinned by the gitlink in this same change.

`release/CHANNELS.tsv` promotes `stable` to v0.4.12 in this same change (a hotfix promotion,
same-day as its tag).

Entries arrive below as they merge (rule 14: the release notes are part of the change, not part of the release).

- **A boss the game forgot to pay now pays retroactively.** 179 checks are corpse-treasure
  awards fired by an EMEVD death event, and a death the event never witnesses — a despawn, a
  fall, a death during a load — left the check permanently unpayable in-game (the reload branch
  force-kills the corpse without re-offering the loot; found live when rouqs' Leyndell Ulcerated
  Tree Spirit died unpaid). The death flag persists in the save, so the pair (death flag up,
  check flag down) is a complete signature of the miss: a new shipped table
  (`death_award_pairs.json`, game data beside the dll like the check-lot table) lets the client
  sweep those pairs at connect and fire the check — retroactively, on any seed old or new, no
  yaml or apworld change. The six sites whose corpses re-offer on reload are excluded, so a
  merely-unlooted corpse is never pre-empted. (clients#385; the client half pairs this entry.)

- **Fast-reopening a shop keeps its Archipelago item names.** The shop-slot repaint (v0.4.11+)
  names each padded row on open, but reopening the same merchant in the same second a lagging
  load-edge `reset()` fired dropped the repaint -- you got hints and unnamed rows (rouqs' 0.4.12
  log: a clean 09:35 open, a nameless 09:56 reopen). `reset()` no longer clears the pending shelf
  range, so a warp-then-fast-open survives; a stale range is harmless because the block-identity
  guard refuses anything older than the re-published baseline. (clients#383.)

- **The F6 tracker resizes horizontally again, and a shrunk window scrolls instead of clipping.**
  The anti-clipping content floor -- the widest row, re-measured every frame -- capped at 95% of
  the display, the SAME 95% as the resize maximum. Once a late-game sweep row landed, the floor met
  the ceiling, `min == max`, and imgui killed left/right resize exactly while up/down kept its own
  band (rouqs: "can resize up/down but left right doesn't work anymore"). The floor now caps at 85%
  (resize max stays 95%), and it is a DEFAULT rather than a hard minimum, so a window dragged
  smaller scrolls its content instead of clipping it. (clients#386, clients#388.)

- **The pickup sound cue is off by default now.** The multiworld-collect cue was the stock Windows
  system chime (`SystemAsterisk` through the OS mixer -- system volume, no game-slider coupling)
  firing on every pickup, which Alaric judged live to be "worse than doing nothing." `sound_cue`
  now defaults false; add `"sound_cue": true` to `apconfig.json` to opt back in. (clients#336 /
  clients#389.)

- **Housekeeping pinned in the same gitlink bump:** the client's exact-version handshake moves to
  0.4.13 (clients#382), and a Bloodborne save-restore reconciliation lands on the shared client
  (clients#384) -- neither changes an Elden Ring seed.

## v0.4.12 — 2026-08-21

### What you need to update

- **Client:** Required — use the v0.4.12 client with v0.4.12 seeds; the exact-version handshake
  moves even though the slot-data shape does not.
- **APWorld:** Host-only — the room host or generator must install v0.4.12; joining players only
  need the matching client.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — finish an active v0.4.11 seed with its matched v0.4.11
  pair. No save migration; do not mix versions.
- **Profile/assets:** No action.

Window opened 2 commits past the v0.4.11 tag; both are the packaging/installer fixes below,
found during v0.4.11's own packaging acceptance and carried here as this window's first entries.

`CONTRACT_HASH` remains `dc0dc687`, verified by loading `contract.py` after the bump. The
slot-data shape is unchanged, but the exact-version handshake still moves to 0.4.12.

Client half: clients#375. Its commit is pinned by the gitlink in this same change.

`release/CHANNELS.tsv` promotes `stable` to v0.4.11 in this same commit.

Entries arrive below as they merge (rule 14: the release notes are part of the change, not part of the release).

- **One purchase no longer padlocks a whole shelf.** Buying an Archipelago shop slot hands you
  its spare "receipt" good, and 64 of the 79 spare rows are vanilla hold-cap-1 items you can
  neither drop, discard, nor sell — so ER itself refused every later purchase resolving to the
  same row ("would exceed the maximum able to be held"), and the name-sharing that reuses rows
  across shops turned one buy into a seed-wide lock. The client now raises both hold caps on
  every spare row it already owns, at the same guarded write that draws the AP flower. Fixes
  every seed ever generated, including live v0.4.11 rooms, the moment the player updates —
  confirmed in-game by the reporting player. (clients#380)
- **Ability-lock test harness (experimental, off by default).** Setting
  ER_ABILITY_LOCK_TEST (for example "roll,r1") masks those abilities' gamepad inputs while in
  gameplay — menus and NPC dialogue are never masked, per the #945 probe findings. Gamepad
  only, physical buttons, no seed integration yet: this is the enforcement half of ability
  lock mode out for wear-testing ahead of the world feature. (clients#377)

- **The release bundle now contains the tools its changelog promises.** `package_release.ps1`
  predated the updater (#954) and the matt's-rando installer (#948), so a bundle cut with it
  advertised `update-er-archipelago.ps1` and `install-into-matts-rando.ps1` "beside the dll"
  while shipping neither — and `--with-flower` died on a missing `install_ap_flower.py`. All five
  player-run tool files now stage into `me3\` as required entries, and `-Version` derives from
  `contract.py` instead of defaulting to a literal four-minors-stale `0.2`. The published
  v0.4.11 zip was cut WITH this fix, so no shipped artifact carried the gap.
- **The matt's-rando installer creates the dll config on a fresh install.** Its refusal used to
  instruct "open 'Add dll mod' once, close it (the app writes the file)" — measured false during
  v0.4.11 acceptance: the app writes nothing on open-and-close, stranding exactly the first-time
  installs the tool exists for. A genuinely missing
  `config_eldenringrandomizer_dll.toml` is now created carrying only the one line the tool owns
  (the app's own measured single-line style); a toml without an `external_dlls` array gets that
  line appended; and if the toml exists in the parent folder or one level down, the installer
  refuses and names the real folder instead of planting a twin.
- **Diagnostics:** FMG entry-insertion rejections now name the measured exe version, so a
  SearchStringTable signature mismatch dates itself (clients#379, from the #371 audit); Bloodborne
  runtime path errors name the setting and the resolved path (clients#378).

## v0.4.11 — 2026-08-21

### What you need to update

- **Client:** Required — use the v0.4.11 client with v0.4.11 seeds; the exact-version handshake
  moves even though the slot-data shape does not.
- **APWorld:** Host-only — the room host or generator must install v0.4.11; joining players only
  need the matching client.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.** This empty window adds no
  option yet.
- **Existing seed/save:** Compatible — finish an active v0.4.10 seed with its matched v0.4.10
  client and APWorld. No save migration is required; do not mix the two versions.
- **Profile/assets:** No action — opening the window changes no profile or packaged asset.

Window opened AT THE TAG of v0.4.10 with ZERO commits past it.

`CONTRACT_HASH` remains `dc0dc687`, verified by loading `contract.py` after the bump. The slot-data
shape is unchanged, but the exact-version handshake still moves to 0.4.11.

Client half: clients#334. Its merged commit is pinned by the gitlink in this same change.

`release/CHANNELS.tsv` promotes `stable` to v0.4.10 in this same commit.

Entries arrive below as they merge (rule 14: the release notes are part of the change, not part of the release).

- **Shop shelves now name every Archipelago item properly.** The shared "Archipelago Items"
  label -- hundreds of shop checks folding onto one spare row's single FMG name -- is gone from
  regular merchants. The insight is a scope change, not a bigger pool: two slots only need
  distinct names if one MENU can show both, and a menu is exactly the row range its ESD passes
  to the shop opener. Generation now colors the spare preview rows against the datamined
  display scopes (tools/datamine_shop_open_ranges.py, 62 scopes, 8 opener kinds; the busiest
  regular menu is the Twin Maiden re-sell at 31 checks against a 79-row pool), so same-shelf
  slots never share a row while different shelves reuse rows freely -- and the paired client
  repaints each opened shelf's rows with that shelf's own item names at shop open. Menus the
  client cannot repaint yet (Enia's transposition menu, Champions/Dragon Communion/Dupe/Puppet
  shops) get private rows first-come, i.e. exactly the old behaviour, never worse. Slot-data
  shape unchanged; old clients on new seeds and new clients on old seeds both degrade to the
  honest shared label. Client half: clients#366.

- **The updater, phase 2: one command brings this install to stable.** The bundle ships
  `update-er-archipelago.ps1` (Python twin included) beside the dll. It reads the same
  `/er/latest.json` the in-game banner reads, refuses while the game runs, and -- the point --
  gates on the CONTRACT: if the new release's contract is not found in your installed dll it
  stops and explains that updating mid-seed breaks your pairing, unless you pass
  `--accept-contract-change`. The download is size-verified against the release asset and the
  zip's own integrity table; the swap replaces only the shipped `me3/` payload, backs up every
  replaced file, and never touches `apconfig.json`, saves, logs, or ledgers. It is deliberately
  never automatic: the banner decides, the human runs. Rides the phase-1 verdict pair
  (site latest.json + client banner).
- **The site now publishes a machine-readable update verdict.** `deploy_wizard.sh` emits
  `/er/latest.json` -- the stable version, its contract hash (from the CONTRACT-VERSIONS
  ledger, never typed), and the release url -- installed with the same atomic discipline as
  the pages. The client's update banner reads it on connect and tells the player the thing
  the update matrix always knew: whether the new build is safe to pick up mid-seed (same
  contract) or their seed pair must finish first (contract moved). Client half: the
  update-check banner PR paired with this window's gitlink.

- **One command wires the client into matt's randomizer.** `install-into-matts-rando.ps1
  -Randomizer path\to\randomizer` (Python twin included) edits the one file matt's launcher actually
  reads -- `config_eldenringrandomizer_dll.toml` -- to point at `eldenring_archipelago.dll`
  inside the release's `me3/` folder, in place. Re-running after an update repoints a stale
  versioned path automatically (the way a launcher ends up loading last release's client),
  a backup is written first, an incomplete bundle refuses instead of installing a dll without
  its data tables, and `-WithFlower` chains the icon installer. It never touches the
  hash-guarded auto-generated config, and it warns if RandomizerHelper.dll shares the list.
  Spec and the measured seam: #944.
- **The matt's-randomizer install step stops inviting stray dll copies.** The walkthrough and
  SETUP now say to point **Add dll mod** at `eldenring_archipelago.dll` inside the release's
  `me3/` folder, in place -- never to copy it out (the dll is inert without its two data tables
  beside it) -- and to unpack releases into a version-less folder name so matt's remembered dll
  path survives an upgrade instead of silently loading last release's client. Docs only.

- **Eight Sites of Grace that lit for NOBODY now light with the region whose ground they stand
  on.** The grace-ground safety gate dropped a grace from the wrong region's bundle but never
  re-homed it to the right one, so these stayed dark all game even after their region opened:
  Shadow Keep Main Gate (lights with Scadu Altus), Main Academy Gate (Raya Lucaria), Grand Lift
  of Rold (Mountaintops), Hidden Path to the Haligtree (Consecrated Snowfield), Castleward
  Tunnel, Limgrave Tower Bridge and Divine Tower of Limgrave (Stormveil), and Wyndham Catacombs
  (Altus). On `region_grace_unlock: entrance`, Stormveil's entrance is now Castleward Tunnel and
  Raya Lucaria's is Main Academy Gate — the canonical doors, and the academy pick no longer
  warps you inside the seal. (#930)
- **Shop previews no longer run out of real names at 62 slots.** The spare-goods pool that lock
  and foreign-item shop-slot previews draw their display names from grew from 62 to 79 rows: the
  same 62 rename-safe goods first — so seeds under the old ceiling draw the identical rows — then
  17 rows with no vanilla text entry at all, which only a client that can CREATE FMG entries is
  able to name. A seed whose preview demand exceeds the first 62 declares
  `shop_preview_fmg_insert` in `requiresClientFeatures`, and a client too old to insert entries
  refuses the connect by name instead of rendering `?GoodsName?` on those slots. When the whole
  pool is spent, generation now logs the demand/supply/lock arithmetic rather than a bare count.
  World: #937. Client: clients#341, whose merged commit is pinned by the gitlink in this same
  change.
- **The Four Belfries Imbued Sword Key chest is a real check.** It had been excluded as "a
  nonexistent fourth key", so the chest kept handing out its vanilla key and could never hold a
  multiworld item. The placement data (treasure asset, MSB row, exact entity coordinates) says it
  is the real Four Belfries treasure: the base game has three Imbued Sword Key checks — The Four
  Belfries, Raya Lucaria, Sellia — and the DLC adds the fourth at Castle Ensis. The chest is
  regioned to Liurnia and joins the location pool. (#940)
- **Every AP shop slot now shows its proper name.** Opening a shop repaints the menu's display
  names from the seed's placement data, so a shelf of multiworld items no longer borrows the
  vanilla goods' names — each slot names what it actually holds. The walk clamps its range before
  touching param rows. Client: clients#366, completing the #937 pair.
- **The Serpent-Hunter's spectral waves now belong to the Rykard fight.** The wave SpEffect is
  applied through the fight itself for its duration rather than bound to the weapon's resident
  equip slot, so the waves follow the arena instead of your inventory state. (clients#345)
- **Receiving the Crafting Kit now actually unlocks crafting.** The delivery sets the same
  crafting-unlock flag the vanilla kit sets, so the menu opens as if you had bought it.
  (clients#335)
- **The client backs up your active game save once per launch** — rotating, timestamped copies,
  so a bad session has something to roll back to. (clients#287)
- **The goal ledger is on screen.** The tracker overlay carries the session's goal state, and the
  withheld-goal lock no longer appears on the hint surfaces. (clients#361)
- **Local pickups that land as AP checks play an audio cue.** You hear the check fire without
  watching the ticker — useful mid-fight and in menus alike. (clients#364, issue clients#336)
- **Quitting the game can no longer abort with a crash report.** Quit-to-menu freed the
  character, quit-game tore the param tables down, and a callback reading them in that window hit
  an upstream panic in a frame that cannot unwind — process gone, crash txt written, on the most
  correct exit there is. Every raw param read (24 sites, 11 modules) now goes through the guarded
  accessor and degrades to one deferred-log line naming the callback. (clients#373, issue
  clients#372)
- **Fixes worth naming:** the wrong-save refusal now names the room the save belongs to
  (clients#337); "Region unlocked" announces on the edge, not every tick of the pass
  (clients#356); spawn requests are paced by wall clock instead of one per frame (clients#947);
  the post-warp fat-roll gap in `no_equip_load` is closed (clients#359); the overlay console
  follows a sweep burst until you scroll it yourself (clients#357); a seed that does not grant a
  boss-sweep clause no longer carries its baked text (clients#936); and a teardown crash avenue is
  closed by retiring the captured inventory pointer at world exit (clients#353).
- **Diagnostics:** probes toggle live from `apconfig.json` with no restart (clients#166); the
  crash reporter decodes id-shaped fault values against this seed's own tables (clients#351) and
  carries the session's scaling-write tallies (clients#367); a probe-gated full id-set dump feeds
  the scaling census (clients#368); the save-marker flag-band audit is recorded with the tool
  that reruns it (clients#370); the scaling census shows the HP-pending population session-wide
  (clients#365).

## v0.4.10 — 2026-08-19

### What you need to update

- **Client:** Required — use the v0.4.10 client with v0.4.10 seeds.
- **APWorld:** Host-only — the room host or generator must install v0.4.10; joining players only
  need the matching client.
- **YAML:** **New YAML optional. Existing YAMLs remain valid.** Generate a fresh template only to
  see and select newly added options such as the Malenia goal.
- **Existing seed/save:** New seed required — finish an active v0.4.9 seed with its matched v0.4.9
  client and APWorld; use a new seed for v0.4.10 features.
- **Profile/assets:** No action — this window does not require a profile or asset reinstall.

Window opened from `main` immediately after v0.4.9 was tagged. The release tag's only commit not on
`main` is its client-gitlink bump; this window supersedes that pin with the v0.4.10 client, so no
player-facing work is stranded between the tag and this branch.

`CONTRACT_HASH` remains `dc0dc687`, verified by loading `contract.py` after the bump. The slot-data
shape is unchanged, but the exact-version handshake still moves to 0.4.10.

Client half: clients#320. Its commit is pinned by the gitlink in this same change.

`release/CHANNELS.tsv` promotes `stable` to v0.4.9 in this same commit.

Entries arrive below as they merge (rule 14: the release notes are part of the change, not part of the release).

- **`cross_game_progression: auto` now balances progression per game.** Every partner game
  receives its own near-`1 / number of games` share of your travelling progression, and your
  world reserves the same share of each partner game's advancement in return -- eleven items at
  a three-game table land roughly 4/4 abroad and 3 at home, instead of one aggregate batch split
  however fill happens to land (the motivating seed split them 2/2/7). Multiple slots of one game
  form one combined pool sampled fairly across their players; owner-local items stay local; and a
  capacity shortfall (a tiny partner game, a full world) caps the share at what fits, with
  requested-versus-reserved counts in the generation log. The older one-batch shape kept a name:
  `cross_game_progression: aggregate` -- and an explicit percentage or `never` behaves exactly as
  before. One lever, three regimes; no new option (the draft's separate toggle was folded into
  `auto` before shipping). This guarantees progression-classified placements, not that every item
  survives the spoiler's redundant-route pruning. World: #927.
- **Your weapons finally reach your friends.** At the shipped settings a non-Elden-Ring partner
  received nothing from an Elden Ring slot but filler -- 0 useful items in 498 measured
  placements -- because of a fill-order artifact, not any option's intent (the partner's own
  progression saturated its slots before Archipelago's useful tier arrived). A dedicated
  reservation pass now places each Elden Ring slot's fair share of useful gear into non-ER worlds
  before the general fill: the share is derived per seed (useful pool x the partner's share of
  open locations), `confine_foreign_progression` stays at its curating default of 100, and
  keep_local/local items are respected. Re-measured across the six-generation CI matrix: 0 -> 983
  useful items delivered, pooled composition 1.01:1 useful:filler -- the pool's own mix. The CI
  export guard now asserts the derived floor instead of a margin-of-one (#918). Ruling: Alaric,
  2026-08-20.
- **The region-lock kick table caught up with the census.** Mountaintops of the Giants' lock now
  covers its own catacombs (play regions the full-MSB census attributed to it); the client's baked
  table was three world regens behind, which the main-only drift gate caught. Consecrated Snowfield
  is now a separate rollable region with its own lock, entrance grace, checks, scaling and boss
  sweeps instead of being bundled into Mountaintops (#868). Clients: clients#331 paired the census
  correction; clients#332 pairs the Snowfield split and this gitlink bump.
- **Enia's DLC rows leave a seed that has no DLC.** Thirty-six of the Finger Reader's shop
  checks are gated on Shadow of the Erdtree content -- the remembrance trades consume a DLC
  remembrance, and the DLC boss armor sets release on DLC ceremony flags -- but Enia stands in
  Roundtable Hold, which every seed keeps, so with `enable_dlc: false` those checks existed
  forever-uncompletable, and on older apworlds the fill could park a REQUIRED item on one
  (AzoTax's two-player seed goal-locked exactly there). The set is derived from the vanilla shop
  params, the locations and their pool items now leave a no-DLC seed together through one
  chokepoint, and the coverage gate compares live and static joins under the same answer.
  Reported by AzoTax on Discord, 2026-08-20.
- **The options wizard is five steps, not eleven.** Players called the wall of tabs out: seven
  option tabs, each a flat list, all reading as mandatory. The seven groups are now collapsible
  sections inside ONE Options step (Start / Options / Seed size / Advanced / Finish), each header
  live-counting your changes, with the first section open on arrival. The Start step now says out
  loud that a preset is a complete, playable yaml on its own. Presentation only: the grouping
  still lives in the world's option_groups (one grouping, two surfaces — Archipelago's own
  player-options page is untouched), and the emitted yaml is byte-identical.
- **Auto-upgrade is a setting again, on by default -- and it now covers every pickup.** Since
  v0.2 every received weapon has been silently raised to the highest reinforce level you hold on
  its track; that behaviour is now the `auto_upgrade` yaml knob (default on, so an existing yaml
  changes nothing). The same raise now applies to any weapon the game adds to your bag -- world
  pickups, chests, and the put-it-down-with-Leave-pick-it-up gesture players know from matt's
  randomizer, which is the intended catch-up for a weapon received before you found your stones
  (in-bag catch-up with no gesture at all is planned separately, behind its own option). The
  client also now watches every suppressed pickup and, if one never turns into a check, names
  the item in the log with its `!give` rescue -- the drop-and-pickup gesture can no longer
  silently cost you a weapon. World: #693; client: clients#329.
- **The wizard's Difficulty section opens with Easy / Standard / Hard.** Three quick-picks that
  set the four scaling dials -- Standard is the default curve, whose cap scales to your run's
  length and lands your final region around the scaling of vanilla Haligtree; Easy caps the climb
  near 2x enemy HP; Hard raises the floor, uncaps the top and front-loads the ramp. The dials
  stay real underneath: set one by hand and no button claims you.
- **`vanilla_placement` and `natural_progression` moved to a collapsed Experimental group.** Both
  invert the randomizer's premise and are filed under Advanced (and folded on Archipelago's own
  options page) rather than greeting new players mid-form. Fully supported, just not front-page.
- **The Seed size card stops claiming your Region Locks never travel.** The sentence shipped as
  a constant -- "Your own progression never travels either way" -- while `progression_bias`'s
  default is 0, meaning every Lock rides the multiworld like any other item. The card now derives
  the sentence from `progression_bias` and `cross_game_progression`, and the render gate flips
  the knob and demands the words follow. The player guide also gains the "anything anywhere"
  recipe for the classic-rando feel. From 255's Discord question, 2026-08-20.
- **Each wizard section leads with its essentials.** Fifteen of the sixty options are the
  decisions that shape a run — goal, seed size, DLC ownership, where the items are, who may hold
  progression, death link, and friends — and they render expanded; the tuning sits behind one
  live-counted "More" fold per section, which opens itself while anything inside it deviates so a
  changed option is never out of sight. The tier lives in the world
  (`core._ESSENTIAL_OPTIONS`, validated at import, flowing through the metadata dump), not in the
  page, and it is presentation only: Archipelago's own options page and the emitted yaml are
  untouched.
- **Legacy dungeon bosses are Major bosses now.** The LegacyBoss surface class was absorbed into
  MajorBoss (a boss standing in a legacy dungeon is a major by any player's reading; the split
  earned nothing but a wizard row). A default seed's progression surface GROWS by the 22
  legacy-standing rows that were not already majors -- deliberate, stated here. Yamls that name
  `LegacyBoss` keep loading: the spelling is normalized to `MajorBoss` on read. Under the hood
  the tag survives as roster data (goal and anchor selection are unchanged); only the player
  category merged.
- **The wizard's boss grid is live, and the messy card is fixed.** The progression-surface
  checkboxes' marginal counts, covered-by notes and totals now recompute on every toggle instead
  of freezing at first render (and the class-preset buttons stop jumping the page to the top).
  The Cross Game Progression tooltip lost its raw-markdown engineering essay for three readable
  paragraphs, and named range values render by name -- the slider says "auto", not "-1 (default
  -1)".
- **The Sewer is part of Leyndell now.** The Subterranean Shunning-Grounds merged into the
  capital -- the well is inside the walls, so one region, one Lock, one wall (Alaric's call on
  #842/#917, taken over the alternative of making it independently accessible). Its graces ride
  the Leyndell bundle, its ground rides the Leyndell kick, the capital's rune gate and the
  no-required-progression-behind-the-wall machinery cover it for free -- which also removes the
  #842 hazard of a Great Rune stranding itself on Mohg the Omen -- and the capital reconciler
  treats sewer ground as version-neutral (standing in the well never rewrites the Royal/Ashen
  map flags). `num_regions` tops out at 27; no shipped yaml or preset named a higher value or
  the Sewer as a start region. Client: the region-lock table regen in the paired gitlink.
- **Malenia can end the run.** `goal: malenia` force-keeps the Haligtree and withholds its Lock
  from fill until the seed's independently selected Great-Rune and region requirements are met.
  Opening it grants Haligtree Canopy alone—even under the all-graces or grace-attunement settings—
  so Loretta, Elphael and the full descent to Malenia remain physical play. The terminal check is
  Malenia's f510200 defeat, not every Haligtree major boss. World: #861.
- **Starting-region candidates now count honestly before you generate.** The additive behavior is
  unchanged: every region in `start_region_pool` is kept, while only `start_regions` of them open
  the run. The wizard's seed-size preview now includes those extra regions and shows their marginal
  0–N contribution beyond `num_regions`; generation logs distinguish them from goal force-keeps
  instead of calling them `goal=auto`. World: #841.
- **The v0.4.9 Radahn stall is fixed.** The known issue that closed the v0.4.9 notes -- an
  enemy-randomizer kill during the Radahn festival leaving the fight unfinishable -- is repaired:
  the client backfills the festival state flags (9130/9412) raise-only when the boss dies without
  its ceremony, so the arena resolves and the check fires. clients#326.
- **Six client repairs ride this window's pin, each closing a reported wedge.** Received items
  now cursor against your Elden Ring character identity, not the connection -- a fresh character
  starts at zero and a reconnect cannot replay or skip a delivery (one cause of the "receiving
  dead" family; clients#327). A contained panic during AddItem no longer poisons the receive
  state -- delivery resumes instead of stalling silently (clients#324). A capital warp against a
  target the current world state cannot resolve is rejected instead of dumped mid-air (the
  stuck-burnt-world class; clients#325). The withheld-goal gate FAILS OPEN when its inputs are
  unresolved -- a data gap can no longer seal the goal room shut, only widen which flags write
  (clients#323). And the rescue console grew `!grace` / `!unlockgrace` -- search by name and
  light any Site of Grace when a seed strands you (clients#328). The auto-upgrade pickup parity
  and its suppressed-pickup watchdog are described above (clients#329).
- **This change also moves the client pin to clients#333's merge commit** -- the same tree the
  previous pin named, recorded at client `main` so the release tag's pin check reads current
  rather than one-merge-behind.
- **The two Region-Lock travel settings now describe separate axes.** `progression_bias` controls
  how many Locks leave their owner, but ordinary fill does not promise those Locks to a much smaller
  partner game; measured cross-game seeds could send that partner zero. `cross_game_progression`
  is the setting that deliberately chooses the non-Elden-Ring share. Documentation only; seed
  behavior is unchanged. World: #633.

## v0.4.9 — 2026-08-18

Window opened 2 commit(s) PAST the v0.4.8 tag.

`CONTRACT_HASH` remains `dc0dc687`, verified by loading `contract.py` after the bump. The slot-data
shape is unchanged, but the client half still moves because its generated handshake embeds the
world version.

Client half: clients#286. Its merged commit is pinned by the gitlink in this same change.

`release/CHANNELS.tsv` promotes `stable` to v0.4.8 in this same commit.

Entries arrive below as they merge (rule 14: the release notes are part of the change, not part of the release).

- **Small-region `keep_out_of_shops` seeds generate cleanly.** The option now decides what fits
  after progression reservations and places the constrained subset with the restrictive filler,
  so an Ensis start no longer strands Cipher Pata opposite Enia despite having legal non-shop
  space. Abyssal and Jagged Peak explicitly relax the oversized category instead of ending in a
  `FillError`; the generation log names every category that could not fit. World: #903.
- **The tracker no longer waits forever for Patches to die.** Patches yields in normal play, so
  his death-flag sweep is no longer sent to the client or advertised as an "also granted by" route.
  Merely unnamed or unaudited sweeps remain available as ordinary convenience grants; only triggers
  positively known not to fire are removed at runtime. World: #878.
- **Previously vanilla-only unique rewards are now checks.** Exact item coordinates recover seven
  missing merchant Bell Bearings, the Serpent Crest Shield, the Sacred Tower painting, and fixed
  pot/bottle pickups; the same audit places Thops's Academy Glintstone Staff, the Discarded Palace
  Key, Comet Azur, Stars of Ruin, and Coastal Cave's Tailoring Tools at their real sources. The full
  30-item residue is committed with a verdict for every duplicate, multi-site, phantom, dead, or
  itemless row, so the old raw "621 unplaced" label cannot return as a defect count. World: #218.
- **Merchant Bell Bearings only enter seeds that keep one of their merchants.** A bell whose every
  merchant region is sealed now pays normal filler count-neutrally instead of opening a wholly
  vanilla Twin-Maiden shop that looks like a failed randomizer. When a vanilla-only bell is handed
  in anyway, the client now says that plainly instead of presenting an apparently empty AP shop.
  World: #560 and #555; client: clients#297.
- **Unaudited boss sweeps cannot host required progression.** A sweep with no authoritative arena
  region still pays its ordinary members, but contributes no `SweepSlot` progression-surface entry
  until the arena is audited. The current 26 circular-evidence triggers now fail closed. World: #671.
- **Lansseax's Glaive is filed in Altus.** Its two independently placed acquisition sites both
  resolve to Altus; the generator now accepts unanimous region evidence from multi-map checks instead
  of letting a one-site entity fallback misfile the incantation under Mt. Gelmir. World: #502.
- **The Golden Hippopotamus is Scadu Altus everywhere.** His fight is fought standing in Scadu
  Altus (the arena play-region), so the reward, the sweep, AND all ~105 checks he grants now present
  under `Scadu Altus ::` instead of `Shadow Keep ::`. Before this, a player holding the Shadow Keep
  lock without Scadu Altus was shown a hundred-plus Shadow Keep rows "also granted by Golden
  Hippopotamus", walked to the fight, and was ejected by the region guard; now those checks exist
  exactly in the seeds that can fire the Hippo, and killing him from Scadu Altus alone pays all of
  them. The one m21_00 pickup he does not grant (a cookbook) stays Shadow Keep. World: #885, from
  cokeman5's report on #330.
- **The 124 unfindable Rada Fruit "locations" are no longer checks.** The DLC's most repeated
  tracker row was mostly bundle math: vanilla expresses one "Rada Fruit xN" corpse as N consecutive
  item lots (each with its own flag), and 55 more lots reference no world object any datamine can
  find -- in a fully-combed Shadow Keep, exactly one of its 125 Rada rows ever fired outside a
  boss-kill sweep. Those rows leave the pool and their pickups revert to vanilla fruit; the four
  uniquely-placed m21 pickups and all of Belurat/Enir Ilim's real corpses (which do fire) remain
  checks. Shadow Keep's tracker list now reflects what a player can actually find. World: #330,
  reported three times by cokeman5.
- **The world census now covers every map, and it culled 77 more phantom checks.** Alaric's
  full-MSB datamine (every map's treasure, enemy-attached, and event-chained references, merged
  with the prior partial run) closed the census's 39 blind maps; the coverage witness now FAILS
  the build if any placed map goes blind again or the denominator comes back empty. Against that
  zero-blind-map census, 77 map-encoded ground-lot flags -- Golden Rune "around <grace>" rows in
  Siofra, Mohgwyn and the Shaded Castle among them -- reference no world object in ANY corpus
  (coords, census, gifts, quest scripts, bell hand-ins, and #898's audited tile placements) and
  leave the pool exactly as the Rada rows did: pickups revert to vanilla, ledgered under
  `worldless_single`. 49 near-identical rows were kept OUT of the cull by three screens: 40
  because EMEVD scripts award them (evergaol drops like Godefroy's Icon, the #653 inverted-tower
  trio -- scripted awards are real checks the ground census cannot see), 8 because #898's audited
  unplaced-tile datamine places them (Eleonora's Poleblade among them), and 1 by hand ruling (the
  Roundtable's Crimson Hood, awarded by a flag-level EMEVD reference the lot-based screen cannot
  see). 5115 -> 5047 locations
  net of the census's own +9 recovered pickups. World: #330 follow-up, the "any other phantoms?"
  sweep.
- **A boss's own drop is granted by killing the boss, even under a host enemy randomizer.**
  Vanilla awards a field/evergaol boss's drop only when its own character dies (common event
  90005860); an enemy randomizer's replacement sets the defeat flag without that death, so the
  kill paid the boss's swept member checks but never its own drop -- CptFabulous's Lansseax's
  Glaive, holding his Liurnia Lock, was the report. All 73 admissible own drops (region-agreeing,
  live-check, sweep-holding triggers) now ride their own trigger's sweep: the moment the defeat
  flag fires, the drop check fires with it, whoever actually died in the arena. The 15
  inadmissible rows fail closed and are pinned by the acceptance test. World: #907.
- **Packaged me3 profiles now name the package that actually ships.** Stable bundles load the
  authenticated `flower-package`; development bundles with no Flower assets omit the package entry
  instead of asking me3 to scan a nonexistent `ap-package`. Both release packagers now reject any
  profile whose declared package directory is absent, preventing the startup `ReadDir: Path not
  found` failure from returning.
- **Ashen Capital opens at Leyndell, Capital of Ash.** Its region unlock no longer treats the
  duplicate Ashen East Capital Rampart as the front door; the full grace bundle still contains both
  entries. World: #853; client: clients#312.
- **Boss-sweep rows collapse by region, and legacy arenas wait for their terminal state.** The
  tracker no longer expands every member of every sweep into one permanent wall of rows; each region
  can be opened when wanted. For inherited arena triggers, completion now follows the terminal flag
  instead of an earlier phase that can fire while the encounter is still live. World: #877 and
  #896; client: clients#293, closing #237.
- **Fresh auto-equip runs keep one left-hand slot, not the starting class's whole off-hand
  loadout.** Left 1 is filled and Left 2/3 are cleared once for a genuinely fresh character; returning
  saves keep the loadout their player arranged. World: #441; client: clients#294.
- **The experimental boss HP probe is off by default.** The runtime witnesses it was built to gather
  are in hand, so ordinary players no longer pay for its live boss-state reads unless they explicitly
  arm the probe. World: #553; client: clients#290.
- **Client sidecar tables resolve beside the AP DLL.** `check_lots_table.json` and
  `shoplineup_flags.json` no longer disappear merely because me3's global mod root differs from the
  profile's natives directory; the loader-root lookup remains as a compatibility fallback. Client:
  clients#302, closing clients#299.
- **World teardown no longer turns an empty param holder into a process abort.** Add-item and
  shop-open callbacks now test the requested table's live holder before reading it, and the extern
  boundary contains any remaining Rust panic instead of unwinding through Elden Ring. Client:
  clients#303, closing clients#300.
- **Starting items have one writer at a time.** The possession backfill now waits until the
  reconciler's complete negative start-item band is drained, rather than treating a readable bag as
  proof that the paced grant ledger is finished. This closes the 2-of-40 race that duplicated pots
  and then reported the remainder capped. World: #267; client: clients#304.
- **Native crash reports now include the faulting x64 registers.** This does not claim to fix the
  separate me3 allocator crash. It makes the next occurrence identify the exact pointer me3 was
  classifying/freeing, so the remaining corruptor can be narrowed from evidence instead of by
  disabling unrelated features. Client: clients#305; follow-up: clients#301.

## v0.4.8 — 2026-08-18

v0.4.8 is the first release after v0.4.6. v0.4.7 was never tagged or released; the number is
intentionally skipped rather than rewriting the already-generated world/client version state. Every
change accumulated since v0.4.6 is recorded in this one release window.

`CONTRACT_HASH` eventually moved from `5c2b9bf2` to `dc0dc687` when armor bundles added the
`armorBundles` map. That feature intentionally refuses clients which can only map one AP item to
one Elden Ring FullID instead of silently losing part of a set. Client half: clients#277.

`release/CHANNELS.tsv` correctly leaves `stable` on v0.4.6 until v0.4.8 is actually tagged.

Entries arrive below as they merge (rule 14: release notes are part of the change, not tag-time
reconstruction).

- **Armor sets now occupy one randomized item instead of one slot per piece.** Families are generated
  from the protector rows, include altered pieces, and reconcile member-by-member across reconnects.
  Tight pools also deduplicate exact weapon names and retire the two trick mirrors and Sacrificial
  Twig into ordinary filler economy capacity.

### The rest of the v0.4.8 window so far

- **Goal requirements are two independent axes.** Great Runes can be required or not, while the
  goal region separately opens from held Region Locks, completed regions, or no region requirement.
  This adds Great Runes-only goals without changing existing YAML defaults. Patches, Enia, and the
  Twin Maidens now reject progression at the location rule as well as the curated surface, so a
  required Great Rune cannot reach those shops through a spill or later fill pass; ordinary
  wandering merchants remain eligible. World: #858.
- **Tiny seeds keep their promised somber-stone floor.** A positive `somber_stones` recipe weight
  now arms the reservation even when its initial proportional share rounds to zero, so one-region
  seeds cannot silently lose an upgrade tier. World: #858.
- **Baked-stable hosts can deploy beta without a false stable success.** `deploy_wizard.sh
  --beta-only` writes only the directory peliarch actually mounts and reports that stable remains
  owned by the immutable image pin, closing the misleading half of #863. World: #864.
- **Progressive stone bells now stay local and actually stock their shelves.** Their replacement
  items inherit `keep_local: [upgrade_bells]`, and every rung sets both the stock and release flags
  used by the Twin Maidens. World: #859.
- **Capital warps respect the selected map version.** Royal and Ashen targets are classified by
  their real map bucket, including the duplicate Ashen graces, so approaching the Ashen endgame no
  longer replays the transition and throws the player back. Client: clients#284.
- **Client logs always live beside the loaded DLL.** Their location no longer changes with the mod
  loader or profile. Client: clients#283.
- **RandomizerHelper is a hard incompatibility, not a warning.** When its DLL is actually co-loaded,
  AP stops before connecting and explains what to remove; a merely present but unloaded file does
  not block startup. Client: clients#285.
- **Quest prerequisites cannot be placed on their own downstream rewards.** Cursemark of Death
  cannot land on Fortissax, with direct rules also covering the Favor, Needle, Valkyrie,
  Fingerslayer, and Dark Moon chains. The items remain filler elsewhere. World: #836, closing #832.
- **TrapLink is opt-in.** ER traps can cross the multiworld; self-echoes and unknown foreign names
  are ignored, and DeathLink remains independent. World: #844. Client: clients#273, closing #758.
- **Hefty Pots and perfumes join DLC curated filler.** Crafted finished pots, aromatics, and the
  smaller throwable pots arrive in useful quantities; reusable vessels stay out. World: #846,
  closing #843.
- **A capped reusable pot no longer blocks every later delivery.** The safety cap still suppresses
  the impossible bottle but advances past the permanent refusal. Client: clients#272.
- **Leyndell's rune gate has an independent backstop.** Flags 105 and 182 are re-derived from
  cumulative AP Great Runes, covering ordinary sends, server `/send`, reconnects, and mid-seed
  upgrades. Client: clients#274.
- **Checks observed across a death/load edge remain report debt until accepted.** Pickups, shops,
  and sweeps no longer depend on one transient frame surviving transport. Client: clients#276,
  closing #720.
- **Dragon Communion and Bayle checks cost one unit of their currency.** World: #835, closing #231.
- **Small-seed Scadutree supply survives tail trimming.** World: #848.
- **Smaller fixes:** Cliffroad's shadowpot stays in Gravesite (#839); the wizard stops advertising a
  frozen surface mode (#840); release bundles keep their requested name instead of inheriting
  `shoplineup_flags.json` through PowerShell's case-insensitive `$Name` (#847).


### Progressive Flask upgrades alternate instead of doubling up

Every Progressive Flask Upgrade used to move both axes at once: charges climbed on an escalating
schedule and potency rose by one Sacred Tear on the same copy, so each upgrade was two half-things.
Copies now alternate deterministically -- charge, potency, charge, potency.

The first copy takes you to **five** total charges, one above the vanilla starting allocation of
four, so it can never be silently absorbed by a fresh character; the old ladder opened below that
allocation, which made the first upgrade or two invisible by construction. Each later charge copy
advances one more observable step until the vanilla cap. Potency is still one consumed Sacred Tear
spent at a grace, now on even copies only.

Each copy therefore carries half as much, so the ladder is twice as long: a seed with no kept Golden
Seed or Sacred Tear check (`dlc_only`, or a `num_regions` seed that seals every flask region)
injects **24** copies instead of 12, which is what both axes need to reach their caps. A seed with
fewer copies tops out honestly below potency 12 rather than pretending otherwise. Flasks never gate
logic, so either way the seed is winnable.

Closes #798. Client: clients#263 -- an alternating ladder needs explicit no-op rungs to keep its copy
index, so `progressiveGrants` now accepts a `{"noop": true}` rung. That is a new rung shape on an
existing key, so `CONTRACT_HASH` does not move; a client without clients#263 loses the index.

### Filler pays out the quantity the source lot actually carried

A vanilla lot holding one arrow was being promoted into the curated quiver's stack, and a lot holding
twenty was being flattened to the base item. Curated bundles now ride their own `<name> x<n>` AP ids
while vanilla-placed items keep the exact units their source lot carried -- that separation is what
lets a vanilla x1 Arrow stay x1 while a curated Arrow stays a quiver. `LOT_STACK_GRANTS` covers every
quantity a source lot actually carries, not just the phase-1 slice.

The curated-filler weights are re-derived on top of that, because the old ones were compensating for
copies the world was discarding. **`stones` drops from 29 to 5 and `juice` rises from 42 to 66.**
Weight 29 was paying for 288 stone copies that never survived; at the real units, `stones: 4` puts
five of nine sample seeds under the 24-unit floor and `stones: 5` clears it. The 24 freed points go
to gear injection, which is the axis that can afford to give; small seeds that need the room have
their useful tail picks trimmed by core's missable-location reserve rather than by a blunt weight.

⚠️ If you have hand-tuned `curated_filler` in your yaml, re-read your numbers: the scale underneath
them moved.

Closes #624. The wizard's copy of the defaults follows in #831.

### Blackout is a real trap now

`Trap: Blackout` joins the catalogue: the screen fades out, holds dark for two seconds, and fades
back in. It is the first of the eleven designed on 2026-08-08 (#114) to graduate from the probe
list, and it graduated on the same rule as the others -- implemented, tested and CI-gated in the
client before its name enters a pool.

Unlike the three older fixed names, Blackout declares its own `blackout` client-capability tag.
Those older names are exact-match and have never changed, so any released trap client fires them and
requiring a tag would refuse clients that can in fact run the seed. Blackout is fixed *and* new, so a
client in circulation would consume it silently. The tag is emitted only when a seed actually mints
one.

World: #824. Client: clients#265.

### A scaling cap on a scaling-off seed stops demanding a client feature

Setting `maximum_enemy_difficulty` below 100 declared the `scaling_ceiling` client capability even
when `enemy_scaling` was off. The connect-time read-back then correctly reported the feature dark and
went on to incorrectly blame a missing value that was in fact present. A cap modifies the scaling
pass; with the pass disabled there is nothing for an older client to mishandle, so nothing is
declared.

Fixes #661.

### Boss sweeps stop losing checks to a stronger region answer

Region ownership and sweep ownership consume the same placement evidence, and the region pass could
answer first and overwrite a row's MSB map, dropping the check out of the map-keyed sweep corpus
entirely. `region_of` now preserves the MSB map on rows still carrying the scanner's `PENDING`
placeholder, and leaves a concrete descriptor map alone -- that stays useful as independent evidence.

World: #830.

### Ancestor urns light up with the doors they belong to

With the catacomb-door option on, both ancestor altars opened and their warps worked, but sixteen
urns stayed dark, so the world told the player the encounters were still closed. Every instantiated
urn flag is now set alongside the aggregate. They are presentation state, not randomized checks; the
boss and its sweep are untouched.

This reverses the earlier ruling that the individual flags stay dark in case the urns became a check
family; #677's follow-up makes presentation part of what the option promises.

World: #821.

### Serpent-Hunter can no longer be hinted

Serpent-Hunter is deliberately absent from the randomized pool -- the client grants it on entry to
Rykard's arena -- and the server was charging hint points to search for it. It is now on the world's
`hint_blacklist`, and asking for it in room chat gets an explanation instead of silence.

World: #823. Client: clients#266.

### The wizard's filler defaults match the world's again

`options-metadata.json` and `wizard.html` still offered `juice: 42` / `stones: 29` after #828
re-derived them. Refreshed, with the source hash following.

World: #831.

### The client's own half of this window

- **Leyndell's seal reads both of its flags.** The physical two-rune seal checks 105 and 182.
  Vanilla supplies 105 through Roundtable / Finger Reader progression and derives 182 from the
  rune-location flags, and either half can be missing when AP supplies the runes and a random start
  skips that sequence. Both are now derived from the same cumulative receive stream ordinary
  deliveries and server `/send` use, and sit in `DesiredInputs` so the active reconciler self-heals
  the write. Flags 171-177 are deliberately untouched: 171-176 are the randomized Great Rune
  location flags and 177 is the same vanilla family. clients#260.
- **A pending boss sweep no longer tells you which boss pays best.** A pending group's exact size is
  routing information. The group and its state stay visible; `members` and `checked` do not, until
  the sweep fires -- at which point the same numbers stop being a way to choose the next boss and
  become confirmation of what happened. Hiding only `members` would have leaked the allocation
  through the ordinary rows. clients#261, closing clients#160.
- **An item that will not fit is retried, not swallowed.** A delivery blocked by inventory capacity
  used to report success and vanish. `grant_full_id` now returns false for that arm, so the receive
  path and the reconciler both hold their watermark and retry the same entry. A partially-fitting
  stack defers whole rather than placing what fits, because placing one of three and retrying would
  duplicate it. A warning line aggregates repeated deferrals so backpressure is visible without
  per-tick spam. clients#262. Refs #692.
- **Only Ashen-exclusive graces force the Ashen capital.** Selecting a capital grace forced the Ashen
  version off whichever map variant the menu happened to be showing. Five of the six m11_05 graces
  have Royal counterparts under the same name, so only the two Ashen-exclusive targets now write the
  burn flag on; every shared grace and every other resolvable target chooses Royal. An unresolvable
  target leaves the flag alone rather than guessing. clients#264.
- **DeathLink can be toggled mid-session.** A session-scoped in-game toggle overrides what slot data
  configured, until reconnect -- including opting a slot that parsed off back in. A kill queued
  before the toggle is cleared rather than left waiting to surprise you when you opt back in;
  cleanup already owed by a kill that fired still finishes. clients#267.

### Previously undocumented -- these shipped in v0.4.6

Rule 14's own failure mode, caught by an audit rather than by the gate: these landed inside the
v0.4.6 window with no changelog line, so anyone who hit them is still looking for the fix. They are
recorded here rather than retro-edited into a tagged section.

- **Progressive stone bells stopped handing you a bearing the game refuses.** A copy granted both
  the physical bell bearing and the Twin Maiden shop-unlock flags. Setting the flags *is* the
  hand-in, so with the stock unlocked the game treats the bearing as already handed in and rejects
  it as over-capacity. The ladder sets flags only; the goods ids (8951-8954 Smithing, 8955-8959
  Somber) are gone from it. `progressiveGrants` was relaxed to match -- a rung may carry goods
  and/or non-empty flags, and a flags-only rung must not declare `consumed`, which is meaningless
  when there is nothing in inventory to reconcile. `CONTRACT_HASH` did not move and no client half
  was owed: the client parser already defaulted `goods` to empty and dropped only fully-empty rungs.
  World: #805, fixing #804.
- **The Moonlight Altar grace left Liurnia's bundle.** It physically stands on Liurnia's tile
  (`m60_34_41`) so the play-region join classified it as Liurnia, and the Liurnia Lock lit it -- a
  shortcut around Lake of Rot and Astel, which is the route that owns access to the plateau. It now
  belongs to no automatic bundle, and deliberately not to Ainsel's either, because that would still
  skip Astel. Its physical checks stay in Liurnia. `gen_data.py` now fails the build if flag 76250
  stops being "Moonlight Altar @ m60_34_41", so the exception cannot go stale silently. This is the
  first **route-gated grace**, a category rather than a one-off. World: #793, closing #792, reported
  by bobler 2026-08-17.
- **The Carian Inverted Statue gate is modelled.** Nine checks behind Carian Study Hall's inversion
  were swept by the ordinary-layout fight; those flags only exist after the statue changes the map,
  so the sweep awarded inaccessible checks and bypassed the key gate. They are excluded by flag, so
  co-checks such as `f34117500` leave together. The gate is in `key_item_gates.tsv` with its
  datamine citation: the pedestal tests `PlayerHasItem(ItemType.Goods, 8111)` and removes the goods
  after the cutscene, so a plain AP grant suffices and no obtained-event flag is owed. World: #787,
  closing #653.
- **There is a Development download channel.** `beta -> main` publishes as the GitHub prerelease tag
  `dev`, a moving pointer, alongside `stable`, which still names an immutable `vX.Y.Z` tag. ⚠️ A
  development build may ship without the AP flower override; when it does it carries a
  `DEVELOPMENT-BUILD-NO-AP-ICON.txt` and every check and AP shop slot renders as a Telescope. The
  packager accepts that opt-out only on an `--unofficial` build. World: #788.
- **A rescue guide ships in the bundle.** `release/GETTING-UNSTUCK.md`, linked from `SETUP.md`: how
  to open the rescue console (F5 -> Console), how to warp out of anywhere, and which flag to touch
  for the progression edges that strand a character. It works while disconnected, which is when it
  is needed. World: #780, closing #722.
- **Item sell values are no longer rewritten for shop visibility.** `shop_value.rs` is gone, along
  with the global param write it performed. Client: clients#250, closing #359.
- **The wizard's progression surface has presets.** "Recommended", "Major bosses only" and the rest,
  instead of 17 flat checkboxes. World: #784. Refs #733, which stays open for the containment
  drawing.
- **Talk-referenced goods are excluded from preview spares**, so a cut bell-bearing row cannot
  produce a `?EventTextForTalk?` shop entry. World: #801, closing #596.
- **Release-gated shops are barred from the advertised surface**, which changes the region-census
  numbers the wizard shows before you generate. World: #783, closing #724.
- **Scaling reads are correlated by instance** in the boss-fight probe and rescale watch -- the
  instrument for clients#251, which stays open. Client: clients#252.

### Cosmetic: the AP Flower works outside the shipped profile

The packaged Mod Engine 3 profile already loaded the AP Flower. The Telescope reports came from
other mod layouts that did not load our atlas override, so this was never an across-the-board icon
failure.

The discarded first attempt rebuilt FromSoftware's atlases on each player's machine and assumed a
local texture toolchain. That path, and its short-lived in-client launch button, were reverted.
Release bundles can instead carry the two authenticated prebuilt atlases, and the standalone Python
installer copies them transactionally into Matt's randomizer data-mod root. It supports safe
install, update, repair, and hash-checked uninstall; PowerShell is only a thin Windows launcher.
Linux and Windows CI exercise the shipped entrypoints against a synthetic authenticated package.

The runtime experiment still established that Elden Ring accepts the DFLT-repacked hi and low
atlases and renders the Flower without runtime texture injection. Players do not need UXM,
WitchyBND, Oodle, Pillow, or texconv for the packaged-asset installer.

World: #819, #826, #856, #857. Client: clients#270 reverted by clients#282. Refs #818, #827.

## v0.4.6 — 2026-08-16

Window opened AT the v0.4.5 tag (`4d96806`), with zero commits past it. That is the third window
opened while every gate was still green and the second in a row: `check_release_notes` reported
`v0.4.5 is tagged and HEAD is at it -- nothing has landed since` rather than failing, so this open
pre-empts the red the next commit would have produced instead of paying one.

`CONTRACT_HASH` is unmoved at `5c2b9bf2` -- the shape the contract has had since 0.3.9 -- so this is
version-lockstep and a v0.4.5 client still handshakes with a v0.4.6 seed. Verified by loading
`contract.py` after the bump and reading the value, not by assuming the shape did not move. Worth
saying explicitly this time: v0.4.5 withheld the goal region's Lock, which changes what the item pool
contains, and it still moved no contract key -- the client was already told which lock to grant.

`release/CHANNELS.tsv` promotes `stable` to v0.4.5 in this same commit. That is the second window
running it has not lagged its tag; before v0.4.4 it lagged every time.

🛑 A client half IS needed, and the last two windows' notes said it was not. `contract_gen.rs` is
generated into the client repo and embeds the version string, so a version-only bump moves it even
when the hash does not — the `generators` gate goes red until the gitlink follows. The v0.4.5 client
commit caught this, wrote *"a version bump always needs this half"*, and promised to correct the row
it came from; the correction never landed, so the next window-opener read the old sentence and
repeated it. Client half: clients#246, gitlink bumped in the same commit (AGENTS §7).

Entries arrive below as they merge (rule 14: the release notes are part of the change, not part of
the release).

### Altus opens at the lift, not inside two unrelated side entrances

With `region_grace_unlock: entrance`, receiving the Altus Lock lit **Old Altus Tunnel** as the
region-open flag and **Abandoned Coffin** as the entrance bundle. Bobler's playtest saw both. The
two derivations independently chose their lowest numeric candidate, and neither candidate is the
way into Altus from the Grand Lift.

Both now resolve to **Altus Plateau** (`76301`), the lift-side grace. The same ruling is carried
through the landmarks tier so the three grace tiers remain nested: moving from landmarks to
entrance removes warp points and never swaps one for a different one.

Refs #641.

### Ainsel and Stormveil open at their real front doors

The entrance tier now grants **Ainsel River Main** for the Ainsel River component instead of
requiring a grace already present in generated region data. Stormveil now owns Margit, his tunnel
entrance, and the Divine Tower approach, keeping boss sweeps in the same region as the boss that
fires them. The generated client region table follows the same boundaries.

The first client integration lost Stormveil's Divine Tower runtime bucket during a merge; a focused
follow-up restored it before release.

World: #803, #807. Client: clients#253, clients#257.

### Metyr's quest is logic now, not a free bell at spawn

The run used to force the Finger Ruins of Dheo bell flag at spawn to make Metyr reachable without
Jagged Peak. Loading the ruins then awarded its check automatically, and the forced flag bypassed
the Hole-Laden Necklace the real bell requires.

Both existing bell checks now describe ringing their respective bell and require the necklace.
When both regions are live, Metyr additionally requires access to Scadu Altus and Jagged Peak,
matching the two bells that open her throne, and neither bell is forced. If Jagged Peak is sealed,
its absent check costs nothing and Dheo alone is supplied so Scadu Altus does not contain an
impossible Metyr check. Neither bell check can ride an unrelated boss's filler sweep.

Closes #665.

### Missable checks stop eating useful gear by default

The 285 checks that can disappear behind a spent currency, a killable NPC, or questline state used
to protect only required progression. They could still consume useful weapons, spells, spirit ashes,
crystal tears, and other build-defining rewards. The default now leaves only filler at those checks.

The setting is now an explicit three-level choice: `off`, `progression` (the previous behaviour), or
`progression and useful` (the new default). Existing YAML booleans remain meaningful: `false` is off
and `true` selects the new default. A seed whose pool cannot supply enough eligible filler is refused
with a specific option error instead of silently switching the protection off.

Closes #582.

### Great Rune goals now mean any four of seven

The Great Rune ending previously defaulted to two and turned the option into a seed-selected named
checklist. Holding the requested number of different Great Runes could therefore fail to finish the
run. It now defaults to four and counts any four distinct Great Runes from the full seven-rune pool;
no particular rune is mandatory. The slot contract exposes the full eligible set and the required
count separately so the client reports and enforces the same rule.

Fixes #813.

### The client enforces the same Great Rune and capital rules

Great Runes received through Archipelago now count toward Leyndell's two-rune seal, and the ending
counter counts any required number of distinct runes from the full eligible set rather than a named
prefix. Divine Tower altar flags are disarmed before an AP rune is delivered, preventing the game
from granting a duplicate vanilla rune when its tower later loads.

The capital reconciler now applies the complete world state: it selects Ashen Capital, sets the
world-burn state, clears the pre-burn state, and preserves that choice while an asynchronous warp
still reports the stale source capital. This fixes both the capital warp race and front-door grace
state that could otherwise regress on reconnect.

Client: clients#248, clients#254, clients#255, clients#256, clients#258.

### Grace rescue commands are pasteable and data-independent

`!grace` now resolves names against the live `BonfireWarpParam`, including valid graces absent from
the generated seed tables, and prints a pasteable `!warp <entity>` command. Parser aliases, console
help, and the overlay all use the same command registry, so the documented rescue syntax cannot
drift from what the client accepts.

Client: clients#247.

### Rakshasa no longer rings a Finger Ruins bell for you

Killing Rakshasa could grant the Cerulean Seed Talisman +1 check from the Finger Ruins of Rhia.
Both checks happened to share the broad Scadu Altus sweep pool, even though the bell is unrelated
to Rakshasa and requires the Hole-Laden Necklace.

That reward is no longer in Rakshasa's sweep, and logic now requires the necklace at the Rhia bell
itself. This also clears the concrete bypass that blocked the ruled Metyr logic model in #665.

Closes #664.

### Cross-game progression now includes required Great Runes

`cross_game_progression` previously routed only released Region Locks. Required Great Runes and
legacy keys were progression too, but the strict surface prefill removed them first and locked them
into their owner's world; Archipelago's later balancing pass can only move advancement that is
already foreign. Bobler's seven local Great Runes exposed the gap: five were useful and could be
local by chance, but the two required by his goal were local by construction.

With a non-zero cross-game share, non-Lock advancement now joins released Locks in the stage-wide
placement pass. The candidate order is shuffled before the foreign quota is sliced so leading Locks
cannot consume the entire share merely because they were constructed first. A zero share preserves
the old local-surface treatment for runes and keys.

Closes #811. Corrects the diagnosis, but not the underlying observation, in #808.

### The CI test suite uses both runner cores

The world pytest step was the workflow's critical path: **413 seconds** in the measured green run,
while the next-longest concurrent job finished in 183 seconds. It ran CPU-bound seed generation on
one of the hosted runner's two cores.

Pytest now runs two process-isolated workers, balanced by whole test file. In the same warmed,
CI-equivalent layout the full guarded suite moved from **224.7 seconds to 130.4 seconds** (42%
faster): 2,529 tests and more than 424,000 subtests in both runs, with the vacuous-quantifier spy
and exact 70-skip census still armed. File-level distribution keeps every module's tests together
and gives monkeypatch-heavy suites separate processes rather than shared global state.

The first parallel run also caught a bug in the skip-census instrument itself: xdist delivers every
skip report in its worker and again in the controller, so the recorder counted every skip twice.
It now writes only from the controller under xdist, with a red-case test for both halves.

Closes #778.

### A refused connection has a troubleshooting path that actually narrows the fault

The setup guide used to send a player back through the room page, address and protocol before it
asked the one question that divides the problem cleanly. It now starts with Archipelago's stock
Text Client against the same host and port: if that also fails, investigate the room or network; if
it connects, the address is exonerated and the fault is specific to `eldenring.exe`.

The next steps distinguish an immediate refusal from the roughly 20-second timeout that currently
prints the same message, then name the per-process filters worth checking: a forgotten outbound
firewall block, antivirus network protection, VPN split tunnelling, or another Mod Engine profile
component hooking WinSock. Wrong slot, password, game and seed mismatches are explicitly ruled out;
they produce later, specific errors and are not reasons to re-read a refusal form.

Closes #613.

### Three playtest probes graduated into decisions

Bobler's 2026-08-17 log closed three client investigations that were still running as default-on
diagnostics.

Enemy scaling now distinguishes the write from the engine's HP reconstruction. An unloaded enemy
accepted rung `7010` while retaining its old `6577` max HP, then loaded at `2792` with no second
write — exactly `NpcParam.hp 2447 * 1.141`. Loading reconstructs HP from the carried rung. The
opposite experiment was just as decisive: three `ready` enemies stayed stale after three
remove/re-apply cycles, so `ready` is not sufficient and repeating the same write is not a
recompute primitive. The client no longer churns those retries; it reports a stale loaded write
once and lets an unloaded write take effect when the character is constructed.

The AP item scout returned all **1,760/1,760** requested locations, and the downstream shop pass
reported **zero missing scout entries**. The cache is production infrastructure now, not a proof:
its request/result/failure telemetry remains, while the 1,760-line dump of every seed item is gone.

The AP-flower seam probe found the game's `oo2core_6_win64.dll` loaded and confirmed that the
mip-0 flower is a **25,600-byte** block-aligned splice inside the **8,388,608-byte** shipped atlas.
No lower mip is block-aligned. That census is retired; the remaining work is visual rather than
another player log — test whether the loader accepts a non-KRAK DCX, and whether a mip-0-only flower
stays correct at every UI scale.

Client: `cac7bf3`, with the retired icon probe removed in `40b6ffc`.

## v0.4.5 — 2026-08-16

Window opened AT the v0.4.4 tag (`1ffac04`), with zero commits past it. `check_release_notes` was
reporting `HEAD is at the tag -- nothing has landed since` rather than failing, so this open
pre-empts the red the next commit would have produced instead of paying one. v0.4.4's own section
records the contrast: it opened one commit late, on the red that #718 caused.

`CONTRACT_HASH` is unmoved at `5c2b9bf2` -- the shape the contract has had since 0.3.9 -- so this is
version-lockstep and a v0.4.4 client still handshakes with a v0.4.5 seed. Verified by loading
`contract.py` after the bump and reading the value, not by assuming the shape did not move.

`release/CHANNELS.tsv` promotes `stable` to v0.4.4 in this same commit rather than the next morning.
That row had lagged its tag every time so far -- two tags in August, two more in July -- and
`check_channels` stayed green through all of it, because it asks whether the pointer RESOLVES and
never whether it is CURRENT.

Entries arrive below as they merge (rule 14: the release notes are part of the change, not part of
the release).

### The ending stops being reachable before you have earned it

You could walk into Radagon one Region Lock deep, watch the ending, take the credits, and land in a
post-ending save with no victory sent. Expected, documented, and still the worst possible time for
the one irreversible thing in a run to happen.

The Ashen Capital's Lock is no longer an item in the pool. The client grants that region's graces
itself, the moment you hold every other goal item — so the arena simply is not there until the run
is done, and there is nothing to walk into early.

No wall was built for this. The fog plane is walk-through by design, the vanilla capital gate reads
*possession* of a key item rather than a flag we could withhold, and ejecting the player is this
project's known way to make a seed unwinnable. What was left was the observation that the key worth
withholding was one of ours all along: you reach the Ashen Capital by warping to its own graces, so
holding the Lock back holds the arena back.

⚠️ **A one-region `region_locks` seed is now refused at generation.** Its only Lock goes to your
starting region, nothing is left to find, and the goal is complete the moment you connect. That was
previously papered over by the Ashen Lock being a second item in the pool — with it withheld, the
seed is genuinely empty rather than merely small, so it is refused rather than shipped.

The refusal is a **yaml lint**: it happens the moment your options are read, before a draw or a pool
is built, and the message names both numbers and every lever that gets you out — fewer starting
regions, more regions, or a Great Runes ending, which is exactly what the required runes are for.

Needs the matching client (#245).

**The DLC ending is covered too, and it was not at first.** `goal: promised_consort` ends the run in
Enir Ilim, and unlike the Ashen Capital that is a region the draw keeps — so its Lock was an ordinary
find and could still land in your first sphere. It is withheld on the same terms now, and the region
opens when you hold everything else. Nothing about the base-game ending changes; that ending is the
one that was already covered.

No client update is needed for this half: the client already works out which Lock is being withheld
from the goal locations the seed sends it, rather than being told a region name.

### Every seed has all seven Great Runes, and the goal can ask for any of them

A Great Rune sits on exactly one region's boss. So the number of Great Runes in your seed was
whatever your region draw happened to keep — seven on a full Shattering, **one** on a three-region
seed — and every consumer downstream silently clamped to that number.

bobler's seed is the case. Three regions, `ending_condition: great_runes`, `goal_great_runes: 2`,
and exactly one Great Rune in the entire multiworld:

```
Number of Regions:    3
Great Runes Required: 2
  great_rune_items = ["Godrick's Great Rune"]
```

He asked for two. The seed gave him one, and printed `Great Runes Required: 2` four lines above the
resolved set containing a single item. His run was still winnable — the clamp exists precisely so it
would be — just shorter than he configured, which is the failure that is hard to notice.

**All seven are now injected into every seed's pool, whatever you drew.** `goal_great_runes`'s
1–7 range means what it says on every seed, the requirement is never silently reduced, and a Great
Rune arriving for a demigod your run does not contain is now a documented rule rather than a
surprise.

⭐ **And the required set stopped being alphabetical.** It was `sorted(available)[:N]`, and
`GREAT_RUNES` is itself sorted — so at the default of 2 the goal named **Godrick's and the Great Rune
of the Unborn, on every seed, forever**. Rykard's sorts last and could only ever be required by a
seed asking for all seven. That is exactly what AHHHREPTAR reported ("Rykard's Great Rune considered
filler despite setting goal to Great Runes") and it was never seed luck. It is a seeded draw now, so
any rune can be the one you need — still reproducible from the seed, just not from the alphabet.

Injecting all seven made that urgent rather than optional: with the pool fixed, an alphabetical
prefix is a *constant*, and the goal would have named the same two runes in every seed this world
ever rolled.

🛑 **DLC Only changes.** A `great_runes` ending used to collapse to `region_locks` there, because no
Great Rune boss stands in the Land of Shadow and the requirement was clamped to what the draw
supplied — under DLC Only, zero. The supply no longer depends on the draw, so the goal works: seven
runes, arriving from the multiworld and from DLC checks. The option help, the player guide and
`KNOWN-ISSUES` all said the old thing and now say this one.

Also: a Great Rune is never `filler` any more. They are GOODS, so they defaulted to junk unless some
gate happened to name one — survivable when the pool held two, not when it holds seven.

The top-up moved out of `features/leyndell_gate`. It was there because the capital wall needed it
(#589 — a one-rune seed sealed Leyndell, the Sewer and Ashen Capital behind a door nothing could
open), and it only ran when Leyndell was in the draw. bobler's seed had no capital, so nothing
topped anything up. A supply floor that exists only when one particular consumer is present is not
a floor; the wall reads the supply now and no longer creates it.

Closes #764, #640. Fixes the clamp half of #504.

### `vanilla_placement` stops building a wall the base game never had

A `vanilla_placement` seed puts every item exactly where Elden Ring puts it, and the mode's own
docstring promises that "the region locks are not used at all ... and the Leyndell wall, the Rold
Medallion and every other door work as they always did". Our *synthetic* two-rune capital wall was
still arming on top of that, on runes it picked itself — and on seed
`60255596019398880819` it picked **Morgott's, whose rune drops inside Leyndell**. The wall gated the
capital on a key kept behind it: `can_beat_game()` false, Leyndell and the Ashen Capital unreachable.

⭐ **The self-gate is old; only its visibility is new.** Selection used to be `sorted(avail)[:want]`
and Morgott's sorts fifth of seven, so a two-rune wall could never reach him. #640 replaced that
prefix with a seeded draw — correctly — and the draw can reach him. Fixing a real defect exposed a
latent one; #640 is not the mistake.

The synthetic wall disarms under `vanilla_placement` now, beside the three conditions that already
disarm it, and says so in the log. 🛑 Disarming it is normally a softlock risk (#589 — it is what
stops fill placing something needed behind the game's fixed gate), but that argument does not reach
this mode: fill has no freedom here, and the base game is winnable.

Bisected rather than guessed — 6 runs per ref: v0.4.4 tag 0/6 red, #762 0/6, #761 0/6, `694d437` 2/6,
`main` 4/6.

Closes #769.

### Sweep slots can be priced by how big the boss was

A sweep payout off a legacy boss and one off a cave boss are different bargains, and `SweepSlot`
priced them the same. `SweepSlotMajor` and `SweepSlotMinor` are subsets of it, **off by default** —
a seed that does not ask for them is byte-unchanged, the same way `Boss` / `LegacyBoss` / `FieldBoss`
already work.

"Major" means exactly the `MajorBoss` progression-surface class. Measured, that is not `legacy`: the
two disagree **46 ways** — 41 legacy triggers are not major (both Tree Sentinels, all three Scadutree
Avatar heads, Esgar) and 5 majors are not legacy (Magma Wyrm Makar, Commander Niall, Elemer of the
Briar, Leonine Misbegotten, Royal Knight Loretta). The achievement roster alone is worse: base-game
only, 0 of 29 rows DLC, so it would have called Messmer and Consort Radahn minor bosses.

Closes #734.

### A sweep trigger now has to correspond to a kill

Nothing checked that a sweep trigger flag meant a *kill*. #697 — a sweep that fired with no boss
fight anywhere near it — was found by a human reading two kinds of log line side by side. That
comparison is a gate now: `sweep_watch.rs` logs the flag, `boss_fight_probe.rs` logs the npc_param,
both to the same timeline, and `tools/check_sweep_kill_correlation.py` finally looks at both.

The join had to be invented — there is no flag→npc table — so it takes two hops through committed
params and yields a **candidate set** rather than an id. That makes it lenient by construction: it
can miss a defect, it cannot invent one. Window is 300s back / 60s forward, generous on purpose,
because `sweep_watch.rs`'s own motivating case is a legitimate 2m45s gap and a tight window would cry
wolf on the case that module exists to explain. One kill cleans one sweep, by maximum matching rather
than a greedy grab.

Offline and forensic: it runs over logs already uploaded, not as a live client warning.

Closes #713.

## v0.4.4 — 2026-08-16

Window opened one commit past the v0.4.3 tag at `c891d04`, which is where `check_release_notes`
went red -- on PR #718 (`tools/`-only, no player-visible change and so no rule-14 entry of its own).
That is worth writing down plainly, because v0.4.3's row claimed a first: it was opened AT the tag
with zero commits past it, while every gate was still green. This one is not that. It is the
ordinary case the gate exists for -- the red arrived on the very next commit, exactly as v0.4.3's
own note predicted it would, and the cost was one PR's CI rather than a shipped section quietly
accumulating notes that were never in the release.

`CONTRACT_HASH` is unmoved at `5c2b9bf2` -- the shape the contract has had since 0.3.9 -- so this is
version-lockstep and a v0.4.3 client still handshakes with a v0.4.4 seed. Verified by loading
`contract.py` and reading the value, not by assuming the shape did not move.

Entries arrive below as they merge (rule 14: the release notes are part of the change, not part of
the release).

### Altus opens at the lift, not inside two unrelated side entrances

With `region_grace_unlock: entrance`, receiving the Altus Lock lit **Old Altus Tunnel** as the
region-open flag and **Abandoned Coffin** as the entrance bundle. Bobler's playtest saw both. The
two derivations independently chose their lowest numeric candidate, and neither candidate is the
way into Altus from the Grand Lift.

Both now resolve to **Altus Plateau** (`76301`), the lift-side grace. The same ruling is carried
through the landmarks tier so the three grace tiers remain nested: moving from landmarks to
entrance removes warp points and never swaps one for a different one.

Refs #641.
### Four pairs of trousers are no longer major bosses

`MajorBoss` is one of the classes the default progression surface confines this world's own
progression to — region Locks, required runes, legacy keys. It read **52 checks. The entity count is
43.**

The roster is keyed on each boss's acquisition flag, which is right. But a flag resolves to a
*family* of checks — the primary drop plus every sibling lot the same flag drives, each minted as its
own co-check — and the whole family was inheriting the tag. For two DLC field bosses that family is
an armour set:

```
530810  Dancer of Ranah    Dancing Blade  + Hood / Dress / Bracer / Trousers
530820  Blackgaol Knight   Greatsword     + Helm / Armor / Gauntlets / Greaves
510260  Magma Wyrm Makar   Scalesword     + the Dragon Heart
```

Nine checks, three bosses, and Dancer of Ranah's Trousers sat on the default progression surface as a
major-boss check. It is one check per boss again: the default surface's hosting count goes 179 → 170,
and the nine it loses were never a boss's *death*, only the rest of its loot.

🛑 **The half that is NOT reversed.** When co-checks landed (#191, 2026-08-13) the ruling was "a
co-check is the same physical acquisition as its primary and inherits its tags", and for `Boss` and
`Legendary` that is exactly right — those answer *how was this check acquired*, and Dancer of Ranah's
Trousers is a boss drop, plainly. `MajorBoss` answers *is this boss on the roster*, which is a claim
about an **entity**, and there ten sibling lots are ten votes for one boss. So the family keeps
inheriting the acquisition tag — `Boss` is unmoved at 266, deliberately, by its own closure — and
stops inheriting the roster tag. That distinction is the whole change.

Gated two ways so it cannot come back quietly: at regen a roster entry must resolve to exactly one
primary check, never zero and never two; host-side an oracle names the offending bosses instead of
reporting a count.

This is **direction 1 of #737 only.** The roster still carries entries matt's list would not (Agheel,
Godefroy) and still misses ten it has — Margit, Red Wolf, Royal Knight Loretta, Godskin Duo, Godskin
Noble, Commander Niall, Mimic Tear, Valiant Gargoyles, Elemer, Dragonkin Soldier of Nokstella.
Re-deriving membership from the game's own achievement bosses is direction 2 and lands separately.
### The wizard's yaml stops being empty

Take the wizard's advice, change nothing, hit Download, and the file you got was:

    Elden Ring: {}   # all options at their defaults

That generates a perfectly correct seed. It is also the only documentation most players ever read,
and it says nothing — after eleven steps explaining 58 options, the artifact handed over mentioned
none of them. `buildYaml` wrote the DEVIATIONS only, so the more the wizard's defaults were worth
trusting, the emptier its output got.

Every option is now written out, defaults included, in the metadata's own field order and with its
display name beside it. The `(default: …)` comment is now the **change marker**: it appears only
where you moved something, so the diff from stock is still readable at a glance.

Two things this buys beyond legibility:

- **A default is not a promise.** `minimum_enemy_difficulty` moved 0 → 25 → 0 inside a single day
  (2026-08-05). Anyone holding a `{}` yaml across a change like that silently rolls a different seed
  from the one they configured. Written-out values pin what was chosen.
- **"Post your yaml" now answers something.** It answered nothing when the yaml was `{}`.

🛑 **The landmine, recorded because it is the interesting half.** `cross_game_progression` and
`maximum_enemy_difficulty` are NamedRanges whose *default* sits outside their own declared `0..100`:
`-1`, reachable only as the name `auto`. While the wizard emitted deviations only, a default was
never written down, so its illegal spelling was never written down either. Writing every option down
puts both into every file, `Range.from_any(-1)` raises, and a cosmetic change becomes a yaml that
does not generate at all. Out-of-range values are now emitted as their special name; in-range ones
stay numbers (`confine_foreign_progression: 100`, not `all` — the number is the legible spelling).

Two new assertions in `test_gf_wizard_yaml_generates.py`, because generation could not have caught
either direction: `{}` is the most generatable yaml there is, and a needless special name generates
fine and is merely less readable. Both were confirmed red against the code they gate.

Fixes #732.

### The major-boss roster is the game's, not ours

Red Wolf of Radagon was not a major boss. Neither were Godskin Noble, Godskin Duo, the Valiant
Gargoyles, Mimic Tear, the Dragonkin Soldier of Nokstella, Royal Knight Loretta, Elemer of the Briar,
Commander Niall or the Ancestor Spirit — so a region Lock could never be placed on any of them, and
the default progression surface was that much smaller and that much stranger.

`MajorBoss` was a **hand-curated list**, and matt's roster showed it wrong in both directions. His UI
describes his set as "Major bosses — 30 checks, **including all achievement bosses**", and that
phrase turned out to be the whole derivation: we do not need his list, because the game ships its
own. `common.emevd` registers one trophy event and every achievement is a call site of it —

```
$Event(9300, Restart, function(achievementId, eventFlagId, timeSeconds) { … AwardAchievement(…) });
$InitializeEvent(26, 9300, 26, 14000850, 0);      // achievement 26 = Red Wolf of Radagon's defeat flag
```

— so "is this a major boss" stopped being an opinion and became a join. 32 call sites, **29 of them
on a boss defeat flag**, and the hop from a defeat flag to the check that death grants is a table we
already had.

**MajorBoss 43 → 51.** Twelve bosses gained a major-boss check; four hand anchors were deleted
because the derived roster covers their regions. Default-surface hosting goes 170 → 179, and the
roster is *better evidenced* than the list it replaced: the share of MajorBoss checks whose region we
are confident about rises 91% → 94%.

**All 29 achievement bosses resolve — including Margit**, and how he got there is the most useful
thing in this entry. He was first written off: *"no boss-drop row exists in our data; his only item
is the Roundtable's Margit's Shackle, which is not a death reward."* Researched, plausible, wrong.
His drop is the **Stormveil Talisman Pouch**, and the game says so plainly —

```
m10_00   // マルギット撃破 -- Defeat Margit
         HandleBossDefeatAndDisplayBanner(10000850, GreatEnemyFelled);
         SetEventFlagID(9100, ON);
common   $InitializeEvent(0, 1100, 9100, 10000, 0, 60510);   →  lot 10000 = Talisman Pouch
```

— a check sitting in the location table the whole time carrying **no tags at all**. What hid it: our
reward datamine discarded the row as *"reward flag flipped by 2 maps"*, because Morgott's defeat
event also sets flag 9100 — behind `if (!EventFlag(9100))`, since Margit and Morgott are the same
character and killing Morgott implies Margit. **A guarded back-fill is not an ownership claim.** The
tool now distinguishes the two; the "never guess which boss a shared reward belongs to" rule is
untouched, and the two genuinely-shared reward flags in that table are still refused.

That one fix cascaded pleasingly. Margit's check re-homes to Limgrave (Stormhill is where you
*stand* to fight him), which made the Agheel anchor redundant, and the redundancy gate deleted it.
**Agheel and Godefroy are the two entries matt's roster explicitly does not count, and both are now
gone for reasons that had nothing to do with matt.** The check also sheds a wrong *"also granted by
Godrick the Grafted"* attribution it had picked up from the same missing join, and `Boss` /
`LegacyBoss` each gain it (267 / 53) — a check that always existed in the game finally carrying the
tags it deserved.

⭐ **The hand list had been rediscovering the trophy table by accident.** Three of the seven deleted
entries — Leonine Misbegotten, Magma Wyrm Makar, Mohg the Omen — are the *same checks* the
achievement roster derives. They were added by hand, one at a time, for regions that looked bare.
`MAJOR_BOSS_EXTRAS` is down to three entries, and a new hard error fails the build if a fourth ever
becomes redundant.

🛑 **The no-check ledger is empty, and asserted empty.** It held Margit for about an hour, and the
lesson is about ledgers rather than about Margit: a waiver is the one place a wrong belief can sit
and look like diligence, because it converts "our derivation is missing something" into a documented
fact about the game that nothing downstream ever questions again.

### There are seven Great Runes

`GREAT_RUNES` was `endswith("Great Rune")` over the item catalog, in four separate copies, and the
Great Rune of the Unborn does not end in "Great Rune". So Rennala's rune was a rune everywhere the
game says it is one and nowhere our code said so: it could not satisfy `great_runes_required`, could
not arm the capital gate, could not be minted to repair a short seed. Seven now, in one place, with
the Unborn rune a full citizen of all three.

### The Academy Glintstone Key stops being a second lock

bobler received the Raya Lucaria Academy Lock and the client told him *"walk in, the Academy
Glintstone Key opens it (no grace warp)"*. A Lock that lights nothing reads as broken, and the key
was buying a wall the region Lock already is. The key gate is gone: **the Academy Lock alone grants
the region's full grace bundle**, like every ungated region's does.

The Academy Glintstone Key is now ordinary loot — it is not progression, nothing in logic requires
it, and fill may place it anywhere. Rennala's Great Rune of the Unborn was gated behind it too and is
now reachable on the Lock alone.

🛑 Raya Lucaria stays a contained child structurally — it keeps its synthetic open flag, so setting
it disarms the kick without lighting a warp target. It is a gated child with **no wall**, a state the
code supported and had never been in.

### Two of the ten default surface classes admitted nothing, and a third could not be spelled

`Remembrance` (25) and `GreatRune` (7) are both strict subsets of `MajorBoss`, so shipping all three
in the default progression surface contributed exactly zero locations. They stay selectable and leave
the default.

`MinorDungeonBoss` is new, and it closes a gap that was not expressible before: **96 of the 267
`Boss` checks carried no sub-class at all** — catacomb, cave, tunnel, gaol and Divine Tower drops a
player could only reach by ticking `Boss`, which drags every field and legacy boss in with it.
*"Exclude the catacombs"* is now a thing you can say.

And the wizard draws the surface as the lattice it is. The classes contain one another; the page drew
them as a flat row of equals, so *"Remembrances"* and *"Major bosses"* looked like two independent
choices. The containment was already computed — it was just small text beside a checkbox.

### The rune numbers were wrong in three different places

- `KeepLocalRuneCap`'s help text — what you read in the options UI and in your own yaml — carried
  **four** wrong claims at once, including a default that was off by a factor of two and a ladder off
  by one rung from `[4]` up. None of them could fail, because prose does not run.
- `RUNE_VALUE` was headed *"KNOWN constants (no source file)"* while the source file sat two
  directories up, and **7 of its 22 rows disagreed with the params** — Hero's Rune [1]-[5] were listed
  at 2,500-7,500 against a real 15,000-35,000. Derived from the params now, 31 values, no hand list.
- `rune_shop_pricing` is frozen OFF at 0. The roll never ran; a rune shop slot keeps the price of the
  ware it used to sell.

### Foreign exports thin instead of vanishing, and the default moved

`filler_foreign_pct` has always been a percentage. What changed is how it is SPENT: a **copy budget
within each category**, rather than a sample over names. A name sample could miss a whole category by
chance, so lowering the lever silently stopped exporting some kinds of thing; the budget never takes
a category's last item, so lowering it now thins what you export instead. Barring a category outright
is `keep_local`'s job and should stay the only way to do it.

🛑 **The default moved 100 → 70, so this option now ships NON-DEFAULT.** 100 is still the no-op
sentinel `_select` short-circuits on; it is just no longer what you get. 70 is the measured 1:1
useful:filler mix in what your partner actually receives — Hollow Knight over 5 seeds: `100 → 0.79:1`,
`70 → 1.00:1`; Bumper Stickers over 3: `100 → 0.77:1`, `70 → 0.97:1`.

⚠️ **That number assumes the shipped `keep_local`.** The two levers compose hard: against
`keep_local: []` the same sweep put 1:1 at pct **6-12**, an order of magnitude away. If you empty or
extend `keep_local`, re-measure rather than reason about it.

### Merchant checks that were never really on the surface

- `_roundtable_merchant_aps()` filtered hub rows on a `ShopSlot` tag the hub does not carry, so it
  barred the **empty set** — Enia's 99 checks and the Twin Maidens' 25 were on the progression
  surface the whole time.
- Release-gated merchant checks were counted as hostable by the surface while the item rules forbade
  them. Thanks to **@emre155** for that one.

### Dryleaf Dane goes missable

He is questline-gated and fightable at more than one site — the boss table carries him twice, and both
of his sweep triggers are among the ones with no arena region, which is the same fact from the other
side. His checks stay in the pool and stop being allowed to host required progression.

While tagging him: three Enir Ilim pickups carry the identical descriptor *"also granted by Dryleaf
Dane"* and only the middle one had ever been tagged.

## v0.4.3 — 2026-08-15

### Your partners stop receiving 400 Golden Runes, and start receiving gear

Two locality options now ship non-empty: `keep_local` holds the consumables, crafting materials,
smithing stones, cookbooks and bell bearings in your own world, and `keep_local_rune_cap` is 12,500
(Golden Rune [13]) instead of 0.

The measurement behind it, on one Elden Ring slot beside Hollow Knight over four seeds: **two thirds
of everything we sent was mechanically inert in their game.** Smithing stones and runes alone were
47.7% of a 654-item export, to a player who cannot spend either. Those items were not a bonus on top
of the gear -- the export budget is slot-limited, so every Golden Rune we sent was occupying a slot a
weapon would otherwise have taken.

What actually changed: exported **useful items are flat, 228 to 231.** Exported filler falls **412 to
320**. Your partners lose 92 Golden Runes, not 92 things they wanted. The useful:filler mix goes
0.55:1 to 0.72:1.

🛑 **`key_items` is deliberately NOT held**, and that is the interesting part. It reads like the most
obvious thing on the list -- nobody in Hollow Knight can spend a Stonesword Key, and the category is
32.3% of everything we export -- but it also carries the Great Runes, both Dectus medallions and every
Remembrance. Holding it took `natural_progression`'s cross-world placements from 12 to **zero** in the
multiworld smoke. Those are the items a multiworld exists to trade, so the junk rides along with them.

That is also why the mix stops at 0.72:1 rather than the 1:1 it was aimed at, and why raising the rune
cap further does almost nothing (80,000 -- every rune kept home -- buys 0.01 more). Getting to 1:1
needs `key_items` split the way `cookbooks` was peeled off it, which is its own change.

If you preferred the old behaviour, `keep_local: []` and `keep_local_rune_cap: 0` restore it exactly.

### Twenty-two more boss sweeps can now be screened for reachability

A sweep is only sent to a seed that can actually reach the boss that fires it (#445). That screen
needs to know where the boss is fought, and for 48 of 218 triggers nobody did -- so they shipped
unscreened, on the permissive side. Twenty-two of those are settled here from evidence that was already
in the repo: where the boss's ARENA sits in a map whose own region is first-hand (a grace join), the
map answers the question.

All twenty-two agree with the region their checks are in, so no seed changes -- what changes is that
twenty-two groups can now be screened instead of assumed. The last two came from Alaric directly
(Ancestor Spirit and Regal Ancestor Spirit, both Siofra River), which is what a ruling is for when no
table has the answer.

Twenty-six remain and are deliberately left alone: their arenas are overworld tiles, and a tile's
region comes from the same nearest-neighbour guess that regions the checks, so "deriving" them would
make the screen agree with itself and inflate a coverage number that is supposed to be able to fail.

Window opened AT THE TAG of v0.4.2 at `33c85f7`, with zero commits past it, so this section starts
empty of changes on purpose and fills as they arrive (rule 14). `CONTRACT_HASH` is unmoved at
`5c2b9bf2` -- the same shape the contract has had since 0.3.9 -- so the bump is version-lockstep and
a v0.4.2 client still handshakes with a v0.4.3 seed.

**This is the first window opened while every gate was still GREEN.** Every previous one was opened
either by a red `check_release_notes` or minutes after a tag had already reddened it: v0.4.0 and
v0.4.2 both say so in their own ledger rows. `check_release_notes` passes at this commit's parent
because `HEAD is at the tag -- nothing has landed since`; it would have gone red on the first commit
past it, and that commit is now this one instead of somebody's feature PR.

Two things that could not be owed this time, and both are recent fixes doing their job:

- The `SHIPPED` fixture is DERIVED from `git tag` since #651, so v0.4.2's row cannot be owed and
  cannot be hidden behind rule 14's abort. That masking was recorded twice (v0.3.12 and v0.4.2) and
  this is the first window where the mechanism that caused it is gone rather than paid.
- The gitlink rides in this branch rather than after it. #648 merged without it and reddened main on
  the cross-side gate, which #650 then had to repair.

Still outstanding at the open, neither of them this window's work:

- `er-release` has now failed at `Fetch the AP icon override` on both v0.4.1 and v0.4.2. `ICON_REPO`
  and `ICON_REPO_TOKEN` are unset -- the repo has zero Actions variables -- so Assemble and Attach
  are skipped every tag, and `pack_release.py` has still never run in CI. The 124 MB player bundle
  on all three v0.4.x releases was uploaded by hand.
- `stable` in `CHANNELS.tsv` still points at v0.4.1, so `deploy_wizard.sh --landing` is serving
  v0.4.1's wizard. Promotion is a separate row and a separate decision.

### SweepSlot now scales with how many people you are playing with

In a two-game multiworld your partner's progression has almost nowhere to go but their own world.
Measured on a 1xER + 1xHK seed: **9.6%** of what reached Hollow Knight was useful, and useful items
left our world at **1.4%** against filler's **10.8%** -- suppressed nearly 8x, from a pool that is
about 40% useful. The cause is not curation, it is surface: one SweepSlot check per boss sweep is
not enough room, so the partner's items saturate their own locations before the fill reaches ours.

SweepSlot now nominates several members per sweep when you have few partners, and exactly one when
you have many. At a single partner that takes useful items reaching them from 9.6% to **34.3%**, and
takes the share of their progression our world can absorb from 87 items to 175.

**Curation is unchanged.** Every foreign progression item that lands here is still on a curated
check -- on-surface stayed at 100% across the whole measured range, and the filler rate stayed flat
while useful rose, so this is the useful tier being unblocked rather than simply more traffic. It is
also why `confine_foreign_progression` stays at 100: lowering it to 50 buys the same recovery and
spends three quarters of the curation to do it.

**Seeds with many players are unchanged**, by construction rather than by measurement -- at eight or
more partners the count is exactly the one this always used, and so is the selection. Solo seeds are
untouched for the same reason.

The wizard's SweepSlot count is now a RANGE, because how many checks the class contributes depends
on a partner count that does not exist yet when you are filling in your yaml -- the same reason
`num_regions` is shown as a draw size rather than a final number.
### Your Region Locks can finally reach a non-Elden-Ring player, and by default half of them do

`progression_bias` has released Locks into the multiworld pool since 0.4.0, and in a multi-slot
Elden Ring seed they travel: about 45% leave their own world. Beside a DIFFERENT game they did not
travel at all. Not rarely -- **not once**. Four configurations were measured against a Hollow Knight
slot and every one returned 0 Locks placed in it, including a two-Elden-Ring-plus-Hollow-Knight seed
where 15 of 28 Locks travelled and all 15 went to the other Elden Ring world.

The cause was structural rather than a bug in the fill. The pass that places released Locks only ever
saw Elden Ring worlds, so a Lock reached a partner solely by being one the pass could not place --
the spill -- and there is no spill: our surfaces host roughly 170 checks against at most ~36 Locks.
Four times the room the pass needs means it always finds room, and the only route out of Elden Ring
was a valve that structurally never opened.

The new `cross_game_progression` offers a share of the released Locks at partner locations FIRST,
before the Elden Ring surfaces get their look. It defaults to `auto`, which is `1 / number of games`
-- half in a two-game seed, a quarter in a four-game one, and nothing at all in a seed that is all
Elden Ring however many slots it has. On the measured 1xER + 1xHK pair that moves Locks landing in
Hollow Knight from 0% to **50.0%**. Set it to a number for that percent, or to `never` for the old
behaviour exactly.

Two things worth knowing before you turn it up. It places items in another game's locations, which
is a thing an apworld may legitimately object to during `pre_fill` -- only empty, unlocked,
non-excluded locations are ever offered, nothing is forced, and a partner that raises makes the
Locks fall back to Elden Ring surfaces rather than failing your seed, but `never` is the escape
hatch if a partner game generates badly beside us. And a travelling Lock is a Lock somebody else is
holding: this is the same trade `progression_bias` already asks you to make, now actually available
across games.

### `start_region_pool` with fewer regions than `start_regions` now says so, in your yaml's words

Naming one region in `start_region_pool` while asking for two `start_regions` used to end the
generation in a Python traceback rather than an option error -- and the message inside it told you
to raise `num_regions`, which cannot help. `start_region_pool` narrows the pool BEFORE the starting
regions are drawn, so a bigger seed only adds regions the option removes again; bobler tried it at
`num_regions: 9` and got the identical crash.

You now get a refusal that names both options, both numbers and the regions you listed, and tells
you the two things that actually work: name more regions, or ask for fewer. The old error survives
as a backstop for the cases this check cannot see, minus the advice that was a dead end.

### The Roundtable, Fringefolk Hero's Grave and the Chapel intro were shipping VANILLA enemies

Completion scaling took its geometry from the KICK table. Three play_region buckets are deliberately
exempt from the kick -- 11100 (Roundtable Hold), 18000 (the Stranded Graveyard cliff and Fringefolk
Hero's Grave) and 10010 (the Chapel of Anticipation intro) -- because the hub is home and because
ejecting a player from the intro crashed the game. Scaling imported that same table, so none of the
three ever reached `regionSphereTargetRanges`, and the client's fallback for a bucket it was never
told about is the FLOOR tier. With `completion_scaling_floor` frozen at 0, "floor tier" means vanilla
HP and vanilla damage.

Measured in bobler's 0.3.12 log, on a seed whose every wired region sat at tier 0: the same
`npc_id 4910` read 7,141 HP in bucket 18000 against 3,386 HP in a wired region. That ratio, 2.109x,
is `SCALING_HP_LADDER[6] / SCALING_HP_LADDER[0]` exactly -- the unwired ground was not merely
mis-tuned, it was the untouched game. One boss in that bucket read 31,518 HP while the largest boss
in any wired region read 6,564. And bobler on the hub, the same day: "this npc fight was almost
harder than every boss in the run bc roundtable was unscaled." The boss probe could not have caught
that one -- `BOSS_HEALTHBARS` has no 11100 row, because Ensha is an NPC invader and carries no
healthbar, so the hub's absence from the 39-fight table was never evidence that nothing fights there.

All three are now on the wire, PINNED at target 0 -- the floor of whatever ramp the seed rolls -- and
not at their host region's tier. That distinction is the fix, not a detail: 18000 rides Limgrave and
10010 rides Stormveil in the region grouping, the order is a linearization of the seed's own lock
chain with a seed-deterministic tie-break, and 11100 is in no rolled region at all. Limgrave sat at
target 0 in bobler's seed by coincidence. Ground you reach in the first five minutes and walk back
through all game must never outpace the player, in every seed rather than the lucky ones. Emitting 0
cannot disturb the curve: it is the minimum of the target space, the ramp already starts there, and
the client normalizes by the MAXIMUM emitted target, which appending zeroes cannot move. Both are
asserted, not assumed.

The generator bakes the one region grouping into three tables -- `REGION_PLAY_IDS` (kick geometry,
byte-identical; the intro and the hub are still kick-exempt), `SCALING_PLAY_IDS` (buckets that take
their region's ramp position) and `SCALING_FLOOR_PLAY_IDS` (the pins) -- and asserts that the last
two together cover every measured bucket. Nothing is scaling-exempt any more, so the next kick
exemption cannot become a silent difficulty exemption.

⚠️ **A pin is necessary, not sufficient, and the hub is the case where that matters (#346).** The
client cannot scale an enemy DOWN unless it can place it: a carried ladder rung, a `native_tier` off
the npc's rune reward, or a baked `AREA_TIERS` entry for the bucket. `greenfield/area_tiers.tsv`
records bucket 11100 as `sample=0, parts=29, unrunged=29` -- zero of the 29 enemy Parts vanilla put
in Roundtable Hold carry a rung -- so the bucket makes no area claim and is absent from the client's
`AREA_TIERS`. Being on the wire is what gets the hub swept at all; whether Ensha himself moves
depends on whether his `NpcParam` row carries a rune reward, which needs the m11_10 MSB to resolve
and is not answerable from this repo. Bucket 18000 has no such doubt: tier 5, 25 of 44 parts runged.

### A `great_runes` seed requires SPECIFIC runes, and every document now says so

`goal_great_runes: 4` never meant "any four Great Runes". The seed resolves four particular ones and
only those complete the goal, and the shipped yaml said "collect `goal_great_runes` Great Runes",
which reads as any four. A player finished a v0.4.0 seed holding four Great Runes, got no victory,
and worked out why by reading his spoiler log. The comment above that line had already been written
to head off the *lesser* misreading -- that killing a rune's boss counts -- while leaving the one
that ends runs.

Nothing about the goal changes. What changes is that four player-facing surfaces now say the same
true thing and point at the same answer: the shipping `release/EldenRing.yaml`, the player guide,
the README and `release/KNOWN-ISSUES.md`. The wizard's own description of `ending_condition` and
`goal_great_runes` says it too, because those come from the option docstrings, which are also fixed.

**Where to read WHICH runes your seed wants.** Your client already prints them the moment you
connect:

    goal: N item(s) must be HELD, not merely their boss killed: <the rune names>

That line IS the requirement -- it is printed from the same list the goal is checked against -- so
the spoiler log is no longer the only route. Do not infer the set from a pattern: today it is the
alphabetically first N of the Great Runes your kept regions can reach, which looks like a rule and
is not one to bet a run on.

**Still not fixed:** the names are not shown anywhere IN GAME. The connect banner is the obvious
place for them and that is a client change, tracked on #656; this release is the world's half.
### Nineteen Roundtable checks were in logic from turn one, behind NPCs you might never reach

Cokeman5 read it out of his own spoiler log on 2026-08-15: `Roundtable Hold :: Furlcalling Finger
Remedy - from Patches or Thiollier [f110030]` held a **Scadu Altus Lock**, placed as though his
friend could take it on the first move -- and his friend held none of the regions Patches or
Thiollier stand in.

The cause is one table doing two jobs. `merchant_shops.tsv` records which physical merchant opens
each shop row; when a row's merchants resolve to SEVERAL regions the generator refuses to pin it and
files the check under Roundtable Hold. That is the right answer to "what do we call this check?" and
#557 documented it as intended. It is not an answer to "when is this check in logic?", and nothing
was asking that question separately -- Roundtable Hold is the hub, the hub is always kept, so the
collapse quietly said "reachable at spawn". Patches is reachable from Limgrave, Mt. Gelmir or
Cerulean; "any of those three" became no requirement at all, which is weaker than the weakest of
them. Same shape as #688, where the kick exemption turned out to be a scaling exemption too.

`merchant_shops.tsv`'s own header already promised the fix -- *a row with >1 distinct map region ->
gen_data collapses to HUB + DEFAULTED* -- and only the first half of that sentence was ever
implemented. The second half is now written: a shop flag whose merchants span more than one region
is DEFAULTED, so it joins every other guessed region on the list that may hold filler and may never
hold anything the seed requires. The bar lands on the location's `item_rule`, which is what fill
obeys; the surface bar alone does not, and that distinction cost a fix once already (#350).

**Exactly 19 checks move**, and the set is derived rather than typed: the 16 Patches / Thiollier rows
plus the three Dragon Communion incantations (`f290500` Dragonfire, `f290750` Dragonclaw, `f290760`
Dragonmaw) that #557's count of 16 left out. Nothing else in Roundtable Hold changes -- Enia's 99,
the Twin Maiden Husks' 25 and the 31 Table of Lost Grace checks are genuinely in the hub and are
untouched. Because the rule reads the merchant table, the next merchant a regen splits across regions
is covered without anyone remembering to add it.

All 19 keep their ap ids, keep their `Roundtable Hold ::` region prefix and keep taking items. They
pick up the same `(region unconfirmed)` suffix every other guessed-region check already carries,
which is the honest label rather than a rename: we do not know which of the three regions the item
is really in. Deciding that -- option B in #701, regioning each row to its earliest site -- is a
separate change and is deliberately not in this one.

### ...and now they are filed where their seller stands, instead of nowhere

The entry above is #701 option C: the nineteen rows stopped being able to hold progression at all.
This is option B, the other half -- give the row a real region so it can hold progression again,
honestly this time.

The rule: a collapsed row is regioned to the EARLIEST of its OWN sites that your seed kept, in the
same spine order the rest of the world means by "earliest", and the check is then gated on reaching
that region. Patches / Thiollier resolve over {Limgrave, Mt. Gelmir, Cerulean}; the three Dragon
Communion incantations resolve over their own pair, {Caelid, Limgrave} -- they are not along for the
Patches ride, they get the same rule applied to their own altars.

**Requiring one site is STRICTER than the truth, which is why it is safe.** The honest rule is a
disjunction -- reachable if you hold ANY of the seller's regions -- and the region-lock world still
cannot express one (#320 / #502; that is #701 option 1 and it is not this change). Naming a single
kept site can only ever refuse a placement you could have reached, never assert one you could not,
and it is exact when your seed kept just one of them.

**If your seed keeps none of the sites, option C's bar stays exactly as it was.** That is the
fallback, not an edge case: a `num_regions` draw that holds none of Patches' three regions is a
legitimate seed and must still generate, so B narrows C's bar to precisely the case where C is still
true rather than removing it. Both halves are tested, in both directions and against real seeds.

**Which sites count, and one that does not.** A site is a map where a merchant instance is placed and
placed only there. Patches' `npc_param` 523090020 is ALSO placed on three overworld tiles -- Scenic
Isle in Liurnia, Seethewater in Mt. Gelmir, the Road of Iniquity in Altus -- and one npc_param is one
character the game shows in at most one place at a time, on a quest condition the generator does not
model. Counting those would have handed these rows **Altus, which every base seed keeps** (it is the
capital's only parent), so the bar would have lifted on essentially every seed on the weakest
evidence in the table. Dropping ambiguous placements leaves exactly the three regions #557's
hand-reviewed table names -- a derived rule landing on a reviewed list -- and leaves the Communion
pair alone.

Nothing static moved: same ap ids, same names, same `Roundtable Hold ::` prefix (renaming is what
#701 forbids), same `(region unconfirmed)` tail, same nineteen rows still taking items. The regioning
is a per-seed decision, so it lives on the location's access rule and on the same `item_rule` bar
option C used -- and one bar at a time: the two rows that are also shop-release-gated (the second Great
Arrow and Ballista Bolt, `f110200` and `f110210`, which the merchant does not stock until an unlock
fires) stay barred, because the region being open says nothing about the shelf.

### Multi-count spawn traps now spawn what they promise

`Trap: Basilisk x3` arrived as one basilisk. The count reached the client intact and the loop ran
three times -- but `spawn_debug_character` does not spawn anything: it writes a single SHARED slot
and raises one flag, so three requests in one tick overwrote each other and the engine acted on the
last. They are staggered one per tick now. The option's own docstring is the acceptance test --
"one is a joke; three is the Death Blight mist" -- and three is what arrives. (client#211)

### The spawn count reports what appeared, not what was asked for

The collapse above was found by a human standing in an arena counting basilisks, because the only
number the client had ever logged was its own request. The burst now counts the room BEFORE it
issues and reports the delta, so a trap that spawned nothing can no longer read as a clean
`3 standing` in a room that already had three. (client#214)

### Rune Thief no longer spends itself announcing a loss that did not happen

At zero runes the arithmetic was right -- halving nothing is nothing -- but the no-op write counted
as success, so the trap announced "half your runes are gone", was consumed, and the server will
never resend it. It defers now. Zero is not an edge case: one reporter sat at `runes: 0 held at
world edge` for eight consecutive epochs. (client#227)

### The pot cap says how much it ate, per row, at the world edge

An AP delivery that hit the game's own hold cap was reported delivered and then not placed, and
further caps on the same row were silent -- so the loss could be noticed but not measured. A per-row
tally now flushes at the world edge, in the same `{:#x}` id shape the existing cap warning uses, so
the two lines join on a grep. A quiet world edge logs nothing, which is what makes a line that does
appear worth reading. (client#213)

### Found hints stop counting, and stay in the list dimmed

The `found` flag has been on the wire for months and the client dropped it, so the tracker's
`Hints (N)` counted collected and live hints alike. Found hints now render dimmed and leave the
header count, so the number means "how much is still outstanding". They stay on the list, because a
found hint still records where something was. (client#226)

### A `great_runes` goal names its runes at connect, in the game

The apworld emitted the required names, the contract declared them, and the client already parsed
and logged them. Every half worked and a player still had to open the spoiler log, because
`log::info!` goes to a file we only read AFTER someone reports a problem. The same string is now
printed through the client message channel at connect -- the channel a player is actually looking
at. (client#222)

### A warning before an ending that will not count

Arriving at the goal arena with Region Locks outstanding now prints, once per arrival:
`N Region Lock(s) outstanding -- the ending will not count yet.` The count and not the region names,
because the count is the actionable number and the names are a hint a multiworld player may not have
paid for. Nothing is blocked -- the notice has no authority over anything, so it has no way to fail
closed. (client#224)

### "Connection refused" and "connection timed out" are different problems and now say so

Both shared one sentence, and the sentence advised checking the URL -- which that code path has
already ruled out, because by the time it runs the name resolved and the socket still never opened.
A refused SYN means nothing is listening (wrong port, paused room); a dropped one means something ate
it (firewall, AV, per-app VPN). They are named separately now. This cost one reporter four rounds of
triage on hypotheses the code could already exclude. (client#216)

### Connect-stage breadcrumbs are readable in a shipped build

"Did the TCP connect fail, or did it succeed and TLS fail?" was unanswerable from any log we ship:
the breadcrumbs were `debug!` and the file sink is pinned to `Info` with no toggle. They are `info!`
now -- deliberately NOT by adding a log-level switch, because raising the sink to `Debug` to reach
eight bounded lines also turns on the entire Archipelago wire stream in every log a player then
uploads. (client#219)

### The capital reconciler names every decline

Three different declines -- not armed, unresolvable, already correct -- all returned one silent
`None`, which is why 66 warps across two sessions produced not one intercept line, and why that
silence read as "the reconciler is inert". It was "already correct", all 66 times. Each decline is
named now, and inferring a burnt world requires corroboration. This does NOT close the underlying
issue; the upstream cause is untouched. (client#220)

## v0.4.2 — 2026-08-14

Window opened AT THE TAG of v0.4.1, with zero commits past it -- so this section starts empty of
changes on purpose and fills as they arrive (rule 14). `CONTRACT_HASH` is unmoved at `5c2b9bf2`, so
the bump is version-lockstep and a v0.4.1 client still handshakes with a v0.4.2 seed.

Two things went red at the tag and this window pays one of them:

- `check_release_notes` (rule 14) failed on every PR opened past the tag, because `APWORLD_VERSION`
  still named the version that had just shipped. That is this commit.
- `test_every_tagged_version_is_recorded_as_shipped` was owed v0.4.1's `SHIPPED` row and **never
  ran to say so** -- rule 14 aborts at step 9 of `generators` and steps 10-12 are skipped. That is
  the second time this exact masking has happened (v0.3.12 was the first), and it is now the ninth
  window where this row was written late. The row is paid here; the fix named at v0.3.10 -- derive
  the fixture from `git tag` instead of typing it -- is still not taken.

### Metyr is reachable again — the run rings the Finger Ruins bells, not the flag they derive

Metyr, Mother of Fingers sits behind Count Ymir's questline: you ring the bell at the Finger Ruins
of Rhia and again at the Finger Ruins of Dheo, and only then does the throne in the Cathedral of
Manus Metyr open. Those two ruins are in **different regions** — Rhia in Scadu Altus, Dheo in
Jagged Peak — so a seed that kept one and sealed the other could never open the throne, and Metyr's
Remembrance sat unreachable while the fill believed her region was open.

Since v0.2 the run papered over that by forcing `9440`, the flag the game DERIVES from the two
bells. That opens the throne and nothing else: Ymir reads the bell flags themselves, so he stayed on
his throne, his dialogue never exhausted, and the questline did not move. The run now sets the bell
flags and lets the game derive `9440` from them, which is what the rest of the questline is
watching.

The Dheo bell is set in every seed, because it is the one that crosses a region boundary. The Rhia
bell is set only when Scadu Altus is sealed — when it is kept, you ring that one yourself with the
Hole-Laden Necklace and its check stays yours to earn. One consequence worth knowing: in a seed that
keeps Jagged Peak, the Crimson Seed Talisman +1 at the Finger Ruins of Dheo now collects itself when
you first walk in, because the game awards it for a bell that is already rung.

Also recorded: the Hole-Laden Necklace's gate is measured rather than assumed. Both bell
interactions are disabled unless you are holding it — plain inventory possession, not an "obtained"
flag, so a client grant does trip it.

### Documentation: five player-facing claims that were false

All five were load-bearing -- each one sent a real player somewhere wrong this week.

- **The Academy's and the capital's graces do NOT light when their key item arrives.** Both guides
  and the yaml template said they did. The mechanism that would have done it (`runeGatedGraces` /
  `greatRuneItemIds`) was retired because its client half was never built, and the docs never
  followed. Both regions are gated children whose grace bundle is withheld while the wall is armed:
  you walk in the vanilla way and touch the graces yourself. Reported from Discord by a player
  holding the Leyndell Lock with nowhere to use it. (#657)
- **And there are THREE gated regions, not two.** The template said "two vanilla-flavored
  exceptions" and never mentioned the Sewer, whose graces are withheld *unconditionally* --
  `WALL_ARMED["Sewer"]` is `lambda world: True`, so no setting lights them in any seed. Found by
  #658, the first report through the new form, who hit it and Leyndell in the same save.
- **`leyndell_runes_required` is FLOORED at the vanilla 2, not "clamped down".** The clamp was the
  #589 bug; the text describing it outlived the fix.
- **`ending_condition: great_runes` needs a SPECIFIC set of runes, not any N.** The template
  promised a count. A player held four Great Runes, got no victory, and had to read the spoiler to
  work out why. (#656, #640)
- **`vanilla_pool` now appears where players read.** The guide, the README and KNOWN-ISSUES all
  still routed you to weighting `junk`, which #629 measured as half a job -- it leaves the presence
  floor standing. (#617, #618)
- **"Connection refused" has a troubleshooting ladder**, and it no longer names the two causes it
  is not. The old text blamed a wrong slot name and a wrong port, both of which produce a different
  error. (#613, and clients#181 for why the message itself is still ambiguous)

Also corrected: the post-burn route into the Royal Capital. The reconciler decides which capital
exists from where you **warp**, so "walk in from Altus" was wrong on its own -- you fast-travel
somewhere non-Ashen first, then walk in. The guide now also carries the known failure: the write
can lose a race with the map load, and the per-tick latch the log line promises as a fallback is
scoped to the capital buckets, so it cannot converge anywhere else. Warping again is a fresh
attempt. (clients#200)

### Three options retired: `local_item_only`, `exclude_local_item_only`, `progression_surface_mode`

All three are now `Options.Removed`, so a yaml naming one fails loudly with the replacement in the
error rather than generating something you did not ask for. **No contract change** -- none of the
three ever reached slot_data, and the client has no consumer for any of them, so a v0.4.1 client
still handshakes with a v0.4.2 seed.

- **`local_item_only` -> `keep_local: [everything]`.** Not a judgement call: the two are identical
  by construction, not merely in measurement. `local_item_only` localized
  `sorted(ITEM_CATALOG) + progressives`; `keep_local: [everything]` expands to every category in
  `CATEGORIES`, and `category_of` is TOTAL, so the two name sets are equal and both feed the same
  `local_items.value.update()`. One knob to learn instead of two, and the surviving one is the one
  that can also keep just your crafting mats.
- **`exclude_local_item_only`** dies with its parent -- it was only ever "everything MINUS these",
  and it was inert whenever `local_item_only` was off. Name what you keep, not what you release.
  This also drains the last `_TEMPLATE_DEBT` entry, so **every player-facing option is now in the
  shipped template** and the set is empty.
- **`progression_surface_mode`** had been frozen at `strict` since the v0.2 slim-down, so `off` and
  `soft` were unreachable from any yaml -- while four branches here and three in core still carried
  them. That gap is how #635 happened: a live docstring citing "when Progression Surface Mode is
  off", a state no seed could be in.

  🛑 **The off-branches were DELETED, not just the option.** Every read site used
  `getattr(..., None)` and treated absent as mode 0, so removing the option alone would have
  silently switched the progression surface OFF -- `apply()` and `audit_reachable()` skipped,
  `confine_foreign_progression` barring nothing, and an empty `progressionSurfaceLocations` shipped
  to a client that genuinely reads it, leaving the tracker starring nothing. A world-only edit with
  a client-visible regression. Strict is now written into core rather than selected.

Closes #512, #634, #635.

### `er_yaml_lint` was dead in two ways, and nothing ran it

It is now armed, and a CI step runs it over the shipped template, the presets and the playtest
fixtures. Two independent failures had to be fixed before that meant anything:

- **Rule 0 never ran.** `load_valid_keys()` looked for an `EROptions` class at two paths that
  stopped existing at the greenfield port, and `if VALID_KEYS:` turned the empty result into
  silence. That rule is the typo check, the stranded-option check AND the delivery mechanism for
  the whole `REMOVED` migration table. The key list now comes from the generated wizard metadata
  PLUS `defaults.FROZEN_OPTIONS` plus AP's common keys -- all three, because metadata alone reports
  every frozen option as unknown and a linter that cries wolf gets switched off.
- 🛑 **`lint_file` looked for a `EldenRing:` block -- the v0.1 game id, without the space.** Every
  yaml written since the v0.2 rename says `Elden Ring`, so the function found nothing and returned
  zero findings, which is indistinguishable from a clean file. Not just rule 0: **all fifteen rules
  had never run on any yaml anyone plays.** Found by injecting a retired key into a preset and
  watching the linter report OK.

What ran once it worked: **29 dead keys across 8 playtest fixtures**, three of them
(`pool_builder`, `pool_builder_juice_cap`, `completion_scaling_floor`) now `Options.Removed`, which
means those fixtures would RAISE at generation rather than be quietly ignored. All cleaned.

`--self-check` is new and runs first in CI, because a linter whose key list failed to load reports
zero errors on everything. It asserts the surface loaded, is plausibly sized, and includes the
frozen options.

**Two of the linter's own rules were quarantined as v0.1 rot** rather than guessed at: 17 of 21
`CHOICE` entries and 16 of 22 `DEFAULT` entries name options that no longer exist, so rules keyed on
them are now structurally unable to fire and `--self-check` prints the count. Two that were firing
on the SHIPPED TEMPLATE are deleted outright -- both claimed `num_regions` was conditional on an
`ending_condition: capital` and a `world_logic` that have not existed for two releases.

`presets/Alaric.yaml` moved to `docs/history/`: it declares `game: EldenRing`, which Archipelago
rejects outright, and nothing referenced it.

Closes #538.

### `open_boss_doors` -- walk into the catacombs and fight

New Quality-of-Life toggle, OFF by default. It opens the boss door in the **18** minor dungeons
whose door is a real lever puzzle, so you fight the boss instead of hunting the lever first.

Vanilla drives nearly all of them from one common event, `90005650`: pulling the lever sets a door
STATE flag and the portcullis rises. The option sets that flag at connect. Nothing is granted and no
check is skipped -- the door is only a prerequisite to REACHING the boss, and the boss and its whole
dungeon sweep still have to be earned.

**Four doors are deliberately left alone.** Sainted and Giant-Conquering Hero's Graves have no lever
at all: their doors open when you kill the Gladiator and the Shadow Troll, so forcing them would
skip a FIGHT. Gelmir and Auriza Hero's Graves have no lever puzzle either -- you walk up and open
the door.

🛑 **Applied at connect, and the door only moves at map load.** A dungeon you are already standing
in needs a reload before its door opens; the event is parked waiting on the lever and never re-reads
the state flag.

Two things checked before this was written, both of which could have made it a bad idea:

- **It spends nothing.** The #647/#662 hazard is a flag that doubles as a lot award, where forcing
  it hands over the item and burns its AP check. Ran that protocol over all 42 ids: every door flag
  occurs once or twice in the entire 589-file EMEVD corpus and only inside its own map's
  constructor, there are ZERO `AwardItemsIncludingClients` in any `m30_*` file, and zero hits in
  `flag_lots.tsv` (disjoint bands -- lots are `300X7xxx`, doors `300X0xxx`) or anywhere in
  `greenfield/` or the client.
- **It cannot strand a seed.** Because no door flag appears anywhere in `greenfield/`, the logic
  never modelled the lever -- fill has always assumed the boss was reachable once its region opened.
  Forcing the door CLOSES that latent gap rather than opening one.

Rides `startGraces`, on the tail, so no new contract key and no client change. A test pins that the
doors never reach the head of that list, which is the clobber sentinel and the fast-travel prime
target.

Closes #669.

### `open_boss_doors` also lights the ancestor altars

The Ancestor Spirit and the Regal Ancestor Spirit are reachable without riding around Siofra
lighting urns. Not doors; same promise, and the option would be lying by omission if it opened every
catacomb and left those two.

**Two flags, not sixteen.** Both altars are in `m12_02` (Siofra River Bank) -- the arena tiles
`m12_08`/`m12_09` hold only the fights and carry no ObjActs at all. Each altar is a counter over its
per-urn flags that sets one aggregate, and the WARP reads the aggregate directly, so `12020609`
(Ancestor) and `12020629` (Regal) are the whole feature.

🛑 **The individual urn flags are NOT set, and a test pins that.** The counter's own already-done
branch lights the altar from the aggregate at map load, so the sixteen are redundant -- and they are
a plausible future check family, which is exactly what a QoL toggle must not quietly pre-satisfy.

Same load-time rule as the doors: applied at connect, visible on entering the tile.

The award check came back clean, and the near-miss is worth recording: a plain grep of
`flag_lots.tsv` HITS on `12020600` and `12020620`, which looks exactly like the #647 shape. Those are
**column 3 -- lot ids, not flag ids** (`lot 12020600` belongs to flag `12027600`, Hefty Beast Bone).
Urn flags are `120206xx`; that tile's lot flags are `12027xxx`. Disjoint, same separation the
catacombs have between `300X0` and `300X7`.

The option's NAME is now doing some work -- an urn is not a door. #677 argues for widening it while
it is still a day old and off by default; that rename is deliberately not in this change.

Refs #677.

### A Bonny Gaol pickup was a live Limgrave check

Spotted by Alaric on his own tracker, on an `enable_dlc: false` seed:
`Limgrave :: Hefty Cracked Pot - near Bonny Gaol [f66930]`. Bonny Gaol is Shadow of the Erdtree.

Flag 66930's only lot is 41010000 -- m41_01, Bonny Gaol -- but the EMEVD provenance chain gave it an
m18 fallback, which resolved to "Stormveil (assoc.)" and from there to a live Limgrave check on the
progression surface. In a base-game seed it shipped pointing at ground the player cannot reach, so
the fill was free to put a Region Lock on it and make the seed unwinnable with no warning.

`gen_data._REGION_CONFIRMED_FLAGS` already carried this exact fix for m41_00 (Belurat Gaol) and
m41_02 (Lamenter's Gaol). **m41_01 was missed** because 66930 does not share their `X0SS7000` flag
shape -- it is a `669xx` common-event pot flag, and its four siblings all stayed safely unplaced, so
the family looked handled. It now goes to Scadu Altus beside every other m41_01 check.

**The repo already knew and had ledgered it.** `(66930, "Limgrave", "Scadu Altus")` was a pinned
tolerated mismatch in `test_gf_check_ground_regions`. Nothing connected "known attribution mismatch"
to "live check pointing into unreachable DLC ground", which is the actual lesson.

A new gate stops the class recurring: **no base-game region may hold a check whose nearest grace is
in a DLC map.** It fails before this fix naming exactly this row and passes after. The predicate is
a two-hop join over committed derived tables (`nearest_grace` -> `grace_flags`) rather than
arithmetic on a lot id -- slicing digits off a lot invents map names for any lot that is not eight
digits, and did so while this was being measured.

Closes #680.

### Great Runes were the wrong item — the capital gate never counted them

Two goods rows in Elden Ring share each Great Rune's name. `191` is Godrick's Great Rune, and so is
`8148`. The catalog we build from the game's own name tables is keyed by name, walks ids in
ascending order, and kept the first of each pair — so every seed since the item pool existed has
been handing out the row **the bosses do not drop**:

```
lot 10010     -> goods 8148   flag 171     <- what Godrick actually drops
lot 34100500  -> goods 191    flag 191     <- what the Divine Tower restore awards
```

Only `8148` carries `enable_ActiveBigRune`. So a player could hold two Great Runes, see them listed
and equippable in the blessing menu, have their "restored" flags set, and stand at the capital gate
watching it stay shut — which is exactly how this was found. Four separate things all looked right:
the menu accepts the row we gave (it is a valid rune item, just not the countable one), the client
sets its restore flag, and the `great_runes` ending matches on item NAMES, so victory could still
fire for runes that never opened a door.

The fix is a rule rather than a rune carve-out: **a check pays what its own lot awards.** The name
only chooses when the lot cannot. 🛑 A global "prefer the row some lot awards" tie-break was tried
first and cannot work — **both** rows are awarded by a real lot, so it has nothing to choose
between; measured across the 2330-entry catalog it moved one unrelated mapping and left all six
runes wrong.

**Fourteen items were pointing at the wrong row**, all the same shape — a name shared by two rows:

| | |
|---|---|
| the six shardbearer Great Runes | `191`–`196` → `8148`–`8153` |
| Cerulean / Ruptured Crystal Tear | `11004` → `11005`, `11016` → `11017` |
| Golden Vow | `6600` → `2003170` (its three locations are all DLC) |
| Unalloyed Gold Needle | `8196` → `8976` |
| Scorpion Stew / Gourmet Scorpion Stew | `2001200` → `2001202`, `2001201` → `2001203` |
| Letter from Volcano Manor | `8127` → `8132` |
| Lord of Blood's Favor | `8154` → `8155` |

⭐ `Great Rune of the Unborn` is the control: it has no duplicate-named row, so it always resolved
correctly, and a regression test now pins it there — if that one ever moves, the fix has become a
carve-out.

**What is NOT settled.** A player who restores a rune at a Divine Tower ends up holding `191` and
can still enter the capital in vanilla, so the gate cannot be counting only the `8148` band. This
change makes the run hand over what the boss hands over, which is right on its own terms; whether it
is *sufficient* to open that door is an in-game check still owed.

Closes #682.

### Hints name the boss that sweeps a check

A player's region Lock was hinted at `Mt. Gelmir :: Perfume Bottle - near Craftsman's Shack`, and the
reasonable next question was "so which boss do I kill?" Under `SweepSlot` the answer is that a boss
hands that check over — and the name, which is all an Archipelago hint has to work with, never said
so.

Sweep members now carry their trigger:

```
Mt. Gelmir :: Perfume Bottle - near Volcano Manor, also granted by Godskin Noble (m16_00) [f66700]
```

**"also granted by", never "kill".** The check is still an ordinary pickup and walking to it is
still a valid route, and 106 of 218 sweep triggers have no audited region, so the run cannot promise
the boss is reachable in your seed. The tile travels with the name because the names are not unique
— `Night's Cavalry` alone names eight different sweeps.

4000 of 5212 location names gained a clause. A member whose trigger cannot fire gets none.

Closes #670.

### Progression no longer lands on a sweep that cannot fire

`SweepSlot`'s promise is that progression only lands where a boss will hand it over. A player
restricted progression to boss sweeps, cleared **19 of 19 Limgrave bosses**, and finished with two
progression checks still open:

- `Limgrave :: Warming Stone - near Limgrave Tower Bridge` — swept by `34100800`, the Divine Tower
  of Limgrave, which **has no boss at all**. The repo's own data already listed that trigger under
  `unresolved_bosses` and nothing consumed the note.
- `Limgrave :: Mushroom - Murkwater Cave` — swept by **Patches**, who yields rather than dying, so
  his defeat flag is never reached in normal play.

Both now refuse to host progression, through a skip list shaped exactly like the one `ShopSlot`
already uses — keyed by what is excluded, valued by *why*, so an exclusion cannot outlive its
reason. The governing sentence was already written in a `SHOP_SLOT_SKIPS` entry: *a slot we cannot
ASSERT is reachable may not be REQUIRED.* One feature over: a member we cannot assert is swept may
not be required.

🛑 Patches is why this cannot be derived from the data. He **has** a name, so no join over the
shipped tables excludes him — the tracker even showed his check ticked, because that is the check
his *encounter* grants, not the sweep's defeat flag.

Nominations drop 218 → 212. The surface only shrinks, and the feasibility ladder widens rather than
failing to generate. **106 of 218 triggers still have no audited region** — that is a larger claim
than "cannot fire" and is tracked separately in #671.

Closes #672.

### Housekeeping

- The filler-economy floor gate was flaking. It asserted against **one arbitrary region draw** with
  no seed pinned, and flipped on an identical tree — green on a branch head, red on that branch's
  own merge, `git diff` between them empty. It now samples six fixed seeds. It was also comparing an
  integer item count against a float threshold, so a documented 50% floor silently demanded 51%: it
  failed a run that had delivered 26 stones of a required 26.239 and reported it as *"bought
  nothing"*. Floors to whole items now. Second recorded member of the draw-flake species. (#684)

## v0.4.1 — 2026-08-13

Window opened minutes after the v0.4.0 tag at `d9cdeafc`, and **not** on purpose: commits had
already landed past it. `CONTRACT_HASH` is unmoved at `5c2b9bf2` -- version-lockstep, so a v0.4.0
client still handshakes with a v0.4.1 seed.

### `no_weapon_requirements` is a setting again

Weapon, shield, catalyst and spell requirements have been zeroed in every seed anyone has ever
rolled. It was frozen ON in the v0.2 option slim, so no yaml could say otherwise -- "any gear the
multiworld hands you is usable" stopped being a choice and became the game. It is a yaml option
again.

**It is still on by default, so a seed you generate today is unchanged.** Set
`no_weapon_requirements: false` if you want your stats to decide what you can hold. Generation is
identical either way and nothing becomes unwinnable; it decides whether the greatsword that arrives
at level 12 is usable now or after you have built for it.

The default being 1 rather than the bare `Toggle` 0 is deliberate and is the whole risk in this
change. Unfreezing an option at its class default is exactly how `pool_builder_intensity` moved
every seed from the 1013-item juice catalog to the 536-item one inside a release whose changelog
said nothing about a default seed had changed. `test_gf_weapon_reqs` pins the freeze value as the
default so that cannot happen here quietly.

World-only: no client half, `CONTRACT_HASH` unmoved.

### `no_fall_damage` is off the yaml surface

It shipped in v0.4.0 and is frozen off one release later. The option surface is a budget and this
one did not earn a row.

Nothing about the client moves: `no_fall_damage.rs` still implements it, the slot_data key is still
emitted at 0, and the ContractKey stays declared -- freezing is not deleting. A yaml naming it is
ignored rather than rejected, and unfreezing it later is deleting one line. The freeze value matches
the option class default, so no seed moves in either direction.

### Spawn Traps is a text field in the builder

`spawn_traps` takes any of the 390 spawnable character-model ids, and the builder drew a checkbox
for every one of them, in numeric order, with no names on them. It is a text box now. Type or paste
the ids, separated by commas or spaces or anything else, in any order.

Ids it does not recognise are named back to you and **not** saved, so `9999` is refused in the
builder rather than failing generation after you have downloaded the yaml. The 390 accepted values
have not changed and neither has what gets written: the list is still sorted into the yaml, so the
file does not change shape depending on the order you typed.

The flag lives on the option class (`wizard_free_text`), so the next set-valued option whose keys
are a catalogue rather than a menu gets the same control by setting one attribute.
`tools/check_wizard_kind_controls.py` now fails if the page stops reading it -- a presentation flag
nothing honours is a silently reverted decision that leaves a working page behind it.

### Castle Watering Hole's 24 checks belong to Scadu Altus, not Shadow Keep

If your seed kept Scadu Altus but not Shadow Keep, you could walk to Castle Watering Hole — on a
grace your own region granted you — and pick up **vanilla items**. Twenty-four checks there were
filed under Shadow Keep, so they were not in your seed at all, and the game happily handed you the
real thing.

The cause was a judgement call the code had already flagged as one. A screen that finds graces whose
checks straddle two regions resolved this one to its majority side (20 Shadow Keep against 4 Scadu
Altus) and, in doing so, deliberately overrode the grace's own evidence — the only place that was
ever allowed. The note beside it said the call needed validating in game. It has been, and it was
wrong: all 24 are Scadu Altus.

Reversing it makes the straddle screen better on every measure rather than trading against it — 51
straddling graces down to 50, and the share of checks sitting on a minority side from 4.23% to
4.10%.

### New: `start_region_pool` — choose where the run opens

`start_region_pool: [Caelid]` and the run starts in Caelid. Name several and the opening region is
drawn from just those; leave it empty (the default) and nothing changes — the opening region is the
size-weighted draw it has always been.

This is boblerrr's ask, and it is a testing tool as much as a play option: `num_regions: 1` plus one
name is "just play Caelid", the same seed every time, which is what you want when you are checking
one region's checks rather than playing a run.

It composes with `start_regions` rather than duplicating it — that one says how MANY regions open,
this one says WHICH they may be. `start_regions: 2` with two names opens both.

🛑 **Every region you name is force-kept**, so this can make a seed larger than `num_regions` asked
for. That number is a draw size and force-keeps are additive — the same seam a named `goal` already
uses, and the generation log names the contribution. Naming three regions and asking for one is a
three-region seed, not a one-region seed with a choice.

Naming a region the seed cannot open in fails generation and says which and why, because the three
ways that happens are invisible to each other: your DLC toggles sealed it, your goal needs it (a run
that opens where it ends is over before it starts), or it is a child region reached through its
parent. Ignored under Natural Progression and Vanilla Placement, which mint no Region Locks — there
is no opening Lock to constrain.

### Changed default: your dungeon sweeps can now hand you progression

**This changes every seed.** The Progression Surface — the set of checks a key item may be placed on
— gains a new class, `SweepSlot`, and it is **on by default**. It nominates ONE member of every
dungeon sweep your seed runs as somewhere progression may go, so killing a sweep boss can now hand
you a region Lock, a required Great Rune, or another player's key item along with the area loot.
Remove `SweepSlot` from `progression_surface` in your yaml if you would rather it never did.

**Why.** The surface was tiny and nobody had measured what that cost. On a four-region seed it is
about **30 checks out of 1500**, and `confine_foreign_progression` — default 100 — lets another
player's progression land *only* there. Measured beside three partner games: a slot received **7 of
the 60** foreign key items it would have received with confinement off. The other 53 did not go
somewhere worse; they never arrived at all, and those checks were backfilled with the slot's own
items. Beside Hollow Knight it was 15 of 110.

One check per sweep roughly triples the surface and takes that intake to **18, 44 and 28** against
the same three partners, while `confine`'s promise stays exactly as strict — nothing foreign lands
off the surface. It also fixes a smaller thing nobody had reported: on a `num_regions: 1` seed with a
narrow surface the fill was already spilling the seed's OWN Locks off it, and the extra room takes
that spill to zero.

**What it costs.** A sweep can pay out progression, which it previously never did under a non-empty
surface. That was already true at `confine_foreign_progression: 0` or an empty surface — 63% of
foreign progression landed on sweep members there, exactly their share of the map — and it is not a
logic hazard, because a sweep member's access rule is its own region: the sweep only makes the check
*earlier*, never reachable only that way. It is a texture change, and it is deliberate.

Everything else about sweeps is unchanged. A sweep still never hands over another boss's reward, a
Remembrance, a Great Rune, a key item or a merchant's stock, and the per-seed cut still takes back
whichever collectathon lines you put on the surface. `SweepSlot` is the one class the cut does not
take back — taking it back would delete the check it just nominated.

### New: `vanilla_pool` — one switch for the vanilla item spread

`vanilla_pool: true` turns pool curation off. Your checks pay what they pay in vanilla Elden Ring:
the `curated_filler` recipe is overridden with "keep what the check already paid", and the
guaranteed set of physick tears and smithing bell bearings is no longer added to the pool. Off by
default; nothing about an existing seed changes.

**Why it is one option and not two.** Half of this was already possible -- an empty `curated_filler`
has returned a junk-only recipe for months -- and it was worse than not having it, because it looks
like it worked. `presence_floor` had no option at all and was not frozen: it was unconditional. So a
player who found the empty recipe, typed it, and went counting still got up to 18 crystal tears
vanilla never placed, from a feature no yaml could reach.

That is not hypothetical, it is the report this came from: a playtester counted 19 tears in his seed
against a catalog that is complete at 37/37 and reported items missing. Nineteen is the 18-item
floor roster plus the one his seed kept. The floor was working exactly as designed and made a
complete catalog look half-empty. One option now means one thing.

It **overrides** `curated_filler` rather than refusing to run alongside it, and says so in the
generation log. It has to: the recipe has a real default, so every yaml carries one whether or not
its author typed it, and rejecting the combination would reject the shipped template.

Worth knowing before you set it: you give up gear injection, the smithing-stone and rune economy,
and any guarantee that a physick tear or bell bearing exists at all in a seed that seals their home
regions. The curation is what was buying those. Items are still shuffled between checks — this
decides which items exist, not where they sit; `vanilla_placement` is the option for that. Also
retired-option housekeeping: `pool_builder: false` still raises, but its message now points at
`vanilla_pool` by name, since that is where someone typing it was trying to get to.

World-only: no client half, `CONTRACT_HASH` unmoved.

### Hosting is back, as one tab, with the defect that killed it fixed

peliarch.ca hosts rooms again, and generates seeds again from the builder's **Generate & host**
button. The site is six things now -- the builder, the downloads, the documentation, the check
browser, the bug report form and a room to play in -- and every page carries the same tab strip,
with the builder first because it is the only surface anyone can use before deciding whether to
install a DLL.

**Why it was gone for one release.** The rooms dashboard listed five hibernated rooms and offered
every one of them the same connect address, `ws://peliarch.ca:38400`, with a Copy button. Two of
them were both named `Player - Elden Ring`. Archipelago's `Connect` packet carries a slot name and
a password and **no room identifier**, so a client that reached whichever server actually held that
port -- with a slot name that seed happened to contain -- would join the wrong multiworld, and
neither side would say anything.

**What was actually wrong, which is not what the retirement note guessed.** That note blamed
Archipelago's random port allocator. peliarch does not use it: it passes `--port` explicitly, so a
*running* room's address was always truthful. The lie was in the room record -- the port was
allocated per **start** and never cleared on **stop**, so five sleeping rooms each remembered the
38400 they last held and the next one to wake took it for real.

**What makes it safe now**, both asserted in `webgui/test_ports.py`:

- A room is given **one port when it is created** and keeps it for as long as it exists, excluding
  every port already promised to another room. A stale address resolves to that room or to nothing;
  it can never resolve to somebody else's seed. Starting a room whose port something else is
  holding fails loudly instead of quietly moving it.
- **No address is published unless the room is `RUNNING`.** A port number is not an address, and a
  sleeping room now says "not listening" and shows its reserved port as a fact rather than as
  something to paste into a client.

The rooms already on the box all record 38400, so the store is de-duplicated on load -- first
claimant keeps the number, the rest are re-homed and the move is logged.

Two smaller things that were false and are now not: **"Sleeping -- connect to wake"** (nothing
listens on a stopped room's port, so connecting is refused; it says "press Start"), and the site's
advertised `wss://` (room ports are published straight through and never reach Caddy, so they speak
plaintext `ws://`; a copied `wss://` address earned `SSLError: WRONG_VERSION_NUMBER`).

🛑 archipelago.gg is still the right answer for a long game with people you do not share a Discord
with. This is one small box, and it has neither the uptime nor the room history.

### +286 checks: the co-check policy replaces a five-family allowlist

A "co-check" is a second check that fires off the same event flag as another — the sibling item a
single pickup grants. Five families were hand-verified and allowlisted; boblerrr regression-tested
them across two full runs, so the policy that selects them is now the one the datamine already used
everywhere else.

**286 sibling checks across 147 families, +5.7% locations.** The catalog goes 2084 -> 2190 and the
number of item names with at least one check goes 1750 -> 1990. That recovers twelve of the items
in bobler's missing list by itself, Maternal Staff, Beloved Stardust, Stargazer Heirloom, Crystal
Burst, Unseen Form and Scouring Black Flame among them.

It is a UNION with the old hand list, not a replacement: two flags hang their sibling on a goods
type the policy calls junk, and a pure derivation would have deleted both — one of them the check
the Scadutree fix below had just repaired.

Two latent defects fell out of doing it. A sibling of a check whose region was a GUESS was coming
back region-confirmed and progression-eligible, because the test asked about the sibling's own id
against a snapshot taken before that id existed — it could never match. And the vanilla bell-bearing
list was eight names on a false premise (Somberstone Miner Bell Bearing [1] is a looted item, on a
shared flag nothing had ever named), which let a vanilla copy stay pool-eligible under
`progressive_stone_bells`. Nine now, and the presence floor's roster is complete for the first time.

### Stacked checks pay the lot quantity: 41 names, 294 copies

926 locations grant more than one copy of their vanilla item and we were paying exactly one of each.
This mints the first slice: **41 stacked names over 127 locations, recovering 294 copies** — 39
smithing/somber stone names across 121 lots, plus Revered Spirit Ash and Scadutree Fragment.

A stack is an AP item ID, not a flag and not a lot: the stacked name is a second id pointing at the
same game item, carrying its count in slot_data. No acquisition flag is minted, no item lot is
touched, and the client already multiplies through — so the contract does not move and there is no
client half.

Ammunition, throwables and pots are deliberately NOT in this slice. `curated_filler` already stacks
those by CATEGORY through the same field, so two systems would answer "how many" for one item and
the winner would be whichever ran last. That wants a ruling first; stones are not in that table,
which is exactly why this slice is safe without one.

### Five checks were paying Rune filler because their item name resolved to nothing

Five rows named an item the game's own text tables cannot resolve. Each was a live check with a live
flag, so it kept its location, silently fell through to Rune filler, and dropped its item out of the
catalog entirely. No error, no count, no gate — which is how two of them reached a player counting
items in game.

```
Note: Walking Mausoleum       -> Note: Wandering Mausoleum
Note: The Preceptors Secrets  -> Note: The Preceptors Secret
Chain Gauntlets               -> Gauntlets
Ancestral Spirits Horne       -> Ancestral Spirits Horn
[Sorcery] Terra Magicus       -> [Sorcery] Terra Magica
```

⭐ **None of these was guessed, and the repo already knew.** Three are shop rows, and
`shop_rows.tsv` — derived from the game's own shop tables — has carried the correct name all along.
Two derived tables, one of them right, and nothing cross-checked them. Generation now collects every
name that fails to resolve, prints the flag and the name, and refuses to finish.

### +135 items a seed could never hand you, and `junk_gear` to put them in

An item lot with no acquisition flag is a random enemy drop: it fires on every kill, so there is no
one-shot event and it can never back a check. The catalog is check-derived, so an item whose only
source is a lot like that never entered it — and gear injection draws from the catalog, so it could
not arrive that way either. Unreachable twice over. Celebrant's Cleaver, Rib-Rake and Sickle are the
reported case.

The catalog goes **2195 -> 2325**, count-neutral: no check changes what it pays.

🛑 **Registering a name is necessary, not sufficient**, and the generator now says so out loud. Of
the 135, only 39 clear the gear-injection tier floor; **96 are rarity 0** — the game's own marker for
trivia — including all three Celebrant's weapons. Shipping the number alone would have read like a
fix while the motivating case stayed unreachable.

So they get somewhere to go instead: **`junk_gear`**, a new `curated_filler` category of the
equippables the game itself rates trivial. Weight it if you want the low end of the armoury in your
filler; it is the only path to the pieces whose only source is an unflagged drop. Zero by default,
so nothing changes unless you ask.

### Four Scadutree Fragment checks were paying half what the game gives you

The base game hands out **50** Scadutree Fragments across 46 pickups -- four of those pickups are
worth two. This world paid one at every single check, so a seed that let you find all 46 gave you
46 units, and the Scadutree blessing (which is a pure function of that number) topped out a rung
below vanilla no matter how thoroughly you swept the Realm of Shadow.

The number was in our own data the whole time: `flag_lots.tsv` has carried a `num` column since the
lot capture landed, and nothing had ever read it. It does now, for **every** item -- 921 locations
in the game grant more than one copy -- and a check whose lot grants two pays the stacked item where
one exists. Today that is `Scadutree Fragment x2`, which the DLC blessing feature already minted for
its own injection; everything else is unchanged, so no other item's pool count moves.

The most visible case was the Hippo's fragment in Scadu Altus. It was already split out as its own
check and still paid one, because the quantity lives on the lot slot and no amount of check-splitting
reads it.

### Dungeon sweeps pay out the good stuff now, unless your seed said otherwise

A boss sweep used to hand you filler and nothing else: every class the Progression Surface can
name was cut when the sweep was built, in every seed, whether or not that seed had put progression
there. Crystal Tears and legendaries are not on the default surface at all, so they were being
withheld to protect a placement that could not happen.

The cut is now in two halves. **The floor never moves** -- no sweep, under any option, hands you
another boss's reward, a Remembrance, a Great Rune, a key item or a merchant's stock. **Everything
else is decided per seed** against your own Progression Surface: Golden Seeds, Sacred Tears,
Scadutree Fragments, Revered Spirit Ashes, Crystal Tears and legendaries sweep unless you put that
class on the surface, in which case they stay where they lie because that is where your Locks are.

At the default surface a full-map seed gains **51 checks** (the legendaries and the Crystal Tears)
and keeps the four collectathon lines protected; untick a line on the surface and the sweep picks
it up. The baked corpus is 3731 -> **3876** member links across all 29 regions, 218 triggers
unchanged, nothing removed.

🛑 With an EMPTY Progression Surface there is no confinement at all and this cut has nothing to act
on -- progression scatters wherever fill puts it, including onto ordinary sweep members, as it
always could.

⚠️ **Seeds move.** The region divvy deals a region's pool round-robin, so adding members re-phases
every share after them: 774 checks changed which boss grants them, with **zero** crossing a region
boundary. Where a check lives is unchanged; which boss pays it out is not.

### ✅ The SHIPPED fixture row for v0.4.0 is here, on time, for the first time in eight windows

`0.3.3`, `0.3.4`, `0.3.6`, `0.3.9`, `0.3.10`, `0.3.11`, `0.3.12` -- every one of those rows was
written LATE, at the following window-open rather than at the tag, and each time a comment
predicting the next one was ignored. This one is written minutes after the tag.

🛑 **That is not a fix, it is a good day.** A row a person remembers is a row a person can forget,
and seven for seven says which way that goes. The fix named at 0.3.10 and still not taken is to
derive the fixture from `git tag`.

### The gitlink pin, corrected twice in one window

The v0.4.1 window PR meant to pin the gitlink at the client half and **silently did not** -- a
`git update-index` whose staged diff nobody looked at, so the pin stayed at `78b1a543` (the
v0.4.0 client) while the world moved to 0.4.1. It is at `f1afb8e5` now, client `main`, where
PR #180 merged.

🛑 **And the first attempt at the correction invented a hash.** The full SHA was written out from
an 8-character prefix rather than read, and `f1afb8e5395a...` is not a commit that exists --
`git update-index --cacheinfo` will happily record a gitlink pointing at nothing, because it never
asks whether the object is there. It was caught by comparing against the API before committing.
Two different silent-failure modes on one two-line change, both of which produce a repo that looks
fine: **read the staged diff, and read the SHA from the source rather than completing it.**

Verified at the pin rather than assumed: client checked out at `f1afb8e5`,
`check_version_sites --expect 0.4.1` agrees across all four sites, and `gen_contract.py` leaves the
client tree clean.

### `stable` finally moves, and it was blocking the landing page

`CHANNELS.tsv` had `stable -> v0.3.10` through **two** tags, and `check_channels` was green the
whole time, because that gate verifies the pointer RESOLVES rather than that it is current.

That was not cosmetic. `deploy_wizard.sh --landing` fetches from the **stable tag**, and v0.3.10
has no `wizard/landing.html` -- so for as long as stable sat there, the new front page could not be
deployed at all. `stable -> v0.4.0` is the row that unblocks it.

### `deploy_wizard.sh` must be ASCII, and I put two 🛑 in it

`test_gf_publish_channels.WizardDeploy.test_it_is_ascii_and_executable` -- "non-ASCII in a shell
script that runs on a strange box" -- went red on the two comment headers added for `--landing`
and the questline DAG. The file uses `!!` for exactly this reason and has since it was written;
the emoji convention is for Python, Markdown and Rust, not for the one file that gets `scp`'d onto
someone else's server and run under whatever locale it finds.

🛑 **This ran in the `generators` job and I never ran that job locally.** The release gates
(`check_release_notes`, `check_contract_version`, `check_version_sites`, `check_channels`) were
green every time I reported them green, and they are not the same set: `generators` also runs 18
repo-only suites via `gf_suite_ledger.py --generators-list`. Reporting "gates green" after running
a hand-picked four is how a red reaches main with a green summary attached to it.

### A stream for website-only updates: `deploy_wizard.sh --site`

A typo on the landing page needed a tag, a `CHANNELS` promotion and a full deploy, because every
artifact here is pinned to the stable tag. That is right for the wizard and wrong for a page that
describes nothing. `--site` ships `landing.html` and `report.html` **from main**, in seconds,
touching nothing else.

🛑 **It is deliberately not "all the static pages", and the split is DERIVED rather than a list
someone maintains.** A page is COUPLED if it carries an option surface (`er-options-metadata`) or a
data stamp (`inputs_hash`); FREE if it carries neither. Today that is exactly wizard/checks/
questlines coupled, landing/report free.

The hazard is the one `SPEC-publishing-pipeline.md` measured in section 2.1: Archipelago does not
error on an option the installed apworld has never heard of -- it prints one line among fifty and
generates the seed **without it**. A wizard shipped ahead of the release does not break, it silently
ignores the setting a player chose. That is the worst failure this pipeline can produce, and it is
why the fast path may never touch the wizard.

`test_gf_publish_channels.SiteChannel` asserts the membership **in both directions**. Forwards stops
a coupled page joining the fast path. Backwards stops a free page being quietly left off it -- and
more usefully, means the day `landing.html` grows a version stamp, the TEST fails rather than the
deploy shipping a stamped page from main forever. Seen to fail before being trusted: adding
`wizard.html` to the set reddens it with the option-surface message.

### A bug report you can file without a GitHub account

`.github/ISSUE_TEMPLATE/bug_report.yml` asks the right questions and lands in the right place --
and it **requires a GitHub account**, which is a real filter on a Discord full of players who have
never opened an issue. A report that is never filed is a bug found weeks later from a playtester
instead.

So the same questions now also live at **`/er/report.html`**, and the answers come out two ways: a
prefilled GitHub issue for people who have an account, and a formatted block on the clipboard for
people who would rather paste it into Discord. No backend, no network calls, nothing typed there
leaves the browser until a button is pressed. Both doors ask the same things on purpose; two intake
forms that disagree would be worse than one.

**It trims the log to the last `SESSION START` for you.** That is the single most repeated
instruction in every triage this project has had, and it is a thing a page can just do instead of
asking. It says when it did it, so nobody wonders where their log went.

🛑 **The GitHub prefill has a length ceiling and it fails ugly, not loudly** -- past roughly 8k of
URL the request is rejected or silently truncated, and a yaml plus a log clears that easily. The
page measures the URL first. When it will not fit, the WHOLE report goes to the clipboard and a
blank issue opens for it to be pasted into, rather than a prefilled issue that quietly dropped the
log -- which is the field triage needs most.

### A missing artifact at the STABLE tag is a skip; at main it is a bug

Adding `report.html` broke `deploy_wizard.sh` for the ordinary case, and the failure was correct
but useless: the file is not in v0.4.0, so `curl -f` 404'd and the whole deploy aborted after
installing the wizard. Every new page would do this once.

A 404 at the **stable tag** now SKIPS, loudly, with a reason -- that tag legitimately predates an
artifact added after it was cut. A 404 at **main** stays FATAL, because main is this repo's own
tree and a file missing there is a bug rather than a gap. Anything that is not a 404 -- network,
DNS, a proxy, a ref that does not exist -- stays fatal for every ref, because none of those mean
what a 404 means. Skips are counted and reported at the end (rule 4: a filter with no tally is a lie).

**And an aborted deploy no longer litters the served directory.** `die` exits the shell, so
`install_one`'s `RETURN` trap never ran and its `.tmp` survived -- inside the directory the web
server is serving, under a name nothing would ever clean up, fetchable and half-written. The
in-flight temp file is tracked globally and cleared on `EXIT` as well.

### The questline DAG was on the host by accident, and is now deployed on purpose

Listing `/er-static` inside the container before mounting over it turned up a file nobody had
accounted for: `er-archipelago-questline-dag.html`, 258 KB, timestamped at **image build time**.
The Dockerfile's `ertools` stage bakes it in, so it was being served -- pinned to no tag, refreshed
only by a rebuild, and about to vanish silently the moment `/er-static` became a bind mount fed by
`deploy_wizard.sh`.

It is a fourth artifact in the script now, at `/er/questlines.html` and `/er/beta/questlines.html`,
with the same ref-pinning and the same atomic install as the other three. `--no-checks` skips it
along with the check browser; together they are ~3.2 MB.

🛑 **It was found by listing the directory, not by anything that would have told us afterwards.**
A page that exists only because of a build step nobody remembers is one rebuild from gone, and
there is no gate for "a URL that used to work".

Its sentinel is `id="mer"`, the graph pane. The page's own `id="q"` search box would not do: one
letter is a string a login page can plausibly contain, and a sentinel that can pass by accident is
not a sentinel.

### 🛑 `--landing` was writing a file nothing would ever serve

The flag shipped in this window pointing at `${ER_ROOT_DIR}/index.html`, on the assumption that
peliarch served `/` from a static directory. **It does not.** `/` is a Flask route
(`webgui/app.py`) and Caddy does `reverse_proxy web:8080` for everything, so that file would have
been written, reported as installed, and never served -- and nobody would have found out until the
front page failed to change after a deploy that said it succeeded.

Alaric asked whether the fork needed updating. It did, and this is what the question found.

The app now serves `ER_STATIC_DIR/landing.html` at `/` (peliarch PR #11), so the page lands in the
same directory, by the same atomic tag-pinned install, as `wizard.html` and `checks.html`. One
directory, three pages, one deploy, `ER_ROOT_DIR` gone.

**Hosting is retired on the peliarch side too.** `POST /rooms` and `POST /generate` answer **410**
rather than being deleted: two callers exist in the wild that we cannot update -- a wizard already
open in a browser, and the `file://` wizard inside every previous release zip -- and the old wizard
prints `data.error` straight into its own UI, so a 410 carrying a readable sentence is the only way
to tell a player what happened. Existing rooms and their pages are untouched; there are five on the
box and at least two belong to other people.

**And the landing page now carries its own footer chrome, by hand.** Every other page on that host
is a Jinja template that gets the donation link and contact details from a context processor, which
peliarch's suite asserted on `/` among others. A static page cannot be reached by a context
processor, so those assertions had to be rescoped to `/room/<id>` and `/downloads` -- a real,
acknowledged loss of coverage -- and the thing they were protecting is paid back in `landing.html`
directly. The peliarch tests say so in their own docstrings rather than being deleted quietly.

## v0.4.0 — 2026-08-12

Window opened AT THE TAG of v0.3.12, and **not** on purpose: main was red on `check_release_notes`
(rule 14, "release notes exist for the open version") from the moment the tag was cut. Four windows
running had been opened deliberately; this one was asked for by a gate, which is the honest way to
record it.

🛑 **The minor component moves for the first time since 0.3.0, and it is not ceremony.** Two things
that landed under the v0.3.12 window change what a default seed does:

- `item_categories` reclassified 319 spells, spirit ashes and crystal tears from filler to
  **useful**, and useful is placed before filler. The same yaml and the same seed number now produce
  a different layout. Nothing is unreachable -- the fill regression ran 88 generations across 11
  configurations with no failures -- but a seed you are part-way through will not match a fresh
  generation of it.
- `rune_shop_pricing` stopped being unconditional and became an option that is **OFF by default**.
  A default seed no longer rolls rune shop prices, which it has done since late July.

A player can see both without reading a note. That is what a minor bump is for, and 0.3.13 would
have understated it.

`CONTRACT_HASH` is unmoved at `5c2b9bf2`. The bump is version-lockstep, not a contract change, so a
v0.3.12 client still handshakes with a v0.4.0 seed and vice versa. The number is `0.4.0` and not
`0.4`: `tools/check_version_sites.py --expect` is anchored `^\d+\.\d+\.\d+$`, and every row in
`CONTRACT-VERSIONS.tsv` since 0.2.0 is X.Y.Z. A two-component version passes the commit and fails
the cut.

### 🛑 v0.3.12's notes were written and never published

The v0.3.12 tag carries a full changelog section and a complete `BLURB-v0.3.12.md` -- eleven items,
including matt's-randomizer telescopes, the bell-bearing split, the classification move and the
Curated Filler control. The GitHub release body for that tag is three words: **"VA/RVA hotfix"**.

Nothing was lost; it is all in this repo. But every one of those changes is, as far as any player
outside this repo can tell, unannounced. The release-notes gate cannot catch this: it checks that
notes EXIST, not that they were ever put in front of anyone. v0.4.0's announcement carries the
v0.3.12 blurb forward rather than leaving it in a file nobody reads.

### The docs finally tell you where the yaml builder is

The options wizard has had a Seed size tab since v0.3.8, seven tabs since v0.3.11, and a live
sent-out readout since v0.3.12. Every one of those landed in a blurb. **Not one player-facing
document has ever contained the URL.** `SETUP.md`, `PLAYER-GUIDE.md`, `DISTRIBUTION.md`, the Nexus
description and the README mention "the wizard" five times between them and never say where it is;
the string `peliarch` appears nowhere outside a spec, a deploy script and the page's own source.

So the surface most players would meet this project through was reachable only by already knowing
about it. <https://peliarch.ca/er/> is now in the setup guide (as step 2, ahead of hand-editing the
template), the player guide, the distribution doc, the Nexus page and the README, with the channel
and staleness caveat stated rather than buried: the page is pinned by nothing, `/er/` tracks the
released build and `/er/beta/` tracks `main`, and Archipelago silently drops an option your
installed apworld has never heard of.

`SETUP.md` also stops calling itself "Setup (v0.2)".

### peliarch.ca has a front door, and it is the builder

The box was set up to host Archipelago rooms and its front page said so. The thing people
actually arrive for is the yaml builder at `/er/`, and it was reachable only by already knowing
the path -- which is the same finding as the docs never carrying the URL, one layer up.

`wizard/landing.html` is a single file, no build step, same palette and type as the wizard so the
handoff does not look like two different sites. The builder is the primary call to action; room
hosting is one card among three, which is what it now is. Every figure on the page is derived
from the tree rather than recalled: **28 regions** (17 base, 11 DLC), **4,931 catalogued checks**,
**56 options**.

**The check browser is now a published surface too.** It was a 2.9 MB self-contained file
committed at the repo root that nothing deployed and nothing linked, and its own source says it
works "offline and on peliarch alike" -- on a path that did not exist. `deploy_wizard.sh` installs
it at `/er/checks.html` and `/er/beta/checks.html`, **pinned to the same ref as the wizard beside
it**, because a reader joined over a different build's generator output describes a different
corpus. That is SPEC-publishing-pipeline.md's measured skew, one file over.

`install_one` now takes its source path and its sentinel as arguments instead of hard-coding the
wizard's, so the refusal-to-install check is per-artifact: the browser's is `id="mapslot"`. The
atomic write, the `curl -f` and the 200-with-a-login-page defence are unchanged. `--no-checks`
skips the 2.9 MB fetch for a cron that runs oftener than the data moves.

🛑 **Not deployed by this commit.** The page and the script are in the repo; putting them on the
box is a separate act, and `/er/beta/` still needs a Flask route or a full path -- the script's own
closing note has said so since it was written.

### The docs described a different game, and a review found it

An independent readiness pass over every player-facing surface, asking one question: does someone
arriving from the Archipelago Discord with no prior knowledge reach a running seed without hitting
a statement that is no longer true? They did not.

**🛑 The DLC default was documented backwards, everywhere.** `EnableDLC` is a `DefaultOnToggle`
(`core.py:253`) -- the apworld's own default is **on**. The shipped `EldenRing.yaml` sets it
`false`, which is where "DLC is off by default" came from, and that sentence was then repeated in
SETUP.md, the player guide, the Nexus page and the landing page as a fact about the *world* rather
than about the *template*. It is not. A yaml with an empty `Elden Ring: {}` section gets all 28
regions -- and so does the options wizard's blank **Defaults** card, which described itself as
"the full base-game experience, untouched" while emitting exactly that empty block. Four of the six
wizard presets pin `enable_dlc: false`; `vanilla_deathlink` and `dlc_only` do not.

The default is unchanged -- flipping it would move every seed generated from a bare yaml. What
changed is that six surfaces now say what it actually is, and the Defaults card names the DLC
instead of promising a base-game run it does not produce.

**Numbers that had drifted, all re-derived from the tree rather than corrected to each other.**
The docs carried **four different region totals**. The true figures: 28 regions (17 base, 11 DLC)
from `data.REGIONS` and `region_spine.DLC_REGIONS`; 4,931 catalogued checks; 56 options from
`options-metadata.json`.

| Where | Said | Is |
|---|---|---|
| `SETUP.md` x2, `NEXUS-DESCRIPTION.txt` | 19 tunable options | 56 |
| `EldenRing.yaml` x2, `SETUP.md` | 30 regions with the DLC | 28 |
| `NEXUS-DESCRIPTION.txt` | 31 with the DLC | 28 |
| `README.md`, `NEXUS-DESCRIPTION.txt` | 14 DLC regions | 11 |
| `KNOWN-ISSUES.md` | 13 DLC regions | 11 |
| `SETUP.md` | shipped `num_regions: 0` | 6 |
| player guide | `0` is the shipped default (and `6` is, 116 lines later) | 6 |
| player guide, `EldenRing.yaml` | sweeps ~1971 / ~3184 | ~1984 / ~3197 |
| `KNOWN-ISSUES.md` | about 507 unconfirmed check names | 512 |

**Claims that were simply false.** `num_regions_order` was documented as "vestigial -- omit the
key" in SETUP.md and "deprecated, every value rolls at random" in the player guide; it has taken
`rolled` and `vanilla_order` since #563, and `vanilla_order` is deterministic. Enemy scaling was
"always on" in the player guide and on Nexus; it is on by default and `enemy_scaling: false` turns
it off. The player guide claimed weapon stat requirements are "waived in v0.2" as though that were
a version-scoped fact.

**`KNOWN-ISSUES.md` was labelled two different versions three lines apart** -- `v0.3.11` in its
title, "Current as of **v0.3.7**" underneath -- during a release-a-day month. Both now read v0.4.0,
and the DLC default is called out there too.

**`deploy_wizard.sh --landing` did not exist.** `landing.html` documented the flag in its own
header and nothing implemented it; the arg parser exits 2 on unknown arguments, so the new front
page could not be published by the only command that claimed to publish it. Implemented, with its
own destination (`ER_ROOT_DIR`, the site root, not `/er/`), its own sentinel (`id="er-landing"`),
and a guard that fails BEFORE fetching anything rather than after three files are installed.
🛑 It fetches from the STABLE tag, so it fails until the `CHANNELS.tsv` promotion row points stable
at a tag that carries the file. That failure is loud and correct.

**Everything above is a labelling repair. No option default, option shape or generated seed moves.**

### 🛑 Hosting is out of scope, and the wizard stops offering it

peliarch.ca is five things as of v0.4.0: **the yaml builder, the downloads, the documentation, the
check browser and the bug report form.** It does not generate seeds and it does not host rooms.

**THE MOTIVATING CASE (rule 11), 2026-08-12.** The rooms dashboard listed five hibernated rooms and
offered every one of them the same connect address -- `ws://peliarch.ca:38400` -- with a Copy button
beside it. The allocator is genuinely port-per-room (`RandomPortSocketCreator` takes a free port out
of 38400-38463 when the socket is created, skipping ports already in use), so 38400 was a
**placeholder shown for rooms with no live socket**, and four of those five addresses were wrong the
moment their room woke.

That is worse than a dead link. Archipelago's `Connect` packet carries a slot name and a password
and **no room identifier**. A client that reaches whichever server actually holds 38400, carrying a
slot name that seed happens to contain, joins the wrong multiworld and is told nothing. Two rooms in
that list were both named `Player - Elden Ring`.

The display bug is fixable. Owning the failure mode is the part that is not worth it a week before
the first public announcement, so the surface is gone rather than patched.

- `wizard.html`'s **Generate & host** card is now **Take your yaml**: Copy, Download, and a pointer
  at archipelago.gg. `doHost()` and `hostEndpoint()` are deleted, so the served page and the
  `file://` page in the release zip now behave identically and there is no same-origin story left
  to get wrong.
- `check_wizard_renders.SIDE_ORDER` moved with it. 🛑 That line changed because the REQUIREMENT
  changed, which is the only reason it may ever change -- editing it to match a wizard that drifted
  would delete the assertion instead of checking it.

### A bug report form, because every triage has started by asking for the same four things

`.github/ISSUE_TEMPLATE/bug_report.yml` asks for the release **tag** both halves came from (not the
printed version -- several builds have shipped under one version string), the whole yaml rather than
the lines the reporter thinks matter, the client log **from the last `SESSION START`** because the
log is appended across sessions, whether the DLC was in play, and what else was loaded --
`RandomizerHelper.dll` and matt's launcher being the two that most often change the answer.

Its `config.yml` routes misregion reports to the check browser instead, which already fills that
issue out with the evidence attached, and puts KNOWN-ISSUES.md in front of the form.

### The version-lockstep sites

`APWORLD_VERSION`, `archipelago.json`, `wizard/options-metadata.json`, `wizard/wizard.html`, the
client's `Cargo.toml` and `Cargo.lock`, and the generated `contract_gen.rs`. The client half is
PR #179, merged at `78b1a543`, and the gitlink points there.

🛑 **The world half merged FIRST this window, which is the wrong order and main went red for it.**
`client-main-drift` regenerates the cross-repo artifacts against client `main`, and client `main`
still read `0.3.12` for 24 minutes after world `main` read `0.4.0`. That job is `skipped` on every
pull request and runs only on `main`, so no PR could have caught it and none did: #603 was green on
its head SHA and red the moment it became a merge commit. The rule the window procedure already
states -- the client half lands first, because a gitlink can only point at a commit that exists --
turns out to have a second reason behind it that nothing had written down.

### The SHIPPED fixture row for v0.3.12 is here, and it was hidden rather than late

`test_every_tagged_version_is_recorded_as_shipped` has caught this row six windows running. On the
seventh it did not run at all: `check_release_notes` fails EARLIER in the `generators` job, an
aborting step skips every step below it, and the tag test is below it. Confirmed from the jobs API
on run 31639475006. Two independent failures had to line up for nobody to notice, and they did.

## v0.3.12 — 2026-08-12

Window opened AT THE TAG of v0.3.11, the fourth time running it has been opened on purpose rather
than by something going red -- although main WAS red at the tag, on the SHIPPED fixture row v0.3.11
owed, for the sixth window in a row.

`CONTRACT_HASH` is unmoved at `5c2b9bf2`. The bump is version-lockstep, not a contract change, so a
v0.3.11 client still handshakes with a v0.3.12 seed and vice versa.

### Playing through matt's randomizer? Your AP items were wearing telescopes

The AP flower is not an item -- it is icon cell 92, the vanilla Telescope, repainted by a texture
we ship as a me3 *package*. One line in `ap.me3` pulls that package in, and matt's randomizer's
"Add dll mod" launch path never reads `ap.me3` (the same reason that path gives you no separate
save file). The client goes on pointing every foreign shop slot at cell 92 regardless, so the
pointing lands and the repaint does not: a shop full of telescopes, and a player who reasonably
concluded his shops held no AP items at all. They did -- the *names* are written at runtime and
were correct the whole time.

- `ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md` now has the fix: copy `menu` out of `ap-package` into
  matt's output folder, beside `regulation.bin`. It is flagged as unconfirmed in game, and it warns
  that re-randomizing may undo it.
- The client no longer stays quiet about it. It already logged all three facts that prove the case
  -- non-me3 loader, our `ap-package` present, a data mod one level up -- and drew no conclusion
  from them. Now it warns in the log with both folder paths, and tells you once on screen.
- On me3, nothing changes and nothing is said.

### Smithing bell bearings are gear; merchant bell bearings are convenience

Elden Ring files all 48 bell bearings in one inventory tab with the gate keys, so this world called
them all `key_items` and classed them junk — including the ones that hand you the entire smithing
economy. A naturally-placed Somberstone Miner's Bell Bearing [4] was filler.

They are two categories now:

- **`upgrade_bells`** (13) — Smithing-Stone Miner's, Somberstone Miner's, Glovewort and
  Ghost-Glovewort Picker's. These are the upgrade economy in one item, and they are **useful**.
- **`merchant_bells`** (35) — a dead merchant's own shelf, moved to the Twin Maidens. Convenient,
  not power, so they stay filler.

Both are selectable in `keep_local`, `exclude_local_item_only` and `keep_out_of_shops`, and the new
`bell_bearings` umbrella covers both at once. **`key_items` still means the whole tab**, so a yaml
that already says it keeps exactly what it kept before.

### Your spells, spirit ashes and crystal tears are gear, and now they say so

Elden Ring files sorceries, incantations, spirit ashes and physick tears under the same internal
category as crafting materials and throwing pots. This world took that at its word, so 319 items a
player equips, casts and drinks were labelled **filler** — junk — everywhere it counts: in
Archipelago's fill priority, in your spoiler, and in the tracker of whoever receives one.

They are `useful` now.

**Be clear about what this does and does not change.** It is a labelling fix, and it was measured
rather than assumed: the share of a seed's pool that is useful moves about a point, and the mix of
what reaches a partner world is unchanged within noise. What changes is that a specific item is
described correctly — Comet Azur arriving in someone's Hollow Knight run reads as gear instead of
junk, and the fill treats it as gear when it places it. The lever that decides *how much* of your
loot travels is still `confine_foreign_progression`.

**Your seeds will differ.** Useful items are placed before filler, so the same yaml and the same
seed number now produce a different layout. Nothing is unreachable — the fill regression ran 88
generations across 11 configurations with no failures — but a seed you were part-way through will
not match a fresh generation of it.

`upgrade_materials` deliberately did NOT move: smithing stones are the economy the filler budget
allocates by the hundred, and promoting them is an economy change, not a labelling one.

### `cookbooks` is its own category, and `key_items` still means the whole tab

`key_items` was 220 items, and 96 of them are crafting cookbooks. There was no way to say "keep my
cookbooks local but send the gate keys out", or the reverse, because the game files both under one
inventory tab and the world took the tab at its word.

`cookbooks` is now a category of its own, selectable anywhere the others are — `keep_local`,
`exclude_local_item_only`, `keep_out_of_shops`.

**Your yaml does not change meaning.** `key_items` becomes an umbrella covering both halves, exactly
as `goods` did when it was split, so a yaml that already says `keep_local: [key_items]` keeps the
same 220 items home and nothing quietly starts travelling. Say `cookbooks` to reach the 96 on their
own, or list the categories you want to peel them off.

### `filler_foreign_pct` moves the numbers now, and the readout is always on screen

Three complaints, one card. Alaric, working the knobs: *"seemingly widget went dead after i messed
with it enough"*, *"can we get it on the right side so you can see it change as you change the
options around"*, and *"it didn't seem responsive to the filler local percent, which id assume is
the main lever"*.

**It is the main lever, and it moved nothing but a footnote.** `filler_foreign_pct` forces
`(100 - pct)%` of your distinct filler NAMES to stay home, and this world's filler is the generic
Rune plus every goods-nibble item — consumables, crafting materials, upgrade stones, the bulk of any
seed. It was left out of the figures because the option samples names and names carry different
numbers of copies, so no exact answer exists. That is a reason to label an estimate, not to print
nothing: at `filler_foreign_pct: 50` the card now reads **1,031 open / 439 held / 30% of your pool**
instead of an unchanged 1,470 and a line of prose. The estimate is the goods categories' measured
share of the pool times the held fraction, and it says out loud that your seed will land either side
of it.

`keep_local_rune_cap` had a worse version of the same problem: it printed *"part of the runes share
above"* when there was no runes share above, so the card said **"Nothing is held back"** and then
described something being held back, in consecutive sentences. It now says which share it eats into
and admits it cannot count it.

**The live readout is in the right-hand rail**, directly under your yaml, so it is on screen on
every step
— the options that feed it live on four different tabs, and watching a number while you turn its
knob is the whole point. The long card with the explanation stays on Seed size. The copy on the
Multiworld & Placement tab is gone: the side card does that job on every tab instead of one.

**On "went dead":** no crash was found. A fuzz over 1,969 single-option states and 700 random
multi-option states across all eleven steps threw no exception. What almost certainly looked dead is
the Seed size step going blank every time it was re-entered (fixed above) plus the two knobs that
answered nothing. The gate for that is new: `check_wizard_renders.py` now also asserts that six
locality options each move a headline FIGURE, and that the rune cap at least changes what the card
says.

🛑 That gate passed its own negative test twice before it worked. Matching any digit in the card is
not the same question — the explanatory prose is full of its own percentages, so a mutation that
froze the headline sailed through. The figures a player reads are marked `fig` in the markup, and
the check reads only those.

### The Seed size step was blank until you touched something

Open the wizard, click through to **Seed size**, and the page drew the ten controls and nothing
else. No "How big is this seed?", no check counts, no filler/useful split, and no contribution
card -- all of it appeared the moment you changed any setting, and not before.

`renderSeedSizeTab()` built its two containers and called `paintSeedSize()` itself. But
`paintSeedSize` finds those containers with `document.querySelector`, and the tree it was painting
into had not been attached to the document yet -- the caller appends it on the next line. The lookup
returned `null`, `paintSeedSize` took its "not the tab on screen" early return, and drew nothing.
The step then stayed empty because every `refresh()` in the page lives in an event handler and
`renderStep` does not call one. Introduced 2026-08-08 by the refactor that split the tab in two so
the controls could sit under the figures they move -- the change that made REPAINT possible is the
one that broke FIRST PAINT. The caller now paints, immediately after attaching.

Nothing was red for three days, and nothing could be: a DOM lookup that misses returns null, and an
empty div renders perfectly. Every wizard gate we had reads the page as text. So there is now one
that runs it -- `tools/check_wizard_renders.py` walks all eleven steps through the step rail's own
click handlers under a small DOM shim and fails if any of them draws nothing. It carries its own
self-test: it re-introduces the detached paint and fails if the shim does not notice, because a
model of a browser that cannot reproduce the bug it was written for is scenery.

🛑 The blank step is NOT what a length check catches -- the control card kept rendering its ten
option rows throughout, which is exactly why an empty tab read as a design choice.

### 🛑 v0.3.11 shipped a client from the day before, and this window is the repair

v0.3.11 was tagged with the submodule pin still at client `a9830ebe` -- 41 commits and 22 merged
pull requests behind the client's own `main`. The tagged build therefore does not contain the work
v0.3.11's notes describe: received spells being memorised, `no_equip_load` writing the field the
game actually reads, the roll mode, the DeathLink toast, the bell hand-in reaching the client feed,
the boss-fight HP sampler, or the guard that stops a non-numeric port becoming a retry loop of
parser errors.

Nothing was lost -- all of it is on `main` and none of it was reverted. What happened is that the
release named it and did not carry it, so a player who read the notes and installed v0.3.11 got a
client that behaves like v0.3.10. **If you are on v0.3.11, this is the update to take.**

`RELEASE-CHECKLIST-v0.3.md` has carried a `Gitlink == client main` row since v0.3.8 -- it exists
because v0.3.7 tagged a pin five client merges old and v0.3.8 was eleven behind on the morning of
the cut -- and it says the tag job refuses a stale pin. It went out anyway. The row is not the
instrument; something that runs is.


### The Curated Filler recipe was unusable in the wizard, and editing it broke your yaml

Curated Filler is the only option whose value is a table rather than a number, a switch or a list.
The wizard had no control for a table, and its branch list ends in a catch-all that makes a plain
text box -- so the recipe was handed to the box as a value and came out as the literal string
**`[object Object]`**. That is what a player saw where the weights should be.

The box was worse than useless. Typing in it stored the text you typed, and the yaml you then
downloaded said `curated_filler: "..."` -- a quoted line where the world expects a table of
categories, which is not a recipe at all. The row also had no way back: two tables are compared by
identity in the page, so once the option had been touched it counted as changed for the rest of the
session, even after every weight was put back. The default in the trailing comment read
`(default: [object Object])` too.

It is now a weight per category, with the share of the filler tail each weight buys shown beside it,
because the weights are relative and the share is the number you are actually choosing. The yaml
comes out as an indented block, and an all-zero recipe writes `{}` -- which the option documents and
honours as *no gear and no upgrade economy*, rather than silently reverting to vanilla junk.

**Seven of the sixteen categories were unreachable from the page even in principle**, and that is the
part that made this unfixable rather than merely ugly: `CuratedFiller` never declared its accepted
keys, so the wizard had nothing to enumerate and could only ever have offered the nine the shipped
recipe happens to weight. `firepots`, `ammunition`, `perfumes`, `utility`, `rare`, `funny` and `junk`
are all real, all documented, and none of them were on the page. The list now comes from one place
that AP's validation, the wizard metadata and the generator's own unknown-category error all read,
so they cannot come to disagree.

🛑 **And the list I first derived it from was wrong.** `_VALID_CATS` omits `juice` -- the gear
injection has no member list of its own -- and `juice` is the largest weight in the shipped default,
so validating against it would have rejected the world's own default recipe and failed every seed
that did not override it. Caught by a test written for exactly that, which is now the one place
those two constants are compared.

Nothing else changes for you: the accepted categories, the default recipe and any yaml you have
already written are untouched. What moves is that an unknown category is now named at option
verification instead of a few steps later.

The gate that was missing is the cheap one -- **every kind of option the metadata can describe must
have a control that draws it**. Everything we gated before asked whether what IS drawn is right; a
text box for something that is not text is the failure that looks like success, and the same shape
as the contribution card reading a frozen option and getting `undefined`. Raised by Alaric off the
live page (#571).


### Traps can drop any enemy in the game on your head, starting with three basilisks

Traps were three fixed effects: half your runes, a dead flask, a Runebear at your feet. Adding a
fourth meant hand-deriving three game ids, hardcoding them, and shipping a client -- which is why
there were three.

The Runebear's ids came from the game's own name table. That route does not generalise, and finding
out why is the useful part of this change: **that table names 76 of roughly 600 enemy models.** The
basilisk is not in it. Neither is almost anything you would want dropped on you. So the ids now come
from the params themselves -- 390 spawnable models, each resolved to the body and the AI rows a
spawn needs, refusing the 26 that have no brain or no body (scenery like the Walking Mausoleum, or
Morgott's corpse) because those would generate cleanly and then do nothing in-game forever.

`traps: [basilisk]` gets you **three basilisks where you are standing**. One is a joke -- the threat
is the Death Blight mist, and mist wants numbers. It can kill you outright, so it sends a DeathLink.

`spawn_traps: [4630]` takes any of the 390 by model id, for anyone who wants something specific.
An id that is not spawnable is a yaml error rather than a silent dud.

Under it: the ids ride in the item NAME (`Trap: Basilisk x3 (4150/41500060)`), so this is
still a synthetic item -- no slot_data key, no `CONTRACT_HASH` move, no version lockstep, and an
older client refuses the name and says so in the log rather than misbehaving. The AP ids are
arithmetic in the model number rather than sequential, so blessing a new enemy later renumbers
nothing.


### Randomised rune shop prices are a choice again, and they are OFF by default

🛑 **This changes what a default seed does.** If you do not name it in your yaml, shop slots now keep
the price of the ware they used to sell.

The behaviour has not changed, only who asks for it. A shop check keeps the price of its old ware --
right for gear, wrong when the reward is a rune, because a rune is just money: a 3500-rune slot
selling a Golden Rune [1] worth 2000 is a slot nobody presses, and the check behind it goes
uncollected. Since 2026-07-25 that price was rolled into `[0, 2x the rune's own worth]` for
**everybody**, because the option was frozen on and removed from the yaml surface entirely.

It is a knob again:

```yaml
  rune_shop_pricing: false   # default; the slot keeps its original price
  rune_shop_pricing: true    # roll it into [0, 2x the rune's worth]
```

Off is the new default because a rolled price is a real design opinion -- sometimes free, sometimes a
bad trade -- and one a player should opt into rather than discover. If you liked it, one line brings
it back, and it is in the wizard under Shops & Merchants.


### A seed with spawn traps now tells an older client, instead of feeding it items it will eat

🛑 **If you use `traps` or `spawn_traps`, everyone on that seed needs a client from this release or
later.** The client says `CLIENT TOO OLD` and names the feature rather than connecting quietly.

The reason is worth stating plainly, because it already happened to a playtester. A spawn trap
carries its enemy's ids inside the item NAME. A client that cannot read that name does not fail
loudly -- the item arrives, Archipelago marks it delivered, the client does not recognise it, and it
is **dropped**. No toast, no tracker row, no way to get it back. Seven checks in one 2026-08-12 seed
were sitting on exactly that fate, and the version handshake passed cleanly the whole time, because
spawn traps declared nothing for it to check.

They declare it now, and only when a seed actually mints one -- a seed with no spawn traps still
connects to any client.

⚠️ The declaration makes the mismatch **loud, not fatal**: the client reports it at connect and
continues. It is a warning you cannot miss rather than a door that closes. Turning it into a hard
refusal is a separate decision, tracked on #595.


## v0.3.11 — 2026-08-10

Window opened AT THE TAG of v0.3.10, deliberately -- the third time running, after five windows that
were opened by something going red. Nothing has landed past the tag yet, so this section starts empty
of changes on purpose and fills as they arrive (rule 14).

`CONTRACT_HASH` is unmoved at `5c2b9bf2`. The bump is version-lockstep, not a contract change, so a
v0.3.10 client still handshakes with a v0.3.11 seed and vice versa.

### The wizard card that tells you what you send to other players had never once rendered

"What are you putting into the multiworld?" shipped on 2026-08-08 and every player who opened it got
the same sentence: *"Shuffle Vanilla Items is off, so there are no real items to send."* It is not
off. It cannot be off -- `item_shuffle` was frozen ON three weeks earlier, on 2026-07-26, which took
it off the yaml surface entirely. The card opened with `!!v("item_shuffle")`, that read an option
that no longer exists, JavaScript answered `undefined`, and `!!undefined` is `false`. The card was
born dead and nothing was ever red.

An absent option means its FROZEN value, never *off* -- the same mistake the client contract made
with its optional keys. `tools/check_wizard_lint_currency.py` now fails on any option key the page
reads without a presence test, checked per function, and its own negative test is the exact line
above.

**And now that it renders, it answers both directions**, which is what was asked for:

- **how many of your checks another player's item can land on** — new, and the number people
  actually want. Nothing in this world ever refuses an item for being foreign, so this is your
  checks minus whatever your locality options pin at home, and it needs to know nothing about the
  other players' slots.
- **how many of your items are free to travel** — the number that was already there.

They are the same figure read from either end, and the card now says so: Archipelago's fill is
count-neutral, so every item you hold at home keeps one of your own checks and every one you let go
opens a check to somebody else.

Underneath, **how many of your checks may hold another player's progression** — your progression
surface at the default `confine_foreign_progression: 100`, widening as you lower it, with the
measured warning attached: at 100 a non-Elden-Ring partner receives ~100% filler from you (no
weapon, armour or talisman reached a Hollow Knight slot in 498 placements), because confining their
key items to your surface fills their own world first and Archipelago places every world's useful
items before any filler.

`item_shuffle` also came out of the seed-size tab's control list, where it had been counted in the
heading while rendering no row.

### The options wizard has tabs now, instead of one accordion labelled "safe to skip"

Every one of the 54 yaml options used to live in a single collapsed section called
**Other Options**, inside the wizard's last step, under a line reading *"Everything here is safe to
skip -- the defaults are fine."* Enemy scaling, the pool builder, the progression surface, Keep
Local, the shop settings: all of it, behind one summary that told you not to open it.

They are now seven steps of their own -- **Goal & Regions**, **DLC & Blessings**, **Difficulty &
Scaling**, **Checks & Item Pool**, **Multiworld & Placement**, **Shops & Merchants** and **Quality of
Life** -- and the step rail highlights the ones you have changed something in. Advanced keeps only
the Archipelago-wide options.

Nothing about the yaml changed: the same options, in the same order, with the same defaults, and
every preset downloads byte-for-byte what it downloaded before. This is where the options are shown,
not what they do.

The grouping is defined once, in the world (`GFWeb.option_groups`), so **the player-options page on
any Archipelago WebHost gets the same sections** -- it had been rendering one undifferentiated Game
Options list for the same reason the wizard had one accordion. An option added later and not filed
under a group falls back into Advanced, which is the old failure one option at a time, so a test now
fails on it.

### New option: **Merchant Bells on Talk** (off by default)

Open a merchant's shop and their Bell Bearing is handed to the Twin Maiden Husks for you, so their
wares are on sale at the Roundtable Hold from then on. Asked for by **boblerrr** on the Nexus page
(#325).

You are NOT given the bell itself. Every Bell Bearing is a real Archipelago item in the pool, and
handing you a vanilla copy would put a second one of a singleton in your bag; what the option
delivers is the shop the bell would have unlocked. The bell stays worth finding -- it just arrives
already spent, and the Maidens will no longer offer to take it.

Your checks are unaffected either way: the Maidens open the merchant's OWN shop rows, not a copy of
them, so a slot bought at the hub fires exactly the check it would have fired at the merchant.

Covers 38 shops -- the roving merchants (Kale, the Nomadic / Isolated / Hermit / Abandoned /
Imprisoned merchants) and the named vendors (Gostoc, Sellen, Seluvis, Patches, Blackguard, Thops,
Corhyn, Miriel, D, Gowry, Rogier, Bernahl, Iji, Pidia, Moore, Ymir). It does NOT cover the peddlers
whose bells add stock to the Maidens' own shelf, and it triggers on the regular buy menu only -- an
Ash-of-War, tailoring or upgrade counter does not fire it.

A seed with this on requires a client that supports it, and will refuse the connect and say so
rather than quietly ignoring the setting.

🛑 **And for four days it did nothing at all.** Both halves shipped and neither one was wrong: the
client baked its 38-row table, armed the hook and put the feature in its supported list; the apworld
declared the option, documented it, and told the client the seed needed it. The single line that puts
the option's VALUE on the wire was never written, so the client was told "this seed needs merchant
bells", agreed that it could do that, and was then handed nothing to switch on. Every gate was green
for a reason -- the value is optional by design, so its absence is indistinguishable from `off`, and
the connect handshake does not cover it. Caught in **boblerrr's** playtest log the same week, from
the one line the client prints when the feature arms and did not print. Fixed, plus the gate that
checks every declared option actually reaches the wire, which is a check this repo did not have in
either direction until now.

🛑 The v0.3.10 SHIPPED fixture row was owed at the tag and written here instead, one window late --
the fifth window running that this has happened. It is recorded in `test_gf_contract_versions.py`
rather than quietly fixed, because a step that five consecutive windows have missed is not something
the next person will remember either.

### New option: **Keep Out Of Shops** (empty by default, so nothing changes unless you set it)

List the categories of your own item that merchants may never stock, and they land out in the world
instead:

    keep_out_of_shops: [weapons, armor]

Asked for by **boblerrr** on Discord, looking at a merchant shelf of weapons, gauntlets and helms
priced 800-25,000 with 11,144 runes in his pocket -- "so its more split around the world". 213 of
the 562 purchase-menu checks pay a weapon or an armour piece in vanilla, so on a small seed a shop
really is where your gear lives, and finding it is a matter of grinding runes rather than of going
somewhere.

It takes categories rather than being a gear-only switch, so `[consumables, crafting]` or
`[spells]` work too -- the same list Keep Local uses, umbrellas (`goods`, `everything`) included.
Both halves of a merchant are covered, the shop checks and the rerolled unlimited shelves, and
bell-bearing shops are shop rows like any other. Other players' items at your shops are untouched.

🛑 A SMALL SEED MAY NOT HAVE ROOM, and the option says so instead of pretending. Everything it
forbids from a shop has to fit somewhere that is not a shop, and the hub alone is 184 shop rows out
of 224 locations -- at `num_regions: 1` there are 93 non-shop slots against 66 weapons and 71
armour pieces. The categories are then taken one at a time, cheapest first, and any that does not
fit is skipped with a log line naming it and both numbers. In that example you get `weapons`
enforced and `armor` skipped rather than the whole option going quiet. A full-world seed has 4336
non-shop slots against 689 gear items and enforces the lot.

Rejected rather than quietly ignored: combining it with `vanilla_placement` (which pins every item
to its base-game location, merchants included, so nothing could be kept out of a shop), and pinning
a forbidden ware with `infinite_hub_wares`.

No contract change and no client change: `CONTRACT_HASH` is unmoved.

### Loading the wrong save no longer bricks the session until you restart the game

If you load a save that belongs to a different seed, the client refuses it on purpose: nothing sends,
nothing arrives, and a toast tells you so. That guard is right and it stays. What was wrong was the
next sentence, which told you to load this room's save or start a fresh character — and neither one
worked. The refusal was a one-way latch for the life of the process, so the brand-new character you
rolled loaded into the same gated, silent session, with the same toast still on screen. It looked
exactly like a broken install, and the only thing that actually fixed it was restarting the game.
Nothing anywhere said that, so at least one person went and rebuilt the client instead.

Quitting to the main menu now releases the refusal, and the next character you load arms normally and
gets its start items. Loading the same wrong save again simply refuses again — the release re-asks the
question rather than answering it, so the guard is exactly as strong as it was.

One refusal deliberately does NOT release: the one you get when the room changes underneath a live
session. That one has a reconciler already built for the old room, and re-arming it is not something
the client can do safely, so its toast still says RESTART and it still means it.

### The shipped yaml template was 17 options behind the game

A player burned the Erdtree, found the capital stuck in its Ashen version with his Leyndell Lock
suddenly useless, went looking for the setting that governs it, and got as far as
`SPEC-capital-reconciler.md` on GitHub before reporting back that no such setting exists in the
template, the player guide or the setup guide.

He was right. `capital_reconciler` has been on by default since v0.2.13 and it decides whether
burning the Erdtree permanently strands Royal Leyndell's ~152 checks -- and it had never appeared in
any file a player receives. Nor had sixteen others, including `start_with_whetblades` and
`progression_bias`: `release/EldenRing.yaml` carried 33 of the 50 player-facing options.

The template had a gate, and the gate only ran one way. `test_gf_shipping_yaml` has checked since
July that no key in the template is a fake option, because the template once went on declaring
`game: EldenRing` through a rename. It never checked that a real option reaches the template -- and
Archipelago ignores a missing option exactly as silently as an invented one, generating on the
default either way. The wizard's list is generated from the option classes; the template is written
by hand; so only the wizard moved when a feature landed, and when three options missed the wizard
two windows ago the conclusion drawn was that the yaml had always accepted them and only the wizard
was behind.

The gate now runs both ways, live, with the remaining sixteen listed in `_TEMPLATE_DEBT` and checked
for staleness so a drained entry cannot linger (#512). `capital_reconciler` is not among them: it is
documented in the template, in the player guide and in `KNOWN-ISSUES.md` in the same commit.

The player-facing half is worth stating on its own, because it is a thing the guide never said. The
burn is the game's own event and it switches off Leyndell's grace warp points, so straight after
burning you cannot fast-travel into the capital even holding its Lock. The reconciler still gives
you the Royal Capital back -- the *warp shortcut* is what the burn takes. Walk in from Altus through
the main gate, touch a grace, and it returns.

It caught an eighteenth on its first run, which is the best argument for it anyone could have
written: `merchant_bells_on_talk` landed earlier in this same window and had not reached the
template either. Documented here rather than quarantined.

`KNOWN-ISSUES.md` was also still titled v0.3.7 at three consecutive tags. Retitled.

### `confine_foreign_progression` is a percentage now, and it was quietly deciding what your friends get

It used to be a yes/no. It is now a share from 0 to 100 — `true` and `false` still work and still
mean 100 and 0, so nothing you have written needs changing — and the reason is a defect nobody had
measured.

The option's job is curation: hold other players' keys to your progression surface so a foreign key
item shows up on a major boss rather than on a Smithing Stone pickup. What it also does, and this was
not in anyone's model, is **push the other game's progression back into the other game's own slots**.
Archipelago places the entire `useful` tier before it places any filler, so by the time it reaches
what is left of your partner's world, only filler is available. At 100 — the shipped default, then and
now — a non-Elden-Ring partner receives *nothing from Elden Ring but filler*. Measured over three
seeds beside Hollow Knight: 498 items sent, **zero** of them a weapon, an armour piece or a talisman,
while a second Elden Ring slot in the same seeds received a healthy 43% useful. boblerrr reported it
from a live game before any gate did — *"dont think ive seen any of those items being global"* — and
he was right.

The default has NOT moved in this release; 100 is still 100 and your seeds generate exactly as they
did. What you have now is the ability to say something else. Beside Hollow Knight, the share buys
gear back quickly: 0% useful at 100, 5% at 90, 23% at 75, 38% at 50, and it is flat below that. The
price is the curation — the released share of foreign progression can land anywhere in your world, and
because "anywhere" is about 3000 checks against a surface of ~170, even a small release means most
incoming foreign keys are no longer on a starred check.

The multiworld smoke test now runs its two Elden Ring slots at *different* shares and asserts that at
least one of the items reaching the partner game is useful-classified. The old check counted items
reaching the partner and never looked at what they were, which is why it was green for the whole life
of the bug.

### A region lock no longer warps you past Sir Gideon

Unlocking the Ashen Capital lit its Queen's Bedchamber for you. That grace sits BEYOND the Erdtree
Sanctuary, so the warp dropped you on the far side of the Sanctuary's boss -- while the grace at his
door stayed withheld, exactly as it should be. You could skip him for free, and if you wanted to
fight him you had to walk back.

The base game's Queen's Bedchamber was fixed for the same reason on 2026-08-04, and it has been
withheld from Leyndell ever since. The ashen twin survived that fix by an accident of order: on the
4th the burnt capital had no grace bundle at all, so there was nothing to take it out of. It got one
two days later and the Bedchamber came along inside it.

Nothing else moves. The Ashen Capital still opens on East Capital Rampart, still lights Leyndell,
Capital of Ash and the Divine Bridge, and the Bedchamber is a short walk from all three once you
have earned it. Reported by Alaric from a playtest.

### ...and the template Archipelago generated for it would not load

Reported by Alaric on 2026-08-11, from the error Archipelago itself raises:

    KeyError: Duplicate key False found in YAML.

The share option accepted six names for its two endpoints -- `true`, `false`, `on`, `off`, `all`,
`none` -- and every one of them was correct. What was not correct was the file Archipelago builds out
of them. It writes a numeric option's accepted names into the template UNQUOTED, and in YAML `off` is
not the word "off", it is the value `false`; `on` is `true`. So the block held the key `false` twice
and the key `true` twice, and Archipelago's own loader refuses a file with a duplicate key. The
default template for this game could not be read by the program that wrote it.

`on` and `off` are gone. Nothing is lost by their going: writing `on` or `off` in your own yaml still
works and always did, because YAML turns those words into booleans long before the option sees them,
and `true` / `false` were never doing separate work. `all` and `none` are untouched, and the option's
behaviour, range and default are all unmoved.

🛑 The loud half of this was the easy half. A yaml loader that does NOT check for duplicates simply
keeps the last one, which means `on: 0` was silently overwriting `true: 50` -- the template shipped
with its own default weighted to zero, and that failure has no error message at all. Three checks
land with the fix; the one that matters generates the template with Archipelago's real generator and
hands it straight back to Archipelago's real loader. Fifty-four options were each correct on their
own, and nothing in this repo had ever read the file they add up to.

### A boss that does not exist no longer holds 10% of Mt. Gelmir hostage

`1038540800` "Fallingstar Beast" (Mt. Gelmir, by First Mt. Gelmir Campsite) has a healthbar, a name,
a defeat flag and 23 sweep checks -- and no beast. Warp to the campsite and there is nothing there.
The EMEVD carries a complete boss script for a character the map never places, so the flag can never
be set, and 23 of Mt. Gelmir's 222 checks -- 10.4% of the region, twelve of them the pickups ringing
that very campsite -- were auto-granted by nothing. Raised from **boblerrr**'s Mt. Gelmir playtest
(#540).

Those 23 checks were never lost: you could always pick them up by hand. What they lacked was the
boss-sweep auto-grant. They now belong to Mt. Gelmir's real field bosses instead -- 12 to the
Ulcerated Tree Spirit and 11 to Demi-Human Queen Maggie, both in the same region -- so no check
changed which region it lives in, and none entered or left the swept set.

This is the SECOND boss of its kind (the Isolated Divine Tower's `34150800` was the first, confirmed
absent 2026-08-05), and the tells that caught the first one caught nothing here: that one was
nameless on an empty map. So the fix is a detector for the SHAPE rather than a list of ids -- an
overworld boss with no arena anywhere on its tile, on a tile whose map data WAS read, that the map
still does not place. Generation now refuses to build if a third one appears without a human having
gone and looked. One candidate is already flagged and under review: the unnamed fight at the Fourth
Church of Marika, which keeps its sweep until someone stands on the tile, because deleting a real
boss's reward is the worse mistake.

### Progressive Stone Bells no longer competes with the bell bearings it replaced

If you turned on `progressive_stone_bells`, you were playing with **two** upgrade ladders at once. The
progressive one paced you up the Twin Maidens' shop a rung at a time; the vanilla one was still lying
around the world in eight pieces, and one of those pieces is `Somberstone Miner's Bell Bearing [5]` --
the top of the somber shop. boblerrr found exactly that, in Enir-Ilim, in a live game on 2026-08-10.
Picking it up did not degrade the ladder, it ended it: every progressive copy after it was a no-op.

The vanilla bearings now become progressive copies, one for one, the same way Golden Seeds and Sacred
Tears already become flask upgrades. With the option on you will not find a loose bell bearing at all.
With it off nothing whatsoever has changed -- all eight are still out there.

There are now exactly as many copies as there are shop tiers to unlock: four smithing, five somber.
Previously it was five and five, so the fifth smithing copy had nothing left to give you. And the fifth
*somber* rung is the reason this is not simply "stop adding copies": the game only ever hands out four
somber bell bearings (there is no `[1]`), so a ladder built purely out of what you find would have
stopped one rung short of Somber Smithing Stone [9] in every seed. It tops itself up instead, which
also means the ladder works on a seed that kept none of the four regions those bearings live in --
DLC-only included.

### Traps are in your item pool now, if you ask for them

Empty by default, so nothing changes unless you write it down:

    traps: [rune_thief, no_flask, runebear]
    trap_count: 8

- **rune_thief** -- half your runes, gone.
- **no_flask** -- your flask heals nothing for 20 seconds. You can still drink it; it just does
  nothing, and the charge is spent.
- **runebear** -- a Runebear appears exactly where you are standing. Kill it and you keep the runes.

Traps are sent to YOU by your own world like any other item, so in a multiworld somebody else may
well be the one who finds them. Asked for by **boblerrr**, whose line was *"enemy horde on your
head"*.

**Your seed does not grow.** A trap is filler and always filler -- no progression may ride one -- and
each one displaces exactly one junk item, so `trap_count` changes how much of your junk bites back
and nothing else. They are dealt round-robin rather than randomly: eight traps over two kinds is
four and four, every time, so enabling two never rolls a seed with seven of one.

The bear spawns at your own feet because that is the only point in the world we know for certain is
valid ground, and it is minted from `npc_param 46300010` rather than the family's template row, which
carries `getSoul 0` -- a player who survives the bear gets paid for it. The id came out of
`NpcName.fmg`'s `90 + <model4> + <variant3>` encoding (`904630310` -> model `c4630`), corroborated
against `NpcParam` and `NpcThinkParam`, because the number I started from was wrong.

**No contract move**, which is the opposite of what the design note in #114 predicted, and that note
is corrected in place. A trap rides the path Boss Keys already use: a feature that declares `ITEMS`
and no `ITEM_GRANTS` mints a synthetic item that never enters `_AP_IDS_TO_ITEM_IDS`, and the client
recognises it by name in the receive stream. No slot_data key, no version lockstep.

The client half landed as three pull requests -- a hotkey probe that fires Rune Thief and No Flask
without a seed, name-based recognition that also guarantees a trap is never *dropped* on the floor,
and the bear spawn itself.

### Charo’s Hidden Grave and the Stone Coffin Fissure are the Cerulean Coast now

Three regions became one, and the region count went 30 -> 28.

| region | locations |
|---|---|
| Cerulean Coast | 43 |
| Charo’s Hidden Grave | 26 |
| Stone Coffin Fissure | 21 |
| **merged** | **90** |

They are one contiguous stretch of the south-west coast -- the Fissure is entered *from* the
Cerulean Coast and Charo’s stands on it -- and each was far under the 100-location median on its
own, which is how a seed ends up keeping one of them and stranding checks in the others. Bucket
`6840` was Cerulean’s until an in-game kick measurement split it out on 2026-07-15; this returns it
with the geometry understood rather than guessed.

**Your check count did not change**: 4931 locations before and after. Only the labels and the region
draw moved.

### A check on a tile with no grace now names its own region

From a Nexus report by **YkaZel** (2026-08-09): *"items said to be in a certain region when they’re
actually in another ... ghostflame call being in Cerulean Coast when it should belong to Charo’s
hidden grave."* He was right, and the data that says so was already committed.

Only tiles that CONTAIN a grace were ever regioned directly -- 151 of the 325 overworld tiles bearing
checks have none -- so the rest were hopped onto whichever neighbour happened to hold one.
`m61_47_39` holds no grace, so its nine checks were filed on the Cerulean Coast graces next door.
`greenfield/play_region_buckets.tsv` has carried a row for that exact tile the whole time: bucket
`68400`, and `68400` is Charo’s. That table is PlayRegionParam itself, in the same id space the
client’s kick-watch compares against -- not a neighbour’s opinion.

Generation now consults it. On a seed that kept one of two adjacent regions and not the other this
was worse than cosmetic: the check either sat somewhere the game would not let you walk, or never
existed at all.

### The endgame was never on the scaling wire

The Ashen Capital is never *rolled* -- it is minted unconditionally at the end of every run -- so it
was not in the kept set and not in the spine, and every path in enemy scaling keyed on one of those
two. Its geometry has always existed and its region **lock** always worked; **scaling silently
skipped the whole endgame**, including play_region `19000`, the Elden Throne, where the goal fight
happens.

Measured from **boblerrr**’s 08-10/08-11 logs: across all seven seeds the scaling wire contained
`11050` or `19000` **zero** times, and the client said so nine times in as many words --
`region 11050/19000 is not in the sphere wire -- left VANILLA (no tier, no down-state)`. So on every
scaled seed anyone has played, the last fight was the one fight that was not scaled. The finale is
now appended to the order in both paths and takes the top of the band. Under `dlc_only` it does not
exist and is correctly absent. Raised as #545.

### Five graces came back, and an arena grace is now adjudicated per boss, not per map

`main` was withholding five graces that had already been ruled not to be arena graces -- three of
them merchant shacks:

| grace | why it is not an arena grace |
|---|---|
| 76118 Warmaster’s Shack | Bell Bearing Hunter is a **night-only** spawn |
| 76311 Hermit Merchant’s Shack | same |
| 76451 Isolated Merchant’s Shack | same |
| 76357 Primeval Sorcerer Azur | Maggie releases no grace on death; separate ledge |
| 76910 Behind the Fort of Reprimand | Black Knight Edredd is not a boss grace |

🛑 **Nothing caught it, and that is the load-bearing part.** The derived count went **UP**, 41 -> 47,
and the floor only guards a shrink. A count ratchet cannot tell a real new arena grace from a
regression that adds five.

The derivation underneath it was also claiming more than it knew. A tile marked *adjudicated* only
meant its map data had been unpacked -- not that every boss standing on it had been located -- so
"tile adjudicated, grace absent" read as *measured safe* when it meant *nobody looked at that boss*.
76931 "Shadow Keep, Back Gate" stands in front of Commander Gaius and was held back only by a hand
list that the standing plan was going to retire. Misses are now tracked per boss and named in the
file’s own header. Found while triaging **boblerrr**’s *"you forgot to give gaius grace in the
shadow keep"* -- which is not a bug: 76930 is boss-gated and 76931 is a correctly withheld arena
grace.

### Stormveil’s merchants are in Stormveil

A merchant’s stock flag is pinned to the region the merchant physically stands in -- but only when
the claimants for that flag resolve to exactly one region. A claimant that cannot be standing where
the table says did not add a wrong answer; it **silently removed the correction** and reinstated the
block guess the file exists to kill. 16 flags resolved to no region at all, 162 to several, and 53 of
those were wrong. Gostoc’s and Rogier’s Stormveil checks were filed in Limgrave and Liurnia (#556);
three spurious claimants, not one, were reaching across the map (#558).

🛑 The correcting issue was itself partly wrong and is corrected here: removing Merchant Kalé alone
fixes **zero** flags. Bell [5]’s rows have four claimants and the real one is the Nomadic Merchant in
Liurnia. The issue’s numbers came from a reimplementation of the tile lookup rather than from
generation’s own; these were re-derived with the real one.

### The spine region order is back, as `num_regions_order: vanilla_order`

Taking the first N regions in Limgrave-first order was removed on 2026-08-05 because it was the only
alternative to a random draw, which made every default six-region seed keep the same eight regions
and left nine base regions unreachable. That is a defect when it is the only behaviour and a feature
when it is chosen, so it returns as an opt-in. **`rolled` stays the default and its rng stream is
untouched, so every seed that does not name the option is byte-identical to before.**

It is **renamed**, because the name was the original problem: two shipped docs had called `spine` the
default (it was not) and said it decided where you *start* (it did not, and still does not -- that is
an independent size-weighted draw). `vanilla_order` names the order the regions are taken in, which
is all it has ever done. `spine` still parses -- it is registered as an alias, so old yamls in the
wild keep generating while the wizard, the spoiler and the option surface all say `vanilla_order`.

### The shipped connection template points at archipelago.gg, and a bad port no longer loops

The client ships with `archipelago.gg:PORT`. Every archipelago.gg room is assigned its own port at
creation, so no number could be correct in a template, and the *local* default `38281` sitting beside
`archipelago.gg` would have been a plausible-looking lie. `PORT` cannot be mistaken for a setting.

That is only safe because the client now treats a non-numeric port as **not connectable** and shows
you the connect form. Without it, `wss://archipelago.gg:PORT` fails to parse, the `wss` -> `ws`
fallback fails identically, and the player gets a retry loop of parser errors instead of somewhere to
type.

### Received spells are memorised now

The live half of spell auto-equip (#440) landed across this window, and it is the part `auto_equip`
never covered:

- **The slot chain the module taught did not land.** It shipped a hop marked *"confirmed twice,
  independently"* that resolves, on 1.16.2, into an object of UTF-16 strings and vtables -- and the
  widely used CE table reads the same garbage from the same offset, so it was never right rather than
  mis-transcribed. Found instead by signature search: walk every pointer field in `PlayerGameData`
  and require both a vtable inside the executable and a back-pointer into the parent.
- **Every spell now costs one memory slot.** 24 of the 213 memorisable spells cost more (three, for
  Comet Azur, Placidusax’s Ruin and Scarlet Aeonia), which meant placement needed bin-packing and a
  three-slot spell could not be placed at all until you had earned three. The slot cost is
  normalised in the same param row the requirement fields are already zeroed in.
- **A seal gets incantations and a staff gets sorceries.** The discriminator was already in the
  data: the spell classifier is four goods types because each school splits attack from support, so
  the sorcery/incantation split is one the code already made.
- **Spells that arrived before the build that could equip them are picked up.** The receive cursor is
  persisted per save, so a spell received under an earlier client sat in the bag unmemorised and
  always would have. Ordering comes from the Archipelago receive stream, which never changes.
- **The log says what the path did**, and the banner stopped claiming otherwise.

Raised by **boblerrr** with Ranni’s Dark Moon and Rotten Breath sitting in the bag with four memory
slots free.

### `no_equip_load` was writing a field the game never reads

The plumbing was fine the whole time, and both earlier investigations looked at it because that is
where the logs pointed -- the logs were telling the truth, the row *was* patched, the effect *was*
resident on the player. The field was the problem.
`allItemWeightChangeRate` takes exactly two values across all 11325 rows of vanilla `SpEffectParam`,
never once as a multiplier; `equipWeightChangeRate` is the one with real multipliers in it. Writing
the second makes the option do what it says. Confirmed in game -- max equip load read back at exactly
the multiple written.

🛑 **A roll mode (off / light / medium) is built on the client and not yet available to you**, because
the yaml half is still open as #548. A fixed multiplier cannot pin you to medium roll on its own --
roll weight is carried over max, and this raises the ceiling -- so the option ships with a readback
that proves which roll you actually got rather than a claim.

### An incoming DeathLink says so on screen

You would drop dead and the record of why existed only in a log file you were not reading, which
reads as the mod misbehaving rather than as another world’s death arriving. It now goes to both
surfaces the client uses for things you are meant to keep -- the toast catches you mid-fight, the
top-right feed keeps the history.

    DeathLink: killed by bobler

The source name is the one place a payload from another world reaches the screen, so it is sanitised
rather than trusted; a name with nothing printable in it renders as *someone*, not as `??`.

### A bell hand-in reaches the top-right feed

The merchant-bells notice was going to the bottom-left toast strip and stopping there, which is a
six-second window and not a record. It now reaches the client feed as well, like every other notice
worth keeping.

### A boss fight can be measured instead of argued about

Three scaling reports in a row -- *"2 bosses in one fight wildly different"*, *"one super squishy and
weak, the other insanely tanky"*, Gideon *"1 shots from 50 vigor"* and a sponge -- and **not one of
them is answerable from what the client used to log.** The scaling census describes our decision; it
says nothing about what the fight was. Two HP curves do. The client now samples player and boss HP
through a boss fight, roughly twice a second.

It is **on by default**, which took a correction: it shipped probe-gated and off, and the repo
already knew better -- an off-by-default probe silently cost a playtest round on 2026-08-08 when the
measurement simply did not happen. The same fix closed a hole where an explicit `ER_*=1` could be
overruled by a config file the developer may not have written; the documentation had claimed env
overrides config in both directions and the code only did one of them.

### The client log answers four questions it could not

All four came out of triaging the same player report twice -- the merchant-bell option that was
declared, documented, and never put on the wire. The one that matters is a **feature handshake**:
what the seed DECLARED, minus what actually ARMED, reconciled once per connect after every feature is
configured. It is a read-back, not a receipt: it reports what the client can observe about itself,
which is the distinction the original defect turned on.

### Under the hood

- The census of checks whose region is a **guess** rather than an answer, and a tool that
  point-in-volume tests the checks against play-region geometry the same way graces already were --
  importing that machinery rather than reimplementing it, so the two answers cannot drift apart.
  Nothing consumes the output yet; a disagreement is a question, not a fix.
- A worksheet of the 83 bosses standing between us and 395 ambiguous checks, and the distance from
  each check to the nearest boss arena spawn.
- The yaml lint’s rune-cap guard was reading the option key from before a rename, so it never fired
  once.
- A scaling spot-check hard-coded a region label that the Cerulean fold moved, so the test went red
  while the code was right; it now derives the label instead of naming it.
- The submodule pin, the Tier-1 regen precondition in AGENTS.md, and witnesses for two tests that
  could previously pass without observing anything.
- The F6 tracker sizes its window to its content and floors it every frame, its sweep rows say when
  a region is unreachable rather than leaving a group looking stuck, and a group that has already
  paid out clears itself.
- A Region Lock now says whether it **warps you in** or only **admits you** -- two different things
  that read identically in the client feed.

### Published

`release/CHANNELS.tsv`: **stable -> v0.3.10**, beta -> main for this window. Two appended rows, no
edits, per the file’s own rule. Both were owed when the window opened on 2026-08-10 and are paid
here.

### 🛑 Everything above this line was note debt, and the gate was green throughout

`check_release_notes` asks whether the OPEN version has a dated changelog section and a non-stub
blurb. Both were true from the moment the window-opening commit wrote them, so **every merge after
the first one landed note-free with a green gate** -- Rule 14 is enforced for the first change in a
window and unenforced for all of them after it. Thirty-nine merged pull requests across the two
repos had no note when this sweep started -- eighteen in the world, twenty-one in the client.

The detection is one command and nobody runs it:

    git log --oneline -1 -- release/CHANGELOG.md release/BLURB-v<n>.md
    git log <that>..main

Anything in the second list is note debt. Run it before the tag, and treat a green
`check_release_notes` as evidence of nothing. A gate that could close this would compare those two
sets; it does not exist yet.
## v0.3.10 — 2026-08-09

Window opened AT THE TAG of v0.3.9, deliberately -- the second time running, after five windows that
were opened by something going red. Nothing has landed past the tag yet, so this section starts empty
of changes on purpose and fills as they arrive (rule 14).

`CONTRACT_HASH` is unmoved at `5c2b9bf2`. The bump is version-lockstep, not a contract change, so a
v0.3.9 client still handshakes -- including a seed with grace attunement on, which is the one setting
v0.3.9 made version-sensitive.

### A bossless map's checks now reach their region's sweep pool

bobler's Shadow Keep paid **one** check for Commander Gaius. His seed also kept 36 West Rampart
checks that no boss sweep could ever grant, and the two facts were the same bug.

A sweep group's members come from two pools: the boss's own map, then a round-robin share of what is
left in the region. That second pool is the one meant to cover checks no particular boss owns -- and
a map with no boss standing on it was excluded from it, *because* it had no boss. m21_02 (West
Rampart) hosts no healthbar boss, so its filler never entered Shadow Keep's remainder, the remainder
came out at 5 instead of 41, and the four DLC overworld bosses folded into Shadow Keep -- Gaius, the
Scadutree Avatar, the Tree Sentinel, the Fallingstar Beast -- had nothing to be topped up with. They
own a tile each and no building, so their own map pool is one or two checks. That is the 1.

The membership gate now asks whether a check sits on an interior map, rather than whether some boss
happens to live there. Shadow Keep's tile bosses go from 1-2 checks to 5-7, Siofra River picks up 13,
and 49 checks stop being discarded. Group sizes elsewhere are unchanged and no group was gained or
lost (219 triggers either way).

**This is not a rebalance, and it should not be read as one.** The remainder is dealt in equal
slices, so Messmer and the Golden Hippopotamus gain five each alongside Gaius; dealing to the emptiest
boss first fixes the order, not the size. A DLC-only seed still ships most of a region behind one
kill -- Belurat is 82 of 93 checks behind the Divine Beast Dancing Lion -- because that region has
exactly one boss to hang them on. That is a separate argument.

### A DLC-only run now ends on Promised Consort Radahn

`goal: auto` on a `dlc_only` seed used to end on whatever terminal region your draw happened to
keep. That was not a malfunction, it was an asymmetry: the base game's ending is guaranteed because
the Ashen Capital is NOT a region you can roll -- it exists on every base-game seed and is reached
by warping to its own graces -- while Enir Ilim is one of the thirteen ordinary DLC regions. Miss it
in the draw and the run ended somewhere else. bobler finished one this week on Romina in the Ancient
Ruins of Rauh and reasonably read the early goal as a broken ending.

Enir Ilim now behaves the way the Ashen Capital does, in the two ways that decide an ending: it is
**barred from the draw** and **always kept**. So `num_regions: 3` on a DLC-only seed means three
regions to play plus the ending, rather than three regions and a lottery -- and the gen log says so
in the line that already explains where your regions came from.

It stays a real region with its own checks and its own Lock, because it is a place you play. The
Ashen Capital is ten checks and a gauntlet; that is why it is not one.

### Enir Ilim can no longer be the region your run OPENS on

The same seed that ends in Enir Ilim could also start there. `goal: promised_consort` has force-kept
it since v0.3.5, and nothing stopped the start-anchor draw from picking it: measured over 20,000
draws on the previous build, **14.7%** of `num_regions: 6` seeds opened on the region they were
supposed to end in, rising to **59.6%** at `num_regions: 1`.

Two bars existed and neither covered it. One names the base-game goal region specifically
(Leyndell), the other bars gated children like the capital, and Enir Ilim is neither. The rule is
now the general one -- whatever regions your goal force-keeps, the run cannot open on them -- so
`auto` and a named goal are covered by the same line.

**Compatibility.** Seeds with the base game in play are byte-identical, including their rolls: the
new force-keep and the new bar are both empty there. DLC-only seeds re-roll differently, because the
draw is now made from a pool that no longer contains Enir Ilim. `CONTRACT_HASH` does not move and no
client change is needed.

### The v0.3.9 SHIPPED row was owed, and main was red without it

To be honest about the "deliberately" above: `test_every_tagged_version_is_recorded_as_shipped` had
been RED on main since the tag. v0.3.9 was tagged, carried a `CONTRACT-VERSIONS.tsv` row, and had no
`SHIPPED` entry in `test_gf_contract_versions.py` -- so something red WAS waiting either way. Added
here with the hash it actually shipped, `5c2b9bf2`.

That is the fourth window running where this one row is the last thing anybody remembers: 0.3.3,
0.3.4, 0.3.6 and now 0.3.9. The streak is only visible because the test asks `git tag` rather than
asking a person, and it is only red at the right moment because `tests.yaml` fetches tags. Both of
those were fixes to earlier misses in the same series.

⭐ 0.3.9 is also the first 0.3.x whose SHIPPED hash differs from the one its window opened on: it
opened version-lockstep on `d7d3a58e` and then took `graceAttunement` while open, which is exactly
what `test_shipped_contract_hashes_are_never_rewritten` allows -- it freezes SHIPPED rows, and a
window has no SHIPPED row until it is tagged.

### First double-digit patch component, and the ordering was checked rather than assumed

`0.3.10` sorts BEFORE `0.3.9` as a string, so this is the release where a lexicographic comparison
would start quietly answering backwards. Audited before the bump:

* `tools/check_channels.py::_ver` parses to an int TUPLE and `max()`es tuples -- correct.
* `check_contract_version`, `check_version_sites`, `check_release_notes` and `contract_gen.rs`'s
  `APWORLD_VERSION_EXPECTED` all compare versions for EQUALITY, which is order-free.
* The only string sorts left are cosmetic: the printed `--derive-history` table and a couple of
  `sorted()` calls over dict items for stable output.
* Archipelago's own `tuplize_version` (which is why `release/CHANNELS.tsv` exists in its current
  shape) parses `0.3.10` fine -- it is a strict `X.Y.Z`, which is the only property that file needs.

Nothing to fix, but it is worth having the answer written down BEFORE the first bug that would have
come from it, rather than after.

### The client half was one PR, not two

The recipe on file says opening a window is a five-step serial chain across two repos with FOUR
merges: client `Cargo.toml`/`Cargo.lock`, then the world bump, then `contract_gen.rs` regenerated
against the merged world, then a second gitlink bump. The reason given for the split is that
`APWORLD_VERSION_EXPECTED`'s value "does not exist until the world bump exists".

That is true of the value's SOURCE and false of the value. `gen_contract.py` generates it from a
WORKING TREE, and the client repo's CI has no gate that reads the world at all -- `test.yaml` builds
and tests, and there is no `contract_gen`, `gen_contract` or `er-archipelago` reference anywhere in
its workflows. So all three client files moved in one PR (clients#121) and this world commit pins the
gitlink at its merge, which is what lets `generators` go green on the first attempt instead of the
third.

🛑 The drift window is unchanged in kind and shorter in practice: between the two merges a client
built from `main` expects an apworld that is not tagged yet. Nothing ships from `main`.

### The client half of this window was five merged PRs behind, and none of it was shipping

The gitlink pinned client `f650aa0`; client `main` was `2f0d4a1`. Between the v0.3.9 pin
(`cfe6ca2`) and `f650aa0` there were exactly two commits -- the version bump and its merge -- so
**nothing client-side had shipped since v0.3.9** while five PRs sat merged. This bumps the pin to
`2f0d4a1` and writes the notes those five owe, in the same commit, which is what rule 14 asks for.

🛑 Worth naming because "merged to client main" and "ships in the open world version" are different
facts and only the gitlink decides. `check_release_notes` cannot see the difference -- it gates that
a section EXISTS, not that it covers what the pin actually moved.

### Enemy scaling reads the ground from a table instead of re-measuring it every sweep

An enemy vanilla ships with no ladder rung -- every named boss, every hand-tuned NPC -- has no
strength we can read off the enemy itself, so the sweep asks how hard vanilla thought the GROUND was
and places it against that. That reading came from a live census over loaded enemies, and the census
counts enemies carrying a vanilla rung AND a band while **our own sweep strips the band**. It erased
its own sample: a region answered once, then answered nothing forever after.

Harmless for the enemies standing there at the time -- they leave the first sweep carrying a rung or
a down state, and both re-derive on every later sweep. Fatal for anything that arrives LATER, which
carries neither and falls through to "leave it exactly as vanilla shipped it", at full strength, in a
region we had already decided was too strong.

Measured in a 2026-08-09 log: one overworld bucket answered `from 0 vanilla-shaped` on **33 of 48
sweeps**, and its count of untouched enemies never converged -- it sat between 122 and 214 for three
hours. A small interior map in the same seed reached zero. That size difference IS the bug: a bounded
map is finished in one pass, a streaming overworld tile keeps loading cells whose placement evidence
the first pass destroyed. It reads in play as "this region feels harder than a region the ramp put
ABOVE it", which is exactly how it was reported.

The ground is a property of the map, so it is now measured offline -- enemy placements joined to
`NpcParam.spEffectID3`, reduced per play_region bucket with the **same** weighted median the live
census uses -- and shipped as a table. Correct on a region's first sweep, and on a save loaded into
ground that is already settled. The census still runs: it is the log's live sample and the fallback
for the 13 buckets the table makes no claim for.

⭐ It reproduces two independent live readings from static data: Liurnia measured 5 against a
recorded 5, and Altus measured 7 against a recorded 7 off a 302-enemy sample. Altus was not in the
acceptance set. Both are pinned as tests.

🛑 DLC buckets are ranked WITHIN the DLC ladder and projected by rank, because the two ladders are
disjoint bands -- the base ladder spans 1.141x to 7.422x HP and the DLC one starts at 7.047x and runs
to 16.641x, overlapping in a single rung. There is no multiplier mapping between them, so a DLC tier
and a base tier are not comparable to each other; each is only ever compared against its own region's
target. Nothing pools them today and nothing should.

🛑 The table is a SAMPLE, not a census: `PlayRegionParam` names only a subset of each overworld
bucket's tiles, so 61% of enemy placements land in no bucket at all. The median is robust to that and
two regions matched their live readings, but it is an estimate over 39% coverage.

`tools/gen_area_tiers.py --check` holds the client's committed bytes to `greenfield/area_tiers.tsv`
in CI. Without it the table would be a hand-maintained file in another repo -- `client-main-drift`
would not have caught that, since it only re-runs the region-lock and contract generators.

### Opening a merchant announces its Archipelago checks as hints

Opening a merchant's buy menu now hints every check on that shelf that would send its reward to
**another player**, once per location per session, one packet per open. Your own rewards are not
hinted: a hint for an item already yours, on a shelf you are looking at, tells the multiworld nothing
it can act on and tells you nothing the screen is not already showing.

🛑 A row whose ownership the client cannot resolve is hinted rather than skipped. Silence would be
indistinguishable from "not a check", and the failure directions are not symmetric -- a spurious hint
is noise, a missing one is a player waiting on something nobody can see.

🛑 **This has not been playtested at a live merchant.** The trigger was validated against one real
session and the decision half is host-tested, but the two have never been run end to end in front of
a shopkeeper. Grep a client log for `shop-hints:` if it misbehaves.

### The tracker no longer names a region you have not unlocked

Every kept region was listed by name at connect, locked or not -- so the region draw, which IS the
seed's shape, was readable before the run started. A locked region now renders as `Locked region`
with its count masked and its rows withheld.

Three things had to go, not one. The name; the **counts**, because the thirteen DLC region sizes are
all distinct and `0/85` identifies a region as surely as its name does; and the **row list**, because
our location names carry the region as a `<Region> :: ...` prefix. Concealed rows also sink to the
bottom -- left in alphabetical order, a masked row between Belurat and Roundtable Hold narrows its
own initial to C..R.

The hint-lock button stays on a concealed row on purpose: buying blind is what turns `Locked region`
into a name, and hiding it would leave the lock-hint economy with nothing to sell.

### The client log now names the goal instead of counting it

It logged `goal: 1 location(s)` -- a count. The generator already logged the answer, but the artifact
that reaches us when a player reports a bad ending is the client log, not the generation log.

Motivating case, 2026-08-07: a `dlc_only` seed goaled on Romina and the player read the early ending
as broken. Nothing had malfunctioned -- Enir Ilim is an ordinary rollable DLC region while the Ashen
Capital is not, so `goal: auto` ended on the deepest terminal region his draw kept -- but establishing
that took his slot_data, because his log could not say which boss the goal even was. It now names the
region and the location, and declines to name one when the resolved names disagree.

### Published

`release/CHANNELS.tsv`: **stable -> v0.3.9**, beta -> main for the new window. Two appended rows, no
edits, per the file's own rule.

### Your Region Locks can now end up in other players' games

They could not before, and nobody had noticed, because nothing FORBADE it. `local_items` genuinely
leaves Region Locks free to travel -- the option's own docstring says so -- and they still never
went anywhere. Locality here was a PLACEMENT, not a rule: `progression_surface` pulls every one of
your own progression items out of the multiworld pool before the general fill and places them on
your own vetted checks. Only what it could not host went back to the pool, and it always could:
~170 hosting locations against a ceiling of 36 items. The escape hatch existed and never opened.

Measured on the previous build: **0 of 105 placed Locks reached another world** across eight
two-player seeds, and **0 spill across 146 world-instances**. In the same seeds, 49.2% of everything
else crossed worlds -- so the measurement was not blind, Locks specifically did not move.

**New option: `progression_bias`, 0-100, default 0.** It is the share of your Locks reserved for
your own Progression Surface. At the default nothing is reserved, and in a two-slot Elden Ring
multiworld **44.4%** of Locks are placed in the other player's world (108 placed, 48 away, four
seeds). 100 pins every Lock at home, which is exactly what previous versions did.

**A travelling Lock is still curated.** It is held to the same Progression Surface everyone's
progression is held to, so it lands on somebody's boss or remembrance rather than on a random
crafting material. The knob that trades the curation itself away is still
`confine_foreign_progression`, and it is deliberately a separate one -- lowering the bias changes
WHOSE surface your key sits on, not whether it sits on one.

Being stuck waiting on another player is the intended consequence, not a side effect.

⭐ **What a tracker star means is correspondingly weaker**, and the client's wording has not caught
up yet: the starred set is "a progression item can be here -- yours or another world's", no longer
"your Locks are somewhere in here". `confine_foreign_progression` keeps every other player's
advancement on that exact set, so it still bounds real progression.

Cross-game is untouched: the placement pass only sees Elden Ring worlds, so a Lock bound for a
Hollow Knight slot is simply one it did not place -- it goes to the general fill and lands anywhere.
`CONTRACT_HASH` does not move; no client change is needed.

🛑 The placement lives in `stage_pre_fill` rather than in an item rule, and that is not a detail.
The first implementation was a rule barring released Locks from non-surface checks. It produced the
same distribution and had NO SPILL, so three different seed shapes -- a narrowed surface,
`num_regions: 1`, and a shifted filler pool -- each failed to generate, and each was missed by a
different capacity threshold. Capacity was never the constraint: reachable capacity in sphere order
is, and no count of open slots can see it. A real fill can, because it just tries, and what it
cannot place spills. A seed can now lose curation; it can no longer lose generation.

### A frozen setting could crash the spoiler at the very end of a successful generation

Some settings are frozen -- they used to be yaml knobs and are now simply the behaviour -- and they
are represented by a stand-in that deliberately refuses to answer questions it was not built for, so
a degraded read announces itself instead of looking like absence.

It refused one question too many. Archipelago's own spoiler writer walks every setting on every
world and asks each one whether it should appear in the spoiler; the stand-in did not carry that
answer, so it raised -- from inside the spoiler write, with the seed already filled. All the work
done, then the write fails. Found by yaml fuzzing on `start_with_whetblades`; it predates the
release that found it.

The stand-in now answers, with "not visible", which is what a frozen setting is: not a choice you
have, so not a choice a spoiler should record as one. `FROZEN_OPTIONS` remains the record of what
the behaviour actually is. Measured: 60 fuzzed yamls that previously crashed once per twenty now run
clean.

Its error message also blamed the wrong place. It said a FEATURE had read the attribute, which sends
you looking in this repo when the reader was Archipelago; it now names both.

### The CI multiworld-smoke SKIP branch was dead code

The step captured its exit code on the line after the command. GitHub runs those blocks under
`bash -e`, so a non-zero exit aborted the step before the assignment -- the "partner world absent, so
skip" tolerance had never once been reachable on Linux, and a skip was indistinguishable from a
failure. It never bit because CI checks out upstream in full and the partner is always there.

## v0.3.9 — 2026-08-08

Window opened the same day v0.3.8 shipped, and opened by a RED GATE rather than by anyone
remembering: `check_release_notes` refused the first commit to land past the tag, because
`APWORLD_VERSION` still named a version that had already been published. That is the gate doing
exactly its job -- v0.3.8's notes had two commits' worth of changes written into a section a player
would read as shipped -- and it is worth recording next to the v0.3.8 entry, which had just finished
celebrating the first window in five to be opened on purpose. One swallow.

`CONTRACT_HASH` MOVED under this window: `d7d3a58e -> 5c2b9bf2`, added by grace attunement below.
The window OPENED as a version-lockstep no-op and stopped being one, which is exactly what an open
ledger row is for -- `test_shipped_contract_hashes_are_never_rewritten` freezes SHIPPED rows only, so
a window may take on a contract change right up until it is tagged. A v0.3.8 client still handshakes
with everything here EXCEPT a seed that turns grace attunement on: that seed refuses an old client
rather than connecting and silently dropping the setting.

### Two things the v0.3.8 tag broke on its way out

**A regen on the Windows box cannot produce the input hash CI expects, and one got committed.**
`test_D_freshness_vs_disk` recomputes the manifest from the repo tree; the box's answer and CI's
differ by 593 declared inputs (the raw `.dcx` event binaries -- the committed bundle carries the
decompiled form) plus `gen_data.py` itself differing in bytes at the same path, which on a Windows
checkout is line endings. Neither is fixable by regenerating harder; they are two legitimate input
sets. The generated CONTENT was byte-identical either way -- all eleven module `body_sha256` values
and every count unchanged -- so the bundle-derived stamp was restored and nothing was lost. The rule
this leaves behind: regenerate on the box if you like, but commit the bundle-derived stamp, and land
it through a pull request so the gate runs before `main` sees it.

**The shipped ledger owed the tag its row.** `"0.3.8": "d7d3a58e"`, added. The comment it replaced
predicted it in as many words, and the fixture now says the same thing about 0.3.9, because it will
be true again.

### The progression-surface option had two names for one thing, and one of them was narrower than its own members

**`Shop` was not a superset of `ShopNonSpell` or `ShopSlot`.** Two predicates answered "is this check
a shop row?" and they disagreed on 35 rows: `ShopNonSpell`/`ShopSlot` were derived from the
detectable stock FLAG, while the `Shop` tag came from the `method` column of a csv. So selecting
`Shop` in `progression_surface` -- expecting "every merchant" -- gave you 28 checks FEWER than
selecting `ShopNonSpell`, and there is now one predicate for both.

That gap was also a hole in an exclusion, and in a sweep. `Roundtable Hold :: Mohgwyn's Sacred Spear
- from Finger Reader Enia` could host progression while all 26 of its neighbours in the same Enia
stock list were correctly barred as buy-only. And felling a Liurnia catacomb boss auto-granted six
of Preceptor Seluvis's sorcery shop slots, because the rule that keeps merchant stock out of dungeon
sweeps was reading the narrower tag. The sweep corpus drops 3691 -> 3685: six of Seluvis's rows, and
nothing else.

**The surface grid in the options wizard now says what it selects.** The 16 classes are tag names,
and several actively mislead: `Church` is the 13 Sacred Tears, not "church locations"; `Basin` is
Crystal Tears; `Seedtree` is Golden Seeds. They rendered as raw keys in alphabetical order, which
also scattered the four boss classes across the grid. They now render with player-facing labels and
one-line hints, grouped by family, with the key still shown small beside the label for anyone
hand-editing a yaml.

The keys themselves are UNCHANGED, deliberately: Archipelago raises on an unknown option key, so
renaming `Church` would hard-fail every yaml already in the wild rather than degrade. Renaming them
with the old names kept as deprecated aliases is a separate change.

**And the grid now tells you when a box adds nothing.** Most of these classes contain each other, so
ticking `Boss` silently makes `MajorBoss`, `LegacyBoss` and `FieldBoss` no-ops, and `MajorBoss`
already covers every `Remembrance` and `Great Rune` check. The lattice is derived from the location
data on every build rather than written down -- because it HAD been written down, in a comment in
`contract.py`, backwards, for months. It claimed `MajorBoss` was a subset of
`Remembrance`/`GreatRune`; it is their superset.

**And every box now shows what it is worth.** Alaric's read of the above was that it points at a
hierarchical selector rather than a flat grid, which is the right instinct about the grid and the
wrong shape for the data: measured over the live tags, 10 class pairs nest but **sixteen overlap
without nesting** -- `MajorBoss` and `LegacyBoss` share 22 checks with neither containing the other,
`MajorBoss` and `FieldBoss` share 10, and 9 `Boss` checks are in none of its three sub-classes. An
indented tree would draw those as separate branches, which is a picture of something untrue.

So the grid answers the question instead of teaching the topology. Each box carries its MARGINAL
contribution -- what ticking it would add, or for a ticked box what unticking it would cost -- above a
running "locations that can host progression" total. Zero means "carrying nothing" on either side of
the checkbox, which is exact under overlap, nesting and disjointness alike, because it is set
arithmetic rather than a claim about shape. It is DLC-aware: a base-game seed does not get offered
"+39 Scadutree Fragments".

Nothing new is shipped to compute it. `wizard/region-census.json` already carries per-region counts
keyed by the FULL tag combination each check holds, which is exactly what makes overlap safe to add
up. The numbers land on `greenfield/surface_confidence.tsv`'s `eligible` column for all 16 classes and
on its headline hosting figure for the default -- and that file is pinned to
`progression_surface.allowed_ap_ids`, so the chain is wizard JS == Python == surface_confidence ==
allowed_ap_ids. The number a player chooses on is the number the fill obeys, and
`check_wizard_keymeta_js.py` asserts every link.

`greenfield/surface_confidence.tsv` gains a `tag_excluded` column. Its `total` was already filtered
and the filter only lived in prose, which is enough to make two honest numbers on one page look like
a defect -- it did, during this work.

### `Boss` was reading one of two reward mechanisms, so it named 143 checks instead of 214

A boss's reward reaches the player more than one way, and the `Boss` location class was derived from
only the first. Measured over the 244 boss-healthbar rows: **65** award through the common handler that
carries both the defeat banner and an `itemLotId`; **104** award off a reward flag the map's own event
script flips; **75** through neither. The first two sets are **disjoint** — zero overlap — so 104
bosses whose drops had already been datamined were never attributed to the class.

Nothing new was extracted. The same table's `BOSS_REWARD_TILE` has been feeding the tile decoder and
the LegacyBoss/FieldBoss geography join for weeks; only the tag predicate wasn't reading it.

`Boss` **143 → 214**, `LegacyBoss` 31 → 42, `FieldBoss` 92 → 95, `MajorBoss` unchanged. 62 of the 71
new checks were previously untagged filler. Location count is unchanged at 4931, so no check moved id.

Three consequences worth stating plainly:

**Eight checks left the filler sweeps, and that is the fix, not the cost.** Talisman Pouch at the
Divine Tower of Caelid, the Gargoyle's Greatsword on the Underground Roadside, Noble Sorcerer Ashes at
the Elden Throne and five more are boss drops; a filler sweep should never have been handing them out.
Sweep corpus 3685 → 3677, with 60 checks re-owned between triggers and **none crossing a region**.

**Three checks entered a dungeon sweep pool and were deliberately allowed.** Omenkiller Rollo's drop,
the Flamedrake Talisman at Groveside Cave and the Sewing Needle at Coastal Cave are each swept by the
trigger of the very boss that drops them. Filtering those would mean killing a boss no longer grants
its own reward. The ratchet that guards this now derives the exemption from the reward table instead of
listing ids, and all six pre-existing debt rows still fail it — so it got sharper, not looser.

**The reason for having no `Underground` class has expired.** It was "only three catacomb bosses drop
an AP-tracked check". It is now **60**, because the mechanism just attributed is the mini-dungeon
reward family. "Exclude the catacombs" is expressible for the first time. Whether to offer it as a
17th class is a separate, player-facing decision and is not taken here.

Still not "every boss": the 75 rows covered by neither mechanism remain untagged. Dryleaf Dane is one
of them — his gear is an asset pickup rather than a boss drop, and its check exists today with no tags
and no item name.

### The decompiled talk ESD was in the bundle but was never a declared input

`gen_inputs.py`'s walk spec has carried `("talk", None, "*.py")` since 2026-07-27 -- 365 files, 9.4 MB
of the db's 1452 -- but `gen_manifest` never DECLARED it, so a talk corpus that changed, or that was
only partly decompiled, could not invalidate the stamp. Same reasoning already written one list up for
`boss_reward_lots.py`: `gen_data` reads it, so omitting it means a stale copy passes.

🛑 The corpus IS currently partial, and that is the point. `gen_data`'s own gesture refusals say so out
loud. Declaring it is what makes an extended decompile move `inputs_hash` and force a regen, rather than
silently widening what the datamines can see while every stamp still claims to be current.

No data change: all 11 module `body_sha256` values unchanged, only `inputs_hash` moves (`27a5f697` ->
`e17cf5d7`) plus the three HTML views that embed it. Regenerated in the order #481 taught -- source
edits, then `gen_data.py`, then the HTML builders.

⚠️ Its stated MOTIVATION was wrong and the next change corrected it. It claimed Metyr's prerequisites
"could not be verified from the ESD" because Ymir's script is absent from the talk corpus. They were
never an ESD question -- flag 9440, its two prerequisites and the door are all EMEVD, all already
bundled. The gap was inferred from a failed search rather than established. Declaring `talk/` is right
on its own merits; the Metyr case is not evidence for it.

### Metyr's door waits on a flag that crosses a region boundary

Metyr (`25000800`, `m25_00`) is reached through an ObjAct on the Cathedral of Manus Metyr's overworld
tile, and `m61_51_45`'s event `2051452600` enables it only when both `EventFlag(9440)` and
`EventFlag(2051450180)` are on. `common.emevd` sets 9440 only after a conjunction of two OTHER tiles --
and 🛑 **those two tiles are in different regions**: `2053460600` is `m61_53_46` (Scadu Altus),
`2050400600` is `m61_50_40` (**Jagged Peak**).

So a seed that keeps Scadu Altus and seals Jagged Peak can never set 9440. The door never enables,
Metyr's remembrance (`510550`, `Remembrance` + `MajorBoss`) is unreachable while AP believes her region
is open, and fill can strand a region Lock on it. `start_grace` now forces 9440. Same shape as the
Radahn festival beside it, except the dependency crosses a REGION boundary rather than merely sitting
outside one -- if anything easier to hit, since Jagged Peak is separately keepable.

🛑 Only 9440 is forced. The other half, `2051450180`, is Ymir's own state on the cathedral's own tile
(the `chrEntityId` threaded through `m61_51_45`'s `90005790..93` NPC lifecycle events), so any seed that
can reach the door sets it naturally. Forcing an NPC-lifecycle flag would risk his presence and his shop
for no reachability gain; the cross-region half is the entire defect. Same reasoning the Radahn entry
uses in forcing the festival rather than Blaidd's flag.

### 29 checks shipped as `check`, and every one of them had already been resolved

Second half of the Dryleaf Dane thread -- the first half attributed his KIND of boss, this one gives his
drop a name. 38 live locations across 29 flags shipped with no item name, and `tools/sweep_unnamed_items.py`
had already written "Dryleaf Arts with Ash of War: Palm Blast" for flag 400730 into
`greenfield/unnamed_item_sweep.tsv` on 2026-07-27, while the world shipped that same check as
`Scadu Altus :: check - around Liurnia Lake Shore [f400730]` -- no item, and a descriptor naming a lake in
the wrong half of the map. That is not missing data. It is a resolver that lived in a tool and was needed
in the generator.

NEW `tools/item_naming.py` carries the three rules and BOTH callers import it, so the worklist and the
world cannot disagree again. All three were settled by reading params, not by inference:

1. category -> `EquipParam` table is MEMBERSHIP, not FMG name-matching (name-matching gets category 3
   wrong on id collisions);
2. weapon ids carry the upgrade level, so `id // 100 * 100` is a safe strip;
3. category 6 is `EquipParamCustomWeapon` -- a weapon + Ash of War pairing, which is why those ids
   resolve in no FMG at all.

**29 checks named**, 4931 locations unchanged: Scepter of the All-Knowing, Igon's Greatbow with Ash of
War: Igon's Drake Hunt, Dueling Shield with Ash of War: Shield Strike, ten Swords of Light, ten Swords of
Darkness, Beast Claw with Ash of War: Savage Claws, and Dane's Dryleaf Arts. Two further renames are
ordinal shifts, not overrides -- newly-named siblings now share an item name, so the disambiguator
numbers them. ONE check is still `check` and stays honest about it.

Four things made loud rather than convenient:

* **It never overrides a curated name.** `region_map`'s own name wins; this only fills blanks. Of 31
  renames, 29 were `check` and 2 are ordinals.
* **The category vote must see the whole corpus.** A 4-row probe voted `3 -> Weapon` and then refused to
  name a Protector id; it is trained on every `(category, item_id)` pair in `FLAG_LOTS`, once.
* **Category 6 was mislabelled by the vote itself** (`6 -> Protector` on id collisions). Rule 3 runs
  first so no name was corrupted, but the printed map was a false statement about the game. The custom
  table now votes too and it reads `6 -> CustomWeapon`.
* **Multi-lot flags name after the first slot we CAN name**, not the first slot. Flag 400281 takes
  "Scepter of the All-Knowing" over a sibling that resolves only in the wrong family. A confidently-wrong
  name in front of a player is worse than naming the sibling you are sure of -- which is why the worklist
  and the world may legitimately print different names for one flag.

The worklist emptied itself, 38 rows to 0, because the work got done. An empty tsv holding only a comment
block reads exactly like a crashed emit, and this repo treats an empty result as a failure until proven
otherwise, so the tool now writes the SOLVED state into the file.

### Grace attunement -- a region hands over one grace, the rest bloom on touch

Unlocking a region lit its ENTIRE grace bundle at once, so the warp network arrived fully built and
traversal collapsed to a menu. Two new options:

    grace_attunement         Range 0..10, default 0 (OFF -- byte-exact no-op)
    grace_attunement_anchor  front_door (default) | random_grace

On unlock the region hands over ONE grace and holds the rest until the player has physically touched
`grace_attunement` of them, at which point the region blooms. The anchor is `REGION_OPEN_FLAGS[region]`
-- the region's own front door, so the player always arrives somewhere sensible. `random_grace` picks any
of the region's graces instead, which can drop you deeper in and cuts more traversal; `REGION_GRACE_POINTS`
already excludes boss-gated and arena graces, so every candidate is a real, physically-present warp point.

🛑 **SKIPPED for small regions**, and the boundary is `<=` on purpose. A region with exactly `threshold`
touchable graces would attune only on its very last one and then bloom NOTHING; below that it could never
attune at all and its remaining graces would stay dark for the whole run, which reads as a bug rather than
a setting. At threshold 4 this gates 16 of the 28 bundled regions and skips 12.

🛑 **A withheld bundle is never gated.** Gated children (`REGION_PARENT`) emit `[]` while their vanilla
wall is armed, and handing one an anchor would put a warp target on the far side of a wall the game
enforces.

⭐ The random anchor is MEMOISED on the world, because `fill_slot_data()` is called more than once and an
inline draw made slot_data non-idempotent: the second call rolled a different anchor, so a caller reading
`region_graces` from one call and `grace_attunement` from another saw one grace duplicated and one lost.
Caught by the conservation test, which did exactly that by accident. `test_slot_data_is_idempotent` now
pins it in both anchor modes, and the draw only happens when the option is ON -- pulling from
`world.random` on a default seed would move the rng stream and change every rolled seed in existence.

`CONTRACT_HASH d7d3a58e -> 5c2b9bf2` (`graceAttunement`). The client half landed first (clients#119); a
gitlink can only point at a commit that exists. Suite: 30 failed / 1708 passed / 174 skipped, the SAME 30
as the branch point, so zero delta; the attunement file ran 5x green because the anchor is draw-dependent.

## v0.3.8 — 2026-08-07

Window opened 2026-08-07, at the tag of v0.3.7 and because somebody remembered rather than because
a gate went red. That is the first time in five windows, and the v0.3.7 notes had just finished
saying it had never happened.

`CONTRACT_HASH` is unmoved at `d7d3a58e`. The version bump is lockstep, not a contract change.

### Beta and stable channels, so the page and the download agree

Three places publish this project -- the GitHub tag, the wizard on peliarch.ca, and Nexus -- and
only the first was pinned to anything. On the morning of 2026-08-08 all three were different builds,
and the newest of them was the one strangers were being pointed at: the live wizard offered 44
options, the newest tag had 42.

**That is worse than "the site is a bit ahead", because Archipelago does not refuse a yaml carrying
an option your apworld has never heard of.** Measured on 0.6.7: it prints one line, in the middle of
about fifty unrelated `Could not load world` lines, and generates the seed **without** the option.
Exit 0. So a player on the released build sets `keep_local`, gets a seed, and their consumables
travel to the multiworld anyway, with nothing anywhere to say why.

**Stable is daily**, which turns out to be the cadence this project already had rather than a new
promise: 30 tags from v0.1 to v0.3.7 over 34 days, median gap **0.82 days**. So the release cadence
was never the problem -- v0.3.7 was cut the day *before* the skew was noticed. Nothing tied the
wizard deploy to the tags.

* **The channel is a POINTER, not a version suffix.** `0.3.8-beta.1` is not available to us:
  Archipelago calls `tuplize_version()` on `archipelago.json`'s `world_version` when it loads an
  apworld, and that raises on any prerelease form, so a suffix is a load-time crash rather than a
  label. `release/CHANNELS.tsv` names which tag each channel is on; promotion is a new row.
* **`/er/` now serves the wizard built at the stable tag, `/er/beta/` the one at `main`**, both via
  `tools/deploy_wizard.sh`. The page works out which it is from its own URL and banners itself, so
  nothing edits the HTML. A copy opened from `file://` shows no banner: a page that cannot tell
  should not claim.
* **Every wizard yaml carries the pairing** in `description:`, which is the one field that reaches
  the generation log and the multidata -- a comment would reach nobody.
* **The bare `eldenring.apworld` finally exists.** `DISTRIBUTION.md` has promised it since v0.2, on
  the grounds that making a host download a game-mod DLL to generate someone else's seed is
  "friction for nothing"; it never shipped, because the packer was PowerShell on one machine. It is
  **1.3 MB** against the player bundle's 123.7 MB, and the release job proves it generates a real
  seed before attaching it -- an apworld that installs but cannot roll a seed fails for the host, in
  their generation, with our name on it.

The one thing still open is on the host: `POST /generate` has a single `AP_ROOT`, so both wizards
generate with whatever apworld is installed there. `SPEC-publishing-pipeline.md` carries the fix.

### Every wizard yaml now says which apworld it was written for

The wizard is a static page on peliarch.ca; the apworld is published on a tag; the player bundle also
goes to Nexus. Nothing pinned the three to each other, and on 2026-08-08 all three were different
builds -- the newest of them being the one strangers were pointed at. The live page offered 44
options; the newest tag, v0.3.7, has 42.

That is worse than it sounds, because Archipelago does not refuse a yaml carrying an option the
installed world has never heard of. Measured on 0.6.7: it prints one line, in the middle of ~50
unrelated `Could not load world` lines, and **generates the seed without the option**, exit 0. A
player sets `keep_local`, the seed rolls, their consumables go out to the multiworld anyway, and
nothing anywhere says why.

So the pairing is now stated at both ends. `wizard/options-metadata.json` carries
`apworld_version`; the wizard header names it; and every emitted yaml puts it in `description:` --

    description: "generated by the ER options wizard 2026-08-08 for apworld v0.3.8, options 3279392e (preset: Defaults)"

-- because `description` is the only field that reaches anything anyone reads later: Archipelago
echoes it in the generation log and stores it in the multidata. A comment would not have.

This labels the skew rather than removing it. `SPEC-publishing-pipeline.md` has the measurements and
the design for removing it, and names the one decision it cannot make on its own: whether the public
wizard should track the newest TAG instead of `main`.

### You can finally see what you put into other people's games, and aim it

Two players asked the same question the same morning, from opposite ends of it. On Nexus,
LordChungle: *"if I am playing with 5 other people who have 200 checks each, then 2/3 of the checks
sent to others are from me [...] I am wondering around how many of the checks are filler checks."*
On Discord, boblerrr, with the answer he wanted instead: *"crafting materials should be local,
upgrade materials other than bell bearing can be local prob, same with ghost gloveworts, every
single consumable item should be local prob, small rune amounts should not be sent out."*

Neither was answerable. There were two locality controls: `local_item_only`, which keeps
*everything*, and `filler_foreign_pct`, which keeps a *percentage of randomly chosen filler names*
and so means something different in every seed. Between "all of it" and "a coin toss" there was
nothing, and no number anywhere said how much was leaving.

- **`keep_local`** takes a list of categories -- `consumables`, `crafting`, `upgrade_materials`,
  `runes`, `crystal_tears`, `spells`, `spirit_ashes`, `key_items`, `weapons`, `armor`, `talismans`,
  `ashes`, `progressive`, `other`, plus the umbrellas `goods` and `everything`. boblerrr's whole ask
  is `keep_local: [consumables, crafting, upgrade_materials, runes]`, and bell bearings are
  `key_items` rather than `upgrade_materials`, so that line sends them out exactly as he wanted.
- **`keep_local_rune_cap`** holds rune items worth N runes or fewer and lets the big ones travel.
  "Small rune amounts" is a number the game publishes, so it is not guessed: the payout comes off
  `EquipParamGoods.refId_default -> SpEffectParam.soul`.
- **The count.** Every seed's generation log and spoiler now carry a line per slot: how many of your
  items went into other worlds, split filler/useful/progression, how many came back, and how many
  your options held at home. The wizard's *Seed size* tab shows the ceiling live as you move the
  knobs, labelled as a ceiling -- Archipelago's fill spreads a world's items in proportion to open
  locations, so a 1,300-check Elden Ring slot keeps most of its own pool whatever you set.

Under it is a new param-derived taxonomy (`eldenring/item_categories.py`, off a new `GOODS_TYPE`
emit): the id nibble called 933 different things "goods", so there was previously no matt-free way
to tell a crafting material from a smithing stone from a throwing pot. `exclude_local_item_only:
[goods]` in an existing yaml keeps meaning exactly what it meant, and there is a test that says so
-- the first draft of the umbrella quietly dropped the runes out of it.

### The client pin catches up with the client that shipped

The world's gitlink sat at `b3045b4` -- the #101 merge -- through the whole of the v0.3.7 window,
including at the tag. Five client merges landed past it and none were pinned: #102 (the equip queue
asked for an upgrade level the bag had never held), #103 and #105 (the Serpent-Hunter's wave
SpEffect, and the discovery that setting it on the weapon row is inert under a weapon already
equipped), #104 (the ESD talk-event probe) and #106 (your own weapon handed back when Rykard dies).

The shipped `.dll` is a local build artifact rather than something built from the submodule, so the
v0.3.7 zip is not necessarily missing those fixes -- but the tag's RECORD of which client the world
pairs with was wrong, and the cross-side `generators` gate had been proving agreement against a
client five merges old. A stale pin cannot fail that gate; it can only make it prove the wrong
thing. This window starts by moving it.

### CI now generates a seed from the wizard's own yaml

The game-name bug shipped past four green gates, and the reason is the same for all four: every one
of them checked an *input* to the wizard. None read what it hands the player.

`test_gf_wizard_yaml_generates` closes that. It runs the wizard's own `buildYaml` under node -- the
actual JavaScript a browser runs, not a Python port that would agree with itself about the same
typo -- and feeds the result to a real `Generate.py` against the installed world, for the defaults
and two presets. It catches the whole family the other gates cannot: a key the world stopped
accepting, a value outside a live range, a preset that rolls into something that will not fill, or a
yaml that is subtly malformed.

**And then it went stale again inside the same window.** By the time this release was cut the pin
was **eleven** client merges behind -- the ramp-saturation fix, the mod-stack scan, the downstate
probe and the apconfig probe gates -- so the section above was describing a fix that did not hold
for one day.

That is not carelessness, it is a missing gate, and the shape of it is worth recording. `generators`
cannot see staleness by construction: it checks out the client AT the gitlink, so an ancient pin
agrees with itself perfectly. `client-main-drift` DOES see it and says so with `::notice::` -- on
pushes to main and the nightly schedule only, never on a pull request, and a notice is a line in a
job log nobody opens. Its own message defers to "REQUIRED before a tag (RELEASE-CHECKLIST)", and the
checklist had no such row.

So the tag job now refuses to publish a release whose gitlink is not the current client
(`ALLOW_STALE_PIN=1` to override, deliberately awkward). A notice is the right severity on main --
client-only work mid-window is normal -- but a tag is the one moment the pairing becomes a permanent
record, and the first moment it can be enforced rather than remembered.

### Every yaml the wizard produced named a game that does not exist

`buildYaml` carried the game name as a literal, `EldenRing`, while the world has been `Elden Ring`
for months. So every yaml the wizard emitted -- Copy, Download, and the Generate & host button --
named a game Archipelago does not have. Copy and Download handed people a file that cannot generate;
the host button 422'd on every click.

Nothing caught it because the option *keys* are metadata-driven and were correct; only the three
strings carrying the game name were typed by hand, and no gate read them. The name now comes from
the metadata, and `tools/check_wizard_census_js.py` runs `buildYaml` under node and fails if the
emitted yaml names anything else.

### The sidebar could cover the page

Ticking every `progression_surface` class makes one yaml line about 200 characters long. The yaml
preview is `white-space: pre`, so its min-content width is its longest line -- and the sidebar was a
flex item without `min-width: 0`, which means it cannot shrink below that. It blew past its 420px
width, shoved the main column aside and rendered as a panel over the page.

Fixed with `min-width: 0` on the sidebar and wrapping in the preview. The wrapping cannot corrupt
anything: Copy and Download both call `buildYaml()` rather than reading the element.

### The Seed size tab carries the options that change it

The figures were on one tab and the knobs that move them on another, so seeing the effect of
narrowing your progression surface meant walking back and forth. `num_regions`, `enable_dlc`,
`dlc_only`, `progression_surface` and `confine_foreign_progression` now render on the Seed size tab
itself, and the numbers repaint as you change them.

They are the same controls over the same state, not copies -- a change here is a change in its own
section and in the yaml, immediately. The figures repaint on change; the controls deliberately do
not, because rebuilding a checkbox mid-click drops focus.

### Seed size is now the wizard's second tab

"How many checks is this, and how much of it is junk?" is the question people actually arrive with,
so it is no longer a small card in the sidebar. The second tab answers it directly and updates as
you change options.

Two numbers, and the tab is explicit about which is which. **Check count, regions kept, and how many
checks can hold progression are exact** -- sums over the region tables, computed over your actual
draw. **The filler / useful / progression split is measured**, because the filler budget and pool
builder reshape the tail at generation time and the only honest way to know the ratio is to build
worlds and count. It comes from `wizard/pool-composition.json`, sampled by
`tools/sample_pool_composition.py`, and the tab shows the sample size, the option set it was
measured at, and the world commit rather than presenting a band as if it were computed.

Roughly: a default seed is about 56% filler and 43% real gear, with under 1% progression. A
one-region draw is mostly gear; the whole map is about 61% filler. Filler here means real
consumables and upgrade stones -- every check pays something.

The tab also says the thing multiworld players keep needing: Elden Ring gear is only useful in Elden
Ring, `local_item_only` is what keeps it home, and `filler_foreign_pct` alone does not, because it
only covers the filler share. Your own progression never travels either way.

### The wizard's Checks panel was describing a randomizer that no longer exists

A player reported one stale warning. An audit found **twenty**: the wizard's conflict rules were
warning about `ending_condition: capital`, `world_logic`, `location_pool`, `random_start_region`,
`num_regions_rune_source` and fifteen more options that were deleted or renamed months ago. Not one
rule in the panel was fully valid.

It survived because a rule whose option vanishes simply stops firing -- which looks exactly like a
rule with nothing to say -- while a rule comparing against a deleted *value* keeps running and can
never match. The option list itself never drifted, because it is generated; only the hand-written
advice did, and nothing checked it.

The panel is now a small set of rules that each cite the docstring or test defining the behaviour
they describe: DLC Only forcing Enable DLC on, a `great_runes` ending collapsing to `region_locks`
under DLC Only, Local Items Only making `filler_foreign_pct` a no-op, an empty Progression Surface
turning confinement off, an enemy-difficulty minimum above its maximum, and a note that
`num_regions` is a draw size pointing at the Seed size panel for the real range.

`tools/check_wizard_lint_currency.py` fails CI when a rule names an option key or choice value that
no longer exists, so this particular rot cannot return. It cannot tell whether a rule is *true* --
that stays a human review, which is why each rule now carries its citation.

### The wizard can hand your seed straight to a host

When the wizard is served from a host that runs the seed-generation endpoint (peliarch), it grows a
`Generate & host` button: it POSTs the yaml it just built, the host generates the seed and starts a
room, and you get the room link and connect address back without ever installing Python,
Archipelago or the apworld.

Same-origin only, deliberately. The wizard also ships as a `file://` page in the release zip, and a
`file://` page has a `null` origin -- a cross-origin POST from it either fails CORS or forces the
host to run `Access-Control-Allow-Origin: *` on the one endpoint that spends CPU on a stranger's
input. Opened from disk, the button is replaced by a line saying where to open it instead, and Copy
/ Download work exactly as before.

A failed generation shows the generator's own log tail rather than "generation failed" -- that tail
is the only thing that names which option combination refused to fill.

### The options wizard tells you how big your seed is before you generate it

Two players asked the same question from opposite ends in two days. bobler asked why
`num_regions: 1` kept four regions; a Nexus commenter asked what fraction of "2000 checks for 6
areas" is filler, before committing five friends to a multiworld. Both answers only existed after
generating, and #409's gen-log line -- which does explain the kept set -- is read after the decision
it would have informed.

The wizard now carries a `Seed size` panel that recomputes as you move `num_regions`, `enable_dlc`,
`dlc_only` and `progression_surface`: how many checks the seed will have, how many regions it will
actually keep, and how many of those checks can hold progression.

It shows a RANGE, not a number, and that is the feature. `num_regions` is a draw size, not a final
count, so at the default 6 the real check count runs from about 1069 to 2279 depending purely on
which regions the draw takes. A wizard printing one number would be teaching the wrong model of the
option; a spread teaches the right one at a glance.

The surface figure counts a UNION over class combinations rather than a sum of per-class counts.
Progression-surface classes overlap -- a check is routinely `GreatRune` and `MajorBoss` and `Boss`
at once -- so ticking two classes in a summed table would double-count exactly the checks that carry
both.

New: `wizard/region-census.json` (`tools/build_region_census.py`), which reuses
`build_surface_confidence`'s bar stack rather than restating it, so "can host progression" still has
one definition in the repo. Gated by `test_gf_region_census` -- including against worlds Archipelago
actually builds -- and by `tools/check_wizard_census_js.py`, a differential run of the wizard's own
JavaScript against a Python reference.

## v0.3.7 — 2026-08-06

Window opened the same day v0.3.6 was tagged, and again because the gate went red rather than
because anyone remembered. That is the fourth window in a row. The gate is doing its job; what has
still never happened is a window being opened before something red asked for it.

`CONTRACT_HASH` MOVED this window, for the first time since v0.3.0: `5e8b11c9` -> `d7d3a58e`. Two
new optional keys carry the Erdtree burn's world state to the client (below). Both are absent-able,
so an older client still gets the burn.

### You can now reach the end of the game on any seed

Burning the Erdtree used to be something the game decided. It happened when Maliketh died, and
Maliketh lives in Crumbling Farum Azula -- so the Ashen Capital, the Elden Throne, Godfrey, Radagon
and the Elden Beast only existed on seeds that happened to keep both Farum Azula and Leyndell. To
make the ending reachable at all, `goal: auto` quietly forced both of those regions into every draw,
and Leyndell dragged Altus in behind it. That is why `num_regions: 1` gave you four regions: you
asked for one, and three more arrived to make an ending possible.

The burn is now an item. **Ashen Capital Lock** is shuffled into the pool like any other progression
item; when it reaches you, the Erdtree burns, the Ashen Capital's graces light, and you can warp to
the end of the game from wherever you happen to be.

So `num_regions: 1` now means one region. Roll Mountaintops and you play Mountaintops, find the Ashen
Capital Lock somewhere in it, and go and fight the Elden Beast. Nothing is forced into your draw any
more, by the goal or by anything else -- and the line in the generation log that explains your kept
set will say so.

Consequences worth knowing before you roll one:

* Every seed with the base game in play now ends on the Elden Beast. Terminal-region variety under
  `goal: auto` is gone, deliberately: the finale is a fixed gauntlet (Gideon, then Godfrey/Hoarah
  Loux, then Radagon/Elden Beast) and it plays well as a capstone no matter what your draw kept.
* The Ashen Capital's checks -- twelve of them, including two that had been mis-attributed to
  Leyndell all along -- now exist on every such seed instead of on the fraction that kept the right
  two regions.
* The Ashen Capital is not a region you can roll. It is never drawn, never counted toward
  `num_regions`, and never where you start. It is a gauntlet, not a place you play.
* `dlc_only` is unchanged: the base game is sealed there, so there is no burn, no lock, and the goal
  is still the deepest region you kept.

### Radahn's rewards no longer need Leyndell

Radahn's Great Rune and the Remembrance of the Starscourge were gated behind the Leyndell lock, on
the reasoning that the Radahn Festival only starts once you reach Altus. The client has force-set the
festival flag at spawn for a month, so that gate was requiring a lock the game itself does not
require -- and once the goal stopped forcing Leyndell into every draw, it started making those two
checks unreachable. It is gone. Radahn is yours with the Caelid lock alone.

### Small seeds keep their upgrade path

A genuinely one-region seed is a new thing, and the first one found a gap: the filler budget shared
out somber smithing stones proportionally, which on a small enough seed left whole tiers out of the
pool. A missing somber tier is not thin supply, it is a wall -- a somber weapon can never pass the
level below it, for the whole run. The somber reservation now has a floor that covers every tier plus
the early guarantee, and says so in the log on the rare seed too small to pay it.

### The Great Rune of the Unborn was missing from every seed

Rennala's kill sets one acquisition flag that feeds two item lots: the Remembrance of the Full Moon
Queen, and the Great Rune of the Unborn. Only the first was modelled as a check.

That matters because the randomizer blanks a check's item lots by **flag**, so it was blanking both
of them — and with nothing modelling the second, nothing handed the rune back. It was removed from
the game and replaced by nothing, in every seed since the check model landed. Because the item had
no name anywhere in our data, nothing noticed: it was absent from the spoiler, absent from hints,
and absent from the item catalog.

It is now its own check, in the same place, alongside the Remembrance. Both are shuffled
independently and both are yours to find.

⚠️ This does **not** yet make it count as a Great Rune. `goal_great_runes` still caps at six and the
Leyndell gate still counts six, which is a separate change — see below.

### You can open a run on more than one region

bobler, the day v0.3.6 shipped: *"is there an option to start with more than 1 region unlocked?"*
There was not. There is now -- **`start_regions`** opens N regions at run start instead of exactly
one.

Everything downstream was already plural-aware, so this changes less than it sounds: every opening
region is sphere 0, the scaling ramp starts from the whole opening, and the goal subtracts the entire
opening rather than just the first region.

* **`start_regions: 1` is the old behaviour exactly.** Not "equivalent" -- identical. The first pick
  is delegated to the untouched one-region draw and makes no further roll, so both the region and the
  position in the random stream are unchanged and every existing seed still rolls the same way.
* **The goal region can still win the first draw, but is never an extra.** Around 9% of seeds already
  open on the region they end in; barring that would change seeds that exist. Handing it out as a
  bonus region is different -- a run that opens on the region it ends in is not a run.
* **The ceiling is what your seed actually KEPT**, not what you asked for, and asking for more than
  that fails loudly with both numbers rather than quietly opening everything. `num_regions` is a draw
  size, so precollecting every kept region would leave a `has_all` goal complete at connect on a seed
  you have not played.

### The Scadutree blessing is two settings, and the ceiling is gone

`global_scadutree_blessing` was one option doing two jobs. It is now
**`scadutree_blessing_scope`** (`dlc_only` or `anywhere`) and **`dlc_blessing_catchup`**. The old key
still works and translates itself, so existing yamls generate the same seed; setting both the old and
new keys to contradictory values is an error rather than a silent winner.

The split makes a fourth combination expressible for the first time: **vanilla scope with the
catch-up floor** -- the blessing behaves exactly as the base game intends, but the DLC never runs
under its expected level. That one needs a client from this window; an older client would have
clamped it to off without saying so.

**The ceiling is removed.** The only limit now is the vanilla ladder's own 20. The old cap of 12 was
never a ceiling argument -- it was a statement about how much of the item pool fragments should eat
-- so it moved next to the code that actually governs supply, and it moved to 20, because the base
game hand-places exactly 50 fragment units and 50 units is exactly ladder level 20.

Paying for that without flooding the pool: half the injected fragments now arrive as a new
**Scadutree Fragment x2**. Fifty units costs 38 items instead of 50. It is a separate item rather
than a bigger stack on the existing one, because stacking in place would have doubled every
hand-placed vanilla fragment as well.

### Three options never reached the wizard

`start_regions`, `scadutree_blessing_scope` and `dlc_blessing_catchup` all landed this window and
none of them appeared on the options wizard. The page's option list is generated from the option
classes themselves, and three merges in a row changed those classes without re-running the
generator -- so the wizard was still offering a single `global_scadutree_blessing` that had already
been split in two, and offered no way at all to open a run on more than one region.

Regenerated. All three are on the page now, and `capital_reconciler` and `natural_progression` sit
back in their right places in the ordering. The yaml has always accepted these options; only the
wizard was behind.

### A boss you cannot fight no longer holds a region's loot hostage

A sweep group has two regions and we were only ever checking one of them: where its checks live, and
where you have to stand to kill the boss that hands them over. For six groups those are different
places, and the worst of them is the Golden Hippopotamus — it hands over 104 Shadow Keep checks, but
the arena you fight it in is Scadu Altus ground. Keep Shadow Keep without Scadu Altus and the region
lock throws you out before you reach the fight, so the sweep sat there forever, and the tracker
cheerfully said "0/104 — waiting on the boss" about a boss the seed would never let you reach.

Those groups are no longer sent to seeds that cannot fire them. **Nothing is lost that you could
have collected**: every one of those checks is an ordinary pickup in its own region and always was —
you walk to it like any other. What you lose is the convenience of being handed them, and what you
gain is not being told to wait for something that is never coming.

The other five: Margit's 55 Stormveil checks (arena is Limgrave), 24 Gravesite checks (arena is Rauh
Base), 11 Abyssal checks (arena is Scadu Altus), and two small Ashen Capital groups that were always
inert. At six kept regions, about half of all seeds had at least one of these.

### Known: 20 checks may stand in a region other than the one we file them under

Found while fixing the above. A check's region decides whether your seed creates it; your position
decides whether the region lock lets you stand there. Those are two different derivations and they
disagree about 20 checks — eleven Gravesite checks that sit on Rauh Base ground, four Cerulean
checks on Charo's ground, and a handful of one-offs. If you keep the first region and not the
second, those checks exist in your seed and you may not be able to walk to them.

They are all filler and none of them can hold progression, so no seed becomes unwinnable. They are
listed and pinned now, so no new ones can appear unnoticed, and each needs an in-game confirmation
before we move it — a datamined coordinate is not a playtest. If you hit one, tell us which.

### Known: on a DLC-only seed, `goal: auto` need not end on Promised Consort Radahn

The base game's finale is guaranteed -- the Ashen Capital is never rolled, exists on every seed with
the base game in play, and is where `auto` ends. The DLC has no equivalent: Enir Ilim is an ordinary
region in the DLC pool, so a draw that does not keep it ends the run on the deepest terminal region
you did keep. A player finished one this week on Romina in the Ancient Ruins of Rauh and reasonably
read the early goal as a broken ending. It is not -- Romina is a real Remembrance boss -- but it is
not the ending he was picturing either.

**`goal: promised_consort`** forces Enir Ilim into the draw and ends the run there. Making `auto` do
it by default on DLC-only is the obvious fix and is not in this window.

### Known: the capital gate counts a rune we do not

Elden Ring opens the capital on a **count of flags**, and the flag Rennala sets is inside the range
it counts. So the game already treats the Great Rune of the Unborn as one of the runes on that door,
and we do not. In practice our logic is the stricter of the two, so nothing becomes unreachable and
no seed can soft-lock on it — but you may find the capital physically open before the randomizer
expects it.

Tracked, with the fix scoped but not yet made, because it changes what "how many Great Runes" means
and that is worth getting right rather than fast.

### You can now play the base game together, with only deaths shared

Some groups do not want a randomizer. They want to play Elden Ring with friends, share their deaths,
and have the Dectus Medallion halves sit in Fort Haight and Fort Faroth where they have always been.
Until now the only thing close to that was Natural Progression, which sounds like it and is the
opposite: it keeps vanilla's *shape* while still shuffling the keys that open it, so the Dectus
halves still ended up in someone else's world.

**Vanilla Placement** is the missing setting. Turn it on and every item goes back where the base game
keeps it -- every key, every Golden Seed, every talisman. Progression is gated the way the base game
gates it, so the region locks are not used at all and Number of Regions is ignored: the whole map is
open from the start and the Leyndell wall, the Rold Medallion and every other door work as they
always did. Checks still fire, the tracker still works, and Death Link still works. Nothing is sent
to or received from other worlds -- your seed is self-contained on purpose.

The new **Vanilla + Death Link** preset in the options wizard is this setting plus Death Link, which
is the whole configuration for a co-op vanilla run.

The start is vanilla too. You begin with what your class begins with: no lantern, no extra flasks,
no Torrent, no Spirit Calling Bell, no crafting pots, no revealed maps, and no levelling until you
meet Melina. All of it is out in the world where the base game keeps it. Three of those gifts were
also quietly ticking off their own Roundtable checks the instant you connected -- the Spirit Calling
Bell, the Flask of Wondrous Physick and the Whetstone Knife are granted by setting the very flags
that mark their checks collected -- so a vanilla run used to open by claiming three checks it had
not been to. It does not any more.

Dropping the 32 starting crafting vessels had a second effect worth knowing about: they were eating
the game's own stack ceiling, and every pool copy past that ceiling pays a Rune instead. On a test
seed that was 21 real items -- eight Cracked Pots, seven Perfume Bottles, three Ritual Pots, three
Hefty Cracked Pots -- replaced by Runes *on their own vanilla locations*. They are back where they
belong.

What this mode still does not change: the combat quality-of-life this world always applies. Weapons
upgrade automatically, the upgrade curve stays flattened, and weapons ignore their stat
requirements. So it is vanilla *placement* and a vanilla *start*, not vanilla *balance*. It also
inherits the base game's own missables -- burning the Erdtree still strands Leyndell's checks.

### Rykard's fight now comes with the spear it was built around

Rykard's second phase is designed around the Serpent-Hunter, a unique great spear the base game
parks on the way to him. A randomizer scatters that spear into the multiworld, so the fight could
demand a tool you had no way to hold. bobler put it best: *"rykard without serpent hunter is some
bs"*.

When Rykard loads, you are handed a copy. It is keyed on the CHARACTER, not on the room -- so if you
are running an enemy randomizer that has moved him somewhere else entirely, the spear follows him
there. It covers both phases, because the God-Devouring Serpent and Rykard are the same character
underneath. The copy you are given never collects the check for the real Serpent-Hunter; that one is
still out in the multiworld for someone to find.

Two things about the timing, both of which took a round of playtesting to get right:

* **The spear goes into your hand when the fight starts**, not when the area loads. It used to arrive
  the moment you walked into the grace, which meant that under an enemy randomizer the toast
  announced where Rykard had been swapped to before you could see him.
* **Weapon auto-equips are held for the duration of that one fight**, so an incoming weapon from
  another world cannot take the spear out of your hands mid-fight. Armour and talismans keep
  flowing. Nothing is dropped -- a held weapon equips the moment the fight ends.

It then took three more client fixes to actually work, all of them found in bobler's logs on
2026-08-07 and all invisible without them:

* **The equip rode on the one-shot grant**, so it fired once per character ever -- a reload, a
  re-fight or a weapon swap afterwards left the spear in the bag while the fight it exists for
  happened without it. It follows the FIGHT now.
* **The queued id was raised to your auto-upgrade target.** That is right for an incoming weapon (a
  grant is about to deposit it upgraded) and wrong for one already banked in your bag at a lower
  level -- it named a row that had never existed, missed the bag lookup, and retried in silence for
  the rest of the session. The queue now asks the bag what it holds.
* **The wave moveset needed a SpEffect the weapon does not carry**, and setting it on the weapon row
  was inert because that field is read when a weapon is EQUIPPED -- editing it under a spear already
  in your hands does nothing until you re-equip. It is applied to the character directly now, so it
  survives being already equipped and survives every area load.

⚠️ **The Serpent-Hunter now throws its waves everywhere, not only at Rykard.** Deliberate: keeping it
fight-only means re-deriving a condition the game sets for its own reasons and does not expose, every
session and after every load. It is a good great spear now.

**Your own weapon goes back into your hand when the fight ends.** An AP weapon that arrived during
the fight outranks the restore, and so does a swap you made yourself.

⚠️ If an enemy randomizer has moved Rykard OUT of Volcano Manor, whoever inherited his arena gets
nothing. That is deliberate: the spear is the answer to Rykard, so it goes where Rykard is, not
where he used to live.

### A check that held an item the game does not have

FromSoft marks cut content by writing `[ERROR]` into the item's name, and it does it two ways: a
bare `[ERROR]`, and `[ERROR]` followed by the real name. Our guard only knew the bare form.

So goods 8130, `[ERROR]Rya's Necklace`, read as an ordinary named item, and flag f400081 shipped as
a live check holding something that does not exist in the game. It was never a second copy of Rya's
Necklace -- the real one is a different item entirely, on a different flag, and is unaffected.

It had a second effect worth naming, because it is the kind that hides: our data strips the marker
from the name, so the pool believed it held two items called "Rya's Necklace" against a game that
will only let you carry one. The ceiling clamp then quietly deleted one of them. Both the phantom
check and the deletion are gone.

### The tracker tells you what a sweep is worth before you fire it

Three small quality-of-life changes on the client:

* The tracker now shows what each boss sweep will hand over, before you kill the boss -- so
  "is this fight worth the detour" is a question you can answer.
* "What is my scaling here" is now something you can ask the tracker, rather than something you wait
  for the game to announce.
* Warping to a grace re-announces the region you land in, so the scaling and lock state of where you
  now are is on screen without a reload.
* The scaling line says so out loud when scaling is **off**, and prints the whole band rather than a
  fragment of it -- so "is this region actually scaled" stops being a question you infer.

## v0.3.6 — 2026-08-06

Window opened 2026-08-06, one day after v0.3.5 was tagged — and this time a gate said so rather
than a person remembering. `tests.yaml` now fetches tags, so
`check_release_notes.check_version_is_still_open` and
`test_gf_contract_versions::test_every_tagged_version_is_recorded_as_shipped` could finally see
their own subject. Both went red on the first PRs to land past the tag. That is the third window in
a row opened late, and the first one caught by the tooling instead of by hindsight.

`CONTRACT_HASH` is unmoved from v0.3.0 (`5e8b11c9`). The bump is version-lockstep across both repos.

### `enemy_scaling: false` now actually turns scaling off

It never did. `completion_scaling` ships in slot_data twice — a top-level copy that was correctly
gated on your option, and a copy inside `options` that was a hard-coded constant. The client reads
the second one. So a seed rolled with enemy scaling turned off still armed the whole sweep: one
player's log shows 240 enemies rescaled at 1.14x on a seed he had explicitly turned it off for.

The curve id is now decided in one place that both copies call, so the switch cannot be half-gated
again, and a test asserts the two copies agree for both settings of the option.

If you rolled a seed with `enemy_scaling: false` on 0.3.5 or earlier, it was not vanilla.

### `num_regions` is a draw size, not a total

Set it to 1 and you can still get four regions. That is intended — a named goal force-keeps the
regions it needs, and any kept region pulls its parents in — but nothing said so, and the option's
own description claimed the opposite: that only kept regions get locks, checks and goal requirement.
That stopped being true when the goal force-keep became goal-sensitive.

The description is corrected, in the shipped template as well as in the wizard, and generation now
logs the breakdown so the number is auditable at roll time rather than four hours in:

    num_regions: 1 drawn (Liurnia) + 2 forced by goal=elden_beast (Farum Azula, Leyndell)
                 + 1 parent closure (Altus) = 4 kept

The goal is deliberately not clamped to the drawn set. A `goal: elden_beast` seed that cannot reach
the Elden Beast is the failure this was built to prevent.

### Enemy scaling can go DOWN

The ladder starts at 1.14x and has no rung below it, so until now an unrunged, hand-tuned enemy
could be scaled up and never down. A region the seed put early kept whatever strength vanilla gave
it, and `NoTouch` was the honest answer rather than a bug — there was nothing to apply.

No single `SpEffectParam` row in the game scales both health and attack below 1.0: of 11,325, twenty
are under on health, twenty-five under on attack, zero on both. The down primitive is therefore a
COMPOSITION of four rows from the DLC ally-tuning block (`20018002/004/008/027`), which stack
because they are `spCategory 0`. `20018004` is the only clean sub-1.0 `maxHpRate` row in the param —
the other nineteen zero their targeting flags, carry an icon and an `addXStatus`, or are timed.
`20018027`'s 3x health is not a defect but the canceller: 3.0 x 0.25 = 0.75.

Which state an enemy gets is the ladder's own ratio between its presumed tier and the region's
target, rounded down, with health as the tiebreak. Below a 0.90 deadband the step is smaller than
the coarsest tool (0.70x) can express and the enemy is left alone.

Measured live, exactly: `523340014` 1098 -> 274 (0.25x), `1000000` 1939 -> 1454 (0.75x). The attack
rates resolve and are carried but have never been read off a live hit — the desk case is that
`20018002` differs from the proven `20018004` only in the rate columns, and writes the same five
columns the ladder itself writes. Shipped to let play validate the magnitude.

### The area may vouch for a named enemy DOWNWARD, but still never upward

`AREA_EXCLUDED` refuses to infer a named, unrewarded character's strength from its neighbours,
because doing that upward made Vyke come out crazy strong. The carve-out was direction-blind and its
justification is not: downward the failure is an enemy that dies too easily, which this file's axiom
prices as a blemish against over-scaling's wall. 275 of its 411 rows have no `getSoul` tier either,
so they were `NoTouch` in both directions — unreachable by every mechanism the client had.

The guard is intact: upward attribution still goes through `presumed_native_tier`, and a test
asserts the area can never up-scale an excluded row at any tier.

### An unmapped region is no longer scaled at all

`tier_for_region` returned the floor tier for a region absent from the wire, which was a guess
wearing a number's clothes — true only while the floor was 0. One log swept 198 enemies at connect
before the game had resolved a region, and 42 in the Chapel of Anticipation. It returns `Option` now
and the sweep declines on `None`. Kept regions are unaffected: every one of their play_region
buckets is wired, and sealed regions are kicked rather than walked.

The region-entry toast moved with it. `RegionScaling::Defaulted` carried the floor tier so it could
announce "using the floor, 1.14x"; once the sweep stopped applying that, the announcement was
actively false. It carries no number at all now.

### Talismans stop piling into one slot

Received talismans rotated on a modulus read from the live character, so once your unlocked slots
were full the lowest one was the only one that ever changed again — and at one unlocked slot, which
is most players for the first several hours, that meant every talisman after the first replaced the
last. One 0.3.5 log has 21 of 22 equips landing on the same slot.

The rotation is now derived from Talisman Pouches in your received-item stream instead, which makes
it a pure function of what you were sent — so a reconnect rebuilds the same loadout instead of
quietly rearranging it. The clobbered talisman was always still in your bag; this is about which
one is worn.

One regression is priced in and worth stating: if a Talisman Pouch reaches you without passing
through Archipelago — a character carried in from another seed — the derived count under-reports and
you get fewer slots than you have earned. The client logs both counts and warns when they disagree.

### Region-lock hints: hint the NEXT lock, and a balance you can actually see

Two defects, one report (#412).

**Naming a lock was a guess.** The in-game lock hint asked which region you wanted, but the order
regions unlock in is not a property of the seed — it is a consequence of the fill. "Altus is second"
only means the Altus Lock item happens to sit in Liurnia. So a player who did not already know the
chain had to buy hints for locks he could not reach in order to find the one he could. One 0.3.5 log
has three `!hint`s three minutes apart doing exactly that, to discover
Liurnia → Altus → Farum Azula → Leyndell.

There is now a single **Hint next lock** button with no target to name. It resolves the *frontier*:
the lock whose own region is still sealed but whose item already lies in a region that is open. That
is a join over three tables the client already had — `coarse_lock_items`, the live region-open flags,
and the connect-time scout — so no new slot data and `CONTRACT_HASH` is unmoved. Reachability here is
region reachability, deliberately: it is the same approximation the tracker's own `[locked]` tag
makes, and two notions of "reachable" in one window would be worse than one imperfect one.

Ties break on the lowest location id. The per-region button stays for players who do want to aim.

**The economy was invisible, which is why nobody used it.** The same log reads `lock hints: ledger
loaded from er_lockhints_2 -- 0 hint(s) already bought`. It loaded, priced itself correctly against
his seed, and was never touched — because everything it had was behind three closed doors at once:
`tracker_visible` defaults to **false**, its F6 toggle was in no guide, and the price rendered only
on the header of a region that had to be both locked and scrolled into view.

The balance is now on the overlay menu bar, which is drawn whenever the main window is, and clicking
it opens the tracker. The tracker leads with the balance and the button, above the filters. Two
latched notices fire — the first time there is a lock to spend on, and the first time the balance is
enough — and neither can repeat. The unit `sp` is gone; it was defined in no file. It reads "surface
checks", with a tooltip for how they are earned.

Client-only. Still owed on Windows and not coverable by CI: the live `CreateHints` round trip, the
data-storage read/write against a real server, and the claim the whole feature rests on — that
`!hint` still shows full hint points afterwards.

### Launching through matt's randomizer does not give you a separate save

Our own setup docs said the Archipelago run uses its own save file, `AP_me3.sl2`, with no condition
attached — and `release/SETUP.md` said it three lines above the paragraph telling you to launch
through matt's randomizer instead.

The separation is the **me3 profile's**, not the client's: it is one line, `savefile =
"AP_me3.sl2"`, in `ap.me3`. Launch any other way and it does not apply, so your Archipelago
character is created in your ordinary Elden Ring save, beside your real ones. A player found this
himself by opening vanilla Elden Ring and seeing the character in the list.

Every doc that made the promise now scopes it, the shipped guide covers it for the first time, and
`ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md` carries the setup — including the `alt_saves` workaround
the reporter verified, credited and marked as **not tested by us**.

🛑 **While you are set up that way, play the Archipelago character and nothing else.** A character
carrying no Archipelago marker reads as a BRAND-NEW Archipelago character, and a new character is
owed everything the room has sent — so loading one of your ordinary saves while connected can grant
it the backlog. The guard that exists catches the other case (a character belonging to a *different*
run is refused outright). Tracked as a code fix; documented here because it bites today.

### The great-rune goal caps at six, and `num_regions` at 30

Both were numbers typed by hand where they should have been counted.

`goal_great_runes` advertised a maximum of **7**. Elden Ring has seven Great Runes in the fiction,
but only six exist as items — the Great Rune of the Unborn is not one you can be given — so a player
who set the advertised maximum got a goal no seed could satisfy and a hint for an item that does not
exist. The cap is derived from the item list now.

⚠️ **Compat:** an out-of-range value is a hard generation failure, not a clamp. A yaml carrying
`goal_great_runes: 7` will now be rejected with `7 is higher than maximum 6` where it used to be
accepted and quietly mean something else. Nothing we ship sets 7; this only affects yamls raised by
hand — which our own advertised range invited.

`num_regions` maxes at **30** (17 base + 13 DLC), and five files said 31, including three places in
the shipped template. The code was always right — the cap is derived from the region list — so this
was purely a documented number nobody could use: type 31 and generation fails.

### Internal

The client now writes what else is loaded beside it into its log — the mod directory, the loader
that brought it in, and any third-party data files sitting next to it. A data mod like matt's
randomizer ships no DLL at all, so it can never appear in a crash backtrace or a module list, and a
report that showed none was read for two sessions as evidence that none was present. It was a
quantifier over an empty set. The log now answers the question without a round trip to the player.

Ten test fixtures were still passing `num_regions_order: spine`, a no-op kept for one release so
yamls in the wild keep rolling. They would all have failed at once, on an unrelated change, the
moment the option is removed. Removed now, with three docstrings that were selling guarantees the
option stopped providing.

`main` was red for part of the window on `test_D_freshness_vs_disk`, whose message says "generated
data lags the inputs". It did not: a full regen moved twelve lines and every module body hash was
unchanged. Body hashes unchanged means the inputs diverged without reaching the outputs — the
committed stamp was computed against a local artifact tree while CI, and every clone, recomputes
from `gen_inputs.db`. Restamped to the bundle. The lasting fix is rebuilding the bundle from the
artifacts, which only one machine has.

⚠️ `release/EldenRing.yaml` — the template players download — was corrected after v0.3.5 was tagged,
so the tagged template and this one differ in the `num_regions` description and in its region
counts. Nothing functional.

## v0.3.5 — 2026-08-04

Window opened 2026-08-04, at the moment v0.3.4 was tagged — which is the whole point of rule 14.
Tagging does not open the next window; a person does, and the two previous windows were both
opened late because everyone assumed otherwise.

Opening it also surfaced a gate that cannot see its own subject.
`test_gf_contract_versions::test_every_tagged_version_is_recorded_as_shipped` asks the git tags
which versions shipped — and the CI checkout does not fetch tags, so it finds none and passes.
v0.3.4 was tagged with no `SHIPPED` row and nothing said so; it only went red in a clone that had
the tags. The row is written here. The gate needs `fetch-depth`/tags before it is worth anything,
which is a to-do, not a fix.

`CONTRACT_HASH` is unmoved from v0.3.0 (`5e8b11c9`), so the handshake is unchanged and seeds
rolled on 0.3.1+ still connect. The bump is version-lockstep across both repos.

### Key items behave more like matt's randomizer

The missable bar used to cover every item an NPC hands you, on the reasoning that an NPC can die.
More than half of those are handed over the first time you talk, with no questline state behind
them — so they now count as places progression can live. In practice the **Rold Medallion**, the
**Drawing-Room Key** and the **right Haligtree Secret Medallion** stop being dead ends for the fill,
and four more items are recognised as key items at all: Messmer's Kindling, the Hole-Laden Necklace,
the Fingerslayer Blade and Rya's Necklace.

The distinction kept is the one that actually bites: an item you can lose by advancing a questline
still cannot hold anything required. Rya's Necklace is barred for that reason, and the Fingerslayer
Blade for a related one — you hand it to Ranni.

The key-item share of the progression surface goes from 8 of 15 checks able to host, to 13 of 19.

### Rya's Necklace was in the wrong region

It was filed under Altus because of a bad map join. It is handed to you at Boilprawn Shack, in
**Liurnia**, which is where it now lives.

_(These landed in #375, which merged before this window was open — the notes belong here, in the
version that will actually ship them, not in the tagged v0.3.4 section they would otherwise have
gone into.)_

## v0.3.4 — 2026-08-04

Window opened 2026-08-04 (rule 14), and opened LATE -- which is the first thing to record.
`v0.3.3` was tagged on 2026-08-03 while `APWORLD_VERSION` still read `0.3.3`, so three commits
landed on main writing their notes into a section that had already shipped. One of them was
player-visible and is moved down into this window below. `tools/check_release_notes.py` stayed
GREEN through all of it, because it asks whether the version named by `APWORLD_VERSION` has a
dated section -- never whether that version already went out. Rule 13 applies to the gate itself:
that blind spot is a to-do list until something checks it.

`CONTRACT_HASH` is unmoved from v0.3.0 (`5e8b11c9`), so the handshake is unchanged and seeds
rolled on 0.3.1+ still connect. The `data/` hash HAS moved, so a seed rolled here is not the seed
v0.3.3 rolled. The client moves only its version string, so an older DLL still connects -- but the
version it reports will not match what you are running, which is the whole point of rule 15.

### Fixed: 36 items were never checks at all, so they dropped their vanilla version

A `region_map.csv` row filed `Global / Common-event (unplaced)` is one whose flag nothing could
decode a map from. gen_data emits no location for it, so the client never blanks the vanilla item
lot, and you pick up the vanilla item with the randomizer none the wiser. Nothing errors; the item
simply is not a check.

Thirty-six of them now are, placed from what the game already records — an observed MSB map for the
flag, or the flag's item lot named by exactly one map's talk ESD. Among them: Kalé's and Gostoc's
Bell Bearings, eleven merchant Bell Bearings, the Glintstone Kris, the Royal Greatsword, Iron Kasa,
nine Ashes of War, two paintings' rewards, and the Sewer-Gaol Key. Three of those are field-boss
drops (Vyke's Dragonbolt, Death Ritual Spear, Star-Lined Sword), so three bosses that carried nothing
now carry a check.

**This adds locations, so a seed rolled here differs from one rolled on v0.3.3** — which is why it
lands at the top of a version window rather than mid-release.

**What is NOT fixed, and it is the case that prompted the work.** Thops still drops the vanilla
Academy Glintstone Staff. Its flag's lots are named by no talk ESD and no map EMEVD, so no corpus we
have can say where it is — it is one of 45 in that position. Another 19 are named by two or three
maps because the NPC relocates, and guessing one would assert a reachability we do not have. Those
64 stay unplaced, counted and printed by the tool rather than quietly dropped.
### Fixed: 21 pot items per seed were being placed, delivered, and then destroyed

The game has a per-item stack ceiling (`EquipParamGoods.maxNum`), and for an item you cannot drop,
sell, or put in the storage box, a copy past that ceiling is not late -- it is gone. The game
refuses it, the client's grant still reports success, and the multiworld has spent the item. On a
default seed the pool plus the start loadout came to 27 Cracked Pots against a ceiling of 19, 12
Ritual Pots against 9, 16 Perfume Bottles against 9, and 13 Hefty Cracked Pots against 10 -- 21
items placed that no player could ever receive.

The generator now knows the ceiling and stops creating those copies; each one pays curated filler
instead, so the seed keeps exactly the same number of items and you get something usable in place
of something that would have evaporated.

Thirteen other goods were in the same trap and had no telemetry at all, because only the pot rows
were capped client-side: a second Whetstone Knife, Cursemark of Death, Lord of Blood's Favor,
Unalloyed Gold Needle, Dragon Cult Prayerbook, three Crystal Tears, three `Note:` items, a Letter
from Volcano Manor, and a ninth Memory Stone against a ceiling of eight.

Consumables are deliberately untouched -- Golden Rune [1] ships 161 copies against a ceiling of 99,
but you spend them, so the stack drains and the surplus is merely early. Weapons, armour, talismans
and spells are untouched too; their duplicates are there on purpose.

The client's existing pot cap is unchanged and stays as the backstop. It could never have fixed
this: for the three rows a vanilla event watches, `maxNum` is exactly the held count that fires the
event, so capping one below it is the only safe state available and there is nowhere for a surplus
pot to go.

### Fixed: 421 checks had lost their nearest Site of Grace to a join that could never match

`build_nearest_grace.py` kept its own copy of the overworld tile fold, and it disagreed with the one
the check browser and the desc-triage map use: it folded every tile at 256 m regardless of LOD, and
its pattern required a trailing `_`. Overworld coordinates are recorded in two id shapes -- 725 item
rows are three-field (`m60_34_50`) and every one of the 225 overworld grace rows is four-field -- so
the item side kept its raw map id as the join key while the grace side folded, and the two could
never meet. No distance was ever computed; the lookup returned empty first.

There is now one fold, in `tools/overworld_fold.py`, shared by all three consumers, and a test that
asserts they are the same object rather than merely agreeing.

Seventeen checks say something better to the player as a result -- thirteen move from a whole-map
"around X" to an exact "near X", three from a raw map id like `m60_42_50`, and one from a locale.
The other 404 recovered rows belong to checks that already had a better descriptor from an earlier
layer; they matter because other tools read the table.

Also fixed by the same change: eighteen checks were matching a grace 8.7-10.4 km away and being
discarded by the distance cap, which is why the grace-straddle screen reported "Altar South"
spanning four regions. They now land 30-356 m from a grace that makes sense.

**Not fixed:** the 134 checks whose descriptor is a bare map id. Zero of them have a coordinate at
all, so no join can reach them -- that half of the report needs the MSB datamine, not this.

### Changed: every Golden Seed and Sacred Tear now has a hand-written location

All 56 flags that award a Golden Seed (43) or a Sacred Tear (13) were walked in game and described
by hand. Before this, 43 of them were named after the nearest Site of Grace, 9 after a whole map
tile, one after a machine locale, and one after nothing at all -- so the tracker said things like
"Golden Seed - around War-Dead Catacombs" for an item that is a Putrid Tree-Spirit drop, and the two
seeds above Outer Wall Phantom Tree were distinguishable only by a "(1)"/"(2)" the generator appended
because it could not tell them apart. 50 hand descriptions land here; 48 of them move a name.

Nine of those checks also had their REGION confirmed on the same walk and are no longer hedged, so
they can host progression for the first time: three Altus seeds, one each in Caelid, Limgrave,
Liurnia and Mountaintops, and the Sacred Tears at Church of Irith, Second Church of Marika and
Stormcaller Church. They previously read "(region unconfirmed)" on screen and were barred from
carrying anything required.

Two checks were deliberately left alone. The Mohgwyn seed near Dynasty Mausoleum Midpoint keeps its
automatic name and is now barred from hosting progression -- Mohgwyn is reached by a one-way
teleport, so its route is awkward in a way the region model does not capture. The Golden Seed between
the Forbidden Lands and the Grand Lift of Rold stays hedged even though its region IS now known: it
sits on ground a Mountaintops-anchored player cannot reach without a Leyndell item, which is a
reachability problem rather than a region one.

### Fixed: a region unlock could warp you into Commander O'Neil's arena, onto a grace that is not there (#244)

The Heart of Aeonia grace does not exist until Commander O'Neil dies -- the game hides its asset
behind his defeat flag and reveals it on the kill. The Caelid region bundle force-lit it anyway, so
warping to it dropped you into the middle of his boss arena on a disabled bonfire: the exact
soft-lock the boss-gated skip list exists to prevent. It is withheld now, and lights normally the
moment you beat him. Caelid keeps its other 37 graces, so nothing is lost the other way.

The mechanism behind it: the skip list was derived from the game's event scripts in July, when only
the 380 legacy-dungeon scripts were decompiled -- and it was COMPLETE for that corpus (37 flags).
The overworld tile scripts landed in the input bundle later, carrying 12 more boss-hidden graces
(Radahn, Fire Giant, Bayle, Rellana, Romina, Gaius and friends). Eleven of the twelve were already
withheld for a different reason (they sit inside boss arenas); Heart of Aeonia was the one that
slipped through, because it is far enough from O'Neil to clear the arena-distance screen while still
being flag-hidden. All twelve are now classified by their real mechanism, with the per-flag evidence
written next to the data, and the independent EMEVD oracle that caught this (dormant and red since
it was written) now runs green in CI on every push -- a corpus regen that grows the true set again
cannot go unnoticed a second time.

### Fixed: the early somber-stone guarantee could quietly under-deliver on small seeds

`early_guarantee` promises TWO copies of Somber Smithing Stone [1], [2] and [3] reachable from the
start -- the same 2x find-rate margin the regular stones get. But `declare_early_items` is an AP
placement HINT: it can only declare what the pool already holds, and the somber coverage floor
(added 2026-08-02) stocked exactly ONE copy of each missing tier. On a small `num_regions` seed the
somber reservation is ~15-25 draws, so the pool held a single copy of a low tier in ~10-20% of
1-region seeds per tier (measured, 54 generations); the hint clamped to one with a warning nobody
sees at gen time, and sphere 0 dutifully received exactly the one copy. That is the shape of
boblerrr's playtest report -- the Somber [1]/[2] sphere-0 floors "may not be getting restricted" at
small num_regions. Measured, the RESTRICTION was never the broken half: sphere-0 counts tracked the
pool exactly, seed for seed, across 116 generations at num_regions 1-3. The supply was short, and a
guarantee that can only clamp to supply is a hope.

The coverage floor now pays the early margin too: the low tiers' floor is the early guarantee's own
count, created where the reservation is drawn, so the hint downstream has nothing left to clamp. The
donor rule was also wrong for small reservations -- "a tier never donates its last copy" protected
the last drawn copy of tiers whose wall vanilla already holds up, which starved the margin at a
~14-stone reservation. Surplus is now computed against the requirement (vanilla copies included), so
the affordable part of the floor is paid in full, deterministically, and anything genuinely
unaffordable warns by name -- absent tiers separately from a thin early margin. After the fix: 0
shortfalls in 36 fresh 1-region generations (pool, declaration, and sphere 0 all hold the 2x margin
for tiers [1..3]; tail-tier presence [4..9] unchanged at 100%).

Deep-tier EARLY placement is explicitly not promised: a Somber [8]/[9] still lands past sphere 1 in
some seeds. Their POOL presence (the 2026-08-02 wall fix) is what matters and is untouched.

## v0.3.3 — 2026-08-03

Window opened 2026-08-03 (rule 14: the note ships WITH the change, not with the tag).
`CONTRACT_HASH` is unmoved from v0.3.0, so the handshake is unchanged and seeds rolled on 0.3.1+
still connect — `region_locks.rs` regenerates byte-identical. The `data/` hash HAS moved, so a seed
rolled here is not the seed v0.3.2 rolled, and `APWORLD_VERSION` should move when this window is cut.

⚠️ **This window now carries CLIENT changes too**, so it needs a new DLL — the "no client work"
line above is about the CONTRACT, not about the build. (It read "the client needs no work" until the
auto_equip fixes landed underneath it. Corrected here rather than at tag time, which is the whole
point of rule 14.)

### Fixed: auto-equipped gear froze once every slot was full

`auto_equip`'s answer to a full loadout was *clobber the lowest slot*, in three separate places. That
is fine the first time and wrong every time after: the lowest slot becomes the only one that ever
changes again, and every other slot sticks on whatever happened to arrive early.

**Talismans (client #49, issue #342).** With all four slots filled, slots 2, 3 and 4 froze on the
2nd, 3rd and 4th talismans you were ever sent — for the rest of the run. The policy's own stated
rationale was *"a player who has never touched the menu ends up with the four most recent talismans
rather than one"*, which held during the fill and inverted the moment the slots were full, leaving
exactly one recent talisman and three stale ones. New talismans now walk the slots in turn.

**Physick tears (client #48, issue #334).** The same bug two slots wide, and the one that exposed it:
the 3rd tear took mixture slot A, and so did the 4th, so slot B froze on whatever arrived second.

The interesting part is why the talisman half was nearly ruled unfixable. The rotation has to survive
a reconnect — the reconciler replays your **whole** received item set every time you connect, so any
policy that is not a pure function of that replayed stream will silently rearrange your loadout
behind you. Tears alternate on the item's position in the received stream, which replays identically.
Talismans could not do the same, because the number of slots to rotate through *grows* from one to
four as you find Talisman Pouches, so the same stream was being divided by a different number live
than on replay. Measured across 329,760 timelines, that form fails to settle in 8.9% of them.

The fix is that the Talisman Pouch **is itself an Archipelago item**, so how many slots you had
earned at any point is readable from the stream rather than from live state. Same 329,760 timelines,
0 failures. The game's own slot count still bounds what may be written, so a slot you have not earned
can never be targeted; when the two disagree — a pouch sent but never granted — the client says so in
the log instead of silently papering over it.

🛑 **Confirmed by test, not yet on a screen.** The freeze is reproduced as a
failing-without-the-fix replay test in `er-logic`, and the whole client builds green. What no host
test can answer is whether the rotation *feels* right while playing; that is outstanding for both.

### Fixed: two overworld tiles were filed under the wrong region, one in each direction

Both tiles sit on the Limgrave/Caelid border, hold no site of grace of their own, and had their
region inferred from the nearest tile that does. In both cases the distance **tied** between a
Limgrave anchor and a Caelid one, and the tie was settled by the row order of an input table rather
than by any evidence. They fell opposite ways and both were wrong.

**m60_45_39 — Summonwater Village and the Third Church of Marika — was filed under Caelid.**
Twelve checks, the Tibia Mariner's own Deathroot, and the entire field sweep that fires when you
kill him. On a seed that does not keep Caelid none of it was ever created, so felling the boss did
nothing at all. Reported twice: once from a playtest, then again on 0.3.2 — *"killed the boss in
Summonwater Village, got no loot on a Limgrave seed."* He now pays out a 24-member Limgrave sweep.

**m60_47_38 — Fort Gael — was filed under Limgrave.** Fifteen checks, twelve of them named after
Caelid graces (Fort Gael North, Caelid Highway South, Astray from Caelid Highway North). Among them
Ash of War: Lion's Claw and the incantation Flame, Grant Me Strength.

Two "Smoldering Butterfly" checks east of Fort Gael belonged to no sweep at all — the only boss near
enough to grant them stood across the seam, and the sweep pass only assigns within a region. They
have one now.

**Also fixed by the Summonwater pin:** D, Hunter of the Dead stands at *two* points on that border,
and a merchant whose positions land in two different regions has his stock quarantined in the hub and
barred from carrying progression. Both his incantations — Litany of Proper Death and Order's Blade —
are ordinary Limgrave shop checks again.

🛑 **Two tiles is not the class.** The inference still guesses for 99 of the 231 overworld tiles that
hold checks, and still breaks ties by table order. Both of these were found by a player noticing,
not by a gate.

## v0.3.2 — 2026-08-03

A bugfix release, and mostly a client one. `CONTRACT_HASH` is unmoved from v0.3.0, so seeds rolled
on 0.3.1 still connect — but the client and the apworld must still match.

### Fixed: a two-boss dungeon paid out its whole sweep when the first boss died

Reported by bobler, 2026-08-04, within seconds of it happening: *"i just got a bunch of checks
entering a boss room without killing anything, in altus tunnel [...] oh it just gave me the loot for
the boss i killed after anyways, so the client thought the boss died -- the boss itself gave no
loot."*

Altus Tunnel holds the Crystalian **duo**, and a duo is two health bars. A dungeon's sweep members
were collected per MAP and then handed out per ENTITY, so both Crystalians carried the same seven
checks and whichever died first paid for the whole tunnel. The log has the client contradicting
itself about it: the sweep fired at 17:57:11 and the fast-travel gate still read that arena as
boss-alive until 17:58:20, 69 seconds later.

Worse in practice than "checks arrive early". If the arena's second head is not the boss standing in
it -- which is what Matt's randomizer does when it swaps a single boss into a duo arena -- that
head's kill flag is already set when the map loads, and the sweep fires **on entry**. bobler
confirmed exactly that twice, the second time walking into the Fell Twins' arena to find Placidusax
in it. Many players run Matt's alongside this, so it is not an edge case.

The game already answers which head reports a fight: its defeat banner. `GameAreaParam` names a
primary arena for three of them, and for the rest the map's own event script says it outright --
Altus Tunnel waits for **both** Crystalians to fall and then fires one banner, under 32050800. So
only the head that fires the banner may trigger a sweep. Fifteen heads across thirteen dungeons lose
theirs, and **79 checks stop being payable by a boss you have not fought**:

| dungeon | the fight | checks |
|---|---|---|
| Altus Tunnel | Crystalian, Ringblade + Spear | 7 |
| Auriza Hero's Grave | Crucible Knight x2 | 8 |
| Unsightly Catacombs | Misbegotten Warrior + Perfumer Tricia | 3 |
| Minor Erdtree Catacombs | Erdtree Burial Watchdog, Sword + Scepter | 4 |
| Academy Crystal Cave | Crystalian, Staff + Spear | 2 |
| Seethewater Cave | Kindred of Rot x2 | 7 |
| Dragonbarrow Cave | Beastman of Farum Azula x2 | 5 |
| Sellia Hideaway | Putrid Crystalian x3 | 12 |
| Coastal Cave | Demi-Human Chief x2 | 3 |
| Perfumer's Grotto | Miranda the Blighted Bloom + Omenkiller | 8 |
| Abandoned Cave | Cleanrot Knight, Spear + Sickle | 4 |
| Spiritcaller Cave | Spiritcaller Snail + the two Godskins it summons | 9 |
| Divine Tower of East Altus: Gate | the Fell Twins | 7 |

No check left the corpus: every list a suppressed head was holding is still held in full by its
arena's primary, so these bosses drop exactly what they always did -- when you actually kill them.

**Not Sage's Cave.** Black Knife Assassin and Necromancer Garris are two separate fights that happen
to share a cave, and its script fires two banners saying so, so both keep their trigger. Four
dungeons are like that, and they are fixed the other way round -- see below.

### Fixed: two bosses in one dungeon each paid out the other's checks

Four dungeons hold two genuinely separate fights, and each boss was granting the whole dungeon's
sweep -- so killing either paid out both bosses' checks, and the second kill then found nothing
left. Suppressing a trigger is the wrong fix here: both bosses are real, and each fires its own
defeat banner. They now split the dungeon between them.

| dungeon | the two fights | was | now |
|---|---|---|---|
| Black Knife Catacombs | Cemetery Shade / Black Knife Assassin | 4 each | 2 + 2 |
| Auriza Side Tomb | Grave Warden Duelist / (a second head) | 10 each | 5 + 5 |
| Murkwater Cave | Patches / Patches | 4 each | 2 + 2 |
| Sage's Cave | Black Knife Assassin / Necromancer Garris | 14 each | 7 + 7 |

Nothing is lost -- every check is still granted by one of the two, and the totals per dungeon are
unchanged. Each of these eight bosses now grants about half what it did, which is the correction:
granting all of it was the bug.

The split is the same round-robin the legacy dungeons have used since v0.2, and for the same reason:
these are ordinary cave pickups -- boluses, a shield, two Golden Runes -- not boss rewards, so
neither boss owns them. *(Assigning each check to the nearer boss was tried and rejected: in Sage's
Cave all 14 are nearer Garris, so it would have handed him everything and left the Black Knife
Assassin dropping nothing.)*

### Fixed: the id-keyed suppressor was eating vanilla items from every source

`detour.rs` sees only `raw_id` off the AddItemFunc buffer and cannot answer "where did this come
from?", so `checkItemFlags` suppressed a check's vanilla ware **by item id, from everywhere**. Goods
were taken off that mechanism in July by repointing each check's lot at the placeholder;
weapons/armour were left on it under the header note in `features/check_lots.py`:

> "a weapon is essentially never farmable, so it lives in the check-only set and cannot eat a
> legitimate source"

`enemy_drops.rs` refutes that in the client tree — 4891 enemy lots carry no flag (farmable) and its
reroll rewrites *"only the GOODS slots; weapon/armor/talisman drop slots keep their vanilla
contents."* So a farmable enemy can drop a vanilla weapon that backs a check, and every such copy was
eaten. This is the 2026-07-11 Golden Rune [1] incident surviving on the non-goods side.

Since `CAN_WRITE_SLOT_CATEGORY` was wired, non-goods check lots are repointed too — so for any item
id whose **every** backing check is lot-covered there is nothing left to suppress. Those ids are
dropped: **1289 armed ids -> 211**, including all 475 goods and 285 of 367 weapons. 13 partially
covered ids stay armed (`should_suppress` needs every mapped flag collected, so an uncovered backing
check still has something to protect) and 198 lot-less ones stay armed because an EMEVD award has no
source to neutralise.

🛑 **This is a cap, not a cure.** For those 211, a vanilla copy picked up *before* that check's award
fires is still withheld. Closing it needs a source discriminator the detour does not have (#321).

### Fixed: auto_equip never equipped a weapon when auto_upgrade was on

The receive loop queued the **pre**-upgrade FullID while `apply_auto_upgrade` put `base + N` in the
bag, and `auto_equip::tick` looks the queued id up by exact FullID. It missed, went back on
`still_pending`, and retried for the session. Protectors are identity under `apply_auto_upgrade`,
which is exactly the reported asymmetry — armour equipped, weapons never did. The upgrade now runs
inside `enqueue`, so there is one enqueue path and a future caller cannot reintroduce the mismatch.
(#296, #302, #303)

### Also

* Ammunition is no longer a held weapon, so bolts stop replacing your main hand (#294).
* Shields, staves, seals, bows and crossbows auto-equip to the **left** hand, per the French
  Challenge ruleset, instead of disarming you (#301).
* The Hefty Cracked Pot cap was 9 against a DLC that ships 10, so the tenth was reported delivered
  and never arrived (#308). There is no EMEVD threshold for it; the old cap was extrapolated from
  the base-game pots.
* Missing FMG entries are created rather than dropped, so items stop rendering as `?GoodsName?`
  (#300).
* A minimised window wrote 612,842 `[ERROR]` lines in one session; repeats collapse.
* The sealed-region kick names the region, the Lock that opens it, and why your vanilla key did not.
* Four more latched game-state writers re-arm on the in-world edge instead of lapsing after a warp.
* `important_locations` is deleted. It forced 256 checks to reject plain filler from **every** world
  in the multiworld, not just this one — it was frozen, unchosen, and taxing everyone else's fill.

### Gates

Rule 15 (a contract change forces a version change) now has a ledger and a gate. The multiworld
smoke asserts three slot_data properties a solo harness cannot pose — armed flags are collectable,
no flag is owned by two item ids, and two slots emit their own tables — and a `--self-test` proves
each of those guards can go red.

## v0.3.1 — 2026-08-02

A bugfix release. Every entry is a way a seed could quietly become unwinnable or trivially winnable
without saying so. `CONTRACT_HASH` is unmoved from v0.3.0.

### Fixed: the Lock lit a grace on the far side of the wall it was gating

For an ordinary region the "region is open" flag is *derived* to be the region's front-door grace
(`gen_data._front_door`), which is right — receiving the Lock should light the way in. For a region
behind a vanilla wall it is a bug, because the front door is **inside**: Leyndell's is East Capital
Rampart (71102), Raya Lucaria's is Church of the Cuckoo (71402), and the Sewer's is 73501.

`features/graces.py` already withheld those grace bundles while the wall was armed, and did so
correctly. But `core.py:968` shipped the same flag through `regionOpenFlags`, and the client's
`open_on_received_name` sets it directly — so receiving the Leyndell Lock lit East Capital Rampart as
a fast-travel target and you could warp in past the two-rune gate. That is the 2026-07-14
gated-children playtest bug ("walked straight in and ended the run at Morgott") returning through a
door the original fix never watched, with all four of its test folds green throughout.

One bit could not do both jobs — the same shape as the whetblade collision in v0.2.18. The kick latch
gets its own bit: `gen_data._GATED_CHILD_OPEN_FLAGS` pins Leyndell **76980**, Raya Lucaria Academy
**76981**, Sewer **76982**, and `region_open_flags.py` is re-emitted. `core.py` and
`features/area_locks.py` changed **zero lines** — fixing the generated table means all four world
consumers, the test corpus and the client's fallback generator inherit atomically, where a runtime
override would half-apply.

All three flags were probed in game before release: read-false, set, rest at a grace, Alt+F4,
relaunch, read-true — with the flag block's base pointer moving between runs (`24927E70080` ->
`2F1A6ED0080`), which is what proves the bits came off disk rather than surviving in memory. A
quit-to-menu is **not** sufficient for this class of test.

⚠️ **New seeds only.** A seed already rolled carries 71102/71402/73501 in its slot_data forever.

### Fixed: the capital's rune wall could be armed below vanilla's two

`generate_early` did `want = min(want, len(_available_runes()))`, on the theory that lowering a
requirement is always safe. It is not: our N is data-driven, the game's capital gate is a fixed
two-Great-Rune wall that does not clamp with us, and while our wall is armed `features/graces`
withholds the capital bundle so the physical gate is the only way in. At N=1 logic believes one rune
opens Leyndell, the game still wants two, and fill may place a region Lock behind a door the player
cannot open.

Two ways in with no warning: `num_regions` keeping exactly one Great-Rune region, or writing
`leyndell_runes_required: 1`, which the `Range(0, 6)` allows. An armed wall is now floored at
`VANILLA_CAPITAL_GATE_RUNES`; when the pool cannot supply two we **disarm** — empty bundle list, the
bundle is granted on the Lock, the player warps in past the physical gate — reusing the already-sound
N=0 path rather than arming low. No change on the shipped default.

Settled while chasing it: the capital gate reads no possession at all. It counts a band —
`CountEventFlags(EventFlag, 190, 199) >= threshold` in common `$Event(720)` — and 191-196 are set by
the Divine-Tower altar initializers through common event `90005110`, which removes the unrestored
rune (goods 8148-8153) and awards the restored lot. So the restored-goods ids and the restored-flag
ids genuinely coincide, that resemblance is FromSoft's parallel numbering rather than our error, and
`keyitems.rs` has been writing the right flags all along. Six rows classified obtained_flag/datamine;
the unknown ceiling drops 25 -> 19. The band is pinned in the test, because a stray flag outside
190-199 would be silently uncounted — the one way this can rot with nothing failing.

### Fixed: legacy boss kills paid out in the wrong region

`_lreg` had two silent failure modes, both found by pulling on **Alaric**'s observation that "Ashen
capital should have 3 bosses: Gideon, Godfrey/Hoarah Loux, Radagon/Elden Beast" and it had none.

- **A tie broken by `Counter` insertion order.** `m11_05` votes {Leyndell 3, Ashen Capital 3,
  Limgrave 1}; `m19_00` votes {Leyndell 1, Liurnia 1}. Nothing decided Leyndell — `most_common()`
  did. Consequence: 42 of Leyndell's 64 divvied checks hung off the four post-burn triggers, and the
  Erdtree burn warps you into `m11_05` **permanently**, so those grants could never fire from base
  Leyndell. Dead on arrival.
- **`or HUB` swallowed the no-vote case.** `m12_04` (Astel), `m12_08` (Ancestor Spirit) and `m12_09`
  (Regal Ancestor Spirit) get no `_mreg` vote at all, so all three paid out **Roundtable Hold** — 13
  checks in a region open from turn one, for kills in the Eternal Cities.
  `boss_data.REGION_BOSSES["Roundtable Hold"]` is `None`; the hub has no bosses and never did.

The curated pin was also consulted *after* the vote, so it could only rescue a map with no votes. The
pin now beats the vote, and `or HUB` is deleted in favour of a generation-time assert naming every
unrouted map. Roundtable Hold 13 swept checks -> **0**; Ashen Capital 0 -> **3**; corpus 3197 ->
3187; cross-region leak 0 before and after. Triggers 241 -> 240, because the Ashen Capital's 3 checks
across 4 triggers leave Radagon (`19000810`) an empty slice — harmless, since Radagon and the Elden
Beast are one fight and `19000800` carries it, but it is why `SWEEP_REGION` is not a boss roster.

Every region came from committed tables — `dungeon_regions.tsv`'s grace join, `check_maps.tsv`, and
each boss's own drop region — not from memory of the game. `boss_data` already disagreed with
`boss_sweeps` in both cases; that disagreement *was* the bug report.

### Fixed: no somber smithing stone tier had a presence floor

`_draw_stones` did `if somber: return out` immediately after the weighted draw and **before** the
deepest-first top-up, so the guarantee that module advertises was regular-Smithing-Stone-[1]-only.
The draw is an i.i.d. weighted sample with replacement, so at `num_regions: 1` (~19 draws, taper
share 1/9 for the deepest tier) the per-seed probability a tier is simply absent measures **[3] ~6%,
[8] ~42%, [9] ~73%**.

A somber weapon costs one stone per level and the tier *is* the level, so an absent tier is not a
thin economy — it is a permanent wall at that exact rung. Tiers 1-9 are now each guaranteed present,
paid for by converting the deepest **surplus** stones already drawn (a tier never donates its last
copy); the reservation is never grown. Stones already on kept locations count toward the floor, so
the guarantee does not spend a slot covering a tier the seed has. Below 9 donors the floor covers the
shallowest tiers first and warns by name with the level a somber weapon cannot pass.

Reported by **Lonelyguy89** on a 1-region seed: "zero Somber Smithing Stone [3] in the game."

Note `fuzz_gf.py` skips `curated_filler` ("no finite domain"), so the fuzz gate never varied the
`somber_stones` weight and could not have found this.

### Fixed: a boss below the Grand Lift of Rold could hold progression

`f530505`, Gargoyle's Black Blades — the Black Blade Kindred below the lift — is filed "Mountaintops
of the Giants" and was progression-eligible. Rold is deliberately not in logic (README: "You never
need the Rold Medallion to reach the Mountaintops of the Giants"), so a Mountaintops-anchored player
cannot stand on that ground: the Rold Medallion is a **Leyndell** check. Fill was free to put a
region Lock or a required Great Rune there. The seed is unwinnable; the character is not, since the
Roundtable warp always works.

The class, not the instance. Two derivations produce a region from a tile and the bar watched one:
`_mtile`, the descriptor tile, and `MSB_TRUTH_MAP`, which `region_of()` ranks **above** it and which
actually produced the region for 2467 of 4875 checks. f530505's descriptor tile `m60_39_53` is
anchored, so the guard waved it through, while the tile that produced its region — MSB `m60_49_52` —
is graceless Forbidden-Lands ground nearest-neighbouring onto the `m60_49_53` seam that carries
graces for **both** regions. Two checks on that same ground were already barred and the boss check
was not.

`region_of()` now records `MSB_TILE_PROVENANCE` — only flags whose region it actually *answered*
through an MSB tile — and the bar judges both tiles. **Union, not precedence, and that is measured:**
judging the MSB tile *instead* would un-bar two checks barred today (f520300 Viridian Amber
Medallion, f400299 Bernahl's Bell Bearing, whose tiles disagree about which side of the map they are
on). `DEFAULTED_REGION_APS` 504 -> **515** of 4875: +11 barred, 0 un-barred, across Mountaintops (5),
Caelid (4), Altus (1) and Mt. Gelmir (1). No key item, Great Rune, medallion or Seedtree is in the
set.

Reported by **Lonelyguy89** on a 2-region seed, softlocked in the Forbidden Lands with the medallion
in Leyndell.

⚠️ **Known cosmetic residue:** for 13 checks the descriptor tile and the MSB tile disagree, and the
descriptor still wins the *name* while MSB wins the region — so f530505 reads "Mountaintops of the
Giants :: Gargoyle's Black Blades - around Bridge of Iniquity", and Bridge of Iniquity is Mt. Gelmir.
The region is safe either way (all 13 are barred); only the label is wrong.

### Fixed (client): an equipped Great Rune was re-granted forever

`inventory_has_goods` decided possession by walking the three inventory backing lists. An equipped
Great Rune is not in any of them — the game holds it in `equipment.equip_item_data.great_rune` — so
the readback reported absent, the reconciler re-granted, the game refused because you *do* have it,
and the refusal is a modal popup that reappears the instant you close it.

Possession is now **the three bag lists ∪ the great-rune equip slot ∪ the storage box**. The handle
is resolved off the pinned crate source rather than guessed: goods are never `is_indexed`, so the
gaitem table is a dead end and `selector()` carries the bare param row, guarded on
`GaitemCategory::Goods` (3 — a different enum from the `ItemCategory::Goods` (4) the bag walk uses).

Honest framing: the underlying mechanism is still unconfirmed in game. This makes the readback
strictly more permissive — it can suppress a wrongly-repeated grant, never cause one — so if the true
cause is elsewhere it masks rather than fixes, and the forensics line that would identify it is kept
deliberately. The `MAX_GRANT_ATTEMPTS = 3` guard from v0.2.17 remains the backstop, so even an
unfixed cause degrades to three popups rather than a wall.

⚠️ **An item in your storage box now counts as owned and will not be re-delivered.** Withdraw it and
lose it and the next tick delivers it again, as before.

### New: `auto_equip` — wear whatever you are sent

Off by default. Turn it on and every weapon or armour piece the multiworld hands you is put on the
moment it lands in your bag, replacing whatever was in that slot — mid-boss-fight included, and
regardless of whether your build can use it. You do not pick your kit; the item order does. This is
the "use what you get" challenge format (the French Challenge run: Wretch start, randomizer,
use-what-you-get, permadeath), and with the region locks and goal this apworld already ships, it is
now a setting rather than a stack of third-party helpers.

⚠️ **The client has had this working for weeks and nobody could use it.** `auto_equip.rs` reads
`slot_data["options"]["auto_equip"]`, and the apworld had never sent that key — an absent key parses
as `false`, so the feature was off for every Elden Ring seed ever generated, silently. This release
is the apworld half.

**A seed with `auto_equip: true` requires a client that supports it and will refuse to connect to
one that does not**, naming the feature. That refusal is deliberate: adding an option does not move
`CONTRACT_HASH`, so without it an older client would report `VERSION: OK`, never see the key, and
run your seed with the setting quietly ignored — exactly the failure above, one release later.
Leave it off and nothing changes; any client still connects.

**Validation, stated plainly.** The memory mechanism is verified, and verified thoroughly: on a live
game with Cheat Engine, writing all four representations Elden Ring keeps for an equipped item
equips it, renders it correctly in the equipment menu, and survives being unequipped by hand — on a
character that had never held the item. That is the half that could have silently destroyed your
gear. A naive handle write never acquires the refcount, so the next menu unequip drops it to zero
and the item disappears from your inventory an interaction later, far from the cause; going through
the game's own refcounted commit is what avoids that, and it was proven before a line of the
shipping code was written.

🛑 **What has NOT had a full playtest is the mod's decision-making on top of that mechanism** — the
probe is told which slot and which item, and the client works both out for itself. Untested in a
real run: weapon-versus-armour routing, shields (they should go to the left hand and that is
explicitly unconfirmed), what happens when gear arrives mid-fight, the retry when an item is
received before the game has finished granting it, and whether an auto-equipped item survives a
save-and-reload. Default is off. If you turn it on, treat it as new — and not on a character you
would mind losing.

### Fixed: two Golden Seeds pointed at the wrong grace, and two more said "region unconfirmed"

From a live playtest (Alaric, in game, 2026-08-02).

A Liurnia Golden Seed read *"near Academy Gate Town"*. That grace is **872 m** away and 27th-nearest;
a player following the descriptor walks to the wrong end of the lake. It now reads **"near Main
Academy Gate"** (184 m). The nearest grace in raw 3D is actually East Gate Bridge Trestle at 86 m --
but 75 m straight down at lake level, while the seed sits up on the raised causeway, so the closest
answer is the one you cannot walk to. A second Liurnia Golden Seed now reads **"near Academy Gate
Town"** instead of "near Fallen Ruins of the Lake": the Fallen Ruins grace is 47 m closer on the tape
measure and the Gate Town is the landmark you actually navigate by. Someone walked both.

Two checks also stop hedging. `Weeping :: Golden Seed - near Castle Morne Rampart` and the Liurnia
seed above were labelled **(region unconfirmed)** and barred from *hosting* progression, because
their region came from a tile-neighbour vote rather than from ground anyone had seen. Both were
collected in game this session, in the region we had guessed. The hedge costs twice when it is wrong
-- the name tells you we do not know something we do, and the progression surface stays smaller than
the map -- so the label is gone and each is an ordinary progression-eligible check again. This is the
mirror of v0.3.0's "two Liurnia checks can no longer be required": the same list, run the other
direction, and only ever per check, never per tile.

### Compatibility

`CONTRACT_HASH` is **unmoved** from v0.3.0 — 87 keys, identical names, shapes, required-ness and
profiles — so a v0.3.0 client and a v0.3.1 apworld still handshake.

The one exception is a seed that turns `auto_equip` on: that seed declares the feature in
`requiresClientFeatures` and needs a v0.3.1 client. A seed that leaves it off (the default) declares
nothing and is unaffected.

⚠️ **Client update recommended.** The re-grant fix is client-side and an old client connects happily
without it.

No option changed its default or its meaning, and nothing here moves an item or a check in a seed
already in progress. A v0.3.0 yaml generates a v0.3.1 seed with no edits. The gated-child, somber,
Rold-seam and descriptor / region-confirmation fixes are all generation-time and reach **new seeds
only**.

## v0.3.0 — 2026-08-01

**Client update required.** The slot_data contract moved from `d970dd88` to `5e8b11c9`
(`goalRequiredItems` and `scaduBlessingCap` were added). A v0.2.x DLL will report a version
mismatch against a v0.3.0 apworld, and it is right to: it cannot enforce the new goal condition.
Ship the apworld and the DLL together.

**Two defaults changed and they change what an old yaml does.** See "Migration" at the end of this
entry before you reuse a v0.2 yaml.

### New: a `goal` option

`goal` picks what ends the run — `auto`, `elden_beast`, or `promised_consort`. A *named* goal
force-keeps its own region, so you can no longer roll a seed whose ending is not in the seed.
`auto` is the previous behaviour and is rng-stream-identical to v0.2.19; an impossible combination
now raises an `OptionError` at generation time instead of producing an unwinnable seed.

### New: the Scadutree Blessing is finally game-wide

Both shipped blessing modes were **inert outside the DLC for their entire life** — the blessing rung
only ever applied inside the Shadow Realm. The client now clones the rung onto `SpEffectParam` row
`20012081`, which the base game reads too. The curve is capped at **12**, and the option is
`global_scadutree_blessing`, which until now could not be set from a yaml at all (the class default
was frozen). Default is still off.

### New: Scadutree Fragments are actually put in the pool

The blessing cap exists to bound an *injection* — and the injection had never been built. Until now
the only mention of the fragment curve anywhere in generation was inside the comment explaining the
cap, so the ceiling sat over a supply that arrived purely by luck of the DLC draw. Measured across
40 seeds a row on the shipped default of six regions: **one seed in forty** could reach the cap.
Fragments are now injected to meet it, and a DLC seed injects none because it already has them.

### New: a region unlocking says so on screen

Receiving a Region Lock — the most consequential item in the seed — produced nothing in game. The
line existed, but only in the AP console. There is now a toast, and it announces the *effect*
rather than the receipt: "Region unlocked: Liurnia", not "you received Liurnia Lock", which is a
receipt you have to translate. It reuses the console line's exact wording so there is one phrasing
to learn.

One deliberate gap: AP replays your entire received stream when you connect, so the first pass
after connecting cannot tell a real arrival from a replay. A lock that lands in that window is
logged but not toasted. Silence there beats six false toasts every time you reconnect.

### New: region-lock hints you can afford

Hint pricing was denominated over the whole location table, which made a region lock cost more than
anyone accumulates. It is now denominated over the ~158-check progression surface and tracks the
host's own `hint_cost`, with a ledger in AP data storage so a hint bought once stays bought across a
reconnect. There is a tracker button for it.

### The client repairs your save after a crash

Archipelago and Elden Ring disagree about whether the past can change. A check, once sent, is on the
server forever. A save can move backwards — Alt-F4, a crash, a restored backup. Left alone that
combination is pure loss: the checks stay spent and whatever they gave you is gone, silently.

The reconnect record lives *inside* the save, so it rewinds with it. On reconnect the client
compares what the save remembers against what the server already delivered and re-delivers the
difference — items and world state both, so a region that had opened re-opens.

Verified in the field on 2026-08-01: a hard Alt-F4 seconds after three pickups came back to a save
25 seconds behind where it was left. All three items were re-delivered on reconnect. Picking the
locations up again gives the ordinary item and does **not** send the check twice or grant a second
copy.

Two honest limits. It only restores what Archipelago delivered — runes, ordinary pickups, boss
progress and your position still go back with the save. And it is not a licence to save-scum: the
checks you already sent stay sent.

### Fixed: the crash on fast travel

Instrumented across six crashes from one player's session, all six faulted **8 bytes below** our FMG
block — the allocator header of a 64 KB-aligned `VirtualAlloc` region that was never mapped, because
`VirtualAlloc` rounds a reservation to the allocation granularity and we had asked for exactly the
payload. Six hits, zero misses, one allocation site. The block is now padded by a page.

### Fixed: reconnecting to a different room leaked 229 checks into it

The seed-marker guard was asked once, at connect, and never again. Change rooms mid-session and the
client kept sending the previous seed's checks — 229 of them, measured. The guard is now re-asked
mid-session and fails closed.

### Fixed: a REFUSED session looked identical to a working one

When the client refused to attach it did so silently. A player spent 55 minutes assuming the mod was
broken. REFUSED now raises a toast that says so.

### Fixed: the goal could fire two regions in

Completion was inferred from boss flags alone, so on a rolled seed the goal region could be the
*second* region you reach — measured at **25% of seeds**. The kept Region Locks must now be held
before Goal is sent.

### Fixed: two toast defects

An em-dash rendered as `?` in-game (the FMG path is ASCII-only; there is now a test that says so),
and the scaling-tier fraction described the vanilla ladder rather than the seed's own band. The
region-scaling toast also gained a production caller — the strings shipped in v0.2.18 with none.

### Fixed: items could stop arriving forever, and nothing said so

Reported on v0.2.18: a multiworld's room changed port, the client reconnected cleanly and kept
*sending* checks — and never received another item again, from anyone, including itself. A fresh
character got no starting lock either, and reinstalling changed nothing.

The client decides who delivers an item from *configuration*, then stands down so the two grant
paths can't both fire. It never checked whether the owner it stood down for actually existed. If
the reconciler never armed — which happens when the inventory pointer is never captured, and
another mod hooking the game's item-pickup function will do exactly that — the client skipped its
own grant, skipped the guard that holds the cursor on a failed placement, advanced the
received-item cursor anyway, and wrote that to disk. Every item after that point was consumed
silently and permanently.

Ownership now requires an armed, un-refused reconciler. Anything else falls back to the old grant
path, which holds its cursor and retries, so the failure mode is a stall you can see instead of a
loss you can't. Two supporting changes: a session that is not going to deliver now says so on
screen rather than looking healthy, and the log carries a single `[reattach]` block stating every
fact behind the decision — identity, marker verdict, both cursors, armed, refused, inventory.

### Fixed: skipping the opening cutscene made you confirm every map

If you sat through the opening cutscene your maps appeared silently. If you skipped it, you had to
click OK on every single map the first time you opened the map screen. One player had learned to
wait in the cutscene until the item ticker moved.

Map reveals are event flags, and they were gated behind an eight-second settle timer. That timer
exists to distrust the *inventory pointer* after a save load. Flags never touch the inventory. The
timer was landing them after you regained control, and the game announces a map revealed while you
hold control. Flags now apply on the first in-world tick; item grants keep the settle, which is
what it was written for. Map reveals that arrive mid-run — from a region lock — still prompt.

### Fixed: a new character on a used save slot got no starting items

"Start items already granted" was stored per seed and slot, with nothing in the key identifying the
character. Roll a new character into a slot you had played and it inherited "already granted" and
started with nothing.

The client now decides by **possession**: it grants whatever is not in your bag. That is
per-character for free, because the bag is, and it cannot go stale the way the old flag did — it
also survives a reload, and re-delivers a start item that a save load wiped. This works because
every start item is durable (flasks, pot vessels, lantern, whetblades); a test now enforces that,
so a consumable can't be added to that path and silently refill every launch.

### Fixed: the start-item backfill reported items it never delivered

The backstop that grants missing start items was measured in one session declaring 32 of 35 absent
off a scan that saw only 17 items, hard-failing 10 of them, quietly capping about 18 to zero and
recording those as delivered. Its summary line claimed 22 of 32 granted. None of those numbers were
true.

Two causes, each correct somewhere else. A pot grant that hits the delivery cap reports success —
right for the item ledger, since the item is as delivered as it will ever be, and wrong for anything
checking the bag. And the scan could run against an inventory that was still filling, so items you
were holding read as missing. It now never reports an item delivered unless a later scan actually
sees it, waits for two consecutive matching scans before trusting one, keeps retrying until nothing
is missing, and names the exact items in the log if it genuinely cannot deliver them.

### Fixed: the game-wide blessing switched itself off when you used it

The blessing level was read by counting Scadutree Fragments **in your bag**. Revering at a DLC grace
consumes them. So a player using the blessing the way the game intends drained their held count to
zero, the derived level collapsed with it, and the game-wide blessing turned itself off mid-run —
and nothing clamped it to raise-only, so the applied rung genuinely fell.

It is now driven by fragments *received*, which AP replays in full on every connect, so the count
survives reconnects, save loads, and anything the game does to your inventory. Matched by item id
rather than name, so a foreign apworld that calls its fragments something else still counts.

### Fixed: quitting with Alt-F4 was reported as a crash

Elden Ring executes a breakpoint instruction on its Alt-F4 teardown path. With no debugger attached
nothing handles it, so it reached the crash handler and was written out as a native CTD, complete
with a backtrace at a stable address. In one playtest log that made **five ordinary sessions look
like four crashes** and produced a confident wrong verdict about an open crash bug. Breakpoints are
now classified separately. The record is still written — a breakpoint inside our own DLL still
matters — only the "process dying" banner is gone.

### Fixed: a crash during generation was reported as a hang

Stock `Generate.py` ends by waiting on "Press enter to close". A generation that *crashed* then sat
on inherited stdin until the tooling timed out, so a real failure surfaced as a 900-second hang with
no diagnosis. Every invoker now closes stdin, and the set of invokers is derived rather than
maintained by hand — the original audit found five by reading twelve files, and a hand-kept list
goes stale silently on the sixth.

### Fixed: two Liurnia checks can no longer be required

Two checks were barred from *hosting* progression on suspicion: a Sacred Tear "around Ruin-Strewn
Precipice" and a Golden Seed "near East Gate Bridge Trestle". The Sacred Tear is our
lowest-confidence placement of the thirteen on three independent signals, and it could not be found
in game at the named grace. The checks themselves are real and stay collectable; only their ability
to hold something you *need* is removed. Being wrong this way costs a filler item somewhere
awkward; being wrong the other way strands a run. The Pilgrimage tear was also re-regioned.

### Also fixed

- A death-cam crash guard was present at four of **five** sites — the fifth walked the player's
  effect list every frame while the engine was tearing it down, which is a native crash. All five
  now call one implementation.
- Region-scaling telemetry read the raw difficulty option rather than the seed's own band, so every
  default seed logged a flat curve in the client log.

### Migration — read this before reusing a v0.2 yaml

- 🛑 **`num_regions` now defaults to 6, not 0.** A yaml that omits `num_regions` used to roll the
  full 30-region spine; it now rolls a **6-region seed**. If you want the whole map, say
  `num_regions: 0` explicitly.
- 🛑 **`num_regions_order` now defaults to `rolled`, not the spine.** Omitting it gives you a random
  start region rather than Limgrave.
- The three shipped presets were re-derived against the new defaults; two of the five were silently
  reinterpreted by the flip and are corrected here.
- The unused top-level `global_scadutree_blessing` slot_data key was removed. Nothing read it.
- No option was renamed or removed. A seed generated on v0.2.19 and already in progress is
  unaffected: the absent `goalRequiredItems` key reads as an empty requirement, exactly as before.
- The client's save file no longer records "start items already granted"; possession replaces it.
  A v0.2 file is read normally and the stale key is ignored, so there is nothing to delete.

## v0.2.18 — 2026-07-30

### Fixed: a shop row priced below the item's own value was dropped from the menu

Elden Ring excludes a `ShopLineupParam` row whose `value` is under the ware's `sellValue`. Money
runes hit that **by construction** — a rune's `sellValue` equals its payout, and the price roll is
`[0, worth]` — so every rune priced as a bargain, which is the entire point of the feature, made
itself invisible. Never rune-specific: a stray Veteran's Helm discounted below its sell value
vanished the same way.

Fixed by **lowering the ware's `sellValue`**, not raising the row's price. Raising it renders the row
and destroys the feature (a rune could never again be a bargain). On a rune `sellValue` is redundant
data — the payout is read from `SpEffectParam.soul`, verified across all 35 rune rows — so lowering
it costs nothing. Sell-back is capped just under what you paid, so there is no money pump; other
merchants selling the same ware keep their own prices.

`ER_SHOP_VALUE_CLAMP=raise` restores the old behaviour with no rebuild.

Reported three times by **Alaric**; the third report is what ended the wrong explanation.

### Fixed: money-rune pricing missed every DLC rune

Rune-ness was an anchored name whitelist — `Golden`, `Hero's`, `Lord's`, `Numen's`. It matched all 21
base-game money runes and **none of the 11 DLC ones** (Shadow Realm [1]-[7], Rune of an Unsung Hero,
Marika's, Leda's, Broken Rune). A miss was not a skip: an unmatched rune fell through to the generic
price path, which for a rune is `sellValue * 10` — *exactly* the 10x bug the code existed to remove,
re-introduced on every DLC rune through two prior "fixed" releases.

Rune-ness now derives from `RUNE_PAYOUT` (`EquipParamGoods.refId_default -> SpEffectParam.soul`), so
a future DLC needs no edit. The retired regex survives as a cross-check in the tests: everything it
used to match must still be priced.

### Fixed: the infinite shop shelves were pointed at menus, not shelves

`reroll_infinite_shop_stock` selected on `eventFlag_forStock == 0` — the exact **inverse** of what
marks a shop check, which reads as "rows that can never be checks" and is not. It collected 455 rows
belonging to the Alter-Garments menu, the Ash-of-War duplication menu and debug entries. No player
can browse those, so the reroll changed nothing buyable and corrupted the menus it did touch.

The predicate now derives a browsable shelf from what one is (real `equipId`, no material cost, no
release gate, unlimited quantity, `eventFlag_forStock > 0`). **Fourteen rows qualify** — Kalé's glass
shards, Iji's somber smithing stones, the throwing-knife and poison-dart racks and their neighbours.
Ammo shelves stay excluded deliberately.

### Fixed: receiving a whetblade collected its own location

Each whetblade unlocks several Ash-of-War affinities and the game tracks them one flag apiece (Iron:
Heavy 65610, Keen 65620, Quality 65630). The **first** affinity's flag is also the lot's
`getItemFlagId` — this world's check flag for that location. One flag, two jobs. The client set it to
unlock the affinity, which simultaneously marked the location found and despawned its treasure: the
item placed there went out as though you had found it, and the chest stopped spawning.

Not fixable by choosing a side — skipping the flag costs an affinity instead. The two jobs are split:
the affinity keeps the vanilla flag, and the check moves to a client-owned adjacent flag
(65611/65641/65661/65681/65721 — same allocated block, unreferenced across the EMEVD corpus,
`flag_lots`, `check_maps`, `region_map` and `esd_flags`). The lot repoint and the poll repoint come
from one table, so writer and watcher cannot drift.

Ground truth for the per-affinity flag map came from the Hexinton CE table. **A whetblade received on
an earlier build already collected its location; that is recorded server-side and cannot be undone.**

Bell Bearing / Whetstone Knife / Rold Medallion / Drawing-Room Key share the collision but have no
lot to repoint (their flags are ESD/EMEVD-set), so their false-collect stands — tracked separately.

### `maximum_enemy_difficulty` defaults to `auto`

Enemy scaling targets a region's **position in your unlock order**, normalised so the deepest kept
region tops out. Right for a long seed, wrong for a short one: with five regions the deepest is
reached quickly and still scaled as "the end of the run", while weapon upgrades sit on a fixed
ladder a short seed does not accelerate — endgame enemies on mid-game gear.

`auto` lowers the ceiling with the length of the run, `pct = round(100 * (n/30) ** (1/3))`, resolved
in **ladder-index space** (multiplier space resolves down a rung and silently changes nothing):

| regions | ceiling |
|---|---|
| 5 | 4.125x |
| 8 | 5.484x |
| 12 | 6.688x |
| 30 / `num_regions: 0` | 7.422x — unchanged |

⚠️ **Behaviour change by default.** Set `maximum_enemy_difficulty: 100` for the old uncapped curve.
Only ~3.7x at five regions has been played; everything above is extrapolation, and the option
docstring says so.

Prompted by **Alaric**'s Patches fight and **CrazzyMatthew21**'s "unclear at which points im supposed
to be in which areas".

### New: `infinite_hub_wares`

Name up to four items the hub merchant always stocks, unlimited:

    infinite_hub_wares: ["Rune Arc", "Larval Tear"]

Four is how many browsable unlimited shelves the hub has; a fifth is rejected at generation with a
message. Each ware sells at its own derived price. Empty by default. Worth a thought before filling:
unlimited Larval Tears is unlimited respec, unlimited Rune Arcs a permanent great-rune buff.

### New: `no_runes_in_shops`

Keeps your own money runes off every shop check and out of the rerolled shelves. Off by default.
Scoped by `SHOP_ROW_FLAGS` membership (561 rows), not by tag; rune-ness from `RUNE_PAYOUT`, so all 31
catalog money runes are covered including every DLC one. Great Runes are not in `RUNE_PAYOUT`, so no
progression item is ever forbidden. Skips enforcement with a logged reason rather than risking a
`FillError` if the pool cannot supply.

### Gems, weapons and armour sell again

Gems sell natively (135 vanilla `equipType 4` rows support it). The floor deciding what was sellable
had been goods-only, so weapons and armour read as worthless.

### Stability

Three guards, two of them generalising fixes that previously covered a single caller each — patching
the instance and leaving the mechanism is what put the same crash in front of players more than once.

- **The inventory pointer is retired at warp REQUEST**, not only on arrival. A warp tears the origin
  map down first and `in_world()` still reads true through it, so grants ran against memory the
  engine was freeing. The static-slot primer is held 3000 ms so it cannot recapture the dying object.
- **Enemy scaling stops during the death-cam.** Three other features already skip work while
  `hp <= 0` because mutating those structures mid-teardown crashes; the scaling sweep touches the
  same structures on every enemy in the area and had no such check.
- **Event-flag writes are bounded like item grants.** A flag the game silently discards was rewritten
  every frame forever (unpaced, ~60/s); it now parks after three unobservable attempts and says so.
  A flag vanilla merely **contests** reads back fine and is never parked, so nothing legitimate stops
  being re-asserted.

Also: the overlay title now shows the build SHA. `0.2.17` named two different client builds — the
version bump landed before the grant-guard fix — so "I'm on the new version" was true and useless.
Start-of-run Perfume Bottles and Hefty Cracked Pots asked for 10 where the delivery cap is 9; the
tenth silently vanished, and a capped pot grant now warns once instead of reporting success.

### Compatibility

`CONTRACT_HASH` is unmoved (`d970dd88`), so a v0.2.17 apworld and a v0.2.18 client still handshake.
⚠️ **Client update required** — most of the above is client-side, and an old client connects happily
without any of it. Confirm with the overlay title or the `ER-AP client` line in the log.

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
- **Dungeon sweeps**, **pool building + varied filler**, **grac
