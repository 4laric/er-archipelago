# Runtime AP Flower without a file override

Status: proposed; diagnostic prototype required before implementation commitment.
Scope: native Elden Ring inventory, shop and pickup UI. This is separate from M4G map pins.

## Problem and desired result

During v0.6 smoke, Deadly Poison Perfume Bottle displayed another weapon's icon,
Wretch's class preview was blank, and other class previews were incorrect. Disabling
Flower restored the icons; M4G pins were correct. This isolates the installed Flower
override as the trigger, but does not establish whether its original atlas, layout
compatibility or repacking was wrong.

The former Flower package replaced whole `menu/{hi,low}/01_common.tpf.dcx` files
to change one sprite. v0.6.0 omits that package and uses the Telescope icon.
This proposal replaces the old dependency with a client-owned runtime patch of the atlas
actually loaded by the game. Players should need neither UXM extraction nor an ME3
asset override for Flower. Continue using the normal DLL loader for the AP client.

Success means the native UI renders Flower wherever the existing client selects the
Telescope icon, while every other sprite remains unchanged. A failure must preserve
the original texture and leave a named, usable AP item with a vanilla icon.

## Verified starting points

- `check_lots.rs::dress_placeholder` reads the live Telescope goods row (2040), obtains
  its `icon_id()`, and assigns that icon to the AP placeholder. It also supplies the
  name `Archipelago Item`. Do not replace the live lookup with a hard-coded icon ID.
- `shop_icon.rs` owns shop icon selection and its protection for real goods. Keep
  that policy unchanged; this feature supplies pixels, not item classification.
- `tools/build_ap_icon.py` already reads the sprite layout and splices BC7 blocks.
  Its historical observed rectangle (2132,1148,160,160) is evidence about one layout,
  not a runtime address or a universal coordinate.
- `tools/ap_icon_src/ap_flower_160.bc7` is project-owned art: 25,600 bytes, SHA-256
  `b26be52daaec18149470383e8f9fda60234a300617b596bfb15aa3c0373ec5e6`.
- The client identifies Elden Ring's renderer as DX12 in `game.rs`. MFG's separate
  overlay renderer is not an established hook into the game's native UI textures.

These sources establish the existing behavior, not a working texture hook. The exact
loader function, resource ownership, thread, synchronization and layout representation
are discovery work. No address, structure offset or callable signature is specified yet.

## Approach

Prefer a hook after the game has decompressed/resolved its texture data and layout,
but before the selected texture becomes visible to rendering. Let the game's own
loader handle archives and compression. Do not intercept arbitrary file reads or
introduce a runtime KRAK decoder/repacker.

Discover which of these seams actually exists and is safe:

1. A loader-owned CPU texture buffer before GPU upload. Patch a private copy or an
   exclusively owned buffer only when lifetime and ownership are established.
2. A validated native UI texture replacement/registration seam.
3. A GPU resource update only if the first two are unavailable and resource states,
   command submission, fences and ownership can be demonstrated. A DX12 resource
   update is not a CPU memcpy and must not run from an arbitrary UI callback.

The first prototype is observational. Do not patch pixels merely because a buffer
has plausible dimensions or resembles an atlas.

## Exact target identification

Resolve the Telescope's live icon ID through the effective UI layout. Bind the
resulting texture identity and sprite rectangle to the exact resource generation
being loaded. Layout and texture must come from the same effective asset set.

Require all of the following before writing:

- Unambiguous icon-to-sprite-to-resource association, with validated lifetimes.
- Supported texture format, dimensions, mip/subresource layout and row pitch.
- Positive, in-bounds, BC-block-aligned rectangle matching the embedded payload.
- A supported ownership and synchronization path with no concurrent readers of
  partially patched data.

Initially support only the validated one-mip, 160x160 BC7 case. Respect actual row
pitch rather than assuming tightly packed GPU memory. Reject unexpected mips,
formats, rectangles, duplicate candidates or missing layout data. Never guess a
neighboring texture, slot, scale or vertical offset.

The Telescope itself will also display Flower because the sprite is shared. This
is the same behavior as the existing override. A dedicated AP-only icon is a later,
separate registration project if a safe native API can be established.

## Lifecycle and implementation boundaries

Keep target validation, splice planning and bounds checks in a pure decision layer.
Keep texture discovery, game memory access and render-thread work in a narrow I/O
adapter. Reuse existing hook ownership and shutdown mechanisms where appropriate.

Track states per resource generation: waiting, validated, patched, unavailable and
retired. Pointer equality alone cannot identify a generation: allocations can reuse
addresses. Handle lazy loading, menu transitions, hi/low variants and resource reloads.

- Patch each validated resource generation once. Repeated callbacks are idempotent.
- Install observation early enough for native UI loading; a connection is not a
  reliable texture-load boundary. If attachment happens late, use a validated
  existing-resource path or wait for a safe reload. Never force a guessed reload.
- Disconnecting AP does not imply the shared UI texture is destroyed. Reconnecting
  must not patch an old pointer or schedule duplicate work.
- On reset/reload, retire old records and wait for the new validated generation.
- Never retain borrowed texture pointers beyond their proven lifetime.
- Unhooking must prevent new callbacks and finish or cancel owned work safely.
  Restore original blocks only while the exact resource generation remains owned
  and synchronization is safe; otherwise do not touch it. Do not promise hot-unload
  restoration until the prototype demonstrates it.

No timer-based rescans or repeated writes across all textures. Bound diagnostic work
and measure startup and reload cost. No network access or publication of game pixels.

## Failure behavior and coexistence

On any identification or validation failure, make no write. Preserve the vanilla or
mod-provided atlas. Existing AP names/check behavior continue; Telescope is the visual
fallback. Log a concise reason once per failure/generation and show an unobtrusive
client status, such as `AP icon unavailable; using the original icon`.

Provide a diagnostic disable switch. It must not disable receiving items or checks.
If an old whole-atlas Flower override is loaded, runtime splicing cannot repair its
unrelated icons. Migration must remove that override from the effective asset chain;
do not claim success simply because the Telescope rectangle already contains Flower.
Do not overwrite another mod's unknown UI atlas or restore a backup over user edits.

## Prototype and acceptance gates

### 1. Observe, without mutation

Record the exact source/build revision and the discovered call site/signature.
Capture resource identities, creation/retirement events, layout association, format,
dimensions, mip count and pitches as metadata. Record thread and ownership evidence.
Exercise startup, class selection, inventory, shops, pickup notifications and reloads.
The output must identify one correct sprite/resource relationship without relying on
atlas position guesses. If that cannot be shown, stop at a diagnostic report.

### 2. Patch one validated generation

Embed only the Flower payload. Prove that only its planned block ranges change and
that headers, padding and all other texture content are preserved. Inspect the final
uploaded/resulting resource, not only the pre-upload CPU buffer, where the selected
seam permits readback. Document the evidence limitation if readback is unavailable.

### 3. Regression and live smoke

Pure tests cover bounds, alignment, non-tight pitch, unsupported format/mips,
ambiguous identity, payload validation, repeated events, pointer reuse and retirement.
Include negative cases proving no write occurs; compare bytes outside the target
rectangle and verify the result contains the expected Flower blocks.

Live acceptance uses the game with no Flower file override:

- AP placeholder pickups and applicable shop entries show Flower and correct names.
- Deadly Poison Perfume Bottle shows its correct inventory icon.
- Wretch and the full starter-class preview list remain correct.
- Ordinary weapons, armor, goods, spells and DLC icons remain unchanged.
- Supported hi/low configurations, reopen/reload, warp, reconnect and shutdown work.
- Missing or unsupported resources produce the fallback without crashes or writes.
- M4G can be absent; when present, its native map pins remain correct.
- A second supported asset/layout configuration proves the target is resolved from
  the loaded layout rather than the historical rectangle.

Native visual smoke and resource-lifecycle evidence are mandatory. Unit tests or a
successful compile alone do not establish this feature works.

## Packaging migration

v0.6.0 already omits the atlas package as a temporary fallback. That release does
not depend on this proposal. For a future runtime implementation, only after its
gates pass:

1. Embed the project-owned payload in the client; record its hash and source.
2. Remove the requirement to fetch, ship and install full Flower atlases. Update both
   release packagers, profile generation, installers, updater and their tests.
3. Stop adding Flower-only package entries while preserving unrelated packages.
4. For existing installs, use ownership records to remove the installed Flower files
   and restore verified prior files where appropriate. Preserve modified files and
   unrelated package entries; report conflicts instead of deleting them blindly.
5. Update setup, attribution, provenance, troubleshooting and the release checklist.
   Test clean installs and upgrades from both portable and Matt-output installations.

Do not remove the existing release dependency before the runtime replacement works.
This proposal does not promise a quick v0.6 fix or silently change an existing build.
If discovery fails, a local atlas rebuild remains the fallback; a separate native-icon
registration investigation is preferable to unsafe broad texture interception.
