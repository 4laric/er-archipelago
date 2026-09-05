# Accepted Map for Goblins placement comparison — 2026-09-05

Map for Goblins is the user-accepted placement reference for this audit. No
additional wiki confirmation is required. By explicit user ruling on 2026-09-05,
**all 3,847 matched checks count as corroborated**, including the 219 with shared
identity ambiguity and the six with differing/additional sites. Corroboration is
recorded separately from spatial comparison and access-rule status. The remaining
1,078 checks are not corroborated by this M4G source. Joining a pin to an acquisition-flag
family remains distinct from proving one particular pickup belongs to one AP check.

## Reproduced results

The vanilla profile contains 7,031 native pins. Table-qualified lot matching
reproduces the previously recorded 3,847 / 4,925 AP-check coverage (78.1%).

| Check result | Count |
|---|---:|
| Coordinate agreement, complete comparison frame | 1,531 |
| Coordinate agreement, interior map variant unspecified | 1,652 |
| Newly supplied position (no previous AP coordinate candidate) | 439 |
| Shared-check identity ambiguity | 219 |
| Coordinate disagreement | 4 |
| Mixture of agreeing and additional/differing sites | 2 |
| No matched native pin | 1,078 |
| Total | 4,925 |

Thus 3,183 agree spatially and 439 gain positions. Agreement uses horizontal and
vertical tolerances of 2 game units each. It means at least one existing AP site
matches the reference; it does not prove all alternative sites or every access
rule. The 1,652 partial-map agreements retain the unknown fourth interior-map byte.
AP region labels are reported, not independently adjudicated from coordinates.
The 439 are check-level gains in reference coverage, not 439 distinct physical sites.

Native identity counts: 3,735 single-check candidates; 223 shared-check candidates;
94 known lots without an AP match; 2,979 pins without lot identity. A single-check
candidate can still cover multiple different lots sharing an acquisition flag.

## Six exceptions

| AP ID | Check | Finding |
|---|---|---|
| 7770613 | Sword of Milos | Event-linked NPC reference differs from existing sites; alternate NPC placement needs association. |
| 7771310 | Mohgwyn Golden Seed | Live treasure reference differs by 126.74 horizontal / 44.69 vertical units; interior variant remains partial. |
| 7773012 | Roped Fire Pot | Traveler armor lots share flag 1048387010 with the Fire Pot lot. Their pins are 165.98 units away; this is not proof the Fire Pot moved. |
| 7774548 | Hippopotamus Scadutree Fragment | Enemy/event reference differs by 38.93 horizontal / 1.89 vertical units. |
| 7771025 | Blessing of the Erdtree | Royal Capital site agrees; another pin exists in Ashen Capital. |
| 7773471 | Furnace Visage | Treasure site agrees; separate scarab/event site is about 340 units away. |

Cipher Pata and Assassin's Prayerbook agree after reversing the explicit
Roundtable display shift in MFG `generate_data.py`. That shift occurs before
`real_posX/Z` are saved. The adapter retains both generated and restored coordinates.

## Reproduction and provenance

Use an isolated vanilla transfer bundle with its `MANIFEST.json`, item database,
and generated C++ tables. The adapter verifies every manifest byte count and hash,
requires the vanilla profile, parses exactly the declared marker count, rejects
invalid/duplicate identities, and never executes the supplied C++.

```sh
python tools/export_mfg_placement_reference.py --bundle /path/to/vanilla --output native-reference.json
python tools/report_mfg_placements.py native-reference.json --profile-manifest /path/to/vanilla/MANIFEST.json --out placement-report.json
python -m pytest tools/test_export_mfg_placement_reference.py tools/test_report_mfg_placements.py -q
```

Reference engine revision: `9550ce34a9782579f3b01b70ea7506956376230f`.
Archive SHA-256: `0a7b8fa931609fe0d778b356fff5259e150d667a0ee2c8daeed38c4285fddc39`.
Generated map-data SHA-256: `d64e94bf9b2483f3e7e77f550eb4aa4bc2b69f8d1ca7c7febf9cd094c659ee0e`.
Item database SHA-256: `34d8d52324bd440a3c5676fba3763ffbea02be498f061dd1ea29658dacd1ff7a`.
The transfer and full reports remain private; this document contains aggregate
findings and reproduction instructions. Reports retain the AP input fingerprints.

The source pipeline previously inferred lot table from placement source; an enemy
can award a map lot. This audit faithfully uses the selected profile's explicit
baked linkage and records its provenance. Correcting future extraction does not
retroactively regenerate the historical profile. No AP placement/access rule or
runtime marker behavior was changed by this audit.

## Access evidence in the same bundle

The native pins contain one explicit positive display-enable condition: marker
5500008, map lot 31000030, resolves to Murkwater Cave Glass Shard AP 7772114.
Its availability/display gate is flag 3691; collection/hide flag 31007030 is
separate. The source switch parser also recognizes the opposite chest state,
but the rendered profile does not emit that negative gate. This is concrete
additional-condition evidence, not a claim that only one check needs access logic.

The profile also supplies positions for 38 imp-statue markers, 37 interactables,
10 paintings and 62 spirit springs. These are review targets; the profile does
not assign every item behind those gates or export complete puzzle predicates.
The item database preserves six Jarburg story-unavailability observations and
458 explicit defeat observations, alongside 4,752 collection candidates.
Those are raw database-row observations, with overlap, not distinct AP checks.
Position agreement does not establish absence of extra access conditions.
