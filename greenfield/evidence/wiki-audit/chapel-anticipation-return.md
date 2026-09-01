# Chapel of Anticipation return-route audit

This #1273 follow-up to #1023 records two independently authored external leads for the repeatable
route back to the Chapel of Anticipation. It changes no world logic or access disposition. Neither
source establishes Elden Ring v1.17 behavior, so the normalized claim remains `lead_only` with
`game_version=unknown`.

## Sources and reproducibility

`sources.tsv` pins immutable Internet Archive captures of Game8's Four Belfries guide and
Eldenpedia's Four Belfries page. Retrieve a `revision_url` with
`curl --compressed -LsS -A "Mozilla/5.0" REVISION_URL` and compare the complete response body with
the recorded SHA-256. The captures are independently authored: Game8 credits its walkthrough team,
while Eldenpedia is a community wiki whose captured HTML identifies revision 65939.

Game8's captured page was last modified in May 2022. Eldenpedia exposes no reliable publication or
modification timestamp in the capture. Neither page names a game patch, so agreement cannot prove
current runtime behavior.

## Route lead

Both sources place the Four Belfries in Liurnia and describe their sending gates as requiring an
Imbued Sword Key. Both identify the Chapel destination; Eldenpedia records its in-world hint as
"Precipice of Anticipation" and names the return-area rewards. The normalized lead therefore groups
the four current AP checks reached by that repeatable route:

- Ornamental Straight Sword and Golden Beast Crest Shield from the Grafted Scion;
- The Stormhawk King and Stormhawk Deenh from the chapel return area.

The lead records Liurnia, an Imbued Sword Key, and the Chapel sending gate as an `all` route. It does
not cover the one-shot prologue attempt, infer that no exploit exists, or promote guide prose into a
game event predicate.

## Comparison boundary

The current project surface is internally split: the Scion pair is filed under Liurnia, while the
two stormhawk checks are filed under Stormveil. The current region-only model also does not encode
an Imbued Sword Key requirement for the Scion pair. This comparison makes the external lead useful
for triage, but it is not evidence that either current rule is wrong. A versioned EMEVD predicate or
controlled v1.17 observation must adjudicate the sending-gate requirement and exact reward
partition before logic changes.
