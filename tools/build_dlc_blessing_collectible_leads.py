#!/usr/bin/env python3
"""Emit conservative second-source bindings for DLC blessing collectibles."""
from __future__ import annotations

import csv
import importlib.util
import json
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "greenfield/evidence/wiki-audit/dlc-blessing-collectible-check-leads.tsv"
REPORT = ROOT / "greenfield/evidence/wiki-audit/dlc-blessing-collectible-coverage.json"
FIELDS = ("lead_id", "subject_kind", "subject_id", "claim_kind", "normalized_value",
          "source_ids", "independence_families", "disposition", "game_version",
          "exact_citations", "summary", "limitations")

# Only anchors that uniquely identify one current AP check are admitted. Bundled or numbered rows
# whose guide text does not distinguish the underlying flags are intentionally absent.
SCADUTREE = {
    7773207: "Rauh Ancient Ruins stairs altar",
    7774548: "Lesser Golden Hippopotamus west of Viaduct Minor Tower",
    7774549: "pot-carrying shadow in the Rauh scorpion area",
    7771791: "Belurat spider-scorpion room Cross",
    7771810: "secret Belurat statue reached from Enir-Ilim",
    7774551: "Cerulean Coast cave guarded by a Demi-Human Chief",
    7771862: "Enir-Ilim altar beyond the bird rooftops",
    7773495: "Highroad Cross",
    7774544: "pot-carrying shadow southwest of Cliffroad Terminus",
    7774545: "Main Gate Cross",
    7774546: "Three-Path Cross",
    7774552: "pot-carrying shadow east of Scorched Ruins",
    7774554: "Marika statue beside Castle Front",
    7773651: "Jagged Peak corpse above the two spiritsprings",
    7773508: "Marika statue on the road to Shadow Keep",
    7773589: "Scaduview Cross",
    7773939: "Marika statue in the flooded church district",
    7774560: "pot-carrying shadow in northeast Moorth Ruins",
    7774562: "Moorth Ruins Cross",
    7774563: "pond north of Moorth Ruins",
    7774571: "waterfall south of the Ruins of Unte",
    7774564: "Shadow Keep Back Gate",
}

REVERED = {
    7772023: "large inquisitor in Midra's library",
    7773357: "glowing enemy in the first Rauh ruins room",
    7771799: "Belurat tree statue near Small Private Altar",
    7771808: "statue after Divine Beast Dancing Lion",
    7771812: "Belurat glowing pot enemy beyond Small Private Altar",
    7773236: "altar east of Cliffroad Terminus",
    7773388: "altar southeast of Scorched Ruins",
    7773401: "statue near Ellac River Cave exit",
    7773334: "altar north of Greatbridge North",
    7773603: "Village of Flies hill altar",
    7773617: "statue southeast of the Ruins of Unte",
    7771934: "Storehouse First Floor hanging specimen",
}


def _module(path: Path):
    spec = importlib.util.spec_from_file_location("_data", path)
    result = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(result)
    return result


def _render(rows):
    out = StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def main():
    data = _module(ROOT / "greenfield/eldenring/data.py")
    checks = {ap_id: (region, name) for region, entries in data.LOCATIONS.items()
              for name, ap_id, _flag in entries}
    rows = []
    for item_name, bindings, source_id, family in (
        ("Scadutree Fragment", SCADUTREE, "wiki:gamesradar:scadutree-fragments:20260902",
         "gameplay-guide:gamesradar"),
        ("Revered Spirit Ash", REVERED, "wiki:samurai-gamers:revered-spirit-ash:20260902",
         "gameplay-guide:samurai-gamers"),
    ):
        for ap_id, anchor in bindings.items():
            region, location = checks[ap_id]
            if item_name not in location:
                raise SystemExit(f"{ap_id} is not a {item_name} check: {location}")
            slug = "gamesradar-scadutree" if item_name == "Scadutree Fragment" else "samurai-revered"
            rows.append({
                "lead_id": f"{slug}-check-{ap_id}", "subject_kind": "check",
                "subject_id": str(ap_id), "claim_kind": "identity_region",
                "normalized_value": json.dumps({"item_name": item_name, "location": anchor,
                                                "region": region}, separators=(",", ":")),
                "source_ids": source_id, "independence_families": family,
                "disposition": "lead_only", "game_version": "unknown",
                "exact_citations": f"{slug}:collectible-list:{anchor};project:check:{ap_id}/detection",
                "summary": f"The complete collectible guide places {item_name} at {anchor}; that exact landmark identifies AP check {ap_id} in {region}.",
                "limitations": "One commercial-guide family and a live retrieval pinned by response-body hash. The repeated item is admitted only where the landmark uniquely selects one AP check; this does not prove access logic, route order, or event timing.",
            })
    rows.sort(key=lambda row: row["lead_id"])
    OUTPUT.write_text(_render(rows), encoding="utf-8")
    report = {"matched_checks": len(rows), "scadutree_fragment": len(SCADUTREE),
              "revered_spirit_ash": len(REVERED),
              "explicitly_withheld_ambiguous_or_unmatched": 69 - len(rows)}
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
