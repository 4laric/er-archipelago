# Board ↔ GitHub Issues bridge

A two-way bridge between the ER Archipelago project board and GitHub issues on
`4laric/er-archipelago`. Written in **Python (stdlib only)** so it runs anywhere `python3` does and can
be tested offline. Runs on your machine — this repo's sandbox can't reach the GitHub API, but the logic
(load, reconcile, HTML regen) is covered by `test_sync_board.py`.

## Files

| File | Role |
|---|---|
| `cards.json` | **Source of truth** for card content (id, col, pri, cat, title, desc) + pulled fields (issue, assignee, comments, activeCol). |
| `board.template.html` | The kanban HTML with a `__CARDS_JSON__` placeholder + an **Export cards.json** button. |
| `sync_board.py` | The bridge: links issues, pushes content, merges open/closed, pulls state, regenerates the board. |
| `test_sync_board.py` | Offline tests (mocked GitHub). `python sync_board.py --self-test`. |
| `.sync-snapshot.json` | Auto-written. Remembers last-synced open/closed per card so a change on *either* side is detected. Don't hand-edit. |
| `er-archipelago-kanban.html` | Generated. The board you open. (Use `--board-out` to write it elsewhere, e.g. the repo root.) |

## Model — board-authoritative, pull state

- **Board wins** for content: `title`, `desc`, `pri`, `cat`, active column (ready/blocked/progress/backlog).
  Every sync **pushes** these to the issues.
- **GitHub wins** for `assignee`, `comment count` — **pulled** back and shown on the cards.
- **open/closed is 3-way merged** against the snapshot, so it flows both ways:
  - Close an issue on GitHub → the card moves to **Done** next sync.
  - Move a card to **Done** in `cards.json` (or drag it + **Export cards.json**) → the issue **closes**.
  - Reopen on GitHub → the card returns to its previous active column (remembered in `activeCol`).
  - A genuine both-sides conflict keeps the **board** value and logs a `CONFLICT` line.

## Usage

```bash
export GH_TOKEN=ghp_...            # Windows: set GH_TOKEN=ghp_...  (or $env:GH_TOKEN="ghp_..." in PowerShell)

python sync_board.py --self-test   # run the offline logic tests (no network)
python sync_board.py --dry-run     # preview every action, write nothing
python sync_board.py               # full reconcile: pull state, push content, regen board
```

Other flags:

```bash
python sync_board.py --mode push                       # only board -> issues
python sync_board.py --mode pull                        # only issues -> board
python sync_board.py --board-out ../er-archipelago-kanban.html   # write the board to the repo root
```

## How you edit the board

`cards.json` is the truth — edit it one of three ways, then run the sync:

1. Edit `cards.json` directly.
2. Open the generated board, **drag** cards, click **⬇ Export cards.json**, replace `cards.json` with the download.
3. Let Claude edit `cards.json`.

Then `python sync_board.py` reconciles everything and regenerates the board.

## First run (adoption)

Issues already created by the old one-way script have no card marker yet. The first sync **adopts** them by
normalized title, links each card to its issue number, and stamps a hidden `<!-- card:ID -->` marker into
the body so future matching survives title/desc edits. Expect a batch of one-time `UPDATE` lines. Adding a
new card to `cards.json` and syncing **creates** its issue automatically.

## Notes

- Labels are board-derived (`P0..P3`, `area:*`, `status:*` for non-done). Manage priority/area/status from
  the board, not on GitHub — a push overwrites them.
- Idempotent: a no-op sync writes nothing.
- The old PowerShell scripts (`sync-board.ps1`, `_issue-mirror/create-github-issues.ps1`) are **superseded**
  and can be deleted.
