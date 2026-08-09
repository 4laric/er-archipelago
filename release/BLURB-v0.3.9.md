# v0.3.9 — release blurb

**This is the release where the map stops handing you the whole warp network at once, and where the
options wizard finally says what it is selecting.**

## Warp points you have to find

Until now, unlocking a region lit every Site of Grace it has, so the warp network arrived fully built
and getting around collapsed into a menu. **Grace Attunement** hands you ONE grace when a region
unlocks and holds the rest until you have physically touched a few of them -- then the region blooms
and the whole bundle lights at once.

    grace_attunement         0..10, default 0 (off, and off is a byte-exact no-op)
    grace_attunement_anchor  front_door (default) | random_grace

The grace you are handed is the region's own front door, so you always arrive somewhere sensible.
`random_grace` gives you any of the region's graces instead, which can drop you deeper in and cuts
more traversal -- and every candidate is a real, physically-present warp point, so it can never
strand you in a sealed arena.

Small regions are left alone entirely. A region without enough graces to reach your number would
either attune on its very last grace and then bloom nothing, or never attune at all and leave its
graces dark for the whole run -- both read as a bug rather than a setting. At a threshold of 4 this
gates 16 of the 28 bundled regions and skips 12.

This one needs a client that supports it. A seed with attunement on will refuse an older client
rather than connect and quietly ignore the setting, which is the only version-sensitive thing in this
release.

## The options wizard says what it is actually selecting

**The progression-surface picker no longer describes itself in tag names.** If you have ever ticked
`Church` in the options wizard believing you were opening up church locations, you were actually
selecting the 13 Sacred Tears -- and `Basin` is Crystal Tears, and `Seedtree` is Golden Seeds. Every
class now shows a real name and a one-line note about what picking it costs you, grouped so the four
boss classes sit together instead of being scattered by the alphabet. Your existing yamls are
untouched: the keys are exactly the same, on purpose.

**Every box now tells you what it is worth.** Next to each class is the number of locations ticking it
would actually add -- or, if it is already ticked, what unticking it would cost -- over a running
total of how many locations can hold progression. Most of these classes overlap each other, so a box
frequently adds nothing at all: `Boss` already covers every major, legacy and field boss, and
`MajorBoss` already covers every Remembrance and Great Rune. You no longer have to know that. The box
just says `adds nothing`.

The count knows about the DLC, so a base-game seed is not offered Scadutree Fragments it cannot
place.

## Bosses, merchants, and 29 checks that had no name

**Bosses now actually count as bosses.** The `Boss` location class knew about 143 checks; it should
have known about 214. Bosses hand you their reward through more than one mechanism in the game's own
scripts, and we were only reading one of them — so more than a hundred bosses whose drops we had
already catalogued were being treated as ordinary loot. Among other things that means a filler
"sweep" was handing out things like the Talisman Pouch from the Divine Tower of Caelid, which it
should never have done, and roughly sixty catacomb and cave bosses now register as bosses at all.

**And a merchant-shaped bug behind it.** `Shop` was quietly NARROWER than `ShopNonSpell`, so asking
for "all merchants" got you fewer checks than asking for a subset of them. The same gap let a
buy-only remembrance weapon at Enia sit on the progression surface, and made a Liurnia catacomb boss
pay out six of Preceptor Seluvis's spell-shop slots on death. All three came from one root cause and
are fixed together.

**And 29 checks that shipped called `check` now have names.** Dryleaf Dane's drop was one of them --
you would find `Scadu Altus :: check - around Liurnia Lake Shore`, with no item and a description
pointing at a lake in the wrong half of the map. Every one of those names had ALREADY been worked out
by one of this project's own tools; the generator just couldn't reach it. Scepter of the All-Knowing,
Igon's Greatbow with Ash of War: Igon's Drake Hunt, Dueling Shield with Ash of War: Shield Strike, ten
Swords of Light, ten Swords of Darkness, Beast Claw with Ash of War: Savage Claws, and Dane's Dryleaf
Arts. Exactly one check is still called `check`, and it stays honest about it.

## A door that could never open

Metyr's boss arena is reached through a door on the Cathedral of Manus Metyr's tile, and the game
enables that door only after you have set flags on two OTHER tiles -- **which are in two different
regions**, one in Scadu Altus and one in Jagged Peak. So a seed that kept Scadu Altus and sealed
Jagged Peak could never open it, while the randomizer went on believing her region was reachable and
could put a region Lock behind her. That flag is now forced open with the region. The half of the
condition that belongs to Ymir's own questline is deliberately left alone -- any seed that can reach
the door sets it by playing.

## Housekeeping

**The window was opened by a red gate.** v0.3.8 was tagged and published on 2026-08-08, and two
commits landed past the tag while `APWORLD_VERSION` still named it — so their notes were being
written into a section a player would read as shipped. `check_release_notes` refused, which is the
whole reason it exists. Worth one line because the v0.3.8 notes had just finished celebrating the
first window in five opened deliberately rather than by a red gate. One swallow.

**Two things the tag broke on its way out, both fixed before anything else landed.** A regen run on
the Windows box committed an input hash CI cannot reproduce — the box and the committed input bundle
are two legitimate but different input sets, and the generated content was identical either way. And
the shipped-contract ledger owed v0.3.8 its row, exactly as the comment sitting above it had
predicted.

The decompiled talk scripts have been carried in the datamine bundle since July but were never
declared as an input, so a changed or half-finished decompile could not invalidate the build stamp.
They are declared now. No data changed -- every generated module is byte-identical; only the input
hash moves.

`CONTRACT_HASH` moves for the first time since v0.3.7: `d7d3a58e` to `5c2b9bf2`, and grace attunement
is the entire reason. Everything else in this release works with a v0.3.8 client.
