# Check accuracy: handoff

**Status, 2026-09-22.** Active development of per-check accuracy for this apworld has stopped.
The maintainer is moving to other projects. This page is the complete state of the work, the
bar it ships at, and how to pick up any part of it. Nothing here is a promise that someone will.

## The bar this apworld ships at

**Sweep mode is the default, and a sweep-granted check is a reachable check.** Kill the boss that
owns a check and the check registers, whether or not the pickup itself was placed in the right
region, behind a quest step, or in a spot the logic misjudged. That is the accuracy guarantee:
the boss is reachable, so the check is.

**Everything else is play at your own risk.** A check that no boss sweeps depends on our
placement being right. Most of them are, and the numbers below say how many are not known to
be. Reports are welcome and are triaged through the queues in this document, but there is no one
working those queues today.

| | Rows | Share |
|---|---|---|
| Checks in the table | 4,932 | |
| Sweep-granted by some boss | 4,115 | 83% |
| Not sweep-granted | 817 | 17% |

Of the 817 unswept rows: 421 are shop rows (a merchant or NPC stock line, filed under the
merchant's home region), 137 are already tagged missable and never host required progression,
and 132 carry `(region unconfirmed)` in their name. By region the unswept rows concentrate in
Roundtable Hold (178, mostly NPC stock), Liurnia (118), Caelid (81), Limgrave (81), Altus (50).

The unswept set is the only set where a placement error can cost a player anything. Any future
accuracy work should start there and nowhere else.

**Required progression is confined to hosts the bar makes safe.** Every location that is not on
a trusted allow-list refuses advancement items from every world. Since 2026-09-23 that allow-list
is the maintainer-certified list plus every check that is corroborated by some second source (the
two-family wiki ledger, or thefifthmatt's table with no review queue disputing it), that some boss
sweep grants, and that is not missable: about 3,650 hosts. Corroboration admits a check; the sweep
is what makes it a host. A required item can therefore never sit on a play-at-your-own-risk check,
and the hub, whose rows no boss sweeps, hosts nothing. See
`features/evidence_progression_hosts.oracle_sweep_aps` and `tables/oracle_corroborated_hosts.py`;
the table is refreshed with the oracle pin (`tools/matt_oracle.py --hosts-table`).

## What "accurate" was measured against

Our tables are generated from vanilla game data (`greenfield/gen_data.py`, inputs under
`greenfield/`). They have exactly one independent second opinion: thefifthmatt's hand-curated
slot table in his SoulsRandomizers repository, read locally at a pinned commit by
`tools/matt_oracle.py` and never copied into this tree (licence: read-only; see the tool's
docstring and AGENTS.md "MATT ORACLE"). His table is the ground truth the wider modding
community uses. Requests to consume it directly went unanswered; his licence permits reading it
as a data source, which is what the oracle does.

What the oracle establishes today, at pin `61014252` (his 2026-09-22 head):

- **Item identity**: 4,077 of 4,085 comparable rows agree on which vanilla item a flag awards.
  The 8 disagreements are explained in the tool's allowlist. This gate is green.
- **Missing slots**: 79 slots of his we do not carry, every one allowlisted with a reason
  (keying difference, out of scope by design, or a real pickup with no region evidence).
  This gate is green.
- **Uncovered rows** (report class I): 640 of our 4,932 rows have no counterpart in his table
  at all and get no second opinion. 426 of those are shop rows keyed on the shop flag rather
  than a slot, 159 are sweep-granted, 32 are gestures, 13 common-event awards, 10 other.
- **Region, missable, enemy drops, reachability**: report-only. The two models partition the
  game differently, so a disagreement is a question for a person, not a defect. Those questions
  are the queues below.

The weekly CI job `.github/workflows/matt-oracle.yaml` re-runs the two gates against the pin and
uploads a JSON verdict. Nobody reads it. If the gates go red, it means one of our tables changed
in a way his contradicts, and the fix is in `gen_data.py` or the allowlist, never in `data.py`.

## The open queues, and how to work each one

Every queue is a committed TSV under `greenfield/evidence/`. Every row is our flag, our AP id,
our region or name, and a reviewer's words. None carries anything of his.

### 1. Region review queue: 177 rows, 143 open

`greenfield/evidence/oracle-region-queue.tsv`. A row means his partition puts the pickup with
different neighbours than our region does. 34 rows are ruled (33 `confirmed-ours`, 1 `moved`),
all by an automated evidence pass, none by a person. Only 12 of the 143 open rows are unswept,
so 131 of them cannot affect a player in default mode.

To work it: open the [check browser](https://4laric.github.io/er-archipelago/er-archipelago-check-browser.html),
facet **Oracle region review**, and rule from the evidence shown (map tile, nearest grace, the
region that grace maps to, wiki second opinion). Record verdicts in the
[player review notebook](PLAYER-REVIEW-NOTEBOOK.md), download the backup, then

```bash
python tools/apply_oracle_verdicts.py --queue region notebook.json
```

A `moved` verdict does not move anything. Apply it through the derivation ladder in
`greenfield/gen_data.py` (`M61_TILE_CURATED`, `DUNGEON_REGION_CURATED`, then
`region_overrides.tsv` as a last resort), regenerate, and the row leaves the queue on the next
refresh. The two ledgers from the last human-readable passes are
[ORACLE-MANUAL-REVIEW-2026-09-09.md](ORACLE-MANUAL-REVIEW-2026-09-09.md) and
[ORACLE-MFG-REVIEW-2026-09-10.md](ORACLE-MFG-REVIEW-2026-09-10.md); they explain what the
"ground batches" are and which rows already have coordinates.

### 2. Missable review queue: 100 rows, all open

`greenfield/evidence/oracle-missable-queue.tsv`. He tags the flag missable; our
`MISSABLE_LOCATIONS` does not. Two bases:

- `second-source-missable-disagrees` (30 rows): our own questline extraction also sees a
  losable gate on the award site. Our evidence backs the question.
- `second-source-missable-disagrees-no-local-gate` (70 rows): our extraction sees no gate. If he
  is right, our extractor missed it, and a seed could place required progression behind a
  consumable the player already spent. Only 24 of the 100 rows are unswept.

Same round trip with `--queue missable`. A `missable` verdict must name the mechanism
(`limited-consumable` / `killable-npc` / `questline-progress`) or the tool refuses it, because
`gen_data`'s missable classes are a closed vocabulary. Apply through `gen_data.py`, never by
editing `tables/missable_locations.py`.

### 3. Unplaced pickups: 26 flags

Real, separately collectable pickups we do not ship because no corpus gives them a region. They
are listed by flag in `tools/matt_oracle.py` under `_B_SCOPE_UNPLACED_GLOBAL` with the reason
each was refused. Closing one needs a witness: an observed map, an item coordinate, or a
single-map EMEVD or talk-ESD award, recorded as a hand pin in `gen_data.GLOBAL_RECOVER`.
Issue #1522 documents a circular-evidence bug in the resolver that would need fixing first.

### 4. Acquisition and quest gates: 63 flags

Checks whose acquisition may depend on quest state, NPC survival, or a consumable, listed in
[oracle-review-2026-09-10.tsv](oracle-review-2026-09-10.tsv). 17 have no sweep fallback and are
the ones that matter. Issues #1085 (questline-condition extractor), #1080 (a player's flag-level
conjunction corpus that nothing consumes yet), #1321 (Euporia route) and #1093 (shop liberation)
are the design threads. Issue #1447 and #1508 hold the most detailed player reports.

### 5. Enemy drops: 244 of his flagged drops we do not model

`tools/matt_oracle.py --report` class C. One-time enemy drops that award both the vanilla item
and an AP check are #1099 and #1044; whether they become checks at all is #1437 and #1000. No AP
locations have been added for this class; it was left as a product ruling and never ruled.

### 6. Gestures: 32 rows

We model gesture awards as checks; he does not. Ownership and gating audit is #1438.

## Running the oracle yourself

```bash
git clone https://github.com/thefifthmatt/SoulsRandomizers /tmp/souls
git -C /tmp/souls checkout 610142523e2c765427c3f74361bfb553dc114367
python tools/matt_oracle.py --souls-rando-dir /tmp/souls --report --json out.json
python tools/matt_oracle.py --souls-rando-dir /tmp/souls --region-queue --missable-queue
```

Do not commit anything from the clone. Do not bump the pin without diffing his `itemslots.txt`
between the two commits and re-running both queues; the workflow file's comment records what the
last bump changed and is the template.

## The alternative you should know about

His randomizer has, since his 2026-09-14 commit "External item rando data structures", an
Archipelago consumer of its own: `ExternalItemPreset.FromArchipelago(slotData, scoutedLocations)`
maps every AP location onto his slot key and writes the permutation inside his tool. That is the
path the Bedrock apworld takes. Anyone whose goal is per-check exactness should evaluate building
on that rather than continuing the hand-corroboration here; his table is authoritative by
construction on that path. This apworld's value is elsewhere: region locks, sweep mode,
progression surface, cross-game prefill, a client that ships today.

## Ground rules if you pick this up

- Never edit `greenfield/eldenring/tables/*.py` by hand. Everything there is generated; change
  the inputs and regenerate (`tools/regen_all.py`).
- Never copy a row, a description, an area name or a tag string from his table into this tree.
  Flag numbers are game facts and are fine.
- Never renumber AP ids. Removals are tombstoned (#1521).
- Run the oracle before and after, and quote the class counts in the PR.
- A disagreement with his table is a reason to look, not proof that we are wrong.

## Where the history is

- [MATT-ORACLE-ROADMAP.md](MATT-ORACLE-ROADMAP.md): what the oracle bought, item by item.
- [ORACLE-AUDIT-2026-09-09.md](ORACLE-AUDIT-2026-09-09.md): the last audit baseline.
- [MFG-INTEGRATION-STATUS.md](MFG-INTEGRATION-STATUS.md): the map-pin evidence source.
- `docs/player-reports/`: raw player notes, the most detailed of which came from one tester
  between August 27 and September 19, 2026, and are indexed in issues #1447, #1508, #1514.
