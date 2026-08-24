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

Map resolution: `check_maps.tsv` gives the map for most flags; 8-digit legacy flags without an entry
fall back to `m{AA}_{BB}` from the flag id. The table is STATIC GAME DATA (vanilla placement->drop is
seed-invariant), baked like `sweep_boss_names` so no wire key moves CONTRACT_HASH.

Usage:
  python tools/gen_enemy_drop_entities.py \
      --msb /path/to/vanilla/map/mapstudio \
      [--db greenfield/gen_inputs.db] [--greenfield greenfield] [--out enemy_drop_entities.rows]

Run on LOCAL disk: reading thousands of Enemy XMLs over a network mount is slow; locally the full
147-check pass is seconds.
"""
import argparse, sqlite3, zlib, csv, io, os, glob, re, sys


def load(db, gf):
    con = sqlite3.connect(db)

    def param(name):
        b = con.execute("select blob from files where path like ?", ('%' + name,)).fetchone()[0]
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
    flagmap = {}
    for r in csv.reader(open(f'{gf}/check_maps.tsv', encoding='utf-8-sig'), delimiter='\t'):
        if r and r[0].isdigit():
            flagmap[r[0]] = r[1]
    return enemy, ap, npc_by_base, flagmap


def main():
    p = argparse.ArgumentParser(description="Generate ENEMY_DROP_ENTITIES rows (#1000).")
    p.add_argument('--msb', required=True, help="vanilla mapstudio dir (WitchyBND-unpacked MSBs)")
    p.add_argument('--db', default='greenfield/gen_inputs.db')
    p.add_argument('--greenfield', default='greenfield')
    p.add_argument('--out', default='enemy_drop_entities.rows')
    a = p.parse_args()

    enemy, ap, npc_by_base, flagmap = load(a.db, a.greenfield)

    def f2m(f):
        return f"m{f[0:2]}_{f[2:4]}" if len(f) == 8 else None

    def mdir(mp):
        if not mp:
            return None
        parts = mp.split('_')
        while len(parts) < 4:
            parts.append('00')
        d = f"{a.msb}/" + '_'.join(parts) + '-msb-dcx/Part/Enemy'
        return d if os.path.isdir(d) else None

    NPC = re.compile(r'<NPCParamID>(\d+)</NPCParamID>')
    EID = re.compile(r'<EntityID>(\d+)</EntityID>')
    idx = {}

    def index_map(mp):
        if mp in idx:
            return idx[mp]
        m = {}
        d = mdir(mp)
        if d:
            for f in glob.glob(d + '/*.xml'):
                t = open(f, encoding='utf-8-sig', errors='replace').read()
                n = NPC.search(t)
                e = EID.search(t)
                if n and e and e.group(1) != '0':
                    m.setdefault(n.group(1), []).append(int(e.group(1)))
        idx[mp] = m
        return m

    table, unresolved = [], []
    for flag, (lot, item, name) in enemy.items():
        loc = ap.get(flag)
        if loc is None:
            continue
        base = str(lot - lot % 10)
        eids = set()
        for mp in (flagmap.get(flag), f2m(flag)):
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

    seen = set()
    with open(a.out, 'w') as fh:
        for e, loc, nm in sorted(table):
            if e in seen:
                continue
            seen.add(e)
            fh.write(f"    ({e}, {loc}), // {nm}\n")
    shipped = sum(1 for f in enemy if f in ap)
    print(f"resolved {len(set(e for e, _, _ in table))} placements for "
          f"{shipped - len(unresolved)}/{shipped} shipped checks -> {a.out}")
    if unresolved:
        print(f"unresolved ({len(unresolved)}): {unresolved}", file=sys.stderr)


if __name__ == '__main__':
    main()
