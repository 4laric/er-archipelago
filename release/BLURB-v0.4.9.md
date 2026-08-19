# v0.4.9 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## What changed at the table

**The tracker got smaller, and what remains is more honest.** Boss sweeps are grouped by region now,
so thousands of checks no longer arrive as one permanently expanded wall; open the regions you care
about and leave the rest folded away. Unaudited sweeps still pay their ordinary checks, but cannot
host required progression until somebody has established which arena actually owns them. Older
multi-phase arena events now wait for their terminal flag instead of firing from an early phase while
the fight is still alive.

The data under those rows was cleaned up too, in both directions. The Golden Hippopotamus and
everything his death grants present as Scadu Altus, matching the arena the region guard actually
permits. Lansseax's Glaive is Altus at both of its real acquisition sites. And the phantom rows are
gone: 124 Rada Fruit rows that were bundle arithmetic or had no world object behind them, then --
once the world census reached every map instead of two-thirds of them -- 77 more of the same shape,
the "around some grace" Golden Rune rows in Siofra, Mohgwyn and the Shaded Castle that players have
combed for and never found. The four real Shadow Keep pickups, the witnessed Belurat/Enir-Ilim
corpses, and every row a script actually awards (evergaol drops, gated pickups) remain.

The same audits ran the other way and put real items INTO the pool. Seven merchant Bell Bearings
that were still dropping vanilla, Thops's staff, the Discarded Palace Key, Comet Azur, Stars of
Ruin, the Serpent Crest Shield, the Sacred Tower painting, Eleonora's Poleblade, and a run of fixed
pot and bottle pickups are now ordinary checks in their real regions. This was the useful residue
behind the misleading old "621 unplaced" count: the release carries a row-by-row audit of the
actual unique-item suspects, and leaves relocating-NPC, duplicate, cut, and dead rows out
deliberately instead of guessing a region for them.

**Starting items stop racing themselves.** Cokeman5's log caught both delivery paths active at once:
the paced reconciler had placed two of forty start entries, while the possession backfill interpreted
the other thirty-eight as missing and granted them too. The backfill now waits for the exact
start-item ledger frontier to drain. A readable inventory proves the bag can be inspected; it does
not prove another writer has finished.

**Two load-edge failures have concrete fixes, and the third has a better witness.** Static tables
such as `check_lots_table.json` and `shoplineup_flags.json` are resolved beside the AP DLL first,
which is where the release actually places them, rather than only beneath me3's global loader root.
Add-item and shop callbacks now refuse a param read after that table's holder has been emptied during
world teardown, and no remaining Rust panic is allowed to unwind through the game's callback frame.
The separate native crash inside me3's allocator is not being called fixed: crash reports now capture
all x64 registers, including the exact pointer me3 was handling, so its next reproduction can identify
the corrupt object instead of inviting a speculative feature shutdown.

**Fresh auto-equip characters get one left-hand slot.** Left 1 is the slot the challenge fills; Left
2 and Left 3 are emptied once when they came from the starting class. Existing saves keep the loadout
their player arranged. The live boss-HP probe is also off by default now that its audit has the
evidence it needed.

**Merchant bells and capital entrances say what they mean.** A Merchant Bell Bearing is removed from
the pool when every merchant who owns it lives in a sealed region. If a vanilla-only bell is handed
in anyway, the client explains that it opened vanilla inventory instead of looking like an empty AP
shop. Ashen Capital now opens at Leyndell, Capital of Ash; the duplicate Ashen East Capital Rampart
stays in the grace bundle without pretending to be the front door.

The packaged me3 profiles also name the package they actually ship. Stable bundles load the
authenticated `flower-package`, development bundles omit a package they do not contain, and the
packager refuses to publish a profile that points at a missing directory.

## Known before tag

**Direct Great Rune receipts still have a representation hole (clients#316).** Setting Radahn's
flags 172 and 192 does not make boss-drop goods row 8149 equippable: vanilla restoration also replaces
that row with restored goods row 192. Until the client performs that inventory conversion, the
in-client recovery for Radahn is:

```
!give 0x400000C0 1
!setflag 192 1
```

That adds the restored copy but cannot safely remove the devoid one. This note should be removed or
rewritten when clients#316 lands; flag-only restoration must not be described as fixed.

**A contained pickup panic can silently stop check reporting until restart (clients#306).** The new
panic containment is strictly better than crashing the game, but if a panic fires while the flag
bookkeeping locks are held, those locks stay poisoned: every later pickup is quietly passed through
to vanilla and nothing is sent to the server. No player has hit it yet; if checks stop registering
mid-session after a "contained panic" line in the log, restart the client and it recovers.

## What carried over from v0.4.8

No player-facing work is carried over. The two post-tag commits corrected the v0.4.8 release prose
and adjusted CI sharding/benchmarks; neither changed a seed or client at runtime.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
