# DeathLink (Wave D) — wiring note

`crates/eldenring-ap/src/game/deathlink.rs` is self-contained and edits NO existing file. To make it
live, apply the edits below by hand (serially — the build runs on Windows; nothing here was
compile-checked). **The network protocol is complete**; two game-memory reads are `// RE:` stubs (see
"RE holes" at the bottom).

Files touched: `mod.rs` (2 lines) and `net.rs` (5 small sites). `grant.rs`, `features.rs`, `flags.rs`,
`detour.rs`, `Cargo.toml` need **no** change.

---

## 1. `mod.rs` — declare the module + call its tick

Behind `feature = "net"` (it depends on the AP event loop + slot_data parse).

**a) Module declaration**, next to the other `#[cfg(feature = "net")]` mods (`features`/`grant`/`net`,
~lines 28-33):

```rust
#[cfg(feature = "net")]
mod deathlink;
```

**b) Tick call** in `fn tick()`, right after the existing `features::tick();` (~line 183):

```rust
    #[cfg(feature = "net")]
    deathlink::tick();
```

`deathlink::tick()` self-gates on `is_enabled()` then `flags::in_world()` — a cheap no-op when
DeathLink is off or the player isn't loaded, same as `features::tick()`.

---

## 2. `net.rs` — configure, tag, receive, send

`net.rs` already has `use super::{features, flags, grant};` — add `deathlink`:

```rust
use super::{deathlink, features, flags, grant};
```

### 2a. Advertise the `DeathLink` tag at connect

`ConnectionOptions::tags(..)` REPLACES the whole tag set (`self.tags = ...`, not additive —
`third_party/archipelago_rs/src/connection_options.rs:48-50`), and the server reads tags from the
**Connect** packet (built BEFORE slot_data is seen). So `is_enabled()` must be known *before* the
`ConnectionOptions` build at ~line 84. The clean way is to source it from apconfig:

1. Add a field to `ApConfig` (the struct at ~line 29):
   ```rust
       #[serde(default)]
       death_link: bool,
   ```
2. In `run()` (~line 66), before the connect loop, seed the flag:
   ```rust
       deathlink::set_enabled(cfg.death_link);
   ```
3. At the `ConnectionOptions` build (~line 84), add the tag when enabled:
   ```rust
       let mut opts = ap::ConnectionOptions::new().receive_items(ap::ItemHandling::OtherWorlds {
           own_world: true,
           starting_inventory: true,
       });
       if deathlink::is_enabled() {
           opts = opts.tags([ap::tags::DEATH_LINK]); // &str -> Ustr; tags() REPLACES the set
       }
   ```

`ap::tags::DEATH_LINK` is `pub const DEATH_LINK: &str = "DeathLink"`
(`third_party/archipelago_rs/src/tags.rs:9`; `pub mod tags;` at `lib.rs:9`). `tags(impl
IntoIterator<Item: Into<Ustr>>)` accepts a `[&str; 1]` (`connection_options.rs:48`).

`configure_from_slot_data` in 2b is still the source of truth once connected and corrects `ENABLED`
from `options.death_link`; the apconfig field just makes the tag right on the FIRST connect (the
server reads tags only at Connect time, so an apconfig hint is required — slot_data arrives too late
to add the tag this cycle). If you skip the apconfig field, the tag only takes effect on the next
reconnect; the apconfig field is the recommended path.

### 2b. Configure from slot_data (in the `if !configured` block, ~line 129, near `features::configure(feat)` ~line 177)

```rust
                deathlink::configure_from_slot_data(sd);
```

Sets `ENABLED` from `options.death_link` (int-or-bool tolerant, like `enable_dlc`) and resets the
per-session latches.

### 2c. Handle the incoming DeathLink event (the `for ev in conn.update()` match, ~lines 113-125)

Add an arm. Verified variant shape (`third_party/archipelago_rs/src/event.rs:71-96`) — note
`source: String` (NOT Option), `cause: Option<String>`, `tags: UstrSet` (NOT Option):

```rust
                ap::Event::DeathLink { source, cause, .. } => {
                    deathlink::on_death_link_event(&source, cause.as_deref(), slot.as_str());
                }
```

`slot` is the local slot name already bound at the top of `connect_and_serve`. The handler does the
self-source guard (skips our own server echo) and latches the kill for the game tick.

### 2d. Drain the outgoing latch each loop iteration (near the end of the serve loop, before the `sleep`, ~line 296)

```rust
        if deathlink::take_pending_outgoing() {
            if let Some(client) = conn.client_mut() {
                let opts = ap::DeathLinkOptions::new()
                    .cause("Slain in the Lands Between.".to_string())
                    .source(slot.clone());
                if let Err(e) = client.death_link(opts) {
                    tracing::warn!("AP: death_link send failed: {e}");
                } else {
                    tracing::info!("AP: sent DeathLink");
                }
            } else {
                tracing::debug!("AP: DeathLink to send but client not ready; dropping");
            }
        }
```

`DeathLinkOptions` is re-exported at the crate root (`pub use client::*` -> `pub use
death_link_options::*`, `client.rs:14,18`). Builders verified in
`third_party/archipelago_rs/src/client/death_link_options.rs:19-76`: `.cause(String)`,
`.source(String)`, `.time(SystemTime)` (defaults to now), plus `.slots/.games/.tags`.
`death_link(&mut self, DeathLinkOptions) -> Result<(), Error>` at `client.rs:696`; it always inserts
the `DeathLink` tag and sets `time = now - server_skew` and `source = slot alias` when unset — so
passing `cause` (and optionally `source`) is sufficient.

---

## 3. Exact archipelago_rs API verified (file:line in `third_party/archipelago_rs`)

| Need | Symbol | Location |
|------|--------|----------|
| Tag constant | `ap::tags::DEATH_LINK` (`&str = "DeathLink"`) | `src/tags.rs:9` (mod at `src/lib.rs:9`) |
| Add tag at connect | `ConnectionOptions::tags(impl IntoIterator<Item: Into<Ustr>>)` — **replaces** the set | `src/connection_options.rs:45-51` |
| Incoming event | `ap::Event::DeathLink { games, slots, tags: UstrSet, time: SystemTime, cause: Option<String>, source: String }` | `src/event.rs:71-96` |
| Send a death | `Client::death_link(&mut self, DeathLinkOptions) -> Result<(), Error>` | `src/client.rs:696` |
| Send-options builder | `DeathLinkOptions::new().cause(String).source(String).time(SystemTime)` | `src/client/death_link_options.rs:19-76` |

`DeathLinkOptions` / `ConnectionOptions` / `Event` re-export at the `archipelago_rs` root
(`src/lib.rs:12-19`): `ap::DeathLinkOptions`, `ap::Event::DeathLink`, `ap::ConnectionOptions` all
resolve. `ap::tags::DEATH_LINK` is reached through the public `tags` module.

---

## 4. The two `// RE:` holes (Cheat-Engine work, NOT network)

The protocol is COMPLETE. These two GAME-MEMORY functions in `deathlink.rs` return a placeholder
until filled in a CE session (full worksheets live in their doc comments):

1. **`kill_player() -> bool`** — kill the local player on an INCOMING DeathLink. Candidates:
   (A) zero `CSChrDataModule.current_hp`, reached via the SAME `WorldChrMan.main_player` PlayerIns
   `flags::play_region_id` already resolves; (B) apply a lethal SpEffect via `CSChrSpEffectModule`.
   Returns `false` now → received deaths are logged + self-suppressed but the player isn't killed yet.

2. **`read_local_death() -> bool`** — detect the local player's death to ORIGINATE a DeathLink.
   Candidates: (A) `current_hp == 0` (shares hole #1's offset, recommended — the `WAS_DEAD` edge-latch
   absorbs the respawn frame); (B) a per-life death byte on PlayerIns (a persistent event flag is NOT
   suitable). Returns `false` now → we never originate a DeathLink yet.

Both reach the player through the exact PlayerIns pointer already proven in `flags.rs`
(`play_region_id`), so the chain to the player object exists in-tree; only the HP/death FIELD offset
is missing. Neither stub invents an offset.

---

## 5. Behavior once wired (holes still open)

DeathLink ON + holes open: client advertises the `DeathLink` tag, RECEIVES death events (logs them,
suppresses our own echo, latches a kill that no-ops until `kill_player` is filled), and watches for a
local death (no-ops until `read_local_death` is filled). Fill the two CE offsets → fully
bidirectional DeathLink.
