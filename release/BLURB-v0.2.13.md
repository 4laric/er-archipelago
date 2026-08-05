# v0.2.13 — release blurb (draft)

> Drafted 2026-07-27 for v0.2.12; **re-cut as v0.2.13** the same day, after v0.2.12 shipped with a
> broken enemy sweep. The hotfix section below is the new part. Everything from "Difficulty is
> configurable" onward was written for v0.2.12 and still belongs here, because most people upgrading
> will be coming from v0.2.11 and have not seen any of it.
>
> **Why 0.2.13 and not 0.2.12.1:** Cargo's version field is strict three-component semver, so the
> client crate cannot carry a four-part number, and a test pins the crate version to the apworld's.
> The Nexus listing can be labelled however reads best; this number cannot.
>
> ✅ **The landmark regen is in** (`c6c635d`). Every number and named example below was re-checked
> against the shipped `data.py` afterwards: 24 landmark changes — 5 that said nothing, 3 that
> showed a raw map id, 16 sharpened — and all eight items named by title verified individually.
>
> ✅ **The missable regen is in too.** `MISSABLE_LOCATIONS` went 151 → 179, all 34 two-region flags
> are tagged (0 untagged), and the Queelign pair is among them.
>
> One item left in "Before you post", and it is a playtest question, not a build.

---

## ⚠️ If you are on v0.2.12, update — enemy scaling did nothing

**v0.2.12's client had a bug that switched enemy scaling off entirely.** A guard meant to avoid
touching characters mid-load was far too strict: it rejected about 99.5% of the game's character
slots, and on a typical sweep the only thing it ever actually scaled was your horse. Every enemy
kept its **vanilla** strength.

If your region order happened to roughly follow the map, you might not have noticed. If it did not —
a rolled start in Mohgwyn or the Consecrated Snowfield — you walked out of the first grace into
endgame enemies at full vanilla strength, which is exactly as bad as it sounds. Thanks to
**ShadowTL** for the report that pinned it down.

Fixed in v0.2.13. A sweep that was scaling one or two things now scales 240–280.

**This is a client fix, so you must replace the `.dll`.** The apworld was never wrong — it had been
sending the correct difficulty all along, and the client was throwing it away.

---

## Short version (Discord / Nexus changelog box)

**Elden Ring for Archipelago v0.2.13 — enemy difficulty is yours now**

Enemy scaling has always been on and keyed to *your* progression rather than the map. This release
opens it up: three yaml options, all `0`–`100`, and on all three **higher is harder**.

```yaml
minimum_enemy_difficulty: 0     # how hard the EASIEST enemies are
maximum_enemy_difficulty: 100   # how hard the TOUGHEST ones get
difficulty_ramp_speed: 0        # how QUICKLY you reach them
```

**The ceiling has doubled.** The game ships twenty enemy-strength settings and we were only using the
lower half. Your deepest region now reaches the top of the ladder — about **7.4x enemy HP**, the
strength vanilla reserves for its endgame — where it previously stopped at 3.7x. Mid-run difficulty
rises with it. **This changes the default experience**, so if you liked v0.2.11's curve, set
`maximum_enemy_difficulty: 50`.

Also: enemies get scaled noticeably sooner after a fast travel, and **24 checks now tell you where
they are** — including five that previously said nothing at all.

**Update both halves.** The apworld and the client `.dll` ship as a matched pair and carry the same
version number.

⚠️ **Location names changed in v0.2.12**, so an in-flight seed from v0.2.11 or earlier will not match
a new tracker. Finish old seeds before updating, or reroll.

---

## Long version (release notes)

### Difficulty is configurable

Enemy and boss scaling is keyed to how deep a region sits in *your* seed's lock chain, not to where
it is on the map — unlock the Weeping Peninsula last and it is tuned like endgame territory. That has
always been true. What is new is that you can now shape it.

- **`minimum_enemy_difficulty`** (default `0`) raises the floor. At `50` nothing in the game sits
  below roughly 4x enemy HP, however early you reached it. Use it if the opening hours feel like a
  formality, or if you keep unlocking "early" regions late and steamrolling them.
- **`maximum_enemy_difficulty`** (default `100`) lowers the top. Worth a look on a **short seed**:
  with `num_regions: 4` your deepest region arrives fast but is still the end of your run, so it gets
  scaled like one — you can meet endgame-strength enemies holding a +6 weapon.
- **`difficulty_ramp_speed`** (default `0`) changes *when* the climb happens, not how high it goes.
  At `50` you are at maximum from about halfway and everything after that is equally hard.

They stack. `minimum_enemy_difficulty: 40` with `difficulty_ramp_speed: 60` starts genuinely
dangerous and is at full strength before the midpoint; add `maximum_enemy_difficulty: 60` and it
becomes a flat, consistently tough run instead of an escalating one.

Rune rewards are unchanged at every setting — a scaled-up enemy is worth exactly what it was before.

### The ceiling doubled — read this if you had a curve you liked

Elden Ring ships its own ladder of enemy-strength settings. We had been using the bottom ten rungs,
topping out at 3.70x enemy HP. Reading the ladder out of the game's own data showed it runs on to
**7.42x**, and that the top of it is real — the game applies that rung to 127 of its own enemies.

So the deepest region of a seed now reaches 7.42x rather than 3.70x, and mid-run tiers rise to match.
That is a deliberate balance change, not a side effect. If you preferred the old feel,
`maximum_enemy_difficulty: 50` is close to where things sat before.

### Fixes

- **Enemy scaling works again.** See the top of this page. Affected v0.2.12 only.
- **Enemies get scaled sooner after a fast travel.** The window dropped from roughly 3 seconds to
  2.5 in the ordinary case, and from about 8 seconds to 3.5 when the game reported an unstable region
  on arrival. If you have ever been jumped immediately after a warp and thought the enemies felt
  weirdly weak, that is what you were seeing.
- **The client now refuses a seed it is too old for**, instead of silently ignoring settings it does
  not understand. If you generate with an option your `.dll` predates, it says so on screen and in
  the log, naming the option.

### 24 checks now say where they are

A check's tracker line ends with a landmark — *Reduvia — near Murkwater Cave*. That landmark comes
from the nearest Site of Grace to the item's actual position, and a boss's reward never had one:
unlike a chest or a corpse, it is handed to you by an event and is not placed anywhere in the map
data, so there was nothing to measure a distance from.

Those rewards can now borrow their boss's arena. 24 lines improved:

- **Five said nothing at all** and now do — *Sword of Night* and *Claws of Night* (near Cathedral of
  Manus Metyr), *Priestess Heart* (near Rest of the Dread Dragon), and Igon's rewards at the foot of
  the Jagged Peak.
- **Three were showing a raw map id** like `m60_50_56`. *Hoslow's Petal Whip* now reads **near
  Consecrated Snowfield Catacombs**, which is where Juno Hoslow invades you.
- **Sixteen got sharper** — *around* a landmark became *near* one, or a better landmark entirely:
  *Bull-Goat Helm* moved from "around Ruin-Strewn Precipice" to **near Magma Wyrm Makar**, and
  *St. Trina's Blossom* from "around Stone Coffin Fissure" to **near Garden of Deep Purple**.

Not many checks, but they are the memorable ones — legendary weapons, key items and Deathroot.

Some rewards deliberately **kept** their blank line rather than get a wrong one. Fire Knight
Queelign can be fought at the Church of the Crusade *or* in Belurat, and drops the Crusade Insignia
first and the Prayer Room Key second — wherever those two fights happen to be for you. There is no
fact in the game data about which site your key came from, so naming one would be wrong for half of
you. Those checks say nothing instead.

### 28 two-region checks can no longer be required

Chasing that Queelign oddity turned up a seed-safety problem behind it. A check is filed in one
region, and the logic treats it as available once that region opens — but a pickup obtainable in
**two** regions, with the order deciding which, breaks that assumption. Put a required item on one
and a player routed the other way is stranded behind a region they have not unlocked yet.

28 checks now refuse required progression for that reason. They are still randomised and still
yours; they simply cannot hold anything the seed *needs*. The screen that found them also
re-derived seven that earlier hand audits had already caught one at a time — Lord of Blood's
Favor, Shabriri Grape, Sword of Milos and friends — which is the reason to trust it about the
rest.

### Renamed options

`completion_scaling_floor` → `minimum_enemy_difficulty`, and `completion_scaling_ramp` →
`difficulty_ramp_speed`.

The ramp also **flipped direction**: it used to be a percent of the run, so *lower* was harder, while
the floor beside it got harder as it *rose*. Two difficulty sliders disagreeing about which way is
harder is a bad time. The old `completion_scaling_ramp: 25` is the new `difficulty_ramp_speed: 75`.

Old yamls will **stop generation with a clear message** rather than quietly ignoring the dead key.

### Versioning

The client `.dll` and the apworld carry the same version number (`0.2.13`). The client had been
reporting `0.1.0-beta.4` for months, which made version-mismatch reports harder to read than they
needed to be. They ship as a matched pair; they now say so.

---

## Before you post

1. **The doubled ceiling has not been playtested.** The number is derived from the game's own data
   and is certainly *correct*; whether the new default curve is *fun* is a different question, and
   this is the change most likely to generate feedback. Consider a short seed at defaults before
   shipping — and note the scaling bug above means **nobody has actually felt the new curve yet**,
   including on v0.2.12.

2. ✅ **RESOLVED, and worth remembering how.** An earlier draft claimed the Siofra / Eternal Cities
   crash was "fixed at the root". That claim rested on the character-load-state filter — the very
   filter that turned out to be the scaling bug at the top of this page. It is pulled and should stay
   pulled. A later read of the crash logs found the crash fires from an identical site whether the
   enemy sweep touches 2 characters or 281, and one crash landed before any sweep had run at all, so
   the sweep was probably never the cause. The crash is guarded as it always was, by the settle
   window. It gets its own line in a later release, once it is actually understood.

3. ✅ **RESOLVED.** The Queelign landmark is refused and the count is **24**, not 26, in the shipped
   regen (`c6c635d`).

   ⚠️ Still yours to decide: the hand-written line **`400696 → "Kill Queelign in church of the
   crusade"`** in `location_descriptions.tsv`. It names one of the two sites, so it is wrong for
   anyone who met him in Belurat first. Something like *"dropped by Fire Knight Queelign"* would be
   true for everyone. I have not touched it.

4. **Nothing else from the tooling window belongs in a player blurb, and I left it out on purpose.**
   The check browser, the description-triage page, the item-naming sweep, the params/msg bundling
   and the provenance work are all developer-facing: they changed how we *find* things, not what a
   player sees. Resisting the urge to list the rest is the point.
