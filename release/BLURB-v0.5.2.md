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

**Four thousand check names stopped promising something a seed might not do.** If a boss's sweep
could pay a check, its name said so -- "also granted by Fire Giant" -- and that was baked into the
name once, for everyone, before any seed existed. Turn sweeps off, or let the surface cut take a
Golden Seed back out, and the name kept saying it anyway. Haraldwyrm noticed first, colombius
brought the receipt, and Alaric ruled: if we are leaving them off sweeps, we should not say they
are granted by the sweep. The clause now reads **"may be sweep-granted by Fire Giant"** -- true in every
seed -- and the tracker, which knows your seed, still tells you when it is a real grant. 4,063 of
4,948 names change; no check moves, no id shifts. Old seeds keep their old wording in spoiler logs
and hints, and the new client reads both (#936).

**Tarnished Edition works without letting its new item rows corrupt the shuffle.** The client now
supports both Elden Ring 2.7.0.0 and the Japanese 2.7.0.1 executable on upstream's real address
tables. Patch 1.17 inserted equipment rows into the middle of several parameter tables, which made
old row-number assumptions show the wrong weapon name or icon. v0.5.2 recognises the verified new
rows and keeps them out of Archipelago's item and location pools for now. You can play the new game
builds; their new equipment simply waits outside the shuffle until its names and placements have a
complete, tested census (#1096, clients#461).

This window was opened at the v0.5.1 tag with zero commits past it, in the same
change that promoted stable to v0.5.1; nothing was carried over. `CONTRACT_HASH` stays at
`13db0b3a` — `abilityUnlockItems` is still the newest slot-data shape, and only the exact-version
handshake moved to 0.5.2. The final client pin is `d99d81d`.

## What carried over from v0.5.1

Nothing — v0.5.1 shipped everything it documented: `region_sync` for seamless co-op, where one
player opening a region opens the door for every opted-in Elden Ring slot in the party;
`full_area_sweeps`, where a boss hands you the whole area instead of a slice of it; `spawn_traps`
taking enemy names instead of only model ids; and the progressive ability-lock fix that hands an
attack back early so a seed that locks all four attack inputs is not stuck against its first
kill-gated check.

`stable` moved to v0.5.1 in this same change, at its tag.

## A client reliability fix also rides in

The pinned client also fixes a Bloodborne failure where a location check written into a silently
dead socket looked locally complete and would not be sent again until relaunch. Checks now remain
pending until the server confirms them. Retries are immediate, then back off through
1/2/4/8/16/30 seconds per location and stay at 30 seconds until acknowledgement; reconnecting resets
the delay for one immediate recovery attempt. There is no terminal retry count, so bounding the
traffic does not reintroduce a lost-check edge case (clients#455, clients#467, clients#468).

## For whoever writes the real one

The v0.5.0 blurb is the model to beat: it opens on what a player does ("You can take an ability
away now"), not on the option name, and only reaches the key names after the feeling. The v0.4.3
blurb is the same shape. Say what someone will feel at the table before what was built.
