# v0.2.12 — release blurb (draft)

> Drafted 2026-07-27. **Two things to settle before this ships** — see "Before you post" at the
> bottom. Everything above it is verified; nothing there is a guess.

---

## Short version (Discord / Nexus changelog box)

**Elden Ring for Archipelago v0.2.12 — enemy difficulty is yours now**

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

Also: enemies get scaled noticeably sooner after a fast travel, and a long-standing crash around
Siofra and the Eternal Cities has been fixed at the root.

**Update both halves.** The apworld and the client `.dll` ship as a matched pair and now carry the
same version number for the first time.

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

- **A crash around Siofra River and the Eternal Cities is fixed at the root.** The client used to
  wait a fixed 2.5 seconds after any map change before touching enemies, because touching one
  mid-load could crash the game. It turns out the game publishes a per-character "am I finished
  loading" state that we were never reading. We read it now, so the wait is no longer doing the
  dangerous work — and the guard it replaced can eventually come down.
- **Enemies get scaled sooner after a fast travel.** The window dropped from roughly 3 seconds to
  2.5 in the ordinary case, and from about 8 seconds to 3.5 when the game reported an unstable region
  on arrival. If you have ever been jumped immediately after a warp and thought the enemies felt
  weirdly weak, that is what you were seeing.
- **The client now refuses a seed it is too old for**, instead of silently ignoring settings it does
  not understand. If you generate with an option your `.dll` predates, it says so on screen and in
  the log, naming the option.

### Renamed options

`completion_scaling_floor` → `minimum_enemy_difficulty`, and `completion_scaling_ramp` →
`difficulty_ramp_speed`.

The ramp also **flipped direction**: it used to be a percent of the run, so *lower* was harder, while
the floor beside it got harder as it *rose*. Two difficulty sliders disagreeing about which way is
harder is a bad time. The old `completion_scaling_ramp: 25` is the new `difficulty_ramp_speed: 75`.

Old yamls will **stop generation with a clear message** rather than quietly ignoring the dead key.

### Versioning

The client `.dll` and the apworld now carry the same version number (`0.2.12`). The client had been
reporting `0.1.0-beta.4` for months, which made version-mismatch reports harder to read than they
needed to be. They ship as a matched pair; they now say so.

---

## Before you post

Two items I could not settle from here:

1. **The in-game crash check is not done.** The Siofra fix is verified by inspection and by the
   Windows build, but nobody has run the game with it. It needs a Siofra well descent and a warp to
   Beside the Rampart Gaol before the "fixed" claim above is honest. Either confirm it, or soften the
   wording to "should be fixed — please report if you still see it".
2. **The doubled ceiling has not been playtested.** The number is derived from the game's own data
   and is certainly *correct*; whether the new default curve is *fun* is a different question, and
   this is the change most likely to generate feedback. Consider a short seed at defaults before
   shipping.

Anything of yours from this window that belongs here — the check browser, the description work, the
item-naming sweep — I have deliberately left out rather than describe from commit subjects.
