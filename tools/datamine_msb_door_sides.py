#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""datamine_msb_door_sides.py -- WHERE a pickup sits relative to a locked door. A RANKING, not a ruling.

WHY THIS EXISTS
---------------
Two key-item gates are stuck at exactly the same place, for exactly the same missing datum.

  #1512  Belurat (m20_00). Asset part `20001562` is bound to `ObjActParam` 417007, whose
         `spQualifiedId_new/_old` is goods 2008004 -- the Well Depths Key. The door is PROVEN: one
         `$InitializeCommonEvent` site, `spQualifiedType=1` (inventory possession), the same
         template as the two Lamenter's Gaol doors. What is NOT proven is WHICH of the fourteen
         Belurat checks (flags 20007210..20007320 by tens, plus 20007991/20007993) are behind it.
         `gen_inputs.db` carries EMEVD, ESD and params but NO MSB, so nothing first-party binds
         that asset to those lots, and the wiki audit holds every one of the fourteen.

  #1511  Subterranean Shunning-Grounds (m35_00). Asset part `35001564`, `ObjActParam` 1027019,
         the Sewer-Gaol Key. Same shape, one candidate: the lot behind flag 9504 (Mending Rune of
         the Fell Curse, award asset 35001711).

Encoding a `legacy_key_gates` conjunction on a walkthrough's route text would be the "flag
relationship asserted from a survey" CONTRIBUTING forbids, and getting it wrong costs a fourteen-
check region-lock strand. The MSB is the one first-party source that can say anything at all here:
the door is a Part with a `<Position>`, and every candidate pickup is a Part with a `<Position>`.
So this tool reads both and prints the geometry.

🛑 WHAT THIS IS NOT: A TOPOLOGY PROOF.
--------------------------------------
This is a GEOMETRIC WITNESS. Distance is not reachability. A pickup five metres past the door
plane can still be reachable by another corridor, a stairwell, a drop from the roof, or the map's
other entrance; a pickup thirty metres in front of the door can be behind a *different* lock. The
door plane is an infinite plane in this tool's arithmetic and a two-metre doorway in the game.

So this tool RANKS and a HUMAN RULES -- exactly the framing `tools/msb_region_vote.py` states for
itself, and for the same reason: it is the same class of instrument (a nearest-neighbour signal
that CANNOT FAIL, CONTRIBUTING rule 1), useful for ORDERING a human's adjudication and worthless
as an adjudicator. A row here is evidence to hand to a player ruling, never a row to write into
`greenfield/key_item_gates.tsv` on its own.

WHAT IT READS (all under the artifacts root; `--path` moves it, exactly as every corpus tool)
---------------------------------------------------------------------------------------------
  mapstudio/<map>_00_00-msb-dcx/Part/{Asset,DummyAsset}/*.xml   the DOOR part: <Name>, <EntityID>,
                                                                <Position>, and <Rotation> if it
                                                                has one
  mapstudio/<map>_00_00-msb-dcx/Event/Treasure/*.xml            <ItemLotID>, <TreasurePartName>
  mapstudio/<map>_00_00-msb-dcx/Part/{Asset,DummyAsset}/*.xml   the TREASURE part's <Position>
  mapstudio/<map>_00_00-msb-dcx/Region/PlayArea/*.xml           via datamine_grace_ground, for the
                                                                play_region column
  greenfield/flag_lots.tsv          flag -> ItemLotParam row + the vanilla item NAME (committed)
  greenfield/msb_flag_region.tsv    flag -> map + lot, the fallback join (committed)

NOTHING IS RE-IMPLEMENTED. Every parse and every metre of geometry is imported from its one owner:

    datamine_item_grace_coords._POS_RE / _NPCID_RE / _msb_sub / _lot2flags / _npc2lots
                                        / _enemy_item_rows      the witchy Part/Treasure readers
    datamine_grace_ground.derive_ground / load_interior_volumes / load_play_region_defaults
                                        / Vol / _srcname        THE point-in-volume ladder
    artifacts_root                                              THE --path flag

The ONE piece of arithmetic that is new here is the signed distance along the door's facing
normal, and it is new because nothing in the repo needed a door normal before.

THE FACING NORMAL, AND WHY ITS SIGN IS NOT AN ANSWER
----------------------------------------------------
`datamine_grace_ground.Vol.contains` is the repo's only reader of a witchy `<Rotation>`: for a Box
it takes `Rotation/Y` as a yaw in DEGREES and tests `dx*cos - dz*sin` against the Width half-extent
and `dx*sin + dz*cos` against the Depth half-extent. So the box's local +Z ("depth") axis in world
terms is `(sin(yaw), 0, cos(yaw))`, and that is the vector this tool uses as the door's normal.

  normal_dist = (treasure - door) . (sin(yaw), 0, cos(yaw))

Rows with the same SIGN are on the same side of the door's plane. WHICH sign is the locked side is
NOT decidable from the MSB alone -- a door asset's authored facing is a modelling convention, not a
semantic one -- so the tool never labels a side "behind". Anchor the sign with ONE pickup whose
side a player already knows (for #1512, the Well Depths Key's own vanilla check f20007510 is
outside the door by construction: it is not one of the fourteen), then read every other row's sign
relative to that. That anchoring step is the human ruling; this column only makes it cheap.

IF THE DOOR PART CARRIES NO `<Rotation>` the column is `-` and the tool SAYS SO on stderr rather
than substituting a zero yaw. A silent zero would print a normal along world +Z for every door in
the game and the numbers would look exactly as authoritative as real ones.

REFUSALS (an empty scan that writes a table is the failure mode this project has already paid for
twice -- see the FATALs in datamine_msb_item_regions.build_treasure_assets and
datamine_item_play_regions). None of these is bypassable:
  * no witchy MSB dirs under the artifacts root at all -> FATAL naming every path tried;
  * the named map's MSB dir absent -> FATAL;
  * the named door part not found in it -> FATAL, listing the part dirs searched and their counts;
  * ZERO candidate rows placed -> FATAL, and NOTHING is written. A door with no candidates beside
    it is a question, not a table.

USAGE (runs on the box with the extracted corpus; CI has none -- the geometry is witnessed by
greenfield/eldenring/tests/test_gf_msb_door_sides.py on synthetic fixtures instead)

  # 1512 -- Belurat, Well Depths Key door, the fourteen candidate flags
  python tools/datamine_msb_door_sides.py --path D:\er\elden_ring_artifacts --map m20_00 \
      --door 20001562 \
      --flags 20007210,20007220,20007230,20007240,20007250,20007260,20007270,20007280,20007290,20007300,20007310,20007320,20007991,20007993 \
      --emit door_sides_m20_00.tsv

  # 1511 -- Subterranean Shunning-Grounds, Sewer-Gaol Key door, the one candidate
  python tools/datamine_msb_door_sides.py --path D:\er\elden_ring_artifacts --map m35_00 \
      --door 35001564 --flags 9504 --emit door_sides_m35_00.tsv

  # enemy-drop flags with no treasure placement: emit the PLACING ENEMY's coordinates
  python tools/datamine_msb_door_sides.py --path D:\er\elden_ring_artifacts \
      --enemy-drops 1049557700,2047407980,65460 --emit enemy_drop_coords.tsv

WHEN THE MSB CHAIN IS SILENT: OPERATOR-ANCHORED PARTS (2026-09-09, the first real run)
--------------------------------------------------------------------------------------
Both automatic chains above stop one hop short of the MSB for a whole class of awards, and the
first run on the real corpus hit that class in BOTH issues:

  * #1511's lot 4920 HAS an Event/Treasure in m35_00 (`アイテム光000 エルデンリングのかけら`) but the
    record carries NO <TreasurePartName> at all (`InChest=2`): the rune is AWARDED by EMEVD, on
    asset 35001711, not picked off a part. treasure_placements has nothing to position.
  * 1049557700 (Larval Tear) and 2047407980 are `AwardItemsIncludingClients` in EMEVD keyed on a
    CHARACTER's death (m60_49_55_00 event 1049552400 on entity 1049550400; common 90005301 on
    entity 2047400499). No NpcParam row points at those lots, so `_enemy_item_rows` is silent.
  * 65460 (Glovewort Crystal Tear) is a furnace-golem (c4900) drop and the corpus carries no
    c4900 placement anywhere -- docs/MATT-ORACLE-ROADMAP.md item 7. NOTHING here can place it.
  * #1512's 20007991/20007993 (lots 20001991/20001993) have no Event/Treasure in m20_00 at all;
    the twelve by-tens flags do, and are the twelve rows the first run wrote.

The part that DOES carry the position is known in every placeable case -- it is in the EMEVD line
(`greenfield/questline_conditions.tsv` names it) -- it just is not reachable from the lot through
the MSB. So the operator hands it over EXPLICITLY, and the table says so:

  --award-parts FLAG=PART[,FLAG=PART...]   door mode: position candidate FLAG at PART (a <Name> or
                                           <EntityID>, searched over EVERY Part/* dir) instead of
                                           through Event/Treasure. lot/item_name still resolve
                                           through the committed tables; treasure_part shows the
                                           part with an `award-part:` prefix; the header note lists
                                           every anchored row.
  --entities MAP:ENTITY[=FLAG][,...]       coords mode: emit the position of ENTITY (name or id) in
                                           MAP, in the same kind,key,map_id,x,y,z,name shape as
                                           --enemy-drops. key is FLAG when given, else the entity.

  # 1511 -- the rune is EMEVD-awarded on asset 35001711; anchor it there
  python tools/datamine_msb_door_sides.py --path D:\er\elden_ring_artifacts --map m35_00 \
      --door 35001564 --award-parts 9504=35001711 --emit door_sides_m35_00.tsv

  # the two death-award flags, at the character the EMEVD watches
  python tools/datamine_msb_door_sides.py --path D:\er\elden_ring_artifacts \
      --entities m60_49_55_00:1049550400=1049557700,m61_47_40_00:2047400499=2047407980 \
      --emit enemy_drop_coords.tsv

Neither option guesses: a FLAG that resolves to no lot, or a PART/ENTITY that is not in the map,
is FATAL, the same as every other refusal here. The anchoring is the operator's ruling -- exactly
the human step the docstring above already reserves for the sign of the normal.

`--emit` output is deterministic (rows sorted by lot, then part name) and belongs to the operator's
run, NOT to the repo: there is no committed table here and there must not be one, because the tool
answers a question about a specific door on a specific day.
"""
import argparse
import csv
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.dirname(HERE)
sys.path.insert(0, HERE)

import artifacts_root                        # noqa: E402  -- THE --path argument, not a copy
import datamine_grace_ground as gg           # noqa: E402  -- THE point-in-volume ladder
import datamine_item_grace_coords as igc     # noqa: E402  -- THE witchy Part/Treasure readers

AR = artifacts_root.default_root(REPO)
GF = os.path.join(REPO, "greenfield")

# The door's <Rotation>. Read with a regex for the same reason igc reads <Position> with one: these
# are witchy-emitted files with one top-level element per field, and we want three floats out of a
# handful of files, not a DOM. `Y` is the yaw; see the module docstring for the axis convention and
# for why an ABSENT rotation is reported rather than defaulted to zero.
_ROT_RE = re.compile(r"<Rotation>\s*<X>(-?[\d.eE+-]+)</X>\s*<Y>(-?[\d.eE+-]+)</Y>"
                     r"\s*<Z>(-?[\d.eE+-]+)</Z>\s*</Rotation>")
_ENT_RE = re.compile(r"<EntityID>\s*(-?\d+)\s*</EntityID>")
_NAME_RE = re.compile(r"<Name>([^<]*)</Name>")

# Where a door asset can live. Same pair igc._treasure_item_rows resolves TreasurePartName against
# -- a door IS an asset, and DummyAsset is where several of them are authored.
PART_DIRS = ("Asset", "DummyAsset")

COLUMNS = ("lot_id", "flag", "item_name", "treasure_part",
           "tx", "ty", "tz", "dx_door", "dy_door", "dz_door",
           "distance_m", "normal_dist_m", "play_region_ids", "play_region_source")

ENEMY_COLUMNS = ("kind", "key", "map_id", "x", "y", "z", "name")


def _set_artifacts_root(path):
    """`--path` (alias `--artifacts`): move the corpus, for this module AND for the two modules it
    borrows its readers from. Re-rooting only our own global would be the exact failure
    test_gf_artifacts_path.py exists to catch: the flag parses, and the readers keep reading the
    old tree. Outputs are unaffected -- `--emit` is an explicit operator path, never repo-relative.
    """
    global AR
    AR = os.path.abspath(path)
    igc._set_artifacts_root(AR)
    gg._set_artifacts_root(AR)


# ---------------------------------------------------------------- map / part lookup

def full_map_id(map_id):
    """`m20_00` -> `m20_00_00_00`; a 4-field id is returned unchanged.

    The witchy dir name is always the four-field map id, but every table and every issue in this
    project spells interior maps with two (`m20_00`, `m35_00`), so both are accepted.
    """
    parts = (map_id or "").split("_")
    if not parts or not re.match(r"^m\d\d$", parts[0]):
        raise SystemExit("FATAL: %r is not a map id (want m20_00 or m20_00_00_00)" % map_id)
    while len(parts) < 4:
        parts.append("00")
    return "_".join(parts[:4])


def msb_dir_or_die(map_id):
    """The witchy MSB dir for one map, or a FATAL that names every place looked."""
    full = full_map_id(map_id)
    d = igc._msb_sub(full)
    if d is None:
        raise SystemExit(
            "FATAL: no witchy'd MSB dir %s-msb-dcx under the artifacts root %s.\n"
            "  %s\n"
            "  This tool cannot answer anything without the corpus, and it will not write a table "
            "instead. WitchyBND the .msb.dcx first, or point --path at the tree that has it."
            % (full, AR, artifacts_root.msb_search_report(AR)))
    return d


class Door(object):
    """The door part, as read: name, entity id, position, and yaw IF the record carries one."""

    __slots__ = ("name", "entity", "x", "y", "z", "yaw", "part_dir")

    def __init__(self, name, entity, x, y, z, yaw, part_dir):
        self.name, self.entity = name, entity
        self.x, self.y, self.z = x, y, z
        self.yaw, self.part_dir = yaw, part_dir

    def normal(self):
        """The world-space unit vector of the part's LOCAL +Z axis, or None with no rotation.

        `(sin(yaw), 0, cos(yaw))` is the depth axis of `datamine_grace_ground.Vol.contains`'s box
        test, which is this repo's one existing reader of a witchy `<Rotation>/<Y>`. Sharing that
        convention is the point: if the yaw convention is ever found to be wrong, it is wrong in
        one place for both tools rather than differently in two.
        """
        if self.yaw is None:
            return None
        r = math.radians(self.yaw)
        return (math.sin(r), 0.0, math.cos(r))


def find_door(msb_dir, spec):
    """Locate the door part by `<Name>` or by `<EntityID>`, over Part/Asset and Part/DummyAsset.

    Both spellings are accepted because both are how the door gets named in practice: the EMEVD
    line for #1512 names entity `20001562`, and an MSB reader hands you a part NAME. The filename
    is deliberately NOT trusted as the name -- witchy names files after the part, but the record's
    own `<Name>` is the field every other tool in this family joins on.
    """
    want_ent = int(spec) if str(spec).lstrip("-").isdigit() else None
    counts = []
    for sub in PART_DIRS:
        d = os.path.join(msb_dir, "Part", sub)
        if not os.path.isdir(d):
            counts.append((sub, 0))
            continue
        files = sorted(f for f in os.listdir(d) if f.endswith(".xml"))
        counts.append((sub, len(files)))
        for fn in files:
            try:
                with open(os.path.join(d, fn), encoding="utf-8-sig", errors="replace") as fh:
                    txt = fh.read()
            except OSError:
                continue
            nm = _NAME_RE.search(txt)
            nm = nm.group(1).strip() if nm else fn[:-4]
            ent = _ENT_RE.search(txt)
            ent = int(ent.group(1)) if ent else None
            if not (nm == str(spec) or (want_ent is not None and ent == want_ent)):
                continue
            pos = igc._POS_RE.search(txt)
            if not pos:
                raise SystemExit("FATAL: door part %s (%s/%s) has no <Position>. It cannot anchor a "
                                 "geometric witness; re-export this MSB." % (nm, sub, fn))
            rot = _ROT_RE.search(txt)
            yaw = float(rot.group(2)) if rot else None
            return Door(nm, ent, float(pos.group(1)), float(pos.group(2)), float(pos.group(3)),
                        yaw, sub)
    raise SystemExit(
        "FATAL: no part named or entitled %r in %s. Searched %s. A door that is not in the MSB is "
        "not a door this tool can measure from -- check the entity id against the "
        "$InitializeCommonEvent line, and check the map."
        % (spec, msb_dir, ", ".join("Part/%s (%d xml)" % c for c in counts)))


def find_part_any(msb_dir, spec):
    """(name, part_dir, (x, y, z)) for a part named or entitled `spec` in ANY Part/* dir, or None.

    find_door is deliberately Asset/DummyAsset-only; an award part can be an Enemy (a death award)
    as easily as an Asset, so this looks everywhere and reports which dir it was in.
    """
    want_ent = int(spec) if str(spec).lstrip("-").isdigit() else None
    pd = os.path.join(msb_dir, "Part")
    if not os.path.isdir(pd):
        return None
    for sub in sorted(os.listdir(pd)):
        d = os.path.join(pd, sub)
        if not os.path.isdir(d):
            continue
        for fn in sorted(f for f in os.listdir(d) if f.endswith(".xml")):
            try:
                with open(os.path.join(d, fn), encoding="utf-8-sig", errors="replace") as fh:
                    txt = fh.read()
            except OSError:
                continue
            nm = _NAME_RE.search(txt)
            nm = nm.group(1).strip() if nm else fn[:-4]
            ent = _ENT_RE.search(txt)
            ent = int(ent.group(1)) if ent else None
            if not (nm == str(spec) or (want_ent is not None and ent == want_ent)):
                continue
            pos = igc._POS_RE.search(txt)
            if not pos:
                raise SystemExit("FATAL: part %s (%s/%s) has no <Position>." % (nm, sub, fn))
            return nm, sub, (float(pos.group(1)), float(pos.group(2)), float(pos.group(3)))
    return None


def _pairs(spec, what, sep="="):
    """`A=B,C=D` -> [(A, B), ...]; a token without `sep` is FATAL."""
    out = []
    for tok in (spec or "").replace(" ", ",").split(","):
        if not tok:
            continue
        if sep not in tok:
            raise SystemExit("FATAL: %s value %r is not of the form X%sY" % (what, tok, sep))
        a, b = tok.split(sep, 1)
        out.append((a.strip(), b.strip()))
    return out


# ---------------------------------------------------------------- flag -> lot, via the committed tables

def _read_tsv(path):
    """Rows of a committed greenfield tsv as dicts, comments dropped. The tables are the join; this
    is only the reader for them."""
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader((ln for ln in fh if not ln.lstrip().startswith("#")),
                                   delimiter="\t"))


def flag_lot_index(gf=None):
    """(flag -> [lot ids], flag -> item name), out of the COMMITTED tables. No corpus needed.

    `greenfield/flag_lots.tsv` is the repo's flag -> ItemLotParam join (tools/datamine_flag_lots.py)
    and it carries the vanilla item `name` in the same row, which is where the `item_name` column
    comes from "cheaply". `greenfield/msb_flag_region.tsv` is the fallback for flags flag_lots has
    no row for -- it is the MSB/EMEVD provenance census and carries `item_lot_id` too. Both are
    committed, so `--flags` resolves on any box, corpus or not.

    THIS IS NOT A REIMPLEMENTATION of either table: the derivations live in their own generators
    and this reads their output. Recomputing flag -> lot from ItemLotParam here would be a second
    opinion that could disagree with the tables every other tool joins on.
    """
    gf = gf or GF
    lots, names = {}, {}
    for r in _read_tsv(os.path.join(gf, "flag_lots.tsv")):
        f, lot = (r.get("flag") or "").strip(), (r.get("lot") or "").strip()
        if not f.isdigit() or not lot.lstrip("-").isdigit():
            continue
        lots.setdefault(int(f), [])
        if int(lot) not in lots[int(f)]:
            lots[int(f)].append(int(lot))
        if (r.get("name") or "").strip() and not names.get(int(f)):
            names[int(f)] = r["name"].strip()
    for r in _read_tsv(os.path.join(gf, "msb_flag_region.tsv")):
        f, lot = (r.get("flag") or "").strip(), (r.get("item_lot_id") or "").strip()
        if not f.isdigit() or not lot.lstrip("-").isdigit():
            continue
        lots.setdefault(int(f), [])
        if int(lot) not in lots[int(f)]:
            lots[int(f)].append(int(lot))
    return lots, names


def resolve_candidates(flags, lots_arg, gf=None):
    """-> ({lot_id: (flag or None, item_name)}, unresolved_flags).

    `--flags` goes through the committed tables above. `--lots` is taken literally, but its flag and
    name are filled in from the INVERSE of the same index where they exist -- because the numbers a
    reader has in hand are often flags wearing a lot's clothes (issue #1512's comment lists
    `20007210..20007320`, which are FLAGS; flag 20007210's lot is 20000210). A `--lots` value that
    is a known flag is REPORTED, not silently reinterpreted.
    """
    f2l, names = flag_lot_index(gf)
    out, unresolved = {}, []
    for f in flags:
        got = f2l.get(f)
        if not got:
            unresolved.append(f)
            continue
        for lot in got:
            out.setdefault(lot, (f, names.get(f, "")))
    inv = {lot: f for f, ls in f2l.items() for lot in ls}
    for lot in lots_arg:
        if lot in f2l:
            sys.stderr.write("NOTE: --lots %d is also a known FLAG (its lot(s): %s). Passing a flag "
                             "to --lots measures a lot id that may not exist; did you mean "
                             "--flags?\n" % (lot, ",".join(str(x) for x in f2l[lot])))
        f = inv.get(lot)
        out.setdefault(lot, (f, names.get(f, "") if f else ""))
    return out, unresolved


# ---------------------------------------------------------------- placements

def treasure_placements(map_id, lot_ids):
    """{lot_id: [(treasure_part_name, (x, y, z)), ...]} for one map.

    The Event/Treasure -> TreasurePartName -> Part position walk is igc._treasure_item_rows's, but
    that function returns (flag, map, xyz) and drops the PART NAME, which is the column a human
    needs to find the thing in a map viewer. So the walk is done here over the same directories,
    with igc's own regexes and igc._msb_sub -- the PARSING is shared, only the projection differs.
    A lot may be placed more than once; every placement is reported.
    """
    full = full_map_id(map_id)
    d = igc._msb_sub(full, "Event", "Treasure")
    out = {}
    if d is None:
        return out
    partdirs = [pd for pd in (igc._msb_sub(full, "Part", s) for s in PART_DIRS) if pd]
    poscache = {}

    def _partpos(name):
        if name in poscache:
            return poscache[name]
        p = None
        for pd in partdirs:
            fp = os.path.join(pd, name + ".xml")
            if os.path.isfile(fp):
                with open(fp, encoding="utf-8-sig", errors="replace") as fh:
                    m = igc._POS_RE.search(fh.read())
                if m:
                    p = (float(m.group(1)), float(m.group(2)), float(m.group(3)))
                break
        poscache[name] = p
        return p

    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".xml"):
            continue
        with open(os.path.join(d, fn), encoding="utf-8-sig", errors="replace") as fh:
            t = fh.read()
        lid = re.search(r"<ItemLotID>(-?\d+)</ItemLotID>", t)
        if not lid or int(lid.group(1)) not in lot_ids:
            continue
        pn = re.search(r"<TreasurePartName>([^<]*)</TreasurePartName>", t)
        pn = pn.group(1).strip() if pn else ""
        xyz = _partpos(pn) if pn else None
        if xyz is None:
            continue
        out.setdefault(int(lid.group(1)), []).append((pn, xyz))
    for lot in out:
        out[lot].sort()
    return out


def _play_region(map_id, xyz, ctx):
    """(ids string, source string) through datamine_grace_ground.derive_ground -- THE ladder.

    Interior maps have PlayArea volumes too (that is `interior-vol:`), so the column is meaningful
    here even though nothing in a Belurat tower is on the overworld grid. `ctx` is the (vols,
    tile_ids, interior_ids) triple built once per run; `vols` is the OVERWORLD volume set and stays
    EMPTY for an interior-only run -- derive_ground never touches it off the m60/m61 grid.
    """
    vols, tile_ids, interior_ids = ctx
    ids, src = gg.derive_ground(map_id, xyz[0], xyz[1], xyz[2], vols, tile_ids, interior_ids)
    return (",".join(str(i) for i in ids) or "-"), src


def door_rows(map_id, door, candidates, ctx, anchored=None):
    """The table: one row per (lot, placement), deterministic, no side effects.

    `anchored` is {lot: [(part_label, xyz), ...]} from --award-parts; those placements are ADDED
    to the Event/Treasure ones, never substituted for them, so a lot that turns out to have both
    shows both and the human sees the disagreement.
    """
    placements = treasure_placements(map_id, set(candidates))
    for lot, extra in (anchored or {}).items():
        placements.setdefault(lot, []).extend(extra)
        placements[lot].sort()
    n = door.normal()
    rows = []
    for lot in sorted(candidates):
        flag, name = candidates[lot]
        for part, (x, y, z) in placements.get(lot, ()):
            dx, dy, dz = x - door.x, y - door.y, z - door.z
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            nd = "-" if n is None else "%.2f" % (dx * n[0] + dy * n[1] + dz * n[2])
            ids, src = _play_region(map_id, (x, y, z), ctx)
            rows.append((str(lot), str(flag) if flag is not None else "-", name, part,
                         "%.3f" % x, "%.3f" % y, "%.3f" % z,
                         "%.3f" % dx, "%.3f" % dy, "%.3f" % dz,
                         "%.2f" % dist, nd, ids, src))
    return rows


# ---------------------------------------------------------------- --enemy-drops

def enemy_drop_rows(flags):
    """Enemy-placed drops that have NO Treasure record -- the placing ENEMY part's coordinates.

    1049557700 (the runebear-disguised noble's Larval Tear, Consecrated Snowfield), 2047407980 and
    65460 are the motivating cases: the item is an NpcParam drop, so there is no `Event/Treasure`
    to stand on and the door-side mode above has nothing to measure. The chain is exactly the one
    `datamine_msb_item_regions` walks for `source=enemy` --
    `Part/Enemy <NPCParamID> -> NpcParam.itemLotId_{enemy,map} -> ItemLotParam.getItemFlagId* ->
    flag` -- and `datamine_item_grace_coords._enemy_item_rows` is that walk WITH the `<Position>`
    already attached, which is the half that matters here. So it is CALLED, not copied.

    Output is `kind,key,map_id,x,y,z,name`, byte-shaped like greenfield/item_grace_coords.tsv so
    the PlayArea scan can consume it directly. `name` is EMPTY, as it is for every `item` row in
    that table -- the shared reader (msb_region_vote.load_coords) does not read it, and filling it
    with an enemy part name here would make this file's column mean something the real table's
    does not.
    """
    lot2flags = igc._lot2flags()
    npc2lots = igc._npc2lots()
    if not lot2flags or not npc2lots:
        raise SystemExit("FATAL: ItemLotParam/NpcParam did not load from %s. Without the params the "
                         "enemy chain resolves nothing and would emit an empty table."
                         % artifacts_root.msb_search_report(AR))
    want = set(flags)
    rows = []
    seen = set()
    for root in (artifacts_root.msb_dirs(AR) or []):
        for name in sorted(os.listdir(root)):
            if not name.endswith("-msb-dcx"):
                continue
            map_id = name[:-len("-msb-dcx")]
            for flag, mid, xyz in igc._enemy_item_rows(map_id, lot2flags, npc2lots):
                if flag not in want:
                    continue
                key = (flag, mid, xyz)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(("item", str(flag), mid, xyz[0], xyz[1], xyz[2], ""))
    return sorted(rows, key=lambda r: (int(r[1]), r[2], r[3], r[4], r[5]))


def entity_rows(pairs):
    """[(kind, key, map_id, x, y, z, name)] for operator-named `MAP:ENTITY[=FLAG]` parts.

    The EMEVD-on-death awards (module docstring, "WHEN THE MSB CHAIN IS SILENT") have no NpcParam
    hop for `enemy_drop_rows` to follow; the watched character IS known from the event line. The
    operator names it; this only reads its <Position>. Same shape as enemy_drop_rows so the
    PlayArea scan consumes either. A missing map or part is FATAL.
    """
    rows = []
    for spec, flag in pairs:
        if ":" not in spec:
            raise SystemExit("FATAL: --entities value %r is not MAP:ENTITY[=FLAG]" % spec)
        map_id, ent = spec.split(":", 1)
        full = full_map_id(map_id)
        msb = msb_dir_or_die(full)
        hit = find_part_any(msb, ent)
        if hit is None:
            raise SystemExit("FATAL: no part named or entitled %r in %s (searched every Part/* "
                             "dir). Nothing written." % (ent, msb))
        nm, sub, (x, y, z) = hit
        sys.stderr.write("NOTE: %s -> Part/%s/%s at (%.3f, %.3f, %.3f)\n"
                         % (spec, sub, nm, x, y, z))
        key = flag if flag else str(ent)
        rows.append(("item", key, full, x, y, z, ""))
    return sorted(rows, key=lambda r: (r[1], r[2], r[3], r[4], r[5]))


# ---------------------------------------------------------------- output

def write_tsv(path, columns, rows, header_note):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for ln in header_note:
            fh.write("# %s\n" % ln)
        fh.write("\t".join(columns) + "\n")
        for r in rows:
            fh.write("\t".join(str(c) for c in r) + "\n")


def _print(columns, rows, stream=sys.stdout):
    # Item names and witchy part names are not cp1252; a Windows console default must not turn a
    # finished scan into a UnicodeEncodeError halfway through the table.
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")
    stream.write("\t".join(columns) + "\n")
    for r in rows:
        stream.write("\t".join(str(c) for c in r) + "\n")


def _ints(spec, what):
    out = []
    for tok in (spec or "").replace(" ", ",").split(","):
        if not tok:
            continue
        if not tok.lstrip("-").isdigit():
            raise SystemExit("FATAL: %s value %r is not a number" % (what, tok))
        out.append(int(tok))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Where candidate pickups sit relative to a locked door asset. A GEOMETRIC "
                    "WITNESS that RANKS; a human RULES (see the module docstring).")
    ap.add_argument("--map", help="map id of the interior, e.g. m20_00 (or m20_00_00_00)")
    ap.add_argument("--door", help="door asset part <Name> or <EntityID>, e.g. 20001562")
    ap.add_argument("--lots", default="", help="comma-separated ItemLotParam_map row ids")
    ap.add_argument("--flags", default="",
                    help="comma-separated acquisition flags, resolved to lots through the COMMITTED "
                         "greenfield/flag_lots.tsv (then msb_flag_region.tsv)")
    ap.add_argument("--enemy-drops", default="",
                    help="second mode: comma-separated enemy-drop flags with no Treasure "
                         "placement. Emits the PLACING ENEMY's map and position in "
                         "item_grace_coords.tsv's kind,key,map_id,x,y,z,name shape.")
    ap.add_argument("--award-parts", default="", metavar="FLAG=PART,...",
                    help="door mode: anchor candidate FLAG at PART (a part <Name> or <EntityID>, "
                         "any Part/* dir) when its award has no Event/Treasure placement -- an "
                         "EMEVD award. The operator's ruling; the row is marked `award-part:`.")
    ap.add_argument("--entities", default="", metavar="MAP:ENTITY[=FLAG],...",
                    help="third mode: emit the <Position> of named parts, in --enemy-drops' shape, "
                         "for awards keyed on a character's death in EMEVD (no NpcParam hop).")
    ap.add_argument("--emit", metavar="TSV",
                    help="write the table here (deterministic). Without it the table goes to "
                         "stdout. Nothing is ever written into greenfield/ -- this answers a "
                         "question about one door on one day, not a committed census.")
    artifacts_root.add_path_argument(
        ap, artifacts_alias=False,
        extra_help="the MSB corpus is REQUIRED: with no witchy'd MSBs this tool exits non-zero "
                   "rather than emitting an empty table")
    args = ap.parse_args(argv)
    root = artifacts_root.resolve(args.path)
    if root:
        _set_artifacts_root(root)

    if args.enemy_drops or args.entities:
        if not artifacts_root.msb_dirs(AR):
            raise SystemExit("FATAL: no witchy'd MSB dirs under %s. %s"
                             % (AR, artifacts_root.msb_search_report(AR)))
        rows, note = [], []
        if args.enemy_drops:
            flags = _ints(args.enemy_drops, "--enemy-drops")
            rows += enemy_drop_rows(flags)
            if not rows:
                raise SystemExit("FATAL: none of the %d enemy-drop flag(s) resolved to a placed "
                                 "Part/Enemy. An empty scan that writes a table is the failure "
                                 "mode this project has already paid for twice -- nothing written."
                                 "\n  If the award is EMEVD-on-death (AwardItemsIncludingClients "
                                 "keyed on a character; see greenfield/questline_conditions.tsv), "
                                 "there is no NpcParam hop to follow: name the character with "
                                 "--entities MAP:ENTITY=FLAG instead." % len(flags))
            note += ["enemy-drop coordinates from tools/datamine_msb_door_sides.py --enemy-drops",
                     "chain: Part/Enemy <NPCParamID> -> NpcParam.itemLotId_* -> ItemLotParam "
                     "getItemFlagId* -> flag (datamine_item_grace_coords._enemy_item_rows)"]
        if args.entities:
            pairs = [(t.split("=", 1) + [""])[:2] for t in
                     args.entities.replace(" ", ",").split(",") if t]
            rows += entity_rows(pairs)
            note += ["operator-anchored coordinates from --entities (the part the EMEVD award "
                     "watches; NOT an MSB-derived chain): " +
                     "; ".join("%s -> flag %s" % (a, b or "(none)") for a, b in pairs)]
        note += ["shape matches greenfield/item_grace_coords.tsv; positions are MAP-LOCAL"]
        if args.emit:
            write_tsv(args.emit, ENEMY_COLUMNS, rows, note)
            sys.stderr.write("wrote %d row(s) -> %s\n" % (len(rows), args.emit))
        else:
            for ln in note:
                sys.stderr.write("# %s\n" % ln)
            _print(ENEMY_COLUMNS, rows)
        return 0

    if not (args.map and args.door):
        raise SystemExit("FATAL: --map and --door are both required (or use --enemy-drops)")
    if not (args.flags or args.lots or args.award_parts):
        raise SystemExit("FATAL: give at least one candidate with --flags or --lots "
                         "(or --award-parts)")

    msb = msb_dir_or_die(args.map)
    door = find_door(msb, args.door)
    if door.yaw is None:
        sys.stderr.write(
            "NOTE: door part %s carries no <Rotation> -- the normal_dist_m column will be '-'.\n"
            "      The witchy fields this family reads on a Part are <Name>, <EntityID>, "
            "<Position><X/Y/Z> and (here) <Rotation><X/Y/Z>; only Rotation/Y is a yaw, and it is "
            "absent on this record. No zero is substituted.\n" % door.name)
    award = _pairs(args.award_parts, "--award-parts")
    award_flags = []
    for f, _p in award:
        if not f.isdigit():
            raise SystemExit("FATAL: --award-parts flag %r is not a number" % f)
        award_flags.append(int(f))
    candidates, unresolved = resolve_candidates(_ints(args.flags, "--flags") + award_flags,
                                                _ints(args.lots, "--lots"))
    for f in unresolved:
        if f in award_flags:
            raise SystemExit("FATAL: --award-parts flag %d has no row in flag_lots.tsv or "
                             "msb_flag_region.tsv, so it has no lot to sit in a row. Nothing "
                             "written." % f)
        sys.stderr.write("NOTE: flag %d has no row in flag_lots.tsv or msb_flag_region.tsv -- it "
                         "cannot be placed and is dropped.\n" % f)
    if not candidates:
        raise SystemExit("FATAL: no candidate lot ids resolved. Nothing written.")

    # --award-parts: the operator's anchor for an EMEVD-awarded lot. Located now, over every
    # Part/* dir, and FATAL if absent -- an anchor that is not in the map is not an anchor.
    anchored, anchor_notes = {}, []
    flag2lots = {}
    for lot, (f, _nm) in candidates.items():
        if f is not None:
            flag2lots.setdefault(f, []).append(lot)
    for f, part in award:
        hit = find_part_any(msb, part)
        if hit is None:
            raise SystemExit("FATAL: --award-parts %s=%s: no part named or entitled %r in %s "
                             "(searched every Part/* dir). Nothing written." % (f, part, part, msb))
        nm, sub, xyz = hit
        for lot in flag2lots.get(int(f), []):
            anchored.setdefault(lot, []).append(("award-part:%s" % nm, xyz))
        anchor_notes.append("flag %s anchored at Part/%s/%s (operator ruling, not an "
                            "Event/Treasure placement)" % (f, sub, nm))

    tile_ids, interior_ids = gg.load_play_region_defaults()
    ctx = ([], tile_ids, interior_ids)     # overworld volumes are not needed for an interior map
    rows = door_rows(args.map, door, candidates, ctx, anchored)
    placed = {int(r[0]) for r in rows}
    for lot in sorted(candidates):
        if lot not in placed:
            f, nm = candidates[lot]
            sys.stderr.write("NOTE: lot %d (flag %s%s) resolved but has NO placement in this map: "
                             "no Event/Treasure names it with a TreasurePartName that is a part "
                             "here. It is NOT in the table. If it is an EMEVD award, anchor it "
                             "with --award-parts %s=PART.\n"
                             % (lot, f if f is not None else "-", (", " + nm) if nm else "",
                                f if f is not None else "FLAG"))
    if not rows:
        raise SystemExit(
            "FATAL: %d candidate lot(s) and ZERO placements found in %s. Either none of these lots "
            "is placed by an Event/Treasure in this map (try --enemy-drops, or check the map), or "
            "the TreasurePartName does not resolve to a Part/{Asset,DummyAsset}. An empty scan "
            "that writes a table is the failure mode this project has already paid for twice -- "
            "nothing written." % (len(candidates), msb))

    note = ["door-side GEOMETRIC WITNESS from tools/datamine_msb_door_sides.py -- it RANKS, a "
            "human RULES. Distance is not reachability.",
            "map=%s door=%s entity=%s part_dir=Part/%s pos=(%.3f, %.3f, %.3f) yaw=%s"
            % (full_map_id(args.map), door.name, door.entity, door.part_dir,
               door.x, door.y, door.z,
               "%.3f" % door.yaw if door.yaw is not None else "ABSENT (normal_dist_m is '-')"),
            "normal_dist_m is signed along the door's local +Z axis (sin(yaw), 0, cos(yaw)), the "
            "same yaw convention as datamine_grace_ground.Vol.contains. Same sign = same side of "
            "the door PLANE; which sign is the locked side is NOT decidable from the MSB.",
            "positions are MAP-LOCAL, the frame greenfield/item_grace_coords.tsv uses."]
    note += anchor_notes
    if args.emit:
        write_tsv(args.emit, COLUMNS, rows, note)
        sys.stderr.write("wrote %d row(s) -> %s\n" % (len(rows), args.emit))
    else:
        for ln in note:
            sys.stderr.write("# %s\n" % ln)
        _print(COLUMNS, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
