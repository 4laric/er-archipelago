# SPEC — model the questlines as a DAG

**Status:** ✅ **TIER 1 SHIPPED 2026-07-28** — `tools/build_questline_dag.py` →
`greenfield/questline_dag.tsv` (283 edges over 154 checks), gated by
`greenfield/eldenring/tests/test_gf_questline_dag.py`. **No world behaviour changed; every check
named in the table still carries its missable tag.** Tiers 2-4 are open; §9a records what tier 1
measured and what it changed about the plan below. Originally written 2026-07-28 by the session that
shipped the Fortissax softlock fix (`6df0a22` → `2a13b6d`), while that context was still warm.
Alaric's ask, verbatim: *"I want to model all the questlines as a dag."*

**CC evidence increment, 2026-08-17 (#789):** the flag-only machine graph remains intact, and a
typed evidence union (`questline_model.tsv`) adds revision-pinned CC BY-SA 4.0 ordering claims from
Elden Ring Wiki. This closes the graph's ability to *display* the known Fortissax arena-existence
hole and represent item prerequisites such as the Hole-Laden Necklace without laundering goods ids
into the event-flag namespace. It still changes no world behaviour; see §9c.

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
- **NPC-state vocabulary** — `esd_flags.tsv` (5219 rows). ⚠️ **CORRECTED 2026-07-28.** This line
  used to read "which flags an ESD state machine TESTS, per path". It is the other way round: the
  table records every flag an NPC talk ESD **SETS**, with its sense, talk id and map
  (`tools/datamine_esd_flags.py` says so in its own docstring, and the file header repeats it). The
  distinction is the whole value of the table — SETS is what ATTRIBUTES a bare 4-digit questline
  flag to an NPC on a map, which is how `source_kind=npc_state` is derived. Nothing in the repo
  currently records which flags an ESD tests; that would be a new datamine.
  🛑 And it does NOT contain the NPC-state BANDS named above: 3405-3417 (Edgar) and 3685-3699
  (Patches) appear NOWHERE in `esd_flags.tsv` — they were read out of EMEVD
  `$Event(3419)`/`$Event(3699)` by hand. Deriving bands needs the EMEVD corpus, not this table.

## 3. Inputs, and what each can actually prove

| source | rows | proves | blind to |
|---|---|---|---|
| `lot_gates.tsv` | 227 pairs, 126 resolvable | a check's award co-occurs with a test of flag Y | polarity (`EndIf` inverts); 91 pairs have no region handle at all |
| `treasure_enablers.tsv` | 172 | what enables a `StartDisabled=1` treasure | corpse-carried (`ForceCharacterTreasure`, 148 sites) |
| `msb_gated_treasures.tsv` | 186 | MSB-side disable/enable | 🛑 `StartDisabled=1` is THE CHEST, not an access gate — see the memory of that name before using it |
| `esd_gifts.tsv` | 48 checks | NPC hands item behind flag | 31 gift lots have no acquisition flag |
| `esd_gates.tsv` | 192 | which flag opens which shop range | shops only |
| `esd_flags.tsv` | 5219 | every flag an ESD **SETS**, per talk (⚠️ corrected — this row said *tests*) | polarity of the test that CONSUMES it; nothing here records what an ESD tests |
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

---

## 9a. What TIER 1 actually measured (2026-07-28) — and the four things it changes about §1-8

`tools/build_questline_dag.py` is AP-free and artifact-free: it joins only committed
`greenfield/*.tsv` plus the generated `data.py` / `missable_locations.py`, so it runs in the agent
sandbox and in the CI `generators` job, and `build.ps1` re-emits it beside the check browser. The
committed table is diff-gated; `test_gf_questline_dag.py` holds the corroboration floor, the
acceptance cases and a freshness/determinism check.

```
edges 280 over 154 target check(s) | sense: set 152, clear 20, unknown 108
by tool: lot_gates 173, esd_gifts 95, treasure_enablers 12
source kind: world 187, npc_state 88, check 5
CORROBORATION: 99 of 154 target checks (64%) are ALREADY missable-tagged
cross-region edges 48 (3 whose target is NOT missable-tagged)
alt_group semantics: single 151, any 11, unknown 35, all 2
edges DEGRADED to unusable by a guard: esd-received-memo 66, treasure-verb-crossproduct 28,
  context-branch-unresolved 7, esd-paths-disagree 3, lot_gates-senses-disagree 2, enabler 2
source region located by: flag_decode 75, setter_map 40, esd_talk_map 33, test_map 15, none 117
```

⚠️ **These are the POST-REVIEW numbers, and the review moved them a long way** — `set` 182→152,
`clear` 62→20, `unknown` 39→108. Nothing about the game changed; three guards were added that
should have been there, and each one converts a confident edge into an admitted refusal. §9b has
the accounting.

**1. The two senses are different animals, and only one of them is a candidate access rule.**
`sense=set` (182 edges, 122 targets) is a PREREQUISITE. `sense=clear` (62 edges, 38 targets) is an
EXCLUSION — the check is LOST once the source fires, which is an argument FOR the missable tag and
can never become an access rule. §1 treats the tag as one blunt instrument; it is actually covering
two populations, and only the first is what tier 3 can graduate.

**2. Grouping siblings is not optional — and saying what the grouping MEANS is a separate job.**
§7 warns that "a DAG with a single edge here is wrong" for the Golden Seed; three AND-edges is
equally wrong. So edges carry an `alt_group` key for the site they were read at, AND a
`group_semantics` column that claims nothing unless the data proves it: `any` only where the members
are separate call sites of one common event (f400191's three triggers — asserted by name), `all`
only where they are the `&&` conjuncts of one enabler condition (f1039537050's three — asserted as
the counter-fixture). Everything else is `unknown`, which is 35 of the 48 multi-edge groups.
🛑 The first cut of this file documented **every** group as "need ANY ONE of them", which is false
on rows the tool itself emits and would have licensed an under-constrained rule. It was our claim
wearing the game's clothes — the exact laundering CONTRIBUTING's "Constraint ownership" section
describes.

**3. Polarity resolved better than §4a feared, but only because the datamine had already done the
hard half.** 123 of the 228 `lot_gates` rows are `commonarg/WaitFor`, and `_common_sigs()` in
`datamine_lot_gates.py` *already* drops acquisition-range params and bail-out params — so what
survives is a positive requirement **by construction**, not by this tool's reading. What is NOT
resolvable is the treasure-verb population: `datamine_lot_gates` emits one row per
(gate-context × verb), so the same `(check, gate)` pair appears under BOTH
`if/EnableAssetTreasure` and `if/DisableAssetTreasure` when the event does both on different
branches. Which branch the gate governs is not in the table — 20 (check, gate) pairs carry both
verbs. Those 28 rows are `sense=unknown`, part of a 108-edge unknown population, and a test fails if
the lot_gates half of it ever empties (a polarity table with no refusals has grown a default).

**4. Check → check edges barely exist: 5 of 283.** Almost every prerequisite is a world or NPC-state
flag, not an item. So tier 3 is not "AND these locations together" — it is "can_reach the region
that SETS the source flag", which is the same shape `test_gf_lot_gates_cross_region` already
screens for, upgraded from a tag to a rule. That also means **`source_locator` is load-bearing**:
117 of 283 edges place their source nowhere at all, and the weakest locator (`test_map`, 15 edges)
says where a flag MATTERS, not where it lives — good enough for a missable tag, never for a rule.

### The three candidates tier 1 surfaced, and why NONE of them is a finding yet

`test_gf_lot_gates_cross_region` reads **only** `lot_gates.tsv` and holds unprotected cross-region
gates there at zero — the new table agrees (0 for that corpus, over 20 cross-region target checks).
The other two corpora have never been screened this way, and they produce three unprotected
cross-region prerequisites. The test WARNS on a green run rather than asserting either way, because
a tile-straddle border and a real gate are indistinguishable from here:

- **`f580600` ← `f9146`** (Leda's message ← Messmer, `m21_01`). ⭐ **Not new, and that is the point:
  it is named as "the one real cross-region prerequisite, still unwired" in the 07-26 AND 07-27
  handoffs, and tier 1 re-derives it automatically instead of it needing a human to remember.**
  `WaitFor(EventFlag(580600) || EventFlag(9146))` — the alternation is with the check's OWN
  acquisition flag ("already taken"), so 9146 is a genuine requirement. This is the first case that
  should graduate, and it is one line either way (tag it, or give it the rule).
- **`f1039537050` / `f1039537060` ← `f1040530655`** (Mt. Gelmir ← Altus, near Bower of Bounty).
  🛑 **Suspect the geometry before the gate.** The enabler waits on THREE flags
  (`1039520655 && 1039530655 && 1040530655`) whose numbers decode to three ADJACENT overworld tiles
  — m60_39_52, m60_39_53, m60_40_53 — none of which appears in `msb_flag_region.tsv` or
  `flag_lots.tsv`. That is the signature of one encounter replicated per tile across a region
  border, which is exactly the "tiles LEGITIMATELY span regions" trap, not a questline. Needs the
  live-game oracle before anyone tags anything.

### What tier 1 deliberately did NOT do

- No world module reads `questline_dag.tsv`. Not one tag changed, not one rule was written.
- The NPC-state **bands** (§2) are not derived — see the §3 correction: they are not in
  `esd_flags.tsv` and need the EMEVD corpus, which the sandbox does not have.
- The arena-existence class (§5) is untouched, and `f510110` is asserted **ABSENT** from the table
  so that a populated graph is never read as a covered one. If a future widening makes it appear,
  the test goes red on purpose: read the edge, do not delete the assertion.

## 9b. What an adversarial review of tier 1 found (same day, before anything consumed it)

Tier 1 was reviewed by a second agent briefed to attack it rather than summarise it. It found two
blockers, and both were the *shape* of failure this repo documents rather than anything exotic —
worth recording, because the next tier will be written by someone who did not watch it happen.

**BLOCKER 1 — a constraint we owned, written down as if the game owned it.** `alt_group` was
documented, in four places, as "edges sharing a key are ALTERNATIVES: the target needs ANY ONE of
them". That is false on rows the tool itself emits: the f1039537050 group holds the three `&&`
conjuncts of one `WaitFor`. Read as an OR, one flag stands in for three — an **under-constrained**
rule, which is the unwinnable-seed direction. Nothing had consumed it yet, so the cost was a
column (`group_semantics`) and a counter-fixture; had tier 3 shipped first, the cost would have
been a seed. CONTRIBUTING's "Constraint ownership" says to name the owner — GAME / ARCHIPELAGO /
US — before designing around a constraint. This one was US, and it never said so.

**BLOCKER 2 — a documented guard that was dead code.** `_enabler_sense` refused to call a flag a
prerequisite when it sat in a `||` alternation. The clause regex was `\(([^()]*\|\|[^()]*)\)`, and
`EventFlag(` contains parentheses, so it could **never** match `WaitFor(EventFlag(a) || EventFlag(b))`.
The refusal had never once fired; f580600 ← 9146 was reaching `set` by fall-through while the basis
string said `conjunctive`, and every fixture passed because the fall-through produced the answer the
fixture expected. Now tokenised, and `test_the_enabler_alternation_guard_actually_fires` calls the
function on a disjunction directly — the only kind of test that separates a live guard from a
decorative one.

**The tests were sense-blind, and a mutation proved it.** Inverting the ESD `1/0` mapping (92 edges)
and flipping `EndIf` to `set` (minting exactly the false prerequisites the docstring warns about)
both left the tool at exit 0 with every acceptance case green. Nothing asserted a *sense* outside
f400191; the corroboration ratio, the edge-count floors and the unknown-nonempty check are all
blind to polarity, and the byte-diff gate only notices a *change*, never a from-birth bug. Fixed
with one fixture per dialect — f65660 ← 11007992 (the `EndIf` inversion) and f400470 ← 1047419201
(the ESD `gate_sense=1` mapping) — each pinned to the construct it depends on, so the failure names
the rule that broke rather than a number that moved. Both mutations now hard-fail.

**39 of 48 `clear` edges were bookkeeping, not exclusions.** `esd_gifts.tsv` says in its own header
that `gate_sense==0` marks the "not yet received" acquisition flag, and measurement confirmed the
majority of `clear` sources are set by the *awarding talk itself*. Those are memos, not questline
steps whose firing costs you the check — producer 3 already dropped the identical class via
`self_set_flags`, and producer 2 now degrades them to `unknown` with a tally. This is why the
exclusion count fell 62 → 20: **the drop is the fix, not a regression.**

## 9c. CC-wiki corroboration is a typed evidence layer, not a new oracle (2026-08-17)

The award-site graph cannot describe two important shapes found in a human walkthrough:

1. a prerequisite may be an **item**, not an event flag (`Hole-Laden Necklace`, goods 2008008);
2. a quest may gate whether an **arena exists**, leaving no award-site edge (`f400392 → f510110`,
   Cursemark of Death before Fortissax).

`greenfield/questline_cc_wiki.tsv` records concise adapted claims with exact page id, revision id,
timestamp, pinned URL, and CC BY-SA 4.0 license. `tools/build_questline_model.py` unions those rows
with the machine DAG using typed node ids (`flag:` and `item:`), while preserving which evidence is
`game_data` and which is `cc_wiki`. The generated page renders the CC evidence in a separate panel
so corroboration cannot be mistaken for derivation.

The first slice covers Fia, Ranni, Ymir, Millicent, and Patches. It deliberately includes one
machine-overlap fixture (Patches) to prove the layers can corroborate each other, one machine-blind
fixture (Fortissax), and one cross-id-space fixture (the Necklace). Keeper tests assert all three,
plus exact-revision attribution and the absence of any runtime consumer.

🛑 Wiki ordering is evidence of ordering, not proof of the game's internal event flag. Numeric ids
still come from the vanilla-data side of this repo. A CC row may join those two facts, but must keep
both provenances visible. Nothing in `greenfield/eldenring/` imports `questline_model.tsv`; promoting
an edge to access logic remains tier 3 and needs the game-derived predicate, region composition,
and fill regression described above.

Also corrected: a comment claiming "12 pairs carry both verbs" (recomputed: 20), a §9a claim that
all 39 unknowns were treasure-verb rows (28 of 108), and the §3 *table row* for `esd_flags.tsv` —
the first pass corrected the prose bullet and left the table saying "tests", which is precisely the
half-applied edit CONTRIBUTING rule 9 is about. A lot_gates pair contradicting itself now degrades
the same way an ESD one does; there had been no reason for the asymmetry, only an oversight.

**One more hole, found by mutation-testing the fix itself.** With the group resolver written inline
in `build()`, *disabling the downgrade rule outright* — every group keeps its producer's hint, i.e.
the original blocker restored — left the entire suite green, because no group in today's data
happens to mix senses or hints. A rule the data does not currently reach is a rule that rots, and
asserting it only through the emitted table is not asserting it at all. It is now
`_resolve_group_semantics()` at module level, with a test that feeds it the synthetic groups the
corpus does not yet contain. Generalise: **a guard whose triggering condition is absent from the
corpus needs a direct call, not a table to look at.**

### ✅ The last hole in "positive by construction" is CLOSED — measured, 2026-07-28

Alaric linked the decompiled EMEVD the same day, so the two holes that had been *argued* safe were
measured instead. `commonarg/WaitFor → set` covers 123 of the 173 `lot_gates` edges, which makes it
the single largest polarity claim in the table, and it rested on `_common_sigs()` having already
dropped acquisition-range and bail-out params. Two things it does not close by construction:

1. the negation test is LOCAL (`!` immediately before `EventFlag(p)`), so a GROUP negation
   `WaitFor(!( … EventFlag(p) … ))` would read as positive when it means the opposite — a polarity
   **inversion**, i.e. a false prerequisite, i.e. an unwinnable seed;
2. a `||` inside the WaitFor makes the flag one of several ways in rather than a requirement —
   over-constraining, the safe direction, but still not what the row claims.

**Both are empty.** Of the 6 gate params `_common_sigs()` selects across 6 common events, **0** sit
in a group negation and **0** sit in a disjunction; all six are pure conjuncts. The Golden Seed's
own handler reads `WaitFor(EventFlag(eventFlagId3) && !AllBatchEventFlags(eventFlagId,
eventFlagId2))` — a positive requirement AND'd with "not already taken", exactly as claimed.

It is a **command, not a sentence in a comment**: `build_questline_dag.py --verify-commonarg`
re-runs the measurement. It cannot live in CI (the EMEVD is licensing-restricted and Windows-only),
so it is opt-in on `ER_EVENT_DIR`, on the `ER_ARTIFACTS_VV` precedent in AGENTS §5. It refuses
rather than reports clean when the corpus is absent, when nothing was examined, or when the file's
braces do not balance — a truncated mount read would otherwise print two reassuring zeroes. Verified
by breaking it: a synthetic group-negated param in event 90005750 turns it red and names the param.

### ✅ Both cross-region candidates ADJUDICATED — Alaric, in-game, 2026-07-28

The whole point of emitting candidates rather than verdicts was that only a human playing the game
can tell a gate from a border. Both calls came back the same day, and both are now **wired, not
just recorded** — a note in a handoff is not a gate, which is exactly how `f580600` survived two
handoffs unprotected.

**`f580600 ← f9146` is REAL.** *"message from leda requires defeating messmer".* The Message from
Leda does not exist until Messmer is dead, and a region Lock lights Belurat's graces — so the player
warps to the pickup and finds nothing. Fill could put required progression there. Tagged via
`gen_data._ENABLER_CROSS_REGION`, with `tests/test_gf_enabler_cross_region.py` as its keeper. That
keeper asserts the **population**, re-derived from the tsv each run, not the flag: a fixture cannot
catch the next one.

**The Gelmir pair is NOT a gate.** *"unseen blade: this is a classic rise puzzle where you have to
interact with three objects near the rise to open the door"*, and *"slumbering egg is probably in
the same rise"*. So the AND-group is **real** — the DAG reads those three flags as `semantics=all`,
correctly, and an OR reading would have been the under-constrained rule §9b warns about — but all
three objects stand at the rise. The cross-region reading is `1040530655` decoding to tile
`m60_40_53` (Altus) while the rise sits **on** the Gelmir/Altus boundary: a BORDER, not a gate,
which is the tile→region arity trap. Independently corroborated by the flag's own EMEVD setter event
name, `Magician's Tower_Stopping the gimmick device` — a mechanism, not a quest.

That second one is a hand entry, which this repo permits only where the derivation genuinely cannot
reach — and "gate or border" is a question about the *game*. So it carries a date, a source and a
reason, and a third test asserts every adjudication is still REACHED by the derivation: an exemption
that has stopped protecting anything gets deleted, not kept as belt-and-braces.

**What this says about tier 1's shape.** Two candidates, one real defect and one artifact, both
resolved in a day by a human reading a table that refused to guess. That is the tier working: had
the tool adjudicated either one itself, it would have been right once and wrong once, and nobody
would have known which.

**Now newly possible, and the obvious next increment:** with the EMEVD linked, the 28
`treasure-verb-crossproduct` edges are no longer structurally unresolvable. Reading which BRANCH of
the enabling event each gate governs would convert the largest remaining `unknown` population into
real polarity — and it is the same call-site resolution that took `lot_gates` from ~1% of the corpus
to 617 pairs.

## 9c. The fourth corpus — the #1085 condition extractor (2026-08-27)

Tier 1's three producers are **award-site** corpora: each pairs a flag test with an award in the
same event. §9a names the three things that cost, and this addendum records which two are now paid
and which one is not.

`tools/extract_questline_conditions.py` (issue #1085, phase 2) resolves the guard cone of an award
**per branch** — `else` arms negated, talk-list menu entries carrying the condition they were
registered under, item consumption scoped to the PATH — down to roots with the **setter cited**.
`--dag-corpus` emits `greenfield/questline_conditions.tsv`, one row per (award site, root), and
`build_questline_dag.py` reads it as producer 4 under `tool=questline_conditions`.

**GAP (a), `source_locator`: partly paid, and only partly.** The extractor walks THROUGH the setter,
so a root arrives with the file/event that writes it — a locator by construction, and a stronger one
than `test_map` (where a flag MATTERS) could ever be. It does not close the gap: a setter in
`common.emevd` names no map, so 812 of the corpus's 1513 edges are still unplaced. The three
award-site corpora are **unchanged**: still 120 unplaced of 300.

**GAP (c), f510110: the premise changed, deliberately.** §9a said Fortissax is "asserted **ABSENT**
so that a populated graph is never read as a covered one… if a future widening makes it appear, the
test goes red on purpose: read the edge, do not delete the assertion." That is what happened. The
assertion was **rewritten to hold both halves** rather than deleted:

* f510110 is **still absent from every award-site corpus** — the blind spot of §5 is unchanged, and
  an award-site corpus that started claiming it would be a defect, not progress;
* f510110 **is present via the extractor**, with `map:m12_03` (Deeproot), `BOSS_KILL(f12030800)`
  (Champions; the band edge `4127 && 12030800 -> 4128` is `common.emevd.dcx.js $Event(4139)`) and
  `goods:8191` (Cursemark of Death — `t322001203_x41` sets f12039161 immediately after
  `PlayerEquipmentQuantityChange(ItemType.Goods, 8191, -1)` at `t322001203.py:913`) among its 59
  sources.

**GAP (b), the `unknown` polarity population: untouched.** The extractor emits `set` only. It
resolves no IRREVERSIBLE-arm root at all, so there is no exclusive alternative to read an EXCLUSION
off, and minting `clear` from negated guards would be a guess ("keep this OFF" is a self-gate far
more often than a questline branch). The 125 `unknown` edges are still the three award-site corpora's.

### What the fourth corpus is NOT allowed to claim

1. **`group_semantics` is always `unknown`.** A cone unions the arms of a disjunction, and a
   disjunction met further down a setter chain is not even marked — so a site's roots are neither
   proven alternatives nor a proven conjunction. Under this table's own rule (*a consumer may act on
   `any`/`all` only*), **every extractor edge is inert as a rule**. It is a locator and a lead.
2. **An unreadable cone is refused wholesale.** `cone_completeness=unreadable` — a guard that could
   not be read at all (`UNSET_FLAG`, `MANY_SETTERS`, `WORKVALUE_UNRESOLVED`, an unrecognised
   predicate) — drops the site: 4539 rows refused and counted. Only `complete` and `budget_capped`
   are admitted, because a cone that merely stopped WALKING can miss a prerequisite, never invent
   one, while a cone with an unread guard cannot vouch for the roots beside it.
3. **The corroboration ratchet is not blended.** The floor stays on the award-site population, whose
   number did not move (54%, 88/164). The extractor corpus is measured separately — 10% (45/441),
   floored separately at 5% — because it reaches every readable award site, not only the NPC
   handovers a missable audit concentrates on, and a ratio over a different population is not the
   same measurement wearing a bigger N.

Non-flag roots enter as **namespaced** sources (`goods:8191`, `map:m12_03`) with
`source_kind=item` / `map_access`: a goods param id is a different id space from an event flag and
must not be read as one.

The three phase-1 claims phase 2 **retracted** (f400020's f10009308/f10009336, f400041's
f1043379223 — all self-gates set by the awarding branch itself) are kept out by the **rule** that
retracted them (path-scoped consumption + per-branch `else` negation), not by a denylist: a denylist
would assert the symptom and let the rule rot.
