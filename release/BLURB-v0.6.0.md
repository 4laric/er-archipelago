# v0.6.0 — alpha release blurb (draft)

The v0.6 alpha puts the AP tracker onto MapForGoblins' in-game map. The bundle includes
matching client and map-engine builds, with gathering-node clutter hidden in its preset.
Your actual treasure checks remain eligible, including crafting-material pickups.

Enable a session map workflow in F6: following map pins, coloring pins, or sharing check
states. Check-only filtering then shows pins matched to your connected seed. You can also
select progression-only or in-logic-only, and enlarge progression highlights. Progression
marks places eligible to hold progression; it does not reveal an unhinted item's contents.
In-logic means tracker region access. Extra quest, key and puzzle requirements are still
outside that filter, and checks with unresolved pin identities may not appear.

F5 activity now uses shorter location labels and AP/Universal Tracker item colors:
plum for progression items, blue for useful items, salmon for traps and cyan for filler.
Session display markers distinguish progression-surface checks (`[P]`) and sweep completions
(`[S]`). A sweep completion does not mean you physically visited that pickup.

MapForGoblins is an accepted placement reference for our location audit. That gives us much
more concrete placement coverage, while ambiguous identities and disagreements remain
visible for follow-up. The overall access audit is still unfinished; this is an alpha for
trying the integration and reporting remaining problems, not a claim of complete logic coverage.

## What you need to update

- **Client:** Required — use the client bundled with this alpha for v0.6.0 seeds.
- **APWorld:** Host-only — the room host or generator must install the matching APWorld.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible when kept on its matching client/APWorld pair.
- **Profile/assets:** Reinstall or replace with this alpha's matching DLLs, configuration and loader profile.
- **Release channel:** This prerelease does not promote stable or beta.

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

Release packaging and live smoke results belong in `ALPHA-v0.6.0.md`. Publication remains
pending until the release checklist has been completed.
