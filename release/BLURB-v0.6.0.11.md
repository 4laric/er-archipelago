# v0.6.0.11 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes, and for a seed rolled on v0.6.0.11 you must.** `CONTRACT_HASH` moved to `2aa64f43` this window (one new optional slot_data key), so an older client refuses a v0.6.0.11 seed with `VERSION MISMATCH`. The other direction is safe: the v0.6.0.11 client reads every earlier 0.6.0-line seed (contract `613fb438`, v0.6.0.3 onward) as an audited compatible subset, so swapping the `.dll` mid-run on an existing seed puts nothing at risk and needs no reroll. The standing version gates still apply and none of them are new here: Elden Ring 2.7.1.0 needs a v0.6.0.6 client or newer, the Respec overlay action needs v0.6.0.7, and the trap-replay and main-menu delivery fixes need v0.6.0.8.

## What you need to update

- **Client:** Required for seeds generated on v0.6.0.11 (the contract moved); optional, and safe, on older seeds.
- **APWorld:** Host-only, for newly generated rooms after this version ships.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible; no regeneration or save migration required.
- **Profile/assets:** No action; no map or asset changes.

## What is in it so far

Your Great Runes stop eating their own checks.

The six demigod Great Rune locations used to be spotted by the same flags the game uses to count
how many runes you are holding. That was fine while nothing but the game wrote them — but the
client is about to start writing them on delivery (clients #685), so that a rune handed to you by
another player actually counts at Leyndell's gate and in third-party rune trackers. The collision
is nasty and silent: receive Godrick's Great Rune before you kill Godrick, and the game marks his
drop as already taken, so the check can never be sent. The rune is yours and the location is gone.

So the six checks now watch the boss DEFEAT flag instead. You send Godrick's rune check by killing
Godrick, which is what it looked like it did all along. Nothing about your yaml, your seed or your
save changes, and the location names are untouched.

The tracker stops listing checks your seed cannot give you.

Ace's Haligtree sat at 116 of 123 with both bosses dead. Four of the leftovers were Millicent's
Prayer Room rewards, and Millicent's story starts with Gowry in Caelid — a region that seed never
kept. The checks existed for the multiworld (as filler, as always), but nothing in the game could
award them, and the tracker had no way to know. Now the apworld tells it: checks whose NPC
questline has to be advanced in a region your seed dropped are hidden from the region lists and
counts, with a one-line "hidden: N unobtainable in this seed" under the checks total so the number
is never a mystery. Only routes someone has reviewed are hidden (Millicent, Ranni's Ainsel leg,
the Volcano Manor letters, Sellen, Edgar); the rest of the datamined candidates are written down
as pending and left visible.

## What carried over from v0.6.0.10

Nothing is owed. v0.6.0.10 shipped tagged and complete — the Scadutree Avatar sweep fix went out
with its client half (#682) and the NPC region corrections (#1555) applied to new seeds at the tag.
No entry from that window was deferred into this one.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
