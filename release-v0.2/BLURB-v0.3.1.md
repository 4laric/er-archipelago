# v0.3.1 — release blurb (draft)

> Drafted 2026-08-02. A bugfix release, and every item in it is a way a seed could quietly become
> unwinnable or trivially winnable without saying so. Two came from player reports on Nexus, one
> from Alaric noticing the Ashen Capital had no bosses, and two from following those up.
>
> ⚠️ **Client update recommended** — the re-grant loop fix is client-side. The slot_data contract is
> **unchanged** from v0.3.0, so a v0.3.0 DLL still connects.
> ⚠️ **The Leyndell warp-in fix reaches new seeds only.** A seed already in progress keeps the old
> behaviour permanently.

---

## Short version (Discord / Nexus changelog box)

**Elden Ring for Archipelago v0.3.1 — five ways a seed could lie to you**

- **Receiving the Leyndell Lock was lighting a grace inside the capital, past the two-rune gate.**
  The front-door grace and the "region is open now" flag were the *same bit*, so unlocking the region
  handed you a fast-travel target on the far side of a wall you had not opened. Same for Raya Lucaria
  and the Sewer. Each gated region now gets its own bit for the two jobs.
- **The capital's rune wall could be set below what the game itself enforces.** With one Great-Rune
  region in the seed, logic believed one rune opened Leyndell; Elden Ring wants two and does not
  negotiate. Fill could then put a region Lock behind a door you could not open. The wall is now
  floored at vanilla's two, or stood down entirely when the pool cannot supply them.
- **Roundtable Hold was paying out 13 checks for bosses in the Eternal Cities**, and the Ashen
  Capital — Gideon, Godfrey, Radagon and the Elden Beast — was paying out none at all. Boss-sweep
  routing had a tie nothing was breaking and a fallthrough that dumped unrouted maps into the hub.
- **A whole tier of Somber Smithing Stones could be missing from the seed.** Reported on a 1-region
  run: zero Somber [3] anywhere. There was no floor on any somber tier — measured at ~6% for [3] and
  ~73% for [9] on a short seed. Every tier 1-9 is now guaranteed present.
- **A boss below the Grand Lift of Rold was filed under the Mountaintops** and could hold a region
  Lock or a required Great Rune. If you started in the Mountaintops, the Rold Medallion was in
  Leyndell, and the seed was over. Reported from a 2-region run.
- **An equipped Great Rune no longer causes an endless "maximum allowed in inventory" popup.** The
  client decided you owned something by walking your bags — and an equipped rune is not in your bags,
  so it re-granted it forever. Possession now also reads the great-rune slot and the storage box.
- **New: `auto_equip` — wear whatever you are sent.** Off by default. Turn it on and every weapon or
  armour piece the multiworld hands you goes straight on, replacing whatever was in that slot,
  mid-boss-fight included. The client has had this working for weeks; the apworld had never sent the
  setting, so it was off for everyone and nothing said so. The equip mechanism itself is verified
  against a live game with Cheat Engine, but the feature has **not** had a full playtest — see below
  before you switch it on.
- **Two Golden Seeds in Liurnia were signposted to the wrong Site of Grace**, one of them to a
  grace 872 m away at the far end of the lake. Both now name the grace you would actually walk
  from. Two more checks stop reading *(region unconfirmed)* -- someone collected them in game, so
  they can hold progression again like any other check.
- ⚠️ **Client update recommended.**

---

## Long version (release notes)

### The Lock opened a door on the wrong side of the wall

Three regions sit behind a wall the base game enforces itself: Leyndell behind the two-Great-Rune
gate, Raya Lucaria behind the Academy seal, and the Sewer below the capital. The randomiser is
supposed to leave those walls alone and gate the region with its Lock instead.

**It was handing you a way around them, and the reason is a nice piece of how this project works.**
For an ordinary region, the flag that means "this region is open" is *derived* to be the region's
front-door grace — which is exactly right, because receiving the Lock should light the way in.
Leyndell's front-door grace is East Capital Rampart. That is **inside** the capital, past the rune
gate.

So receiving the Leyndell Lock lit East Capital Rampart as a fast-travel target and you could warp
straight in, gate unopened. This is the same trivialisation reported from a July playtest — "walked
straight in and ended the run at Morgott" — coming back through a door the earlier fix never watched.
That fix withheld the grace *bundle* for gated regions and did so correctly; the open flag shipped
the same grace through a different slot_data key, and every test on the first path stayed green
throughout.

One bit could not do both jobs, so the two jobs now get two bits: Leyndell, Raya Lucaria and the
Sewer are pinned to dedicated flags that are not graces at all. Nothing else changed — the fix is in
the generated table, so all four consumers inherit it at once rather than four places each getting
their own override.

**Those three flags were verified in game before release**, not assumed: read-false, set, save at a
grace, Alt+F4, relaunch, read-true — with the flag block's base pointer moving between runs, which is
what proves the bits came off disk rather than surviving in memory.

### The rune wall could be set lower than the game's own

`leyndell_runes_required` decides how many Great Runes our logic wants before the capital counts as
reachable. It was being lowered to match what the seed could actually supply, on the reasonable
theory that asking for *less* is always safe.

It is not, because the number is ours and the wall is not. Elden Ring's capital gate is a fixed
two-Great-Rune check, and while our wall is armed the capital's grace bundle is withheld — so the
physical gate is the only way in. Ask for one rune, and logic will happily place a region Lock behind
a door that still wants two.

Two ways to land there without warning: `num_regions` keeping exactly one Great-Rune region, or
simply writing `leyndell_runes_required: 1` in your yaml, which the option range allows. An armed
wall is now floored at two. When the pool genuinely cannot supply two, the wall stands down entirely
and the grace bundle is granted on the Lock — reusing the path that already existed for asking for
zero. **No change on the shipped default.**

While chasing this, the capital gate's actual predicate got settled for good: it does not check
whether you *hold* anything, it counts restored-rune flags in a fixed band. That rules out a
long-standing suspicion and confirms the client has been writing the right flags all along.

### The Roundtable had bosses it does not have

Alaric, looking at a sweep list: "Ashen capital should have 3 bosses: Gideon, Godfrey/Hoarah Loux,
Radagon/Elden Beast." It had none. Chasing that found two failure modes in how legacy-dungeon boss
kills are routed to a region, both silent:

- **A tie that nothing was breaking.** Two maps had their region decided by a vote that came out
  even, and the winner was whichever the counter happened to see first. One consequence: 42 of
  Leyndell's 64 swept checks hung off post-burn triggers — and the Erdtree burn moves you into the
  post-burn map *permanently*, so those checks could never fire from Leyndell proper. Dead on arrival.
- **A fallthrough that swallowed the no-vote case.** Three Eternal Cities maps — Astel, the Ancestor
  Spirit and the Regal Ancestor Spirit — got no vote at all and defaulted to Roundtable Hold. Thirteen
  checks paying out in a region that is open from turn one. The hub has no bosses and never did.

The curated override now beats the vote instead of only rescuing maps that had no vote, and the
silent hub fallback is deleted in favour of a generation-time error that names any map it cannot
route. Roundtable Hold goes 13 swept checks to 0; the Ashen Capital goes 0 to 3.

### A tier of Somber stones could simply not exist

From a player on a 1-region seed: *"I've had a run where I had zero Somber Smithing Stone [3] in the
game."*

He was right, and it was worse than one tier. The filler pass reserves a share of the pool for somber
stones and fills it by drawing at random with a taper toward the low tiers — an independent draw each
time, with nothing checking the result covered anything. The deepest-first floor that the module
advertises turned out to be **regular** Smithing Stone [1] only; the somber path returned one line
before reaching it. No somber tier had any guarantee at all, for as long as the reservation has
existed.

The consequence is sharper than a thin economy. A somber weapon costs exactly one stone per level and
the tier *is* the level, so a missing tier is not "fewer upgrades" — it is a permanent wall at that
rung. On a short seed the odds measured about **6% for [3] and 73% for [9]**.

Every somber tier 1-9 is now guaranteed present, paid for by converting the deepest surplus stones
already drawn rather than by growing the reservation. Stones you already have on kept locations count
toward it, so the guarantee does not spend a slot on a tier the seed already covers.

### The boss under the lift

From a player on a 2-region seed: *"I've been softlocked where my lock was located in the Forbidden
Lands. My starting area was in the Mountain Tops of Giants. I needed the Rold Medallion to use the
lift, but that was located in Leyndell."*

The Grand Lift of Rold is deliberately not part of Archipelago logic — the Lock is the only thing that
gates a region, and you are never meant to need the Rold Medallion to reach the Mountaintops. That is
sound **only** if nothing filed under the Mountaintops actually sits below the lift.

The Black Blade Kindred does. Its check was filed under the Mountaintops, sits on Forbidden-Lands
ground, and was eligible to hold progression — so fill could put a region Lock or a required Great
Rune on a patch of ground a Mountaintops-anchored player cannot stand on. Two other checks on that
exact ground were already barred; the boss check was not, because a check's region can be derived two
different ways here and the guard only watched one of them. It now judges both.

Eleven checks are newly barred from holding progression. No key item, Great Rune, medallion or
Seedtree is among them.

Worth being clear about what this bug did: you were never trapped — the Roundtable warp always works.
The *seed* was unwinnable, which is worse, because nothing tells you.

### The rune you were wearing did not count

Client-side. When the reconciler wants to know whether you already own something, it walks your
inventory. An equipped Great Rune is not in your inventory lists — the game moves it to a slot of its
own — so the client concluded you did not have it and granted it again. The game refused, because you
did have it, and the refusal is a popup. Then it tried again.

That is the "you can't have two of this rune" loop, and it was reported again this week from an older
build: a popup that reappears the instant you close it, leaving you able to run around and nothing
else. A guard added in v0.2.17 already bounds it — three attempts, then it stops — so recent builds
degrade to three popups rather than an endless wall. This release removes the cause rather than the
symptom: possession now means **your bags, plus the great-rune slot, plus the storage box**.

Honestly stated: the underlying mechanism is still unconfirmed in game, and this change makes the
readback more permissive rather than proving what was wrong. It can suppress a wrongly-repeated grant;
it cannot cause one. The diagnostic logging that would identify the true cause is deliberately kept.

One consequence to know: an item sitting in your storage box now counts as owned and will not be
re-delivered. Take it out and lose it and the next tick delivers it again as before.

### New: wear whatever you are sent

`auto_equip`, off by default. Turn it on and every weapon or armour piece the multiworld sends you is
put on the moment it lands in your bag, replacing whatever was in that slot — in the middle of a boss
fight, and whether or not your build can hold it. You do not choose your kit; the item order does.
That is the "use what you get" challenge format, and with region locks and a goal already here, a
French Challenge run (Wretch start, randomizer, use-what-you-get, permadeath) is now a yaml rather
than a stack of third-party helpers.

**The awkward part is that the client could already do all of this.** `auto_equip.rs` has been
reading `slot_data["options"]["auto_equip"]` for weeks, and the apworld had never once sent that key.
An absent key reads as `false`, so the feature was off for every Elden Ring seed ever generated, and
there was no symptom to notice — no warning, no log line, nothing in the wire that looked wrong. It
surfaced from a cross-side gate that lists every setting the client reads and the world never
produces. This release is the missing half.

A seed with `auto_equip: true` **requires a v0.3.1 client and will refuse to connect to an older
one**, saying which feature it needs. That refusal is the point: adding an option does not move the
contract hash, so without it an old DLL would report `VERSION: OK`, never see the key, and run your
seed with the setting silently ignored — the same failure again, one release later.

**Where this has and has not been tested, plainly.** The memory mechanism is verified, and verified
carefully: on a live game with Cheat Engine, writing all four representations Elden Ring keeps for an
equipped item equips it, renders it correctly in the equipment menu, and survives being unequipped by
hand — on a character that had never held that item. That is the half with teeth. A naive handle
write never acquires the item's refcount, so the next time you unequip through the menu the count
hits zero and the item is **destroyed** — gone from your inventory, one interaction after the thing
that caused it. Going through the game's own refcounted commit is what avoids that, and it was proven
on a throwaway character before any of the shipping code existed.

🛑 **What has not had a full playtest is the mod's decision-making on top.** The probe is handed a
slot and an item id; the client has to work both out for itself, and none of that is exercised by a
memory test. Untested in a real run: weapon-versus-armour routing, shields (they should go to the
left hand, and that is explicitly unconfirmed), gear arriving in the middle of a fight, the retry
path when an item is received before the game has finished granting it, and whether an auto-equipped
item survives a save-and-reload. It is off by default. If you turn it on, treat it as new — and not
on a character you would be upset to lose.

---

## Compatibility

⚠️ **Client update recommended, not required.** The re-grant fix is client-side and you want it. But
the slot_data contract is **unchanged from v0.3.0** — same 87 keys, same shapes — so a v0.3.0 DLL
connects to a v0.3.1 seed without complaint. A v0.2.x DLL still will not, exactly as in v0.3.0.

⚠️ **The Leyndell / Raya Lucaria / Sewer fix reaches NEW seeds only.** The old flags are baked into
seeds already rolled and cannot be changed from here. If you are mid-run on a v0.3.0 seed and want
the capital to actually be gated, you need to re-roll.

⚠️ **The somber floor and the Rold-seam bar are generation-time**, so they also apply to new seeds
only. An existing seed missing a somber tier stays missing it.

⚠️ **One seed shape does require the new client: `auto_equip: true`.** That seed declares the feature
in `requiresClientFeatures` and a v0.3.0 DLL will refuse it by name rather than connect and ignore
the setting. Leave the option off — the default — and nothing changes.

**Nothing here moves an item or a check in a seed already in progress**, and no existing option
changed its default or its meaning (`auto_equip` is new, and off). A v0.3.0 yaml generates a v0.3.1
seed with no edits.

---

## Before publishing — open items

- [ ] **Version bump.** `APWORLD_VERSION` in `greenfield/eldenring/contract.py` and
      `greenfield/eldenring/archipelago.json` both still read `0.3.0`, plus the two client-side sites
      and its `Cargo.lock`.
- [ ] **Confirm the client's version check.** This draft claims a v0.3.0 DLL connects to a v0.3.1
      seed, on the grounds that the contract hash has not moved. If the client compares
      `APWORLD_VERSION` for exact equality rather than comparing the contract, that claim is wrong and
      the warning above must become **Client update required**. Worth settling before this goes out.
- [ ] **Changelog entry.** `release-v0.2/CHANGELOG.md` has no v0.3.1 section yet.
- [ ] There is no `BLURB-v0.3.0.md` — the blurb series stops at v0.2.18. If v0.3.0 shipped its notes
      straight from the changelog, this file may want to follow that instead.
