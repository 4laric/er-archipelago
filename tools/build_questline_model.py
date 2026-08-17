#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the typed questline evidence model.

`questline_dag.tsv` is intentionally strict: both ends are event flags derived from game data.
That makes it unable to represent possession requirements such as the Hole-Laden Necklace without
lying about the id space. This layer keeps those machine edges and adds the separately licensed,
revision-pinned evidence in `questline_cc_wiki.tsv` using typed node ids:

    flag:510110
    item:Hole-Laden Necklace

The output is still evidence, not access logic. Nothing in the world imports it.
"""
import argparse
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GF = os.path.join(ROOT, "greenfield")
CC_INPUT = os.path.join(GF, "questline_cc_wiki.tsv")
OUT = os.path.join(GF, "questline_model.tsv")

sys.path.insert(0, HERE)
import build_questline_dag as dag  # noqa: E402

ITEMS = dag._load_module("gf_item_ids", os.path.join(GF, "eldenring", "item_ids.py"))

COLUMNS = [
    "source_node", "target_node", "relation", "group_id", "group_semantics",
    "evidence_kind", "evidence_origin", "quest", "source_label", "target_label",
    "source_region", "target_region", "claim", "source_game_ref", "id_evidence", "source_page",
    "source_page_id", "source_revision", "source_timestamp", "source_url", "license",
]
CC_COLUMNS = [
    "source_node", "target_node", "relation", "group_id", "group_semantics", "quest", "claim",
    "source_game_ref", "id_evidence", "source_page", "source_page_id", "source_revision", "source_timestamp",
    "source_url", "license",
]
RELATION = {"set": "requires", "clear": "excludes", "unknown": "unknown"}


def _tsv_rows(path):
    if not os.path.isfile(path):
        sys.exit("FATAL: required input is absent: %s" % os.path.relpath(path, ROOT))
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(
            (line for line in fh if not line.lstrip().startswith("#")), delimiter="\t"))
    if not rows:
        sys.exit("FATAL: %s parsed to ZERO rows" % os.path.relpath(path, ROOT))
    return rows


def _flag_id(node):
    if not node.startswith("flag:"):
        return None
    raw = node.split(":", 1)[1]
    return int(raw) if raw.isdigit() else None


def _region(name):
    return name.split(" ::", 1)[0] if " ::" in name else ""


def build():
    machine, _tally, notes = dag.build()
    world = notes["world"]
    labels = {}
    for edge in machine:
        if edge["source_label"] or edge["source_label_ja"]:
            labels.setdefault(edge["source_flag"], edge["source_label"] or edge["source_label_ja"])

    rows = []
    for edge in machine:
        rows.append({
            "source_node": "flag:%d" % edge["source_flag"],
            "target_node": "flag:%d" % edge["target_flag"],
            "relation": RELATION[edge["sense"]],
            "group_id": "game:%s" % edge["alt_group"],
            "group_semantics": edge["group_semantics"],
            "evidence_kind": "game_data",
            "evidence_origin": edge["tool"],
            "quest": "",
            "source_label": (world.flag_name.get(edge["source_flag"])
                             or labels.get(edge["source_flag"], "")),
            "target_label": edge["target_name"],
            "source_region": edge["source_region"],
            "target_region": edge["target_region"],
            "claim": edge["evidence"],
            "source_game_ref": "event_flag:%d" % edge["source_flag"],
            "id_evidence": "questline_dag.tsv:%s" % edge["tool"],
            "source_page": "",
            "source_page_id": "",
            "source_revision": "",
            "source_timestamp": "",
            "source_url": "",
            "license": "project-derived",
        })

    cc = _tsv_rows(CC_INPUT)
    if list(cc[0]) != CC_COLUMNS:
        sys.exit("FATAL: questline_cc_wiki.tsv columns drifted: %r (expected %r)"
                 % (list(cc[0]), CC_COLUMNS))
    for edge in cc:
        target = _flag_id(edge["target_node"])
        source = _flag_id(edge["source_node"])
        target_name = world.flag_name.get(target, "") if target is not None else ""
        source_name = (world.flag_name.get(source, "") or labels.get(source, "")) if source else ""
        if edge["source_node"].startswith("item:"):
            source_name = edge["source_node"].split(":", 1)[1]
        rows.append({
            **edge,
            "evidence_kind": "cc_wiki",
            "evidence_origin": "eldenring.wiki.gg",
            "source_label": source_name,
            "target_label": target_name,
            "source_region": _region(source_name),
            "target_region": _region(target_name),
        })

    rows.sort(key=lambda r: (
        r["target_node"], r["source_node"], r["relation"], r["evidence_kind"],
        r["evidence_origin"], r["group_id"], r["source_revision"],
    ))
    return rows, world


def validate(rows, world):
    """Refuse wrong id spaces, unpinned attribution, and evidence that points at no live check."""
    if not rows:
        sys.exit("FATAL: typed questline model has ZERO rows")
    seen = set()
    cc = 0
    for row in rows:
        key = tuple(row[c] for c in COLUMNS)
        if key in seen:
            sys.exit("FATAL: duplicate questline evidence row: %s -> %s"
                     % (row["source_node"], row["target_node"]))
        seen.add(key)
        if row["relation"] not in {"requires", "excludes", "unknown"}:
            sys.exit("FATAL: invalid relation %r" % row["relation"])
        if row["group_semantics"] not in {"single", "any", "all", "unknown"}:
            sys.exit("FATAL: invalid group semantics %r" % row["group_semantics"])
        target = _flag_id(row["target_node"])
        if target is None or not world.is_check(target):
            sys.exit("FATAL: target is not a live event-flag check: %s" % row["target_node"])
        if row["source_node"].startswith("flag:"):
            if _flag_id(row["source_node"]) is None:
                sys.exit("FATAL: malformed event-flag node: %s" % row["source_node"])
            expected = "event_flag:" + row["source_node"].split(":", 1)[1]
            if row["source_game_ref"] != expected:
                sys.exit("FATAL: %s crosses id spaces: source_game_ref=%s, expected %s"
                         % (row["source_node"], row["source_game_ref"], expected))
        elif row["source_node"].startswith("item:"):
            name = row["source_node"].split(":", 1)[1]
            if name not in ITEMS.ITEM_CATALOG:
                sys.exit("FATAL: item node is not in the generated item catalog: %s" % name)
            if not row["source_game_ref"].startswith("goods:"):
                sys.exit("FATAL: item node %s lacks a typed goods: game reference" % name)
        else:
            sys.exit("FATAL: unknown source node type: %s" % row["source_node"])
        if row["evidence_kind"] == "cc_wiki":
            cc += 1
            required = ("quest", "claim", "id_evidence", "source_page", "source_page_id", "source_revision",
                        "source_timestamp", "source_url", "license")
            missing = [name for name in required if not row[name].strip()]
            if missing:
                sys.exit("FATAL: CC evidence %s -> %s lacks %s"
                         % (row["source_node"], row["target_node"], ", ".join(missing)))
            if row["license"] != "CC-BY-SA-4.0":
                sys.exit("FATAL: CC evidence carries unexpected license %r" % row["license"])
            if "eldenring.wiki.gg/" not in row["source_url"] or "oldid=" not in row["source_url"]:
                sys.exit("FATAL: CC evidence URL is not a pinned wiki.gg revision: %s"
                         % row["source_url"])
            if "fextra" in " ".join(row.values()).lower():
                sys.exit("FATAL: Fextralife is not a licensed input to this model")
    if cc == 0:
        sys.exit("FATAL: typed model contains ZERO CC-wiki evidence rows")
    cc_groups = {}
    for row in rows:
        if row["evidence_kind"] == "cc_wiki":
            cc_groups.setdefault(row["group_id"], []).append(row)
    for group_id, members in cc_groups.items():
        semantics = {row["group_semantics"] for row in members}
        targets = {row["target_node"] for row in members}
        if len(semantics) != 1:
            sys.exit("FATAL: CC group %s mixes semantics %s" % (group_id, sorted(semantics)))
        semantics = semantics.pop()
        if semantics == "single" and len(members) != 1:
            sys.exit("FATAL: CC group %s says single but has %d rows" % (group_id, len(members)))
        if semantics in {"any", "all"} and (len(members) < 2 or len(targets) != 1):
            sys.exit("FATAL: CC group %s says %s but does not hold multiple sources for one target"
                     % (group_id, semantics))


def render():
    rows, world = build()
    validate(rows, world)
    out = io.StringIO(newline="")
    out.write("# AUTO-GENERATED by tools/build_questline_model.py -- DO NOT EDIT.\n")
    out.write("# Typed evidence union over questline_dag.tsv + questline_cc_wiki.tsv.\n")
    out.write("# This file as a compilation is CC BY-SA 4.0; project-derived rows retain their "
              "underlying status. See release/ATTRIBUTION.md.\n")
    out.write("# EVIDENCE ONLY: nothing in the world imports this table. requires/excludes are "
              "candidate facts, not access rules.\n")
    out.write("# Nodes are typed (`flag:` / `item:`); never compare their bare ids across spaces.\n")
    counts = {kind: sum(r["evidence_kind"] == kind for r in rows)
              for kind in ("game_data", "cc_wiki")}
    out.write("# MEASURED: %d evidence rows (%d game-data, %d CC-wiki), %d typed edges.\n"
              % (len(rows), counts["game_data"], counts["cc_wiki"],
                 len({(r["source_node"], r["target_node"], r["relation"]) for r in rows})))
    writer = csv.DictWriter(out, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows({c: row.get(c, "") for c in COLUMNS} for row in rows)
    return out.getvalue()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    text = render()
    if text != render():
        sys.exit("FATAL: questline model generation is not deterministic")
    if args.check:
        if not os.path.isfile(OUT) or open(OUT, encoding="utf-8", newline="").read() != text:
            print("DRIFT: greenfield/questline_model.tsv is stale; run "
                  "`python tools/build_questline_model.py`.", file=sys.stderr)
            return 1
        print("--check: committed typed questline model matches a fresh build")
        return 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("wrote %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
