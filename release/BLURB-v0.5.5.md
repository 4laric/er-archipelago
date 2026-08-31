# v0.5.5 — release blurb

## What you need to update

- **Client:** Required — use the v0.5.5 client with v0.5.5 seeds.
- **APWorld:** Host-only — the room host or generator must install the matching APWorld.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.** Mine-material rerolling defaults
  on; set `reroll_mine_materials: false` to keep vanilla mine rewards.
- **Existing seed/save:** Compatible — keep active seeds on their matching client/APWorld pair;
  the new option affects newly generated seeds only.
- **Profile/assets:** No action.

## Highlights

**Mines stop handing out a fixed upgrade sequence behind the randomizer's back.** The 133 verified
Smithing and Somber deposits now draw useful consumable replacements per seed through their 11
shared reward templates. They remain respawning world pickups rather than becoming checks, and the
change does not touch quantities, flags, inventory, AP location count, or Ancient Dragon capstones.
Players who prefer the vanilla deposits can disable the option (#1095).

The new seed table moves the contract hash to `8397a952`, so v0.5.5 requires its matching client
(clients#493).

**Direct enemy and boss rune payouts can follow sphere difficulty.** The new default-off
`scale_rune_rewards` option keeps runes-per-effort steadier when randomized progression moves an
early fight late or a late fight early. Golden Rune items are never changed, and the client uses
the already-loaded regulation as its baseline so the option composes with enemy randomizers
instead of multiplying their rewards repeatedly (#1091).

**Progressive flask upgrades can stay on important checks.** The default-off
`flask_upgrades_on_progression_surface` option uses the selected Progression Surface and widens
only when necessary to fit every upgrade (#1090). The tracker also gains a separate default-off
option to reveal names of bosses holding locked sweep payouts without revealing the locked region
(#1184).

**A broad progression and region cleanup landed.** Morgott's randomized arena boss now opens both
post-Morgott golden seals; Fia's Mending Rune cannot hold its own Cursemark prerequisite; the
Jagged Peak Summit grace unlocks without granting Bayle's post-fight grace; Leyndell's eastern
exit, Corhyn's wandering shop, Patches' cookbook, Pillar Path, Castle Ensis, and several shared-lot
rewards now use their evidence-backed owners. The Tonic of Forgetfulness, Cave of Knowledge Dragon
Communion Seal, and Ruin-Strewn Precipice rune checks have explicit source-neutralization coverage.

**The matching client includes the latest delivery and diagnostics fixes.** A pending sustain
grant can no longer starve ordinary AP deliveries, map loads correctly re-arm sphere-scaled rune
rewards, and the next teardown or signature mismatch report carries direct timing/byte evidence.
The bundled Bloodborne client also includes its GUI-v2, live-save binding, compact pickup toasts,
and debounced contextual guidance. The larger Rescue panel remains outside this release pending its
Windows visual acceptance pass.
