# Carian Study Hall route audit

This #1273 slice records two independently authored walkthrough leads for the route split used by
the Carian Inverted Statue logic. It does not change logic or the v0.6 access-disposition ledger.
Neither source states an Elden Ring patch version, so both normalized claims remain `lead_only` with
`game_version=unknown`.

## Sources and reproducibility

`sources.tsv` pins immutable Internet Archive captures for the Eldenpedia Study Hall page and
Redmaw's completion walkthrough. Retrieve either `revision_url` with
`curl --compressed -LsS -A "Mozilla/5.0" REVISION_URL` and compare the complete response body with
the recorded SHA-256. The Eldenpedia provenance also records captured revision 71979 and its
MediaWiki SHA-1. Redmaw's page exposes no publication or modification timestamp, so those fields say
`unknown` rather than turning the repository or archive dates into article dates.

The publishers and authorship families are independent: one is a community wiki and the other is a
completion walkthrough maintained by GitHub user `rdmaw`. Their agreement is useful corroboration,
but cannot establish v1.17 behavior without versioned game data or a live observation.

## Route partition

Both sources distinguish the two layouts:

- The standard layout contains the two Golden Runes, Cerulean Seed Talisman, Carian Glintstone
  Staff, and the first Miriam reward, Magic Downpour. It does not require the statue.
- Placing the Carian Inverted Statue exposes the inverted route. Its named rewards are Mask of
  Confidence, Holyproof Dried Liver, Glintstone Fireflies, Lucidity, the bridge Godskin Noble set,
  and the Divine Tower's Cursemark of Death and Stargazer Heirloom.

The normalized leads map those names to the current AP check IDs. The standard and inverted sets are
explicitly disjoint. Nine inverted acquisition flags map to ten AP checks because Cursemark of Death
and Stargazer Heirloom share flag 34117500.

## Comparison boundary

The ten-check inverted set matches the existing `_LEGACY_EXTRA["Carian Inverted Statue"]` table and
its standard-layout exclusion regression. That is a comparison, not circular evidence: the wiki
families remain leads, while an `encoded` disposition must cite the project rule and test that
actually implement it. This audit must not promote either guide into a proven access predicate or
silently extend the statue requirement into option modes where the rule is inactive.
