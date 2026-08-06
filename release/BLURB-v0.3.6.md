# v0.3.6 — release blurb (draft)

_Draft. Written as the window fills, not at tag time — the moment a change lands is the only
moment anyone remembers why it mattered._

## What is in it so far

**If you turned enemy scaling off, it did not turn off.** This is the one to lead with, because it
is the kind of bug where the setting looked like it worked. The seed shipped the switch twice —
once correctly set from your yaml, once as a constant — and the client read the constant. So
`enemy_scaling: false` rolled a seed that still re-tiered everything: one player's log has 240
enemies rescaled in a single pass on a run he had explicitly asked to leave alone. If you played a
0.3.5 or earlier seed with scaling off, it was not vanilla, and that is worth knowing before you
judge how the run felt.

The fix is small and the test is the point: the curve is now decided in one place both copies read
from, and a test asserts they agree for both settings, so the switch cannot be half-gated again.

**`num_regions` is how many regions get DRAWN, not how many you end up with.** Set it to 1 and a
four-region seed is correct: the goal you named force-keeps the regions it needs, and any region
kept pulls its parents in behind it. That was always the design — what was wrong is that the option
description said the opposite, and nothing told you the difference at roll time. Generation now
prints the arithmetic:

```
num_regions: 1 drawn (Liurnia) + 2 forced by goal=elden_beast (Farum Azula, Leyndell)
             + 1 parent closure (Altus) = 4 kept
```

We deliberately did not "fix" this by clamping the goal to your drawn regions. A seed that names
Elden Beast as its goal and then cannot reach the Elden Beast is a worse bug than a surprising
region count.

**Talismans stop overwriting each other.** With one unlocked talisman slot — which is most players
for the first few hours — every talisman you were sent replaced the one before it, so you wore the
most recent and never saw the rest. One log has 21 of 22 landing on the same slot. They were never
lost, just never worn.

Which slot a talisman takes is now worked out from the Talisman Pouches in your received-item
stream rather than read off your character, which also means reconnecting rebuilds the same loadout
instead of silently rearranging it.

One honest caveat: if a Talisman Pouch reaches you outside Archipelago — a character brought in from
another seed — the count under-reports and you get fewer slots than you have earned. The client
warns when it notices.

**Enemies can now be scaled DOWN, which they never could before.** Every complaint about scaling
in the last two releases came from one gap: the mod's whole ladder starts at 1.14x and has no rung
below it, so an enemy vanilla tuned for the endgame could be made stronger and never weaker. If your
seed opened on Mountaintops, the things living there stayed exactly as strong as vanilla made them,
and you met them with starting gear.

Fixing it needed a tool the game does not ship. No single effect in Elden Ring's 11,325 scales both
health and damage below normal — 20 rows lower health, 25 lower damage, none do both. What exists is
a handful of leftover ally-tuning rows from the DLC that stack, so the down-states are composed:
0.70x damage, 0.45x damage at three-quarter health, and so on down. The composition is measured, not
assumed — one enemy's health went 1098 to 274 and another 1939 to 1454, both exact.

How far an enemy comes down is the game's own step between the two difficulty rungs, not a number we
picked. Where that step is under ten percent we leave the enemy alone, because the smallest tool we
have is a thirty percent cut and firing it at a five percent problem is not a fix.

**Named characters come down with everything else, and this one is a deliberate trade.** Invaders
and duel NPCs carry no rune reward, so the mod cannot read their strength directly and has to infer
it from the ground they stand on. It used to refuse to do that at all, because inferring *upward*
once made Vyke come out crazy strong. But that reasoning only ever applied to making something
stronger — going the other way the worst case is an enemy that dies too easily, which is a
disappointment rather than a wall.

So the rule is set on the fight that hurts: Okina in a Mountaintops you reached first, or Ancient
Dragon Man on a Gravesite Plain start. The cost is that characters who were already reasonable get
cut too. Vyke did not need it and gets it anyway. If that reads as mushy, say so — the fix is to
move the whole curve, not to strand that class again.

**Areas the seed does not cover are left completely alone.** Roundtable Hold, the Chapel of
Anticipation, and the moment at connect before the game has worked out where you are. Those used to
get the bottom rung of the ladder applied to them on no evidence at all. Making no statement about a
place the seed does not reach is the right answer, and it is now what happens.

---

## Notes for the next pass

- Region-lock hint work (#412) and the Moonlight Altar region fix (#410) are queued, not in yet.
- The scaling down-direction (#346 phase 1b) SHIPPED this window — the entry above. The attack
  rate it buckets on is still argued from the param rather than measured in game; the health half
  is measured exactly. Play validates the rest.
- Still open and worth a line if it lands: the floor is doing nearly all the difficulty work,
  because most kept regions sit at sphere 0. Tuning it matters more than the gradient does.
- Do not write the "what's fixed for players" section from this file alone — check the merged PR
  bodies, which carry the player reports and the measured tables.
