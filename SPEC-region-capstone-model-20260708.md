# SPEC — Region capstone model: the Threshold Rule (2026-07-08)

Design spec for how the overworld is carved into play_regions and how each region
resolves. Fixes the ad-hoc "some subareas are their own region, some are folded in"
situation with a single stated principle, and defines the boss-lock capstone for each
region using legible vanilla key items.

Synthesis of an Opus main-thread design pass and an independent Fable 5 consult.
Supersedes the intent of archive/SPEC-region-boss-gating.md and folds in the
legible-key-lock direction (er-legible-key-locks-spec).

---

## 1. Motivation

Some regions lack a natural capstone. Liurnia is the worst offender: no clear "Liurnia
boss," so the region just ends without resolving. Meanwhile the carve between overworld
zones and their sub-dungeons has been decided case-by-case (Raya Lucaria separate,
Stormveil separate, Leyndell separate) with no rule that says *why*. That inconsistency
is the actual defect — not any single region.

The goal: every region gets the same legible shape — **enter, then resolve on a capstone
boss whose reachability is gated by a real vanilla key item** — and a rule that decides
region granularity uniformly instead of by feel.

## 2. The Threshold Rule (the stated principle)

Look at what stands at a subarea's front door in **vanilla**:

- **Front door is a boss fog** -> cut there. The boss is the *parent's* capstone, and the
  subarea becomes **its own region**. (Margit gates Stormveil; Fire Giant gates Farum
  Azula.) These are "legacy-dungeon regions": they resolve on the lord's fog reached by
  traversal.
- **Front door is a key-item check** -> **fold the subarea in**. The key becomes the
  parent's capstone lock and the lord inside becomes the parent's capstone boss.
  (Academy Glintstone Key gates Rennala; two Great Runes gate Morgott.) These are
  "overworld fold-in regions."
- **Front door is open geometry** (no fog, no key) -> **fold in as ride-along** content.
  (Weeping Peninsula, Castle Sol's approach, the Eternal Cities' surface lifts.)

This reproduces the existing instincts as *consequences of the rule*, not exceptions:
Stormveil is boss-thresholded, so cutting it is principled; Raya Lucaria is
key-thresholded, so folding it is principled.

Two region archetypes fall out:

1. **Overworld fold-in region** — capstone boss lives in a folded sub-dungeon whose
   vanilla front door is a KEY. Lock = that key. Large footprint, single fog resolution.
2. **Legacy-dungeon region** — its own region because a boss fog gates it in vanilla.
   Resolves on the lord's fog reached by traversal; a capstone key is optional and added
   only for AP-progression reasons (see Farum, section 4).

### 2a. Two kinds of lock: capstone vs internal boss

Every region contains bosses that are *not* its capstone — mid-bosses on the critical path
and terminal dead-end bosses. These are handled by a second, distinct lock kind:

- **Capstone lock** — one per region. A legible vanilla KEY that gates the region's lord
  and *resolves* the region (unlocks the next in the spine). This is what the tables below
  enumerate.
- **Internal boss lock** — one per sub-boss. Under the existing sweep-gate boss-lock model
  (er-boss-locks-v01), each internal boss's physical fog is individually gated, but beating
  it does NOT resolve the region — only the capstone does. Internal bosses still emit their
  own checks and can hold their own required item.

The distinction matters for the fold-in tables: a subarea listed as a fold-in still carries
its boss as an internal boss lock; it just isn't the capstone. Base-game examples that stay
internal: Red Wolf inside Raya Lucaria (Rennala is Liurnia's capstone), Godskin Duo inside
Farum (Maliketh is capstone), Commander Niall inside Castle Sol (Fire Giant is capstone).

**But which bosses are internal vs capstone is a granularity dial, not a fact the rule
fixes.** The Threshold Rule marks every boss fog as an *available* cut point; how many of
those cuts you actually take is what sizes your regions. Any internal terminal boss can be
*promoted* to a capstone by deciding to cut its subarea into its own region — that is
exactly the Stormveil move (Godrick could have been an internal boss of a big Limgrave; we
chose to cut). The two leading DLC promotion candidates:

- **Belurat + Divine Beast Dancing Lion** — Belurat Tower Settlement is a self-contained
  mini-legacy-dungeon with Dancing Lion as its lord, structurally a Stormveil. Promote and
  it becomes its own region; Dancing Lion resolves it.
- **Ancient Ruins of Rauh + Romina** — split Rauh from Enir-Ilim: Romina resolves Rauh,
  leaving Enir-Ilim as the pure Kindling-gated finale slice.

The tables in 3a **pull both cuts** (Dancing Lion resolves Belurat, Romina resolves Ancient
Ruins of Rauh); had we folded them instead, both would be internal locks under Rellana and
Radahn respectively. The tradeoff is the general one: **more slices = finer sphere gradient,
more but smaller regions** (easier per-region curation, more capstone keys to theme
legibly) vs **fewer slices = larger regions resolving on a single fight** (swingier pacing,
heavier curation load per Rule A). Pick per region by feel; the mechanism is identical
either way — a capstone is just an internal boss lock we elected to make region-resolving.

Decision on the two DLC dials: **cut both.** Belurat (Dancing Lion capstone) is a
self-contained mini-legacy-dungeon, Stormveil-tier. Ancient Ruins of Rauh is **pulled out**
with Romina as its capstone, leaving Enir-Ilim as the pure Kindling-gated finale slice — the
thin-finale worry is outweighed by giving the Kindling a clean single-purpose region to open
and letting Romina resolve real estate that otherwise sat as dead traversal before Radahn.
Both revisitable after playtest.

## 3. Region-by-region capstone table

| Region | Archetype | Fold-ins | Capstone boss | Capstone lock (vanilla key) |
|---|---|---|---|---|
| Limgrave | start | Weeping Peninsula | Margit | none — start region resolves free (sphere-1) |
| Stormveil | legacy-dungeon | — | Godrick | none — lord fog by traversal |
| Liurnia | overworld fold-in | **Raya Lucaria Academy** | Rennala | **Academy Glintstone Key** |
| Caelid | overworld | Dragonbarrow | Radahn | Dectus halves double as festival trigger |
| Altus | overworld fold-in | **Leyndell** | Morgott | **two Great Runes** (vanilla capital gate) |
| Volcano Manor | legacy-dungeon | — | Rykard | Drawing-Room Key |
| Mountaintops | overworld | Castle Sol (made mandatory) | Fire Giant | **Haligtree Secret Medallion (Right)** |
| Snowfield/Haligtree | overworld fold-in | Ordina, Elphael | Malenia | Haligtree Secret Medallion (both halves, Rold) |
| Farum Azula | legacy-dungeon | — | Maliketh | **N Deathroot** (see 4) |
| Mohgwyn | overworld fold-in | — | Mohg | Pureblood Knight's Medal |
| Eternal Cities | overworld fold-in | Siofra, Nokron, Ainsel, Deeproot | Astel | Fingerslayer Blade |

### 3a. DLC (Shadow of the Erdtree) — same rule, six regions

The Threshold Rule applies unchanged. Two geography facts drive the carve: Cerulean Coast
and Charo's Hidden Grave hang off *southern Gravesite Plain* (Ellac River), not Scadu
Altus; and Ancient Ruins of Rauh is reachable two ways (Shadow Keep west rampart viaduct
*and* up from Rauh Base on the Gravesite side). Geometry leaks around every fog on the way
to the finale — only Messmer's Kindling does not leak. That is why the finale is the one
clean key-lock in the DLC.

| Region | Archetype | Fold-ins | Capstone boss | Capstone lock |
|---|---|---|---|---|
| Gravesite Plain (DLC root) | overworld fold-in | Castle Ensis, Ellac River, Rauh Base, Cerulean Coast, Charo's Hidden Grave, Stone Coffin Fissure, Dragon's Pit -> Jagged Peak, gaols/catacombs | Rellana, Twin Moon Knight | none — Ensis fog by traversal; region's own front door = base-game "Withered Arm" gate (Mohg + Radahn) |
| Belurat | legacy-dungeon | Tower Settlement | Divine Beast Dancing Lion | none — lord fog by traversal (cut, not folded — see 2a) |
| Scadu Altus | overworld fold-in | Bonny Village, Moorth Ruins, Fort of Reprimand, Ruins of Unte, Cathedral of Manus Metyr (quest-gated interior) | Golden Hippopotamus | none — Shadow Keep gate-opening is pure route-work (Storeroom/Church District or back route); Hippo fog by traversal |
| Shadow Keep | legacy-dungeon | Church District, Storeroom, Specimen Storehouse, West Rampart; ride-alongs: Recluses' River (one-way), Abyssal Woods + Midra, Scaduview + Scadutree Base (O Mother door) | Messmer the Impaler | none — lord fog by traversal; his kill check *is* the Kindling location |
| Ancient Ruins of Rauh | legacy-dungeon | Rauh Base approach, Church of the Bud | Romina, Saint of the Bud | none — Romina's fog by traversal (pulled out, Romina promoted from internal — see 2a) |
| Enir-Ilim (finale) | overworld fold-in | Sealing Tree, Divine Gate, Enir-Ilim tower | Promised Consort Radahn | **Messmer's Kindling** (burns the Sealing Tree) |

Spine: Gravesite -> (Rellana) -> Scadu Altus -> (Hippo) -> Shadow Keep -> (Messmer, drops
the Kindling). Belurat (Dancing Lion) and Ancient Ruins of Rauh (Romina) resolve in parallel
off the mainline; the Kindling then opens Enir-Ilim -> Radahn. Everything else rides along.

Carve justifications by the rule: Scadu Altus's front door is Rellana's *boss fog* -> cut,
Rellana = Gravesite's capstone. Shadow Keep's front door is *geometry not a key*, first fog
past it is the Hippo -> cut at Hippo. Shadow Keep is entered through a boss fog -> own
legacy-dungeon region, resolves on Messmer. Belurat and Ancient Ruins of Rauh are the two
*dial* cuts (2a): both are self-contained dungeon slices, so we cut them into their own
regions with Dancing Lion and Romina as capstones rather than folding them in. Enir-Ilim's
front door is a *key check* (Kindling at the Sealing Tree) -> its own first-class finale
region, capstone Radahn — the Academy-Glintstone -> Rennala pattern exactly, now standing
alone once Rauh is pulled out.

The Scaduview edge case: its front door is the O Mother gesture (a key check), which by rule
would make O Mother Shadow Keep's capstone — but that slot is spent on Messmer and the
Kindling is the finale key; don't dilute it. Ruling: Scaduview stays a *fold-in* of Shadow
Keep with O Mother as an internal legible lock (synthetic AP item driving the door flag —
gestures are not goods, see risk 8 in 6a), one region one capstone.

**Scadutree Fragments / Revered Spirit Ash = parallel power axis, never a capstone, never
in logic.** Every fragment/ash *location* is an emitted curated check (they are the DLC's
map-pins, always worth a notification — passes Rule A for free and gives every fold-in its
checks backbone). The *items* enter the pool as progressive Scadutree Blessing / Revered Ash
Blessing, classified **useful, not advancement**: blessing gates difficulty, not
reachability, and putting a soft stat into sphere math yields seeds that are logically
beatable but miserably BK-feeling. Handle the pacing risk on the difficulty side (DLC
boss-scaling tiers, optionally completion-scaling); this dovetails with the
global-scadutree-blessing spec (client persists stored level, grants progressive on
receive).

Optional content (consistent with "DLC boss locks except Bayle"): **Bayle — no lock at
all** (long one-way dead-end gauntlet, nothing downstream; a lock would gate only pain and
entangle Igon's quest). **Abyssal Woods / Midra — locked but optional** (standard boss lock,
self-heals since nothing is behind him; never capstone, never progression; stealth
traversal makes "reachable" a lie for logic, and the Frenzied Flame ending stays entirely
out of goal/logic). Both are safe as optional precisely because neither contains a capstone
key, so Rule B is untouched.

## 4. Two design decisions locked in this pass

**Fire Giant / Castle Sol.** Endorsed. Mountaintops' vanilla structure is a dead Torrent
corridor to the Fire Giant. Fix: make **Castle Sol mandatory** by using the Haligtree
Secret Medallion (Right) as Fire Giant's capstone key — Commander Niall becomes the
mid-boss guarding it. This converts an interminable ride into a two-beat region (ride in
via Rold -> Castle Sol is the dungeon, Niall the mid-boss, medallion the prize -> Fire
Giant's fog opens -> region resolves). Whiteridge Road / Guardians' Garrison demote to
optional check-farming, which is honestly what they are. The medallion is dual-duty (its
left half co-keys Snowfield/Haligtree at Rold) — acceptable, but this is the single place
to lean hardest on the legible-key renaming/messaging layer, since one item advancing two
regions reads clean to a designer and can confuse a player mid-seed.

**Maliketh / N Deathroot — with the self-containment proviso.** Farum has no vanilla key
item inside it, but Maliketh *is* Gurranq, who devours Deathroot. Gate his fog on N
deathroot. Lore-true, and the items are already pooled with missable-tagging done.
**Proviso (softened by Rule B):** deathroot is a normal multiworld progression item — fill
may place Farum's deathroot in another world, and being BK'ed in a Farum-first start while
you wait for it is intended, not a soft-lock. So the old "must be findable within Farum"
requirement is downgraded to a nicety for solo/async seeds. The real constraint on Farum as
a start region is the general one in Rule B: expose a non-empty sphere-0 foothold so the
player is not fully stuck from frame one. Never gate Farum's *other* checks on deathroot —
only Maliketh's own reward — or fill could be forced into a within-world cycle.

## 5. Two rules that govern the whole model

**Rule A — Fold-ins must be largely curated.** An overworld fold-in region (Liurnia,
Altus) is large and resolves on a single fog. Its many traversal checks must be
**curated / big-ticket weighted**, not flooded with trivial filler. Concretely: do not
flood the multiworld sync with dozens of junk checks strung along the path to Godrick /
Rennala / Morgott. Every check the region emits should be worth a sync notification. This
is the important_locations + curated_fill + big-ticket machinery doing its job; for
fold-ins it is not optional polish, it is what keeps the region from being dead air before
the capstone and keeps the sync signal meaningful. Fold-ins get *proportionally more*
curated checks than the region count would suggest, precisely because their resolution is
one fight.

**Rule B — Capstone keys are first-class multiworld items; local BK is intended.** A
capstone key (vanilla or synthetic Boss Key) goes into the general item pool and fill may
place it in **any player's world**. Being locally stuck — every reachable check exhausted,
waiting for your Academy Glintstone Key / Kindling / deathroot to arrive from someone else's
world — is a *feature of multiworld, not a soft-lock*, and the design must keep it possible.
Do not constrain fill to keep capstone keys local. The invariants are:

- **Global winnability, not local self-sufficiency.** The multiworld must complete in some
  sphere order; a single world need not be solvable alone. BK-via-remote-lock is a valid,
  intended state.
- **No within-world cycle.** Fill must never be forced to place your key behind the very
  boss it gates. This is the one hard local constraint — and it is already handled: gate only
  the boss's *own* AP check on `has(key)`, never the region's other checks (see section 7).
  That is precisely what frees the key to be placed anywhere, including another world.

This **supersedes the earlier "self-containment" framing.** A rollable start region does not
need its capstone key locally; it needs only a non-empty *sphere-0 foothold* (some checks
reachable with no items) so the player is not fully BK'ed from the first frame and fill has
early landing spots — and even that is a UX/fill-health preference, not a winnability
requirement. The Farum deathroot proviso is downgraded accordingly (see section 4): local
deathroot is a nicety for solo/async play, not a rule.

## 6. Risks / edge cases (must be handled in impl)

1. **Great Rune of the Unborn does not count** toward vanilla's two-rune Leyndell gate.
   Gen logic and client flag check must agree on excluding it — exactly the contract-drift
   class the slot_data contract guards.
2. **Possession, not tower activation.** Vanilla's Leyndell check is rune *possession*.
   Do not let the Altus lock require Divine Tower activation, which would drag Divine
   Towers (other regions) into Altus logic. Watch this given the recent great-rune
   restore-flag fixes.
3. **Deathroot is consumed** when fed to Gurranq. The Maliketh lock must count the
   collected-set / flags, never live inventory — same pattern as the vanilla-suppress
   collected-set fix.
4. **Dectus bypass.** Ruin-Strewn Precipice reaches Altus keyless. Gate the *capstone*
   (two runes -> Morgott) rather than hard-KICKing Altus entry, or a legit Precipice
   climber reads it as a bug.
5. **Margit/Godrick skippable to Liurnia** via the Stormhill cliff path. Liurnia access
   logic must not silently assume Limgrave resolved.
6. **Teleport punctures.** Four Belfries (one drops inside Farum Azula), Sellia trap chest
   (Limgrave->Caelid), Imbued Sword Keys. Every boss-thresholded region needs a defined
   answer for "player is physically here without access" — existing KICK / front-door-latch
   machinery, but Farum-by-belfry specifically needs a test.
7. **Radahn festival triggers are multiple** (Ranni's quest, reaching Altus), not just
   Dectus. If Caelid's lock is Dectus halves, suppress alternate triggers or the capstone
   unlocks itself.
8. **Mountaintops assumes Torrent.** Region is unplayable mountless; the known
   torrent-regionlock bug becomes a region-design dependency here. Spectral Steed Whistle
   should be logic-required for Mountaintops access, full stop.
9. **Rennala gates respec.** Folding her behind the Academy Key locks larval-tear respec
   until Liurnia resolves. Acceptable; release-notes line.
10. **Fortissax is a trap capstone.** His fog is buried in Fia's missable quest-sleep
    sequence — logic poison. Eternal Cities capstone is **Astel** (fixed fog), not
    Fortissax or the Regal Ancestor Spirit.

## 6a. DLC-specific risks

- **Entry is a compound base-game gate** (Mohg + Radahn + arm-touch; two Mohgwyn routes —
  Varre quest *or* Snowfield teleporter). The whole DLC subtree hangs off it: logic must
  accept either Mohgwyn route, and no base-game progression item needed *before* Mohg/Radahn
  may fill into the DLC (cycle risk). Use a single synthetic "Withered Arm" legible lock as
  the DLC root's front door.
- **Reachable != survivable at Blessing 0**, Radahn especially — the one fight where "logic
  said go" at low blessing reads as a bug. Resolved by the power-axis decision above; watch
  it.
- **Two-phase Radahn is one fight** — one lock, one goal check on the final kill flag; never
  emit a phase-1 check.
- **Quest state machines are progression poison**: Ymir/Metyr (bells at Finger Ruins of Rhia
  on Cerulean Coast and Dheo on the Scaduview side — cross-region, missable), Leda's faction
  chain (Enir-Ilim gank), Thiollier/St. Trina, Igon, the Needle/Frenzied-Flame branch. Tag
  all quest-chained checks missable, exclude from advancement, and never boss-lock Metyr (a
  quest-gated boss behind a lock item is a double-gate soft-lock).
- **One-way drops** (Recluses' River/Abyssal Woods, Stone Coffin Fissure, Jagged Peak
  descent): warp-in / random-start placement inside these needs the warp-out guarantee
  (region_access=warp); audit alongside Rule B.
- **Poor start regions (design, not winnability)**: Enir-Ilim and Scaduview have ~no
  sphere-0 foothold — they are pure finale/interior slices, so a random start there would
  open fully BK'ed on frame one. Exclude them as start candidates for *UX* reasons, NOT
  because their keys are external (external keys are fine under Rule B — they can and should
  be able to live in another world). Gravesite, Belurat, Scadu Altus, Shadow Keep, and
  Ancient Ruins of Rauh have real early footholds and are good start candidates.
- **Boundary mis-bucketing will recur** (Rauh Base vs Rauh Ruins share naming; Cerulean /
  Charo's / Fissure blend; Church District straddles Keep and Altus) — same class as the
  Liurnia/Altus boundary mis-region fix. Budget play_region overrides and run the
  region-correctness gate on DLC tiles from day one.
- **O Mother is a gesture, not a good** — client grant path differs from inventory items;
  back the legible lock with a synthetic AP item driving the door flag, not the gesture.
  Fragment sources grant unequal amounts (some boss drops give multiples) — progressive
  granularity must reconcile to vanilla totals or the power curve drifts.

## 7. Implementation primitive: (boss, regions) -> lock

The whole model reduces to one declarative primitive: **define a set `{boss B, regions R[],
key K}`; the output is a boss-lock such that holding K and killing B releases the checks in
R[].** The entire capstone table is data over this primitive, and an internal boss lock is
the degenerate case where R = just that boss's own checks (it resolves nothing else).

**We largely have this already** — greenfield/eldenring/features/boss_locks.py, mode B
("Boss Keys"). What exists today:

- The **boss<->region join** is data: `REGION_BOSSES {region: [(ap_id, flag, reward)]}`
  (matt-free, pre-generated). This is the `{boss, region}` input.
- The **lock item** is `Boss Key: <Boss>` (progression), minted one per kept boss.
- The **release edge** is the dungeon sweep: `DUNGEON_SWEEP_FLAGS {boss_defeat_flag:
  [member_ap_ids]}` plus a client handler (P3b-client, pending) that grants the members when
  the boss-defeat flag fires. `sweepLockGates {flag: Boss Key}` **defers** that release until
  the key has arrived. Net: **hold key AND kill boss -> checks release** — exactly the
  primitive. And it gates *rewards only, never the fight*, so it cannot soft-lock.

Gaps to turn this into the full capstone model (backlog, not blockers):

1. **Member set is dungeon-derived, not region-resolved.** Sweep members come from the
   DarkScript EMEVD per-dungeon; the location-keyed `DUNGEON_SWEEPS` variant that would let a
   boss release an *arbitrary region's full check set* is empty (needs the ItemLotParam
   boss-reward-location join). The capstone model wants `capstone_boss -> all checks in R[]`,
   so this join is the main missing piece.
2. **DLC is excluded** (v0.2 scope filters `DLC_REGIONS`). The DLC carve in 3a needs this
   lifted.
3. **Multi-boss regions coarsen to one representative key** — `sweepLockGates` routes every
   sweep in a region to its first base Boss Key because no per-boss defeat-flag join exists.
   A region holding both a capstone and internal bosses needs per-boss precision.
4. **Legible-key layer** — today the lock is a synthetic `Boss Key: <Boss>`. The capstone
   model wants the vanilla key (Academy Glintstone Key, two Great Runes, Messmer's Kindling)
   as the lock where one exists; the rename/messaging layer (er-legible-key-locks-spec) maps
   synthetic -> vanilla.

So the answer to "do we have the capacity": yes at the mechanism level, no at the coverage
level. Reaching the capstone model is (1) the boss-reward-location join, (2) DLC un-scoping,
(3) per-boss flag precision, (4) the legible-key mapping — all on top of the existing
boss_locks feature, not a new subsystem.

## 8. Status

Design-approved (Opus + Fable + Alaric, 2026-07-08). Not yet built. Downstream work:
region-spine surgery (er-region-spine-surgery-spec), legible-key rename layer
(er-legible-key-locks-spec), and the fold-in curation weighting (curated_fill /
important_locations). Rules A and B are new acceptance criteria for any capstone-lock impl.
