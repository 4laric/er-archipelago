# SPEC — Goal progress in the in-game tracker

*Draft 2026-08-31. Client-only presentation over goal data that already ships in slot data and is
already enforced by the client.*

## Problem

The F6 tracker currently reduces the ending gate to one compact text line, such as
`goal: 2 outstanding -- Consecrated Snowfield Lock, Great Runes (1/2)`. The line is accurate, but
it asks the player to translate three different mechanics at once:

- the seed's completion goal;
- required Region Locks;
- a count over eligible Great Runes.

That translation repeatedly fails at the Ashen Capital boundary. A player can hold every visible
Lock, see no Ashen Capital Lock in the pool, and reasonably conclude that the seed is broken. The
actual rule is that the client withholds the goal region and opens it automatically when the other
goal requirements are satisfied. The current tracker exposes the verdict but not the checklist.

## Goal

Put a small **Goal Progress** card near the top of the F6 Item Tracker. It must answer, without a
spoiler log or console command:

1. What must I still collect?
2. Which Great Runes have I received?
3. Why is the Ashen Capital still locked?
4. Will I receive an Ashen Capital Lock item?

This is a legibility feature. It does not change logic, placement, gate enforcement, completion,
or the server protocol.

## Existing authoritative data

No contract expansion is needed. The client already parses and uses:

| Fact | Existing source | Existing consumer |
|---|---|---|
| Required held items | `goalRequiredItems` | `goal::GoalConfig.item_goals` and `region::tick_goal_gate` |
| Eligible Great Runes | `great_rune_items` | `goal::GoalConfig.rune_goals` |
| Required rune count | `great_runes_required` | `goal::GoalConfig.runes_required` |
| Received item names | Archipelago received-item stream | tracker snapshot and goal predicates |
| Goal-region Lock name | tracker tables + `goalLocations` | `region::configure_goal_arena` |
| Live gate verdict | `region::tick_goal_gate` | `region::goal_gate_status` |

The view must derive from these values. It must not create a second Great Rune list, infer
requirements from item-name suffixes, or inspect vanilla inventory as a substitute for AP receipt
truth.

## Player-facing design

The card appears below the tracker totals and region-roster summary, before lock-hint controls and
the region tree.

### Header

Use one of these states:

- `Goal Progress — READY` in green when the gate decision opens.
- `Goal Progress — LOCKED` in amber when requirements remain.
- `Goal Progress — unavailable for this seed` in disabled text when legacy or foreign slot data
  provides no item requirements and no resolvable goal gate.

`READY` means the requirements represented by this card are satisfied. It does not replace the
separate final-boss or goal-location progress used to send `Goal` to the server.

### Great Rune section

Only render this section when `runes_required > 0`.

```text
Great Runes                         2 / 4 required
[✓ Godrick] [✓ Unborn] [· Radahn] [· Morgott]
[· Rykard]  [· Mohg]   [· Malenia]
```

- Every name in `GoalConfig.rune_goals` gets one badge.
- Acquired badges use a green accent and `✓`; missing badges use disabled text and `·`.
- The counter is `min(acquired, required) / required required`, while all eligible badges remain
  visible. This makes “any four of seven” unambiguous.
- Preserve the canonical label `Great Rune of the Unborn`; a display helper may shorten badge text
  to `Unborn`, but identity and matching continue to use the full name.
- A hover tooltip shows the full canonical item name and `Received` or `Not received`.
- Color is supplementary. The glyph and text must communicate state without color.

The first implementation uses ImGui text/buttons or bordered text badges. Actual Elden Ring rune
art is a later enhancement because the current overlay has no general texture-loading path. Artwork
must not block the checklist.

### Required-item section

Render one row per `GoalConfig.item_goals` entry:

```text
Required Locks
✓ Limgrave Lock
· Mountaintops of the Giants Lock
```

Use the same received-name set and the same accessible glyph-plus-color treatment as Great Runes.
Do not show the withheld goal-region Lock as a collectible requirement. It is not placed in the
multiworld and cannot be hinted.

### Ashen Capital explanation

When the resolved goal region is the Ashen Capital and the gate is withheld, show:

> Ashen Capital unlocks automatically when the requirements above are complete. There is no Ashen
> Capital Lock item to find.

When ready, replace it with:

> Requirements complete. The Ashen Capital gate is opening automatically.

Use the resolved goal-region name rather than hard-coding behavior around one ending. For another
withheld goal region, substitute its name in the same sentence.

### Relationship to the existing status line

The card supersedes the bare `goal: ...` line in the tracker. Keep the existing log/status-line
functions for diagnostics and one-shot notifications. Do not render both in F6: duplicate summaries
create two apparent authorities and waste the space the checklist is intended to use.

The existing Leyndell compound-gate line remains separate. Leyndell access and the ending gate are
different gates, even when both mention Great Runes.

## Pure view model

Put the decision-shaped transformation in `er-logic`, for example
`er_logic::goal_progress`. The Windows/ImGui crate should only snapshot inputs and draw rows.

Suggested model:

```rust
pub struct GoalItemRow {
    pub canonical_name: String,
    pub display_name: String,
    pub received: bool,
}

pub enum GateState {
    Locked,
    Ready,
    Unavailable,
}

pub struct GoalProgress {
    pub state: GateState,
    pub region_name: Option<String>,
    pub required_items: Vec<GoalItemRow>,
    pub runes: Vec<GoalItemRow>,
    pub runes_required: usize,
    pub runes_received: usize,
}
```

The builder accepts `item_goals`, `rune_goals`, `runes_required`, the received-name set, the
resolved goal-region name, and the live gate decision. It must clamp malformed rune thresholds to
the eligible set in the same way `goal::parse` does.

Keep ordering stable:

- required items retain slot-data order unless the current UI already promises a sorted order;
- Great Runes use the slot-data order emitted by the world;
- no `HashSet` iteration may reach the UI.

## Compatibility and failure behavior

- **Current greenfield seeds:** show the complete card.
- **Older seeds without `great_rune_items`:** omit rune badges. Show required Locks if supplied.
- **Foreign apworlds:** show only facts actually supplied. Never invent a greenfield ending rule.
- **Malformed threshold:** clamp to the eligible rune count and log the existing contract warning;
  the tracker must remain usable.
- **Goal gate not yet evaluated:** show the checklist with `Checking gate...`, not a false `READY`.
- **Disconnected/menu state:** preserve the last connected snapshot exactly as the existing tracker
  does for its other seed-scoped tables, or show unavailable after the normal seed reset. Do not
  read live game pointers from the render closure.

The feature is display-only and therefore does not need a `requiresClientFeatures` tag. A new client
can render an old seed; an old client can play a new seed exactly as before.

## Implementation boundaries

1. Add the pure model and unit tests in `crates/er-logic`.
2. In `render_tracker_window`, build the model from `self.goal`, the received-name snapshot,
   `region::goal_region_name()`, and a structured gate state.
3. Draw the card before lock hints.
4. Replace the tracker-only bare goal status line; retain diagnostic logging and toasts.
5. Keep all ImGui inputs in owned/local snapshot data before the window closure, matching the
   tracker's established borrowing rule.

The current `region::goal_gate_status()` returns presentation text. The tracker card needs
structured state, so expose a small structured snapshot beside it rather than parsing that string.
The gate decision remains authoritative; the UI must not independently decide whether to open.

## Tests

Host-native `er-logic` tests must cover:

- any-four-of-seven with zero, partial, exactly four, and all seven received;
- `Great Rune of the Unborn` matching and display shortening;
- required Locks mixed between received and missing;
- withheld goal Lock absent from required rows;
- stable row order;
- zero-rune goals;
- legacy data with neither item list nor gate state;
- a ready checklist versus a gate decision that is still pending;
- malformed `runes_required > rune_goals.len()` clamping;
- duplicate received events not increasing counts.

Client-side structural tests should pin that:

- the card is rendered above lock hints and region rows;
- the old tracker-only `goal: {status}` line is removed;
- state uses both a glyph and color/disabled styling;
- the ImGui closure consumes a prebuilt model and does not borrow or query live game state.

Run the whole-workspace formatting gate, host-native `er-logic` tests and clippy locally. The Windows
PR gate remains authoritative for the ImGui integration and full client build.

## Acceptance

- A player missing an ending requirement can identify it from the first screen of F6.
- An any-N Great Rune goal shows every eligible rune and which ones count as received.
- A withheld Ashen Capital explicitly says that no Ashen Capital Lock item exists and that the gate
  opens automatically.
- The card agrees with the same gate decision that controls the flag write.
- No new slot-data key, game-data artifact, texture asset, or live-memory read is introduced.
- Legacy and foreign seeds never display invented requirements.

## Later enhancement: rune artwork

If the overlay gains a supported texture registry, map canonical Great Rune names to bundled,
redistributable icons and render a small monochrome/disabled treatment for missing runes. This needs
an explicit asset provenance decision, DPI scaling, device-reset handling, and a text fallback.
It is deliberately outside the first slice; the badge checklist ships without it.
