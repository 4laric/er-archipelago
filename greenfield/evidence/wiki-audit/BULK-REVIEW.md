# Whole-guide review queue (#1412)

This queue retains possible matches that the corroboration importer cannot safely accept.
It does not feed the confidence calculation. One guide remains one source family even when
many steps or linked wiki pages discuss a pickup.

## Reproduce

Run python tools/build_bulk_check_review.py --check to verify the committed queue.
python tools/regen_all.py --phases tables,pages rebuilds it after confidence changes and
embeds it in er-archipelago-evidence-browser.html.

walkthrough-review-observations.json contains link labels, link targets, section names and
step identifiers extracted from the already registered Redmaw revision
7281cb6f7f067e71856f12d5e7083b97ad081bb1. It contains no walkthrough paragraphs.
To recapture, fetch that revision's sheets/walkthrough.html and
sheets/dlc-walkthrough.html into a temporary directory and pass --capture DIRECTORY.
Both original SHA-256 hashes must match the source registry.

## What the matcher can establish

Exact normalized item names select all same-name AP checks. The declared guide section
can narrow the region; an explicitly linked landmark can narrow it further. Numbered
suffixes, flags, and sweep-boss map tiles are not independent landmarks. Already corroborated
alternatives are retained rather than subtracted to manufacture a unique result.

Each observation records both the narrowed and full candidate sets, the reasons, and the
missing evidence. An unmapped section or disagreeing region retains all same-name checks
and is explicitly marked weak. Even a single remaining candidate is only a suggestion:
a linked item can be an incidental mention instead of a collection instruction. The matcher
does not infer quantity, coordinates, event predicates, quest requirements, or item ownership.

The current queue has 1,978 observations touching 2,071 held checks. Of those checks, 244
already have one external family and could benefit from an independently reviewed Redmaw
match. These are overlapping candidates, not 2,071 validated pickups. Source-area mappings
combine both existing Redmaw importers, keeping the union when they disagree; mismatches
remain visible for review. Resolving section aliases such as Ainsel narrows the initial
candidate population without counting any new confirmation.

## First reviewed batch

The initial pass had 2,004 observations and 2,210 held candidates. Reading the pinned
acquisition passages resolved eight boss rewards that already had Eldenpedia evidence:
two Tibia Mariners, Smarag, Ekzykes, Greyll, the Mt. Gelmir Magma Wyrm, the Altus Fallingstar
Beast, and the Gravesite Ghostflame Dragon. Their explicit item/boss/area statements are
recorded separately in walkthrough-reviewed-landmark-check-leads.tsv, with immutable
line citations and step ids. The existing confidence builder therefore rises from
1,143 to 1,151 trusted identity/region checks out of 4,925. No access claim is promoted.

The remaining five single-landmark observations are deliberately still candidates. In particular,
the Jagged Peak Drake passage describes one of multiple drakes; a superficially unique
catalog label is not enough to resolve boss ownership.

## Player review workflow

The review page defaults to items and places, with search, area and collection filters.
Choose a location, inspect any guide candidates, then report what was actually observed.
Catalog labels and observed item/place fields remain separate. Players can save a JSON file,
copy a text report, or prepare a GitHub issue; the page never submits it.

The JSON format er-player-review-v1 carries the check id, catalog fingerprint, observed
item/place, route, evidence, environment and versions. It is a report for maintainers to
adjudicate, not an accepted evidence import. Drafts stay in memory while switching locations
and are lost on reload; save/copy before leaving. A randomized item or sweep completion does
not establish the pickup's original identity or route.

Maintainer mode retains the claim/family/disposition views and old claim permalinks. Lists
render at most 200 claims at once and explain how to refine the filters.
