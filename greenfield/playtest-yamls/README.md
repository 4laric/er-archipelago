# Greenfield playtest yamls

The flagship seed is `greenfield\players\Greenfield.yaml` (item-shuffle, 4-region Shattering,
region-lock goal). Running `.\build.ps1 -Greenfield` gens whatever is in `greenfield\players\`.

**One yaml in `players\` = a solo seed. Two or more = a multiworld.** For a targeted test, copy
one variant below over `players\Greenfield.yaml` (or move the flagship out first):

| yaml | what it validates | checklist tier |
|------|-------------------|----------------|
| (players/Greenfield.yaml) | flagship Shattering: item-shuffle + num_regions 4 + region-lock goal | T1/T2/T3 |
| GF-Boot.yaml       | boot contract in isolation (locks light graces, filler grants, checks send) | T0 |
| GF-GreatRunes.yaml | great-rune goal (all 22 regions so 2 runes are required)          | T3.4 |
| GF-Grace-Scatter.yaml | grace freebie + scatter items                                  | T3.1 |
| GF-FullWorld.yaml  | the long run -- all regions, full pool, progressive items         | soak |
| GF-DLC.yaml        | DLC-only regions (experimental)                                   | T4.3 |

See `greenfield\IN-GAME-VALIDATION.md` for the step-by-step pass/fail per tier. Prereq every time:
`python greenfield\gen_data.py` first (gen-greenfield copies the world as-is; it does NOT regenerate
the data files), and for dungeon sweeps apply `patch_p3b_client.py` + rebuild the DLL.

Reminder -- these are GREENFIELD options, NOT the release EldenRing apworld's. Valid keys:
num_regions(0-22) num_regions_order(spine|rolled) item_shuffle ending_condition(region_locks|great_runes)
great_runes_required(1-7) enable_dlc dlc_only completion_scaling_floor(0-50)
global_scadutree_blessing(off|player_only|scaled) dungeon_sweep(none|minidungeons|all|bosses)
boss_lock_placement(scatter|own_region|any_boss) merchant_bell_logic(off|logic_only) grace_rando
death_link start_with_torch pool_builder pool_builder_juice_cap(0-400) progressive_flasks
progressive_stonesword_keys local_item_only exclude_local_item_only(weapons|armor|talismans|goods|ashes|progressive)
