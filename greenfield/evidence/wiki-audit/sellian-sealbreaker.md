# Gameplay-wiki audit pilot: Sellian Sealbreaker

This bounded #1273/#1280 pilot records vanilla acquisition and use leads for the Sellian
Sealbreaker. The item is absent from the generated Archipelago location and item tables, so the
pilot compares external route prose with committed ESD and param evidence. It does not add the item
or change gameplay logic.

## Sources and reproducibility

The Game8 Sellen revision already registered by the ending pilot is paired with an independently
authored GameSpot guide by James Carr. `sources.tsv` records immutable Internet Archive revisions,
authors, publication and modification dates, archive times, response-body SHA-256 values, license
disposition, and version scope. Retrieve each revision with
`curl --compressed -LsS -A "Mozilla/5.0" REVISION_URL` and verify its SHA-256.

No source prose is redistributed. `leads.tsv` contains short paraphrases and stable section or
JSON-LD anchors. Both pages are commercial guides without a stated reuse license. Neither states
v1.17 applicability, and both were last edited before that version, so all statements remain
`lead_only` with unknown game version. GameSpot consistently says "Sellian Spellbreaker" rather
than the in-game "Sellian Sealbreaker"; the audit records that discrepancy rather than silently
correcting its testimony.

## Normalized leads

The two independent guide families agree on this sequence:

1. Obtain Comet Azur from Primeval Sorcerer Azur on Mt. Gelmir, return to Sellen, show her the
   sorcery, and accept her request. Sellen then gives the key item.
2. Carry the key to Sellia Hideaway in Caelid and use it on the barrier leading to Lusat and Stars
   of Ruin.

Acquisition and use are separate claims. The first does not imply that possessing the item opens the
barrier without Caelid/Sellia access; the second does not prove the preceding Sellen dialogue branch.

## Comparison with committed evidence

Committed `esd_gifts.tsv` records Sellen talk 316006000, dialogue step 1044369218, awarding lot
101020. `flag_lots.tsv` identifies that lot as goods 8169 with acquisition flag f400102. This proves
the item identity and that one Sellen dialogue step grants its lot, but the extracted condition cone
for f400102 is unresolved and does not prove which immediate predicates select that step.

`region_map.csv` retains the candidate as AP 7000879 with `PENDING` global placement, while generated
`eldenring/data.py` contains no Sellian Sealbreaker check. The guide agreement makes the missing item
and route worth resolving, but does not justify promoting AP 7000879: the pages are unversioned, the
ESD award branch is not acceptance-pinned, and no committed evidence establishes how replacing or
withholding goods 8169 affects the Sellia barrier in v1.17.

The next proof step is a bounded ESD audit of t316006000_x55 and the barrier interaction, with exact
branch predicates and version provenance. Until then, adding the key as progression could create an
ungrantable item or a false gate.
