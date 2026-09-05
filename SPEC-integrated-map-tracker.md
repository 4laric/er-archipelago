# Integrated F6 and MapForGoblins tracker

**Status:** proposed implementation specification, 2026-09-05. No native bridge has
been built or game-tested. This is the next stage after [client PR 627][client-pr]
and [world PR 1422][world-pr], which add opt-in browser review links and an outdoor
review map. Those PRs do not control MapForGoblins.

**Recommendation:** build a maintained map-engine fork from the available C++
source, use the supplied 2.1.3 DLL as a behavioral reference, and make the existing
Rust F6 tracker its AP controller. Ship one coherent experience in one optional
bundle, initially as two DLLs. Do not duplicate the AP client or try to call
unexported functions in the released DLL.

The first release targets vanilla Elden Ring + DLC with Archipelago. Compatibility
with a separate Item/Enemy Randomizer installation is an explicit later matrix
entry, not something inherited automatically from upstream's claims.

## 1. What “fully integrated” means

A player enables **Map tracker** once in client settings. F6 then provides:

- **Checks in this seed**, with remaining/completed filters and consistent totals.
- **Show on map** for a location, highlighting its pin on the game's own map.
- Hovering a native pin selects the corresponding check in F6 without revealing
  an unhinted randomized reward.
- Plain labels: **Remaining**, **Completed**, **Area locked**, **Needs review**,
  **No precise pin**. “Area unlocked” must not be renamed “reachable” when the
  underlying model only knows coarse region access.
- **Review this location**, leading to the player form with the exact check and
  selected marker context. “Something is different” is as easy as confirmation.
- Optional **Help verify locations** mode for finding checks that need evidence.
  Normal play does not become a review queue.
- Keyboard and controller operation, with one settings surface and predictable
  input focus. The native map continues to own its cursor and pan/zoom controls.

A check can legitimately have several possible sites, an approximate anchor, or
no mappable position. Full integration means every seed check is accounted for,
not that all 4,925 catalog checks acquire invented exact coordinates.

The ordinary F6 list and browser-review fallback remain usable without the addon.
The final release is opt-in and persistent; the current PR's session-only review
checkbox is a separate, smaller feature.

## 2. What we actually have

| Input | Verified fact | Consequence |
|---|---|---|
| Public source | [a25443312dd07c21bb616bd2aeda16ee889df045][source], July 16; CMake version 2.0.6 | A readable implementation, not source for the supplied release |
| Supplied vanilla DLL | Package README says 2.1.3, adds game 1.17 support and performance/stability improvements | Current-game support must be recovered or reimplemented before replacing it |
| Binary interface | x86-64 PE export-directory RVA and size are zero | No callable external API; the current client probe cannot turn this into a bridge |
| Settings | Supplied INI uses native menu mode; [old schema][schema] describes overlay render modes | Menu/render architecture changed between source and binary |
| Generated data | [Ignore rules][ignore] exclude vanilla and shared generated directories | A plain source checkout is not a complete vanilla build |
| License | Bundled license permits modification/distribution with notices retained | A maintained source fork is permitted; retain upstream and dependency notices |
| Existing browser map | PR 1422 plots 2,019 of 4,925 catalog checks | Useful fallback, not a complete native-map coordinate database |

Reference binary SHA-256:

    ed984d5bb3ee49e304ab02e5ac1bc1bfc3a6368c2bc8743f85edefe2a73f2ea3

Its package README is release documentation, not proof that its runtime is correct.
We have inspected it statically, not run a comparative game session.

The source already contains the essential pieces: map-row injection, original and
live loot references, [hovered-row detection][hover], [focus/highlight support][inject],
map projection, completion hiding, category controls and per-save manual hides.
The work is adapting and hardening those pieces, not inventing a map renderer.

Two important corrections to the older SPEC-map-for-goblins.md:
“reads the loaded regulation” does not prove timing compatibility with AP's later
rewrites, and a disappearing marker does not prove a check was visited or reported.
Both require explicit integration and tests below.

## 3. Architecture and ownership

    AP server / existing client
              |
        F6 tracker model ----------> player review browser / saved report
              |
       seed binding + policy
              |
       versioned C interface
              |
      maintained MFG map engine
              |
      game's native map and pins

**Rust client owns:** connection, seed identity, checked locations, pending reports,
hints, existing region/access policy, review metadata and player-facing controls.

**Map engine owns:** native hooks, injected rows, row lifetimes, marker identity,
projection, map layers and applying presentation changes. It is the only writer
of its native map rows.

**World/tools own:** a versioned check-to-site manifest and its provenance. This
manifest is not another hand-maintained list of AP locations.

Keep the map engine a separate library initially. A single binary would require
additional C++/Rust build and renderer consolidation without improving correctness.
One UI does not require one DLL. Do not share C++ containers, Rust objects or ImGui
contexts across the interface.

Use F6 for settings rather than reproducing 2.1.3's native F10 menu. Retain only
the map engine's drawing facilities actually needed for pins/highlights. If
projected highlight rings require upstream overlay code, either keep a minimal
non-interactive drawing surface or port that drawing to our existing overlay;
do not accidentally retain a second input-capturing settings window.

## 4. Recover a buildable, current-game baseline first

### Required inputs and environment

- An isolated Windows staging/build area, VS 2022 C++ tools, CMake 3.28.1+,
  Python and the upstream tool dependencies.
- The user's matching, unpacked vanilla game + DLC inputs: regulation, maps,
  events, messages and required art. The [pipeline][pipeline] also references the
  game's Oodle library. Our gen_inputs.db does **not** contain the MSBs needed
  to replace these inputs.
- Pinned SoulsFormats/Paramdex and other dependency versions, with dependency
  hashes and notices. The repository contains relevant libraries/definitions;
  their compatibility with current inputs still needs verification.
- A known game executable build/hash and a repeatable offline test character.
  All extraction/build work stays outside the live er-archipelago checkout.
  Restricted game inputs must not be committed or published.

Regenerate both src/generated_vanilla and src/generated_shared using the real
upstream build pipeline. Its batch file supports the vanilla profile and invokes
generation before compilation. Capture every required input and generated output
in a manifest; do not quietly compile the committed ERR data instead.

First compare two clean generations for identical normalized data. Do not require
a reconstructed 2.0.6 build to byte-match the unrelated 2.1.3 release. Reproducible
outputs from our own pinned source/data/toolchain are the achievable contract.

### Close the 2.0.6 → 2.1.3 gap

Create a compatibility inventory for every active hook and game structure:
source location, signature, expected unique match, calling convention, fields read
or written, supported executable hash, and failure behavior.

Use the DLL for a bounded investigation:

1. Inventory its resources, imports, embedded strings, settings and marker counts.
2. Compare stock 2.1.3 and the source build in **separate** equivalent game runs.
3. Where the source fails on the current game, use targeted disassembly/debugging
   to understand that specific change and implement a source-level fix.
4. Add a reproducible probe/regression case for each recovered behavior.

A copied offset is not a supported interface. No integration should depend on
reaching inside stock MapForGoblins.dll. A signature hit alone also does not prove
that a structure layout or function call is safe.

Baseline parity must cover current-game startup, map open/close, base/DLC/underground
layers, loot pickup hiding, manual hide/restore, anonymous labels, save reload,
load timing and map performance. Classify differences as required fixes, intentional
F6 replacements, or deferred upstream features. The newer menu need not be cloned;
current-game safety and stability cannot be waived to get an early demo.

**Gate:** a repeatably built vanilla engine works on the target game without AP
integration. Until then, estimate the port as an investigation, not a small wrapper.

## 5. Build a trustworthy check-to-marker registry

The registry must distinguish:

- AP location ID and catalog revision.
- Original source identity: acquisition flag, lot table/row, entity/site identity
  and alternatives where known.
- Live runtime flag(s), which may differ after AP or randomizer rewriting.
- A generation-scoped runtime marker handle.
- Physical map, layer/floor, original position, displayed position and precision.
- Binding result and provenance.

Original position and displayed position are separate because upstream's
[generator][pipeline] deliberately offsets overlapping icons. A de-overlapped
icon location must never be exported as the pickup's actual coordinates.

Match by source identity, scoped to the current catalog and seed. A flag is a
useful join key, not a universal unique identifier. Never match solely by the item
currently in the lot, display name, row offset, icon category or nearby coordinates.

Required outcomes are **exact**, **multiple sites**, **approximate anchor**,
**unresolved**, and **not in this seed**. Keep explicit candidates for ambiguity.

Every seed check belongs to exactly one binding outcome in the coverage report.
Count checks and physical pins separately. Account for all checks, including shops,
dialogue rewards, boss rewards, scripted drops and checks with no physical pickup.
A merchant or dungeon entrance can be an anchor, visibly labelled as such; it cannot
masquerade as an exact item position.

The public pipeline's scripted-award search scans for numerical co-occurrences
and its fallback can choose the first candidate. Such rows need their heuristic
provenance retained; they do not automatically qualify as exact pins. Audit those
joins instead of importing upstream positions as independently verified truth.

Prefer rebuilding positions from game data to scraping binary arrays. If binary
data recovery is necessary, isolate it in an offline, hash-specific extractor
with layout/size/finite-coordinate checks and known witness rows. Keep unresolved
records unresolved. Do not make runtime DLL memory scraping the production data path.

## 6. Add a small, negotiated interface

The API described here is **new work**, not an API exported by either input.
Finalize a C header with explicit widths, packing, calling convention and ownership
before implementing either side. Update the client's existing observation-only
probe together with it; do not infer support from the older proposed symbol names.

Logical operations:

| Operation | Purpose |
|---|---|
| Negotiate interface | ABI version, structure sizes, supported features, build/data IDs |
| Read marker snapshot | Copy stable identity and presentation facts to caller-owned buffers |
| Read hover snapshot | Selected handle, layer, freshness and generation |
| Publish seed presentation | Batch seed membership, completion presentation and allowed labels |
| Focus / clear focus | Highlight an explicit set of bound sites |
| Clear AP session | Remove our overrides on disconnect or seed change |

Exports copy or enqueue work; they must not perform arbitrary game-memory mutations
on the caller's thread. Apply queued changes at the map engine's established safe
update point. Establish that point explicitly: the presence of a manual-hide mutex
in the old source does not make every row list thread-safe.

No raw game pointers cross the boundary. Reject stale generations, unknown handles,
unsupported versions, oversized batches and invalid coordinates. Define bounded
buffer negotiation, all-or-nothing updates and error codes. A row-table rebuild
invalidates every previous handle.

Publish snapshots and state changes in batches. Do not scan thousands of rows,
read the server, serialize JSON or make HTTP requests in the render callback.
Coalesce updates; hover can use a small cached snapshot with a documented expiry.
Measure acceptable refresh rates rather than assuming per-frame full scans are cheap.

## 7. Make collection, visibility and evidence different states

Use three separate state families:

1. **AP completion:** unchecked, locally reported/pending, server-confirmed.
2. **Map presentation:** visible, hidden by player, hidden by map discovery,
   filtered out, unsupported layer or missing position.
3. **Review status:** needs evidence, source agreement, conflicting reports.

None implies either of the others. In particular:

- Hidden is not completed.
- A boss sweep can complete a check without a player visiting its site.
- A coordinate from MFG and a coordinate from our datamine are not two independent
  sources if both derive from the same game records.
- A live pickup flag is diagnostic context, not a submitted player observation.

AP owns AP check completion; non-AP landmarks may retain the map engine's normal
game-state behavior. Review mode can expose completed AP sites deliberately, while
respecting manual hides unless the player explicitly chooses to reveal them.
Use a presentation override, never a write to acquisition/completion flags.

Order visibility policies explicitly: valid session/binding, spoiler permission and
map discovery, selected filters, completion display, manual hide. Highlighting must
not silently bypass a spoiler or discovery restriction. Existing upstream focus
behavior must be audited here rather than inherited.

Unhinted randomized rewards stay anonymous. “This seed” is the default population;
browsing the wider catalog requires an explicit spoiler opt-in.

## 8. Join F6, native pins and player reviews

First implement one exact pickup end to end:

- F6 selection → native highlight.
- Native hover → F6 name/status.
- Complete the check → consistent F6/map presentation.
- Quit/reload → fresh handles and correct restored state.
- Review → matching check/site context, with no automatic confirmation.

Then extend to multi-site rewards, merchants, interior layers and other binding
classes. Multiple checks on one pin open a small chooser; multiple sites for one
check remain individually identifiable.

A review export should contain catalog and map-data revisions, original check
identity, selected site's precision/provenance, client/addon/game versions and the
player's finding. Keep the selected catalog pin separate from a player-proposed
corrected position and from any optional captured game position.

Position capture is explicit and sampled on the game thread, with map/layer,
freshness and load state. Never prefill “I found it here” from that sample. Reports
are saved/copied or submitted by a deliberate player action; no background telemetry.
Public links must not contain credentials, room addresses, slot names or seed secrets.

The browser remains useful for writing a longer report and attaching a guide.
F6 may later add a short “right / different / unsure” draft panel, but the draft and
browser must share a schema so the reviewer does not enter the same details twice.

## 9. Lifecycle, packaging and recovery

Give the fork its own version and provenance; do not call a rebuilt 2.0.6-derived
binary “upstream 2.1.3.” Package exact client, engine and data revisions together.

The integrated profile loads **one** map engine. Detect/disable a duplicate stock
MFG installation instead of allowing two engines to inject rows and hook the same
functions. Never attempt to unload and replace a hooked DLL while the game runs.

- At startup, negotiate before enabling AP-specific presentation.
- At character/seed changes, clear session state and regenerate bindings.
- At map-table rebuilds, retire old handles before publishing new snapshots.
- On disconnect, clear AP-specific labels/focus under a documented conservative
  policy; do not leak a previous seed's information.
- If unsupported or unavailable, keep ordinary F6 and the browser fallback.
- Runtime disable clears owned overrides safely; full engine replacement requires
  a restart and an alternate loader profile.
- Migrate manual-hide preferences only when marker identity is demonstrably stable.

Show actionable messages such as “Map addon needs updating” or “No precise pin for
this check.” Keep flags, ABI versions and diagnostics behind a technical-details
panel.

## 10. Work packages and exit gates

| Stage | Deliverable | Required exit evidence |
|---|---|---|
| A — baseline inventory | Pinned source/DLL/input manifests and a differences register | Missing inputs identified; exact game build fixed; no assumed 2.1.3 parity |
| B — rebuild and port | Reproducible vanilla map-engine build for the current game | Baseline matrix passes without AP; failures on unsupported builds are safe |
| C — bindings and interface | Check/site registry, API header, fake engine and host tests | All seed checks accounted for; stale/ambiguous/malformed cases rejected |
| D — integrated vertical slice | One pickup through F6, hover, highlight, completion and review | In-game recording/logs across reload; completion and observation remain distinct |
| E — complete tracker behavior | Binding classes, filters, controller flow, interiors and multi-site UI | Full acceptance matrix; explicit residual/approximate coverage |
| F — release hardening | Versioned bundle, diagnostics, CI and rollback profile | Performance/soak results and reproducible release manifest |

A–B are the high-uncertainty work. Do them before promising a delivery date for C–F.
The first useful decision point is a current-game source build plus one correctly
identified hover; it tells us whether to continue the fork or wait for updated source.
Do not commit to reconstructing every undocumented 2.1.3 feature.

Required roles/resources: one owner comfortable with Windows C++ hooks and Rust
client integration, an isolated game-data/build environment, and a player/tester
for repeatable in-game acceptance. Agent work can cover source analysis, tools,
pure logic, fixtures and builds; it cannot substitute for actually exercising the
DLL in the game.

## 11. Verification that blocks release

**Automated:** deterministic data manifests; complete check partition; duplicate and
ambiguous identity fixtures; rewritten live flags; invalid/stale handles; ABI
mismatches; atomic state updates; reconnect/reload invalidation; escaped review
links; client/world version pairing; no unintended game-flag writes.

**In game:** base/DLC/underground maps, nearby-but-different floors, map fragment
gates, direct pickups versus sweeps, server reconnect, hints/anonymous rewards,
shops and multi-site quests, manual hides, death/warp/quit/reload, both supported
loader orders, keyboard/controller focus, and disabling the feature. Test a separate
randomizer only before advertising that combination as supported.

**Performance:** paired traces against stock 2.1.3 and against AP without the addon
on the same hardware/save/route. Record frame-time percentiles, map-open latency,
memory and repeated-reload growth. Proposed initial budget: no sustained frame-time
regression above 5% and no new visible map-open hitch in the agreed test scenes.
These are acceptance targets, not measurements already obtained.

**Coverage:** publish exact, multi-site, anchor and unresolved counts by check
category. Also count markers lacking a seed check. All catalog and seed checks
must be accounted for; “all mapped” is not an acceptance criterion if it hides
uncertainty.

**Evidence integrity:** a pin selection, AP acknowledgement or map-derived
coordinate must never automatically promote a corroboration claim.

## 12. Go/no-go decision

Proceed with the source fork if we can regenerate the vanilla data and establish
a safe current-game baseline. Prefer a narrow source-level port for failures
identified against 2.1.3, and keep those patches separable from AP integration.

Pause the native replacement if the baseline remains unsafe, essential data cannot
be regenerated, or unresolved runtime behavior cannot be bounded. The existing
F6/browser work remains useful while waiting. If VirusAlex publishes newer source,
rebase the narrow compatibility patches and bridge, regenerate data and rerun the
same gates; do not discard the registry, tests or UI contract.

**First implementation milestone to commission:** stages A–B followed by the
read-only portion of C and one hover-to-check demonstration. That proves the risky
foundation before spending effort on a polished full tracker.

[source]: https://github.com/VirusAlex/ERR-MapForGoblins-DLL/tree/a25443312dd07c21bb616bd2aeda16ee889df045
[ignore]: https://github.com/VirusAlex/ERR-MapForGoblins-DLL/blob/a25443312dd07c21bb616bd2aeda16ee889df045/.gitignore
[schema]: https://github.com/VirusAlex/ERR-MapForGoblins-DLL/blob/a25443312dd07c21bb616bd2aeda16ee889df045/src/goblin_config_schema.cpp
[hover]: https://github.com/VirusAlex/ERR-MapForGoblins-DLL/blob/a25443312dd07c21bb616bd2aeda16ee889df045/src/goblin_maphover.hpp
[inject]: https://github.com/VirusAlex/ERR-MapForGoblins-DLL/blob/a25443312dd07c21bb616bd2aeda16ee889df045/src/goblin_inject.hpp
[pipeline]: https://github.com/VirusAlex/ERR-MapForGoblins-DLL/blob/a25443312dd07c21bb616bd2aeda16ee889df045/tools/README.md
[client-pr]: https://github.com/4laric/from-software-archipelago-clients/pull/627
[world-pr]: https://github.com/4laric/er-archipelago/pull/1422
