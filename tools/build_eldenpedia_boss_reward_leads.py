#!/usr/bin/env python3
"""Build exact Eldenpedia boss-reward leads from pinned pages and game-data joins."""
from __future__ import annotations

import argparse, csv, importlib.util, json, re
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "greenfield" / "evidence" / "wiki-audit"
LEADS = AUDIT / "eldenpedia-boss-reward-check-leads.tsv"
MANIFEST = AUDIT / "eldenpedia-combatant-pages.tsv"
FIELDS = ("lead_id", "subject_kind", "subject_id", "claim_kind", "normalized_value",
          "source_ids", "independence_families", "disposition", "game_version",
          "exact_citations", "summary", "limitations")
MANIFEST_FIELDS = ("source_id", "page_id", "revision_id", "revision_timestamp",
                   "revision_sha1", "title", "canonical_url", "revision_url",
                   "combatant_category", "drop_links", "disposition")


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); assert spec.loader
    spec.loader.exec_module(result)
    return result


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def item_name(location: str) -> str:
    value = location.split(" :: ", 1)[1].split(" - ", 1)[0]
    value = re.sub(r"^\[[^]]+\]\s*", "", value)
    return value.replace("[", "").replace("]", "")


def infobox_field(content: str, field: str) -> str:
    match = re.search(rf"(?ims)^\|\s*{field}\s*=\s*(.*?)(?=^\|\s*[\w ]+\s*=|^}})", content)
    return match.group(1) if match else ""


def links(value: str) -> list[str]:
    return [raw.split("|")[-1].replace("<nowiki>", "").replace("</nowiki>", "")
            for raw in re.findall(r"\[\[([^\]]+)\]\]", value)]


def render(rows: list[dict[str, str]], fields: tuple[str, ...]) -> str:
    out = StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    return out.getvalue()


def build(capture: dict[str, list[dict]]) -> tuple[list[dict[str, str]], list[dict[str, str]], dict]:
    boss_drops = module("_boss_drops", ROOT / "greenfield/eldenring/boss_drops.py")
    boss_rewards = module("_boss_rewards", ROOT / "greenfield/eldenring/boss_reward_lots.py")
    healthbars = module("_healthbars", ROOT / "greenfield/eldenring/boss_healthbars.py")
    data = module("_data", ROOT / "greenfield/eldenring/data.py")
    pages = {int(page["pageid"]): (category, page) for category, entries in capture.items()
             for page in entries}
    by_title = {norm(page["title"]): (category, page) for category, page in pages.values()}
    locations = {flag: (ap_id, location, region) for region, entries in data.LOCATIONS.items()
                 for location, ap_id, flag in entries}
    joins = [(flag, entity, "boss-drop entity")
             for flag, entity in boss_drops.BOSS_DROP_ENTITY.items()]
    joins += [(flag, defeat, "boss-reward defeat flag")
              for flag, defeat in boss_rewards.BOSS_REWARD_DEFEAT.items()]
    emitted, used = {}, {}
    stats = {"candidate_game_data_joins": len(joins), "refused_missing_page": 0,
             "refused_missing_exact_drop": 0, "refused_missing_ap_check": 0}
    for flag, boss_key, join_kind in joins:
        if boss_key not in healthbars.BOSS_HEALTHBARS or flag not in locations:
            stats["refused_missing_ap_check"] += 1; continue
        boss = healthbars.BOSS_HEALTHBARS[boss_key][3]
        found = by_title.get(norm(boss))
        if not found:
            stats["refused_missing_page"] += 1; continue
        category, page = found
        revision = page["revisions"][0]
        content = revision["slots"]["main"]["content"]
        drop_links = links(infobox_field(content, "drops"))
        ap_id, location, region = locations[flag]
        exact = [drop for drop in drop_links if norm(drop) == norm(item_name(location))]
        if len(exact) != 1:
            stats["refused_missing_exact_drop"] += 1; continue
        page_id, revision_id = int(page["pageid"]), int(revision["revid"])
        source_id = f"wiki:eldenpedia:page-{page_id}:revision-{revision_id}"
        used[source_id] = {
            "source_id": source_id, "page_id": str(page_id), "revision_id": str(revision_id),
            "revision_timestamp": revision["timestamp"], "revision_sha1": revision["sha1"],
            "title": page["title"],
            "canonical_url": "https://eldenring.wiki.gg/wiki/" + page["title"].replace(" ", "_"),
            "revision_url": f"https://eldenring.wiki.gg/w/index.php?oldid={revision_id}",
            "combatant_category": category, "drop_links": str(len(drop_links)),
            "disposition": "lead_only",
        }
        value = {"boss": boss, "flag": flag, "item_name": exact[0], "region": region}
        emitted[ap_id] = {
            "lead_id": f"eldenpedia-boss-page-{page_id}-revision-{revision_id}-check-{ap_id}",
            "subject_kind": "check", "subject_id": str(ap_id), "claim_kind": "identity_region",
            "normalized_value": json.dumps(value, ensure_ascii=False, sort_keys=True,
                                             separators=(",", ":")),
            "source_ids": source_id, "independence_families": "gameplay-wiki:eldenpedia",
            "disposition": "lead_only", "game_version": "unknown",
            "exact_citations": (f"eldenpedia:pageid-{page_id}:revision-{revision_id}:"
                                f"infobox-drops:{exact[0]};project:{join_kind}:flag-{flag}:boss-{boss_key}"),
            "summary": (f"Eldenpedia revision {revision_id} lists {exact[0]} as a drop from {boss}; "
                        f"committed game data joins AP flag {flag} to that boss via {join_kind}."),
            "limitations": ("Community-wiki reward lead cross-checked against an exact committed "
                            "boss/flag join. It does not prove access, route order, patch completeness, "
                            "event timing, or absence of another acquisition."),
        }
    rows = sorted(emitted.values(), key=lambda row: row["lead_id"])
    manifests = sorted(used.values(), key=lambda row: row["source_id"])
    stats["matched_checks"] = len(rows); stats["pinned_pages"] = len(manifests)
    return rows, manifests, stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    rows, manifest, stats = build(json.loads(args.capture.read_text(encoding="utf-8")))
    LEADS.write_text(render(rows, FIELDS), encoding="utf-8")
    MANIFEST.write_text(render(manifest, MANIFEST_FIELDS), encoding="utf-8")
    (AUDIT / "eldenpedia-boss-reward-coverage.json").write_text(
        json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(stats, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
