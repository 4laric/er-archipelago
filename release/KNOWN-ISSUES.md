# Known Issues -- v0.4.0

Current as of **v0.4.0** (2026-08-12).

Everything we currently know about, what it looks like in play, and what (if
anything) to do about it.

The short version: **no open issue is known to make a seed unwinnable.** Where
one could in principle, it says so. Most of what follows was reported by players
on the Nexus page or in Discord -- that loop is the single most useful thing
anyone does for this project, so if something looks wrong and is *not* on this
list, we want to hear about it. Bring your YAML and the spoiler log.

For what has been *fixed*, see [CHANGELOG.md](CHANGELOG.md); it is written for
players, one section per fix, and it is the honest record.

## Region locks and reachability

- **Leyndell can open on one Great Rune** (#427). The capital's wall counts the
  **Great Rune of the Unborn** toward its total and we do not, so the gate can
  open one rune earlier than your `leyndell_runes_required` says -- typically
  once Rennala is dead and you hold one other rune. The gate is *more* generous
  than intended, never less, so it cannot lock you out. What to do: nothing. If
  you want the stricter gate, set the requirement one higher.

- **The Mountaintops can be entered early, through two graces inside Leyndell**
  (#323). Two of Leyndell's graces lead into Mountaintops territory without
  passing the Lock check, so a region you do not hold can be reached mid-run.
  This is a sequence break, not a soft-lock -- nothing is lost and the run stays
  winnable. What to do: if you care about the intended progression, do not warp
  onward from those two graces until the Lock arrives.

- **Consecrated Snowfield rides the Mountaintops Lock** (#406), so its checks
  count as in-logic as soon as you hold that Lock, without the Rold medallion
  path vanilla would ask for. In practice the Lock lights the graces and you can
  warp in, so the checks really are reachable; the logic is looser than the map.
  What to do: nothing.

- **Some region data is wrong.** East Divine Tower loot files under Altus, and
  the Sage's Cave and Wyndham graces are missing (#324). The Moonlight Altar is
  keyed to Liurnia (#410), which files Ranni's late checks under an early
  region. What to do: nothing -- but it is why a check occasionally shows up
  under a region that surprises you.

- **A few out-of-region check lots pay out nothing** (#329). A lot that is not a
  check in your seed can still be repointed, and then hands you neither the
  Archipelago item nor the vanilla one. What to do: nothing; those lots are
  never allowed to hold progression, so the cost is a missed pickup.

## Items and checks

- **Some NPC gifts and quest pickups are not randomised yet** (#217, #218). A
  batch of pickups never got a location built for them, so the game hands you
  the vanilla item and nothing registers as a check. The one you are most likely
  to notice is **Roderika at Stormhill Shack** -- neither her Spirit Jellyfish
  Ashes nor the Sitting Sideways gesture is a check. Others in the batch include
  the Flask of Wondrous Physick, the Tarnished's Furled Finger and the Tailoring
  Tools. What to do: nothing, and nothing is lost -- you still get the vanilla
  item, there is just no multiworld check attached.

- **Evergaol boss rewards are withheld until you teleport out** (#296). The
  reward lands when you leave the arena rather than when the boss dies, and
  `auto_equip` can miss the weapon when it finally arrives. What to do: leave
  the Evergaol; the item follows you out.

- **Dropping an item and picking it back up does not return it** (#225).
  What to do: do not drop multiworld items.

- **Dragon Communion can ask an absurd number of Dragon Hearts** (#231) when a
  Great Rune is rolled into one of its slots. What to do: skip that slot; no
  progression is placed there.

- **A check's name can point at the wrong Site of Grace.** 512 checks read
  `(region unconfirmed)` in their name, and some DLC descriptors name a grace
  nowhere near the check they describe (#330, #349, #418, #338). Names are
  derived from the nearest grace we can prove, which near a border is sometimes
  across the line. What to do: trust the region prefix over the landmark, and
  use the tracker.

## Client and platform

- **A crash on some AMD systems** (#411). An ACCESS_VIOLATION inside
  `amdxc64.dll`, reached through the overlay's D3D12 present path. Seen in one
  player's log across two startups. What to do: if it happens to you, keep the
  `crash-<pid>.txt` the client writes next to itself and attach it to a report --
  that file is what identifies these.

- **"Could not translate RVA to VA" at startup** (#222 on Linux, #475 on
  Windows). The client could not find one of the game's internal objects, and
  the game can only be exited. Despite the wording it is almost never about
  your game version: the build check runs first and fails with its own
  `Unsupported game version` text, so seeing *this* message means your build is
  one we support.

  **On Windows it is a startup race, not something you did.** The client asks
  the game for its task scheduler as soon as the game's window exists, which
  can be a moment before the game has finished registering the objects we look
  up. Ask too early and the lookup comes back empty, and that empty answer is
  reported as this message with no second attempt. Anything that shifts startup
  timing -- a faster disk, a busy machine, another overlay mod loading
  alongside ours -- can flip it, which is why it can appear on an install that
  launched fine a few times before. **What to do: quit and launch again.** It
  usually takes. If it happens every launch, attach `archipelago-<date>.log`
  from the folder the client sits in -- the file is appended across launches,
  so the last `SESSION START` block is the one that matters -- and say what
  else was in your DLL mods list.

  **On Linux it happens every launch** and is a different problem: Proton is
  not supported yet, so play on Windows for now.

## Tracker

- **The tracker counts gated regions as in-logic** before you hold the Great
  Runes or the Academy Glintstone Key (#297). The graces correctly do *not*
  light -- the gate itself works -- the tracker is just optimistic about what
  you can currently reach. What to do: nothing; believe the graces.

## Shadow of the Erdtree

DLC seeds work, and the DLC's 11 regions behave like any other region. It is
still the less-travelled path: the base game is better tested and remains the
smoother first run.

🛑 **`enable_dlc` is ON in the apworld's own defaults.** The shipped
`EldenRing.yaml` sets it to `false`, and four of the six wizard presets pin it
`false` -- but a yaml with an empty `Elden Ring: {}` section, the wizard's blank
**Defaults** card, and the `vanilla_deathlink` preset all leave it at the
apworld default, which means the DLC is in. If you do not own Shadow of the
Erdtree, say `enable_dlc: false` explicitly rather than relying on a default.

- **The Shadow Keep church-basement grace can warp you in before the water is
  drained** (#123). Fast-travelling to Church District Lower / Scadutree Base
  before draining the keep can drop you onto lethal moving platforms. What to
  do: avoid warping there until you have drained Shadow Keep.

- **Jagged Peak grants 3 of its 5 graces** (#370), which may over-skip toward
  the summit. What to do: nothing.

## By-design behaviours

These are deliberate, not bugs -- listed so you can tell them apart from the
real thing. No report needed for anything below.

- **The item pool is CURATED, so vanilla items will be missing from your seed
  -- by design, and on the default settings.** This is the most-reported
  non-bug we have, and it is not something you switched on. Three causes:
  (1) `curated_filler` spends the entire junk end of the pool on a recipe --
  every check that would have paid a Rune or a junk consumable is reallocated,
  by default about two fifths of it to real weapons, armor, spells, talismans
  and Ashes of War. The vanilla spread of tears, throwables, greases and
  crafting junk is what paid for that. (2) Farmable enemy drops carry no
  one-time flag, so they can never be checks in any randomizer; their contents
  are rerolled per seed at vanilla drop rates, which changes *what* farms give
  you. (3) The presence floor force-injects a curated set of physick tears and
  smithing bell bearings when their home regions are sealed -- a floor, not a
  promise about the rest. What to do: nothing. If you want the vanilla-ish
  spread back, set `vanilla_pool: true` -- that is the whole switch. Weighting
  `junk` in `curated_filler` ("keep whatever the check already paid") only does
  the first half and leaves the presence floor standing. The player guide's **"What fills your junk checks"** has the
  shipped recipe and every dial. 🛑 Sort it by where the fault is: an item
  absent from the POOL is this entry and needs no report. A CHECK that hands
  you the wrong thing -- the vanilla item, or nothing -- is a real defect, and
  the open ones are listed further up this file (#217, #218, #329).

- **`merchant_bell_logic` is RESERVED and inert.** The bell-to-shop mapping
  lives in engine code rather than in any param or EMEVD, so it cannot be
  derived from game data. The option exists so configs stay forward-compatible;
  shop checks are assumed reachable regardless of what you set. Leave it off.

- **Location-keyed sweeps and sweep-lock gates are empty on purpose.** Only
  flag-keyed dungeon sweeps fire -- kill the boss and the dungeon's other checks
  register. Dungeon sweeps themselves work normally.

- **About 1% of checks pay a Rune instead of a real item.** A small set of
  checks whose item names are not present in the game's text tables -- quest
  notes, a source typo, non-item text -- fall back to a Rune in the shuffle.

- **Great Runes are "useful", not progression**, unless
  `ending_condition: great_runes` requires them, in which case they become
  progression and are placed reachably.

- **Burning the Erdtree switches off Leyndell's grace warp points.** The burn
  is the game's own event and one of the things it does is clear the capital's
  fast-travel graces, so immediately afterwards you cannot warp into Leyndell
  even holding its Lock. `capital_reconciler` (on by default) still gives you
  the Royal Capital back -- it is the *warp shortcut* that is gone, not the
  region. What to do: walk in from Altus through the main gate (the Great Rune
  wall is unchanged) and touch a grace; the warp point comes back with it. If
  you would rather have vanilla's one-way burn, set `capital_reconciler: false`
  -- Royal Capital checks are then barred from holding progression, so the seed
  stays winnable either way.

- **`(region unconfirmed)` in a check name is the label being honest**, not a
  defect. Those checks are never allowed to hold progression, so a wrong guess
  cannot strand a run.

## Reporting

Useful reports include: your YAML, the spoiler log, the client log, and -- if
the game crashed -- the `crash-<pid>.txt` written next to the client. The single
most valuable thing you can say is what you did immediately before it happened.
