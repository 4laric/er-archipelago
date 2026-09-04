# Gameplay-wiki audit pilot: Lamenter's Gaol

This is the bounded pilot for #1273 and the Lamenter's Gaol regression named in #1271. It records
normalized leads, not accepted v1.17 access evidence. Neither source states an Elden Ring patch
version, so agreement between them cannot upgrade a claim beyond `lead_only`.

## Reproduction and provenance

The two `revision_url` values in `sources.tsv` are immutable Internet Archive captures. Retrieve a
capture with `curl --compressed -LsS -A "Mozilla/5.0" REVISION_URL` and compare its SHA-256 with
`body_sha256`. The digest covers the complete response body; no source text is redistributed here.
Only short paraphrases and section anchors are committed. Page dates and authors come from the
captures' own HTML metadata. Both pages are commercial guides with no content-reuse license stated,
so their text is treated as all-rights-reserved.

The sources are independently authored: Game8 credits its Elden Ring walkthrough team, while Gamer
Guides credits Shane Williams. Their agreement is useful discovery evidence, but it is not current
game-version proof. They also do not become independent of each other merely because one route is
restated in several sections of the same page.

## Findings

Both sources describe the same progression order:

1. The Upper Level Key is in the entrance-side area before the first locked gate.
2. That key opens the route to the area containing the Lower Level Key.
3. The Lower Level Key opens the later gate on the route to Lamenter.

That yields three normalized leads in `leads.tsv`: region-only access for the Upper key check, the
Upper key for the Lower key check, and both keys for the boss. There is no source-to-source
contradiction in this pilot.

The v1.17 game-data bundle supplies the missing door predicate family. Map event `m41_02` initializes
ObjActParam `449008` for the first door and `1449008` for the two later doors; those rows require
goods `2008005` (Gaol Upper Level Key) and `2008006` (Gaol Lower Level Key), respectively. The map
lots bind those named goods to f41027000 and f41027320. Combined with the independently authored
route-order leads, this adjudicates the three exact checks: Upper Key is region-reachable, Lower Key
requires Upper, and Lamenter requires both. `legacy_key_gates.py` and its regression encode those
tiers.

The remaining interior checks are intentionally not promoted. The game data proves which goods the
doors consume, but the bundle has no MSB coordinates to bind each pickup to a side of each door, and
the two walkthrough pages do not map every AP flag precisely enough. They retain the conservative
both-key fallback and remain in the investigation queue.

The Archipelago Lamenter sweep path is a separate alternate-acquisition claim and is not adjudicated
by these vanilla walkthroughs.

## Investigation queue

`queue-targets.tsv` is the small curated boundary between normalized leads and the next research
batch. `tools/build_wiki_audit_queue.py` combines it with `leads.tsv` and the current access
disposition ledger to produce `queue.json`. The generated report separates exact AP-check bindings,
unbound route/boss/item leads, uncovered high-risk regression classes, and explicit gaps.

The queue never promotes an external claim: every emitted lead remains `lead_only`. It also never
manufactures a contradiction from missing text. A contradiction appears only after a curator records
an explicit disagreement; alternate routes and incomplete coverage remain routes and gaps.
Explicit disagreements belong in `contradictions.tsv`; its validator requires at least two known
leads with different normalized values, so an empty file honestly means “none recorded.”

## Broad walkthrough coverage

### Upgrade materials, flask upgrades, and blessing collectibles

`upgrade-blessing-review.tsv` inventories the full upgrade/blessing family rather than selecting
easy individual rows. It separates repeated Smithing Stone and Glovewort rows from uniquely
landmark-anchored Golden Seed, Sacred Tear, Scadutree Fragment, and Revered Spirit Ash checks. Each
row retains its exact event flag and map anchor, external-family count, and separate access
disposition. Identity and region evidence never implies that a route is logically accessible.

`upgrade-blessing-review-summary.json` reports audited, trusted, held, conflicted, and untouched
counts per category. Repeated material rows require an exact flag/map-lot or uniquely identifying
landmark; broad guide order is not enough to bind a repeated item to an AP slot.

```bash
python tools/build_upgrade_blessing_review_batch.py
python tools/build_upgrade_blessing_review_batch.py --check
```

`walkthrough-check-leads.tsv` is the first corpus-scale pass. It is derived from Redmaw's immutable
base-game and DLC walkthroughs at commit `7281cb6f7f067e71856f12d5e7083b97ad081bb1` by
`tools/build_walkthrough_check_leads.py`. The source bodies are not redistributed: each row retains
only its section id, step id, item label, source identity, and the one current AP check that exact
item name identifies inside the section's declared region set. When an exact name repeats within a
section, the builder may accept it only if one candidate's complete stored `near`/`around` place
suffix occurs verbatim in the same checklist step. The pinned pair plus that whole-place rule expand
the pass from 813 to 1,220 exact check bindings without dropping any earlier binding; 1,386 ambiguous
and 2,461 unmatched links remain refused.

This deliberately leaves repeated consumables, stones, and runes ambiguous. It also remains
`lead_only`: one walkthrough mention can externally cross-check an identity and coarse region, but it
cannot prove access logic, a game event predicate, or the absence of another acquisition route.
`tools/check_walkthrough_check_leads.py` fails if a bound AP id disappears, its region changes, the
source becomes dangling, duplicate check coverage appears, or the broad pass unexpectedly collapses.

Reproduce from the immutable source commit recorded in `sources.tsv`:

```bash
git clone https://github.com/rdmaw/elden-ring-completion-sheets.git /tmp/redmaw
git -C /tmp/redmaw checkout 7281cb6f7f067e71856f12d5e7083b97ad081bb1
python tools/build_walkthrough_check_leads.py /tmp/redmaw/sheets
python tools/check_walkthrough_check_leads.py
python tools/build_evidence_browser.py
```

`redmaw-location-anchor-check-leads.tsv` is a narrower repeated-item pass over the pinned current
base and DLC walkthroughs. It considers only steps that link both a repeated item and a named
MapGenie location, then requires that exact location phrase to select one current AP candidate in
the declared section region and that the candidate's flag have a matching v1.17 map-lot detection
claim. This resolves 27 checks, including repeated smithing stones, Sacred Tears, and Scadutree
Fragments; six other repeated links with named locations are refused.

Only factual link labels and immutable section/step anchors are retained. Redmaw's prose is not
redistributed, this pass shares the same `gameplay-guide:redmaw` family as the other Redmaw inputs,
and every row remains `lead_only`. Same-step placement does not establish access or route order.

```bash
git -C /tmp/redmaw checkout 7281cb6f7f067e71856f12d5e7083b97ad081bb1
python tools/build_redmaw_location_anchor_leads.py /tmp/redmaw/sheets
python tools/check_redmaw_location_anchor_leads.py
python tools/build_evidence_browser.py
```

`redmaw-embedded-ash-check-leads.tsv` resolves a separate naming gap: six weapon pickups whose AP
labels append the weapon's innate `with Ash of War: ...` text, while Redmaw links the canonical base
weapon name. The builder accepts only an exact base-name prefix in the same pinned walkthrough
region, a unique current AP candidate, and the same v1.17 map-lot flag in the evidence ledger.
Backhand Blade, Great Katana, Nagakiba, Dryleaf Arts, Dueling Shield, and Igon's Greatbow meet that
bar. Two Beast Claw links are refused because their walkthrough region does not select the current
AP candidate. These are still `lead_only` identity/region cross-checks, not access evidence.

```bash
git -C /tmp/redmaw checkout 7281cb6f7f067e71856f12d5e7083b97ad081bb1
python tools/build_redmaw_embedded_ash_leads.py /tmp/redmaw/sheets
python tools/check_redmaw_embedded_ash_leads.py
python tools/build_evidence_browser.py
```

## Redmaw completion-checklist coverage

`redmaw-checklist-check-leads.tsv` binds factual item labels from eleven completion sheets at
Redmaw commit `7281cb6f7f067e71856f12d5e7083b97ad081bb1`. The builder accepts only the pinned
SHA-256 for each sheet, retains the sheet section, checkbox id, and linked wiki.gg target, and emits
a row only when the normalized label identifies exactly one current AP check globally. Its generated
coverage report records 3,249 labels: 1,857 exact label bindings covering 1,499 distinct checks,
432 ambiguous labels, and 960 unmatched labels. Of the distinct bindings, 899 were not present in
the earlier Redmaw walkthrough pass.

The upstream repository states no reuse licence. No HTML or guide prose is redistributed. These
rows retain only factual item names and audit anchors, remain `lead_only`, and claim neither region
nor access logic. The completion sheets and walkthrough also share `gameplay-guide:redmaw`; agreement
between them is not independent corroboration.

The follow-up `redmaw-merchant-check-leads.tsv` revisits the 292 repeated labels in the merchant
sheet. It accepts a binding only when the pinned merchant section plus the current AP shop
description or physical-merchant datamine select exactly one candidate. This resolves 157 checks
and refuses the remaining 135, including every duplicated shared-shop binding. The associated 491
wiki.gg item targets from the complete merchant sheet are pinned to revision ids in
`redmaw-merchant-wikigg-revisions.tsv`, so every accepted row has both an immutable checklist anchor
and an immutable item-page citation. These remain identity-only leads: the merchant context does not
independently prove AP's region assignment, stock conditions, or access logic.

Reproduce from the immutable source commit:

```bash
git clone https://github.com/rdmaw/elden-ring-completion-sheets.git /tmp/redmaw
git -C /tmp/redmaw checkout 7281cb6f7f067e71856f12d5e7083b97ad081bb1
python tools/build_redmaw_checklist_leads.py /tmp/redmaw/sheets
python tools/check_redmaw_checklist_leads.py
python tools/build_redmaw_wikigg_revisions.py /tmp/redmaw/sheets  # explicit network refresh
python tools/build_redmaw_merchant_leads.py /tmp/redmaw/sheets
python tools/check_redmaw_merchant_leads.py
python tools/build_evidence_browser.py
```

## Eldenpedia repeated map-pickup coverage

The item-acquisition lane also includes a focused pass over the 620 checks that had only the
Redmaw family in the progression-host confidence report. The refresh requested 598 distinct item
pages (including the prior pinned acquisition set), and accepted 41 additional checks only where
an exact multiword acquisition anchor selected one current AP map-lot flag. This raises trusted
identity-and-region host coverage from 1,046 to 1,087 while leaving 579 members of that Redmaw-only
queue unpromoted.

The refusal boundary remains deliberate: 1,140 candidate comparisons had no matching acquisition
anchor, 654 candidates belonged to pages without an Acquisition section, 499 comparisons were
reserved for the separate upgrade-material lane, 140 had a weak anchor or lacked exact map-lot
detection, 13 repeated the same anchor ambiguously, and 25 requested titles had no wiki page.
Repeated pickups are not selected merely because their item page names the right broad region.

Reproduce the focused network capture and deterministic outputs with:

```bash
python tools/fetch_eldenpedia_redmaw_only_capture.py /tmp/eldenpedia-redmaw-only.json
python tools/build_eldenpedia_item_acquisition_leads.py /tmp/eldenpedia-redmaw-only.json
python tools/check_eldenpedia_item_acquisition_leads.py
python tools/build_progression_host_confidence.py
python tools/build_evidence_browser.py
```

`eldenpedia-repeated-pickup-check-leads.tsv` resolves a conservative subset of the repeated item
names that the first location-page pass deliberately refused. It reuses the same 341 immutable
page revisions pinned by `eldenpedia-location-pages.tsv`; the companion coverage report records the
full ambiguity/refusal boundary.

A repeated Notable Loot link binds only when the normalized location-page title occurs as a whole
phrase in exactly one same-region AP description and that check's current v1.17 detection claim
uses `ItemLotParam_map.getItemFlagId` with the same flag as `data.py`. This joins an external page
and item identity to committed game-param evidence without guessing between repeated stones,
runes, keys, grease, or other consumables. Page-title silence and multiple title matches remain
refusals.

Every result remains `lead_only` at `game_version=unknown`; the pinned wiki revision does not prove
access, route order, coordinates, completeness, event timing, or alternate-acquisition absence.
Nothing here is consumed by world logic or the access disposition ledger.

Reproduce from the same-run API capture used by the broad Eldenpedia pass:

```bash
python tools/build_eldenpedia_location_leads.py --write-capture /tmp/eldenpedia-locations.json
python tools/build_eldenpedia_repeated_pickup_leads.py /tmp/eldenpedia-locations.json
python tools/check_eldenpedia_repeated_pickup_leads.py
python tools/build_evidence_browser.py
```

## Game8 legacy-dungeon corpus

`game8-check-leads.tsv` independently cross-checks the Redmaw pass against five immutable Game8
legacy-dungeon captures: Raya Lucaria, Redmane Castle, Leyndell, Farum Azula, and the Haligtree.
The builder verifies each complete response-body SHA-256 before parsing it. It searches only
walkthrough/loot sections and binds only an exact item name that identifies one current AP check in
the page's declared AP region. Repeated stones and other ambiguous names are refused.

All five pages share `gameplay-guide:game8`; pages from one publisher are not five independent
witnesses. Every result remains `lead_only` at `game_version=unknown`, and no route prose becomes
access logic. Reproduce by downloading the five `revision_url` captures in `sources.tsv` as
`<archive-id>.html`, then run:

```
python tools/build_game8_check_leads.py /path/to/game8-captures
python tools/check_game8_check_leads.py
python tools/build_evidence_browser.py
```

## Eldenpedia location-page coverage

`eldenpedia-location-pages.tsv` inventories the `Category:Locations` corpus without redistributing
wiki prose. Each row pins the MediaWiki page id, revision id, revision timestamp and revision SHA-1,
plus the page's infobox-region link and count of links in `Notable Loot`. The `oldid` URL is an
immutable, human-reviewable capture of the cited revision.

`tools/build_eldenpedia_location_leads.py` binds a loot link only when its exact normalized item
name identifies one current AP check inside an explicit wiki-region-to-AP-region mapping. A check
mentioned on more than one location page is refused wholesale; unmatched names and repeated items
remain gaps. The checked-in `eldenpedia-location-check-leads.tsv` contains no prose and every row
points to the exact page id, revision id, section and loot-link target.

This track is deliberately external and `lead_only`. It cross-checks check identity and coarse
region; it does not establish route order, access requirements, v1.17 predicates, completeness, or
absence. Nothing in this corpus is consumed by world logic or the access disposition ledger.

To refresh from the public MediaWiki API while retaining a same-run local capture for audit:

```bash
python tools/build_eldenpedia_location_leads.py --write-capture /tmp/eldenpedia-locations.json
python tools/check_eldenpedia_location_leads.py
python tools/build_evidence_browser.py
```

## Eldenpedia upgrade-material acquisition coverage

`eldenpedia-upgrade-material-check-leads.tsv` is the reserved repeated-upgrade-material pass over
the pinned Eldenpedia item-page corpus. It normalizes bracketed AP tiers such as `Smithing Stone
[7]` to the wiki's `Smithing Stone 7`, then accepts a row only when an exact multiword acquisition
anchor selects one current AP check and its flag is independently present as an
`ItemLotParam_map.getItemFlagId` detection claim. Fourteen checks add new union coverage; 15 safe
matches already covered by an earlier corpus are counted but not duplicated. The report also keeps
the full refusal boundary: 721 candidate checks, 591 absent anchors, 84 weak-anchor or non-map-lot
refusals, and 17 ambiguous anchors.

The seven item pages used by accepted rows are pinned by MediaWiki page id, revision id, timestamp,
and SHA-1 in `eldenpedia-upgrade-material-pages.tsv`. All output remains `lead_only`; an acquisition
mention does not establish access, route order, coordinates, completeness, event timing, or the
absence of another source.

Reproduce from the same pinned-title capture used for the broader acquisition pass:

```bash
python tools/build_eldenpedia_upgrade_material_leads.py /path/to/eldenpedia-items.json
python tools/check_eldenpedia_upgrade_material_leads.py
python tools/build_evidence_browser.py
```

### Row-level linked-place refinement

`eldenpedia-upgrade-location-row-check-leads.tsv` narrows the same upgrade family further: it
requires a single pinned Acquisition bullet to link one named place, that place to select exactly
one current AP check, and the check's flag to agree with the current map-lot detection claim. This
adds three union checks. Of 170 inspected source rows, 148 did not select one check, one failed the
map-lot gate, four candidate matches were refused because multiple source rows selected the same
check, and 14 safe bindings were already covered elsewhere.

The item revisions are reused from the pinned acquisition manifests and every linked place must
also occur in `eldenpedia-location-pages.tsv`. Output remains `lead_only`: a linked acquisition row
does not prove access, route order, coordinates, completeness, event timing, or alternate-source
absence.

```bash
python tools/build_eldenpedia_upgrade_location_rows.py /path/to/eldenpedia-items.json
python tools/check_eldenpedia_upgrade_location_rows.py
python tools/build_evidence_browser.py
```

## Eldenpedia repeated-item acquisition coverage

`eldenpedia-deathroot-check-leads.tsv` covers all nine Deathroot acquisitions from Eldenpedia page
10213, revision 38369. A repeated item name cannot identify any one check, so the builder requires a
unique revision-local set of linked anchors: a named boss, dungeon, or nearby site. Each acquisition
row binds exactly one current Deathroot AP id, and the validator refuses missing, duplicated, or
changed anchors.

The CC BY-SA 4.0 revision is pinned by page id, revision id, timestamp, and MediaWiki SHA-1 in
`eldenpedia-deathroot-pages.tsv`; no wiki prose is retained. The leads intentionally record both
the source's coarse area and the current AP region without declaring them equivalent. In particular,
the Wyndham Catacombs row records Eldenpedia's Altus Plateau wording beside the current Mt. Gelmir
bucket, making that boundary difference visible for later adjudication. All nine rows remain
`lead_only` and do not establish v1.17 behavior or access logic.

Reproduce from the immutable MediaWiki revision:

```bash
python tools/build_eldenpedia_deathroot_leads.py
python tools/check_eldenpedia_deathroot_leads.py
python tools/build_evidence_browser.py
```

`eldenpedia-shabriri-grape-check-leads.tsv` applies the same immutable-revision discipline to all
three Shabriri Grapes. Unique linked anchors distinguish the room past Godrick's throne, Purified
Ruins, and Revenger's Shack rows; each selected AP flag is also required to remain a Shabriri Grape
in the committed ItemLot corpus. This records Eldenpedia's Limgrave wording for the post-Godrick
room beside AP's Stormveil bucket and preserves the Edgar row's Weeping quest dependency without
promoting either observation into region or access logic.

```bash
python tools/build_eldenpedia_shabriri_grape_leads.py
python tools/check_eldenpedia_shabriri_grape_leads.py
python tools/build_evidence_browser.py
```

`eldenpedia-crystal-tear-check-leads.tsv` binds all 18 current Crystal Tear checks through 15
immutable item-page revisions. Unique item names resolve 12 checks directly; source-local area or
site links separate the two Cerulean, two Crimson, and two Ruptured Crystal Tears. Every AP flag is
also checked against the committed ItemLot item id. These rows remain `lead_only` and establish no
access rule, route, coordinates, or event predicate.

```bash
python tools/build_eldenpedia_crystal_tear_leads.py
python tools/check_eldenpedia_crystal_tear_leads.py
python tools/build_evidence_browser.py
```

`eldenpedia-golden-seed-check-leads.tsv` adds 28 exact bindings from Golden Seed page 8969,
revision 99538. This raises the union coverage from 10 to 38 of 43 AP checks. Unique acquisition-row
anchors and committed ItemLot ids guard every join. Five checks remain explicitly refused: four
AP slots cannot be selected from the page's single `2x` row, and the Roderika/Lake-Facing Cliffs
check is not distinguished by the source. All rows remain `lead_only`.

```bash
python tools/build_eldenpedia_golden_seed_leads.py
python tools/check_eldenpedia_golden_seed_leads.py
python tools/build_evidence_browser.py
```

`eldenpedia-whetblade-check-leads.tsv` binds the complete seven-check whetblade family through six
immutable item-page revisions. The two Whetstone Knife rows are separated by Gatefront Ruins and
Twin Maiden Husks anchors; committed ItemLot ids guard all seven bindings. This adds the one
previously uncovered check and raises union coverage from 6/7 to 7/7, with no refusals.

```bash
python tools/build_eldenpedia_whetblade_leads.py
python tools/check_eldenpedia_whetblade_leads.py
python tools/build_evidence_browser.py
```

`eldenpedia-memory-stone-check-leads.tsv` closes the two-check gap in the nine-check Memory Stone
family. A pinned Eldenpedia revision names Testu's Rise and Seluvis's Rise, and committed ItemLot
id 10030 guards both joins. Union coverage rises from 7/9 to 9/9 with no refusals; the rows remain
`lead_only` and do not establish tower-puzzle or route logic.

```bash
python tools/build_eldenpedia_memory_stone_leads.py
python tools/check_eldenpedia_memory_stone_leads.py
python tools/build_evidence_browser.py
```

`eldenpedia-sacred-tear-check-leads.tsv` binds 12 church-named Sacred Tear acquisitions from
Eldenpedia page 13254, revision 99877. Every church link is unique in that revision, and every
selected AP flag must remain a Sacred Tear in the committed ItemLot corpus. The AP-only
Ruin-Strewn Precipice row is deliberately left unbound because the pinned source does not list it;
the corpus remains `lead_only` and establishes neither completeness nor access logic.

```bash
python tools/build_eldenpedia_sacred_tear_leads.py
python tools/check_eldenpedia_sacred_tear_leads.py
python tools/build_evidence_browser.py
```

`eldenpedia-seedbed-curse-check-leads.tsv` records all six acquisition rows from page 3879,
revision 100628. Only Big Boggart and Volcano Manor bind to checks: each has a unique current AP
region/flag within this item family, and Big Boggart's `f400308` identity is independently tied to
NPC death flag 4143 by the committed questline-condition and FromSoftware flag-name corpora. The
two Leyndell and two Haligtree rows are retained as four explicit unbound leads because committed
lots do not distinguish same-region duplicates. Capital Outskirts and AP's Altus bucket remain
visible side by side rather than being silently normalized.

```bash
python tools/build_eldenpedia_seedbed_curse_leads.py
python tools/check_eldenpedia_seedbed_curse_leads.py
python tools/build_evidence_browser.py
```

## PowerPyx regional coverage

`powerpyx-check-leads.tsv` is a second, source-independent corpus pass over fifteen immutable
PowerPyx regional walkthrough captures. It covers Ainsel River, Caelid, Caria Manor, Deeproot
Depths, Haligtree, Leyndell, Limgrave, Liurnia, Mohgwyn Palace, Mountaintops of the Giants, Raya
Lucaria Academy, Siofra River, Stormveil Castle, Volcano Manor, and Weeping Peninsula. The builder
accepts only the registered SHA-256 bodies. It emits a binding only when an exact item name occurs
in exactly one article block and names exactly one current AP check in that page's declared region.
Each citation retains the article heading, block ordinal, and a digest of that normalized block;
the source registry retains the complete response-body digest and immutable revision URL.

This intentionally conservative pass leaves repeated consumables and repeated prose unbound. Its
rows are `lead_only` and `game_version=unknown`: PowerPyx is independent of Redmaw, but agreement
between old walkthroughs still cannot prove a v1.17 event predicate, access rule, route order, or
absence of another acquisition.

Reproduce with the capture bodies named in `tools/build_powerpyx_check_leads.py`:

```bash
python tools/build_powerpyx_check_leads.py /path/to/powerpyx-captures
python tools/check_powerpyx_check_leads.py
python tools/build_evidence_browser.py
```

## Fextralife item-page coverage

`fextralife-item-check-leads.tsv` is a broad, source-independent pass over Fextralife's structured
item pages. The checked-in `fextralife-item-pages.tsv` pins the exact MediaWiki page and revision
IDs, timestamp, revision SHA-1, and immutable `oldid` URL used by each binding. No wiki prose is
redistributed.

The builder starts from item names that identify exactly one current AP check globally. It emits an
identity row only when the wiki revision's structured `name` field exactly matches that AP item. It
adds coarse region to the claim only when a structured `location`, `obtained`, or `found` field also
contains the current AP region literally. This intentionally declines aliases and inferred
geography rather than maintaining a second region ontology. It also declines repeated AP items.

Every row remains `lead_only` at `game_version=unknown`. A Fextralife page can cross-check identity
and coarse region, but cannot prove v1.17 access logic, event predicates, route order, coordinates,
completeness, or alternate-acquisition absence. All pages share one
`gameplay-wiki:fextralife` family.

The API client batches forty titles per request, waits between uncached requests, identifies itself,
and can retain each complete JSON response in a cache directory. A same-run aggregate capture makes
reproduction independent of later edits during review:

```bash
python tools/build_fextralife_item_leads.py \
  --cache-dir /tmp/fextralife-api --write-capture /tmp/fextralife-batches.json
python tools/build_fextralife_item_leads.py --capture /tmp/fextralife-batches.json
python tools/check_fextralife_item_leads.py
python tools/build_evidence_browser.py
```
