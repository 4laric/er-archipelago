# Chapel of Anticipation return-route audit

This #1273 follow-up to #1023 records two independently authored external leads for the repeatable
route back to the Chapel of Anticipation. Issue #1303 then adjudicated that lead against committed
v1.17 EMEVD: m60_34_47 event 1034472611 requires Goods 8186, persists the sending-gate unlock, and
common event 90005605 sends the player to m10_01. The external normalized claim remains `lead_only`
with `game_version=unknown`; it corroborates rather than substitutes for that game-data evidence.

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

## Adjudication

All four checks are now adjudicated as Liurnia access: the Scion pair already used that bucket, and
#1303 moves The Stormhawk King and Stormhawk Deenh there as well. The latter two remain physically
authored in m10_01, whose coarse grace join says Stormveil; the ground-region audit therefore keeps
an exact two-flag access-route ruling rather than teaching the physical map that it moved. The
Imbued Sword Key is progression when Liurnia is in play and gates these four checks under legacy
key logic. This ruling covers the repeatable vanilla sending gate, not the one-shot prologue or
out-of-bounds routes.
