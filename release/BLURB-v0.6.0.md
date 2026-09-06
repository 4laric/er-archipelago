# v0.6.0 — release blurb

## Can I update the client during a run?

**Yes, for an existing v0.6.0 run using the matching seed-data contract.** Exit the
game and replace the paired client and map DLLs; keep your save and map settings.
For a v0.5.x run, keep its matching client/APWorld pair rather than upgrading it to
v0.6.0 mid-run. Install the v0.6.0 APWorld when generating a new v0.6.0 seed.

## What you need to update

- **Client:** Required — use the client bundled with this release for v0.6.0 seeds.
- **APWorld:** Host-only — the room host or generator must install the matching APWorld.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible when kept on its matching client/APWorld pair.
- **Profile/assets:** Reinstall or replace with this release's matching DLLs, configuration and loader profile.
- **Release channel:** Stable v0.6.0.

## Bundled map integration

**Temporary icon fallback:** v0.6.0 omits the Flower atlas override to avoid wrong weapon
icons and missing class previews. AP placeholders use the Telescope icon; AP names
and gameplay still work. Existing installs must disable or restore old Flower overrides
as described in SETUP.md.

The v0.6 release puts the AP tracker onto MapForGoblins' in-game map. The bundle includes
matching client and map-engine builds, with gathering-node clutter hidden in its preset.
Your actual treasure checks remain eligible, including crafting-material pickups.

Connect and open the map: check sharing and pin coloring start automatically. The
fresh preset shows only pins matched to your connected seed. Use F10 → Archipelago for
optional progression-only and in-logic-only filters or to resize progression highlights.
Following map pins and player-review tools remain off by default in F6. Progression
marks progression-surface places, excluding pickups granted by an enabled boss sweep;
the map highlights the granting boss instead. F6 stars and F5 `[P]` still describe the
original seed surface. None of these marks reveals an unhinted item's contents.
In-logic means tracker region access. Extra quest, key and puzzle requirements are still
outside that filter, and checks with unresolved pin identities may not appear.
A granting boss without a native MapForGoblins pin cannot receive a map highlight;
the associated checks remain available in F6.

The default highlight size is 1.5x. F10 opens MapForGoblins settings without the client
stamina diagnostic. Missing live item names keep a valid original label instead of
showing `[ERROR]`, and current check states take precedence over old orange highlights.

F5 activity now uses shorter location labels and AP/Universal Tracker item colors:
plum for progression items, blue for useful items, salmon for traps and cyan for filler.
Session display markers distinguish progression-surface checks (`[P]`) and sweep completions
(`[S]`). A sweep completion does not mean you physically visited that pickup.

MapForGoblins is an accepted placement reference for our location audit. That gives us much
more concrete placement coverage, while ambiguous identities and disagreements remain
visible for follow-up. The overall access audit remains unfinished; stable release status
does not certify every access rule or imply complete map-pin coverage.

## Other changes in the v0.6 window

Normal weapons can cost one Smithing Stone per upgrade; the existing two-stone default
remains available. Collected Scadutree Fragments strengthen you everywhere by default,
with the explicit DLC-only option retained. Flask and fragment placement uses a soft
preference for important checks rather than making fill fail when that surface is full.

The player notebook focuses on the place, region-lock assignment and collection requirements,
including unused or unobtainable checks. Acquisition flags are searchable and copyable.
Enable **Help verify locations (this session)** in F6 to reveal Review and Map actions,
including for completed checks. These open the notebook; they do not submit a report.
Save or copy your notes and follow the sharing instructions to send them to the project.

Release packaging and live smoke results belong in `RELEASE-v0.6.0.md`. Publication remains
pending until the release checklist has been completed.
