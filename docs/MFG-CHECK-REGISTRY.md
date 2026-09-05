# Check/source registry: first implementation milestone

Build a development manifest from committed inputs, without game files or AP installed:

    python3 tools/export_mfg_check_registry.py --out /tmp/mfg-check-registry.json
    python3 tools/export_mfg_check_registry.py --out /tmp/mfg-check-registry.json --check

This does not change slot data or add a player feature.
The generated file is an explicit development output, not a checked-in release asset.
The source-built map engine exports read-only marker identities (table and lot row).
Client PR #628 consumes them in F6 with connected-seed filtering and player-review
links. This exporter supplies the static registry; it does not install either component.

Schema version 1 contains every AP location in LOCATIONS, sorted by AP ID, and SHA-256
fingerprints of all four source files. Missing files, invalid coordinate kinds,
nonfinite coordinates, unknown lot tables, duplicate IDs, and empty catalogs fail.
The check command compares the complete deterministic output, including source hashes.

## Identity and positions

- original_acquisition_flag is the original catalog flag, including shop stock flags.
  It must never be replaced by a randomized live flag.
- source_identity.item_lots names the table (map or enemy) and row_id separately.
  Equal row numbers in different tables are different identities.
- source_identity.scope is acquisition_flag_group. These are candidate identities
  for the entire flag group, **not a proven lot-to-individual-AP-check assignment**.
- co_triggered_ap_ids preserves every AP location sharing that flag. A hover may
  legitimately identify a group. Consumers must not choose the first sibling.
- physical_sites preserves map-local XYZ, including height and interior map IDs.
  These positions come from MSB treasure/enemy parts through item_grace_coords.tsv.
  They are candidates joined by flag, not independently verified exact pickup points.
  map_id_scope exposes partial map IDs already present in the source; consumers must
  not invent missing map-version fields or treat partial IDs as exact native row keys.
- display_position is null. Projection, underground transforms and displaced icons
  belong to the map engine; writing them over physical coordinates would lose evidence.
- No lot-to-position or entity relationship is invented. The committed coordinate
  table does not carry that information. The source fork must expose original
  identity and preserve the relationship when generating its native registry.

The mutually exclusive site_status partition is unresolved (no recorded position),
ambiguous_shared_flag (positions exist but several checks share the flag),
multiple_candidate_sites, or single_candidate_site. The latter is still a data
candidate, not corroboration. Shared flags without positions remain unresolved;
co_triggered_ap_ids independently exposes their identity ambiguity.

On the v0.6 input snapshot 45048ceb this accounts for all 4,925 checks:
3,075 single-site candidates; 660 with multiple candidates; 160 shared-flag ambiguous
with positions; 1,030 without a position. These include interiors and are not the
browser's outdoor coverage count. Run the tool to derive current counts.

Grace coordinates are explicitly counted and excluded from check sites. Unused
side-table flags are retained as residual_source_flags, rather than silently dropped.
They are not automatically missing AP checks.

## Validation and next consumer

Run the AP-free test directly:

    python3 greenfield/eldenring/tests/test_gf_mfg_registry.py

Tests cover shared flags, overlapping map/enemy row spaces, distinct floors at the
same XZ, duplicate position collapse, missing and corrupt input rejection, catalog
totality, deterministic encoding and provenance. No current-game behavior is claimed.

The next consumer must intersect the registry with the connected seed's check set,
validate original flag and lot table together, return all unresolved candidate checks,
and keep AP completion, physical visits, map visibility and player review separate.
Neither this file nor a successful match can count as independent corroboration.

## Offline hover consumer

    python3 tools/resolve_mfg_hover.py --lot-table map --lot-row 14000960
    python3 tools/resolve_mfg_hover.py --original-flag 197 --lot-table map --lot-row 10180

The first resolves the baked Dark Moon Ring map lot to AP check 7770000. The second
retains both checks 7770007 and 7900004 sharing flag 197. These are committed-source
witnesses, not in-game demonstrations. A supplied flag must agree with the supplied
lot. Unknown original flag is zero; a baked lot can independently select candidate
flag groups. No identity, a wrong table or contradictory identifiers returns unmatched.

The tool calls the same pure resolve function exercised by the tests. Its response is
single_candidate, ambiguous_candidates, or unmatched, with every candidate grouped
by original acquisition flag. A native consumer must additionally restrict this to
the connected seed and reject stale runtime handles before presenting a result.

## Measure a generated native profile

Compile the source fork's tools/export_ap_marker_lots.cpp against its generated
profile and save its CSV, then run:

    python3 tools/report_mfg_marker_coverage.py marker-lots.csv --out coverage.json

The CSV contract is marker_row_id,lot_table,lot_row; table 0 is unknown and must
pair with lot 0, table 1 is map, table 2 is enemy. Duplicate marker IDs, empty input,
malformed rows and inconsistent unknown pairs fail before a report is written.

The report inventories every catalog check as with or without candidate baked
markers, every native marker by matching status, and all candidate flag groups.
Shared-flag siblings stay together. Unknown identity and a known identity without
a catalog match are separate counts. The exact CSV bytes and registry input files
are SHA-256 stamped. There is no spatial, exact-site or live-game validation claim.
A regenerated profile may move these counts; inspect provenance before comparing.

### Bounded marker audit (2026-09-05)

The source-built vanilla profile used for the first live validation contained 7,031
markers (CSV SHA-256 `ce93110fbd4a2ec1e7328a8b71f2273c270323f5b63fd29c3a2a523331b309a3`).
The marker-level result was:

| marker status | count | action |
| --- | ---: | --- |
| `single_check_candidate` | 3,735 | show the one static AP candidate, subject to connected-seed filtering |
| `shared_flag_candidates` | 223 | retain every sibling in the original flag group; require review |
| `unmatched` | 94 (40 map, 54 enemy) | retain as an unresolved native lot; do not infer from names or proximity |
| `unknown_identity` | 2,979 | retain as unknown; wait for a later exact identity source |

At check level, 3,628 checks had only single candidates, 219 were touched by a
shared-flag candidate, and 1,078 had no candidate marker. No marker in this profile
produced multiple original flag groups. These are static candidate classifications,
not corroboration or physical-visit claims. The report now emits
`checks_by_candidate_status` and `marker_status_counts_by_table` so the native
consumer can act on each class without turning the 3,847/4,925 candidate figure
into a confidence score.
