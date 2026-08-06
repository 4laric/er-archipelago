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

---

## Notes for the next pass

- Region-lock hint work (#412) and the Moonlight Altar region fix (#410) are queued, not in yet.
- The scaling down-direction (#346 phase 1b) is still blocked on an in-game attack measurement.
- Do not write the "what's fixed for players" section from this file alone — check the merged PR
  bodies, which carry the player reports and the measured tables.
