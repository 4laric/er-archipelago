# v0.2.15 — release blurb (draft)

> Drafted 2026-07-28. Mostly a **you-asked-for-it** release: two options that already worked but were
> locked or undocumented, plus one check that could hold progression it should not. One thing needs
> saying out loud — **the client and apworld must be updated together this time.**

---

## Short version (Discord / Nexus changelog box)

**Elden Ring for Archipelago v0.2.15 — two knobs unlocked, one check made safe**

- **You can turn dungeon sweeps off.** `dungeon_sweep: none` — every check is picked up where it
  lies. `minidungeons` and `bosses` are the two middles. **Your boss rewards are unaffected**: a
  boss's own drop is a normal check and is never part of a sweep. Requested by **ShadowTL**.
- **You can turn the Shattering off.** `natural_progression: true` plays the whole map gated by
  *real* vanilla keys and boss remembrances — still shuffled, so they can be anywhere — in vanilla's
  own dependency shape, with no synthetic Region Locks. This has worked since v0.2.9; it was never
  written into the yaml template, so nobody could find it. Also **ShadowTL**.
- **Fixed:** the Message from Leda could hold something your seed required, and it does not exist
  until Messmer is dead.
- **Tracker:** its region list now comes from the seed instead of being baked into the `.dll`, so it
  is correct on `num_regions` seeds.
- ⚠️ **Update both halves.** A new client with an old seed will say so and group nothing rather than
  guess.

---

## Long version (release notes)

### Two options that were already finished

Neither of these is new code. `dungeon_sweep` was pinned to `all` during the v0.2 option slim — but
`none` was already handled and already covered by a test. It was locked because the option list was
being trimmed, not because the other values were unfinished, and it was sitting in the yaml's
"setting this does nothing" list, which actively told you the wrong thing.

**Turning sweeps off never costs you an item.** Of the 27 boss own-reward checks, none is a member
of any sweep group, and all 27 are ordinary locations with their own detection flag — as are all
3197 sweep members. Killing a boss pays its reward exactly as before. What you give up is the
convenience: you walk the dungeon and collect the rest yourself. (The client labels sweep toasts
"Boss sweep", because sweeps trigger on boss-defeat flags — dungeon sweep and boss sweep are one
feature under two names, and `none` turns off both, field bosses included.)

`natural_progression` is the answer to "can I turn the Shattering off". It is the inverse of
`num_regions`: instead of sealing regions and handing out synthetic Region Locks, the whole eligible
map is in play and regions open on their real vanilla keys — Dectus halves, the Haligtree medallion,
boss remembrances — still shuffled into the multiworld, minus a few kept chokepoints (the DLC behind
Mohg, Mt. Gelmir behind Liurnia and the Academy, Rauh behind Shadow Keep, the capital behind Altus
and two Great Runes). It has shipped and worked since v0.2.9. It simply was not in the template, so
the one place a player actually reads never mentioned it.

Both requested by **ShadowTL**, whose third question — rune yield not matching enemy scaling — is a
real bug and is **not** fixed here.

### The Message from Leda

It sits near Scaduview Cross, but its container is only enabled once Messmer falls. The generator did
not know that, so it could place required progression there — and because a region lock lights
Belurat's graces, you would warp straight to the spot and find nothing.

It can no longer hold anything a seed requires. Found by screening a corpus the existing cross-region
check had never read, and that screen is permanent now, so the next one of these fails a test instead
of reaching a player.

### The tracker knows what is in your seed

The tracker's region list used to be a table compiled into the `.dll`, built from the full region
list. On a `num_regions` seed that meant it grouped checks into regions your seed does not contain,
and marked them as in logic. It reads the list from the seed now, so it is right for whatever you
actually rolled.

**This is why both halves must move together.** An old client with a new seed is fine. A new client
with an old seed finds no region list, says so in the log, and groups nothing — visibly wrong rather
than quietly wrong.

### Under the hood

**v0.2.14 shipped stamped `0.2.13`.** If you are on v0.2.14, your logs and spoilers say v0.2.13 — the
packager checked that the changelog named the right version but not that the code did. Fixed, and the
packager now refuses to build unless every version site agrees. If you filed a bug against "0.2.13"
recently, it may have been v0.2.14.

---

## Before you post

1. ⚠️ **Say "update both" prominently.** The contract hash moved. A player who refreshes only the
   `.dll` gets a tracker that groups nothing — recoverable and self-announcing, but it will generate
   reports if they are not told.

2. **`natural_progression` is not new, and should not be sold as new.** It has been shipping since
   v0.2.9. The honest framing is "this existed and we hid it", which is also the more useful thing
   for anyone who wanted it three releases ago.

3. **Do not promise rune scaling.** ShadowTL's Adula question is a real defect with a located cause —
   boss runes live in a different table than enemy scaling touches — but the fix is not written and
   the balance call (should an early-met late boss pay *less*, or should late regions pay *more*?) is
   open. "Looking at it" is the accurate thing to say.

4. **`dungeon_sweep: none` has not been played end to end.** The option works and is tested at
   generation, and the boss-reward claim above is measured rather than assumed — but a full run
   without sweeps is a different pacing experience and nobody has done one.

5. **If someone asks for field-boss sweeps without full dungeon sweeps, the answer is "not yet".**
   The four values cannot express it; splitting the option into two is on the board
   (`split-sweep-options`), not in this release.
