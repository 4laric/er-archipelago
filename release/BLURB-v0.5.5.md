# v0.5.5 — release blurb (draft)

_Draft. Written as the window fills, not at tag time._

## What you need to update

- **Client:** Required — use the v0.5.5 client with v0.5.5 seeds.
- **APWorld:** Host-only — the room host or generator must install the matching APWorld.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.** Mine-material rerolling defaults
  on; set `reroll_mine_materials: false` to keep vanilla mine rewards.
- **Existing seed/save:** Compatible — keep active seeds on their matching client/APWorld pair;
  the new option affects newly generated seeds only.
- **Profile/assets:** No action.

## What is in it so far

**Mines stop handing out a fixed upgrade sequence behind the randomizer's back.** The 133 verified
Smithing and Somber deposits now draw useful consumable replacements per seed through their 11
shared reward templates. They remain respawning world pickups rather than becoming checks, and the
change does not touch quantities, flags, inventory, AP location count, or Ancient Dragon capstones.
Players who prefer the vanilla deposits can disable the option (#1095).

The new seed table moves the contract hash to `8397a952`, so v0.5.5 requires its matching client
(clients#493).
