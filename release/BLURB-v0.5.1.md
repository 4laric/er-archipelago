# v0.5.1 — release blurb (draft)

_Draft. Written as the window fills, not at tag time — the moment a change lands is the
only moment anyone remembers why it mattered._

## What you need to update

- **Client:** Required — use the v0.5.1 client with v0.5.1 seeds.
- **APWorld:** Host-only — the room host or generator must install v0.5.1; joining players only
  need the matching client.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — keep an active v0.5.0 seed on its matched v0.5.0 pair.
  There is no save migration; just do not mix client and APWorld versions.
- **Profile/assets:** No action — no profile or packaged asset changed when the window opened.

## What is in it so far

Enia sells what Enia sells. Finger Reader Enia's shop is vanilla again — her hundred stock rows
are no longer checks, nothing from across the multiworld can turn up on her shelves, and the
"empty Enia" report is impossible by construction rather than by luck. The Roundtable's quietest
merchant goes back to being a shop, not a slot machine.

One housekeeping note: removing her rows shifts every later AP location id down by exactly 100.
Seeds are self-consistent, so nothing in play changes — but if you keep an external tracker or
notes that reference 0.5.0 location ids, regenerate them from a 0.5.1 seed.

## What carried over from v0.5.0

Nothing — v0.5.0 shipped everything it documented (the ability lock and its progressive unlocks,
co-op difficulty, `shop_checks`, `armor_bundles`, the Leyndell capital-gate and as-sent Great Rune
fixes, the wider corpse-award sweep, `!check`).

`stable` moved to v0.5.0 in the same change that opened this window — the promotion v0.5.0 held
back while it was still an integration branch. Players on the stable channel get the ability lock
now, not at the next tag.

## For whoever writes the real one

The v0.5.0 blurb is the model to beat: it opens on what a player does ("You can take an ability
away now"), not on the option name, and only reaches the key names after the feeling. The v0.4.3
blurb is the same shape. Say what someone will feel at the table before what was built.
