# v0.5.2 — release blurb (draft)

_Draft. Written as the window fills, not at tag time — the moment a change lands is the
only moment anyone remembers why it mattered._

## What you need to update

- **Client:** Required — use the v0.5.2 client with v0.5.2 seeds.
- **APWorld:** Host-only — the room host or generator must install v0.5.2; joining players only
  need the matching client.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — keep an active v0.5.1 seed on its matched v0.5.1 pair.
  There is no save migration; just do not mix client and APWorld versions.
- **Profile/assets:** No action — no profile or packaged asset changed when the window opened.

## What is in it so far

Nothing yet. This window was opened at the v0.5.1 tag with zero commits past it, in the same
change that promoted stable to v0.5.1; nothing was carried over. `CONTRACT_HASH` stays at
`13db0b3a` — `abilityUnlockItems` is still the newest slot-data shape, and only the exact-version
handshake moved to 0.5.2. The client half is clients#459, whose merge commit this change pins.

## What carried over from v0.5.1

Nothing — v0.5.1 shipped everything it documented: `region_sync` for seamless co-op, where one
player opening a region opens the door for every opted-in Elden Ring slot in the party;
`full_area_sweeps`, where a boss hands you the whole area instead of a slice of it; `spawn_traps`
taking enemy names instead of only model ids; and the progressive ability-lock fix that hands an
attack back early so a seed that locks all four attack inputs is not stuck against its first
kill-gated check.

`stable` moved to v0.5.1 in this same change, at its tag.

## The Tarnished situation

Elden Ring 2.7.0.0 (Tarnished Edition) is still the thing standing over this window. v0.5.1
shipped **candidate** offsets for it — a build that can find out whether it works instead of
refusing on sight — and they have not been run against the real 2.7.0.0 executable, so the
in-client warning saying the addresses are unverified still stands. The upstream `eldenring-rs`
arm for 2.7.0.0 is still pending; the fork pin retires the moment it lands. The Japanese
Tarnished executable remains unsupported and says so.

## For whoever writes the real one

The v0.5.0 blurb is the model to beat: it opens on what a player does ("You can take an ability
away now"), not on the option name, and only reaches the key names after the feeling. The v0.4.3
blurb is the same shape. Say what someone will feel at the table before what was built.
