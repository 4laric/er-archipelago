# SPEC: v0.6 check evidence ledger

**Status:** proposed (2026-08-31)

**Tracks:** [#1208](https://github.com/4laric/er-archipelago/issues/1208),
[#1271](https://github.com/4laric/er-archipelago/issues/1271)

**Related:** #1092, [#1085](https://github.com/4laric/er-archipelago/issues/1085),
[#1080](https://github.com/4laric/er-archipelago/issues/1080), `PROVENANCE.md`, `CONTRIBUTING.md`,
`SPEC-provenance-oracle-20260710.md`, `SPEC-questline-dag-20260728.md`

## 1. Promise

For v0.6, every shuffled check is an auditable collection of claims.

A player or reviewer must be able to ask:

1. Why does this check exist and what does it identify?
2. Why is it filed in this region?
3. What must be done before it is obtainable?
4. How does the client detect and suppress its vanilla award?
5. Can a sweep or alternate acquisition retire it?
6. Which sources agree, which disagree, and what has not been checked?

The answer is not required to be `proven` on day one. It is required to be honest. A row with one
source says `single_source`; a disagreement says `conflicted`; missing evidence says `unverified`.
No blank cell, generated default, or confident sentence may silently stand in for proof.

This is a provenance system, not a majority vote. Two generated tables derived from the same MSB
record are one witness. Three wikis copying the same guide are one witness family. A live report
without a reproducible environment is a lead, not an adjudication.

## 2. Scope: claims, not checks

One check carries several claims with different evidence and risk. The ledger records them
separately.

| claim kind | question | minimum structured value |
|---|---|---|
| `identity` | What vanilla acquisition does this AP check represent? | flag, AP id, item/lot/shop/entity namespace and id |
| `region` | Which AP region owns it? | region key |
| `access` | What is required to obtain it? | typed requirement expression or explicit unknown |
| `detection` | What observable game state retires it? | flag/read mechanism |
| `suppression` | What vanilla award must be blanked or reconciled? | typed lot/shop/gesture/award target |
| `sweep_owner` | Which boss or field sweep may grant it? | trigger id and owner region |
| `alternate_acquisition` | Which vanilla paths represent the same check? | equivalence-group id and members |
| `description` | Where/how should the player find it? | text plus precision class |

Phase 1 must support all eight kinds. It need not populate all eight for every check.

This list is deliberately finer than the current generated location row. A region can be proven
while access remains unknown. A correct detection flag does not prove suppression is safe. The
ledger must never promote one claim because a different claim on the same check is strong.

## 3. Stable identities

### 3.1 Check identity

`check_id` is the AP location id. The current flag remains evidence about the represented vanilla
acquisition, not the primary ledger key: multiple AP ids may share a flag and alternate vanilla
paths may collapse into one future check.

Every record also stores the current human name for browsing, but names are not keys.

### 3.2 Claim identity

```
claim_id = "check:<ap_id>/<claim_kind>"
```

Claims that are naturally group-scoped use a typed group key as well:

```
group:flag:<flag>/region
group:alternate:<stable_slug>/alternate_acquisition
```

The build must reject duplicate active claims for the same `(subject, claim_kind, game_version)`.
Superseded claims remain in history but are not active.

### 3.3 Evidence identity

Evidence gets a stable id derived from its immutable citation, not from its prose summary. Examples:

```
game:emevd:m10_00_00_00:90005300:instruction-17
game:param:ItemLotParam_map:10010:lotItemId01
game:msb:m60_42_36_00:Treasure:AEG099_060_9000
wiki:wiki.gg:pageid-12345:revision-67890
testimony:discord:<message-id>:<attachment-sha256>
```

The exact formatting may change during implementation, but identity must be deterministic and
reviewable.

## 4. Evidence schema

The canonical checked-in representation is normalized TSV under `greenfield/evidence/`. TSV keeps
the current diff, attribution, and deterministic-generation habits. JSON is generated for the
browser; Python modules are generated only if runtime logic eventually consumes an adjudicated
claim.

### 4.1 `sources.tsv`

One row describes a source snapshot.

| field | meaning |
|---|---|
| `source_id` | stable source identity |
| `source_kind` | `game_data`, `external_reference`, `live_testimony`, `project_derivation`, `ruling` |
| `family_id` | independence family; see section 5 |
| `title` | short display name |
| `game_version` | version proved, or `unknown` |
| `retrieved_at` | ISO date/time for mutable sources |
| `revision` | git sha, wiki revision, corpus stamp, message id, or dump hash |
| `url_or_path` | public URL or repo-relative input path |
| `license` | licence or `project-derived`/`private-evidence` |
| `environment_id` | optional environment manifest for live evidence |
| `supersedes` | older source snapshot, if any |

Raw game assets and private attachments do not enter the repository. Their source rows carry a
hash and precise local citation sufficient to reproduce the extraction from a legitimately owned
installation.

### 4.2 `evidence.tsv`

One row states what one source says about one claim.

| field | meaning |
|---|---|
| `evidence_id` | deterministic citation identity |
| `claim_id` | claim being supported or contradicted |
| `source_id` | source snapshot |
| `stance` | `supports`, `contradicts`, `silent`, `ambiguous` |
| `value` | typed JSON scalar/object using the claim-kind schema |
| `citation` | exact event/instruction, state node, param field, page section, or message id |
| `method` | extractor/tool/procedure that produced the row |
| `independence_notes` | why this is or is not independent of adjacent evidence |
| `valid_from` / `valid_to` | game-version bounds when known |
| `notes` | short reviewer-facing context; never the only home of a numeric id |

`silent` is retained only when the source was actually searched and its coverage makes silence
meaningful. A source that was never checked contributes no row. Silence never counts as support or
contradiction.

### 4.3 `claims.tsv`

One row is the current adjudication.

| field | meaning |
|---|---|
| `claim_id` | stable claim id |
| `subject_kind` / `subject_id` | check or group identity |
| `claim_kind` | closed vocabulary from section 2 |
| `value` | current typed value, or empty when unresolved |
| `status` | closed vocabulary from section 6 |
| `risk` | `critical`, `high`, `medium`, `low` |
| `adjudication` | rule/tool/ruling that selected the value |
| `evidence_ids` | sorted list of contributing evidence ids |
| `last_reviewed` | ISO date |
| `review_issue` | issue or PR resolving a conflict/unknown |

The status is generated from evidence and policy where possible. A hand ruling is itself a named
`ruling` source; it cannot quietly overwrite the evidence rows.

### 4.4 `environments.tsv`

Live evidence is meaningful only with an environment manifest:

- game and DLC version;
- AP world and client exact versions/contracts;
- seed id and relevant YAML options;
- launcher and loaded mods;
- whether regulation or loose files were present;
- save provenance;
- reproduction steps and result;
- log/screenshot/video hashes and private/public location.

Missing fields do not make testimony worthless, but keep it at `lead` strength and prevent it from
adjudicating a critical claim alone.

## 5. Independence model

### 5.1 Families

Every source belongs to one `family_id`. Distinct rows inside a family are corroborating detail,
not independent votes.

Initial families:

| family | examples |
|---|---|
| `game:param:<table>` | raw parameter rows and direct field extracts |
| `game:emevd:<event>` | an event and all tables generated solely from it |
| `game:esd:<talk>` | one talk script/state machine and its transforms |
| `game:msb:<map>` | one map record and coordinate/region joins derived from it |
| `game:runtime:<environment>` | probe/readback or observed live behavior |
| `reference:<publisher>:<lineage>` | wiki/guide lineage, including known mirrors |
| `testimony:<reporter>:<run>` | one player's report and all attached media/logs |
| `project:ruling:<issue>` | an explicit design ruling where truth is conventional |

`data.py`, the check browser, and a report generated from `data.py` are the same project-derived
family. `msb_flag_region.tsv` and `nearest_grace.tsv` may be independent only when their actual
lineage is different; a join that ultimately consumes the same MSB coordinate does not create a
second witness.

### 5.2 Independence is claim-specific

The same pair of sources can be independent for one claim and dependent for another. An MSB
treasure record and a wiki page may independently corroborate region, while the wiki's item name
may have been copied from the game text. The evidence row therefore records a `family_id` and the
adjudicator groups by family per claim.

### 5.3 Source priority is not vote count

For game-mechanic claims, direct first-party instructions/rows outrank prose references. External
references and testimony are valuable for discrepancy discovery, coverage, and live semantics.
They do not outvote an exact pinned instruction. Conversely, a runtime probe can demonstrate that
our interpretation of a static instruction is wrong; that becomes `conflicted` until resolved,
not a forced static-data win.

## 6. Status policy

Statuses are mutually exclusive and generated from active evidence:

| status | meaning |
|---|---|
| `proven` | exact first-party datum or reproducible runtime probe establishes the claim, plus an independent corroborating family where policy requires it |
| `corroborated` | at least two independent families agree, but the claim lacks the direct authority required for `proven` |
| `single_source` | exactly one usable family supports the current value |
| `conflicted` | usable independent families disagree, or runtime evidence contradicts the static interpretation |
| `inferred` | value is produced by a documented heuristic/model rather than directly stated |
| `unverified` | no usable evidence establishes a value |

`silent` and `ambiguous` evidence never raise a status.

### 6.1 Bars by risk

| risk | examples | shipping bar for a new/changed claim |
|---|---|---|
| `critical` | access requirement that may make a seed unwinnable; suppression that may delete or duplicate progression | `proven`; no active contradiction |
| `high` | region ownership under locks; detection flag; alternate-acquisition collapse; sweep ownership | `proven` or `corroborated` with exact game-data citation; no active contradiction |
| `medium` | identity/category, shop ownership, missable classification | `corroborated` or `single_source` with direct game-data citation |
| `low` | display description and hint precision | `inferred` allowed when labelled; conflict remains visible |

Legacy rows below these bars may remain during migration. A touched row may not regress, and a new
critical/high claim must meet the bar before it affects generation.

### 6.2 Conventional rulings

Some AP regions are design boundaries rather than facts the game states. An explicit project
ruling can settle `region` when the evidence describes multiple legitimate presentations. The
claim status is `proven` only as **project policy**, labelled `adjudication=design_ruling`; the
underlying geography disagreement stays visible.

### 6.3 v0.6 per-check access gate

Region ownership is not access proof. For v0.6, every enabled check needs an active `access` claim
whose structured value separates the owning region from any additional requirement and records one
logic disposition:

| disposition | meaning |
|---|---|
| `region_sufficient` | reviewed evidence proves that reaching the owning region is sufficient |
| `encoded` | the accepted access expression is enforced by Archipelago reachability logic |
| `excluded` | the check is not enabled for the affected option set, with a linked issue/ruling |
| `waived` | a dated, explicitly reviewed release exception; never inferred from legacy behavior |
| `unresolved` | requirements or their AND/OR structure are not established |

An absent access claim is `unresolved`, not `region_sufficient`. A location's current region entrance
rule is not evidence that its item, shop, boss, or quest award can be collected. High- or
critical-risk `unresolved` access, including a claim below its section 6.1 shipping bar, blocks the
v0.6 release unless the check is `excluded` or has an explicit `waived` disposition. Exclusions and
waivers require a review issue, affected option set, reason, owner, and expiry or next-review date;
a blanket waiver for a region or claim family is invalid.

Only accepted expressions may affect generated reachability. An incomplete quest cone must remain
`unresolved`: the generator must not turn every observed predecessor into a guessed AND rule, nor
discard alternative routes and accidentally turn OR into AND. Evidence extraction and expression
encoding are tracked by #1085 and #1080; #1271 owns the complete per-check audit, disposition, and
release gate.

Initial regression examples include Lamenter's Gaol keys, Patches' shop state, the alternative
Radahn Festival routes, Sellen/Jerren endings, transformed map variants, warp-only entrances, bell
bearings, seals, gestures, and boss/event order. Each example is a class to census, not a licence to
copy one rule across every member.

## 7. Pipeline and ownership

```
licensed/private inputs         public references        live reports
          |                            |                      |
          +--> source adapters --> normalized evidence <----+
                                      |
                              claim adjudicator
                                      |
                 +--------------------+-------------------+
                 |                    |                   |
             audit TSV          offline browser       CI report/gates
                                                           |
                                            adjudicated runtime tables
                                            (later phase, explicit only)
```

Rules:

1. Adapters emit evidence; they do not edit claims or runtime data.
2. Adjudication is deterministic. The same inputs produce byte-identical status and reports.
3. External references and testimony are evidence-only by default. Runtime consumption requires a
   separately reviewed promotion step backed by the claim-type shipping bar.
4. Existing generated sources keep their current owners. The ledger references them rather than
   duplicating their entire contents.
5. Hand-curated source snapshots preserve licence, revision, and attribution. No foreign
   randomizer list becomes a checked-in source or build dependency; `PROVENANCE.md` still governs.

## 8. Audit browser

Extend the existing offline check browser or ship a sibling stamped page. One selected check shows:

- all claim kinds and statuses;
- the current value and risk;
- evidence grouped by independent family;
- exact citations and source versions;
- disagreements, ambiguity, and searched-source silence;
- derivation lineage so two dependent outputs cannot look independent;
- review issue, last-reviewed date, and a permalink;
- a history/diff view between builds.

Top-level facets include status, claim kind, risk, game version, evidence family, conflict, stale
source, and “changed since baseline”. The page also exports a risk-ranked audit queue. It is a
reader and worksheet, never an oracle.

The four questions the browser must answer without reading code are:

1. Why is this check here?
2. What says the player can reach and collect it?
3. What disagrees with that answer?
4. What evidence would graduate it to the next status?

## 9. CI ratchet

A hard 100% gate on the existing corpus would freeze development or encourage fake evidence. CI
therefore tightens in stages.

### Phase A: schema and baseline, report-only

- validate closed vocabularies, typed values, citations, source references, and deterministic order;
- calculate coverage/status counts by claim kind and risk;
- reject dangling evidence, duplicate active claims, unknown source families, and dependency loops;
- commit a generated baseline manifest with counts and content hash.

### Phase B: no-regression gate

For every changed check or claim:

- status may not weaken without an explicit issue and `expected_regression` ruling;
- evidence families may not disappear silently;
- `proven` may not survive a new active contradiction;
- game-version applicability may not be widened without evidence;
- new critical/high runtime claims must meet section 6.1.

Global coverage percentages may not fall below the baseline. Improvements update the baseline in
the same reviewed commit, making progress one-way.

### Phase C: risk ratchet

Gate complete coverage in this order:

1. progression-bearing checks and goal prerequisites;
2. access, suppression, and detection claims;
3. region-lock and sweep claims;
4. shops, alternate acquisitions, and missable quest awards;
5. remaining identity and descriptions.

Each rung ships only after its exact population and exception list are measured. Exceptions carry
an issue and expiry/review date; a blank exception is a failure.

For v0.6, rung 2 is a release gate rather than a post-release ratchet: every enabled check must have
an access claim and logic disposition as defined in section 6.3. The generated report must fail on
missing dispositions and on unresolved high/critical access claims without a valid exclusion or
waiver. It must also drift-check the accepted `encoded` expressions against the reachability rules
shipped by the world.

### Current-corpus access gap (2026-09-01)

The normalized current-corpus ledger at `66d50a54` contains 4,923 region claims but only 8 access
claims. Therefore **4,915 checks have no access claim at all**. The 8 present access claims are all
`critical` and `single_source`, below section 6.1's `proven` shipping bar. On the evidence ledger
alone, **0 of 4,923 checks currently satisfy the full v0.6 access gate**.

This is a migration census, not a finding that 4,923 runtime rules are wrong. Many checks will
graduate cheaply to `region_sufficient`; the ledger currently has no auditable row saying so. The
count must be regenerated from `claims.tsv`, split by disposition/risk/option set, and ratcheted in
release review rather than copied forward as a permanent constant.

## 10. Migration plan

Each step is independently useful and shippable.

1. **Skeleton and census.** Create the schema/validator and emit `identity` plus `region` claims
   from current generated locations, explicitly marking their shared lineage.
2. **First-party adapters.** Add direct citations from item lots, shops, MSBs, EMEVD/ESD, params,
   region joins, and questline corpora. Preserve exact row/event/state references.
3. **Known-curation import.** Convert region overrides and other reason-carrying tables into ruling
   evidence without removing their current runtime ownership.
4. **External-reference adapter.** Generalize #1092 and the second-opinion worksheet with pinned
   page revision, timestamp, game version, licence, and lineage. No bulk wiki prose.
5. **Testimony intake.** Define a small report template and importer for logs/screenshots/video
   metadata. Attachments remain outside git; hashes and public message links may enter.
6. **Browser and audit queue.** Put conflicts and high-risk single-source claims first.
7. **Phase-B CI.** Freeze evidence regressions for touched claims and require bars for new claims.
8. **Risk audits.** Progress through section 9, opening focused defect issues from disagreements.
9. **Runtime promotion.** Only after claim-type bars and tests exist, let adjudicated claims replace
   current hand paths one population at a time.

The first implementation slice should be small: schema, validator, census, and browser display for
`identity` and `region`. It must prove dependency grouping using an example where two current
outputs share one source family.

## 11. Acceptance cases

The system is not credible until it can express these real failure classes:

1. **Cross-region lock:** nearest grace and filed region disagree at a boundary; a design ruling
   may settle AP ownership without erasing geography evidence.
2. **Quest-gated award:** exact EMEVD/ESD prerequisites are incomplete or disjunctive; status stays
   `inferred`/`unverified`, never a guessed conjunction.
3. **Arena-existence gate:** Fortissax requires evidence about fight availability, not merely its
   award site.
4. **Shared lot or alternate acquisition:** several vanilla paths must not become several AP
   progression checks without an explicit equivalence claim.
5. **Sweep ownership:** a boss trigger grants checks across a map/region boundary; trigger, members,
   and owner evidence remain separately inspectable.
6. **Merchant row:** shop row, stock flag, NPC state, and region are distinct claims and source
   citations.
7. **Live-only behavior:** a static flag relationship appears valid but the game does not execute
   the dependent event after randomization; dated runtime evidence conflicts with the static model.
8. **Patch drift:** a 1.16 external page disagrees with 1.17 game data; the result is version drift,
   not a timeless contradiction.
9. **Dependent witnesses:** `data.py` and the check browser agree because one embeds the other; the
   status engine counts one family, not two.
10. **External silence:** a wiki does not list a check; the claim does not lose confidence unless
    the source's declared coverage makes that absence meaningful.

## 12. Definition of done for v0.6

The v0.6 audit promise is met when:

- every shipped check has ledger rows for `identity`, `region`, `access`, `detection`, and
  `suppression`, including explicit `unverified` rows where necessary;
- every enabled check has one section 6.3 logic disposition for each applicable option set;
- every `encoded` access expression is present in generated Archipelago reachability logic and
  protected by a drift test;
- no unresolved high/critical region-only check ships unless it has a valid, dated exclusion or
  waiver linked to its review issue;
- every progression-bearing check meets the critical/high shipping bars for all applicable claims;
- every active contradiction is visible in the browser and linked to an issue or ruling;
- every evidence row has a source snapshot, version scope, exact citation, and independence family;
- changed/high-risk claims are protected by the Phase-B no-regression gate;
- the audit browser covers 100% of shipped checks and can diff two builds;
- generated coverage/status totals are reproducible and included in release review;
- no wiki, testimony, foreign randomizer, or heuristic silently becomes runtime truth.

“Every check audited” therefore does not mean “every row painted green.” It means every claim has a
visible evidentiary state, the dangerous claims meet a strict bar, and the remaining uncertainty is
named, ranked, and steadily shrinking.

## 13. Non-goals

- Proving that every community source is correct.
- Treating source count as truth.
- Copying third-party databases into the repository.
- Blocking v0.6 on perfect descriptions for low-risk filler.
- Replacing exact game-data extraction with wiki prose.
- Hiding disagreements behind a single confidence score.
- Making evidence collection itself alter seed logic without a separately reviewed promotion.
