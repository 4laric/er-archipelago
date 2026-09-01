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
