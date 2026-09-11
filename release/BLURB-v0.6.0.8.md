# v0.6.0.8 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes.** Versions are V.R.M.F and this is still the 0.6.0 line: a v0.6.0.8 client plays every seed
rolled by any 0.6.0-line apworld, your run included, and the contract hash has not moved since
v0.6.0.3, so a v0.6.0.3 through v0.6.0.7 client also plays every v0.6.0.8 seed. Your save is not
at risk in either direction. Two things that are not about the contract at all: on Elden Ring
2.7.1.0 you need a v0.6.0.6 or newer client to attach, and the Respec overlay action needs
v0.6.0.7 or newer. Both were already true before this window opened.

## What you need to update

- **Client:** **Optional** — unless your game is on Elden Ring 2.7.1.0 (v0.6.0.6 or newer
  required) or you want Respec (v0.6.0.7 or newer).
- **APWorld:** Host-only — install v0.6.0.8 when generating a new room once it ships.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — a fixpack never strands a running seed.
- **Profile/assets:** No action so far. If an entry below moves the MapForGoblins build or the AP
  Flower package, this line changes with it.

## What is in it so far

- **Furnace golem checks (#1544):** Furnace golem rewards now use the complete eight-encounter MSB census: all sixteen rewards are checks, including the previously missing Furnace Visage. Rauh, Cerulean and Castle Watering Hole rewards use their corrected regions. Existing check IDs are preserved; these changes apply to newly generated rooms (#1543).
- **Region evidence pass (#1538):** Twelve more checks now use corrected regions in new rooms, backed by MapForGoblins placements and route evidence. These include Sacred Blade in Limgrave, the Church of Consolation greathammer in Gravesite, six Abyssal Woods rewards, Crimson-Sapping Cracked Tear in upper Rauh, Bloodfiend Hexer ashes in Gravesite and two Scadu Altus Furnace Visages. Their region locks and sweep owners follow those homes.

## What carried over from v0.6.0.7

Nothing is owed. Both v0.6.0.7 release workflows succeeded on `4b2f4472`, the window opened at
that tag with no commits past it, and every v0.6.0.7 entry sits under its own heading. The one
loose end is not a note debt: the tag push was delivered twice, so the v0.6.0.7 release carries two
client bundles that differ only in their build timestamp; one of them should be removed from the
release page.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
