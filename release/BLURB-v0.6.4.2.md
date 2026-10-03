# v0.6.4.2 — finish Elden Beast and Radahn

Optional `progressive_talismans: true` makes numbered talisman families arrive
base first, then +1/+2/+3. Small seeds can stop earlier. Defaults off and
requires a client supporting `progressive_talismans_v1`. Weapon and Rune Level
hard caps are still under development and are not available options.

You can keep Elden Beast as your finale and require either Radahn, or both, too.
Choose Additional Required Bosses under Regions & Finish Line → Advanced in the YAML
builder. Their regions stay in the seed even if you roll a small set of regions.

```yaml
goal: elden_beast
required_bosses: [starscourge_radahn]
```

For DLC Radahn, use `promised_consort_radahn` and enable DLC. Base-game Radahn cannot
be selected with DLC Only. Select both names to require both Radahns. Empty is the
default and adds no requirement. The normal Great Rune and region requirements still
apply, as do the existing Elden Beast goal's Hoarah Loux requirements. Defeat them in
either order: completion waits for all required fights. Shuffled Remembrances and
server-side `!collect` do not count as the extra boss defeat.

## Can I update the client during a run?

**Yes.** The client keeps goals from existing 0.6.4 seeds; no save migration is needed.
Updating an existing seed cannot add requirements: generate a new seed to use the option.
New additional-boss seeds need a client supporting `required_bosses_v1`; older clients
refuse this capability explicitly. The top-level contract hash remains `2aa64f43`.

## What you need to update

- **Client:** Required for new additional-boss seeds; optional for existing seeds.
- **APWorld:** Host-only update to generate the new requirements.
- **YAML:** **New YAML optional. Existing YAMLs remain valid.** Add `required_bosses`
  only when you want extra defeats.
- **Existing seed/save:** Compatible; a new seed is required to add the option.
- **Profile/assets:** No action. Keep the matching room/save profile.

## What carried over from v0.6.4.1

The YAML builder and sweep reference remain available. The tagged release's signed
bundle and stable website deployment still depend on its release workflow completing;
opening this development window does not claim those assets have been published.

With boss randomization, these requirements follow the original Radahn arenas.
