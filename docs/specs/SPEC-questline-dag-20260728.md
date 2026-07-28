# SPEC — model the questlines as a DAG

**Status:** design brief, nothing built. Written 2026-07-28 by the session that shipped the Fortissax
softlock fix (`6df0a22` → `2a13b6d`), while that context was still warm. Alaric's ask, verbatim:
*"I want to model all the questlines as a dag."*

**Read first:** `greenfield/gen_data.py` around `QUEST_GATED_FLAGS` — every set folded into it is a
piece of this graph discovered one screen at a time, and its comments carry the provenance rules that
should survive into the DAG.

---

## 1. What this replaces, and what it must not lose

Today a quest-gated check gets **one blunt instrument**: a missable tag, which forbids *required*
progression there (`features/missable_locations`, item-rule, default on). 214 checks carry it, 172 of
them labelled `questline`.

That is deliberately conservative and it works: the check stays randomised and obtainable, and a
player who does the quest gets it. What it costs is **surface** — 172 checks, several of them the
memorable ones, can never carry anything a seed needs, and a whole class of interesting seed shapes
("the Dectus half is behind Ranni's chain") is unreachable by construction.

The DAG's promise is that a quest-gated check becomes ORDINARY: fill may place progression there
because the logic knows what it costs to get. **The bar to clear is not "the graph is pretty" — it is
that a seed with progression on a quest check is still provably winnable.** Until an edge is proven,
its check keeps the missable tag. The tag is the floor, not the competition.

## 2. The vertices are FLAGS, not "quests"

Nothing in the game data knows what a "questline" is. What exists:

- **Event flags** — the only real vertices. A check is a flag; a quest step is a flag; an NPC's state
  is a flag.
- **NPC state BANDS** — the closest thing to an authored questline. `$Event(3419)` "NPC311 Peninsula
  Fort Castle Lord" (Edgar) owns the mutually-exclusive band **3405-3417**; `$Event(3699)` (Patches)
  owns **3685-3699**. A band is a state machine and therefore already a linear DAG; the edges within
  it are free once the band is parsed. See `_NPC_STATE_GATED` in gen_data for the two that were read
  by hand.
- **Item handovers** — `esd_gifts.tsv` (48 live checks): NPC gives item X behind acquisition flag Y.
- **Talk conditions** — `esd_flags.tsv` (5219 rows) is the raw material: which flags an ESD state
  machine TESTS, per path. This is the biggest untapped input in the repo.

## 3. Inputs, and what each can actually prove

| source | rows | proves | blind to |
|---|---|---|---|
| `lot_gates.tsv` | 227 pairs, 126 resolvable | a check's award co-occurs with a test of flag Y | polarity (`EndIf` inverts); 91 pairs have no region handle at all |
| `treasure_enablers.tsv` | 172 | what enables a `StartDisabled=1` treasure | corpse-carried (`ForceCharacterTreasure`, 148 sites) |
| `msb_gated_treasures.tsv` | 186 | MSB-side disable/enable | 🛑 `StartDisabled=1` is THE CHEST, not an access gate — see the memory of that name before using it |
| `esd_gifts.tsv` | 48 checks | NPC hands item behind flag | 31 gift lots have no acquisition flag |
| `esd_gates.tsv` | 192 | which flag opens which shop range | shops only |
| `esd_flags.tsv` | 5219 | every flag an ESD tests, per path | says a flag MATTERS, not that it is a prerequisite |
| boss arenas | 1 known | a fight that does not exist until a quest creates it | **no screen covers this class at all** — see §5 |

`tools/datamine_esd_gates.py` already implements the hard part of reading ESD: an
**environment-carrying descent** from root states, so a `(lot, gate)` pair binds at its call site and
cannot cross-contaminate between two callers. The DAG builder should extend that walk rather than
start a new reader.

## 4. The three hard problems

**(a) Polarity.** `EndIf(EventFlag(X))` means the body needs X *clear* — the opposite of the naive
read. A gate corpus without a per-context sense column is a set of candidate pairs, not edges. Assign
sense during triage and record it; a wrong-polarity edge is an unwinnable seed, which is worse than
no edge.

**(b) An edge is a claim about REACHABILITY, and reachability here is per-seed.** Under `num_regions`
the seed keeps a subset of regions. A quest chain whose step sits in an excluded region has no source
vertex, so its target must degrade to unreachable — and therefore to unrequirable. **The DAG must
compose with region locks, not sit beside them.** Concretely: an edge is only usable as an access
rule if every ancestor's check is in the kept set. When it is not, fall back to the tag. This is the
single constraint most likely to be got wrong, because it is invisible on a full-region seed.

**(c) Warps make most "physical" gating moot, and one class survives it.** A region Lock lights that
region's graces, so the player warps past Ranni's chain into Lake of Rot, past the medallion lifts,
past the Pureblood Medal. Those are NOT edges worth modelling — the model already handles them. What
survives a warp is a fight or a pickup that **does not exist yet**. Model that; ignore the rest.

## 5. The class no screen sees

Every corpus above reads an AWARD SITE. Lichdragon Fortissax (f510110) appears in **none** of them,
because what the questline gates is not the award — it is whether the fight exists. Fia's Deathbed
Dream is entered through an NPC-owned portal with no grace of its own.

The screen that would derive this class, described but not written: resolve each boss's spawn/enable
event in its arena map's EMEVD through the `$InitializeEvent` **call sites** (the same resolution that
took `lot_gates` from ~1% of the corpus to 617 pairs) and report every boss whose enable condition
tests a flag its own map never sets. Fortissax is one KNOWN member; the class is not closed, and
`_BOSS_ARENA_QUEST_GATED` says so in its own comment.

## 6. Shape of the delivery

Suggested tiers, each independently shippable and each leaving the tag in place for whatever it does
not cover:

1. **Emit the graph, assert nothing.** `greenfield/questline_dag.tsv`: `(source_flag, target_flag,
   sense, evidence, tool)`. Ship it beside the other corpora, render it in the check browser, and let
   it be read by a human for a week. No world behaviour changes.
2. **Corroborate.** The keeper test re-derives it and asserts the overlap with the 172 hand/derived
   `questline` tags. If the graph does not RE-FIND most of what a year of hand audits found, the
   graph is wrong — that is the same argument `_MULTI_SITE` earns its trust with.
3. **Access rules for the proven subgraph only.** A check whose full ancestry is derived, polarity
   known, and entirely inside the kept region set becomes an ordinary check with a rule. Everything
   else keeps the missable tag. Measure how many checks actually graduate — if it is 20 of 172, that
   may still be the right 20.
4. **Then** consider the interesting seeds (progression on quest checks, questline-aware hints).

## 7. Acceptance cases

Any implementation should be argued against these before it is believed. Each is a real report or a
real audit finding, not a hypothetical:

- **Fortissax / Fia** (`f510110` ← Cursemark handover `f400392`) — the arena-existence class. The
  motivating case, and the one no award-site screen can see.
- **Golden Seed at Stormhill Shack** (`f400191`, gates `3708`/`3709`/`1041389414`) — three ways to
  trigger one pickup; a DAG with a single edge here is wrong.
- **Edgar / Revenger's Shack** (5 checks behind state `3409` in band 3405-3417) and **Patches /
  Murkwater Cave** (`31007010`/`31007030` swap on `3691`) — mutually-exclusive state bands, and the
  Patches pair is the case where it is still UNKNOWN in-game whether a player can get both.
- **Fire Knight Queelign** (`f400694`/`f400696`) — two sites, order decides which drop lands where.
  The DAG must not claim a site.
- **Rold Medallion** (Melina, after Morgott) and **Drawing-Room Key** (Tanith) — plain handovers,
  the easy end, useful as the first graduating cases.

## 8. Rules of engagement

- **Derive the datum, don't pin the symptom.** Every edge names its tool and its evidence row.
- **Refusing to answer beats answering wrong.** An unresolvable gate keeps the tag; it does not get a
  guessed edge. A false edge is an unwinnable seed; a missing edge costs one filler slot.
- **Absence from a corpus is not evidence of safety.** Say it in the docstring of whatever you build,
  because every screen so far has needed that sentence.
- **The live-game oracle is Alaric.** Two corrections in one afternoon on this exact topic: Fia's
  Mist is NOT in the chain (it drops from Fia's Champions, whom you warp to and hit), and Ash of War:
  Golden Land is an ordinary pickup. "Quest-adjacent" is not the test.
