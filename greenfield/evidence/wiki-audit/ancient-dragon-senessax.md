# Ancient Dragon Senessax reward audit (#1296)

## Ruling

Defeating Ancient Dragon Senessax awards one Ancient Dragon Smithing Stone and one Somber Ancient
Dragon Smithing Stone. They are two lots on one acquisition flag, so the Archipelago projection is
two co-firing checks at the same boss. Both lots must be neutralized, and both checks must ride the
Senessax sweep for enemy-randomizer compatibility.

## Primary game-data evidence (Elden Ring v1.17)

- `m61_54_39_00.emevd.dcx.js` initializes common boss reward event `90005860` for entity
  `2054390850` with reward lot `30805`.
- `ItemLotParam_map` lot `30805` awards Ancient Dragon Smithing Stone and uses acquisition flag
  `530805`.
- The immediately chained lot `30806` awards Somber Ancient Dragon Smithing Stone and uses the same
  acquisition flag `530805`.
- `boss_healthbars.py` and `game_areas.tsv` independently place entity `2054390850` in
  `m61_54_39_00`, Jagged Peak.

## External corroboration (lead-only)

- Eldenpedia's Ancient Dragon Senessax page lists both stones among the boss rewards:
  https://eldenring.wiki.gg/wiki/Ancient_Dragon_Senessax
- Game8's DLC smithing-stone guide says Senessax drops the Ancient Dragon Smithing Stone together
  with a Somber Ancient Dragon Smithing Stone:
  https://game8.co/games/Elden-Ring/archives/459589

These pages corroborate the human-facing reward identity and location. The committed EMEVD and
ItemLotParam data remain authoritative for the implementation mechanism and exact flags/lots.
