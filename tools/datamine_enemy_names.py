#!/usr/bin/env python3
"""datamine_enemy_names.py -- the DISPLAY NAME of a spawnable character model, where the game
ships one.

WHY THIS EXISTS
---------------
SwiftyTaco, Discord 2026-08-26, on the `spawn_traps` option: *"Am I supposed to put in ids, or the
name of the enemy?"* -- having first tried the ids in `traps`, which is the other option and takes
words. The answer was "ids, and only ids", because `spawn_traps` was born as an escape hatch onto a
catalogue of 390 bare `c<chr>` model numbers. That is a fine yaml for someone who has already looked
a model up and a hostile one for everybody else.

This tool is the table that lets the option take a NAME. `features/traps.py` resolves a name to the
model id at GENERATION TIME and mints exactly the item name it minted before, so the accepted yaml
grows and the emitted contract does not move -- no slot-data key, no `CONTRACT_HASH` move, no client
lockstep. See `SpawnTraps` for that argument stated where it is load-bearing.

WHAT THE GAME ACTUALLY SHIPS, and the reason this table is SMALL
----------------------------------------------------------------
Elden Ring has no per-enemy nameplate, and the params carry no dev names either: the `Name` column
of both `NpcParam.csv` and `AtkParam_Npc.csv` is empty in every one of their 7039 / 12855 rows in
the committed bundle. The ONE place the game names a creature is `NpcName.fmg.xml`, reached through
`NpcParam.nameId`, and that column is set for 188 NpcParam families, of which 31 are spawnable
models. Everything else a player thinks of as an enemy name -- "Godrick Soldier", "Bloodhound
Knight" -- is a WIKI name, not a game string, and this repo does not invent data (CONTRIBUTING,
"Provenance -- derive the datum, don't pin the symptom").

So the honest shape of this table is: every model the game names, plus the handful this project has
already named IN PUBLIC and may therefore quote back. It is not 390 rows and cannot be, and the
option keeps taking raw ids precisely because of that. Adding a curated name later is safe and is
the designed extension point; see `CURATED_NAMES`.

THE DERIVATION
--------------
For each spawnable model in `greenfield/spawn_traps.tsv` (the eligibility oracle -- this tool does
NOT re-derive spawnability):

    names = { NpcName[r.nameId] : how many rows carry it   for r in NpcParam if r.ID // 10000 == chr
                                                            and r.nameId resolves }

A FAMILY OFTEN CARRIES SEVERAL NAMES, and that is content rather than noise: c3200 is six merchants
(Kale, Nomadic, Isolated, Hermit, Abandoned, Imprisoned), c2050 is Ranni AND Renna, c2160 is the
Finger Reader Crone, the Keeper of the Forbidden Lands and Godwyn's Wet Nurse. One model, one name
is a lie either way; the question is only which lie is stable. The rule:

    the name carried by the MOST rows wins, ties broken by the LOWEST nameId.

Row count rather than id order, because the row count is what "this model usually is" means: 16 of
c3200's 35 named rows are Merchant Kale, and picking by id would hand the whole model to whichever
merchant happened to be authored first. The tie-break is by nameId and not by name text so that the
answer cannot move when a translation does.

AND ACROSS MODELS. Three names are carried by two models each (Boc, Latenna, Smithing Master Hewg --
an NPC with a second body). A name has to resolve to ONE model or `spawn_traps: [Latenna]` is not a
specification, so `features/traps.py` resolves a duplicate name to the LOWEST model id and this tool
records the collision in the table rather than hiding it. Lowest id, because it is the one that
exists in the base game.

USAGE
-----
    python tools/datamine_enemy_names.py            # regenerate greenfield/eldenring/enemy_names.py
    python tools/datamine_enemy_names.py --check    # drift gate: exit 1 if the module is stale

Artifacts: reads `elden_ring_artifacts/` under the repo, the same staging every other datamine tool
uses (`python tools/gen_inputs.py --extract elden_ring_artifacts` materialises it from the committed
bundle -- no game install needed). `--check` needs them too; it re-derives and compares.
"""
import argparse
import collections
import csv
import glob
import os
import re
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AR = os.path.join(REPO, "elden_ring_artifacts")
PARAMS = os.path.join(AR, "vanilla_er", "vanilla_er")
SPAWN_TSV = os.path.join(REPO, "greenfield", "spawn_traps.tsv")
OUT = os.path.join(REPO, "greenfield", "eldenring", "enemy_names.py")

#: chr_id -> a name this PROJECT has already published for that model, and may therefore quote back
#: without inventing anything. Every entry is already a public string:
#:
#: 4630 "Runebear"          -- the shipped fixed trap item `Trap: Runebear` (features/traps.TRAPS).
#: 4150 "Basilisk",
#: 2120 "Malenia (Phase 1)",
#: 5280 "Aging Untouchable" -- the three CURATED labels in tools/datamine_spawn_traps.py, which are
#:                             already the visible half of the item name and already yaml keys.
#:
#: A NAME HERE IS A PUBLIC OPTION VALUE. Adding one is safe; REMOVING one fails an old yaml, the
#: same compat rule the curated trap keys obey (issue #114 rule 4). Never add a name you might
#: withdraw, and never add one you cannot cite to something already shipped or already datamined.
CURATED_NAMES = {
    2120: "Malenia (Phase 1)",
    4150: "Basilisk",
    4630: "Runebear",
    5280: "Aging Untouchable",
}


def _npc_names():
    """{nameId: text} from every NpcName FMG in the artifacts, base and both DLC layers."""
    out = {}
    pat = os.path.join(AR, "msg", "**", "NpcName*.fmg.xml")
    for fp in sorted(glob.glob(pat, recursive=True)):
        try:
            body = open(fp, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for m in re.finditer(r'<text id="(\d+)"[^>]*>(.*?)</text>', body, re.S):
            v = m.group(2).strip()
            # %null% and [ERROR] are the FMG's own placeholders for an unassigned row; a row that
            # holds one is not a name and must not become a yaml value.
            if v and v not in ("%null%", "[ERROR]"):
                out.setdefault(int(m.group(1)), v)
    if not out:
        raise SystemExit(
            "FATAL: no NpcName rows under %s -- this tool needs elden_ring_artifacts staged.\n"
            "Run: python tools/gen_inputs.py --extract elden_ring_artifacts"
            % os.path.join(AR, "msg"))
    return out


def _spawnable():
    """The model ids `spawn_traps.tsv` says are spawnable. THAT FILE IS THE ORACLE, not this one:
    naming a model this repo refuses to spawn would put a yaml value in front of a player that
    generation then rejects."""
    if not os.path.isfile(SPAWN_TSV):
        raise SystemExit("FATAL: %s missing -- run tools/datamine_spawn_traps.py first." % SPAWN_TSV)
    with open(SPAWN_TSV, encoding="utf-8", newline="") as fh:
        return [int(r["chr_id"]) for r in csv.DictReader(fh, delimiter="\t")]


def _npc_rows():
    path = os.path.join(PARAMS, "NpcParam.csv")
    if not os.path.isfile(path):
        raise SystemExit(
            "FATAL: %s missing -- this tool needs elden_ring_artifacts staged.\n"
            "Run: python tools/gen_inputs.py --extract elden_ring_artifacts" % path)
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        rd = csv.DictReader(fh)
        for col in ("ID", "nameId"):
            if col not in (rd.fieldnames or ()):
                raise SystemExit("FATAL: NpcParam.csv lacks column %r. A renamed column must fail "
                                 "loudly, not silently derive an empty table." % col)
        return list(rd)


def derive():
    """-> list of dict rows, sorted by chr_id. One row per NAMED spawnable model."""
    text = _npc_names()
    spawnable = _spawnable()
    fam = collections.defaultdict(collections.Counter)   # chr -> {name: rows}
    first_id = {}                                        # name -> lowest nameId carrying it
    for r in _npc_rows():
        try:
            row_id, name_id = int(r["ID"]), int(r["nameId"] or 0)
        except (TypeError, ValueError):
            continue
        if name_id > 0 and name_id in text:
            nm = text[name_id]
            fam[row_id // 10000][nm] += 1
            if nm not in first_id or name_id < first_id[nm]:
                first_id[nm] = name_id

    picked = {}
    for chr_id in spawnable:
        if chr_id in CURATED_NAMES:
            picked[chr_id] = (CURATED_NAMES[chr_id], "curated")
            continue
        cand = fam.get(chr_id)
        if not cand:
            continue
        # rows DESC, then nameId ASC -- see the module docstring. Never by name text.
        best = sorted(cand.items(), key=lambda kv: (-kv[1], first_id[kv[0]]))[0][0]
        picked[chr_id] = (best, "fmg")

    by_name = collections.defaultdict(list)
    for chr_id, (nm, _src) in picked.items():
        by_name[nm.casefold()].append(chr_id)

    out = []
    for chr_id in sorted(picked):
        nm, src = picked[chr_id]
        others = sorted(c for c in by_name[nm.casefold()] if c != chr_id)
        out.append({"chr_id": chr_id, "name": nm, "source": src, "dup": others})
    return out


def ascii_fold(s):
    """'Merchant Kale' with an acute -> 'merchant kale'. The casefolded, accent-stripped form a
    player is likely to type when their keyboard has no acute accent. `features/traps.py` indexes on
    this too, so the unaccented spelling resolves; the canonical spelling is what the table
    carries."""
    return "".join(c for c in unicodedata.normalize("NFKD", s.casefold())
                   if not unicodedata.combining(c))


def render(rows, n_spawnable):
    dups = sum(1 for r in rows if r["dup"])
    lines = [
        '"""AUTO-GENERATED by tools/datamine_enemy_names.py -- DO NOT EDIT '
        '(regenerate: python tools/datamine_enemy_names.py; --check is the drift gate).',
        "",
        "The DISPLAY NAME of a spawnable character model, for the `spawn_traps` yaml option.",
        "",
        "SOURCE = NpcParam.nameId -> NpcName.fmg.xml, plus tools/datamine_enemy_names.CURATED_NAMES.",
        "Small on purpose: %d of the %d spawnable models carry a name here -- the ones the game"
        % (len(rows), n_spawnable),
        "itself names, plus %d this project had already published. Nothing else is invented. See"
        % sum(1 for r in rows if r["source"] == "curated"),
        "the tool's docstring for why, and for the most-rows/lowest-nameId pick rule.",
        '"""',
        "# chr_id -> display name",
        "ENEMY_NAMES = {",
    ]
    for r in rows:
        note = "  # %s" % r["source"]
        if r["dup"]:
            note += "; name also on %s -- lowest id is canonical" % \
                    ", ".join(str(c) for c in r["dup"])
        lines.append("    %d: %r,%s" % (r["chr_id"], r["name"], note))
    lines += [
        "}",
        "",
        "#: chr_id -> 'fmg' (the game's own NpcName row) or 'curated' (a name this project already",
        "#: published). Advisory: nothing branches on it, but a table that cannot say where a row",
        "#: came from is one nobody can audit.",
        "ENEMY_NAME_SOURCE = {",
    ]
    for r in rows:
        lines.append("    %d: %r," % (r["chr_id"], r["source"]))
    lines += [
        "}",
        "",
        "#: The %d model(s) whose name another model also carries. The resolver takes the LOWEST" % dups,
        "#: model id; recorded here so the collision lives in the table and not only in the code.",
        "ENEMY_NAME_COLLISIONS = {",
    ]
    for r in rows:
        if r["dup"]:
            lines.append("    %d: (%r, [%s])," % (r["chr_id"], r["name"],
                                                  ", ".join(str(c) for c in r["dup"])))
    lines.append("}")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="drift gate: exit 1 if the committed module differs from a fresh datamine")
    args = ap.parse_args()

    rows = derive()
    if not rows:
        raise SystemExit("FATAL: derived ZERO names. An empty table would silently turn every named "
                         "yaml into an unknown-name error. Refusing to emit it.")
    text = render(rows, len(_spawnable()))
    curated = sum(1 for r in rows if r["source"] == "curated")

    if args.check:
        if not os.path.isfile(OUT):
            print("STALE: %s does not exist. Run: python tools/datamine_enemy_names.py" % OUT,
                  file=sys.stderr)
            return 1
        if open(OUT, encoding="utf-8").read() != text:
            print("STALE: enemy_names.py differs from a fresh datamine. "
                  "Run: python tools/datamine_enemy_names.py", file=sys.stderr)
            return 1
        print("enemy_names.py up to date (%d named models, %d curated)" % (len(rows), curated))
        return 0

    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("wrote %s -- %d named models (%d curated, %d from NpcName)"
          % (os.path.relpath(OUT, REPO), len(rows), curated, len(rows) - curated))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
