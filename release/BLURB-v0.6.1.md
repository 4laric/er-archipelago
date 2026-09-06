# v0.6.1 — release blurb (draft)

## Can I update the client during a run?

Keep an existing v0.6.0 run on its matching client and APWorld. The v0.6.1 development
window adds checks for newly generated seeds; replacing a DLL does not add them to
an existing room. Use the matching v0.6.1 client when testing a v0.6.1 seed.

## What you need to update

- **Client:** Required — use the matching v0.6.1 client for new seeds.
- **APWorld:** Host-only — install v0.6.1 when generating a new room.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible when kept on its matching client/APWorld pair; new checks require a new seed.
- **Profile/assets:** No action — keep the M4G assets and use the matching client DLL.

## Recovered pickups

Four Oathseeker Knight armor pieces and Royal Magic Grease return as checks, backed
by Map for Goblins placement evidence. Briars of Sin is recovered from its actual
enemy drop, replacing a wrongly identified synthetic source. Existing check IDs
are preserved. Further
NPC, enemy-drop, and access-rule investigations remain open under #1437; this draft
does not claim those reports are fixed.

Eleonora’s Poleblade now checks the real invasion reward instead of an unused copy. Generate a new seed to receive this correction.
