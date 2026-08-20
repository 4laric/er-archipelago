# v0.4.6 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the only moment
anyone remembers why it mattered._

## What changed at the table

Great Rune runs finally mean what the option says: every seed contains all seven, and the goal is
now **any four of seven**, not a seed-picked shopping list. Required progression can also travel to
other players when cross-game progression is enabled instead of Great Runes being local by
construction.

The client carries those rules into the game. Great Runes received through Archipelago open
Leyndell, Divine Tower altars cannot hand out a second vanilla copy, and the goal counter counts any
four distinct runes. The capital reconciler now switches the complete Royal/Ashen world state and
holds it through the game's delayed warp bookkeeping, closing the races that could leave the map or
front-door graces on the wrong capital.

Region entrances got a playtest-driven pass too. Altus opens at the lift-side **Altus Plateau**
grace, Ainsel River opens at **Ainsel River Main**, and Stormveil owns Margit and its Divine Tower
route. The matching client tables were regenerated, including a follow-up that caught Stormveil's
runtime bucket being lost during integration.

The console is more useful when a seed does strand you: `!grace` resolves the live grace table and
prints a pasteable `!warp` command, including graces that are not part of the seed's generated
region data.

Missable rewards no longer eat the good stuff by default. The 285 checks that can vanish behind a
spent currency, a dead NPC, or quest progress are now filler-only, so losing one cannot take a useful
weapon, spell, summon, or tear with it. The old progression-only protection remains available as the
middle setting, and the protection can still be turned off for guaranteed-access play.

A failed connection now has a short diagnostic ladder in the setup guide. The first test is the
stock Archipelago Text Client against the same room: one attempt tells you whether to investigate
the room/network or `eldenring.exe` specifically. The guide then separates immediate refusal from
timeout and points at the process-specific firewall, antivirus, VPN and mod-hook cases that used to
take several rounds of chat to rediscover.

Rakshasa no longer pays out the Finger Ruins of Rhia bell reward. The bell now properly requires
the Hole-Laden Necklace instead of being claimable through an unrelated Scadu Altus boss sweep.

Metyr's route now follows that logic all the way through: both Finger Ruins bells require the
necklace, and when both regions are in play, reaching Metyr requires both Scadu Altus and Jagged
Peak. Dheo is no longer silently rung in a seed where its check exists; a sealed Jagged Peak still
gets the flag because there is then no Dheo check to auto-award.

Behind the scenes, the full world suite now uses both runner cores. Its measured CI-equivalent time
fell from 224.7 seconds to 130.4 without dropping a test or either guard against silently inert
tests, so every later change gets its green-or-red answer sooner.

## What carried over from v0.4.5

Nothing is owed. v0.4.5 shipped complete: its changelog section and its blurb were both finished
while the window was open, and `release/CHANNELS.tsv` promoted `stable` to it in the same commit that
opened this window rather than the morning after -- the second window running that row has not
lagged its tag.

⚠️ One thing v0.4.5 shipped is worth repeating to anyone reading this before they generate: a
**one-region seed on the plain region-locks goal is refused now**. The goal region's Lock is
withheld, so a seed whose only Lock is the region you start in has nothing left to find. Generation
says so and names the ways out.

🛑 And one thing IS owed, unchanged from the last two windows because it is not ours to write:
**Elden Ring Tarnished Edition ships 2026-08-28** and a paid content update moves the executable
version. v0.4.4 shipped the gate that explains that failure to a player instead of showing them a
Rust backtrace, but the RVA table it reports against lives in a third-party crate. When the update
lands, the recovery is an upstream revision plus a rebuild -- see #241. That date is now eleven days
out, so it is likely to land IN this window rather than after it.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option name. Its
opening line -- "You can get BK'ed now, and that is the point" -- says what a player will feel before
it says what was built, and that is the right order. v0.4.5's opening section is the same move.
