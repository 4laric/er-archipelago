#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_questline_dag.py -- TIER 1 of SPEC-questline-dag-20260728: emit the graph, assert nothing.

WHAT THIS IS. One table, `greenfield/questline_dag.tsv`, of directed edges between EVENT FLAGS:

    source_flag  --(sense)-->  target_flag

`target_flag` is always a LIVE AP CHECK. `source_flag` is a flag the game tests before that check's
award can happen. `sense` says which STATE of the source the award needs -- and the two senses are
different animals, which is the whole reason this table exists rather than a list of "gates":

    sense=set    the source must be SET      -> a PREREQUISITE. Candidate access rule (tier 3).
    sense=clear  the source must be CLEAR    -> an EXCLUSION. The check is LOST once the source
                                                fires. This can never be an access rule; it is the
                                                argument FOR the missable tag, not against it.
    sense=unknown  the corpus does not encode it. NO EDGE MAY BE USED. Tallied, never guessed.

WHAT THIS IS NOT -- and this paragraph is the point of the file.

  * 🛑 It is NOT an access-rule generator. Nothing in the world reads this table. Tier 1 of the spec
    is "emit the graph, assert nothing"; the missable tag stays exactly where it is on every check
    named here. A `sense=set` edge is a CANDIDATE, and the thing that would promote it is a human
    reading this file, not this file's own confidence.
  * 🛑 An edge is CO-OCCURRENCE plus a polarity rule, not proof. `datamine_lot_gates.py` pairs every
    flag test in an event with every award in that event -- a cross product -- so a test that sits
    on a branch which never reaches the award still emits a row. This tool inherits that.
  * 🛑 ABSENCE FROM THIS TABLE IS NOT EVIDENCE OF SAFETY. Every corpus feeding it reads an AWARD
    SITE. A questline that gates whether a FIGHT EXISTS leaves no award-site trace at all, and the
    motivating case of the whole spec -- f510110, Fortissax, behind Fia's Deathbed Dream -- is
    absent from this table BY CONSTRUCTION. `--check` asserts that absence out loud, so that nobody
    reads a populated graph as a covered one. See SPEC §5 and gen_data._BOSS_ARENA_QUEST_GATED.

POLARITY, THE THING THAT MAKES OR BREAKS THIS (SPEC §4a)
--------------------------------------------------------
A false prerequisite is an unwinnable seed. A missing one costs a filler slot. So polarity is
assigned from a table of constructs, per row, and every construct not in that table yields
`unknown` rather than a plausible guess.

`lot_gates.tsv` records the construct verbatim in its `context` column precisely so this decision
happens here, once, in the open:

    commonarg/WaitFor   set      The gate arrived as a literal at an `$InitializeCommonEvent` call
                                 site and the callee tests it in a NON-NEGATED, LOCAL `WaitFor`.
                                 This is the one shape the datamine itself already filtered for:
                                 `_common_sigs()` drops acquisition-RANGE params (AllBatchEventFlags
                                 -- "already taken", not a prerequisite) and drops BAIL-OUT params
                                 (`EndIf(EventFlag(p))`, `if (p) {... EndEvent()}` -- a completion
                                 test whose polarity is inverted). What survives is a positive
                                 requirement BY CONSTRUCTION, not by this tool's reading.
                                 ✅ AND NOW MEASURED, 2026-07-28, against the real corpus (see
                                 `--verify-commonarg`). Two holes were argued to be safe but
                                 unchecked: a group negation `!(... EventFlag(p) ...)` evading the
                                 local negation test, and an `||` inside the WaitFor. Both are
                                 EMPTY: of the 6 gate params `_common_sigs()` selects, 0 sit in a
                                 group negation and 0 sit in a disjunction -- all six are pure
                                 conjunctions. So this row is verified, not merely reasoned.
    WaitFor             set      `WaitFor(... EventFlag(X) ...)` blocks until X is set.
    !WaitFor            clear    the test is negated inside the WaitFor.
    EndIf               clear    `EndIf(EventFlag(X))` TERMINATES the event when X is set, so the
                                 award below it runs only while X is CLEAR. This is the inversion
                                 the lot_gates header warns about, and reading it the naive way is
                                 how a false prerequisite gets minted.
    !EndIf              set      `EndIf(!EventFlag(X))` -- terminates while X is clear.
    anything with       unknown  🛑 THE VERB IS A CROSS PRODUCT, NOT A BINDING. Rows whose context
    /EnableAssetTreasure         carries a treasure verb are emitted once per (gate-context, verb)
    /DisableAssetTreasure        pair, so the SAME (check, gate) appears under both
    /EnableObjAct                `if/EnableAssetTreasure` AND `if/DisableAssetTreasure` when the
    /DisableObjAct               event does both on different branches. Which branch that gate
                                 governs is not in the table. Measured 2026-07-28: 20 (check, gate)
                                 pairs carry both verbs. Guessing either way is a coin flip on an
                                 unwinnable seed, so they are `unknown`. (This read "12" until it
                                 was RECOMPUTED in review -- a number in a comment is a claim, and
                                 claims rot.)
    ? / EventFlag /     unknown  accumulator (`flag &= EventFlag(X)`) and branch forms. The flag
    if / GotoIf / SkipIf         feeds a variable or a jump whose consuming branch is not recorded.
    WaitForEventFlag             (arg 1 carries ON/OFF, but it only ever co-occurs with a treasure
                                 verb here, so the cross-product objection applies anyway.)

`esd_gifts.tsv` is the happy case: `datamine_esd_gates.py` walks the ESD with an environment-carrying
descent and emits `gate_sense` ITSELF (1 = set, 0 = clear), per path. It is taken as given -- with
one guard: if the same (source, target) appears with BOTH senses across paths, the flag is not a
requirement in either direction and the pair degrades to `unknown` (`esd-paths-disagree`).

`treasure_enablers.tsv` carries `gate_verbatim` and explicitly does NOT encode polarity. Its nine
`external_gate_flags` rows get a deliberately narrow parse (see `_enabler_sense`): `set` only when
the flag appears non-negated inside a `WaitFor(... && ...)` conjunction or an enclosing
`if (EventFlag(X))`, and NEVER when it sits in a `||` alternation with something other than the
target's own acquisition flag. Everything else is `unknown`. Nine rows do not justify a parser; they
do justify saying which nine.

SIBLING EDGES: `alt_group` GROUPS THEM, `group_semantics` SAYS WHAT THE GROUPING MEANS
--------------------------------------------------------------------------------------
SPEC §7 names the trap: the Stormhill Shack Golden Seed `f400191` has THREE ways to trigger it
(3708 / 3709 / 1041389414) and "a DAG with a single edge here is wrong". Three AND-edges is equally
wrong. So sibling edges are grouped by the SITE they were read at (`alt_group` = tool + target +
event/talk) -- that is what makes them siblings in the data rather than in our opinion.

🛑 GROUPING IS NOT SEMANTICS, AND THE FIRST VERSION OF THIS FILE CONFLATED THEM. It documented
`alt_group` as "the target needs ANY ONE of them" -- flatly, for every group. That is false on rows
this tool itself emits: the `treasure_enablers` group for f1039537050 holds three flags whose own
`gate_verbatim` is `WaitFor(EventFlag(a) && EventFlag(b) && EventFlag(c))`, a CONJUNCTION, and 16 of
41 multi-edge groups mixed `set` with `clear`, under which "any one" is not even coherent. An OR
read of that group licenses an UNDER-constrained rule -- one flag standing in for three, which is
the unwinnable-seed direction. It was a constraint WE owned, undocumented, written down as if the
game owned it: exactly the laundering CONTRIBUTING's "Constraint ownership" section is about.
(Found in review, 2026-07-28, before anything consumed it.)

So the meaning is a COLUMN now, per group, and it claims nothing unless the DATA proves otherwise:

    any       PROVEN alternatives: the group is `commonarg` rows for one common event, and each row
              is a SEPARATE `$InitializeCommonEvent` CALL SITE (`_common_arg_gates` iterates call
              sites and emits one row each). N independent instances of the same handler, each
              awaiting its own flag and each awarding the same lot, so whichever fires first pays
              out. f400191 is exactly this, and it is asserted by name.
    all       PROVEN conjunction: `treasure_enablers` rows whose external gates are the `&&`
              conjuncts of ONE condition above the enable call, none of them in an alternation.
    unknown   everything else, and it is the majority. Several flag tests in one EMEVD event body
              (`lot_gates` non-commonarg) have a control flow this corpus does not record; ESD gift
              rows are "one row PER GATE PATH" but the tsv carries no path id, so AND-within-a-path
              and OR-across-paths are indistinguishable once they land in one group.

A group is downgraded to `unknown` if its members disagree about which of those they are, if it
mixes senses, or if any member's sense is `unknown`. A consumer may only act on `any` / `all`.

SOURCE ATTRIBUTION -- what KIND of thing the prerequisite is
-------------------------------------------------------------
    check       the source flag is itself a live AP check -- the only kind that could become a
                pure item/location rule with no region reasoning at all. Measured: rare.
    npc_state   an NPC talk ESD SETS it (`esd_flags.tsv`). This is the questline vocabulary: a bare
                4-digit id like 3708 is not decodable, but "talk 102001110 on m11_10 sets it" is a
                datum. ⚠️ SPEC §3 describes esd_flags.tsv as "which flags an ESD TESTS". That is
                WRONG -- the tool's own docstring and header say SETS, and the distinction matters:
                SETS is what makes the flag attributable to an NPC.
    world       set by a map's EMEVD and nothing else.
    unknown     no corpus places it.

Region resolution uses the same four locators, in the same precedence, as
`greenfield/eldenring/tests/test_gf_lot_gates_cross_region.py::_gate_region_resolver` -- flag-number
decode, then setter map, then common-event call-site map, then (weakest) the test-site map. That
test is the keeper for the region half; `test_gf_questline_dag.py` asserts this tool AGREES with it
on the overlapping rows, so the two copies cannot drift silently.

INPUT:  committed `greenfield/*.tsv` + the generated `eldenring/{data,missable_locations}.py`.
        AP-free and artifact-free: it runs in the agent sandbox, like build_check_browser.py.
OUTPUT: greenfield/questline_dag.tsv

USAGE:
    python tools/build_questline_dag.py --probe    # print the tallies, write nothing
    python tools/build_questline_dag.py            # write greenfield/questline_dag.tsv
    python tools/build_questline_dag.py --check    # re-emit to memory, diff against the committed
                                                   # file, exit 1 on drift (the CI shape)
    python tools/build_questline_dag.py --verify-commonarg
                                                   # NEEDS the decompiled EMEVD (ER_EVENT_DIR or
                                                   # elden_ring_artifacts/event). Re-measures the
                                                   # two holes in the `commonarg/WaitFor -> set`
                                                   # argument against the real corpus and exits 1
                                                   # if either has become non-empty. Cannot run in
                                                   # CI (the artifacts are licensing-restricted and
                                                   # Windows-only), which is exactly why it is a
                                                   # COMMAND and not a sentence in a comment: the
                                                   # claim it backs is the polarity of 123 of the
                                                   # 173 lot_gates edges, and a claim with no way
                                                   # to re-run it is folklore with syntax
                                                   # highlighting (CONTRIBUTING rule 10).
"""
import argparse
import collections
import csv
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GF = os.path.join(ROOT, "greenfield")
PKG = os.path.join(GF, "eldenring")
OUT = os.path.join(GF, "questline_dag.tsv")

COLUMNS = ["source_flag", "target_flag", "sense", "evidence", "tool",
           "basis", "alt_group", "group_semantics", "source_kind", "source_region",
           "source_locator",
           "target_region", "cross_region", "target_ap_id", "target_name"]


# ---- polarity table -----------------------------------------------------------------------------
# Every entry is argued in the module docstring. A context ABSENT from here is `unknown`, which is
# the whole reason it is a lookup and not an if-chain that falls through to a default of "set".
_CONTEXT_SENSE = {
    "commonarg/WaitFor": ("set", "commonarg-positive-by-construction"),
    "WaitFor": ("set", "waitfor-blocks-until-set"),
    "!WaitFor": ("clear", "waitfor-negated"),
    "EndIf": ("clear", "endif-bailout-inverts"),
    "!EndIf": ("set", "endif-negated-bailout"),
}
# A context carrying one of these verbs is a (gate-context x verb) CROSS PRODUCT -- see the
# docstring. The verb does not bind to the gate, so the row cannot be given a polarity.
_VERB_MARKERS = ("/EnableAssetTreasure", "/DisableAssetTreasure",
                 "/EnableObjAct", "/DisableObjAct", "/ForceCharacterTreasure")


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _rows(name, tally=None):
    """A committed greenfield tsv, comment lines stripped.

    The header is the first NON-comment line: every one of these files opens with a provenance
    block, and a DictReader handed the raw handle takes a `#` line as its header and yields NOTHING
    -- an empty result that reads as a clean run (CONTRIBUTING rule 2). gen_data has the same guard.
    """
    path = os.path.join(GF, name)
    if not os.path.isfile(path):
        if tally is not None:
            tally["missing_input:" + name] += 1
        return []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        out = list(csv.DictReader(
            (ln for ln in fh if not ln.lstrip().startswith("#")), delimiter="\t"))
    if not out:
        sys.exit("FATAL: %s parsed to ZERO rows. An empty input is a failure, not a clean run." % name)
    return out


def _int(value):
    value = (value or "").strip()
    return int(value) if value.lstrip("-").isdigit() else None


# ---- region resolution --------------------------------------------------------------------------
# MIRRORS test_gf_lot_gates_cross_region._gate_region_resolver, deliberately and with the same
# precedence. It is a SECOND copy, which this repo normally treats as a smell -- so
# test_gf_questline_dag.py asserts the two agree on every row they both see. A copy with a
# cross-check is a different thing from a copy that can drift silently.
def _region_resolver():
    rg = _load_module("region_groups", os.path.join(GF, "region_groups.py"))
    play2ap = rg.PLAY2AP
    dungeon = {(r.get("map_id") or "").strip(): (r.get("region") or "").strip()
               for r in _rows("dungeon_regions.tsv")}
    tiles = {(r.get("warpUnlockFlag") or "").strip(): (r.get("mapTile") or "").strip()
             for r in _rows("grace_flags.tsv")}
    play = {(r.get("grace_flag") or "").strip(): (r.get("play_region_id") or "").strip()
            for r in _rows("grace_region_map.tsv")}
    votes = collections.defaultdict(collections.Counter)
    for warp, tile in tiles.items():
        region = play2ap.get(play.get(warp, ""))
        m = re.match(r"(m6[01])_(\d\d)_(\d\d)", tile or "")
        if region and m:
            votes[(m.group(1), int(m.group(2)), int(m.group(3)))][region] += 1
    tile_region = {k: c.most_common(1)[0][0] for k, c in votes.items()}
    # An empty or collapsed join would place every gate as "unknown region" and the tool would report
    # a clean, useless graph. Refuse rather than emit one.
    if len(tile_region) <= 100:
        sys.exit("FATAL: the grace->tile->region join resolved only %d tiles; it has drifted. "
                 "Refusing to emit a graph whose regions are silently blank." % len(tile_region))

    def by_flag(flag):
        s = str(flag)
        if len(s) == 8 and s[4] == "7":
            return dungeon.get("m%s_%s" % (s[0:2], s[2:4]))
        if len(s) == 10 and s[0] == "1":
            return tile_region.get(("m60", int(s[2:4]), int(s[4:6])))
        if len(s) == 10 and s[0] == "2":
            return tile_region.get(("m61", int(s[2:4]), int(s[4:6])))
        return None

    def by_map(map_field):
        """A `|`-joined map list -> one region, or None.

        Genuinely one-to-many. If the maps disagree this REFUSES rather than taking the first --
        an ambiguous gate resolved by first-wins is exactly the confident wrong answer the whole
        spec is written against.
        """
        regions = set()
        for mid in (map_field or "").split("|"):
            mid = mid.strip()
            m = re.match(r"(m6[01])_(\d\d)_(\d\d)", mid)
            if m:
                regions.add(tile_region.get((m.group(1), int(m.group(2)), int(m.group(3)))))
            elif re.match(r"m\d\d_\d\d", mid):
                regions.add(dungeon.get(mid[:6]))
        regions.discard(None)
        return regions.pop() if len(regions) == 1 else None

    by_flag.by_map = by_map
    by_flag.tiles = len(tile_region)
    return by_flag


class World(object):
    """The generated side: which flags are live checks, where they are, what is already protected."""

    def __init__(self):
        data = _load_module("gf_data", os.path.join(PKG, "data.py"))
        miss = _load_module("gf_missable", os.path.join(PKG, "missable_locations.py"))
        self.flag_ap, self.flag_name, self.flag_region = {}, {}, {}
        for region, locs in data.LOCATIONS.items():
            for name, ap_id, flag in locs:
                self.flag_ap[flag] = ap_id
                self.flag_name[flag] = name
                self.flag_region[flag] = region
        self.missable = set(miss.MISSABLE_LOCATIONS)
        if not self.flag_ap:
            sys.exit("FATAL: data.LOCATIONS is empty -- no live checks to build a graph over.")
        if not self.missable:
            # The corroboration statistic below is the only evidence this graph is not noise, and it
            # is measured AGAINST this set. An empty one would make every overlap read as 0/N and
            # look like a broken graph rather than a broken oracle.
            sys.exit("FATAL: MISSABLE_LOCATIONS is empty -- the corroboration check would compare "
                     "against nothing and report a meaningless zero.")

    def is_check(self, flag):
        return flag in self.flag_ap


# `gate_verbatim` splices the enabling event's condition text, and
# `datamine_treasure_enablers.py` marks anything BELOW the enable call with a leading `> ` (its own
# tsv header says so; it writes the marker around line 291). A condition below the enable is not a
# precondition of it -- it is what the event does next -- so everything from the first marker on is
# cut before polarity is read. Without the cut, f15007990 took
# `WaitFor(EventFlag(15002805) && InArea(...))`, text BELOW its enabler, as a prerequisite: an
# invented requirement, in the direction that looks safe.
_BELOW_ENABLE = "> "
# 🛑 Operands carry their OWN parentheses, so a clause regex written `\(([^()]*\|\|[^()]*)\)` can
# NEVER match `WaitFor(EventFlag(a) || EventFlag(b))` -- `EventFlag(` violates `[^()]`. The first
# version of this function shipped exactly that, so the alternation refusal below was DEAD CODE
# reading as a protection to anyone auditing the file, and "conjunctive" was minted as the basis for
# disjunctive input. Flag tests are TOKENISED before the clause match now, and
# `test_the_enabler_alternation_guard_actually_fires` calls the function on a disjunction so the
# guard cannot go dead again silently.
_FLAG_TEST = re.compile(r"\b(!?)\s*EventFlag\(\s*(\d+)\s*\)")


def _resolve_group_semantics(members):
    """-> (semantics, was_downgraded) for one alt_group. A module-level function ON PURPOSE.

    It was inline in `build()`, and a mutation test proved that made it untestable in the way that
    matters: DISABLING the downgrade rule entirely left the whole suite green, because no group in
    today's data happens to exercise it. A rule the data does not currently reach is exactly the
    rule that rots -- so it lives here and `test_group_downgrade_rule_is_exercised_directly` feeds
    it the synthetic groups the corpus does not yet contain.

    The producers HINT (`any` for separate call sites of one common event, `all` for the `&&`
    conjuncts of one enabler condition); this decides whether the hint survives contact with the
    group. It does not if the members disagree about the hint, if any member's sense is unknown, or
    if the senses differ -- "any one of these" and "all of these" are both incoherent over a group
    holding a prerequisite AND an exclusion.
    """
    if len(members) == 1:
        return "single", False
    hints = {m["group_semantics"] for m in members}
    senses = {m["sense"] for m in members}
    if len(hints) > 1 or hints == {"unknown"} or "unknown" in senses or len(senses) > 1:
        return "unknown", hints != {"unknown"}
    return hints.pop(), False


def _enabler_sense(flag, target_flag, verbatim):
    """Polarity for a `treasure_enablers.tsv` external gate -- deliberately narrow. See above.

    Returns (sense, basis). `set` only for a flag that
      (a) appears NON-negated and ABOVE the enable call, and
      (b) is not in a `||` alternation with anything but the target's own acquisition flag.
    f580600's `WaitFor(EventFlag(580600) || EventFlag(9146))` is why (b) has an exception at all:
    the alternation is with the CHECK'S OWN flag ("already taken"), so 9146 is a requirement rather
    than one of two ways in.
    """
    text = " ".join((verbatim or "").split())
    if not text:
        return "unknown", "enabler-no-verbatim"
    text = text.split(_BELOW_ENABLE)[0]
    if not text.strip():
        return "unknown", "enabler-condition-is-below-the-enable-call"
    tests = [(neg, int(fid)) for neg, fid in _FLAG_TEST.findall(text)]
    if not any(fid == flag for _neg, fid in tests):
        # Either an ObjAct/asset id and not an EventFlag test at all (a DIFFERENT ID SPACE; reading
        # one as the other is CONTRIBUTING rule 3), or its only occurrence was below the enable.
        return "unknown", "enabler-not-an-eventflag-test-above-the-enable"
    if any(neg and fid == flag for neg, fid in tests):
        return "unknown", "enabler-negated-occurrence"
    tokenised = _FLAG_TEST.sub(lambda m: "%sF%s" % (m.group(1), m.group(2)), text)
    for clause in re.findall(r"\(([^()]*\|\|[^()]*)\)", tokenised):
        if re.search(r"\bF%d\b" % flag, clause):
            others = {int(x) for x in re.findall(r"\bF(\d+)\b", clause)} - {flag}
            # Anything OR'd with our flag other than the target's own acquisition flag means the
            # game offers a SECOND WAY IN, and a second way in is not a requirement.
            if others - {target_flag}:
                return "unknown", "enabler-alternation-not-a-requirement"
            return "set", "enabler-alternation-with-the-checks-own-flag"
    return "set", "enabler-conjunctive-eventflag-test"


def build(verbose=True):
    """-> (rows, tally, notes). Pure: writes nothing."""
    tally = collections.Counter()
    world = World()
    resolve = _region_resolver()

    # --- source attribution vocabularies -------------------------------------------------------
    esd_flags = _rows("esd_flags.tsv", tally)
    npc_state = collections.defaultdict(set)
    for r in esd_flags:
        flag = _int(r.get("flag"))
        if flag is not None:
            npc_state[flag].add(((r.get("talk_id") or "").strip(), (r.get("map_id") or "").strip()))
    if not npc_state:
        sys.exit("FATAL: esd_flags.tsv yielded no NPC-state vocabulary -- source attribution would "
                 "silently label every questline flag 'world'.")
    # talk_id -> the flags THAT talk sets. Used only for the received-memo guard in producer 2.
    npc_state_by_talk = collections.defaultdict(set)
    for r in esd_flags:
        flag = _int(r.get("flag"))
        if flag is not None:
            npc_state_by_talk[(r.get("talk_id") or "").strip()].add(flag)

    lot_to_flag = {}
    for r in _rows("flag_lots.tsv", tally):
        if (r.get("table") or "").strip() != "map":
            continue
        lot, flag = _int(r.get("lot")), _int(r.get("flag"))
        if lot is None or flag is None:
            continue
        # First-wins, but COUNTED. Zero collisions today; if a map lot ever gains a second flag this
        # join starts silently picking one, and a first-wins rule with no tally is the shape of
        # every silent wrong answer in this repo.
        if lot in lot_to_flag and lot_to_flag[lot] != flag:
            tally["flag_lots:map-lot-with-a-SECOND-flag"] += 1
            continue
        lot_to_flag.setdefault(lot, flag)
    if not lot_to_flag:
        sys.exit("FATAL: flag_lots.tsv gave no map lot->flag join; every ESD gift would drop out.")

    def source_kind(flag):
        if world.is_check(flag):
            return "check"
        if flag in npc_state:
            return "npc_state"
        return "world"

    edges = []

    def add(source, target, sense, basis, evidence, tool, alt_group,
            locator="", source_region=None, group_hint="unknown"):
        # Every rejection is TALLIED BY TOOL. A filter with no tally is a lie (CONTRIBUTING rule 4),
        # and an aggregate tally hides WHICH corpus went blind.
        if source == target:
            tally["drop:%s:self-loop" % tool] += 1        # a check's own acquisition flag
            return
        if not world.is_check(target):
            tally["drop:%s:target-not-a-live-check" % tool] += 1
            return
        if source <= 0:
            tally["drop:%s:sentinel-source" % tool] += 1  # 0 / -1 = "no gate", never a flag
            return
        treg = world.flag_region.get(target)
        sreg = source_region
        loc = locator
        if sreg is None:
            sreg, loc = None, ""
        edges.append({
            "source_flag": source, "target_flag": target, "sense": sense, "basis": basis,
            "evidence": " ".join((evidence or "").split())[:180], "tool": tool,
            "alt_group": alt_group, "group_semantics": group_hint,
            "source_kind": source_kind(source),
            "source_region": sreg or "", "source_locator": loc,
            "target_region": treg or "", "target_ap_id": world.flag_ap.get(target, ""),
            "target_name": world.flag_name.get(target, ""),
            "cross_region": ("unknown" if not (sreg and treg) else
                             ("yes" if sreg != treg else "no")),
        })
        tally["sense:" + sense] += 1
        tally["tool:" + tool] += 1

    def locate(gate_flag, row, target_region):
        """(region, locator) for a lot_gates gate. Same four handles, same order, as the keeper test.

        Precedence is strongest-first and each fallback is WEAKER, not merely later:
          flag_decode  the flag's own number encodes its map.
          setter_map   the map(s) whose EMEVD SET it.
          common_map   set only by common.emevd, routed back through the maps that call it.
          test_map     nothing sets it anywhere we can place, so fall back to where it is TESTED,
                       minus the check's own map. This says where the flag MATTERS, not where it
                       lives. It is strong enough to justify a missable tag and NOT strong enough
                       to mint an access rule -- consumers must read `source_locator`.
        """
        region = resolve(gate_flag)
        if region:
            return region, "flag_decode"
        for field, locator in (("gate_map", "setter_map"), ("gate_common_map", "common_map")):
            value = (row.get(field) or "").strip()
            if value:
                region = resolve.by_map(value)
                if region:
                    return region, locator
                return None, "ambiguous"
        test_map = (row.get("gate_test_map") or "").strip()
        if test_map:
            foreign = {resolve.by_map(m.strip()) for m in test_map.split("|") if m.strip()}
            foreign = {r for r in foreign if r and r != target_region}
            if len(foreign) == 1:
                return foreign.pop(), "test_map"
            return None, "ambiguous" if foreign else "no_handle"
        return None, "no_handle"

    # --- producer 1: lot_gates.tsv (EMEVD award-site co-occurrence) ------------------------------
    for row in _rows("lot_gates.tsv", tally):
        target, source = _int(row.get("check_flag")), _int(row.get("gate_flag"))
        if target is None or source is None:
            tally["drop:lot_gates:unparsable"] += 1
            continue
        context = (row.get("context") or "").strip()
        if any(v in context for v in _VERB_MARKERS):
            sense, basis = "unknown", "treasure-verb-crossproduct"
        else:
            sense, basis = _CONTEXT_SENSE.get(context, ("unknown", "context-branch-unresolved"))
            if basis == "context-branch-unresolved":
                tally["context-not-in-polarity-table:" + (context or "?")] += 1
        region, locator = locate(source, row, world.flag_region.get(target))
        # SIBLINGS ARE THE CALL SITE. f400191's three triggers all arrive as arg5 of the same
        # $InitializeCommonEvent(90005750) at the same event; grouping by (target, event) is what
        # makes them alternatives in the DATA rather than in our opinion.
        # Each `commonarg` row is a DISTINCT $InitializeCommonEvent call site (`_common_arg_gates`
        # iterates call sites), so N of them for one lot are N independent handler instances --
        # genuine alternatives. Every other lot_gates context is several tests inside ONE event body
        # whose control flow this corpus does not record, so it claims nothing.
        add(source, target, sense, basis, row.get("evidence"), "lot_gates",
            "lot_gates:%s:%s" % (target, (row.get("event_id") or "").strip()),
            locator=locator, source_region=region,
            group_hint="any" if context.startswith("commonarg/") else "unknown")

    # --- producer 2: esd_gifts.tsv (NPC dialogue handovers) --------------------------------------
    # `datamine_esd_gates.py` emits gate_sense ITSELF, per path, from an environment-carrying descent
    # -- so polarity here is the ESD walk's, not ours. The one thing we add is the disagreement
    # guard: a (source, target) seen with BOTH senses is not a requirement in either direction.
    gift_rows = []
    for row in _rows("esd_gifts.tsv", tally):
        lot = _int(row.get("item_lot"))
        source = _int(row.get("gate_flag"))
        sense_raw = (row.get("gate_sense") or "").strip()
        if lot is None or source is None:
            tally["drop:esd_gifts:unparsable"] += 1
            continue
        target = lot_to_flag.get(lot)
        if target is None:
            tally["drop:esd_gifts:lot-has-no-flag"] += 1
            continue
        if sense_raw not in ("0", "1"):
            tally["drop:esd_gifts:sense-not-binary"] += 1
            continue
        gift_rows.append((source, target, "set" if sense_raw == "1" else "clear", row))
    contradictory = {(s, t) for (s, t, sense, _r) in gift_rows
                     if {sense} != {x for (a, b, x, _q) in gift_rows if (a, b) == (s, t)}}
    for source, target, sense, row in gift_rows:
        basis = "esd-walk-gate-sense"
        if (source, target) in contradictory:
            sense, basis = "unknown", "esd-paths-disagree"
        elif source in npc_state_by_talk.get((row.get("talk_id") or "").strip(), ()):
            # 🛑 A MEMO, NOT AN EXCLUSION. `esd_gifts.tsv`'s own header: "gate_flag with
            # gate_sense==0 is the 'not yet received' acquisition flag". Measured 2026-07-28: 39 of
            # the 48 `clear` edges had a source that the AWARDING TALK ITSELF sets -- so the flag is
            # that talk's bookkeeping ("already handed this over"), not a questline step whose
            # firing costs you the check. Counting those as exclusions inflates the exclusion
            # population with rows that say nothing about reachability. Producer 3 already drops the
            # identical class via `self_set_flags`; this is that rule applied to the corpus that
            # carries it implicitly. The row is KEPT (it is real provenance) and made UNUSABLE.
            sense, basis = "unknown", "esd-received-memo"
            tally["esd_gifts:received-memo-not-a-gate"] += 1
        talks = npc_state.get(source, set())
        maps = "|".join(sorted({m for (_t, m) in talks if m}))
        region = resolve(source) or (resolve.by_map(maps) if maps else None)
        locator = "flag_decode" if resolve(source) else ("esd_talk_map" if region else "")
        # "One row PER GATE PATH" (tsv header) -- but the table carries no path id, so a group is
        # AND-within-a-path and OR-across-paths mixed together, indistinguishable. Claims nothing.
        add(source, target, sense, basis,
            "talk %s gate_sense=%s lot %s" % (row.get("talk_id"), row.get("gate_sense"),
                                              row.get("item_lot")),
            "esd_gifts", "esd_gifts:%s:%s" % (target, (row.get("talk_id") or "").strip()),
            locator=locator, source_region=region, group_hint="unknown")

    # --- producer 3: treasure_enablers.tsv (external gates on a disabled treasure) ---------------
    for row in _rows("treasure_enablers.tsv", tally):
        target = _int(row.get("flag"))
        if target is None:
            tally["drop:treasure_enablers:unparsable-flag"] += 1
            continue
        if (row.get("verdict") or "").strip() == "NO_ENTITY_HANDLE":
            tally["drop:treasure_enablers:no-entity-handle"] += 1
            continue
        external = [x.strip() for x in (row.get("external_gate_flags") or "").split(",") if x.strip()]
        # `self_set_flags` is a MEMO ("this event already ran"), NOT a prerequisite -- the tsv header
        # says so in its own words. An edge built on one inverts the graph.
        selfset = {x.strip() for x in (row.get("self_set_flags") or "").split(",") if x.strip()}
        verdicts = {}
        for raw in external:
            source = _int(raw)
            if source is None:
                tally["drop:treasure_enablers:unparsable-gate-flag"] += 1
                continue
            if raw in selfset:
                tally["drop:treasure_enablers:self-set-memo"] += 1
                continue
            verdicts[source] = _enabler_sense(source, target, row.get("gate_verbatim"))
        # The datamine lists this row's external gates as the operands of ONE condition above the
        # enable call. When EVERY one came back a plain conjunct -- non-negated, above the enable, in
        # no alternation -- the group is an AND and says so. One alternation or one refusal anywhere
        # in the row and the whole group claims nothing.
        hint = ("all" if len(verdicts) > 1
                and all(b == "enabler-conjunctive-eventflag-test" for _s, b in verdicts.values())
                else "unknown")
        for source, (sense, basis) in sorted(verdicts.items()):
            region = resolve(source) or resolve.by_map((row.get("external_flag_set_in") or "").strip())
            locator = "flag_decode" if resolve(source) else ("setter_map" if region else "")
            add(source, target, sense, basis,
                (row.get("gate_verbatim") or "")[:180], "treasure_enablers",
                "treasure_enablers:%s:%s" % (target, (row.get("enabler_event") or "").strip()),
                locator=locator, source_region=region, group_hint=hint)

    # --- post-pass 1: a pair that disagrees with ITSELF is not evidence of anything ---------------
    # Producer 2 applied this per-path for the ESD walk; the other corpora were left without it,
    # so (3383 -> 400033) stood as set AND clear and (31000800 -> 400183) as all three -- the same
    # situation, contradicting verdicts, and no stated reason for the asymmetry (found in review,
    # 2026-07-28). One rule now, every producer: if one corpus says both things about one pair, that
    # corpus does not know.
    verdicts = collections.defaultdict(set)
    for e in edges:
        if e["sense"] != "unknown":
            verdicts[(e["tool"], e["source_flag"], e["target_flag"])].add(e["sense"])
    for e in edges:
        key = (e["tool"], e["source_flag"], e["target_flag"])
        if len(verdicts.get(key, ())) > 1 and e["sense"] != "unknown":
            e["sense"], e["basis"] = "unknown", "%s-senses-disagree" % e["tool"]
            tally["%s:senses-disagree-within-one-corpus" % e["tool"]] += 1

    # --- post-pass 2: resolve group semantics -----------------------------------------------------
    # `alt_group` groups siblings; this decides what the grouping MEANS, and defaults to claiming
    # nothing. A group keeps its producer's hint only when every member agrees on that hint, every
    # member's sense is known, and those senses are all the same -- "any one of these" and "all of
    # these" are both incoherent over a group mixing a prerequisite with an exclusion.
    grouped = collections.defaultdict(list)
    for e in edges:
        grouped[e["alt_group"]].append(e)
    for _key, members in grouped.items():
        resolved, downgraded = _resolve_group_semantics(members)
        if downgraded:
            tally["group-downgraded-to-unknown"] += 1
        for m in members:
            m["group_semantics"] = resolved

    edges.sort(key=lambda e: (e["target_flag"], e["tool"], e["source_flag"], e["sense"]))
    seen, deduped = set(), []
    for e in edges:
        key = (e["source_flag"], e["target_flag"], e["sense"], e["tool"], e["alt_group"])
        if key in seen:
            tally["drop:%s:duplicate-row" % e["tool"]] += 1
            continue
        seen.add(key)
        deduped.append(e)
    return deduped, tally, {"tiles": resolve.tiles, "world": world}


# ---- acceptance fixtures (SPEC §7) --------------------------------------------------------------
# CONTRIBUTING rule 11: the case that motivated the work is the acceptance test, and it is asserted
# on the FINISHED pipeline, by name -- not on a producer in isolation. Each of these is a real
# report or a real audit finding.
def _acceptance(edges):
    """-> list of (ok, label, detail). Never raises; the caller decides what is fatal."""
    out = []
    by_target = collections.defaultdict(list)
    for e in edges:
        by_target[e["target_flag"]].append(e)

    seed = [e for e in by_target.get(400191, []) if e["tool"] == "lot_gates"]
    gates = {e["source_flag"] for e in seed}
    groups = {e["alt_group"] for e in seed}
    semantics = {e.get("group_semantics") for e in seed}
    out.append(({3708, 3709, 1041389414} <= gates and len(groups) == 1 and semantics == {"any"},
                "f400191 Golden Seed / Stormhill Shack",
                "3 triggers in ONE alt_group with semantics=any (separate call sites of one common "
                "event); found gates %s in %d group(s), semantics %s"
                % (sorted(gates), len(groups), sorted(x for x in semantics if x))))
    out.append((all(e["sense"] == "set" for e in seed) and bool(seed),
                "f400191 polarity",
                "every trigger is a POSITIVE prerequisite (commonarg/WaitFor); senses %s"
                % sorted({e["sense"] for e in seed})))

    # 🛑 THE COUNTER-FIXTURE to the one above, and the reason `group_semantics` exists at all. The
    # Gelmir enabler's three gates are `&&` conjuncts of ONE WaitFor. Documented as "alternatives"
    # -- which is what the first version of this file said of EVERY group -- they would license an
    # UNDER-constrained rule, one flag standing in for three.
    gelmir = [e for e in by_target.get(1039537050, []) if e["tool"] == "treasure_enablers"]
    out.append((bool(gelmir) and {e.get("group_semantics") for e in gelmir} == {"all"},
                "f1039537050 Gelmir enabler -- a CONJUNCTION, not alternatives",
                "three `&&` conjuncts of one WaitFor must read semantics=all; got %s"
                % sorted({e.get("group_semantics") for e in gelmir})))

    rold = [e for e in by_target.get(400001, []) if e["tool"] == "esd_gifts"]
    out.append((bool(rold), "f400001 Rold Medallion (Melina handover)",
                "the easy end of the graph: %d ESD-gift edge(s)" % len(rold)))

    # 🛑 THE TWO SENSE FIXTURES, and why they had to be added. Reviewed 2026-07-28: with only the
    # EXISTENCE fixtures above, inverting an entire dialect's polarity left this tool at exit 0 with
    # every case green -- the ESD 1/0 mapping flipped (92 edges), and `EndIf` flipped to `set`,
    # minting exactly the false prerequisites the docstring warns about. Nothing noticed, because
    # nothing asserted a SENSE outside f400191, and every other guard is sense-blind: the
    # corroboration ratio, the edge-count floors, the unknown-nonempty check. One fixture per
    # dialect, each pinned to the CONSTRUCT it depends on so the failure names the rule that broke.
    endif = [e for e in by_target.get(65660, []) if e["source_flag"] == 11007992]
    out.append((bool(endif) and all(e["sense"] == "clear" for e in endif),
                "f65660 <- 11007992 -- the EndIf INVERSION",
                "`EndIf(EventFlag(X))` ends the event when X is SET, so the award below needs X "
                "CLEAR; reading it the naive way mints a false prerequisite. senses %s"
                % sorted({e["sense"] for e in endif})))
    esd_set = [e for e in by_target.get(400470, []) if e["source_flag"] == 1047419201]
    out.append((bool(esd_set) and all(e["sense"] == "set" for e in esd_set),
                "f400470 <- 1047419201 -- the ESD gate_sense=1 mapping",
                "Great-Jar's Arsenal is handed over behind a SET flag; if the 1/0 mapping inverts, "
                "this is the fixture that says so. senses %s"
                % sorted({e["sense"] for e in esd_set})))

    f580 = [e for e in by_target.get(580600, []) if e["source_flag"] == 9146]
    out.append((bool(f580) and all(e["sense"] == "set" for e in f580),
                "f580600 <- 9146 (treasure enabler)",
                "the one known real cross-region prerequisite; senses %s"
                % sorted({e["sense"] for e in f580})))

    # 🛑 THE NEGATIVE FIXTURE, and the most important line in this file. Fortissax is the case the
    # whole spec was written from, and it is ABSENT here BY CONSTRUCTION -- every corpus above reads
    # an AWARD SITE, and what the questline gates is whether the FIGHT EXISTS. If a future widening
    # ever makes it appear, that is a real finding and this flips: read it, do not silence it.
    out.append((510110 not in by_target,
                "f510110 Fortissax -- ABSENT BY CONSTRUCTION",
                "no award-site corpus can see an arena-existence gate; absence here is the "
                "BLIND SPOT, never evidence of safety (SPEC §5)"))
    return out


def summarise(edges, tally, notes):
    """The measured header. Recomputed on every emit -- these are not prose and cannot go stale."""
    world = notes["world"]
    lines = []
    by_sense = collections.Counter(e["sense"] for e in edges)
    by_tool = collections.Counter(e["tool"] for e in edges)
    by_kind = collections.Counter(e["source_kind"] for e in edges)
    targets = {e["target_flag"] for e in edges}
    set_targets = {e["target_flag"] for e in edges if e["sense"] == "set"}
    clear_targets = {e["target_flag"] for e in edges if e["sense"] == "clear"}
    tagged = {f for f in targets if world.flag_ap.get(f) in world.missable}
    cross = [e for e in edges if e["cross_region"] == "yes"]
    cross_untagged = [e for e in cross if world.flag_ap.get(e["target_flag"]) not in world.missable]
    weak = collections.Counter(e["source_locator"] for e in edges)
    lines.append("edges %d over %d target check(s) | sense: set %d, clear %d, unknown %d"
                 % (len(edges), len(targets), by_sense["set"], by_sense["clear"],
                    by_sense["unknown"]))
    lines.append("by tool: %s" % ", ".join("%s %d" % kv for kv in sorted(by_tool.items())))
    lines.append("source kind: %s" % ", ".join("%s %d" % kv for kv in sorted(by_kind.items())))
    lines.append("targets: %d with a PREREQUISITE (sense=set), %d with an EXCLUSION (sense=clear)"
                 % (len(set_targets), len(clear_targets)))
    # THE CORROBORATION NUMBER (SPEC §6 tier 2). A graph that re-finds what a year of hand audits
    # found is credible; one that overlaps nothing is noise wearing a tsv. It is printed as a RATIO
    # and never as a pass.
    lines.append("CORROBORATION: %d of %d target check(s) are ALREADY missable-tagged (%d%%); "
                 "the tag set holds %d checks in total"
                 % (len(tagged), len(targets),
                    round(100.0 * len(tagged) / max(1, len(targets))), len(world.missable)))
    lines.append("cross-region edges: %d (%d whose target is NOT missable-tagged)"
                 % (len(cross), len(cross_untagged)))
    groups = {}
    for e in edges:
        groups[e["alt_group"]] = e["group_semantics"]
    lines.append("alt_group semantics: %s (a group claims OR/AND only where the DATA proves it)"
                 % ", ".join("%s %d" % kv
                             for kv in sorted(collections.Counter(groups.values()).items())))
    # Counted off the EMITTED edges, not off `tally`: the tally counts input ROWS, which are deduped
    # afterwards, so quoting it here would claim more degraded edges than the table holds.
    lines.append("edges DEGRADED to unusable by a guard (each is a refusal, not a loss): %s"
                 % (", ".join("%s %d" % kv for kv in sorted(collections.Counter(
                     e["basis"] for e in edges if e["sense"] == "unknown").items())) or "none"))
    lines.append("source region located by: %s"
                 % ", ".join("%s %d" % (k or "none", v) for k, v in sorted(weak.items())))
    drops = sorted((k, v) for k, v in tally.items() if k.startswith("drop:"))
    lines.append("dropped rows (a filter with no tally is a lie): %s"
                 % (", ".join("%s %d" % (k[5:], v) for k, v in drops) or "none"))
    unresolved = sorted((k, v) for k, v in tally.items()
                        if k.startswith("context-not-in-polarity-table:"))
    if unresolved:
        lines.append("contexts with NO polarity rule (-> unknown, never guessed): %s"
                     % ", ".join("%s %d" % (k.split(":", 1)[1], v) for k, v in unresolved))
    return lines


_HEADER = """\
# AUTO-GENERATED by tools/build_questline_dag.py -- DO NOT EDIT, re-emit.
# TIER 1 of docs/specs/SPEC-questline-dag-20260728.md: EMIT THE GRAPH, ASSERT NOTHING.
# Directed edges over EVENT FLAGS. target_flag is always a live AP check.
#   sense=set     the source must be SET   -> a PREREQUISITE. A CANDIDATE access rule, not one yet.
#   sense=clear   the source must be CLEAR -> an EXCLUSION. Never an access rule; this is the
#                 argument FOR the missable tag.
#   sense=unknown the corpus does not encode the polarity. UNUSABLE. Tallied, never guessed.
# 🛑 NOTHING IN THE WORLD READS THIS FILE. Every check named here keeps its missable tag.
# 🛑 An edge is CO-OCCURRENCE + a polarity rule, not proof: datamine_lot_gates pairs every flag test
#   in an event with every award in it, so a test on a branch that never reaches the award is here.
# 🛑 ABSENCE IS NOT SAFETY. Every corpus below reads an AWARD SITE. A questline that gates whether a
#   FIGHT EXISTS leaves no award-site trace -- f510110 (Fortissax), the case this spec was written
#   from, is absent BY CONSTRUCTION and the tool asserts that absence out loud.
# alt_group groups edges READ AT ONE SITE; `group_semantics` says what that grouping MEANS, and it
#   is `unknown` unless the data proves otherwise -- `any` only for separate call sites of one
#   common event (f400191's three triggers), `all` only for the `&&` conjuncts of one enabler
#   condition (f1039537050's three). 🛑 An earlier version called EVERY group "alternatives"; that
#   was OUR claim wearing the game's clothes, and an OR read of a conjunction is an
#   UNDER-constrained rule. A consumer may act on `any` / `all` only.
# source_locator: how the source's region was placed -- flag_decode > setter_map > common_map >
#   test_map (WEAKEST: where the flag MATTERS, not where it lives -- good enough for a missable tag,
#   never for an access rule). Empty = unplaced.
# MEASURED THIS RUN (recomputed on every emit; the tool hard-fails on a degenerate parse):
"""


def emit(edges, tally, notes, path=OUT):
    body = []
    body.append(_HEADER)
    for line in summarise(edges, tally, notes):
        body.append("#   %s\n" % line)
    body.append("# ACCEPTANCE (SPEC §7, asserted on the finished pipeline by name):\n")
    for ok, label, detail in _acceptance(edges):
        body.append("#   [%s] %s -- %s\n" % ("ok" if ok else "FAIL", label, detail))
    body.append("\t".join(COLUMNS) + "\n")
    for e in edges:
        body.append("\t".join(str(e[c]) for c in COLUMNS) + "\n")
    text = "".join(body)
    if path:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return text


def _guard(edges, tally, notes):
    """Refuse to write a table that looks fine and means nothing (CONTRIBUTING: 'the silent wrong
    answer'). Each of these has a mechanism attached, not just a threshold."""
    world = notes["world"]
    if not edges:
        sys.exit("FATAL: zero edges. An empty graph is a FAILURE, not 'no questlines found'.")
    if not any(e["sense"] == "set" for e in edges):
        sys.exit("FATAL: not one PREREQUISITE edge survived polarity assignment. The context "
                 "vocabulary in lot_gates.tsv has changed and _CONTEXT_SENSE no longer matches it "
                 "-- re-triage the contexts rather than loosening the table.")
    targets = {e["target_flag"] for e in edges}
    tagged = {f for f in targets if world.flag_ap.get(f) in world.missable}
    if not tagged:
        sys.exit("FATAL: the graph corroborates NOTHING that a year of hand audits already tagged "
                 "missable. That is a broken join, not a discovery -- check the flag/lot joins "
                 "before trusting a single edge.")
    bad = [label for ok, label, _d in _acceptance(edges) if not ok]
    if bad:
        sys.exit("FATAL: acceptance case(s) lost: %s\nThe pipeline no longer reports the cases it "
                 "was built for. Fix the derivation, not the fixture." % "; ".join(bad))


def verify_commonarg():
    """Re-measure the two holes in `commonarg/WaitFor -> set`. -> exit code.

    THE CLAIM UNDER TEST. `_CONTEXT_SENSE` maps `commonarg/WaitFor` to `set` on the grounds that
    `datamine_lot_gates._common_sigs()` has already reduced those params to positive requirements:
    it drops acquisition-RANGE params (`AllBatchEventFlags` -- "already taken") and BAIL-OUT params
    (`EndIf(EventFlag(p))`, `if (p) {... EndEvent()}` -- completion tests with inverted polarity),
    and requires a non-negated occurrence inside a local `WaitFor`. That is 123 of the 173
    `lot_gates` edges, so it is the single largest polarity claim in the table.

    THE TWO HOLES it does not close by construction, both argued to be safe:
      1. the negation test is LOCAL (`!` immediately before `EventFlag(p)`), so a GROUP negation
         `WaitFor(!( ... EventFlag(p) ... ))` would read as positive when it is the opposite;
      2. a `||` inside the WaitFor makes the flag one of several ways in, not a requirement --
         over-constraining, which is the safe direction, but still not what the row claims.

    Both were UNCHECKED until the corpus was linked (2026-07-28), and both measured EMPTY: 0 of 6
    selected gate params in either shape. This re-runs that measurement rather than leaving a
    number in a comment to rot. It is opt-in because the EMEVD is licensing-restricted and absent
    from CI -- the same `ER_ARTIFACTS_VV` precedent AGENTS §5 sets for staged artifact work.
    """
    sys.path.insert(0, HERE)
    try:
        import datamine_lot_gates as lot_gates                       # noqa: PLC0415
    except ImportError as exc:
        print("cannot import datamine_lot_gates: %s" % exc, file=sys.stderr)
        return 1
    common = os.path.join(lot_gates.EVT, "common_func.emevd.dcx.js")
    if not os.path.isfile(common):
        print("NO CORPUS: %s absent. Set ER_EVENT_DIR to the decompiled EMEVD, or run this on a "
              "tree with elden_ring_artifacts/event/. REFUSING to report a clean run over nothing "
              "-- an empty check is a failure, not a pass." % common, file=sys.stderr)
        return 1
    text = open(common, encoding="utf-8", errors="replace").read()
    # A truncated mount read would silently shrink the corpus and print two reassuring zeroes.
    if text.count("{") != text.count("}"):
        print("REFUSING: %s has unbalanced braces (%d/%d) -- a truncated read, not a corpus. Every "
              "count below would be a false negative."
              % (common, text.count("{"), text.count("}")), file=sys.stderr)
        return 1
    sigs = lot_gates._common_sigs()
    marks = list(lot_gates.EVENT_RE.finditer(text))
    bodies = {int(m.group(1)): text[m.end(): marks[i + 1].start() if i + 1 < len(marks) else len(text)]
              for i, m in enumerate(marks)}
    negated, disjunctive, examined = [], [], 0
    for eid, (params, _lot_idx, flag_idx, _batch) in sorted(sigs.items()):
        body = bodies.get(eid, "")
        for idx in flag_idx:
            param = params[idx]
            pattern = r"\bEventFlag\(\s*%s\s*\)" % re.escape(param)
            for wm in re.finditer(r"\bWaitFor\(([^;]{0,300}?)\)\s*;", body, re.S):
                clause = wm.group(1)
                if not re.search(pattern, clause):
                    continue
                examined += 1
                if "||" in clause:
                    disjunctive.append((eid, param, " ".join(clause.split())[:160]))
                for gm in re.finditer(r"!\s*\(", clause):
                    depth, k = 0, gm.end() - 1
                    while k < len(clause):
                        if clause[k] == "(":
                            depth += 1
                        elif clause[k] == ")":
                            depth -= 1
                            if depth == 0:
                                break
                        k += 1
                    if re.search(pattern, clause[gm.end():k]):
                        negated.append((eid, param, " ".join(clause.split())[:160]))
    if not sigs or not examined:
        print("REFUSING: %d common event(s) with a gate param, %d WaitFor site(s) examined. Nothing "
              "was checked, which is not the same as nothing being wrong." % (len(sigs), examined),
              file=sys.stderr)
        return 1
    print("commonarg gate params: %d common event(s), %d param(s), %d WaitFor site(s) examined"
          % (len(sigs), sum(len(f) for _p, _l, f, _b in sigs.values()), examined))
    for label, hits in (("inside a GROUP negation `!( ... )`", negated),
                        ("inside a DISJUNCTION `||`", disjunctive)):
        print("  %-38s %d" % (label, len(hits)))
        for eid, param, clause in hits:
            print("      event %d param %s: %s" % (eid, param, clause))
    if negated or disjunctive:
        print("\nFAIL: the `commonarg/WaitFor -> set` argument no longer holds for every selected "
              "param. A group-negated one is a polarity INVERSION (a false prerequisite -- an "
              "unwinnable seed); a disjunctive one is an over-constraint. Re-triage those params "
              "before trusting the 123 edges that rest on this rule.", file=sys.stderr)
        return 1
    print("\nOK: every selected gate param is a pure, non-negated conjunct of its WaitFor. The "
          "`commonarg/WaitFor -> set` mapping is MEASURED, not just reasoned.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--probe", action="store_true", help="print the tallies, write nothing")
    ap.add_argument("--check", action="store_true",
                    help="re-emit to memory and diff against the committed file; exit 1 on drift")
    ap.add_argument("--verify-commonarg", action="store_true",
                    help="re-measure the commonarg polarity argument against the decompiled EMEVD "
                         "(needs ER_EVENT_DIR / elden_ring_artifacts/event)")
    args = ap.parse_args(argv)

    if args.verify_commonarg:
        return verify_commonarg()

    edges, tally, notes = build()
    for line in summarise(edges, tally, notes):
        print(line)
    print("acceptance (SPEC §7):")
    for ok, label, detail in _acceptance(edges):
        print("   [%s] %s -- %s" % ("ok" if ok else "FAIL", label, detail))
    _guard(edges, tally, notes)

    if args.probe:
        print("--probe: nothing written")
        return 0
    text = emit(edges, tally, notes, path=None)
    if args.check:
        if not os.path.isfile(OUT):
            print("DRIFT: %s does not exist. Run the tool." % OUT, file=sys.stderr)
            return 1
        current = open(OUT, encoding="utf-8", newline="").read()
        if current != text:
            print("DRIFT: greenfield/questline_dag.tsv is stale. Re-emit with "
                  "`python tools/build_questline_dag.py`.", file=sys.stderr)
            return 1
        print("--check: committed table matches a fresh emit")
        return 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("wrote %s (%d edges)" % (os.path.relpath(OUT, ROOT), len(edges)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
