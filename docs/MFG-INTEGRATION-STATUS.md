# Optional map tracker: integration status and acceptance

The map engine and AP client are separate components. A source-built engine with
the read-only v1 exports is required; the client never loads a map DLL itself.
The performance experiment is independent of the matching and UI work.

## What each result means

- A native marker identity can select candidate AP checks through its original
  table-qualified lot and/or original acquisition flag.
- The connected seed narrows that candidate set. Exact catalog-name agreement
  guards against reused AP IDs; an ID match alone is insufficient.
- Shared acquisition flags can leave multiple candidates. No first-sibling
  selection is implied.
- AP completion says the server checked the location. It does not prove a
  physical visit; boss sweeps are a separate completion route.
- A saved hover is an observation from its recorded time, not a live selection.
- Candidate mapping, recorded coordinates, and player reports are not independent
  corroboration. Unknown identities and positions remain explicit.
- Special-rule readiness remains separate work under world issue #1085.

## Independent development tracks

World PR #1424 inventories source identities, positions and native-marker
coverage. Client PR #628 consumes candidate identities in F6 and links to the
player notebook. Engine PR #2 measures map-call costs without enabling the
legacy deferred-layout optimization. These tracks need not wait on each other.

The player notebook is available at https://peliarch.ca/er/beta/review.html and
covers the full catalog. It can accept player notes without the map engine.

## Integration acceptance matrix

Run with the intended client, source-built engine and seed; record their versions.

1. With no map engine loaded, enabling the optional map workflow gives an
   actionable unavailable status. It must not load or install anything.
2. With the source-built engine, hover two different known pins. The latest
   accepted observation identifies candidates from the current seed.
3. Opening F6 preserves the saved observation and clearly describes it as history.
   Input captured by the client must pause background hover sampling.
4. Disabling/clearing the workflow and disconnecting or switching seeds clears
   old observations; an old handle cannot be carried into a new session.
5. A shared-flag pin lists all remaining seed candidates. A contradictory flag/lot,
   malformed identity, or catalog-name mismatch must not select a location.
6. A pin absent from the seed says so rather than presenting a full-catalog match
   as a current-seed check.
7. Review links use the exact candidate ID/name. Opening one submits no report.
8. An AP-completed check is labeled as AP completed; physical collection remains
   unproven unless separately witnessed.
9. Collect a known pickup and confirm normal pin hiding still works. Reopen the
   map and test layer changes; no optimization is required for this check.
10. With optional sampling disabled, no continuing hover API polling occurs.
    With it enabled, polling is bounded and does not log every pin/frame.

For a detailed performance capture, follow the engine's docs/fastmap-profile.md.
Record stationary, pan/zoom, and close/reopen intervals separately. Call timings
are not frame times, and hiding gathering nodes does not remove injected rows.

## Recorded live witnesses

See MFG-LIVE-VALIDATION-2026-09-05.md for the exact Glintstone Scrap and Flail
observations. The Greatsword's disappearing pin is a collection/visibility witness,
not a recorded identity match. These witnesses do not validate the whole catalog.
