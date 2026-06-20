# SPEC: Progressive Smithing-Stone Bell Bearings

Status: IN PROGRESS (2026-06-16). DECISION LOCKED: **Option B (set the
`eventFlag_forStock` directly) AND also grant the cosmetic bell goods for the inventory
record.** Supersedes the `UPLIFT_STONE_BELLS` note in `curation_uplift_draft.py`. Related
memory: `er-merchant-bell-bearing-logic`, `er-qol-patches-shop`,
`er-rune-skip-injectable-room`, `er-trimmed-audit`.

### IMPLEMENTED 2026-06-16 (behind default-OFF flag; needs Windows gen + client build + playtest)
- `options.py`: `ProgressiveStoneBells` toggle + `progressive_stone_bells` dataclass field.
- `items.py`: two progressive items (sentinel er_code 99998; `inject=False`).
- `stone_bells.py` (NEW): `STONE_BELL_GRANTS` per-tier `{goods, flags}` — single source of truth.
- `__init__.py`: `_progressive_bells_active()` (= option ON and `auto_upgrade==0`);
  `_DISCRETE_STONE_BELLS` dropped from the pool when active (location stays a check);
  progressive copies added to `_all_injectable_items` AND treated as priority injectables in
  the dlc_only count + Fix A so they seat in-world (not spilled to start);
  `_bell_bearings_required` → `state.has(progressive, up_to)` when active; `fill_slot_data`
  emits `progressiveGrants` (goods GOODS-packed `|0x40000000`) + `progressive_stone_bells`
  options echo.
- Client (`Dark-Souls-III-Archipelago-client`): `progressiveGrants` + `progressiveCounter`
  members (Core.h); slot_data consumer (ArchipelagoInterface.cpp); receive-handler block —
  Kth copy sets `flags[k]` (idempotent, via `pendingGraceFlags`) and pushes cosmetic
  `goods[k]` through the normal grant queue (respects `last_received_index`), then `continue`;
  counter reset on the reconnect queue-rebuild (Core.cpp); sentinel `99998` skip guard
  (GameHook.cpp).

### To validate on Windows
1. Gen with `progressive_stone_bells: true`, `auto_upgrade: false` (dlc_only): seed compiles,
   progressive bells seat in-world (NOT precollected to start), beatable.
2. Build client; connect: log shows `Progressive: 2 progressive item(s) loaded`.
3. In-game: receive copies in order → cosmetic bell appears + Twin Maiden stone rows unlock
   the matching tiers; verify shop-row repaint after the flag-set; verify reconnect keeps
   tiers aligned (no dup grant, no tier desync).

## Goal

Replace the nine discrete Miner's Bell Bearings with two **progressive** items so a
trimmed / `auto_upgrade=off` pool can hand out the smithing-stone ladder in order. The
Nth copy you receive unlocks the next rung of the Twin Maidens stone shop — you can
never get the +7/+8 tier before +1/+2, and "found a bell" always means a real,
immediately-useful step up.

- **Progressive Smithing-Stone Miner's Bell Bearing** — 4 copies (covers Smithing Stone [1]–[8]).
- **Progressive Somberstone Miner's Bell Bearing** — 5 copies (covers Somber [1]–[9]).

Only meaningful when `auto_upgrade == 0`. With auto-upgrade on, received weapons arrive
maxed and the whole ladder is moot — so the feature self-gates off (see §6).

## 1. Why progressive (vs. the 9 discrete bells today)

Today `items.py` defines bells 8951–8959 as distinct `progression` items and
`_bell_bearings_required` already checks the **cumulative** ladder
(`has_all([[1]..[up_to]])`). So the logic is already "need the whole run up to N." The
only thing missing is *ordered delivery*: with discrete bells, fill can place [4] in
sphere 1 and [1] in sphere 5, which is logically legal but useless in-hand. Progressive
collapses that into a clean count: the Kth copy = rung K.

## 2. The grant mechanism — two options

Each Miner's Bell Bearing tier unlocks **two** stone tiers in the Twin Maidens shop
(Roundtable, reachable in `dlc_only`). The shop rows are gated by `eventFlag_forStock`
in `ShopLineupParam` (Twin Maiden bell-bearing shop, IDs `1018xx`). Extracted from
`vanilla_er/ShopLineupParam.csv`:

| Progressive copy # | Bell (vanilla id) | Stones unlocked | `eventFlag_forStock` to set |
|---|---|---|---|
| Smithing 1 | [1] (8951) | Smithing Stone [1],[2] | **280080, 280090** |
| Smithing 2 | [2] (8952) | Smithing Stone [3],[4] | **280110, 280120** |
| Smithing 3 | [3] (8953) | Smithing Stone [5],[6] | **280140, 280150** |
| Smithing 4 | [4] (8954) | Smithing Stone [7],[8] | **280160, 280170** |
| Somber 1 | [1] (8955) | Somber [1],[2] | **280180, 280190** |
| Somber 2 | [2] (8956) | Somber [3],[4] | **280200, 280210** |
| Somber 3 | [3] (8957) | Somber [5],[6] | **280230, 280240** |
| Somber 4 | [4] (8958) | Somber [7],[8] | **280250, 280260** |
| Somber 5 | [5] (8959) | Somber [9] | **280280** |

### Option A — grant the bell item, player hands it to the Twin Maidens
The client grants the real bell goods (8950+N); the player walks to the Twin Maiden
Husks and turns it in as in vanilla, which fires the game's own handover event and sets
the flags above.
- **Pro:** zero flag knowledge; fully vanilla fulfillment path; the bell shows in the
  inventory/menu as a record.
- **Con:** extra manual chore per rung; and the shop won't restock until the handover
  ESD runs — i.e. it still leans on the **shop-refresh-on-unlock** dependency
  (`er-merchant-bell-bearing-logic` / `er-qol-patches-shop`). If a player receives a
  bell while the shop is open, stock lags until reopen.

### Option B — set the `eventFlag_forStock` directly (RECOMMENDED)
On receipt of progressive copy K, the client sets that rung's flag group (table above)
via the existing `SetEventFlag` path. The shop row appears with no handover and no
restock plumbing — setting `eventFlag_forStock` *is* the unlock.
- **Pro:** no manual turn-in; **eliminates the shop-refresh dependency**; deterministic;
  uses the flag-set drain the client already has (`pendingGraceFlags` /
  `kCompanionAcquireFlags` pattern).
- **Con:** no physical bell in inventory (cosmetic — can optionally grant the goods too,
  purely for the menu record, without relying on it for unlock).
- **Caveat to verify in-game:** a shop screen already open when the flag is set may need
  a reopen to repaint; confirm the row shows on next shop open (expected: yes).

**Recommendation: Option B.** It is strictly less in-game friction, and it retires a
dependency instead of adding one. Option A stays documented as the fallback if flag-set
proves flaky in-game.

## 3. AP-side changes (apworld) — LOW effort

`items.py`
- Add `Progressive Smithing-Stone Miner's Bell Bearing` and `Progressive Somberstone
  Miner's Bell Bearing` (GOODS, `progression`). These do **not** carry a single er id —
  the tier is resolved at grant time (§4), so their `apIdsToItemIds` entry is a sentinel
  routed past the normal lookup (mirror the `99999` logic-only-lock handling).

`__init__.py` (`create_items` / pool)
- When the feature is active, place the smithing progressive ×4 and the somber
  progressive ×5 **instead of** the discrete bells 8951–8959. They ride the guaranteed
  progression-inject path that the rune-skip demand-drop frees in-world slots for
  (`er-rune-skip-injectable-room`) — not the count-neutral filler swap.

`__init__.py` (logic) — one function:
```python
def _bell_bearings_required(self, state, up_to, bell_type):
    name = ("Progressive Somberstone Miner's Bell Bearing" if bell_type
            else "Progressive Smithing-Stone Miner's Bell Bearing")
    return state.has(name, self.player, up_to)
```

`fill_slot_data` — emit one ordered table (Option B form):
```python
"progressiveGrants": {
  "Progressive Smithing-Stone Miner's Bell Bearing": [[280080,280090],[280110,280120],
                                                      [280140,280150],[280160,280170]],
  "Progressive Somberstone Miner's Bell Bearing":    [[280180,280190],[280200,280210],
                                                      [280230,280240],[280250,280260],[280280]],
}
```
(Option A form would instead be ordered er ids: `[8951,8952,8953,8954]` /
`[8955,8956,8957,8958,8959]`, granted via the existing FullID path.)

## 4. Client-side changes — MODERATE (the real work + rebuild)

The grant path resolves one fixed er id per ap id (`apIdsToItemIds → GrantFullID`), so a
progressive item needs new handling:

1. **Consume `progressiveGrants`** at connect into `unordered_map<string, vector<vector<uint32_t>>>`.
2. **Per-item counter** `unordered_map<string,int>`: on receiving a progressive item,
   take `grants[name][counter]`, set those flags (Option B) — or grant er id (Option A) —
   then `counter++`.
3. **Reconnect correctness (the one fiddly bit).** AP replays the full item list every
   connect; the client skips re-granting via `last_received_index`. The counter must
   still advance across the skipped prefix or tiers desync. Cleanest: in the ordered
   receive iteration, advance the per-item counter for *every* occurrence, and only
   perform the flag-set/grant for items past `last_received_index`. Deterministic because
   the replay order is fixed. Idempotent flag-sets make this safe even if double-applied.

No new persistence file needed — counters are rebuilt from the ordered replay each
connect.

## 5. slot_data contract

- New key `progressiveGrants` (Option B: name → ordered list of flag-groups). Absent ⇒
  client no-ops (back-comp). Bump the `versions` band (beta.N lockstep, per the contract
  note in `fill_slot_data`).
- Sentinel `apIdsToItemIds` entry for each progressive item so the receive loop doesn't
  warn "not found in item pool" (reuse the lock-sentinel routing).

## 6. Gating & interactions

- **`auto_upgrade == 0` only.** With auto-upgrade on, drop the progressive bells from the
  pool entirely (weapons upgrade free). Mutually exclusive with the current default.
- **`dlc_only`:** Roundtable/Twin Maidens reachable from load (`startGraces` 71190), so
  the shop is usable — good fit.
- **Trimmed pool:** pairs with the stone-check cut (`er-trimmed-curation-impl`): cut raw
  stone checks, deliver the ladder via these bells instead.

## 7. Effort / risk summary

- AP side: ~1–2 hrs (2 items, pool swap, 1 logic fn, 1 slot_data table).
- Client side: ~half a day (consumer + counter + reconnect handling + sentinel routing),
  plus build + in-game test. Reconnect counter is the main risk; flag idempotency de-risks it.
- Dependency: **Option B removes** the shop-refresh dependency; Option A keeps it.
- Verify in-game: (a) shop row repaint timing after flag-set; (b) reconnect tier
  alignment; (c) confirmed flag groups actually populate the Twin Maiden rows.

## 8. Decision (resolved 2026-06-16)

**Option B + cosmetic grant.** On the Kth copy the client sets that rung's
`eventFlag_forStock` group (the real unlock) AND grants the cosmetic bell goods
`STONE_BELL_GRANTS[name][K]["goods"]` so the bell shows in the menu. No Twin Maidens
hand-over; shop-refresh dependency retired.
