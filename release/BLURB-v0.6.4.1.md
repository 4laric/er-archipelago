# v0.6.4.1 — development window (draft)

Mario Stat Upgrades is an optional, default-off setting that requires Mario Mode.
Start at four of eight health wedges and 75% normal attack damage. Four Progressive
Health items add one maximum wedge each, without healing; three Progressive Power
items raise damage to 100%, 125%, then 150%. Coins, grace and stars respect the
current maximum. These useful items replace seven filler rewards and never gate
checks or goals.

## Can I update the client during a run?

Existing seeds retain their original settings: updating cannot add stat progression
to them. To use it, generate a **new seed** with `mario_mode: true` and
`mario_stat_upgrades: true`, and use compatible paired AP client and Mario DLLs.
New enabled seeds require `mario_stats_v1`; older clients reject that requirement.
Keep the matching room/save profile. No save migration is introduced.

## What you need to update

- **Client:** Required for new stat-upgrade seeds; update both paired DLLs.
- **APWorld:** Host-only update to generate the new optional items.
- **YAML:** **New YAML optional. Existing YAMLs remain valid.** Stat upgrades default off.
- **Existing seed/save:** New seed required to enable stat progression. Existing seeds remain supported.
- **Profile/assets:** Reinstall or replace both paired DLLs for new stat seeds. Keep your Mario setup and own SM64 ROM.

## Validation limits

Mario remains experimental. Generation and runtime automated tests do not establish
full live playthrough validation. Further slot/history replay, region kicks, healing,
combined icons, the statue/Goldmask route, required special bosses and ending
completion remain unverified live. This option does not close those checks.
`CONTRACT_HASH` remains 2aa64f43.
