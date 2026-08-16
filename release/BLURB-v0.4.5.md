# v0.4.5 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the only moment
anyone remembers why it mattered._

## What is in it so far

### You cannot walk into the ending early any more

Reach Radagon one Region Lock short and the game let you do it: you fought him, watched the ending,
took the credits, and then found out from a spoiler log that nothing had counted. Working as
designed, and a miserable way to spend the one part of a run you cannot repeat.

The Ashen Capital now opens when you hold everything the goal asked for, and not before. There is no
wall and no getting yanked out of the arena — the place simply is not reachable yet, the same way
every other region you have not unlocked is not reachable yet.

⚠️ One consequence worth knowing: a one-region seed on the plain region-locks goal is now refused
when you generate it, because your only Lock is the region you start in and there would be nothing
left to find. Ask for more regions, or set the goal to Great Runes and go get those instead.

### Rykard's Great Rune can finally be the one you need

If your goal is Great Runes, the runes it asked for were the alphabetically first ones — every seed,
forever. At the default of two that meant Godrick's and the Great Rune of the Unborn, and Rykard's,
last in the alphabet, could only ever be required by someone asking for all seven. A player reported
his Rykard's Great Rune sitting in the pool as junk on a Great Runes run and assumed it was bad luck.
It wasn't luck; it was the sort order.

The set is drawn properly now, so any rune can be the one you go looking for.

### And all seven are in every seed

Each Great Rune lives on one region's boss, so how many existed depended entirely on which regions
you drew. A three-region seed could hold exactly one — and if you'd asked for two, you got one
anyway, with nothing to tell you the number had moved. Your run was still winnable, just quietly
shorter than the one you set up.

Every seed has all seven now, whatever you drew. Ask for six and you get six. A rune turning up for a
demigod who isn't in your run is normal, not a glitch — it came from the multiworld, like everything
else does.

That also makes a Great Runes goal work under **DLC Only**, where it used to quietly turn into a
region-locks goal because no Great Rune boss stands in the Land of Shadow.

## What carried over from v0.4.4

Nothing is owed. v0.4.4 shipped complete -- both its changelog section and its blurb were finished
while the window was open, and `release/CHANNELS.tsv` promoted `stable` to it in the same commit that
opened this window rather than the morning after. The contract is unmoved at `5c2b9bf2`, the shape it
has had since 0.3.9, so a v0.4.4 client still handshakes with a v0.4.5 seed and no client half was
needed to open this.

🛑 One thing IS owed, and it is not ours to write: **Elden Ring Tarnished Edition ships 2026-08-28**
and a paid content update moves the executable version. v0.4.4 shipped the gate that explains that
failure to a player instead of showing them a Rust backtrace, but the RVA table it reports against
lives in a third-party crate. When the update lands, the recovery is an upstream revision plus a
rebuild -- see #241, and the client's `Cargo.toml` now pins the revision it shipped so the move can be
a deliberate one.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option name. Its
opening line -- "You can get BK'ed now, and that is the point" -- says what a player will feel before
it says what was built, and that is the right order.
