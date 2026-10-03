# v0.6.5 — experimental bingo branch (draft)

## Can I update the client during a run?

Existing seeds keep their settings. Bingo defaults off. To try it, generate a new seed with `presets/bingo-short.yaml`, build the paired client branch, and use a fresh character. This branch has not been published as a release.

## What you need to update

- **Client:** Required for bingo seeds; build the matching `codex/bingo-mode` client. Its F6 tracker displays the board and reports square rewards from local defeat flags.
- **APWorld:** Host-only update to generate the experimental boss board.
- **YAML:** **New YAML optional. Existing YAMLs remain valid.** For bingo use `presets/bingo-short.yaml`; bingo defaults off. Objectives choose regions, so `num_regions` is ignored for these runs.
- **Existing seed/save:** New seed required to try bingo; use a fresh character. Existing board-free seeds remain compatible. The new client bridges the previously shipped contract windows.
- **Profile/assets:** Reinstall or replace the paired bingo DLL; no new graphics assets. This branch is experimental and has not been published as a release.

Complete boss objectives on a 5 by 5 board to receive progression rewards. The first completed row, column, or diagonal also releases up to twenty reserved native checks. The default goal ends the run on one line; count and blackout are available.

Objectives choose the regions needed by the run, including prerequisites. The default board uses at most six regions. This first catalogue supports base-game bosses; the full community squares and DLC-only boards remain planned. Live game acceptance is outstanding.
