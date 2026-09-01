# Gameplay-wiki audit pilot: Radahn Festival routes

This #1273 pilot records two vanilla ways to start the Radahn Festival, then contrasts them with
Archipelago's deliberate festival override. It is an audit/report/test slice only and makes no
gameplay-rule change.

## Sources and reproducibility

The source registry adds immutable Internet Archive revisions from Game8's Elden Ring walkthrough
team and Gamer Guides author Seren Morgan-Roberts. It records publication, modification, and archive
dates, complete-response SHA-256 values, license disposition, and version scope. Retrieve a revision
with `curl --compressed -LsS -A "Mozilla/5.0" REVISION_URL` and verify its SHA-256.

No source prose is redistributed. The normalized leads use short paraphrases and stable section
anchors. The two commercial guides are independently authored and state no reuse license. Neither
states v1.17 applicability, so both leads remain `lead_only` with unknown game version.

## Vanilla-route leads

Both source families describe two alternatives rather than one combined requirement:

1. Activate a Site of Grace in Altus Plateau.
2. Advance Ranni's questline until the festival information is learned. Game8 describes the
   Blaidd/Iji and Seluvis conversations; Gamer Guides names the broader Ranni route.

The registry preserves those as separate `vanilla_access_route` leads for Radahn boss 1051360800.
It does not combine Altus and Ranni into an AND, and it does not promote Game8's finer route wording
when the second family only corroborates the broader quest route.

## Why this does not add Archipelago requirements

The vanilla routes explain why unmodified Elden Ring can leave Radahn unavailable. They do not
describe the AP runtime. `StartGrace.slot_data` unconditionally appends `_RADAHN_FESTIVAL = 9410` to
the spawn flags. That bypass exists specifically because Altus, Liurnia, or Limgrave can be sealed
when Caelid is open; requiring any vanilla festival route would recreate the softlock the override
prevents.

The reviewed v0.6 evidence ledger therefore marks both Radahn progression checks as
`region_sufficient` for every option set:

- AP 7770002: Radahn's Great Rune.
- AP 7770665: Remembrance of the Starscourge.

Their accepted access claims explicitly include runtime bypass flag 9410. The wiki leads do not
contradict that disposition because they answer a different question: how vanilla starts the
festival when no AP start flag is injected. They should not add Altus, Ranni, Blaidd, Iji, Seluvis,
or other quest requirements to AP logic.

This contrast is also a guardrail for future wiki audits: independently authored vanilla route
agreement is useful discovery evidence, but project-owned runtime overrides must be checked before
translating it into an Archipelago rule.
