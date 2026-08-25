# Getting unstuck with the rescue console

The client has a rescue console that works even while disconnected. Use it when a bad warp,
missing grace, or progression edge has left the character somewhere the normal map cannot fix.
These commands change live game state, so make a save backup first and use only the specific flag
you mean to change.

## Open the console

1. Press **F5** if the Archipelago overlay is hidden.
2. Choose **Console** from the overlay menu.
3. Type a command and press Enter. Results appear in the main overlay log.

Type `!help` to see the command list shipped by your client.

## Escape anywhere

Type:

```text
!warp 11102950
```

That warps to the Table of Lost Grace in Roundtable Hold. It is the first recovery step when you
are out of bounds, trapped in unloaded geometry, or cannot use the map.

## Find and warp to a grace

Search the grace entries carried by the seed. For a region bundle, use part of the region name:

```text
!grace liurnia
!grace leyndell
```

Each match shows its unlock flag and a complete warp command, for example:

```text
Leyndell Lock bundle: flag 71102 = false; !warp 11001952
```

Copy the `!warp ...` part back into the console. The number after `flag` is a different ID; do not
pass that number to `!warp`.

If the line says `warp unavailable`, the game had not made `BonfireWarpParam` readable yet or no
row matched. Load a character fully and retry. The flag-only fallback below still works.

## Restore a missing grace

When the destination is safe but its grace never lit, set that grace's unlock flag:

```text
!setflag <grace flag> 1
```

The number comes from `!grace`, not from guesswork. Confirm it before writing with:

```text
!flag <grace flag>
```

Capital flags that have been needed in real support cases are:

| Grace | Unlock flag | Command |
|---|---:|---|
| Elden Throne | 71100 | `!setflag 71100 1` |
| East Capital Rampart | 71102 | `!setflag 71102 1` |
| West Capital Rampart | 71105 | `!setflag 71105 1` |
| Queen's Bedchamber | 71107 | `!setflag 71107 1` |

These IDs come from the shipped `grace_flags.tsv`. Do not substitute a nearby-looking number.
After the write, open the map and fast-travel normally, or use the pasteable command from
`!grace` if map travel is the thing that is broken.

## The Leyndell capital gate will not open

The Seal of the Royal Capital reads two flags: the two-great-rune gate (`182`) and its paired
capital condition (`105`). When a seed's rune supply has left the capital sealed and you cannot get
in, set both, then confirm:

```text
!setflag 182 1
!setflag 105 1
!flag 182
```

`182` is the game's "at least two great runes possessed" result, so setting it opens the fogwall
directly; `105` is the paired condition the seal also checks. This is the standard fix for being
routinely unable to enter Leyndell.

## A check never registered

Some checks are picked up from an enemy, boss, or NPC drop, and their flag can fail to fire -- most
often under enemy randomization, where the enemy that would have set it never spawns. If you have a
pickup that "didn't fire", `!check` finds its acquisition flag by name:

```
!check larval tear
```

The console prints each matching check, whether its flag is set, and a ready `!setflag`:

```
Ainsel River :: Larval Tear - around Dragonkin Soldier of Nokstella (1): flag 12017965 = false; !setflag 12017965 1
```

Copy the `!setflag ...` line to send the check on the next poll. `!check` only lists checks that
carry a settable flag -- enemy, boss and NPC drops and offline pickups; a normal world pickup fires
on its own and will not appear.

Setting a check's flag also drops its vanilla item locally, so use this for a check that never fired,
not to double up a pickup you can still reach.

For a boss whose swept checks never released, set its **defeat flag** from the table at the
end of this guide instead.

## The goal did not fire

Pick up any item. Some older goal paths defer their final send until the next pickup. If that does
not finish the slot, capture the log from the current session before restarting and report it.

## Find the client log

Logs are named `archipelago-YYYY-MM-DD.log` and append several launches from the same day. Search
from the last `=== SESSION START` line when reporting the current run.

- **The shipped me3 profile:** `%LocalAppData%\Programs\garyttierney\me3\log`
- **thefifthmatt's randomizer, ModEngine2, or another non-me3 loader:** open the folder that
  contains the loaded `eldenring_archipelago.dll`; its log is in the `log` folder beside that DLL.
  With matt's **Add DLL mod** layout this is normally the randomizer output's DLL folder, not the
  me3 AppData folder.

Attach the whole log, your YAML, what you typed, and what happened. The session-start line records
the client build and the log's early provenance lines name which loader and nearby mods were seen.

## Appendix: boss defeat flags

If a boss's checks never released -- the sweep did not fire, or enemy randomisation replaced the
boss so the vanilla kill flag never set -- set its defeat flag and the swept checks report on the
next poll:

```text
!setflag <defeat flag> 1
```

Set a defeat flag only when that fight is genuinely done and its checks are stuck: it marks the boss
dead. Some names appear more than once -- those are separate arenas or phases; pick the flag for the
one you are at.

| Boss | Defeat flag |
|---|---:|
| Godrick the Grafted | 10000800 |
| Margit, the Fell Omen | 10000850 |
| Grafted Scion | 10010800 |
| Morgott, the Omen King | 11000800 |
| Godfrey, First Elden Lord | 11000850 |
| Godfrey, First Elden Lord | 11050800 |
| Sir Gideon Ofnir, the All-Knowing | 11050850 |
| Dragonkin Soldier of Nokstella | 12010800 |
| Dragonkin Soldier | 12010850 |
| Valiant Gargoyle | 12020800 |
| Valiant Gargoyle (Twinblade) | 12020801 |
| Dragonkin Soldier | 12020830 |
| Mimic Tear | 12020850 |
| Crucible Knight Siluria | 12030390 |
| Fia's Champion | 12030800 |
| Sorcerer Rogier | 12030810 |
| Lionel the Lionhearted | 12030811 |
| Fia's Champion | 12030812 |
| Fia's Champion | 12030813 |
| Lichdragon Fortissax | 12030850 |
| Astel, Naturalborn of the Void | 12040800 |
| Mohg, Lord of Blood | 12050800 |
| Ancestor Spirit | 12080800 |
| Regal Ancestor Spirit | 12090800 |
| Maliketh, the Black Blade | 13000800 |
| Beast Clergyman | 13000801 |
| Dragonlord Placidusax | 13000830 |
| Godskin Duo | 13000850 |
| Rennala, Queen of the Full Moon | 14000800 |
| Rennala, Queen of the Full Moon | 14000801 |
| Red Wolf of Radagon | 14000850 |
| Malenia, Blade of Miquella | 15000800 |
| Loretta, Knight of the Haligtree | 15000850 |
| Rykard, Lord of Blasphemy | 16000800 |
| God-Devouring Serpent | 16000801 |
| Godskin Noble | 16000850 |
| Abductor Virgin (Swinging Sickle) | 16000860 |
| Abductor Virgin (Wheel) | 16000861 |
| Ulcerated Tree Spirit | 18000800 |
| Soldier of Godrick | 18000850 |
| Elden Beast | 19000800 |
| Radagon of the Golden Order | 19000810 |
| Divine Beast Dancing Lion | 20000800 |
| Radahn, Consort of Miquella | 20010800 |
| Promised Consort Radahn | 20010801 |
| Needle Knight Leda | 20010850 |
| Dryleaf Dane | 20010851 |
| Redmane Freyja | 20010852 |
| Golden Hippopotamus | 21000850 |
| Base Serpent Messmer | 21010800 |
| Messmer the Impaler | 21010801 |
| Putrescent Knight | 22000800 |
| Metyr, Mother of Fingers | 25000800 |
| Midra, Lord of Frenzied Flame | 28000800 |
| Cemetery Shade | 30000800 |
| Erdtree Burial Watchdog | 30010800 |
| Erdtree Burial Watchdog | 30020800 |
| Spiritcaller Snail | 30030800 |
| Grave Warden Duelist | 30040800 |
| Cemetery Shade | 30050800 |
| Black Knife Assassin | 30050850 |
| Erdtree Burial Watchdog | 30060800 |
| Erdtree Burial Watchdog | 30070800 |
| Ancient Hero of Zamor | 30080800 |
| Red Wolf of the Champion | 30090800 |
| Crucible Knight Ordovis | 30100800 |
| Crucible Knight | 30100801 |
| Black Knife Assassin | 30110800 |
| Misbegotten Warrior | 30120800 |
| Perfumer Tricia | 30120801 |
| Grave Warden Duelist | 30130800 |
| Erdtree Burial Watchdog (Sword) | 30140800 |
| Erdtree Burial Watchdog (Scepter) | 30140801 |
| Cemetery Shade | 30150800 |
| Putrid Tree Spirit | 30160800 |
| Ancient Hero of Zamor | 30170800 |
| Ulcerated Tree Spirit | 30180800 |
| Putrid Grave Warden Duelist | 30190800 |
| Stray Mimic Tear | 30200800 |
| Patches | 31000800 |
| Patches | 31000850 |
| Runebear | 31010800 |
| Miranda Blossom | 31020800 |
| Beastman of Farum Azula | 31030800 |
| Cleanrot Knight | 31040800 |
| Bloodhound Knight | 31050800 |
| Crystalian (Staff) | 31060800 |
| Crystalian (Spear) | 31060801 |
| Kindred of Rot | 31070800 |
| Kindred of Rot | 31070801 |
| Demi-Human Queen Margot | 31090800 |
| Beastman of Farum Azula (Cleaver) | 31100800 |
| Beastman of Farum Azula (Throwing Knife) | 31100801 |
| Putrid Crystalian (Spear) | 31110800 |
| Putrid Crystalian (Ringblade) | 31110801 |
| Putrid Crystalian (Staff) | 31110802 |
| Misbegotten Crusader | 31120800 |
| Demi-Human Chief | 31150800 |
| Demi-Human Chief | 31150801 |
| Guardian Golem | 31170800 |
| Miranda the Blighted Bloom | 31180800 |
| Omenkiller | 31180801 |
| Black Knife Assassin | 31190800 |
| Necromancer Garris | 31190850 |
| Cleanrot Knight (Spear) | 31200800 |
| Cleanrot Knight (Sickle) | 31200801 |
| Frenzied Duelist | 31210800 |
| Spiritcaller Snail | 31220800 |
| Godskin Apostle | 31220801 |
| Godskin Noble | 31220802 |
| Scaly Misbegotten | 32000800 |
| Stonedigger Troll | 32010800 |
| Crystalian | 32020800 |
| Stonedigger Troll | 32040800 |
| Crystalian (Ringblade) | 32050800 |
| Crystalian (Spear) | 32050801 |
| Magma Wyrm | 32070800 |
| Fallingstar Beast | 32080800 |
| Astel, Stars of Darkness | 32110800 |
| Onyx Lord | 34120800 |
| Godskin Apostle | 34130800 |
| Fell Twin | 34140850 |
| Fell Twin | 34140851 |
| Mohg, the Omen | 35000800 |
| Esgar, Priest of Blood | 35000850 |
| Magma Wyrm Makar | 39200800 |
| Death Knight | 40000800 |
| Death Knight | 40010800 |
| Demi-Human Swordmaster Onze | 41000800 |
| Curseblade Labirith | 41010800 |
| Lamenter | 41020800 |
| Chief Bloodfiend | 43000800 |
| Ancient Dragon-Man | 43010800 |
| Alecto, Black Knife Ringleader | 1033420800 |
| Erdtree Avatar | 1033430800 |
| Bols, Carian Knight | 1033450800 |
| Glintstone Dragon Adula | 1034420800 |
| Glintstone Dragon Smarag | 1034450800 |
| Royal Revenant | 1034480800 |
| Glintstone Dragon Adula | 1034500800 |
| Omenkiller | 1035420800 |
| Royal Knight Loretta | 1035500800 |
| Magma Wyrm | 1035530800 |
| Death Rite Bird | 1036450800 |
| Night's Cavalry | 1036480800 |
| Onyx Lord | 1036500800 |
| Full-Grown Fallingstar Beast | 1036540800 |
| Deathbird | 1037420800 |
| Bell Bearing Hunter | 1037460800 |
| Ancient Dragon Lansseax | 1037510800 |
| Demi-Human Queen Maggie | 1037530800 |
| Ulcerated Tree Spirit | 1037540810 |
| Adan, Thief of Fire | 1038410800 |
| Erdtree Avatar | 1038480800 |
| Demi-Human Queen Gilika | 1038510800 |
| Tibia Mariner | 1038520800 |
| Fallingstar Beast | 1038540800 |
| Night's Cavalry | 1039430800 |
| Tibia Mariner | 1039440800 |
| Godefroy the Grafted | 1039500800 |
| Night's Cavalry | 1039510800 |
| Elemer of the Briar | 1039540800 |
| Black Knife Assassin | 1040520800 |
| Sanguine Noble | 1040530800 |
| Fallingstar Beast | 1041500800 |
| Tree Sentinel | 1041510800 |
| Wormface | 1041530800 |
| Ancient Hero of Zamor | 1042330800 |
| Tree Sentinel | 1042360800 |
| Crucible Knight | 1042370800 |
| Deathbird | 1042380800 |
| Bell Bearing Hunter | 1042380850 |
| Godskin Apostle | 1042550800 |
| Leonine Misbegotten | 1043300800 |
| Erdtree Avatar | 1043330800 |
| Flying Dragon Agheel | 1043360800 |
| Night's Cavalry | 1043370800 |
| Bell Bearing Hunter | 1043530800 |
| Deathbird | 1044320800 |
| Night's Cavalry | 1044320850 |
| Bloodhound Knight Darriwil | 1044350800 |
| Mad Pumpkin Head | 1044360800 |
| Deathbird | 1044530800 |
| Tibia Mariner | 1045390800 |
| Draconic Tree Sentinel | 1045520800 |
| Putrid Avatar | 1047400800 |
| Decaying Ekzykes | 1048370800 |
| Mad Pumpkin Head (Hammer) | 1048400800 |
| Bell Bearing Hunter | 1048410800 |
| Night's Cavalry | 1048510800 |
| Death Rite Bird | 1048570800 |
| Night's Cavalry | 1049370800 |
| Death Rite Bird | 1049370850 |
| Commander O'Neil | 1049380800 |
| Nox Monk | 1049390800 |
| Battlemage Hugues | 1049390850 |
| Black Blade Kindred | 1049520800 |
| Great Wyrm Theodorix | 1050560800 |
| Death Rite Bird | 1050570800 |
| Putrid Avatar | 1050570850 |
| Crucible Knight | 1051360800 |
| Putrid Avatar | 1051400800 |
| Black Blade Kindred | 1051430800 |
| Commander Niall | 1051570800 |
| Flying Dragon Greyll | 1052410800 |
| Night's Cavalry | 1052410850 |
| Roundtable Knight Vyke | 1053560800 |
| Night's Cavalry (Glaive) | 1248550800 |
| Starscourge Radahn | 1252380800 |
| Fire Giant | 1252520800 |
| Borealis the Freezing Fog | 1254560800 |
| Romina, Saint of the Bud | 2044450800 |
| Rugalea the Great Red Bear | 2044470800 |
| Ghostflame Dragon | 2045440800 |
| Dancer of Ranah | 2046380800 |
| Demi-Human Queen Marigga | 2046400800 |
| Knight of the Solitary Gaol | 2046410800 |
| Red Bear | 2046450800 |
| Divine Beast Dancing Lion | 2046460800 |
| Death Rite Bird | 2047390800 |
| Black Knight Garrew | 2047450800 |
| Ghostflame Dragon | 2048380850 |
| Rellana, Twin Moon Knight | 2048440800 |
| Jagged Peak Drake | 2049410800 |
| Black Knight Edredd | 2049430850 |
| Dryleaf Dane | 2049440800 |
| Ralva the Great Red Bear | 2049450800 |
| Commander Gaius | 2049480800 |
| Dryleaf Dane | 2050430800 |
| Tree Sentinel | 2050470800 |
| Scadutree Avatar | 2050480810 |
| Scadutree Avatar | 2050480811 |
| Scadutree Avatar | 2050480812 |
| Tree Sentinel | 2050480860 |
| Rakshasa | 2051440800 |
| Jori, Elder Inquisitor | 2052430800 |
| Fallingstar Beast | 2052480800 |
| Bayle the Dread | 2054390800 |
| Ancient Dragon Senessax | 2054390850 |
