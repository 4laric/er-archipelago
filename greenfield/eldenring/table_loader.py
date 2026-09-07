"""THE loader for the generated data tables (#1464).

The generated tables -- `data.py` (HUB/REGIONS/LOCATIONS), `item_ids.py`, `shop_data.py`,
`boss_*.py`, ... -- live in the `tables/` subpackage. Nothing in `core.py` imports one of them by
name any more; `core.py` calls `table_loader.load()` once and reads `world.tables`.

WHY `tables/` AND NOT `data/`. #1464 asked for a `data/` package. `data.py` is itself one of the
generated modules (and by far the most-imported one: `from .data import LOCATIONS`), so a package
called `data` would have to BE that module's namespace -- `data/__init__.py` re-exporting the
literals -- and every "is this the package or the module?" question in the tree would have two
answers. `tables/` keeps `tables.data` a plain module and leaves the loader a separate, ALWAYS
PRESENT file. That last property is the point of the acceptance criterion below: if the loader
lived in `tables/__init__.py`, deleting the package would delete the code that is supposed to
explain the deletion.

DELETING `tables/` IS A SUPPORTED STATE (#1464 acceptance). The one-apworld design wants our tables
to be a build-time-optional module. `load()` therefore raises `MissingTablesError` NAMING the
modules it could not import, and `core.py` calls it as its first world-local import -- so a
tables-less tree refuses to register the World with that message, instead of an ImportError from
the middle of `core.py` (or, worse, one of the `except ImportError: pass` fallbacks below quietly
degrading to an empty table and generating a broken seed).

ID BASES LIVE HERE, not beside the orchestration code in `core.py`: they describe the id space the
tables occupy, and the client contract depends on them being stable.
"""

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, List, Mapping, Tuple
import importlib
import importlib.util
import os

# --- the id space -------------------------------------------------------------------------------
# 🛑 FROZEN. Every shipped seed and the client contract are keyed on these. Moving one silently
# remaps every check/item id -- see tests/test_gf_data.py, which asserts them independently.
LOCATION_ID_BASE = 7770000        # gen_data.BASE_AP: the ap-id of the first generated check
LOCK_ITEM_ID_BASE = 7780000       # "<Region> Lock" + FILLER + the ashen lock (core allocates from here)
REAL_ITEM_ID_BASE = 7790000       # vanilla catalog items (real-item-pool)
ABILITY_UNLOCK_ITEM_BASE = 7900000  # contract.ABILITY_UNLOCK_ITEM_BASE (ability-lock items)

# Every module in `tables/` that is AUTO-GENERATED. The grep test
# (tests/test_gf_data_tables_loader.py) reads this list, so adding a generated table here is what
# puts it under the no-direct-import rule.
GENERATED_MODULES: Tuple[str, ...] = (
    "boss_data",
    "boss_drops",
    "boss_healthbars",
    "boss_reward_lots",
    "boss_sweeps",
    "check_lots_data",
    "data",
    "enemy_drops_data",
    "enemy_names",
    "evidence_progression_hosts",
    "item_ids",
    "item_tiers",
    "location_tags",
    "mine_material_data",
    "missable_locations",
    "region_graces",
    "region_open_flags",
    "region_play_ids",
    "repeatable_goods",
    "shop_data",
    "shop_stock_data",
    "spawn_trap_data",
)

# The tables that MUST be present for the World to mean anything. The rest are optional by
# construction -- core.py has always tolerated their absence (a pre-regen tree, an older apworld),
# and turning that tolerance into a hard failure here would be a behaviour change, not a layering
# one.
REQUIRED_MODULES: Tuple[str, ...] = ("data",)

DEFAULT_MODE = "shattering"


class MissingTablesError(ImportError):
    """The generated tables are absent. Raised by `load()`, NAMING what is missing."""


@dataclass(frozen=True)
class Tables:
    """One loaded table set. `core.py` and (eventually) the features read this, never a module."""

    mode: str
    modules: Mapping[str, Any]

    # --- regions + locations (tables/data.py) ---
    hub: str
    regions: Tuple[str, ...]
    locations: Mapping[str, List[Tuple[str, int, int]]]
    finale_region: Any
    finale_host_region: Any

    # --- the real-item pool (tables/item_ids.py) ---
    item_catalog: Mapping[str, int]
    location_item: Mapping[Any, Any]
    goods_hold_cap: Mapping[str, int]
    filler_pool: Any
    dlc_item_names: Any
    location_units: Mapping[Any, int]

    # --- region wiring ---
    region_open_flags: Mapping[str, Any]
    regions_pending_bucket: FrozenSet[str]

    # --- location policy sets (tables/location_tags.py) ---
    defaulted_region_aps: FrozenSet[int]
    hub_unattributed_aps: FrozenSet[int]
    erdtree_burn_aps: FrozenSet[int]
    shop_release_gated_aps: FrozenSet[int]

    # --- shops ---
    shop_row_flags: Mapping[str, Any]
    dlc_gated_shop_check_flags: FrozenSet[int]

    # --- traps ---
    spawn_traps: Mapping[Any, Any]

    # --- the id space (see module docstring) ---
    location_id_base: int = LOCATION_ID_BASE
    lock_item_id_base: int = LOCK_ITEM_ID_BASE
    real_item_id_base: int = REAL_ITEM_ID_BASE
    ability_unlock_item_base: int = ABILITY_UNLOCK_ITEM_BASE

    def module(self, name: str) -> Any:
        """The raw generated module `name`, or None if it is not present.

        The escape hatch for the tables this dataclass does not surface yet (boss data, sweeps,
        check lots, ...). It is deliberately an accessor rather than an import: a caller that goes
        through here is still reading a LOADED table set, so a tables-less tree gives it None
        instead of an ImportError."""
        return self.modules.get(name)


_HERE = os.path.dirname(os.path.abspath(__file__))


def _import(name: str):
    """The `tables.<name>` module, or None.

    Two ways in, because this file is read two ways: as a member of the installed world package
    (the relative import, which also works inside a zipped .apworld), and by FILE PATH from the
    source tree -- tools and the pure-python tests load it that way, where `__package__` is empty
    and there is no package to be relative to."""
    if __package__:
        try:
            return importlib.import_module("." + name, __package__ + ".tables")
        except Exception:
            pass
    path = os.path.join(_HERE, "tables", name + ".py")
    if not os.path.isfile(path):
        return None
    try:
        spec = importlib.util.spec_from_file_location("_gf_tables_" + name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


_CACHE: Dict[str, Tables] = {}


def load(mode: str = DEFAULT_MODE) -> Tables:
    """Load the generated tables. `mode` is the table set to load.

    Only "shattering" exists today -- the parameter is the seam the one-apworld design needs (a
    second author's tables alongside ours), not a live option. An unknown mode is an error rather
    than a silent fallback to ours.

    Raises MissingTablesError, naming the modules, when the `tables/` package is absent."""
    if mode != DEFAULT_MODE:
        raise MissingTablesError(
            "Elden Ring: unknown data-table mode %r (available: %r)" % (mode, DEFAULT_MODE))
    cached = _CACHE.get(mode)
    if cached is not None:
        return cached

    modules = {name: _import(name) for name in GENERATED_MODULES}
    missing = [name for name in REQUIRED_MODULES if modules.get(name) is None]
    if missing:
        raise MissingTablesError(
            "Elden Ring cannot register: the generated data tables are missing. "
            "Could not import %s from the `tables` package (worlds/eldenring/tables/). "
            "Regenerate them with `python greenfield/gen_data.py`, or install an apworld that "
            "ships them." % ", ".join("tables.%s" % m for m in sorted(missing)))

    def g(mod: str, attr: str, default):
        m = modules.get(mod)
        if m is None:
            return default
        return getattr(m, attr, default)

    d = modules["data"]
    tables = Tables(
        mode=mode,
        modules=modules,
        hub=d.HUB,
        regions=tuple(d.REGIONS),
        locations=d.LOCATIONS,
        finale_region=d.FINALE_REGION,
        finale_host_region=d.FINALE_HOST_REGION,
        item_catalog=g("item_ids", "ITEM_CATALOG", {}),
        location_item=g("item_ids", "LOCATION_ITEM", {}),
        goods_hold_cap=g("item_ids", "GOODS_HOLD_CAP", {}),
        filler_pool=g("item_ids", "FILLER_POOL", []),
        dlc_item_names=g("item_ids", "DLC_ITEM_NAMES", set()),
        location_units=g("item_ids", "LOCATION_UNITS", {}),
        region_open_flags=g("region_open_flags", "REGION_OPEN_FLAGS", {}),
        regions_pending_bucket=frozenset(g("region_play_ids", "REGIONS_PENDING_BUCKET", frozenset())),
        defaulted_region_aps=frozenset(g("location_tags", "DEFAULTED_REGION_APS", frozenset())),
        hub_unattributed_aps=frozenset(g("location_tags", "HUB_UNATTRIBUTED_APS", frozenset())),
        erdtree_burn_aps=frozenset(g("location_tags", "ERDTREE_BURN_APS", frozenset())),
        shop_release_gated_aps=frozenset(g("location_tags", "SHOP_RELEASE_GATED_APS", frozenset())),
        shop_row_flags=g("shop_data", "SHOP_ROW_FLAGS", {}),
        dlc_gated_shop_check_flags=frozenset(g("shop_data", "DLC_GATED_SHOP_CHECK_FLAGS", frozenset())),
        spawn_traps=g("spawn_trap_data", "SPAWN_TRAPS", {}),
    )
    _CACHE[mode] = tables
    return tables
