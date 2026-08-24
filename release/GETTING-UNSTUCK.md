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

Enemy and boss drops and NPC gifts send when their acquisition flag fires. If enemy randomisation
replaced the source, or the drop was missed, that flag never sets and the check stays unsent. If you
know the acquisition flag, set it and the client reports the check on the next poll:

```text
!flag <acquisition flag>
!setflag <acquisition flag> 1
```

Finding that flag per check is not yet a console lookup, so until one lands, capture the log and
report the unsent checks (see below) or ask in the thread.

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
