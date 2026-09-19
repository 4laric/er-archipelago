"""WebWorld.options_presets -- ready-made starting points for players who skip the web wizard.

Archipelago turns each entry into (a) a preset dropdown on the WebHost player-options page and (b) a
ready-to-use yaml written under Players/Templates/Presets/ by "Generate Template Options". The
Launcher's Options Creator has no preset support, so for Launcher-only players the answer is the
short "Start Here" page plus that folder.

A preset carries ONLY deviations from the option defaults, spelled the way the yaml spells them
(choice names as strings, toggles as bools, ranges as ints). The wizard's own starting points
(tools/dump_options_metadata.PRESETS) are a separate table with descriptions; these four are the
ones that map onto them, and tests/test_gf_options_presets.py keeps both honest.

Two rules a preset must obey, both pinned by that test:
  * every key must be a live option, and every value must parse for that option;
  * every SCALAR key must stay on the simple UI (Visibility.simple_ui). The WebHost applies a preset
    with an unguarded getElementById(key).value = ..., so a key that is hidden from the page throws
    and the whole dropdown stops working.
"""
from typing import Any, Dict

# enable_dlc defaults ON (it is a DefaultOnToggle), so every base-game preset states
# `enable_dlc: false` -- that is a real deviation and the point of the preset.
# num_regions defaults to 6, so "Base Game" alone is a six-region base-game run.
OPTIONS_PRESETS: Dict[str, Dict[str, Any]] = {
    "Base Game": {"enable_dlc": False},
    "Base Game - Short Run": {"enable_dlc": False, "num_regions": 4},
    "Base Game - Whole Map": {"enable_dlc": False, "num_regions": 0},
    "DLC Only (experimental)": {"dlc_only": True, "num_regions": 0},
}
