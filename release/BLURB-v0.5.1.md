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

You can ask for a Basilisk by writing `Basilisk`. The Spawn Traps list took bare character model
numbers and nothing else, which meant the only people who could use it were the ones who had
already gone and looked a number up — and the list of *words* sitting right next to it made that an
easy thing to get wrong. It takes names now, in any casing, alongside the ids it always took, and if
you misspell one it tells you which name you were probably reaching for. Put a number in the wrong
list and it says which list numbers go in. Only 35 enemies have a name to give: Elden Ring never
writes an enemy's name on the screen, so for most of the 390 models there is genuinely no name in
the game to use, and those stay as numbers rather than as something we made up.

Behind the scenes, a second-opinion audit tool now cross-checks the
305 checks whose names still read `(region unconfirmed)` against an independent, permissively
licensed corpus, so those guesses can finally be argued with instead of trusted.

Nothing else yet. This window was opened at the v0.5.0 tag with zero commits past it, in the same
change that promoted stable to v0.5.0; nothing was carried over. `CONTRACT_HASH` stays at
`13db0b3a` — only the exact-version handshake moved.

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
