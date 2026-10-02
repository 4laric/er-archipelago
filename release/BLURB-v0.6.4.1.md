# v0.6.4.1 — development window (draft)

Generation errors for already-placed items left in the unplaced pools now distinguish
the affected item owners from the hook responsible. A world can place another game's
items, so the error no longer tells hosts to update or disable the owner as if it
were the proven culprit. Update the host's apworld for the clearer message and steps
to isolate the responsible hook. The pool consistency check still stops generation.

Mario Stat Upgrades is an optional, default-off setting that requires Mario Mode.
Start at four of eight health wedges and 75% normal attack damage. Four Progressive
Health items add one maximum wedge each, without healing; three Progressive Power
items raise damage to 100%, 125%, then 150%. Coins, grace and stars respect the
current maximum. These useful items replace seven filler rewards and never gate
checks or goals.

Mario FLUDD is also optional and default off. Find one Hover, Rocket and Turbo
Nozzle each; they start locked. Three Progressive FLUDD Tanks raise capacity from
60 to 80, 100, then 120 units, without refilling on receipt. These six useful items
replace filler and never gate checks or goals. Squirt is unfinished and excluded.

## Can I update the client during a run?

Existing seeds retain their original settings: updating cannot add stat progression
to them. To use it, generate a **new seed** with `mario_mode: true` and
`mario_stat_upgrades: true`, and use compatible paired AP client and Mario DLLs.
Stat seeds require `mario_stats_v1`; FLUDD seeds require `mario_fludd_v1`.
To use FLUDD, generate a new seed with `mario_mode: true` and `mario_fludd: true`.
Both options require compatible paired DLLs; older clients reject the new requirements.
Keep the matching room/save profile. No save migration is introduced.

## What you need to update

- **Client:** Required for new stat-upgrade or FLUDD seeds; update both paired DLLs.
- **APWorld:** Host-only update to generate the new optional items.
- **YAML:** **New YAML optional. Existing YAMLs remain valid.** Stat upgrades and FLUDD default off.
- **Existing seed/save:** New seed required to enable stat or FLUDD progression. Existing seeds remain supported.
- **Profile/assets:** Reinstall or replace both paired DLLs for new stat or FLUDD seeds. Keep your Mario setup and own SM64 ROM.

## Validation limits

Mario remains experimental. Generation and runtime automated tests do not establish
full live playthrough validation. No live FLUDD playtest is claimed. Further slot/history replay, region kicks, healing,
combined icons, the statue/Goldmask route, required special bosses and ending
completion remain unverified live. This option does not close those checks.
`CONTRACT_HASH` remains 2aa64f43.
