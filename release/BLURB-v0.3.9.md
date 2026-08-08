# v0.3.9 — release blurb (draft)

_Draft. Written as the window fills, not at tag time — the moment a change lands is the only moment
anyone remembers why it mattered._

## What is in it so far

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

**And a merchant-shaped bug behind it.** `Shop` was quietly NARROWER than `ShopNonSpell`, so asking
for "all merchants" got you fewer checks than asking for a subset of them. The same gap let a
buy-only remembrance weapon at Enia sit on the progression surface, and made a Liurnia catacomb boss
pay out six of Preceptor Seluvis's spell-shop slots on death. All three came from one root cause and
are fixed together.
