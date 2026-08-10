# Known Issues -- v0.3.11

Current as of **v0.3.7** (2026-08-06).

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

- **A check's name can point at the wrong Site of Grace.** About 507 checks read
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

- **Linux is not supported** (#222). The client throws "Could not translate RVA
  to VA" under Proton and the game can only be exited. What to do: play on
  Windows for now.

## Tracker

- **The tracker counts gated regions as in-logic** before you hold the Great
  Runes or the Academy Glintstone Key (#297). The graces correctly do *not*
  light -- the gate itself works -- the tracker is just optimistic about what
  you can currently reach. What to do: nothing; believe the graces.

## Shadow of the Erdtree

DLC seeds work, and the DLC's 13 regions behave like any other region. It is
still the less-travelled path: the base game is better tested and remains the
smoother first run.

- **The Shadow Keep church-basement grace can warp you in before the water is
  drained** (#123). Fast-travelling to Church District Lower / Scadutree Base
  before draining the keep can drop you onto lethal moving platforms. What to
  do: avoid warping there until you have drained Shadow Keep.

- **Jagged Peak grants 3 of its 5 graces** (#370), which may over-skip toward
  the summit. What to do: nothing.

## By-design behaviours

These are deliberate, not bugs -- listed so you can tell them apart from the
real thing. No report needed for anything below.

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
