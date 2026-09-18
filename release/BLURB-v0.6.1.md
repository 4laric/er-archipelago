# v0.6.1 — release blurb (draft)

_Draft. Written as the window filled, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes -- and your existing runs keep working.** v0.6.1 changes what *new* rooms roll, not what the
client and the apworld say to each other: `CONTRACT_HASH` is unmoved at `2aa64f43` since v0.6.0.11.
So the v0.6.1 client plays seeds from v0.6.0.11 and v0.6.0.12 directly, and reads every 0.4.13,
0.5.x and 0.6.0.x seed older than that through the audited legacy-contract bridge. Swapping the
`.dll` mid-run on any of them puts nothing at risk and needs no reroll or save migration. The
standing version gates still apply and none are new: Elden Ring 2.7.1.0 needs a v0.6.0.6 client or
newer, Respec needs v0.6.0.7, the trap-replay and main-menu delivery fixes need v0.6.0.8, and a
seed rolled on v0.6.0.11 or newer (including v0.6.1) needs a v0.6.0.11-or-newer client.

## What you need to update

- **Client:** Optional for seed compatibility; update for the Margit region-lock fix (existing runs too), Region Sync standing opens, and lighter enemy scaling. No reroll.
- **APWorld:** Host-only, for newly generated rooms after this version ships.
- **YAML:** **New YAML optional. Existing YAMLs remain valid.** A YAML that leaves out `ending_condition` and `goal_region_unlock_policy` now rolls the new default goal; set them explicitly to keep the old one.
- **Existing seed/save:** Compatible; no regeneration or save migration required.
- **Profile/assets:** No action; no map or asset changes.

## What is in it

**The default goal is four Great Runes now, and Region Locks are no longer needed to finish.**
Players kept getting caught out by Locks being required for the ending, so a fresh yaml no longer
asks for them. Want the old goal? `ending_condition: region_locks` with
`goal_region_unlock_policy: items_held`. Anything that already set either key rolls exactly as it did.

**One switch for how progression is shared.** `progression_sharing: balanced` is what the mod has
always done; `open` is ordinary Archipelago, with no 1/N reservation and no bar on foreign
progression. The older trio of options is tucked out of the wizard but still honoured in existing yamls.

**Leyndell opens on its Lock, like everywhere else.** The capital used to sit behind a second gate --
two Great Runes on top of the Leyndell Lock -- and while that wall was armed the Lock lit nothing at
all, the single most-reported "my Lock is broken" in the mod. That wall is gone: the Lock lights the
whole capital bundle, sewer graces included, and the physical seal opens on the same receipt. Great
Runes still count for the `great_runes` ending, but open no doors in Leyndell. (`natural_progression`
mode has no Locks, so the game's own two-rune gate still stands there.)

**Mountaintops unlocks give you a way onto the mountain.** With limited graces, new seeds now
retain both Forbidden Lands and Zamor Ruins instead of leaving upper access dependent on Rold or a
closed Hero's Grave door, and attunement keeps the separate entry points in Mountaintops and Ainsel
available. Existing seeds keep their original bundles.

**Margit's arena follows the Stormveil lock.** Its raw game region previously got collapsed into
Stormhill, so starting in Stormveil could eject you to Roundtable during the fight intro. Existing
seeds benefit from updating the client.

**Region Sync stops leaving your partner behind.** A region you started in, or one opened while
they were offline, is now re-announced every couple of minutes instead of only on a live Lock receipt.

**Less stutter in crowded areas.** The enemy-scaling sweep backs off once a region has settled and
snaps back the moment anything changes.

## What carried over from v0.6.0.11

Nothing is owed. v0.6.0.12 was opened and never tagged; it became this release.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
