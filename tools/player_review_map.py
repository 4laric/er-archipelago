"""Map presentation from recorded item coordinates, never nearest-grace guesses."""
import csv
import json
import math
from pathlib import Path
from overworld_fold import world_xz

INPUTS = (
    "greenfield/item_grace_coords.tsv",
    "greenfield/maps/map_calibration.json",
    "greenfield/maps/map_calibration_dlc.json",
    "greenfield/maps/lands_between_map.svg",
    "greenfield/maps/land_of_shadow_map.svg",
)


def load_map(root):
    root = Path(root)
    positions = {}
    with (root / INPUTS[0]).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader((line for line in handle if not line.startswith("#")), delimiter="\t"):
            if row["kind"] != "item":
                continue
            flag, x, z = int(row["key"]), float(row["x"]), float(row["z"])
            if not math.isfinite(x) or not math.isfinite(z):
                raise ValueError("Non-finite player map coordinate")
            folded = world_xz(row["map_id"], x, z)
            if folded:
                point = {"map": folded[0], "x": round(folded[1], 1), "z": round(folded[2], 1)}
                if point not in positions.setdefault(flag, []):
                    positions[flag].append(point)
    maps = {}
    for key, calibration, svg in (("m60", INPUTS[1], INPUTS[3]), ("m61", INPUTS[2], INPUTS[4])):
        maps[key] = {"calibration": json.loads((root / calibration).read_text()),
                     "svg": (root / svg).read_text(encoding="utf-8")}
    return positions, maps
