# Screenshots

Images live in `release-v0.2/screenshots/`.

## What we have (9) -- the compose-with-matt's walkthrough

These document the highest-risk procedure in the whole release: running thefifthmatt's randomizer
for enemies and starting loadouts, with **item randomization OFF**, and loading our client through
his launcher. Prose cannot make "make sure this tab is unticked" as unambiguous as a picture of the
unticked tab. All eight are referenced from `ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md`.

| File | What it shows |
|------|---------------|
| `matt-01-item-randomizer-OFF.png` | **The one that matters.** Item Randomizer tab unticked, whole panel greyed out; Enemy + DLC ticked. |
| `matt-02-enemy-randomizer-ON.png` | Enemy Randomizer tab, enemies being replaced. |
| `matt-02b-misc-options-starting-class.png` | **Misc Options: "Randomize starting class loadouts" ticked.** Proves the starting class does NOT come from the Item Randomizer -- which is why you still get it with items off. Without this picture the doc's headline promise is unverifiable. |
| `matt-03-dll-mods-dialog.png` | The "Add dll mod" dialog, empty. |
| `matt-04-select-client-dll.png` | Picking `eldenring_archipelago.dll` out of the `me3` folder. |
| `matt-05-client-dll-added.png` | The client listed; main window reads "Using eldenring_archipelago.dll". |
| `matt-06-randomize-enemies.png` | The Randomize enemies button. |
| `matt-07-blank-seed-and-launch.png` | A BLANK seed box -- matt's ticks "Reroll seed" for you and greys it out, so the player gets their own enemy layout rather than ours. This is why the shipped options string has no `seed:` token. |
| `matt-08-enemy-tab-detail.png` | Enemy tab, fuller view (spare). |

## Still worth taking (in-game)

Nobody has shot these yet. Each kills a specific question players actually ask:

| Shot | The question it kills |
|------|----------------------|
| The overlay, connected, showing the slot name | "How do I know it's working?" The single most useful image we do not have. Belongs at the end of SETUP's connect step. |
| A check being picked up, showing **another player's item** | "What happens when I open a chest?" The whole multiworld idea in one frame. |
| A **Region Lock** arriving + the region-opened message | The marquee mechanic. Sells the project better than any paragraph. |
| The kick: warped out of a locked region | Answers "is this a bug?" It is not. Goes beside the explanation in the Player Guide. |
| The F6 tracker, mid-run | "How do I know what is left?" |

## Conventions

- **PNG**, cropped to the thing being shown. A full-monitor 4K shot teaches nothing.
- Named for what they show, not when they were taken.
- No personal information: crop out real slot names, passwords, room URLs, and unrelated folders.

## Known nits in the current set

- `matt-04-select-client-dll.png` shows an unrelated sidebar of local folders. Harmless, but a
  tighter crop would be better.
Not worth blocking a release over; worth fixing if anyone reshoots.
