# v0.3.7 — release blurb

_Written as the window filled rather than at tag time — the moment a change lands is the only
moment anyone remembers why it mattered._

## What is in it

**One of Elden Ring's Great Runes has been missing from every seed, and nothing noticed.**

Beat Rennala and the game hands you two things: the Remembrance of the Full Moon Queen, and the
Great Rune of the Unborn. Only the Remembrance was ever modelled as a check.

That would be harmless if the two were independent, but they are not — they hang off the same
acquisition flag, and the randomizer clears a check's vanilla items by flag. So it was clearing
both, and because only one of them had a check to hand something back, the Great Rune of the Unborn
was simply deleted. Not misplaced, not made rare: removed from the game and replaced by nothing, in
every seed, since the check model landed.

What kept it hidden is that the item had no name anywhere in our data. Not in the spoiler, not in
hints, not in the item catalog. A player who went looking for it found no trace of it existing —
which is exactly what a player did earlier this week, and it read like the rune had been excluded on
purpose.

It is now a check of its own, in the same place, beside the Remembrance. Both are shuffled
independently. Both are yours to find.

If you use Rennala to respec, this is worth a moment of your attention: vanilla wants that rune in
your inventory to offer rebirth. We have not yet confirmed whether the game asks for the item or
just the flag, so we do not know whether respec has been quietly unavailable this whole time. If you
have tried to respec in a recent seed, we would like to hear either way.

## The Hippopotamus problem

bobler's tracker said `Shadow Keep 124/270` and he said "all bosses dead except hippo which i can't
fight". He was right on both counts, and the two facts were the same fact.

Killing a boss hands you the loot from its area — that is what `dungeon_sweep` is. The Golden
Hippopotamus's sweep is 104 Shadow Keep checks, 38% of the whole region. But the arena you fight it
in is not Shadow Keep. Its reward is scripted in the Keep's map, so that is where we filed the
sweep, while the ground under the fight belongs to Scadu Altus. His seed kept the Keep and not
Scadu Altus, so the region lock ejected him every time he walked toward the fight.

We knew half of this in July. The Hippo's *reward* was re-homed to Scadu Altus back then, with a
note in our own data explaining the kick. The 104-check sweep was left in Shadow Keep and nobody
asked whether that was the same problem wearing different clothes. It was.

Six groups had this shape. They are no longer sent to seeds that cannot fire them, and the tracker
no longer promises a payout that depends on a fight you are not allowed to have. Every check
involved is still in your seed, still in its own region, still yours to walk to and pick up — the
sweep was a convenience, and you keep the checks either way.

The part worth saying plainly: **this had been true in roughly half of all six-region seeds since
sweeps shipped**, and no gate anywhere asked the question. There is one now, over all 225 sweep
groups rather than over the one that got reported.

## Two settings, one of them because somebody asked

**You can open a run on more than one region.** bobler asked for it the day v0.3.6 shipped -- *"is
there an option to start with more than 1 region unlocked?"* -- and the honest answer was no.
`start_regions` is that option. Set it to 1 and nothing changes at all: not "equivalent to before",
identical, down to the position in the random stream, so every seed anyone has rolled still rolls
the same way.

**The Scadutree blessing is two settings now, and it has lost its ceiling.** One option had been
doing two jobs -- where the blessing applies, and whether the DLC gets a catch-up floor -- so they
are separate, which makes a fourth combination sayable for the first time: vanilla scope *with* the
floor, meaning the blessing behaves exactly as the base game intends while the DLC never runs under
its expected level.

The cap of 12 is gone, and it is worth saying why it was there, because it was never a balance
opinion about the blessing. It was a statement about how much of the item pool fragments were
allowed to eat. Those are different arguments and it had been standing in for both. The real ceiling
is the game's own ladder at 20 -- the base game hand-places exactly fifty fragment units, which is
exactly level 20 -- so that is the ceiling now, and the pool-pressure question is answered where it
actually lives: half the injected fragments arrive as a **Scadutree Fragment x2**, so fifty units
costs 38 items instead of 50.

## Rykard, and the spear he assumes you brought

Rykard's second phase is built around one weapon. The base game leaves the Serpent-Hunter on the
path to him so that you arrive holding it; a randomizer sends it to somebody else's world. bobler,
who has been playing this build harder than anyone: *"rykard without serpent hunter is some bs"*.

So the fight now brings its own. Walk into Rykard and, if you do not have one, you are handed a
copy. It is keyed on the character rather than the room, which matters more than it sounds: bobler
runs an enemy randomizer, and over two of his seeds Rykard turned up in Lamenter's Gaol and then in
the Chapel of Anticipation. The spear found him both times. It covers the God-Devouring Serpent too
-- same character underneath -- and it never claims the check for the real Serpent-Hunter, which is
still out there for someone to find.

Getting the timing right took three passes and we were wrong twice.

The first version handed the spear over on area load, which under an enemy randomizer meant the
toast told you where Rykard had been swapped to before you could see him. The second held your
weapon slots from that same moment, so a foreign weapon was silently refused for minutes on the walk
toward a fight that had not started. Both are fixed: the grant still fires early, because a
field-spawned Rykard has no healthbar to wait for, but the hold is now keyed on the boss healthbar
-- the game's own statement that the fight is happening.

Then bobler said the fix was not working: *"no spear whatsoever"*. We could not tell him why, and
that turned out to be the actual defect. A non-grant was completely silent -- "Rykard was never
loaded", "you already own one", and "a read failed" all looked identical in the log, which is to say
they all looked like nothing at all. His log was 13,160 lines and contained no evidence either way.

So we shipped a diagnostic instead of a guess, and it answered in one line on his next session:

    boss-grant: healthbar npc_param 47101038 = chr 4710, IS Rykard |
    c4710 loaded = yes | already holds the spear = yes -> no grant

The real Rykard, the real spear in his bag, and nothing in his hand. The equip had been riding on
the one-shot grant, so it fired exactly once per character, ever -- reload, re-fight, or just swap
weapons afterwards and the spear stayed in the bag while the fight it exists for happened without
it. It now follows the fight rather than the grant.

And then it still did not work, twice more, for two entirely different reasons. Both are worth
telling, because both were invisible in exactly the way the first one was.

**The spear went into a queue and never came out.** The next log had the line saying we were putting
it in his hand — and nothing after it. That silence was the whole diagnosis: every equip this client
performs writes a line naming the inventory handle it resolved, and his two successful ones from
earlier that day both did. The one that mattered did not.

With auto-upgrade on, an incoming weapon is queued at your current upgrade level, because the grant
that is about to deposit it will deposit it upgraded — the queue and the bag have to agree. But this
spear was not incoming. It was already in his bag, banked at +0 hours earlier when +0 was the
target, and no grant was coming to raise it. So we asked the game for a Serpent-Hunter +3 that had
never existed, missed, and retried in silence for the rest of the session. It now asks the bag what
it has instead of predicting what a grant would have put there.

**Then the spear was in his hand and still did nothing.** bobler: *"it equipped but weapon dont
work"*. The waves.

Those waves are not a property of the weapon. The Serpent-Hunter's own row ships empty in the field
that would grant them; the game switches the moveset on during the fight and off again afterwards,
which is why the spear is famously useless anywhere else. So we set the field ourselves — and
shipped a probe alongside it, because we had been wrong twice already and did not intend to guess a
third time.

The probe answered on the first session, in one line, and it was not the answer we expected: the
write had landed, read back clean, and the effect still was not on him. He had been holding the
spear for thirty-three minutes. That field is read when a weapon is *equipped*, so editing it under
a weapon already in your hands changes nothing at all until you re-equip. bobler confirmed it by
swapping weapons and walking back in, at which point the waves worked. The effect is now applied to
the character directly, so it survives being already equipped — and survives every area load, which
would otherwise have quietly killed it and made the whole feature look intermittent.

**Worth knowing before you notice it yourself: the Serpent-Hunter now throws its waves everywhere.**
Not just at Rykard. Keeping it fight-only would have meant re-deriving, every session and after
every load, a condition the game sets for its own reasons and does not tell us about — and on a
randomizer where the spear can be found anywhere and an enemy randomizer can move Rykard into a DLC
arena, "only in the vanilla arena" is not a rule worth protecting. It is a good great spear now.
That is a deliberate change, not a side effect.

**And you get your weapon back.** When Rykard's healthbar drops, whatever you were holding goes back
into your hand. Two things outrank that: a weapon that arrived from another world during the fight
(it is yours, you should be holding it), and a swap you made yourself mid-fight (it was your
decision, and we already overrode one of those on the way in). Weapons that arrived while you were
busy have always been held rather than dropped, and they still land the moment the fight ends.

One thing none of this can do: if an enemy randomizer has moved Rykard out of Volcano Manor, whoever
inherited his arena gets nothing. The spear is the answer to Rykard, so it goes where Rykard goes.

## Known, and honest about it

**On a DLC-only seed, `goal: auto` does not necessarily end on Promised Consort Radahn.** A player
finished one this week, saw the goal complete after a boss that was plainly not an ending, and
reasonably concluded the ending was broken. It was not — but the shape is worth explaining, because
anyone rolling DLC-only can meet it.

The base game's finale is guaranteed: the Ashen Capital is never rolled, exists on every seed with
the base game in play, and is where `auto` ends. The DLC has no equivalent. Enir Ilim is an ordinary
region in the DLC pool, so a draw that does not happen to keep it ends your run on the deepest
terminal region you did keep — for him, Romina in the Ancient Ruins of Rauh. That is a real
Remembrance boss and a defensible capstone; it is just not the ending he was picturing.

If you want Promised Consort Radahn, say so: **`goal: promised_consort`** forces Enir Ilim into your
draw and ends the run there. Making `auto` do it by default is the obvious fix and is not in this
window.

**The capital gate counts a rune we do not.** Elden Ring opens Leyndell on a count of flags rather
than on which runes you hold, and Rennala's flag falls inside the range it counts. So the game has
always treated the Great Rune of the Unborn as one of the runes on that door. We do not, yet.

The good news is which direction that error runs: our logic is the stricter of the two. Nothing
becomes unreachable, no seed can soft-lock on it, and no fill is unsafe. What you may see is the
capital physically open a little earlier than the randomizer expects.

Fixing it properly changes what "how many Great Runes" means — the goal option, the gate, and the
item pool all have an opinion — so it is scoped and deliberately not rushed into this window.
