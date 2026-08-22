# v0.4.10 — release blurb

## What you need to update

- **Client:** Required — use the v0.4.10 client with v0.4.10 seeds.
- **APWorld:** Host-only — the room host or generator must install v0.4.10; joining players only
  need the matching client.
- **YAML:** **New YAML optional. Existing YAMLs remain valid.** Generate a fresh template only to
  see and select newly added options such as the Malenia goal.
- **Existing seed/save:** New seed required — finish an active v0.4.9 seed with its matched v0.4.9
  client and APWorld; use a new seed for v0.4.10 features.
- **Profile/assets:** No action — this window does not require a profile or asset reinstall.

## Your friends finally get your stuff

Two measured multiworld defects die in this release, and both were the same shape: Elden Ring
took from the table without giving back.

**Your progression is balanced across every game now.** `cross_game_progression: auto` — the
shipped default — gives every partner game its own near-1/N share of your travelling progression:
your Region Locks, all seven Great Runes when a rune goal is active, the works. Eleven items at a
three-game table land roughly four in each partner and three at home, instead of one batch that
ordinary fill happened to split 2/2/7. Your world reserves the same share of each partner game's
progression in return, so their keys ride your starred checks too. Prefer the old shape?
`aggregate` is its name now, and an explicit percentage or `never` behaves exactly as it always
did.

**Your weapons reach them too.** At the shipped settings a non-Elden-Ring partner received
nothing from an Elden Ring slot but filler — 0 useful items in 498 measured placements — a
fill-order artifact, not anyone's setting. A dedicated pass now places your fair share of useful
gear into partner worlds before the general fill. Re-measured: 0 → 983 useful items delivered
across the CI matrix, and the partner sees the pool's own mix, about one weapon or talisman for
every consumable.

## The wizard stops being homework

The complaint was fair: seven tabs, sixty flat options, all reading as mandatory. The wizard is
five steps now — Start / Options / Seed size / Advanced / Finish — with the old tabs folded into
collapsible sections that lead with the fifteen decisions that actually shape a run and tuck the
tuning behind a live-counted "More". Difficulty opens with **Easy / Standard / Hard** quick-picks
(Standard lands your final region around vanilla Haligtree's scaling; the dials stay real
underneath). The Seed size card stops claiming your Locks never travel — the sentence is derived
from your actual settings now — and starting-region candidates count honestly in the preview
before you generate. The progression-surface grid's counts are live too: every checkbox toggle
recomputes the marginals and totals instead of freezing at first render, and named values render
by name — the slider says `auto`, not a bare `-1`. The emitted yaml is byte-identical throughout:
this is presentation, not behavior.

**Legacy dungeon bosses are Major bosses now.** The LegacyBoss surface class was absorbed into
MajorBoss — a boss standing in a legacy dungeon is a major by any player's reading, and the split
earned nothing but a wizard row. A default seed's progression surface grows by the 22
legacy-standing boss checks that were not already majors: deliberate, and stated here. Yamls that
name `LegacyBoss` keep loading — the spelling is normalized on read — and goal and anchor
selection are unchanged underneath.

## Quality of life at the table

**Auto-upgrade covers every pickup.** The silent raise-to-your-level that received weapons always
got is a real `auto_upgrade` setting now (default on), and it applies to world pickups and chests
too — including the put-it-down-pick-it-up gesture players know from matt's randomizer as the
catch-up for a weapon that arrived before you found your stones. A watchdog names any suppressed
pickup that never became a check, with its `!give` rescue, so the gesture can no longer silently
cost you a weapon.

**Malenia can be the ending.** `goal: malenia` guarantees the Haligtree but hands you Haligtree
Canopy alone once your Great-Rune and region requirements resolve — Loretta, Elphael and the full
descent remain physical play. Works with every existing goal axis.

**The map got more honest.** Consecrated Snowfield is its own rollable region with its own Lock,
grace, scaling and sweeps instead of hiding inside Mountaintops — and the Subterranean
Shunning-Grounds merged into Leyndell, because the well is inside the walls: one region, one
Lock, one wall, and a Great Rune can no longer strand itself on Mohg the Omen.

**Enia's DLC rows leave a no-DLC seed.** Thirty-six Finger Reader checks consume or gate on
Shadow of the Erdtree content; with `enable_dlc: false` they existed forever-uncompletable, and a
required item could park on one — a real reported goal-lock. They leave the seed together now.

## The client stops eating your session

The known issue that closed the v0.4.9 notes is fixed: an enemy-randomizer kill during the
Radahn festival left the fight unfinishable — the client now backfills the festival state when
the boss dies without its ceremony, and the check fires. Alongside it: received items cursor
against your character identity, so a fresh character starts at zero and a reconnect cannot
replay or skip a delivery; a contained panic during item delivery no longer silently stalls the
receive stream; a capital warp the world state cannot resolve is rejected instead of dropping
you mid-air; the withheld-goal gate fails open, so a data gap can never seal the goal room shut;
and the rescue console grew `!grace <name>` / `!unlockgrace` to search and light any named Site
of Grace when a seed strands you.

## What carried over from v0.4.9

No player-facing work is carried over. The v0.4.9 release tag differs from `main` only by its
client gitlink bump, and this window's v0.4.10 client pin supersedes it.
