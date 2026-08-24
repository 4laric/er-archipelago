#!/usr/bin/env python3
r"""gen_enemy_drop_entities.py -- placement EntityID -> flagged enemy-drop CHECK, for er-archipelago#1000.

WHY THIS EXISTS. A flagged enemy-drop check (`ItemLotParam_enemy.getItemFlagId`) is bound to the
enemy's `NpcParam`. Under enemy randomisation (matt's rando) the MSB placement keeps its `EntityID`
but its `ModelName`+`NPCParamID`+`ThinkParamID` are repointed to a different enemy, so the swapped
occupant rolls its own drops, the flagged lot never rolls, and the check's acquisition flag never
fires. Confirmed by diffing a matt seed against vanilla (EntityID 28000390 c5320->c5240; 12010245
c3330->c5540). The `EntityID` SURVIVES the swap, so it is the anchor the client watches
(`crates/er-logic/src/enemy_drop_watch.rs`, `ENEMY_DROP_ENTITIES`).

THE ONE-HOP LOOKUP THIS TOOL DOES, AND WHY IT IS LOCAL-ONLY. An MSB `Part/Enemy` row carries
`EntityID` and `NPCParamID` on the SAME record -- a one-hop join. `tools/datamine_sweep_trigger_npcs.py`
wanted exactly this and could not have it, because `tools/gen_inputs.py` bundles "what gen_data READS,
not the MSBs". So this tool takes the vanilla MSBs as an EXTERNAL input (WitchyBND-unpacked, the
`<map>-msb-dcx/Part/Enemy/*.xml` form -- soulstruct cannot parse the v74 DLC MSBs) and MUST be run on
a local checkout where those files exist. It is not a CI/regen step; it emits a Rust const block to
paste into `enemy_drop_watch.rs::ENEMY_DROP_ENTITIES`.

  check lot -> base lot (lot - lot%10) -> NpcParam.itemLotId_enemy -> npc id(s)
    -> vanilla MSB Part/Enemy <NPCParamID> -> <EntityID>          (per shipped AP location)

MAP RESOLUTION. `check_maps.tsv` gives the map(s) for most flags -- it is ONE-TO-MANY BY DESIGN (its
own header: "A check on N maps gets N rows"), so EVERY map row for a flag is tried, not just the last
one read. 8-digit LEGACY-DUNGEON flags without an entry fall back to `m{AA}_{BB}` decoded from the
flag id; that grammar does NOT cover the overworld (m60/m61 tiles are three-part, `m60_35_50`), so an
8-digit 60/61-prefixed flag with no `check_maps.tsv` row is a HARD REFUSAL naming the flag rather
than a silent "unresolved" that blends into the un-datamined remainder. The table is STATIC GAME DATA
(vanilla placement->drop is seed-invariant), baked like `sweep_boss_names` so no wire key moves
CONTRACT_HASH.

THE XML PAIRING CONTRACT (pinned by tools/test_gen_enemy_drop_entities.py). WitchyBND unpacks
`Part/Enemy` as ONE PART PER FILE, so taking the first `<NPCParamID>` and the first `<EntityID>` in a
file pairs two fields of the SAME record. A file carrying two parts would silently mis-pair the first
NPC id with the first entity id; a single-`Part.xml` layout would resolve nothing at all. Both are
indistinguishable from "the MSBs weren't unpacked", so both are refused loudly instead.

Usage:
  python tools/gen_enemy_drop_entities.py \
      --msb /path/to/vanilla/map/mapstudio \
      [--db <repo>/gen_inputs.db] [--greenfield <repo>/greenfield] [--out enemy_drop_entities.rows]

Run on LOCAL disk: reading thousands of Enemy XMLs over a network mount is slow; locally the full
147-check pass is seconds.
"""
import argparse, sqlite3, zlib, csv, io, os, glob, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The overworld tiles. Their flags are 10-digit and always carry a check_maps.tsv row; the 8-digit
# `m{AA}_{BB}` decode below is a LEGACY-DUNGEON grammar and would invent a nonexistent tile here.
OVERWORLD_PREFIXES = ('60', '61')

NPC = re.compile(r'<NPCParamID>(-?\d+)</NPCParamID>')
EID = re.compile(r'<EntityID>(-?\d+)</EntityID>')


class Refusal(Exception):
    """A hard, NAMED refusal: the alternative is a wrong or silently-empty table."""


def open_db(path):
    """Open gen_inputs.db READ-ONLY, refusing a missing path.

    `sqlite3.connect` CREATES a missing file, so a wrong --db used to leave an untracked zero-byte
    database in the tree -- exactly what tools/check_integrity.py reds on -- and then failed with an
    unhelpful "no such table: files".
    """
    if not os.path.isfile(path):
        raise Refusal("--db %r does not exist (gen_inputs.db lives at the REPO ROOT). Refusing to "
                      "let sqlite3 create an empty database there." % (path,))
    return sqlite3.connect("file:%s?mode=ro" % (path,), uri=True)


def index_enemy_parts(d):
    """{NPCParamID: [EntityID, ...]} for one unpacked `<map>-msb-dcx/Part/Enemy` directory.

    ONE PART PER FILE is the whole assumption; both ways it can break are refusals, not silence.
    """
    files = sorted(glob.glob(os.path.join(d, '*.xml')))
    if not files:
        raise Refusal("%s contains no *.xml -- WitchyBND unpacks Part/Enemy as one XML per part, so "
                      "an empty Enemy dir means the layout is not the one this tool parses." % (d,))
    m = {}
    for f in files:
        with open(f, encoding='utf-8-sig', errors='replace') as fh:
            t = fh.read()
        npcs = NPC.findall(t)
        eids = EID.findall(t)
        if len(npcs) > 1 or len(eids) > 1:
            raise Refusal("%s holds %d <NPCParamID> and %d <EntityID> -- more than one part per "
                          "file. Pairing the FIRST of each would mis-pair records; refusing."
                          % (f, len(npcs), len(eids)))
        if npcs and eids and eids[0] != '0':
            m.setdefault(npcs[0], []).append(int(eids[0]))
    if not m:
        raise Refusal("%s: %d XML(s) parsed and not one yielded an (NPCParamID, non-zero EntityID) "
                      "pair -- the part layout is not what this tool parses. Refusing to report "
                      "that as a partial resolve." % (d, len(files)))
    return m


def f2m(f):
    """8-digit LEGACY flag -> `m{AA}_{BB}`. None for anything this grammar does not cover."""
    if len(f) != 8 or not f.isdigit():
        return None
    if f[0:2] in OVERWORLD_PREFIXES:
        return None
    return "m%s_%s" % (f[0:2], f[2:4])


def load(db, gf):
    con = open_db(db)

    def param(name):
        rows = con.execute("select path, blob from files where path like ?",
                           ('%' + name,)).fetchall()
        if len(rows) != 1:
            raise Refusal("%s: expected exactly one match in %s, got %d (%s). Refusing to pick one "
                          "arbitrarily." % (name, db, len(rows), [r[0] for r in rows]))
        b = rows[0][1]
        try:
            d = zlib.decompress(b)
        except Exception:
            d = b
        return list(csv.DictReader(io.StringIO(d.decode('utf-8', 'replace'))))

    enemy = {}
    for r in csv.DictReader(open(f'{gf}/flag_lots.tsv', encoding='utf-8-sig'), delimiter='\t'):
        if r.get('table') == 'enemy':
            enemy[r['flag']] = (int(r['lot']), r['item_id'], r['name'])
    ap = {}
    for m in re.finditer(r"\(\s*'[^']*\[f(\d+)\]'\s*,\s*(\d+)\s*,\s*(\d+)\s*\)",
                         open(f'{gf}/eldenring/data.py', encoding='utf-8').read()):
        ap[m.group(1)] = int(m.group(2))
    npc_by_base = {}
    for r in param('NpcParam.csv'):
        il = r.get('itemLotId_enemy', '0')
        if il and il != '0':
            npc_by_base.setdefault(il, []).append(r['ID'])
    return enemy, ap, npc_by_base, read_flagmap(f'{gf}/check_maps.tsv')


def read_flagmap(path):
    """flag -> [map, ...], in file order.

    ONE-TO-MANY, not last-wins: check_maps.tsv emits one row per (flag, PHYSICAL POSITION) -- its
    own header says so -- and keeping only the last row read would silently drop a multi-map
    check's other homes. Zero of the 147 enemy-drop checks are multi-map today; this removes the
    trap rather than relying on that staying true.
    """
    flagmap = {}
    with open(path, encoding='utf-8-sig') as fh:
        for r in csv.reader(fh, delimiter='\t'):
            if r and r[0].isdigit():
                if r[1] not in flagmap.setdefault(r[0], []):
                    flagmap[r[0]].append(r[1])
    return flagmap


def maps_for(flag, flagmap):
    """Every map to try for a flag, in order. Raises on the overworld decode trap."""
    cands = list(flagmap.get(flag, []))
    fb = f2m(flag)
    if fb and fb not in cands:
        cands.append(fb)
    if not cands and len(flag) == 8 and flag.isdigit() and flag[0:2] in OVERWORLD_PREFIXES:
        raise Refusal("flag %s: 8-digit overworld (%s) flag with NO check_maps.tsv row. The "
                      "m{AA}_{BB} decode is a legacy-dungeon grammar and would name a tile that "
                      "does not exist. Refusing rather than reporting it as unresolved."
                      % (flag, flag[0:2]))
    return cands


def build(enemy, ap, npc_by_base, flagmap, index_map):
    """(rows, unresolved). `index_map(mapname) -> {npc: [eid]}`; separated out so the test can
    drive the join over a fixture without an MSB tree."""
    table, unresolved = [], []
    for flag, (lot, item, name) in enemy.items():
        loc = ap.get(flag)
        if loc is None:
            continue
        base = str(lot - lot % 10)
        eids = set()
        for mp in maps_for(flag, flagmap):
            mi = index_map(mp)
            for n in npc_by_base.get(base, []):
                eids.update(mi.get(n, []))
            if eids:
                break
        if not eids:
            unresolved.append(flag)
            continue
        for e in sorted(eids):
            table.append((e, loc, (name[:40] or item)))
    return table, unresolved


def render(table, fh):
    """Write the Rust rows, lowest EntityID first, one row per EntityID."""
    seen = set()
    for e, loc, nm in sorted(table):
        if e in seen:
            print("warning: EntityID %d is reached by more than one check; keeping the first row "
                  "and DROPPING (%d, %d) // %s" % (e, e, loc, nm), file=sys.stderr)
            continue
        seen.add(e)
        fh.write("    (%d, %d), // %s\n" % (e, loc, nm))
    return seen


def main():
    p = argparse.ArgumentParser(description="Generate ENEMY_DROP_ENTITIES rows (#1000).")
    p.add_argument('--msb', required=True, help="vanilla mapstudio dir (WitchyBND-unpacked MSBs)")
    p.add_argument('--db', default=os.path.join(REPO, 'gen_inputs.db'))
    p.add_argument('--greenfield', default=os.path.join(REPO, 'greenfield'))
    p.add_argument('--out', default='enemy_drop_entities.rows')
    a = p.parse_args()

    def mdir(mp):
        if not mp:
            return None
        parts = mp.split('_')
        while len(parts) < 4:
            parts.append('00')
        d = f"{a.msb}/" + '_'.join(parts) + '-msb-dcx/Part/Enemy'
        return d if os.path.isdir(d) else None

    idx = {}

    def index_map(mp):
        if mp not in idx:
            d = mdir(mp)
            idx[mp] = index_enemy_parts(d) if d else {}
        return idx[mp]

    try:
        enemy, ap, npc_by_base, flagmap = load(a.db, a.greenfield)
        table, unresolved = build(enemy, ap, npc_by_base, flagmap, index_map)
    except Refusal as e:
        print("REFUSED: %s" % (e,), file=sys.stderr)
        return 2

    with open(a.out, 'w', encoding='utf-8', newline='\n') as fh:
        render(table, fh)
    shipped = sum(1 for f in enemy if f in ap)
    print(f"resolved {len(set(e for e, _, _ in table))} placements for "
          f"{shipped - len(unresolved)}/{shipped} shipped checks -> {a.out}")
    if unresolved:
        print(f"unresolved ({len(unresolved)}): {unresolved}", file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
