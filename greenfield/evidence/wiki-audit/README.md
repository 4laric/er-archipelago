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
