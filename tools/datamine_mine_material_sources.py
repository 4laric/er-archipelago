#!/usr/bin/env python3
"""Census repeatable smithing-stone asset pickups for issue #1095.

The delivery chain is independent of AP's location table:

    MSB Part/Asset ModelName -> AssetEnvironmentGeometryParam
      -> pickUpItemLotParamId -> ItemLotParam_map -> EquipParamGoods FMG name

Rows are emitted per placed asset, so counts and maps are measured rather than inferred from the
19 reusable asset templates.  Capstones remain labelled and are never folded into ordinary mine
materials.  With no MSB corpus, ``--templates-only`` still records the parameter-side mechanism.
"""
import argparse
import csv
import glob
import os
import re
import xml.etree.ElementTree as ET


STONE_RE = re.compile(r"^(Somber )?(Ancient Dragon )?Smithing Stone(?: \[(\d+)\])?$")
MSB_RE = re.compile(r"^(m\d\d_\d\d_\d\d_\d\d)-msb-dcx$")
MODEL_RE = re.compile(r"^AEG(\d{3})_(\d{3})$")
LOT_FIELDS = (
    "breakItemLotParamId",
    "pickUpItemLotParamId",
    "pickUpReplacementItemLotParamId",
    "repickItemLotParamId",
    "repickReplacementItemLotParamId",
)


def _int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def goods_names(path):
    root = ET.parse(path).getroot()
    return {int(node.attrib["id"]): node.text or "" for node in root.iter("text")}


def stone_lots(path, names):
    out = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            rewards = []
            for slot in range(1, 9):
                suffix = f"{slot:02}"
                goods_id = _int(row.get("lotItemId" + suffix))
                if _int(row.get("lotItemCategory" + suffix)) != 1:
                    continue
                name = names.get(goods_id, "")
                match = STONE_RE.match(name)
                if not match:
                    continue
                rewards.append({
                    "goods_id": goods_id,
                    "item_name": name,
                    "quantity": _int(row.get("lotItemNum" + suffix)),
                    "family": "somber" if match.group(1) else "regular",
                    "tier": _int(match.group(3)),
                    "capstone": "yes" if match.group(2) else "no",
                })
            if rewards:
                out[_int(row.get("ID"))] = rewards
    return out


def asset_templates(path, lots):
    out = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            geometry_id = _int(row.get("ID"))
            for field in LOT_FIELDS:
                lot_id = _int(row.get(field))
                if lot_id not in lots:
                    continue
                out[geometry_id] = {
                    "lot_field": field,
                    "lot_id": lot_id,
                    "repeatable": "yes" if _int(row.get("isEnableRepick")) else "no",
                    "break_on_pickup": "yes" if _int(row.get("isBreakOnPickUp")) else "no",
                    "rewards": lots[lot_id],
                }
    return out


def geometry_id(model_name):
    match = MODEL_RE.match(model_name or "")
    return int(match.group(1) + match.group(2)) if match else None


def map_id(dirname):
    match = MSB_RE.match(dirname)
    if not match:
        return None
    raw = match.group(1)
    parts = raw.split("_")
    return "_".join(parts[:3]) if parts[0] in ("m60", "m61") else "_".join(parts[:2])


def placed_assets(msb_root, templates):
    for msb_dir in sorted(glob.glob(os.path.join(msb_root, "m??_??_??_??-msb-dcx"))):
        mid = map_id(os.path.basename(msb_dir))
        if not mid:
            continue
        for path in sorted(glob.glob(os.path.join(msb_dir, "Part", "Asset", "*.xml"))):
            try:
                root = ET.parse(path).getroot()
            except (OSError, ET.ParseError):
                continue
            model = (root.findtext("ModelName") or "").strip()
            gid = geometry_id(model)
            if gid not in templates:
                continue
            yield {
                "map_id": mid,
                "asset_name": (root.findtext("Name") or "").strip(),
                "model_name": model,
                "instance_id": _int(root.findtext("InstanceID")),
                "asset_entity_id": _int(root.findtext("EntityID")),
                "geometry_id": gid,
            }


FIELDS = (
    "map_id", "asset_name", "model_name", "instance_id", "asset_entity_id", "geometry_id",
    "lot_field", "item_lot_id", "goods_id", "item_name", "family", "tier", "quantity",
    "repeatable", "break_on_pickup", "capstone",
)


def emit(out_path, templates, placements):
    rows = []
    if placements is None:
        placements = ({"map_id": "", "asset_name": "", "model_name": "",
                       "instance_id": 0, "asset_entity_id": 0, "geometry_id": gid}
                      for gid in sorted(templates))
    for placed in placements:
        template = templates[placed["geometry_id"]]
        for reward in template["rewards"]:
            rows.append({
                **placed,
                "lot_field": template["lot_field"],
                "item_lot_id": template["lot_id"],
                **reward,
                "repeatable": template["repeatable"],
                "break_on_pickup": template["break_on_pickup"],
            })
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        fh.write("# generated by tools/datamine_mine_material_sources.py; issue #1095\n")
        writer = csv.DictWriter(fh, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", required=True,
                        help="elden_ring_artifacts root containing vanilla_er and msg")
    parser.add_argument("--msb-root", help="directory containing Witchy *-msb-dcx directories")
    parser.add_argument("--templates-only", action="store_true")
    parser.add_argument("--out", default="greenfield/mine_material_sources.tsv")
    args = parser.parse_args(argv)
    if not args.templates_only and not args.msb_root:
        parser.error("pass --msb-root or --templates-only")

    vv = os.path.join(args.artifacts, "vanilla_er", "vanilla_er")
    names = goods_names(os.path.join(args.artifacts, "msg", "engus", "item-msgbnd-dcx",
                                     "GoodsName.fmg.xml"))
    lots = stone_lots(os.path.join(vv, "ItemLotParam_map.csv"), names)
    templates = asset_templates(os.path.join(vv, "AssetEnvironmentGeometryParam.csv"), lots)
    if len(templates) != 19:
        raise SystemExit(f"expected 19 smithing-stone asset templates, found {len(templates)}")
    placements = None if args.templates_only else placed_assets(args.msb_root, templates)
    rows = emit(args.out, templates, placements)
    if not rows:
        raise SystemExit("no smithing-stone sources emitted")
    print(f"mine-material census: {len(templates)} templates, {len(rows)} placed reward rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
