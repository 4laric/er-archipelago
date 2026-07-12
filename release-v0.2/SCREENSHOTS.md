# Screenshots

Images live in `release-v0.2/screenshots/`. Nothing here yet -- this file is the shot list, so
the pictures we take are the ones that answer real questions rather than whatever was on screen.

A randomizer is hard to explain in prose and trivial to explain in one picture. Every shot below
exists to kill a specific question someone actually asks.

## The shot list

| # | Shot | The question it kills |
|---|------|----------------------|
| 1 | The in-game overlay, connected, showing the slot name | "How do I know it's working?" -- this is the single most valuable image in the set. It belongs in SETUP.md at the end of the connect step. |
| 2 | A check being picked up: the item toast showing **another player's item**, e.g. "Sent Hylics to Player2" | "What actually happens when I open a chest?" This is the whole idea of a multiworld in one frame. |
| 3 | Receiving a **Region Lock** item, with the "region opened" message | The marquee mechanic. Explains `num_regions` faster than the Player Guide's whole section. |
| 4 | The kick: standing at a locked region border and getting warped out | Answers "is this a bug?" It is not. Put it right next to the explanation in the Player Guide. |
| 5 | The F6 tracker open, mid-run | "How do I know what's left?" |
| 6 | A merchant with rerolled infinite stock (the shop full of something useful) | Shows `reroll_infinite_shop_stock` in one glance, and stops people reading it as enemy rando. |
| 7 | matt's randomizer settings screen with **item randomization OFF** and enemies ON | The single highest-risk step in the compose-with-matt's recipe. A picture removes all doubt about which box must be unticked. Goes in ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md. |
| 8 | The Archipelago Players/ folder with `EldenRing.yaml` in it | Trivial, and it is still the step people get wrong. |

## Conventions

- **PNG**, cropped to the thing being shown. A 4K screenshot of a whole monitor teaches nothing.
- Name them after what they show, not when they were taken: `overlay-connected.png`, not `2026-07-12-1.png`.
- No personal information: crop out slot names/passwords that are not `Player1`, and anything else
  from a real room.
- Redact or avoid room URLs.

## Where each one goes

- SETUP.md -- 1, 8
- Player Guide -- 2, 3, 4, 5
- ENEMY-AND-STARTING-CLASS-RANDOMIZATION.md -- 7
- RELEASE-NOTES -- 3 (the Region Lock shot is the one that sells the project)

Reference an image from a doc with a relative path, e.g.:

    ![The overlay, connected](screenshots/overlay-connected.png)

(From the Player Guide, which sits at the repo root, that is `release-v0.2/screenshots/...`.)
