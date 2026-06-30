# PROGRESSIVE-WIRING.md — wiring the `progressive` module (Phase 5, Wave C)

The new module is `crates/eldenring-ap/src/game/progressive.rs`. It is self-contained
(net-thread queueing + game-thread drain, same pattern as `features.rs`) but needs a handful of
lines added to the shared modules. I did NOT touch any of these files — apply the edits below
serially. Nothing here changes behavior for seeds without a `progressiveGrants` key (the parse
returns an empty map and `on_item_received` returns `false` for every name).

Threading invariant preserved: `progressive::parse` / `configure` / `on_item_received` run on the
NET thread and only touch our own queues + the persisted counter/high-index; `progressive::tick`
runs on the GAME thread and is the only place `grant_full_id` / event-flag writes happen.

---

## 1. `mod.rs` — module declaration

Next to the other `#[cfg(feature = "net")]` module decls (`features`, `grant`, `net`), add:

```rust
#[cfg(feature = "net")]
mod progressive;
```

## 2. `mod.rs` — game tick

In `fn tick()`, next to the existing `features::tick();` call (the last `#[cfg(feature = "net")]`
block), add a sibling call AFTER it:

```rust
    #[cfg(feature = "net")]
    progressive::tick();
```

(Order vs `features::tick()` does not matter — they own disjoint queues. Placing it right after
`features::tick();` reads cleanly.)

## 3. `net.rs` — install config at connect

In the slot_data parse block, right AFTER the existing `features::configure(feat);` line (~178),
add:

```rust
                progressive::configure(progressive::parse(sd));
```

`sd` is the parsed slot_data `serde_json::Value` already in scope there. `configure` RESETS the
progressive queues (like `features::configure`); it does NOT reset the persisted counter/high-index
— those come from the save via `progressive::restore` (wired in step 5). Order relative to
`features::configure` is irrelevant, but keeping it adjacent matches the rest of the Phase-5 install.

Add the import alongside the other `super::` uses at the top of net.rs (it already imports
`features`, `grant`, `flags`):

```rust
use super::progressive;
```

## 4. `net.rs` — receive loop: resolve tier + SKIP the normal grant

In the receive loop (~227-255), the per-item body currently has two independent watermark blocks:
`idx >= dispatched_through` (name-dispatch, full replay) and `idx >= pushed_through` (grant enqueue).
`progressive::on_item_received` does its OWN persisted index-dedup, so call it on the full replay
(in the `dispatched_through` block) and remember the result; then use it to gate the grant enqueue.

Replace the per-item body so it reads:

```rust
                for ri in client.received_items() {
                    let idx = ri.index() as i64;
                    let name = ri.item().name().to_string();

                    let mut progressive_handled = false;
                    if idx >= dispatched_through {
                        features::on_item_received(&name);
                        dispatched_through = idx + 1;
                    }
                    // Progressive items resolve their tier here (own index-dedup vs the persisted
                    // high-index); a `true` return means "handled — do NOT grant normally" (the C++
                    // `continue`). Called on the full replay so a reconnect recomputes correctly; the
                    // module's HIGH_INDEX makes replayed copies advance no tier.
                    if progressive::on_item_received(&name, idx) {
                        progressive_handled = true;
                    }

                    if idx >= pushed_through {
                        if !progressive_handled {
                            let ap_item_id = ri.item().id();
                            match item_map.get(&ap_item_id) {
                                Some(&full_id) => {
                                    let qty = item_counts.get(&ap_item_id).copied().unwrap_or(1).max(1);
                                    grant::enqueue(grant::GrantMsg {
                                        full_id: full_id as i32,
                                        qty: qty as i32,
                                        ap_index: idx,
                                        name,
                                    });
                                }
                                None => tracing::warn!(
                                    "AP: received item id {} not in apIdsToItemIds; skipping (check seed options)",
                                    ap_item_id
                                ),
                            }
                        }
                        pushed_through = idx + 1;
                    }
                }
```

Key points:
- `progressive::on_item_received(&name, idx)` is called for EVERY item (full replay) BEFORE `name`
  is moved into `GrantMsg`, so it borrows `&name` fine.
- When it returns `true`, the grant enqueue is skipped but `pushed_through` STILL advances (the C++
  `continue` likewise consumed the index). The progressive goods/flags are granted by
  `progressive::tick()` on the game thread; the persisted high-index gates re-application.
- Non-progressive items are completely unaffected (`progressive_handled` stays `false`).

## 5. `grant.rs` — persist + restore the two progressive fields

The progressive module deliberately does NOT own a save file — `progressive_counter` and
`progressive_high_index` round-trip through grant.rs's per-seed save, exactly as the C++ kept them in
the single JSON. Two small edits:

(a) In `configure()` (the net-thread load at connect), AFTER the existing block that reads
`start_items_granted` / `notify_granted` from the parsed `v` (inside the
`if let Ok(v) = serde_json::from_str::<serde_json::Value>(&text)` arm), add:

```rust
            super::progressive::restore(
                v.get("progressive_counter").unwrap_or(&serde_json::Value::Null),
                v.get("progressive_high_index").and_then(|x| x.as_i64()).unwrap_or(-1),
            );
```

`restore` tolerates a `Null` / missing object (clears the counter) and defaults the high-index to
`-1` when the key is absent — matching `Core->progressiveHighIndex = -1`.

(b) In `write_save()`, extend the `serde_json::json!` object with the two snapshot fields. Replace
the body construction:

```rust
    let notify: Vec<i32> = notify_granted().lock().unwrap().iter().copied().collect();
    let (prog_counter, prog_high) = super::progressive::snapshot();
    let body = serde_json::json!({
        "last_received_index": idx,
        "start_items_granted": START_ITEMS_GRANTED.load(Ordering::Relaxed),
        "notify_granted": notify,
        "progressive_counter": prog_counter,
        "progressive_high_index": prog_high,
    })
    .to_string();
```

`snapshot()` returns `(serde_json::Value /* {name: int} */, i64)`. The keys match the C++
`WriteSaveFile` exactly, so a save written by either client is readable by the other.

> Note: `grant::persist()` (which calls `write_save`) is invoked by `progressive::tick()` whenever a
> tier advances, so the new fields are flushed promptly after each progressive receipt — the same
> persistence cadence as the notify/start-item drains.

grant.rs already has `use super::...` lines; the `super::progressive::` paths above need no new
import (or add `use super::progressive;` if you prefer the short form, then drop the `super::`
prefix in the two call sites).

---

## Summary of the diff surface
- `mod.rs`: `mod progressive;` decl + `progressive::tick();` in the tick.
- `net.rs`: `use super::progressive;`, `progressive::configure(progressive::parse(sd));` at connect,
  and the receive-loop gate that skips the normal grant when `on_item_received` returns true.
- `grant.rs`: `progressive::restore(...)` in `configure()` and the two `snapshot()` fields in
  `write_save()`.
- No changes to `features.rs`, `flags.rs`, `detour.rs`, or `Cargo.toml`.
