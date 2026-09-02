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

The current implementation is deliberately more conservative: `legacy_key_gates.py` requires both
keys for every Lamenter's Gaol map-lot check, including the two key locations. The pilot therefore
identifies a concrete likely over-gating regression, but does not authorize changing world logic.
Before an accepted v1.17 rule replaces it, the door predicates or a versioned in-game route capture
must establish the same order. Interior checks also need to be partitioned by which door precedes
them; the two walkthrough pages do not map every AP check precisely enough to do that.

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

`walkthrough-check-leads.tsv` is the first corpus-scale pass. It is derived from Redmaw's immutable
100% base-game walkthrough capture by `tools/build_walkthrough_check_leads.py`. The capture body is
not redistributed: each row retains only its section id, step id, item label, source identity, and
the one current AP check that exact item name identifies inside the section's declared region set.

This deliberately leaves repeated consumables, stones, and runes ambiguous. It also remains
`lead_only`: one walkthrough mention can externally cross-check an identity and coarse region, but it
cannot prove access logic, a game event predicate, or the absence of another acquisition route.
`tools/check_walkthrough_check_leads.py` fails if a bound AP id disappears, its region changes, the
source becomes dangling, duplicate check coverage appears, or the broad pass unexpectedly collapses.

Reproduce from the immutable capture recorded in `sources.tsv`:

```bash
curl --compressed -LsS -A 'Mozilla/5.0' REVISION_URL -o /tmp/redmaw-walkthrough.html
python tools/build_walkthrough_check_leads.py /tmp/redmaw-walkthrough.html
python tools/check_walkthrough_check_leads.py
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

Reproduce from the immutable source commit:

```bash
git clone https://github.com/rdmaw/elden-ring-completion-sheets.git /tmp/redmaw
git -C /tmp/redmaw checkout 7281cb6f7f067e71856f12d5e7083b97ad081bb1
python tools/build_redmaw_checklist_leads.py /tmp/redmaw/sheets
python tools/check_redmaw_checklist_leads.py
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

## PowerPyx regional coverage

`powerpyx-check-leads.tsv` is a second, source-independent corpus pass over three immutable
PowerPyx regional walkthrough captures: Limgrave, Liurnia, and Raya Lucaria Academy. The builder
accepts only the registered SHA-256 bodies. It emits a binding only when an exact item name occurs
in exactly one article block and names exactly one current AP check in that page's declared region.
Each citation retains the article heading, block ordinal, and a digest of that normalized block;
the source registry retains the complete response-body digest and immutable revision URL.

This intentionally conservative pass leaves repeated consumables and repeated prose unbound. Its
rows are `lead_only` and `game_version=unknown`: PowerPyx is independent of Redmaw, but agreement
between old walkthroughs still cannot prove a v1.17 event predicate, access rule, route order, or
absence of another acquisition.

Reproduce with the three capture bodies named in `tools/build_powerpyx_check_leads.py`:

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

The builder starts from item names that identify exactly one current AP check globally. It emits a
row only when that item's wiki page has a structured `location`, `obtained`, or `found` template
field containing the current AP region literally. This intentionally declines aliases and inferred
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
