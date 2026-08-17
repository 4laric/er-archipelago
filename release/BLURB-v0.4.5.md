# v0.4.5 — release blurb

_Written as the window filled rather than at tag time: the moment a change lands is the only moment
anyone remembers why it mattered._

## The ending waits for you now

Reach Radagon one Region Lock short and the game let you walk in. You fought him, watched the ending,
took the credits — and then found out from a spoiler log that none of it had counted. Working as
designed, and a miserable way to spend the one part of a run you cannot do twice.

The goal region opens when you hold everything the goal asked for, and not before. There is no wall
and nothing yanks you out of the arena: the place simply is not reachable yet, the same way every
other region you have not unlocked is not reachable yet.

That covers **both** endings. If your goal is Consort Radahn, Enir Ilim is held back on the same
terms — it is a region the draw keeps, so its key used to be an ordinary find that could turn up in
your first hour.

⚠️ One consequence worth knowing before you generate: a **one-region seed on the plain region-locks
goal is refused now.** Your only Lock is the region you start in, so there would be nothing left to
find and the goal would be met the moment you connected. Ask for more regions, or set the goal to
Great Runes and go get those instead — generation names both ways out.

## Rykard's Great Rune can finally be the one you need

If your goal was Great Runes, the runes it asked for were the alphabetically first ones. Every seed,
forever. At the default of two that meant Godrick's and the Great Rune of the Unborn, and Rykard's —
last in the alphabet — could only ever be required by someone asking for all seven. A player reported
his Rykard's Great Rune sitting in the pool as junk on a Great Runes run and put it down to bad luck.
It wasn't luck. It was the sort order.

The set is drawn properly now, so any rune can be the one you go looking for. Still reproducible from
your seed — just not from the alphabet.

## And all seven are in every seed

Each Great Rune lives on one region's boss, so how many existed depended entirely on which regions
you drew. A three-region seed could hold exactly one — and if you had asked for two, you got one
anyway, with nothing to tell you the number had moved. Your run stayed winnable, just quietly shorter
than the one you set up. That is the kind of failure nobody notices.

Every seed has all seven now, whatever you drew. Ask for six and you get six. A rune turning up for a
demigod who is not in your run is normal rather than a glitch — it came from the multiworld, like
everything else does.

It also makes a Great Runes goal work under **DLC Only**, where it used to quietly turn into a
region-locks goal because no Great Rune boss stands in the Land of Shadow.

## Smaller things

**Vanilla Placement stops building a wall the base game never had.** The mode's promise is that the
game's own doors do the gating, but our synthetic two-rune capital wall was still arming on top —
and it could pick Morgott's rune, which drops *inside* Leyndell. The wall then gated the capital on a
key kept behind it, and the seed could not be finished. The game's own two-rune gate is untouched;
only ours stands down.

**Sweep slots can be priced by how big the boss was.** A payout off a legacy boss and one off a cave
boss are different bargains and were priced the same. There are separate major and minor sweep groups
now — off by default, so a seed that does not ask for them is unchanged.

## What carried over from v0.4.4

Nothing is owed. v0.4.4 shipped complete — both its changelog section and its blurb were finished
while the window was open, and `release/CHANNELS.tsv` promoted `stable` to it in the same commit that
opened this window rather than the morning after. The contract is unmoved at `5c2b9bf2`, the shape it
has had since 0.3.9, so a v0.4.4 client still handshakes with a v0.4.5 seed.

🛑 One thing IS owed, and it is not ours to write: **Elden Ring Tarnished Edition ships 2026-08-28**
and a paid content update moves the executable version. v0.4.4 shipped the gate that explains that
failure to a player instead of showing them a Rust backtrace, but the RVA table it reports against
lives in a third-party crate. When the update lands, the recovery is an upstream revision plus a
rebuild — see #241, and the client's `Cargo.toml` now pins the revision it shipped so the move can be
a deliberate one.
