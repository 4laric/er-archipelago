# Screenshots

Images live in `release-v0.2/screenshots/`.

## The compose-with-matt's walkthrough (9)

These document the highest-risk procedure in the whole release: running thefifthmatt's randomizer
for enemies and starting loadouts, with **item randomization OFF**, and loading our client through
his launcher. Prose cannot make "make sure this tab is unticked" as unambiguous as a picture of the
unticked tab. All nine are referenced from `ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md`.

| File | What it shows |
|------|---------------|
| `matt-01-item-randomizer-OFF.png` | **The one that matters.** Item Randomizer tab unticked, whole panel greyed out; Enemy + DLC ticked. |
| `matt-02-enemy-randomizer-ON.png` | Enemy Randomizer tab, enemies being replaced. |
| `matt-02b-misc-options-starting-class.png` | **Misc Options: "Randomize starting class loadouts" ticked.** Proves the starting class does NOT come from the Item Randomizer -- which is why you still get it with items off. |
| `matt-03-dll-mods-dialog.png` | The "Add dll mod" dialog, empty. |
| `matt-04-select-client-dll.png` | Picking `eldenring_archipelago.dll` out of the `me3` folder. |
| `matt-05-client-dll-added.png` | The client listed; main window reads "Using eldenring_archipelago.dll". |
| `matt-06-randomize-enemies.png` | The Randomize enemies button. |
| `matt-07-blank-seed-and-launch.png` | A BLANK seed box -- matt's ticks "Reroll seed" for you and greys it out, so the player gets their own enemy layout rather than ours. This is why the shipped options string has no `seed:` token. |
| `matt-08-enemy-tab-detail.png` | Enemy tab, fuller view (spare). |

## In-game (1)

| File | What it shows |
|------|---------------|
| `overlay-connected.png` | **"How do I know it's working?"** -- the overlay reading `[Connected]` and the log line `Tester_A2 (Team #1) playing Elden Ring has joined.` It doubles as live proof of the game id WITH THE SPACE. (The turtle shell is an Archipelago item the client granted on a check.) Used in SETUP.md's connect step. |

## Conventions

- **PNG**, cropped to the thing being shown. A full-monitor 4K shot teaches nothing.
- Named for what they show, not when they were taken.
- No personal information: crop out real slot names, passwords, room URLs, and unrelated folders.
