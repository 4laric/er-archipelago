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
