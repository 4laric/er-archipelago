# v0.6.0.6 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes — and if Steam has updated your game, you have to.** Versions are V.R.M.F and this is the
0.6.0 line: a v0.6.0.6 client plays every seed rolled by any 0.6.0-line apworld, your run
included, and the contract hash has not moved since v0.6.0.3, so a v0.6.0.3, v0.6.0.4 or v0.6.0.5
client also plays every v0.6.0.6 seed. Your save is not at risk either way. But Elden Ring moved
to 2.7.1.0 on September 8th, and older clients switch themselves off on that executable — on the
new game binary this update is the only client that runs.

## What you need to update

- **Client:** **Required on Elden Ring 2.7.1.0** (the 2026-09-08 Steam update); optional
  otherwise — a v0.6.0.5 client keeps playing every 0.6.0-line seed on 2.6.2.x or 2.7.0.x, and
  the contract hash has not moved since v0.6.0.3.
- **APWorld:** Host-only — install v0.6.0.6 when generating a new room once it ships.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — a fixpack never strands a running seed.
- **Profile/assets:** **Reinstall or replace** — both of them. Use the MapForGoblins build and
  preset shipped with this release (it carries a crash fix and new map defaults), and reinstall
  the AP Flower package with the bundled installer: the Flower ships again in this bundle, rebuilt
  from the 2.7.1.0 atlas, so a v0.6.0 install that had it disabled should re-enable it.

## What is in it so far

**The builder starts with the run you want.** Combine content, run size, difficulty,
Boss Rush, rewards, travel and multiplayer profiles, then customize the individual settings.
You can keep the run in base-game regions while mixing DLC gear into its pool. There is
also a useful-consumables reward profile inspired by Nightreign. Existing option names stay
the same, and vanilla placement is tucked away under advanced settings instead of appearing
in starting templates. Existing YAMLs remain valid; the new DLC gear option is off unless
you select it.

**Elden Ring updated to 2.7.1.0 on September 8th, and this client follows it.** Older clients
show the "unsupported game version" box and switch themselves off; your save is untouched
either way. The new addresses come from the same generator upstream uses, run against the real
executable, and the patch itself changed nothing in the game's item tables -- so nothing about
your seed moves. Players still on 2.6.2.x or 2.7.0.x keep working. What has NOT happened yet is
a live run on 2.7.1.0; until one is logged, treat this as a build that should work rather than
one that has.

**The in-game map stops crashing and stops lagging.** A use-after-free on the map overlay
thread, caught in a v0.6.0 player log, is fixed. Late-game map opens are faster because pins
hidden by a setting or by collection are no longer built at all; the trade is that unhiding a
marker takes effect on the next map open. Two defaults changed with it: **"In logic only" is
now on**, so the map pins only checks your tracker says you can reach right now (turn it off
under F10 for everything), and **the orange progression rings are gone** along with their size
slider -- they buried the pins they were meant to lift.

**The Divine Tower of East Altus is Leyndell now.** Two players, a month apart, said the same
thing about it -- boblerrr on the Nexus page in August, Sinon on the 7th: the tower's loot was
counted as Altus, and the tower is not Altus. You reach its gate one way, over the greatbridge out
of Leyndell's eastern ward that opens after Morgott, so an Altus-only seed was steering people at
seven checks they could not walk to while a Leyndell seed walked them past all seven. The checks,
the Fell Twins' sweep and the tower's own kick geometry all moved together, which is the part that
matters: the region lock now ejects the player who has no business up there and lets in the one who
does. Its two graces stay out of every warp bundle -- owning Leyndell buys you the walk, not a
shortcut past Morgott. Altus loses seven checks and Leyndell gains them, so seeds roll differently;
nothing about the client, the contract or a save in progress changes.

**The Finger Ruins of Dheo bell is Shadow Keep ground, not Jagged Peak.** The bell is a gate
check, so a seed was asking for Jagged Peak access to reach something you only ever walk to
through the Keep -- and Metyr's remembrance inherited the same wrong requirement. Nothing was
mis-typed by hand: the tile the bell sits on has no grace, no region row and no boss, so the
derivation hopped to its nearest neighbour and landed one diagonal step away on Jagged Peak
ground. It is pinned now, and the two places that had the region written out in code read it off
the shipped table instead. Exactly one check moves -- Jagged Peak 40 to 39, Shadow Keep 118 to
119 -- so seeds roll differently; the client, the contract and a save in progress are untouched.

**The AP Flower is back, and the icons are right this time.** v0.6.0 pulled the Flower atlas
override because it was built before the Tarnished pack: it drew the wrong icons on Tarnished
weapons and left the starter-class previews blank, so the AP placeholder fell back to the game's
Telescope icon. That fallback was meant to last one release and lasted three -- the packaging gate
that omitted it matched the string "0.6.0" exactly, so v0.6.0.4 and v0.6.0.5 quietly shipped the
old atlases instead of shipping none. The override is rebuilt from the Elden Ring 2.7.1.0 menu
files and back in the bundle, both symptoms with it; and the packer now refuses the two old
atlases by their checksums, so no future build can re-ship them by failing to match a version
number. If you disabled the Flower package entry back in v0.6.0, re-enable it or run the bundled
installer again.

**Twenty-two player reports from one notebook, worked one row at a time.** 255 sent a 124-entry
notebook on the 8th and it is now in the repo, unedited, as the thing every issue points at. Three
pickups are newly marked missable -- Latenna's somber stone, which you can lose forever just by
receiving the two Haligtree medallions in the wrong order, and the Chrysalids' Memento / Crimson
Hood pair, which the game makes mutually exclusive off a line of Hewg's dialogue. Ten checks moved
region, most of them because the game's own play-area volumes put them somewhere other than where
we had filed them. The nine Ymir and Metyr rewards now ask for the Hole-Laden Necklace, and the
both-bell ones for the Finger Ruins region too, instead of sitting behind Scadu Altus alone -- and
two bosses stopped handing those rewards out for free. Ten checks that no object in the world
actually holds, including six leftover tutorial pop-ups, are gone.

🛑 **That last one renumbers the AP location ids.** Ids are positional, so dropping ten checks
moved 3848 of them -- everything from 7770795 up shifts down by one to ten. **Nothing you are
playing breaks:** the client reads the seed, not a baked table, the contract hash has not moved,
and a seed or save in flight keeps working exactly as it did. What it means is that a seed rolled
on v0.6.0.6 is not the same seed those settings would have rolled on v0.6.0.5. Our independent
second opinion on the item tables reads the same on both sides of all of it -- 4076 agreements,
eight known disagreements, eighty known gaps, nothing unexplained.

**For a run Steam stranded, there is a way out.** If you were mid-run on a v0.5.7 or v0.5.8 seed
when Elden Ring updated, you were caught between two refusals: your own client would not touch
2.7.1.0, and the v0.6.0.5 client would not touch your seed. This client accepts both, so you can
finish the run. It is a rescue, not a promise -- it carries the 0.6 check and region tables
against a 0.5.7 server's location list, so if a lock or a sweep looks strange on that pairing,
that is why. Roll the next seed on a 0.6.0-line apworld.

**Typing in the connect box stops leaking into the game.** With the overlay's connect modal open,
keystrokes were reaching Elden Ring's own menu whenever the mouse cursor drifted off the modal --
navigating it, sometimes closing the box. The cause was a class of input device the client could
not identify (another mod's proxy `dinput8.dll`, or a device made before our hook was in place),
which fell through to being treated as a mouse. Unidentifiable devices are now blocked whenever
either keyboard or mouse input is, and a typing box owns the mouse regardless of where the cursor
is, so stray clicks stop landing on the game behind it. The open-the-settings-screen workaround is
no longer needed.

**Bookkeeping you will not feel:** the flag-to-lot table behind multi-copy checks was
re-derived against the current param corpus and its datamine is now gated in CI, the
patch-day runbook grew a name-stripping tool so the next Elden Ring update is diffed in
minutes instead of a morning, there is a real enemy-drop table now and every boss we know carries
a class, and the five big offline browser pages are built and published by CI instead of living in
the repository, where they were making every data change collide with every other one.

## What carried over from v0.6.0.5

Two things, and both are ledger rather than promise.

First, everything above landed AFTER v0.6.0.5 was tagged. #1487 and #1489 wrote their notes
under the already-shipped `## v0.6.0.5` heading; this window moves them here, and the v0.6.0.5
blurb is back to its tagged text. So the 2.7.1.0 and MapForGoblins prose in this file has a
day of provenance behind it even though the window is minutes old — nothing was written twice,
and nothing is claimed for v0.6.0.5 that v0.6.0.5 did not ship.

Second, the debts. 🛑 **The 2.7.1.0 client has never been run against the game.** Every one of
its 2.7.1.0 addresses is signature / binary-mapper derived and prologue-checked -- matched against
the shipped executable, never confirmed by a running one. The live smoke test (gate silent,
connect, one check, one item) is being done at this tag and `stable` does not move until its log
exists, and `VANILLA_MULTI_SLOT_ROWS` is still unmeasured on a vanilla 2.7.1.0 run. 🛑 **The
world-side param re-export for the 2.7.1.0 `regulation.bin` has not been done either**: the
committed `gen_inputs.db` is still the 2026-08-29 export, so every table in this release is
derived from the 1.17 corpus. The two regulations compared data-identical across all 239 params,
which is why that is a tidiness debt rather than a correctness one -- but it is owed, not done. Older still, and unchanged: `tools/matt_oracle.py`
leaves 107 item-identity disagreements and 45 missing slots allowlisted by cause, chiefly a DLC
upgrade-material tier disagreement spanning 99 event flags, and v0.6.0.5's `flag_lots.tsv`
refresh sharpened rather than answered that — on 37 of those checks the curated name no longer
names any item the flag's lot grants. Those are research debts against our tables, not risks to
a run.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
