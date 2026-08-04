# Changelog

The narrative — what this project is and what v0.2 brings — lives in
`RELEASE-NOTES-v0.2.md`. This file is the terse per-release delta.

## v0.3.4 — 2026-08-04

Window opened 2026-08-04 (rule 14), and opened LATE -- which is the first thing to record.
`v0.3.3` was tagged on 2026-08-03 while `APWORLD_VERSION` still read `0.3.3`, so three commits
landed on main writing their notes into a section that had already shipped. One of them was
player-visible and is moved down into this window below. `tools/check_release_notes.py` stayed
GREEN through all of it, because it asks whether the version named by `APWORLD_VERSION` has a
dated section -- never whether that version already went out. Rule 13 applies to the gate itself:
that blind spot is a to-do list until something checks it.

`CONTRACT_HASH` is unmoved from v0.3.0 (`5e8b11c9`), so the handshake is unchanged and seeds
rolled on 0.3.1+ still connect. The `data/` hash HAS moved, so a seed rolled here is not the seed
v0.3.3 rolled. The client moves only its version string, so an older DLL still connects -- but the
version it reports will not match what you are running, which is the whole point of rule 15.

### Fixed: 421 checks had lost their nearest Site of Grace to a join that could never match

`build_nearest_grace.py` kept its own copy of the overworld tile fold, and it disagreed with the one
the check browser and the desc-triage map use: it folded every tile at 256 m regardless of LOD, and
its pattern required a trailing `_`. Overworld coordinates are recorded in two id shapes -- 725 item
rows are three-field (`m60_34_50`) and every one of the 225 overworld grace rows is four-field -- so
the item side kept its raw map id as the join key while the grace side folded, and the two could
never meet. No distance was ever computed; the lookup returned empty first.

There is now one fold, in `tools/overworld_fold.py`, shared by all three consumers, and a test that
asserts they are the same object rather than merely agreeing.

Seventeen checks say something better to the player as a result -- thirteen move from a whole-map
"around X" to an exact "near X", three from a raw map id like `m60_42_50`, and one from a locale.
The other 404 recovered rows belong to checks that already had a better descriptor from an earlier
layer; they matter because other tools read the table.

Also fixed by the same change: eighteen checks were matching a grace 8.7-10.4 km away and being
discarded by the distance cap, which is why the grace-straddle screen reported "Altar South"
spanning four regions. They now land 30-356 m from a grace that makes sense.

**Not fixed:** the 134 checks whose descriptor is a bare map id. Zero of them have a coordinate at
all, so no join can reach them -- that half of the report needs the MSB datamine, not this.

### Changed: every Golden Seed and Sacred Tear now has a hand-written location

All 56 flags that award a Golden Seed (43) or a Sacred Tear (13) were walked in game and described
by hand. Before this, 43 of them were named after the nearest Site of Grace, 9 after a whole map
tile, one after a machine locale, and one after nothing at all -- so the tracker said things like
"Golden Seed - around War-Dead Catacombs" for an item that is a Putrid Tree-Spirit drop, and the two
seeds above Outer Wall Phantom Tree were distinguishable only by a "(1)"/"(2)" the generator appended
because it could not tell them apart. 50 hand descriptions land here; 48 of them move a name.

Nine of those checks also had their REGION confirmed on the same walk and are no longer hedged, so
they can host progression for the first time: three Altus seeds, one each in Caelid, Limgrave,
Liurnia and Mountaintops, and the Sacred Tears at Church of Irith, Second Church of Marika and
Stormcaller Church. They previously read "(region unconfirmed)" on screen and were barred from
carrying anything required.

Two checks were deliberately left alone. The Mohgwyn seed near Dynasty Mausoleum Midpoint keeps its
automatic name and is now barred from hosting progression -- Mohgwyn is reached by a one-way
teleport, so its route is awkward in a way the region model does not capture. The Golden Seed between
the Forbidden Lands and the Grand Lift of Rold stays hedged even though its region IS now known: it
sits on ground a Mountaintops-anchored player cannot reach without a Leyndell item, which is a
reachability problem rather than a region one.

## v0.3.3 — 2026-08-03

Window opened 2026-08-03 (rule 14: the note ships WITH the change, not with the tag).
`CONTRACT_HASH` is unmoved from v0.3.0, so the handshake is unchanged and seeds rolled on 0.3.1+
still connect — `region_locks.rs` regenerates byte-identical. The `data/` hash HAS moved, so a seed
rolled here is not the seed v0.3.2 rolled, and `APWORLD_VERSION` should move when this window is cut.

⚠️ **This window now carries CLIENT changes too**, so it needs a new DLL — the "no client work"
line above is about the CONTRACT, not about the build. (It read "the client needs no work" until the
auto_equip fixes landed underneath it. Corrected here rather than at tag time, which is the whole
point of rule 14.)

### Fixed: auto-equipped gear froze once every slot was full

`auto_equip`'s answer to a full loadout was *clobber the lowest slot*, in three separate places. That
is fine the first time and wrong every time after: the lowest slot becomes the only one that ever
changes again, and every other slot sticks on whatever happened to arrive early.

**Talismans (client #49, issue #342).** With all four slots filled, slots 2, 3 and 4 froze on the
2nd, 3rd and 4th talismans you were ever sent — for the rest of the run. The policy's own stated
rationale was *"a player who has never touched the menu ends up with the four most recent talismans
rather than one"*, which held during the fill and inverted the moment the slots were full, leaving
exactly one recent talisman and three stale ones. New talismans now walk the slots in turn.

**Physick tears (client #48, issue #334).** The same bug two slots wide, and the one that exposed it:
the 3rd tear took mixture slot A, and so did the 4th, so slot B froze on whatever arrived second.

The interesting part is why the talisman half was nearly ruled unfixable. The rotation has to survive
a reconnect — the reconciler replays your **whole** received item set every time you connect, so any
policy that is not a pure function of that replayed stream will silently rearrange your loadout
behind you. Tears alternate on the item's position in the received stream, which replays identically.
Talismans could not do the same, because the number of slots to rotate through *grows* from one to
four as you find Talisman Pouches, so the same stream was being divided by a different number live
than on replay. Measured across 329,760 timelines, that form fails to settle in 8.9% of them.

The fix is that the Talisman Pouch **is itself an Archipelago item**, so how many slots you had
earned at any point is readable from the stream rather than from live state. Same 329,760 timelines,
0 failures. The game's own slot count still bounds what may be written, so a slot you have not earned
can never be targeted; when the two disagree — a pouch sent but never granted — the client says so in
the log instead of silently papering over it.

🛑 **Confirmed by test, not yet on a screen.** The freeze is reproduced as a
failing-without-the-fix replay test in `er-logic`, and the whole client builds green. What no host
test can answer is whether the rotation *feels* right while playing; that is outstanding for both.

### Fixed: two overworld tiles were filed under the wrong region, one in each direction

Both tiles sit on the Limgrave/Caelid border, hold no site of grace of their own, and had their
region inferred from the nearest tile that does. In both cases the distance **tied** between a
Limgrave anchor and a Caelid one, and the tie was settled by the row order of an input table rather
than by any evidence. They fell opposite ways and both were wrong.

**m60_45_39 — Summonwater Village and the Third Church of Marika — was filed under Caelid.**
Twelve checks, the Tibia Mariner's own Deathroot, and the entire field sweep that fires when you
kill him. On a seed that does not keep Caelid none of it was ever created, so felling the boss did
nothing at all. Reported twice: once from a playtest, then again on 0.3.2 — *"killed the boss in
Summonwater Village, got no loot on a Limgrave seed."* He now pays out a 24-member Limgrave sweep.

**m60_47_38 — Fort Gael — was filed under Limgrave.** Fifteen checks, twelve of them named after
Caelid graces (Fort Gael North, Caelid Highway South, Astray from Caelid Highway North). Among them
Ash of War: Lion's Claw and the incantation Flame, Grant Me Strength.

Two "Smoldering Butterfly" checks east of Fort Gael belonged to no sweep at all — the only boss near
enough to grant them stood across the seam, and the sweep pass only assigns within a region. They
have one now.

**Also fixed by the Summonwater pin:** D, Hunter of the Dead stands at *two* points on that border,
and a merchant whose positions land in two different regions has his stock quarantined in the hub and
barred from carrying progression. Both his incantations — Litany of Proper Death and Order's Blade —
are ordinary Limgrave shop checks again.

🛑 **Two tiles is not the class.** The inference still guesses for 99 of the 231 overworld tiles that
hold checks, and still breaks ties by table order. Both of these were found by a player noticing,
not by a gate.

## v0.3.2 — 2026-08-03

A bugfix release, and mostly a client one. `CONTRACT_HASH` is unmoved from v0.3.0, so seeds rolled
on 0.3.1 still connect — but the client and the apworld must still match.

### Fixed: the id-keyed suppressor was eating vanilla items from every source

`detour.rs` sees only `raw_id` off the AddItemFunc buffer and cannot answer "where did this come
from?", so `checkItemFlags` suppressed a check's vanilla ware **by item id, from everywhere**. Goods
were taken off that mechanism in July by repointing each check's lot at the placeholder;
weapons/armour were left on it under the header note in `features/check_lots.py`:

> "a weapon is essentially never farmable, so it lives in the check-only set and cannot eat a
> legitimate source"

`enemy_drops.rs` refutes that in the client tree — 4891 enemy lots carry no flag (farmable) and its
reroll rewrites *"only the GOODS slots; weapon/armor/talisman drop slots keep their vanilla
contents."* So a farmable enemy can drop a vanilla weapon that backs a check, and every such copy was
eaten. This is the 2026-07-11 Golden Rune [1] incident surviving on the non-goods side.

Since `CAN_WRITE_SLOT_CATEGORY` was wired, non-goods check lots are repointed too — so for any item
id whose **every** backing check is lot-covered there is nothing left to suppress. Those ids are
dropped: **1289 armed ids -> 211**, including all 475 goods and 285 of 367 weapons. 13 partially
covered ids stay armed (`should_suppress` needs every mapped flag collected, so an uncovered backing
check still has something to protect) and 198 lot-less ones stay armed because an EMEVD award has no
source to neutralise.

🛑 **This is a cap, not a cure.** For those 211, a vanilla copy picked up *before* that check's award
fires is still withheld. Closing it needs a source discriminator the detour does not have (#321).

### Fixed: auto_equip never equipped a weapon when auto_upgrade was on

The receive loop queued the **pre**-upgrade FullID while `apply_auto_upgrade` put `base + N` in the
bag, and `auto_equip::tick` looks the queued id up by exact FullID. It missed, went back on
`still_pending`, and retried for the session. Protectors are identity under `apply_auto_upgrade`,
which is exactly the reported asymmetry — armour equipped, weapons never did. The upgrade now runs
inside `enqueue`, so there is one enqueue path and a future caller cannot reintroduce the mismatch.
(#296, #302, #303)

### Also

* Ammunition is no longer a held weapon, so bolts stop replacing your main hand (#294).
* Shields, staves, seals, bows and crossbows auto-equip to the **left** hand, per the French
  Challenge ruleset, instead of disarming you (#301).
* The Hefty Cracked Pot cap was 9 against a DLC that ships 10, so the tenth was reported delivered
  and never arrived (#308). There is no EMEVD threshold for it; the old cap was extrapolated from
  the base-game pots.
* Missing FMG entries are created rather than dropped, so items stop rendering as `?GoodsName?`
  (#300).
* A minimised window wrote 612,842 `[ERROR]` lines in one session; repeats collapse.
* The sealed-region kick names the region, the Lock that opens it, and why your vanilla key did not.
* Four more latched game-state writers re-arm on the in-world edge instead of lapsing after a warp.
* `important_locations` is deleted. It forced 256 checks to reject plain filler from **every** world
  in the multiworld, not just this one — it was frozen, unchosen, and taxing everyone else's fill.

### Gates

Rule 15 (a contract change forces a version change) now has a ledger and a gate. The multiworld
smoke asserts three slot_data properties a solo harness cannot pose — armed flags are collectable,
no flag is owned by two item ids, and two slots emit their own tables — and a `--self-test` proves
each of those guards can go red.

## v0.3.1 — 2026-08-02

A bugfix release. Every entry is a way a seed could quietly become unwinnable or trivially winnable
without saying so. `CONTRACT_HASH` is unmoved from v0.3.0.

### Fixed: the Lock lit a grace on the far side of the wall it was gating

For an ordinary region the "region is open" flag is *derived* to be the region's front-door grace
(`gen_data._front_door`), which is right — receiving the Lock should light the way in. For a region
behind a vanilla wall it is a bug, because the front door is **inside**: Leyndell's is East Capital
Rampart (71102), Raya Lucaria's is Church of the Cuckoo (71402), and the Sewer's is 73501.

`features/graces.py` already withheld those grace bundles while the wall was armed, and did so
correctly. But `core.py:968` shipped the same flag through `regionOpenFlags`, and the client's
`open_on_received_name` sets it directly — so receiving the Leyndell Lock lit East Capital Rampart as
a fast-travel target and you could warp in past the two-rune gate. That is the 2026-07-14
gated-children playtest bug ("walked straight in and ended the run at Morgott") returning through a
door the original fix never watched, with all four of its test folds green throughout.

One bit could not do both jobs — the same shape as the whetblade collision in v0.2.18. The kick latch
gets its own bit: `gen_data._GATED_CHILD_OPEN_FLAGS` pins Leyndell **76980**, Raya Lucaria Academy
**76981**, Sewer **76982**, and `region_open_flags.py` is re-emitted. `core.py` and
`features/area_locks.py` changed **zero lines** — fixing the generated table means all four world
consumers, the test corpus and the client's fallback generator inherit atomically, where a runtime
override would half-apply.

All three flags were probed in game before release: read-false, set, rest at a grace, Alt+F4,
relaunch, read-true — with the flag block's base pointer moving between runs (`24927E70080` ->
`2F1A6ED0080`), which is what proves the bits came off disk rather than surviving in memory. A
quit-to-menu is **not** sufficient for this class of test.

⚠️ **New seeds only.** A seed already rolled carries 71102/71402/73501 in its slot_data forever.

### Fixed: the capital's rune wall could be armed below vanilla's two

`generate_early` did `want = min(want, len(_available_runes()))`, on the theory that lowering a
requirement is always safe. It is not: our N is data-driven, the game's capital gate is a fixed
two-Great-Rune wall that does not clamp with us, and while our wall is armed `features/graces`
withholds the capital bundle so the physical gate is the only way in. At N=1 logic believes one rune
opens Leyndell, the game still wants two, and fill may place a region Lock behind a door the player
cannot open.

Two ways in with no warning: `num_regions` keeping exactly one Great-Rune region, or writing
`leyndell_runes_required: 1`, which the `Range(0, 6)` allows. An armed wall is now floored at
`VANILLA_CAPITAL_GATE_RUNES`; when the pool cannot supply two we **disarm** — empty bundle list, the
bundle is granted on the Lock, the player warps in past the physical gate — reusing the already-sound
N=0 path rather than arming low. No change on the shipped default.

Settled while chasing it: the capital gate reads no possession at all. It counts a band —
`CountEventFlags(EventFlag, 190, 199) >= threshold` in common `$Event(720)` — and 191-196 are set by
the Divine-Tower altar initializers through common event `90005110`, which removes the unrestored
rune (goods 8148-8153) and awards the restored lot. So the restored-goods ids and the restored-flag
ids genuinely coincide, that resemblance is FromSoft's parallel numbering rather than our error, and
`keyitems.rs` has been writing the right flags all along. Six rows classified obtained_flag/datamine;
the unknown ceiling drops 25 -> 19. The band is pinned in the test, because a stray flag outside
190-199 would be silently uncounted — the one way this can rot with nothing failing.

### Fixed: legacy boss kills paid out in the wrong region

`_lreg` had two silent failure modes, both found by pulling on **Alaric**'s observation that "Ashen
capital should have 3 bosses: Gideon, Godfrey/Hoarah Loux, Radagon/Elden Beast" and it had none.

- **A tie broken by `Counter` insertion order.** `m11_05` votes {Leyndell 3, Ashen Capital 3,
  Limgrave 1}; `m19_00` votes {Leyndell 1, Liurnia 1}. Nothing decided Leyndell — `most_common()`
  did. Consequence: 42 of Leyndell's 64 divvied checks hung off the four post-burn triggers, and the
  Erdtree burn warps you into `m11_05` **permanently**, so those grants could never fire from base
  Leyndell. Dead on arrival.
- **`or HUB` swallowed the no-vote case.** `m12_04` (Astel), `m12_08` (Ancestor Spirit) and `m12_09`
  (Regal Ancestor Spirit) get no `_mreg` vote at all, so all three paid out **Roundtable Hold** — 13
  checks in a region open from turn one, for kills in the Eternal Cities.
  `boss_data.REGION_BOSSES["Roundtable Hold"]` is `None`; the hub has no bosses and never did.

The curated pin was also consulted *after* the vote, so it could only rescue a map with no votes. The
pin now beats the vote, and `or HUB` is deleted in favour of a generation-time assert naming every
unrouted map. Roundtable Hold 13 swept checks -> **0**; Ashen Capital 0 -> **3**; corpus 3197 ->
3187; cross-region leak 0 before and after. Triggers 241 -> 240, because the Ashen Capital's 3 checks
across 4 triggers leave Radagon (`19000810`) an empty slice — harmless, since Radagon and the Elden
Beast are one fight and `19000800` carries it, but it is why `SWEEP_REGION` is not a boss roster.

Every region came from committed tables — `dungeon_regions.tsv`'s grace join, `check_maps.tsv`, and
each boss's own drop region — not from memory of the game. `boss_data` already disagreed with
`boss_sweeps` in both cases; that disagreement *was* the bug report.

### Fixed: no somber smithing stone tier had a presence floor

`_draw_stones` did `if somber: return out` immediately after the weighted draw and **before** the
deepest-first top-up, so the guarantee that module advertises was regular-Smithing-Stone-[1]-only.
The draw is an i.i.d. weighted sample with replacement, so at `num_regions: 1` (~19 draws, taper
share 1/9 for the deepest tier) the per-seed probability a tier is simply absent measures **[3] ~6%,
[8] ~42%, [9] ~73%**.

A somber weapon costs one stone per level and the tier *is* the level, so an absent tier is not a
thin economy — it is a permanent wall at that exact rung. Tiers 1-9 are now each guaranteed present,
paid for by converting the deepest **surplus** stones already drawn (a tier never donates its last
copy); the reservation is never grown. Stones already on kept locations count toward the floor, so
the guarantee does not spend a slot covering a tier the seed has. Below 9 donors the floor covers the
shallowest tiers first and warns by name with the level a somber weapon cannot pass.

Reported by **Lonelyguy89** on a 1-region seed: "zero Somber Smithing Stone [3] in the game."

Note `fuzz_gf.py` skips `curated_filler` ("no finite domain"), so the fuzz gate never varied the
`somber_stones` weight and could not have found this.

### Fixed: a boss below the Grand Lift of Rold could hold progression

`f530505`, Gargoyle's Black Blades — the Black Blade Kindred below the lift — is filed "Mountaintops
of the Giants" and was progression-eligible. Rold is deliberately not in logic (README: "You never
need the Rold Medallion to reach the Mountaintops of the Giants"), so a Mountaintops-anchored player
cannot stand on that ground: the Rold Medallion is a **Leyndell** check. Fill was free to put a
region Lock or a required Great Rune there. The seed is unwinnable; the character is not, since the
Roundtable warp always works.

The class, not the instance. Two derivations produce a region from a tile and the bar watched one:
`_mtile`, the descriptor tile, and `MSB_TRUTH_MAP`, which `region_of()` ranks **above** it and which
actually produced the region for 2467 of 4875 checks. f530505's descriptor tile `m60_39_53` is
anchored, so the guard waved it through, while the tile that produced its region — MSB `m60_49_52` —
is graceless Forbidden-Lands ground nearest-neighbouring onto the `m60_49_53` seam that carries
graces for **both** regions. Two checks on that same ground were already barred and the boss check
was not.

`region_of()` now records `MSB_TILE_PROVENANCE` — only flags whose region it actually *answered*
through an MSB tile — and the bar judges both tiles. **Union, not precedence, and that is measured:**
judging the MSB tile *instead* would un-bar two checks barred today (f520300 Viridian Amber
Medallion, f400299 Bernahl's Bell Bearing, whose tiles disagree about which side of the map they are
on). `DEFAULTED_REGION_APS` 504 -> **515** of 4875: +11 barred, 0 un-barred, across Mountaintops (5),
Caelid (4), Altus (1) and Mt. Gelmir (1). No key item, Great Rune, medallion or Seedtree is in the
set.

Reported by **Lonelyguy89** on a 2-region seed, softlocked in the Forbidden Lands with the medallion
in Leyndell.

⚠️ **Known cosmetic residue:** for 13 checks the descriptor tile and the MSB tile disagree, and the
descriptor still wins the *name* while MSB wins the region — so f530505 reads "Mountaintops of the
Giants :: Gargoyle's Black Blades - around Bridge of Iniquity", and Bridge of Iniquity is Mt. Gelmir.
The region is safe either way (all 13 are barred); only the label is wrong.

### Fixed (client): an equipped Great Rune was re-granted forever

`inventory_has_goods` decided possession by walking the three inventory backing lists. An equipped
Great Rune is not in any of them — the game holds it in `equipment.equip_item_data.great_rune` — so
the readback reported absent, the reconciler re-granted, the game refused because you *do* have it,
and the refusal is a modal popup that reappears the instant you close it.

Possession is now **the three bag lists ∪ the great-rune equip slot ∪ the storage box**. The handle
is resolved off the pinned crate source rather than guessed: goods are never `is_indexed`, so the
gaitem table is a dead end and `selector()` carries the bare param row, guarded on
`GaitemCategory::Goods` (3 — a different enum from the `ItemCategory::Goods` (4) the bag walk uses).

Honest framing: the underlying mechanism is still unconfirmed in game. This makes the readback
strictly more permissive — it can suppress a wrongly-repeated grant, never cause one — so if the true
cause is elsewhere it masks rather than fixes, and the forensics line that would identify it is kept
deliberately. The `MAX_GRANT_ATTEMPTS = 3` guard from v0.2.17 remains the backstop, so even an
unfixed cause degrades to three popups rather than a wall.

⚠️ **An item in your storage box now counts as owned and will not be re-delivered.** Withdraw it and
lose it and the next tick delivers it again, as before.

### New: `auto_equip` — wear whatever you are sent

Off by default. Turn it on and every weapon or armour piece the multiworld hands you is put on the
moment it lands in your bag, replacing whatever was in that slot — mid-boss-fight included, and
regardless of whether your build can use it. You do not pick your kit; the item order does. This is
the "use what you get" challenge format (the French Challenge run: Wretch start, randomizer,
use-what-you-get, permadeath), and with the region locks and goal this apworld already ships, it is
now a setting rather than a stack of third-party helpers.

⚠️ **The client has had this working for weeks and nobody could use it.** `auto_equip.rs` reads
`slot_data["options"]["auto_equip"]`, and the apworld had never sent that key — an absent key parses
as `false`, so the feature was off for every Elden Ring seed ever generated, silently. This release
is the apworld half.

**A seed with `auto_equip: true` requires a client that supports it and will refuse to connect to
one that does not**, naming the feature. That refusal is deliberate: adding an option does not move
`CONTRACT_HASH`, so without it an older client would report `VERSION: OK`, never see the key, and
run your seed with the setting quietly ignored — exactly the failure above, one release later.
Leave it off and nothing changes; any client still connects.

**Validation, stated plainly.** The memory mechanism is verified, and verified thoroughly: on a live
game with Cheat Engine, writing all four representations Elden Ring keeps for an equipped item
equips it, renders it correctly in the equipment menu, and survives being unequipped by hand — on a
character that had never held the item. That is the half that could have silently destroyed your
gear. A naive handle write never acquires the refcount, so the next menu unequip drops it to zero
and the item disappears from your inventory an interaction later, far from the cause; going through
the game's own refcounted commit is what avoids that, and it was proven before a line of the
shipping code was written.

🛑 **What has NOT had a full playtest is the mod's decision-making on top of that mechanism** — the
probe is told which slot and which item, and the client works both out for itself. Untested in a
real run: weapon-versus-armour routing, shields (they should go to the left hand and that is
explicitly unconfirmed), what happens when gear arrives mid-fight, the retry when an item is
received before the game has finished granting it, and whether an auto-equipped item survives a
save-and-reload. Default is off. If you turn it on, treat it as new — and not on a character you
would mind losing.

### Fixed: two Golden Seeds pointed at the wrong grace, and two more said "region unconfirmed"

From a live playtest (Alaric, in game, 2026-08-02).

A Liurnia Golden Seed read *"near Academy Gate Town"*. That grace is **872 m** away and 27th-nearest;
a player following the descriptor walks to the wrong end of the lake. It now reads **"near Main
Academy Gate"** (184 m). The nearest grace in raw 3D is actually East Gate Bridge Trestle at 86 m --
but 75 m straight down at lake level, while the seed sits up on the raised causeway, so the closest
answer is the one you cannot walk to. A second Liurnia Golden Seed now reads **"near Academy Gate
Town"** instead of "near Fallen Ruins of the Lake": the Fallen Ruins grace is 47 m closer on the tape
measure and the Gate Town is the landmark you actually navigate by. Someone walked both.

Two checks also stop hedging. `Weeping :: Golden Seed - near Castle Morne Rampart` and the Liurnia
seed above were labelled **(region unconfirmed)** and barred from *hosting* progression, because
their region came from a tile-neighbour vote rather than from ground anyone had seen. Both were
collected in game this session, in the region we had guessed. The hedge costs twice when it is wrong
-- the name tells you we do not know something we do, and the progression surface stays smaller than
the map -- so the label is gone and each is an ordinary progression-eligible check again. This is the
mirror of v0.3.0's "two Liurnia checks can no longer be required": the same list, run the other
direction, and only ever per check, never per tile.

### Compatibility

`CONTRACT_HASH` is **unmoved** from v0.3.0 — 87 keys, identical names, shapes, required-ness and
profiles — so a v0.3.0 client and a v0.3.1 apworld still handshake.

The one exception is a seed that turns `auto_equip` on: that seed declares the feature in
`requiresClientFeatures` and needs a v0.3.1 client. A seed that leaves it off (the default) declares
nothing and is unaffected.

⚠️ **Client update recommended.** The re-grant fix is client-side and an old client connects happily
without it.

No option changed its default or its meaning, and nothing here moves an item or a check in a seed
already in progress. A v0.3.0 yaml generates a v0.3.1 seed with no edits. The gated-child, somber,
Rold-seam and descriptor / region-confirmation fixes are all generation-time and reach **new seeds
only**.

## v0.3.0 — 2026-08-01

**Client update required.** The slot_data contract moved from `d970dd88` to `5e8b11c9`
(`goalRequiredItems` and `scaduBlessingCap` were added). A v0.2.x DLL will report a version
mismatch against a v0.3.0 apworld, and it is right to: it cannot enforce the new goal condition.
Ship the apworld and the DLL together.

**Two defaults changed and they change what an old yaml does.** See "Migration" at the end of this
entry before you reuse a v0.2 yaml.

### New: a `goal` option

`goal` picks what ends the run — `auto`, `elden_beast`, or `promised_consort`. A *named* goal
force-keeps its own region, so you can no longer roll a seed whose ending is not in the seed.
`auto` is the previous behaviour and is rng-stream-identical to v0.2.19; an impossible combination
now raises an `OptionError` at generation time instead of producing an unwinnable seed.

### New: the Scadutree Blessing is finally game-wide

Both shipped blessing modes were **inert outside the DLC for their entire life** — the blessing rung
only ever applied inside the Shadow Realm. The client now clones the rung onto `SpEffectParam` row
`20012081`, which the base game reads too. The curve is capped at **12**, and the option is
`global_scadutree_blessing`, which until now could not be set from a yaml at all (the class default
was frozen). Default is still off.

### New: Scadutree Fragments are actually put in the pool

The blessing cap exists to bound an *injection* — and the injection had never been built. Until now
the only mention of the fragment curve anywhere in generation was inside the comment explaining the
cap, so the ceiling sat over a supply that arrived purely by luck of the DLC draw. Measured across
40 seeds a row on the shipped default of six regions: **one seed in forty** could reach the cap.
Fragments are now injected to meet it, and a DLC seed injects none because it already has them.

### New: a region unlocking says so on screen

Receiving a Region Lock — the most consequential item in the seed — produced nothing in game. The
line existed, but only in the AP console. There is now a toast, and it announces the *effect*
rather than the receipt: "Region unlocked: Liurnia", not "you received Liurnia Lock", which is a
receipt you have to translate. It reuses the console line's exact wording so there is one phrasing
to learn.

One deliberate gap: AP replays your entire received stream when you connect, so the first pass
after connecting cannot tell a real arrival from a replay. A lock that lands in that window is
logged but not toasted. Silence there beats six false toasts every time you reconnect.

### New: region-lock hints you can afford

Hint pricing was denominated over the whole location table, which made a region lock cost more than
anyone accumulates. It is now denominated over the ~158-check progression surface and tracks the
host's own `hint_cost`, with a ledger in AP data storage so a hint bought once stays bought across a
reconnect. There is a tracker button for it.

### The client repairs your save after a crash

Archipelago and Elden Ring disagree about whether the past can change. A check, once sent, is on the
server forever. A save can move backwards — Alt-F4, a crash, a restored backup. Left alone that
combination is pure loss: the checks stay spent and whatever they gave you is gone, silently.

The reconnect record lives *inside* the save, so it rewinds with it. On reconnect the client
compares what the save remembers against what the server already delivered and re-delivers the
difference — items and world state both, so a region that had opened re-opens.

Verified in the field on 2026-08-01: a hard Alt-F4 seconds after three pickups came back to a save
25 seconds behind where it was left. All three items were re-delivered on reconnect. Picking the
locations up again gives the ordinary item and does **not** send the check twice or grant a second
copy.

Two honest limits. It only restores what Archipelago delivered — runes, ordinary pickups, boss
progress and your position still go back with the save. And it is not a licence to save-scum: the
checks you already sent stay sent.

### Fixed: the crash on fast travel

Instrumented across six crashes from one player's session, all six faulted **8 bytes below** our FMG
block — the allocator header of a 64 KB-aligned `VirtualAlloc` region that was never mapped, because
`VirtualAlloc` rounds a reservation to the allocation granularity and we had asked for exactly the
payload. Six hits, zero misses, one allocation site. The block is now padded by a page.

### Fixed: reconnecting to a different room leaked 229 checks into it

The seed-marker guard was asked once, at connect, and never again. Change rooms mid-session and the
client kept sending the previous seed's checks — 229 of them, measured. The guard is now re-asked
mid-session and fails closed.

### Fixed: a REFUSED session looked identical to a working one

When the client refused to attach it did so silently. A player spent 55 minutes assuming the mod was
broken. REFUSED now raises a toast that says so.

### Fixed: the goal could fire two regions in

Completion was inferred from boss flags alone, so on a rolled seed the goal region could be the
*second* region you reach — measured at **25% of seeds**. The kept Region Locks must now be held
before Goal is sent.

### Fixed: two toast defects

An em-dash rendered as `?` in-game (the FMG path is ASCII-only; there is now a test that says so),
and the scaling-tier fraction described the vanilla ladder rather than the seed's own band. The
region-scaling toast also gained a production caller — the strings shipped in v0.2.18 with none.

### Fixed: items could stop arriving forever, and nothing said so

Reported on v0.2.18: a multiworld's room changed port, the client reconnected cleanly and kept
*sending* checks — and never received another item again, from anyone, including itself. A fresh
character got no starting lock either, and reinstalling changed nothing.

The client decides who delivers an item from *configuration*, then stands down so the two grant
paths can't both fire. It never checked whether the owner it stood down for actually existed. If
the reconciler never armed — which happens when the inventory pointer is never captured, and
another mod hooking the game's item-pickup function will do exactly that — the client skipped its
own grant, skipped the guard that holds the cursor on a failed placement, advanced the
received-item cursor anyway, and wrote that to disk. Every item after that point was consumed
silently and permanently.

Ownership now requires an armed, un-refused reconciler. Anything else falls back to the old grant
path, which holds its cursor and retries, so the failure mode is a stall you can see instead of a
loss you can't. Two supporting changes: a session that is not going to deliver now says so on
screen rather than looking healthy, and the log carries a single `[reattach]` block stating every
fact behind the decision — identity, marker verdict, both cursors, armed, refused, inventory.

### Fixed: skipping the opening cutscene made you confirm every map

If you sat through the opening cutscene your maps appeared silently. If you skipped it, you had to
click OK on every single map the first time you opened the map screen. One player had learned to
wait in the cutscene until the item ticker moved.

Map reveals are event flags, and they were gated behind an eight-second settle timer. That timer
exists to distrust the *inventory pointer* after a save load. Flags never touch the inventory. The
timer was landing them after you regained control, and the game announces a map revealed while you
hold control. Flags now apply on the first in-world tick; item grants keep the settle, which is
what it was written for. Map reveals that arrive mid-run — from a region lock — still prompt.

### Fixed: a new character on a used save slot got no starting items

"Start items already granted" was stored per seed and slot, with nothing in the key identifying the
character. Roll a new character into a slot you had played and it inherited "already granted" and
started with nothing.

The client now decides by **possession**: it grants whatever is not in your bag. That is
per-character for free, because the bag is, and it cannot go stale the way the old flag did — it
also survives a reload, and re-delivers a start item that a save load wiped. This works because
every start item is durable (flasks, pot vessels, lantern, whetblades); a test now enforces that,
so a consumable can't be added to that path and silently refill every launch.

### Fixed: the start-item backfill reported items it never delivered

The backstop that grants missing start items was measured in one session declaring 32 of 35 absent
off a scan that saw only 17 items, hard-failing 10 of them, quietly capping about 18 to zero and
recording those as delivered. Its summary line claimed 22 of 32 granted. None of those numbers were
true.

Two causes, each correct somewhere else. A pot grant that hits the delivery cap reports success —
right for the item ledger, since the item is as delivered as it will ever be, and wrong for anything
checking the bag. And the scan could run against an inventory that was still filling, so items you
were holding read as missing. It now never reports an item delivered unless a later scan actually
sees it, waits for two consecutive matching scans before trusting one, keeps retrying until nothing
is missing, and names the exact items in the log if it genuinely cannot deliver them.

### Fixed: the game-wide blessing switched itself off when you used it

The blessing level was read by counting Scadutree Fragments **in your bag**. Revering at a DLC grace
consumes them. So a player using the blessing the way the game intends drained their held count to
zero, the derived level collapsed with it, and the game-wide blessing turned itself off mid-run —
and nothing clamped it to raise-only, so the applied rung genuinely fell.

It is now driven by fragments *received*, which AP replays in full on every connect, so the count
survives reconnects, save loads, and anything the game does to your inventory. Matched by item id
rather than name, so a foreign apworld that calls its fragments something else still counts.

### Fixed: quitting with Alt-F4 was reported as a crash

Elden Ring executes a breakpoint instruction on its Alt-F4 teardown path. With no debugger attached
nothing handles it, so it reached the crash handler and was written out as a native CTD, complete
with a backtrace at a stable address. In one playtest log that made **five ordinary sessions look
like four crashes** and produced a confident wrong verdict about an open crash bug. Breakpoints are
now classified separately. The record is still written — a breakpoint inside our own DLL still
matters — only the "process dying" banner is gone.

### Fixed: a crash during generation was reported as a hang

Stock `Generate.py` ends by waiting on "Press enter to close". A generation that *crashed* then sat
on inherited stdin until the tooling timed out, so a real failure surfaced as a 900-second hang with
no diagnosis. Every invoker now closes stdin, and the set of invokers is derived rather than
maintained by hand — the original audit found five by reading twelve files, and a hand-kept list
goes stale silently on the sixth.

### Fixed: two Liurnia checks can no longer be required

Two checks were barred from *hosting* progression on suspicion: a Sacred Tear "around Ruin-Strewn
Precipice" and a Golden Seed "near East Gate Bridge Trestle". The Sacred Tear is our
lowest-confidence placement of the thirteen on three independent signals, and it could not be found
in game at the named grace. The checks themselves are real and stay collectable; only their ability
to hold something you *need* is removed. Being wrong this way costs a filler item somewhere
awkward; being wrong the other way strands a run. The Pilgrimage tear was also re-regioned.

### Also fixed

- A death-cam crash guard was present at four of **five** sites — the fifth walked the player's
  effect list every frame while the engine was tearing it down, which is a native crash. All five
  now call one implementation.
- Region-scaling telemetry read the raw difficulty option rather than the seed's own band, so every
  default seed logged a flat curve in the client log.

### Migration — read this before reusing a v0.2 yaml

- 🛑 **`num_regions` now defaults to 6, not 0.** A yaml that omits `num_regions` used to roll the
  full 30-region spine; it now rolls a **6-region seed**. If you want the whole map, say
  `num_regions: 0` explicitly.
- 🛑 **`num_regions_order` now defaults to `rolled`, not the spine.** Omitting it gives you a random
  start region rather than Limgrave.
- The three shipped presets were re-derived against the new defaults; two of the five were silently
  reinterpreted by the flip and are corrected here.
- The unused top-level `global_scadutree_blessing` slot_data key was removed. Nothing read it.
- No option was renamed or removed. A seed generated on v0.2.19 and already in progress is
  unaffected: the absent `goalRequiredItems` key reads as an empty requirement, exactly as before.
- The client's save file no longer records "start items already granted"; possession replaces it.
  A v0.2 file is read normally and the stale key is ignored, so there is nothing to delete.

## v0.2.18 — 2026-07-30

### Fixed: a shop row priced below the item's own value was dropped from the menu

Elden Ring excludes a `ShopLineupParam` row whose `value` is under the ware's `sellValue`. Money
runes hit that **by construction** — a rune's `sellValue` equals its payout, and the price roll is
`[0, worth]` — so every rune priced as a bargain, which is the entire point of the feature, made
itself invisible. Never rune-specific: a stray Veteran's Helm discounted below its sell value
vanished the same way.

Fixed by **lowering the ware's `sellValue`**, not raising the row's price. Raising it renders the row
and destroys the feature (a rune could never again be a bargain). On a rune `sellValue` is redundant
data — the payout is read from `SpEffectParam.soul`, verified across all 35 rune rows — so lowering
it costs nothing. Sell-back is capped just under what you paid, so there is no money pump; other
merchants selling the same ware keep their own prices.

`ER_SHOP_VALUE_CLAMP=raise` restores the old behaviour with no rebuild.

Reported three times by **Alaric**; the third report is what ended the wrong explanation.

### Fixed: money-rune pricing missed every DLC rune

Rune-ness was an anchored name whitelist — `Golden`, `Hero's`, `Lord's`, `Numen's`. It matched all 21
base-game money runes and **none of the 11 DLC ones** (Shadow Realm [1]-[7], Rune of an Unsung Hero,
Marika's, Leda's, Broken Rune). A miss was not a skip: an unmatched rune fell through to the generic
price path, which for a rune is `sellValue * 10` — *exactly* the 10x bug the code existed to remove,
re-introduced on every DLC rune through two prior "fixed" releases.

Rune-ness now derives from `RUNE_PAYOUT` (`EquipParamGoods.refId_default -> SpEffectParam.soul`), so
a future DLC needs no edit. The retired regex survives as a cross-check in the tests: everything it
used to match must still be priced.

### Fixed: the infinite shop shelves were pointed at menus, not shelves

`reroll_infinite_shop_stock` selected on `eventFlag_forStock == 0` — the exact **inverse** of what
marks a shop check, which reads as "rows that can never be checks" and is not. It collected 455 rows
belonging to the Alter-Garments menu, the Ash-of-War duplication menu and debug entries. No player
can browse those, so the reroll changed nothing buyable and corrupted the menus it did touch.

The predicate now derives a browsable shelf from what one is (real `equipId`, no material cost, no
release gate, unlimited quantity, `eventFlag_forStock > 0`). **Fourteen rows qualify** — Kalé's glass
shards, Iji's somber smithing stones, the throwing-knife and poison-dart racks and their neighbours.
Ammo shelves stay excluded deliberately.

### Fixed: receiving a whetblade collected its own location

Each whetblade unlocks several Ash-of-War affinities and the game tracks them one flag apiece (Iron:
Heavy 65610, Keen 65620, Quality 65630). The **first** affinity's flag is also the lot's
`getItemFlagId` — this world's check flag for that location. One flag, two jobs. The client set it to
unlock the affinity, which simultaneously marked the location found and despawned its treasure: the
item placed there went out as though you had found it, and the chest stopped spawning.

Not fixable by choosing a side — skipping the flag costs an affinity instead. The two jobs are split:
the affinity keeps the vanilla flag, and the check moves to a client-owned adjacent flag
(65611/65641/65661/65681/65721 — same allocated block, unreferenced across the EMEVD corpus,
`flag_lots`, `check_maps`, `region_map` and `esd_flags`). The lot repoint and the poll repoint come
from one table, so writer and watcher cannot drift.

Ground truth for the per-affinity flag map came from the Hexinton CE table. **A whetblade received on
an earlier build already collected its location; that is recorded server-side and cannot be undone.**

Bell Bearing / Whetstone Knife / Rold Medallion / Drawing-Room Key share the collision but have no
lot to repoint (their flags are ESD/EMEVD-set), so their false-collect stands — tracked separately.

### `maximum_enemy_difficulty` defaults to `auto`

Enemy scaling targets a region's **position in your unlock order**, normalised so the deepest kept
region tops out. Right for a long seed, wrong for a short one: with five regions the deepest is
reached quickly and still scaled as "the end of the run", while weapon upgrades sit on a fixed
ladder a short seed does not accelerate — endgame enemies on mid-game gear.

`auto` lowers the ceiling with the length of the run, `pct = round(100 * (n/30) ** (1/3))`, resolved
in **ladder-index space** (multiplier space resolves down a rung and silently changes nothing):

| regions | ceiling |
|---|---|
| 5 | 4.125x |
| 8 | 5.484x |
| 12 | 6.688x |
| 30 / `num_regions: 0` | 7.422x — unchanged |

⚠️ **Behaviour change by default.** Set `maximum_enemy_difficulty: 100` for the old uncapped curve.
Only ~3.7x at five regions has been played; everything above is extrapolation, and the option
docstring says so.

Prompted by **Alaric**'s Patches fight and **CrazzyMatthew21**'s "unclear at which points im supposed
to be in which areas".

### New: `infinite_hub_wares`

Name up to four items the hub merchant always stocks, unlimited:

    infinite_hub_wares: ["Rune Arc", "Larval Tear"]

Four is how many browsable unlimited shelves the hub has; a fifth is rejected at generation with a
message. Each ware sells at its own derived price. Empty by default. Worth a thought before filling:
unlimited Larval Tears is unlimited respec, unlimited Rune Arcs a permanent great-rune buff.

### New: `no_runes_in_shops`

Keeps your own money runes off every shop check and out of the rerolled shelves. Off by default.
Scoped by `SHOP_ROW_FLAGS` membership (561 rows), not by tag; rune-ness from `RUNE_PAYOUT`, so all 31
catalog money runes are covered including every DLC one. Great Runes are not in `RUNE_PAYOUT`, so no
progression item is ever forbidden. Skips enforcement with a logged reason rather than risking a
`FillError` if the pool cannot supply.

### Gems, weapons and armour sell again

Gems sell natively (135 vanilla `equipType 4` rows support it). The floor deciding what was sellable
had been goods-only, so weapons and armour read as worthless.

### Stability

Three guards, two of them generalising fixes that previously covered a single caller each — patching
the instance and leaving the mechanism is what put the same crash in front of players more than once.

- **The inventory pointer is retired at warp REQUEST**, not only on arrival. A warp tears the origin
  map down first and `in_world()` still reads true through it, so grants ran against memory the
  engine was freeing. The static-slot primer is held 3000 ms so it cannot recapture the dying object.
- **Enemy scaling stops during the death-cam.** Three other features already skip work while
  `hp <= 0` because mutating those structures mid-teardown crashes; the scaling sweep touches the
  same structures on every enemy in the area and had no such check.
- **Event-flag writes are bounded like item grants.** A flag the game silently discards was rewritten
  every frame forever (unpaced, ~60/s); it now parks after three unobservable attempts and says so.
  A flag vanilla merely **contests** reads back fine and is never parked, so nothing legitimate stops
  being re-asserted.

Also: the overlay title now shows the build SHA. `0.2.17` named two different client builds — the
version bump landed before the grant-guard fix — so "I'm on the new version" was true and useless.
Start-of-run Perfume Bottles and Hefty Cracked Pots asked for 10 where the delivery cap is 9; the
tenth silently vanished, and a capped pot grant now warns once instead of reporting success.

### Compatibility

`CONTRACT_HASH` is unmoved (`d970dd88`), so a v0.2.17 apworld and a v0.2.18 client still handshake.
⚠️ **Client update required** — most of the above is client-side, and an old client connects happily
without any of it. Confirm with the overlay title or the `ER-AP client` line in the log.

## v0.2.17 — 2026-07-29

### How much of a region an unlock opens

`region_grace_unlock` decides how many Sites of Grace a region unlock lights.

| value | what it lights | total across the map |
|---|---|---|
| `all` (default) | every warp point in the region — Liurnia is 59 at once | 338 |
| `landmarks` | one per sub-area, using the warp menu's own grouping | 47 |
| `entrance` | the region's front door only | 27 |

`landmarks` resolves Liurnia to Lake-Facing Cliffs, East Raya Lucaria Gate, Moonlight Altar and
Ruin-Strewn Precipice — its four real chunks. The partition is the **game's own**
(`BonfireWarpParam.bonfireSubCategoryId`), not a hand list, so it is uneven on purpose: a few
regions (Gravesite, Scadu Altus, Weeping) have a single sub-area and behave the same as `entrance`.

Nothing here can strand you or move an item. Region unlocks are still the only progression, every
check stays where it was, and a grace you were not handed is still reachable on foot and still
unlocks by touching it. Regions behind a wall the game itself enforces — the Academy seal, the
capital's Great Rune gate, the sewer — hand out nothing under any value.

Requested by **dafranky67**.

### Fixed: the tutorial Grafted Scion paid out 36 Stormveil checks

The game buckets `m10_01` — the ruined Chapel of Anticipation intro — under Stormveil, so the
generator counted the intro Grafted Scion as one of Stormveil's legacy bosses and handed it a
round-robin slice of the region's sweep pool. Killing an optional tutorial boss in the first few
minutes therefore paid out three dozen Stormveil Castle checks.

**Scope, honestly: those 36 are all ordinary filler.** Legacy-dungeon sweep pools — which is what
the Scion was wrongly counted into — are filler-only by construction: Remembrances, key items, Great
Runes, boss rewards, legendaries and shop slots are cut before the pool is built, and all 36 of these
carried no important tag at all. So this was an early dump of junk and consumables, not a progression
break. Stormveil's pool is unchanged in total; it now divides
between its two real bosses (Godrick and Margit) instead of three.

The Scion's own drop, the Ornamental Straight Sword, is a normal check and is untouched.

### `dungeon_sweep`'s middle settings now do something

`minidungeons`, `all` and `bosses` were **identical** — the emit checked only "is it off?" and never
filtered by boss class, so all three granted the whole sweep set. The values are real now:

| value | sweeps | checks |
|---|---|---|
| `none` | nothing | 0 |
| `minidungeons` | catacombs, caves, tunnels, minor dungeons | 515 |
| `all` | + legacy dungeons and castles | 1971 |
| `bosses` (default) | + field bosses | 3184 |

**The default moved from `all` to `bosses`, and that is not a change to your seeds** — the full set
is what every non-`none` value already granted, so `bosses` is simply the correct name for what has
been shipping. Leaving it at `all` would have quietly removed field-boss sweeps from every seed.

`all` is now genuinely "dungeons without field bosses", which is the split that was asked for.

### Also

- **The AP flower icon can be built again.** `build_ap_icon.py` was lost in July 2026 and the
  placeholder has worn a vanilla Telescope ever since. The generator is rewritten, the flower art is
  in the repo, `build.ps1` builds the override instead of printing a command, and `package_release`
  now refuses to ship a bundle without it. (No visual change until a build stages the texture.)
- The client re-applies the AP icon after a load. It writes an icon param that loads revert, and it
  was the only such writer that never re-armed — so flowered shop slots fell back to a telescope
  after the first load of a session.

## v0.2.16 — 2026-07-28

### The filler pool is yours to tune

> 📖 Player documentation: [What fills your junk checks](https://github.com/4laric/er-archipelago/blob/main/Elden-Ring-Archipelago-Player-Guide.md#what-fills-your-junk-checks) in the Player Guide.

`curated_filler` is back in the shipped `EldenRing.yaml`, written out with the real default weights
so you can see and edit them. It is the game's main dial for what fills your junk checks — how much
gear (`juice`), how many upgrade stones, how many runes — and a template that hides it hides the
dial. A new gate (`test_gf_shipping_yaml_recipe`) keeps the template's numbers identical to the
code's default, so it can never quietly ship an old economy again. Delete the block to follow the
default automatically.

`pool_builder_intensity` works again. It sets how good a piece of gear has to be to count as `juice`:

| setting | counts as juice | catalog size | gear in the finished pool* |
|---|---|---|---|
| `normal` | legendary only | 149 | 230 |
| `high` | legendary + rare | 536 | 872 |
| `max` (default) | + B-tier | 1013 | 1518 |

\* one seed, and it counts every catalog-grade item in the pool — the vanilla gear that was always
there plus what the recipe injected — not injected gear alone. Injected juice can never exceed the
catalog size in the column to its left.

🛑 **A higher floor means LESS gear, not better gear.** Each level is a strictly smaller catalog while
the `juice` weight is unchanged — so raising the floor asks for the same number of items out of a
shorter list, and the surplus becomes junk. It buys quality by paying quantity. The option had been
frozen and inert since the filler-budget rework; it is a live knob again and the generator now warns
when the catalog cannot fill the allocation.

### Four options retired

`pool_builder`, `pool_builder_scope`, `pool_builder_juice_cap` and `pool_builder_juice_pct` described
a private juice budget that no longer exists — the filler tail has one budget and the `juice` weight
in `curated_filler` is the cap, the share and the on/off switch. They are now `Removed` stubs, so a
yaml naming them **raises** instead of being silently ignored. For no gear at all, set `juice: 0`.

`CONTRACT_HASH` is untouched, so an already-installed client still pairs with this apworld. A default
seed rolls the same juice catalog it did in v0.2.15 — the option's own default was corrected to `max`
in review, because unfreezing it while the class default underneath still said `high` would have
quietly halved the catalog for anyone not using the shipped template.

### Also

- Multiworld coverage in CI: two Elden Rings and two Hollow Knights, asserting items flow both ways
  and that foreign progression lands only on the progression surface. Its first run found a real
  leak — the finale's 10 locations bypassed the location-creation seam and never got the
  confinement rule, so 7 foreign progression items had been placed off-surface. Fixed.
- The player guide now documents `natural_progression`, `dungeon_sweep` and what fills your junk
  checks.

## v0.2.15 — 2026-07-28

Requires **Archipelago 0.6.7**. Regenerate your seed **and** refresh the client — the two must be
updated together this time (the client reads its region list from the seed now; see below).
Location names last changed in v0.2.12.

### Changed — options

- **`dungeon_sweep` is settable again.** It was pinned to `all` in the v0.2 option slim. `none`
  turns sweeps off entirely — every check is picked up where it lies — and `minidungeons` /
  `bosses` are the two middles. Requested by **ShadowTL**.

- **"Can I turn the Shattering off?" — yes, and the option already existed.** `natural_progression:
  true` plays the whole map gated by REAL vanilla keys and boss remembrances (still shuffled, so
  they can be anywhere) in vanilla's own dependency shape, with no synthetic Region Locks;
  `num_regions` is ignored. It has worked since v0.2.9 and was simply never written into the yaml
  template, so the one place a player actually reads never mentioned it. It is documented next to
  `num_regions` now. Also requested by **ShadowTL**.

### Fixed — apworld

- **The Message from Leda could hold something your seed required, and it does not exist until
  Messmer is dead.** It sits near Scaduview Cross, but its container is only enabled after Messmer
  falls — and a region lock lights Belurat's graces, so you warp to the spot and find nothing. It
  can no longer hold required progression. Confirmed in game by Alaric. Found by screening a corpus
  (`treasure_enablers`) that the existing cross-region check had never read; that screen is now
  permanent, so the next one of these fails a test instead of reaching a player.

### Changed — client

- **The tracker's region list now comes from the seed instead of being baked into the `.dll`.**
  It used to be a generated table built from the full region list, which meant that on a
  `num_regions` seed the tracker grouped checks into regions that seed does not contain and marked
  them in logic. It is now read from the seed itself, so it is right for whatever regions you
  actually rolled. **This is why the client and apworld must be updated together** — an old client
  with a new seed is fine, but a new client with an old seed will say so in the log and group
  nothing rather than guess.

### Fixed — release process

- **v0.2.14 shipped stamped `0.2.13`.** The packager checked that the changelog named the right
  version but not that the code did, so every v0.2.14 seed reported itself as v0.2.13 and a bug
  report could not tell the two apart. The packager now refuses to build unless every version site
  agrees with the build.

## v0.2.14 — 2026-07-28

Requires **Archipelago 0.6.7**. Regenerate your seed **and** refresh the client. Location
names last changed in v0.2.12, so an in-flight seed from v0.2.11 or earlier still will not
match a new tracker.

### Fixed — apworld

- **A region lock could land behind Lichdragon Fortissax, and nothing could open that fight.**
  Fortissax is fought inside Fia's Deathbed Dream, which does not exist until she is handed the
  Cursemark of Death. The generator treated his Remembrance as an ordinary boss reward — and
  because it carries the major-boss tag, it was one of the *preferred* places to put a region
  lock. Reported by Nova71288, from three players' spoiler logs. That check can no longer hold
  anything a seed requires. The rest of Fia's chain was already protected; the boss reward at
  the end of it was not, because every screen we have for finding quest-gated checks inspects
  how an ITEM is awarded, and what a questline gates here is whether the FIGHT exists.

- **Key items were being deleted from the item pool.** The filler allocator decided what it
  could overwrite by asking whether an item was a *Goods* item — and in Elden Ring every key
  item is a Goods item, so it could overwrite them, and with the shipped recipe it essentially
  always did. Bell bearings, whetblades, the crafting kit, maps, prayerbooks and scrolls, the
  Dectus and Haligtree medallion halves, the Rold Medallion, Pureblood Knight's Medal and the
  Cursemark of Death were all being removed from seeds. The set is now read from the game's own
  key-item flag (`EquipParamGoods.goodsType`): **108 item names across 270 checks** keep their
  real item. This is a pool-shape change as well as a bug fix — a seed holds more real key items
  and correspondingly less curated filler.

- **35 more checks can no longer be required.** 34 are NPC dialogue handovers — derived from the
  game's own talk scripts rather than found one at a time, and 14 of the 48 the screen lands on
  were already tagged by earlier hand audits, which is the reason to trust it about the rest. The
  ones most likely to be noticed: **Rold Medallion** (Melina, after Morgott), **Drawing-Room
  Key** (Tanith), **Haligtree Secret Medallion (Right)**. Plus the Fortissax reward above.
  Missable checks went 179 → 214. All of them remain randomised and obtainable; they simply
  cannot hold something the seed needs.

### Changed

- **More smithing stones in the filler pool** (`stones` 27 → 29, paid for out of `juice` 44 → 42).
  Every check barred from holding progression displaces the progression that remains into earlier
  slots, and protecting key items shrank the pool that share is measured against. Both squeeze the
  early upgrade economy, which is held to a stated bar — a player who has cleared a realistic
  fraction of what is open to them can afford a **+3 weapon**. At the old share three of nine test
  seeds fell under it.

- **Crafting cookbooks are deliberately NOT protected.** They are key items by the game's
  reckoning, all 96 of them, and holding 96 vanilla cookbooks in the pool instead of curated
  filler is a change to how a seed feels that nobody asked for. Prayerbooks, scrolls and bell
  bearings ARE kept: same family, far fewer, and a missing bell bearing is felt.

- **The progression surface counts only checks that can actually hold progression.** It had been
  counting checks the fill rules already refused. Harmless until the Fortissax reward was tagged,
  at which point Deeproot Depths claimed a place to put a lock while having none — that reward was
  its only surface member.

### Fixed — client

- **The tracker's location table was regenerated** for the 35 newly-unrequirable checks (214
  missable, was 179). Client-side data only; replace the `.dll` so the tracker agrees with the
  apworld.

## v0.2.13 — 2026-07-27

Requires **Archipelago 0.6.7**. Regenerate your seed **and** refresh the client. Location
names changed in v0.2.12, so an in-flight seed from v0.2.11 or earlier will not match a new
tracker — finish old seeds before updating, or reroll.

### Fixed — client

- **Enemy scaling did nothing at all in v0.2.12, and works again now.** A guard added that
  release to avoid touching characters while a map was still loading was far too strict: it
  rejected roughly 99.5% of the game's character slots, so a sweep that should have rescaled
  a few hundred enemies typically rescaled one — the player's horse. Every enemy kept its
  **vanilla** strength, which for a rolled start in a late region (Mohgwyn, the Consecrated
  Snowfield) meant walking out of the first grace into endgame enemies at full power.
  Reported by ShadowTL. The guard is reverted; the settle window that guarded this before
  v0.2.12 is unchanged and is doing the job again. Sweeps now scale 240–280 enemies where
  they were scaling 1–2. **The apworld was never at fault** — it had been sending the correct
  difficulty all along, and the client was discarding it. Client-side fix: replace the `.dll`.

### Changed

- **Version is now `0.2.13` on both halves.** Not `0.2.12.1`: the client crate's version must
  be three-component semver, and a test pins it to the apworld's `APWORLD_VERSION`. The
  contract hash is unchanged, so a v0.2.12 apworld still pairs with a v0.2.13 client without
  reporting a mismatch — only the descriptive version differs.

## v0.2.12 — 2026-07-27

Superseded by v0.2.13 the same day; see the enemy-scaling entry above. Everything below
shipped in v0.2.12 and is still current.

### Fixed — apworld

- **28 checks that can be picked up in two different regions can no longer be required.** A
  check is filed in one region, and the reachability model treats it as available once that
  region opens. Some event-awarded pickups are obtainable in more than one place, and *which*
  place is decided by the order you happen to do things. Fire Knight Queelign is the clearest
  case: he can be fought at the Church of the Crusade **or** in Belurat, and drops the Crusade
  Insignia first and the Prayer Room Key second wherever those two fights land — so half of all
  players get each item in the "wrong" region. A seed could put a required item on one and
  strand a player whose route went the other way. They stay randomised and stay yours; they
  just cannot hold anything the seed *needs* any more. Found by a screen that also re-derived
  seven checks earlier audits had already caught by hand, which is what makes the rest
  credible.

### Changed — apworld

- **24 checks now name a landmark, and five of them said nothing at all before.** A check's
  tracker line ends with the nearest Site of Grace to where the item actually is, and a boss
  **reward** never had one — it is handed over by an event rather than placed in the map, so
  there was no position to measure from. Those rewards now borrow their boss's arena. Five
  bare lines gained a landmark (*Sword of Night*, *Claws of Night*, *Priestess Heart*, and
  Igon's rewards), three stopped showing a raw map id (*Hoslow's Petal Whip* now reads **near
  Consecrated Snowfield Catacombs**), and sixteen got sharper — *Bull-Goat Helm* went from
  "around Ruin-Strewn Precipice" to **near Magma Wyrm Makar**. They are a small set but a
  memorable one: legendary weapons, key items and Deathroot. The landmark is the **boss's**
  location rather than the item's, which is an inference and recorded as one — so where a boss
  can be fought in more than one place it is refused rather than guessed. Fire Knight Queelign
  is fightable at the Church of the Crusade or in Belurat and drops the Crusade Insignia first
  and the Prayer Room Key second wherever those happen, so neither keeps a landmark.

## v0.2.11 — 2026-07-26

Requires **Archipelago 0.6.7**. Regenerate your seed **and** refresh the client. Location
names changed in this release, so an in-flight seed will not match a new tracker — finish
old seeds before updating, or reroll.

### Changed — apworld

- **`Boss` now means every boss.** The `Boss` location type was silently excluding the
  remembrance and great-rune bosses, so `important_locations: [Boss]` gave you 95 checks
  with **Godrick, Rennala, Radahn, Rykard, Mohg and Malenia all absent**. The cause was a
  filter that discarded any boss whose reward is *named* after a remembrance or a great
  rune — our rule, not the game's, and a leaky one: Agheel and a couple of others kept
  their tag purely because their drop is named something else. `Boss` is now 134 checks and
  a major boss is guaranteed to be one. If you play with this option, expect more of them.
- **A guessed region says so.** 506 checks sit on ground we cannot pin exactly — usually a
  border tile, where the nearest landmark is across a region line. They now read
  `(region unconfirmed)` instead of stating a region we do not actually know. Nothing about
  where they are has changed; they were already barred from holding progression. Only the
  label was overconfident. The example that prompted it: the Tibia Mariner's Deathroot at
  Summonwater, which sits on the Limgrave side of a tile whose other checks are Caelid.
- **Shop checks name the merchant who actually sells it.** Turning in a bell bearing moves
  a merchant's stock to the Twin Maiden Husks, so the Husks were being listed as a second
  seller on **377 wares they do not stock until you have found that bearing** — reading as
  an early alternative that does not exist. They are dropped from those notes and kept
  where they genuinely are the seller.
- **Eight more questline-gated checks are marked missable.** Each sits in one region but
  does not exist until a questline advances somewhere else — most visibly the **Golden Seed
  at Stormhill Shack**, which is not there until you have progressed past the Roundtable.
  They stay randomised and stay yours if you do the questline; a seed just cannot put
  anything *required* on them any more. The others: Varré's Lord of Blood's Favor, the
  Witch's Glintstone Crown, Patches' Murkwater Cave drops, the Wise Man's Mask, and three
  Volcano Manor invasion rewards.

### Fixed — apworld

- **A missable check could be forced to hold something good, and then hold nothing at all.**
  `important_locations` says a tagged check must reject filler; a missable check must reject
  progression. A location under both accepted *nothing*, and generation had no legal item
  for it. Missable now wins — a check you can lose permanently is never forced to carry
  something worth losing.

## v0.2.10 — 2026-07-26

Requires **Archipelago 0.6.7**. Regenerate your seed **and** refresh the client. Mostly
about knowing where a check actually is, and about questline pickups no longer being
thrown away.

### Added — apworld

- **Seven NPC and quest gestures are checks now.** Questline rewards used to be out of
  scope; they are in, randomised, and marked missable so a seed never *requires* one.
- **Check descriptions got a lot less bare** — 608 checks with no description down to 126.
  482 shop checks now name the merchant who sells the ware, six unnamed dungeons were
  filled in, and a batch of checks that were described by the wrong map tile now use the
  right one.

### Changed — apworld

- **Questline-gated checks are randomised and missable, not excluded.** An earlier attempt
  removed eight pickups from the pool entirely to guarantee a property the missable rule
  already provides. They are back in, marked instead.
- **Patches' chest pair and Edgar's five Revenger's Shack pickups are marked missable** —
  they are switched off until an NPC state changes, which nothing had noticed.

### Fixed — apworld

- **1189 checks that had no position at all now have a map**, and merchant checks inherit
  the merchant's own position — closing the coordinate gap from 34.3% to 19.4%.

### Fixed — packaging

- **The build freshness gate could never pass.** It compared timestamps against a file the
  script itself rewrote, then against commit time, which is always *after* the build. It
  now stamps the build with a content hash.

## v0.2.9 — 2026-07-24

Requires **Archipelago 0.6.7**. Regenerate your seed **and** refresh the client — they
ship together. Shop and merchant fixes on the apworld side, and on the client a crash,
three classes of check that gave you nothing, and shop purchases that handed over the
vanilla item.

### Fixed — apworld

- **Dragon Communion purchases could be asked to carry progression.** Incantations
  bought at a Dragon Communion altar cost Dragon Hearts — a limited consumable — so
  spending one closes off the others. Those checks are meant to be marked missable and
  barred from holding anything required. The rule only matched one of the game's cost
  types, so **eleven alt-currency checks were unmarked**, including every ware at the
  DLC's Grand Altar of Dragon Communion. A seed could place a required item behind a
  purchase you no longer had the hearts to make. Now any purchase not paid in Runes is
  marked, and each cost type is tracked separately.
- **Merchant hints named one shop when several sell the ware.** The tracker would say
  "Nomadic Warrior's Cookbook [1] — Kalé, Church of Elleh", you'd buy out Kalé's stock,
  and the check wouldn't fire — because four different merchants sell that row and the
  note named one of them. **496 of the game's 709 shop-check rows have more than one
  seller.** Five hand-written seller notes are removed, and generation now refuses to
  build if one comes back.
- **The one progression-eligible slot per merchant now really belongs to that
  merchant.** Each merchant contributes at most one slot that can hold progression.
  That slot was picked on a test that couldn't tell "one shop sells this" from "one
  price tag exists for it", so eight of the ten picks were sold by two to seven
  merchants apiece, and one was filed in a region where **no seller stands at all**.
  Slots are now chosen per physical merchant, must be a ware only that merchant sells
  out in the world, and must sit in the region the check claims. Fewer slots qualify,
  and the ones that do are findable.

*(The Twin Maiden Husks re-sell a merchant's stock after you hand in their bell
bearing; that mirror is no longer counted as a second seller, since you can only reach
it by killing the merchant first.)*

### Fixed — client

The apworld and the client ship together; refresh both.

- **Crash a few seconds after a boss sweep.** Felling a boss that pays out a batch of
  nearby checks could take the game down with an access violation. The client kept a
  pointer to your inventory that it captured once and reused forever; a map load frees
  that memory, so every grant after your first load was handing the game a dead
  reference. It now retires the pointer at every load and re-acquires it before the
  next grant.
- **Chests, scarab Ash-of-War drops and boss drops that gave you nothing.** Suppressing
  the vanilla item at a check is the same act as detecting it — both hang off the
  pickup. For weapons, armour, talismans and Ashes of War the client was emptying the
  slot outright, so there was nothing to pick up: no item, no popup, and the check
  never registered. Leonine Misbegotten's drop went unclaimed for a four-hour session
  this way.
- **Swept checks left dead pickups lying around.** When a boss sweep claimed the checks
  near its arena, the world was never told: the chests and corpses stayed put, opened
  on nothing, and gave no sign they had already been collected. The sweep now marks
  each one, retrying until the game confirms it.
- **Shop purchases that delivered the vanilla ware.** After the first map load, every
  rewritten shop row quietly reverted to selling its vanilla item while the client
  still believed it had been handed over — so you bought the check, got the ordinary
  item, and the multiworld item never arrived. Both halves are fixed: rows are
  re-armed on every load, and delivery is now re-proved against the live shop row
  rather than assumed.
- **Progressive Flask Upgrades that appeared to do nothing.** The flask has two axes:
  Sacred Tears raise potency, charges are reconciled against a ladder. The early rungs
  of that ladder ask for fewer charges than a fresh character already has, so the first
  few upgrades legitimately added none — silently. The client now says so, and
  announces a charge increase when one actually happens.

### Added — client

- **On-screen notices for grants that have no item.** Anything the client applies
  directly — flask charges today — now announces itself in the overlay, so an effect
  with no inventory item is no longer indistinguishable from a broken feature.
- **Crash reports.** A native crash now writes `crash-<pid>.txt` next to the client
  with the fault address and a stack. If the game goes down, that file is the single
  most useful thing to attach to a bug report.

### Changed

- **Some checks may hand you a duplicate vanilla item.** Stopping the dead-pickup bug
  above means the vanilla ware stays on the shelf for weapons, armour, talismans and
  Ashes of War, so you can receive both it and the multiworld item. This is deliberate
  and temporary: a duplicate is cosmetic, while the alternative was a check that never
  fired at all. The proper fix — swapping those slots for the Archipelago placeholder
  rather than emptying them — is in progress.

## v0.2.8 — 2026-07-23

Requires **Archipelago 0.6.7**. Hotfix-heavy; regenerate your seed and refresh the
client. Headline: a class of shop/merchant checks that handed out the vanilla item
(or fired nothing) in `num_regions` seeds.

### Fixed

- **Merchant checks sealed in the wrong region.** A shop check inherited its region
  from its ShopLineupParam *block*, but a block can hold two merchants in two
  regions — so the Altus Hermit Merchant's stock (Prophet set, Perfume Bottle,
  Sentry's Torch, Golden Sunflower, Distinguished Greatshield, …) was tagged Liurnia
  and got sealed out whenever Liurnia was rolled away. You'd buy from him in kept
  Altus and get the plain vanilla item with nothing sent. Region is now derived from
  the *physical merchant* (talk-ESD `OpenRegularShop` range → MSB placement), fixing
  the whole nomadic/roving-merchant class and the mirror **softlock** (a merchant in
  a sealed region whose check the world thought was reachable).
- **Foreign shop slots showed as the vanilla ware** instead of being flowered with
  the AP telescope; every foreign / region-lock slot now flowers, and a wider spare-
  good pool gives more of them a distinct name.
- **Cross-region "near <grace>" descriptions.** A guard stops a check being labelled
  by a Site of Grace in a different region (Roundtable Memory Stone no longer reads
  "near South Raya Lucaria Gate").
- **Ornamental Straight Sword** (tutorial Grafted Scion drop) → Limgrave, off the
  progression surface (a missable one-time fight can't gate a Lock).
- **Capital Rampart grace** no longer force-lit by its region Lock — it's unlocked by
  the Draconic Tree Sentinel.
- **Belurat Scadutree fragment** (needs Enir Ilim access) off the progression surface
  so a Belurat Lock can't strand on it.

### Added

- Interior checks read by **dungeon name** ("treasure — Sellia Crystal Tunnel")
  instead of a raw map tile.
- **Spirit Ashes** tiered into the juice pool (25, S/A-weighted); **Messmerfire
  Grease** added to filler.
- **`datamine_merchant_shops`** (talk-ESD + MSB → `merchant_shops.tsv`): ground-truth
  shop-check regions. A guard now hard-errors on any region override the derivation
  already reproduces, so redundant hand-pins can't accumulate.
- Client: all clippy warnings cleared (style only).

### Known

- **Non-goods double-dip** persists this build: weapons / armor / talismans / ashes
  can still hand out their vanilla copy alongside the AP item at enemy / scarab /
  scripted drops (e.g. Ash of War: Lightning Ram). The apworld now ships the data to
  blank these at the source; it goes live once the client's zero-slot handler lands.

## v0.2 — 2026-07-12

Requires **Archipelago 0.6.7**. A from-scratch, provenance-clean rebuild of the
Elden Ring world (`PROVENANCE.md`); pure-runtime (vanilla game on disk, the
client does everything live).

### Breaking

- **Game id is now `Elden Ring`** (was `EldenRing`). A v0.1 yaml is rejected at
  generation (`No world found to handle game EldenRing`). Upside: v0.1 and v0.2
  install side by side.
- **Option surface shrank to 19 tunable options**; the rest are frozen to
  defaults and no longer appear in the yaml. **Do not retrofit a v0.1 yaml** —
  Archipelago warns on each unknown option but then generates on defaults
  anyway, so you get a seed you did not configure. Start from the shipped
  `EldenRing.yaml`.

### Added

- **The Shattering (`num_regions`)** on the clean base: spawn at Roundtable Hold,
  each region's Lock is a multiworld item, the goal region is always kept.
  `num_regions_order` = `spine` (fixed) or `rolled` (random).
- **Real item shuffle** — each check pays out its own vanilla ER item, shuffled.
- **Great-Rune goal** (`ending_condition: great_runes`), auto-clamped to what is
  reachable.
- **Dungeon sweeps**, **pool building + varied filler**, **grace bundling** (a
  Lock lights all of its region's graces at once).
- **Scaling & QoL** — completion scaling, Scadutree blessing scope, start
  torch/steed/flasks, all maps revealed, early leveling, no weapon requirements,
  buyable Stonesword Keys, flattened smithing ladder, DeathLink.

### Fixed (playtested 2026-07-12)

- Spirit Calling Bell now usable from the received item.
- Map-piece items no longer minted on connect; the reveal fires without grants.
- Flasks no longer double-granted after a tutorial-death reload.
- A rolled start can no longer leave you without Torrent.

### Known issues

See `KNOWN-ISSUES.md`. Headline: a few checks can still pay the vanilla item
(contained — cannot strand a run); DLC seeds are experimental; base game is the
supported config.

### Licensing

Upstream Archipelago license (MIT); the runtime client is MIT and the
data-derived apworld ships no FromSoftware content or third-party randomizer
code. See `ATTRIBUTION.md`.

---

*Elden Ring and Shadow of the Erdtree are trademarks of FromSoftware / Bandai
Namco. This is an unofficial fan project and ships no game assets.*
