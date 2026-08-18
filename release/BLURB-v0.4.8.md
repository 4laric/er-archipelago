# v0.4.8 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## What changed at the table

**Every Archipelago item you have ever picked up in this randomizer was a telescope.** Cell 92 of
the game's icon sheet belongs to the Telescope, and the AP flower was supposed to be composited over
it. The art had been in the repo since 2026-07-29, but the first shipping attempt tried to rebuild
the atlases on each player's machine. That assumed access to unpacked game files and turned a small
icon replacement into an installation toolchain. We backed that approach out.

The Flower itself still ships. Release bundles now carry authenticated, prebuilt atlases, and the
client's install button copies them into either an ordinary Mod Engine 2 setup or Matt's randomizer.
Players do not need UXM, WitchyBND, Oodle, an image library, or a texture compressor. The installer
does not reconstruct FromSoft assets from a local unpack; it installs the release payload and asks
for the Matt-randomizer path when it cannot find that layout safely.

The ending can now wait for you to finish the regions you opened, rather than appearing as soon as
their Locks arrive. Under the optional `regions_completed` policy, every progression-surface check
in each non-final region must be satisfied. Merely looking through a merchant's visible inventory
counts for its shop checks—you do not have to buy filler to prove you visited—and that view progress
survives reconnects.

## What carried over from v0.4.6

The runtime experiment still settled the technical question that had stalled the feature: Elden Ring
accepts the DFLT-repacked atlases, both icon sheets load, and the Flower renders without runtime
texture injection. What changed after that result was delivery, not the image.

**Progressive Flask Upgrades stop doing two things at once.** Each copy used to nudge charges *and*
hand you a Sacred Tear, which made every upgrade two half-upgrades, neither of which felt like
anything. They alternate now: charge, potency, charge, potency, in that order, every time. The first
copy puts you at five total charges -- one above what a fresh character starts with -- so you can see
it land. The old ladder opened below the vanilla allocation, so the first upgrade or two were
invisible by construction.

The trade is that a copy is worth half what it was, so the ladder is twice as long. Seeds that inject
flask copies because they kept no Golden Seed or Sacred Tear check -- `dlc_only`, or a `num_regions`
seed that seals every flask region -- now inject 24 instead of 12, which is what it takes to max both
axes. Fewer than that and your potency honestly tops out below 12 instead of the ladder pretending
otherwise. Flasks never gate logic, so as before, either way the seed is winnable.

**Your filler is going to look different, and it is because the old numbers were lying.** A vanilla
lot holding one arrow was being promoted into the curated quiver's twenty; a lot holding twenty was
being flattened back to one. Both are fixed -- a curated bundle and a vanilla pickup are separate
items now, so each pays what it should. What that exposed is that the curated weights had been tuned
*against* the loss: `stones: 29` was paying for 288 smithing stone copies the world threw away before
you ever saw them. At the real quantities, five does the same job. The 24 points that frees go into
`juice` -- gear injection -- which climbs from 42 to 66.

So: fewer stone *entries*, the same stones in your hands, and noticeably more actual gear in the
filler pool. ⚠️ If you have hand-tuned `curated_filler` in your yaml, this is the release to re-read
your numbers, because the scale underneath them moved.

**There is a new trap, and it turns the lights off.** `Trap: Blackout` fades your screen out, holds
it dark for two seconds, and fades it back. It is the first of the eleven traps designed on
2026-08-08 to graduate from the probe list, and it graduated the only way anything gets into that
catalogue -- somebody confirmed it works in a real game. Add it to `traps` if you want it. A seed
that mints one asks your client whether it knows the name, so an older client is refused up front
rather than silently eating the item.

**The client got quieter about things it should not tell you, and louder about things it should.** A
pending boss sweep no longer publishes its member count, because that count is a map of which boss
pays best; the numbers come back the moment the sweep fires, when they are confirmation instead of
routing. An item that will not fit in your inventory is now retried instead of reported delivered and
dropped on the floor. DeathLink has an in-game toggle that lasts the session. And Leyndell's two-rune
seal reads both of the flags it actually checks, so a random start that skips the Roundtable sequence
cannot leave you standing at a gate holding the runes it wants.

**Smaller things you might notice.** Both ancestor altars light every urn when the catacomb-door
option opens them, instead of opening the warp while sixteen dark urns insist the encounters are
closed. Serpent-Hunter can no longer be hinted -- the client hands it to you at Rykard's arena, so
the server was charging you points to search for something that was never in the pool, and asking
now gets an explanation. And a seed with `enemy_scaling` off no longer demands a scaling feature from
your client that it has nothing to do with, which was producing a connect message that reported the
feature dark and then blamed a value that was right there.

**Armor sets stop eating a short seed alive.** One randomized item delivers the whole family,
altered pieces included, while reconnects fill only missing members. Exact duplicate weapons, both
trick mirrors, and Sacrificial Twigs stop consuming scarce pool slots too.

**Quest items can stay ordinary without locking their own quests.** Cursemark cannot land on
Fortissax, and direct prerequisite rules protect the Needle, Valkyrie, Fingerslayer, Favor, and Dark
Moon chains while leaving those items filler everywhere else.

**TrapLink is here when you ask for it.** ER traps can cross the multiworld; self-echoes and unknown
names are ignored, and DeathLink remains separate.

**The useful consumable tail got heavier.** DLC Hefty Pots, perfumes, and smaller throwable pots
arrive in useful quantities. Dragon Communion and Bayle altar checks cost one unit of their currency.

**Several missing-item reports were receive edges.** A permanent pot cap no longer jams all later
deliveries, death-edge checks stay queued until the server accepts them, and Leyndell's rune seal has
an independent cumulative backstop—including server `/send` and mid-seed upgrades.

## What carried into v0.4.8

**Ten changes that shipped in v0.4.6 had no changelog line, and they are written down in this
window's section instead.** Two of them matter enough to repeat here. Progressive stone bells were
granting the physical bell bearing alongside the shop-unlock flags, and since setting the flags *is*
the hand-in, the game refused the bearing as already handed in -- fixed 2026-08-17, findable as of
now. And the Moonlight Altar grace left Liurnia's bundle: it stands on Liurnia's tile but is reached
from Ainsel after Lake of Rot and Astel, so the Liurnia Lock was handing out a shortcut around the
route that owns it.

That is rule 14's own failure mode, and it was caught by an audit rather than by the gate.
`check_release_notes` asks whether the open version has a section; it never asks whether the section
accounts for the window's commits, which is why it stayed green through v0.4.6 at 13 entries for 28
merged PRs and this window at one for ten. Comparing merged PR numbers against the numbers cited in
the section, with an explicit allowlist for the deliberately internal ones, is the missing half --
tracked in #709, which filed exactly this for the client side of the v0.4.3 window.

🛑 And one thing is still owed, unchanged for four windows because it is not ours to write: **Elden
Ring Tarnished Edition ships 2026-08-28** and a paid content update moves the executable version.
v0.4.4 shipped the gate that explains that failure to a player instead of a Rust backtrace, but the
RVA table it reports against lives in a third-party crate, so the recovery is an upstream revision
plus a rebuild -- see #241. That is ten days out. It lands in this window.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option name. Its
opening line -- "You can get BK'ed now, and that is the point" -- says what a player will feel before
it says what was built, and that is the right order.
