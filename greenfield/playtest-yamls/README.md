# Greenfield playtest yamls

Targeted test yamls for the in-game validation checklist. Running
`.\build.ps1 -Greenfield` regenerates the data, installs the world, and gens
whatever is in `greenfield\players\` (the resident flagship there is
`A2-the-shattering.yaml`).

**One yaml in `players\` = a solo seed. Two or more = a multiworld.** For a
targeted test, copy one variant below into `players\` (move the resident yaml
out first for a solo seed):

| yaml | what it validates | checklist tier |
|------|-------------------|----------------|
| GF-Boot.yaml       | boot contract in isolation (locks light graces, filler grants, checks send) | T0 |
| GF-Shattering-4Region.yaml | flagship Shattering: item-shuffle + num_regions 4 (spine) + region-lock goal | T1/T2/T3 |
| Alaric_shattering.yaml | the same Shattering with 4 *rolled* regions | T1/T2/T3 |
| GF-Grace-Scatter.yaml | grace freebie + scatter items                                  | T3.1 |
| GF-GreatRunes.yaml | great-rune goal (all regions kept, 2 runes required)               | T3.4 |
| GF-FullWorld.yaml  | the long run -- all regions, full pool, progressive items          | soak |
| GF-DLC-Playtest.yaml | full world with the DLC enabled (reach the DLC via its Locks; boss keys off to isolate) | T4.3 |
| GF-DLC.yaml        | DLC-only regions (experimental)                                    | T4.3 |

See `greenfield\IN-GAME-VALIDATION.md` for the step-by-step pass/fail per tier.
No client patch or rebuild step is needed: the client is the prebuilt DLL from
the `from-software-archipelago-clients` submodule (`.\build.ps1 -Rust` builds
it), and `-Greenfield` regenerates the data files itself.

Reminder -- these are GREENFIELD options, NOT the release EldenRing apworld's.
Core keys: num_regions(0-31, 0 = all in play) num_regions_order(spine|rolled)
ending_condition(region_locks|great_runes) goal_great_runes(1-7) enable_dlc
dlc_only. The feature options ride on top (the frozen v0.2 behaviours are no
longer yaml-settable); the full surface is documented inline, option by option,
in `release-v0.2/EldenRing.yaml`.
