# Tester archetypes

Three yamls, three pinned seeds. Between them they cover the option space a real player
lands in: the near-default seed, the marquee (`num_regions`), and the DLC.

| # | yaml | seed | what it exercises |
|---|------|------|-------------------|
| A1 | `A1-first-light.yaml` | **11111** | near-default, base game, all regions in play |
| A2 | `A2-the-shattering.yaml` | **22222** | **the marquee** — 4 rolled regions, region locks, great-rune goal |
| A3 | `A3-land-of-shadow.yaml` | **33333** | DLC on, mixed base+DLC regions, Scadutree blessing floor |

All three are verified to generate cleanly at the seed above (2026-07-11).

## Run one

```
python Generate.py --player_files_path <dir with ONE yaml> --seed <the pinned seed>
```

Most testers should be on **A2**. `num_regions` is what turns Elden Ring into an AP game,
so its bugs outrank everything else — and a rolled start is where the nastiest ones live
(can you leave the region you woke up in?).

## Reporting

**Attach the seed and the `AP_*.zip`.** A report that reproduces from data is worth ten that
don't; a paraphrase of what went wrong is a bug we cannot chase. If you can, also attach the
client log.

The most valuable report is not "this crashed" — the client is fairly solid now. It is:

- *"I am stuck and I don't think the game intends this."* A check you cannot reach, a region
  you cannot leave, a key that never showed up.
- *"This item is in the wrong place."* An item that belongs in region X showing up gated
  behind region Y. (This class was rampant; a provenance oracle now catches most of it, but
  the game is the final arbiter.)
- *"The difficulty is absurd here."* Especially in the DLC (A3) — that is the blessing floor
  failing.

## One tester should never launch the game

Generation failures are worse than gameplay bugs: a client bug ruins one evening, a gen
failure blocks an entire multiworld room and gets "Elden Ring" quietly dropped from the
group's yaml set. If you are that tester, your job is to **break `Generate.py`** with hostile
yamls — weird option combinations, extremes, contradictions. Per CONTRIBUTING, any yaml must
either gen clean or reject with a message a player can act on. A `FillError` or a stack trace
is the bug.
