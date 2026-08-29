# v0.5.3 — release blurb (draft)

_Draft. Written as the window fills, not at tag time — the moment a change lands is the
only moment anyone remembers why it mattered._

## What you need to update

- **Client:** Required — use the v0.5.3 client with v0.5.3 seeds.
- **APWorld:** Host-only — the room host or generator must install v0.5.3; joining players only
  need the matching client.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — keep an active v0.5.2 seed on its matched v0.5.2 pair.
  There is no save migration; just do not mix client and APWorld versions.
- **Profile/assets:** No action.

## What is in it so far

**The questline-DAG rebuild no longer trips over its existing table on Windows.** The #1085
extractor completed all of its semantic checks, then one local full regen failed while reopening
`questline_dag.tsv` for output. The generator now writes a complete sibling temporary file and
atomically replaces the old table, so it neither opens that destination directly nor leaves a
half-written corpus when replacement fails (#1110).

This window opened at the v0.5.2 tag. `CONTRACT_HASH` stays at `13db0b3a` —
`abilityUnlockItems` remains the newest slot-data shape — while the exact-version handshake moves
to 0.5.3. Client half: clients#469.

## For whoever writes the real one

Keep this about the player-visible work that fills the window. The atomic writer is release
infrastructure: important because it keeps the shipped corpus reproducible, but not the eventual
headline unless the window remains a narrow maintenance release.
