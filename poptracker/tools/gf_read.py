#!/usr/bin/env python3
"""Greenfield data reader for the PopTracker pack generator.

The greenfield apworld (``greenfield/eldenring``) is the live Archipelago world; its ``core.py``
imports the AP framework (``BaseClasses``, ``worlds.AutoWorld``, ``Options``). We are NOT inside an
Archipelago checkout, so we import ``core`` under a set of permissive framework stubs -- enough to
run the module-level item/location id allocation (which is what we need) and then let it fail
harmlessly at the later ``make_dataclass(GFOptions, ...)`` step (that needs a real
``PerGameCommonOptions`` and produces nothing we read).

What we harvest, all authoritative:
  * ``core.item_name_to_id``      item name -> AP network item id   (region "<R> Lock" + real items)
  * ``core._item_class``          item name -> ItemClassification    (progression detection)
  * ``core.GREAT_RUNES``          the six great-rune item names
  * ``data.LOCATIONS``            region -> [(loc_name, ap_loc_id, flag)]   (ap id == AP network id)
  * ``data.REGIONS`` / ``HUB``    lock-item source list + the connective hub
  * ``region_spine.DLC_REGIONS``  Land-of-Shadow region set
  * ``region_spine.REGION_PARENT``the (sparse) child -> parent region tree
  * ``item_ids.LOCATION_ITEM``    ap_loc_id -> vanilla item name  (pool copy-count for consumables)
  * ``item_ids.DLC_ITEM_NAMES``   DLC-only item names

Everything is pure data; no seed is rolled. Returns the same normalized shapes the pack emitters in
gen_poptracker.py already consume, so the port is a reader swap, not an emitter rewrite.
"""
from __future__ import annotations
import enum
import importlib.util
import os
import sys
import types
from collections import Counter


def _dunder(n):
    return n.startswith("__") and n.endswith("__")


class _ItemClassification(enum.IntFlag):
    filler = 0
    progression = 1
    useful = 2
    trap = 4
    skip_balancing = 8
    progression_skip_balancing = 9


class _StubMeta(type):
    def __getattr__(cls, name):
        if _dunder(name):
            raise AttributeError(name)
        return 0


class _Stub(metaclass=_StubMeta):
    def __init__(self, *a, **k):
        pass

    def __init_subclass__(cls, **k):
        pass

    def __getattr__(self, name):
        if _dunder(name):
            raise AttributeError(name)
        return 0

    def __call__(self, *a, **k):
        return self


def _permissive_module(modname, preset=None):
    """A module whose every un-set attribute resolves to a fresh stub class (non-dunder only, so
    Python's own dataclass/typing machinery still sees real AttributeErrors)."""
    m = types.ModuleType(modname)
    for k, v in (preset or {}).items():
        setattr(m, k, v)

    def __getattr__(name):
        if _dunder(name):
            raise AttributeError(name)
        cls = _StubMeta(name, (_Stub,), {})
        setattr(m, name, cls)
        return cls

    m.__getattr__ = __getattr__
    return m


def _install_stubs():
    """Register the minimal AP-framework stub modules (idempotent enough for one process)."""
    sys.modules.setdefault("BaseClasses",
                           _permissive_module("BaseClasses", {"ItemClassification": _ItemClassification}))
    if "worlds" not in sys.modules:
        w = types.ModuleType("worlds")
        w.__path__ = []
        sys.modules["worlds"] = w
    sys.modules.setdefault("worlds.AutoWorld", _permissive_module("worlds.AutoWorld"))
    sys.modules.setdefault("Options", _permissive_module("Options"))
    sys.modules.setdefault("Utils", _permissive_module("Utils"))


def load_modules(apworld_dir):
    """Import the greenfield submodules we read. ``core`` is allowed to fail after its id
    allocation (the ``GFOptions`` dataclass build needs a real framework); we only require that
    ``item_name_to_id`` made it into the module namespace first."""
    apworld_dir = os.path.abspath(apworld_dir)
    _install_stubs()
    pkg_name = "eldenring"
    if pkg_name not in sys.modules:
        pkg = types.ModuleType(pkg_name)
        pkg.__path__ = [apworld_dir]
        sys.modules[pkg_name] = pkg
    else:
        sys.modules[pkg_name].__path__ = [apworld_dir]

    def _load(sub, required_attr=None):
        full = f"{pkg_name}.{sub}"
        spec = importlib.util.spec_from_file_location(full, os.path.join(apworld_dir, f"{sub}.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[full] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:
            if required_attr and not hasattr(mod, required_attr):
                raise
        return mod

    data = _load("data")
    region_spine = _load("region_spine")
    item_ids = _load("item_ids")
    core = _load("core", required_attr="item_name_to_id")
    return {"core": core, "data": data, "region_spine": region_spine, "item_ids": item_ids}


# --------------------------------------------------------------------------- normalized readers
def _ordered_regions(data, region_spine):
    """Base regions (SPINE order) first, then DLC, then any LOCATIONS-only regions (hub, finale)."""
    dlc = set(region_spine.DLC_REGIONS)
    spine = list(region_spine.SPINE)
    base = [r for r in spine if r not in dlc]
    dlc_ordered = [r for r in spine if r in dlc]
    ordered = base + dlc_ordered
    for r in data.LOCATIONS:                    # Roundtable Hold (hub), Ashen Capital (finale)
        if r not in ordered:
            ordered.append(r)
    return [r for r in ordered if r in data.LOCATIONS]


def read_regions(mods):
    data, region_spine = mods["data"], mods["region_spine"]
    region_locations = {region: [(name, ap) for (name, ap, _flag) in locs]
                        for region, locs in data.LOCATIONS.items()}
    return {
        "ordered_regions": _ordered_regions(data, region_spine),
        "dlc_set": set(region_spine.DLC_REGIONS),
        "region_locations": region_locations,
    }


def _is_key(name, key_substrings):
    return any(sub in name for sub in key_substrings)


def read_items(mods, key_substrings):
    """Tracked items: the region "<R> Lock" gates (always) + curated key items. ap_code is the AP
    network item id; stage is the pool copy-count (so multi-copy goods -- Scadutree Fragment, etc. --
    render as consumables with a real max)."""
    core, item_ids = mods["core"], mods["item_ids"]
    name_to_id = core.item_name_to_id
    item_class = getattr(core, "_item_class", {})
    dlc_names = set(getattr(item_ids, "DLC_ITEM_NAMES", set()))
    copies = Counter(getattr(item_ids, "LOCATION_ITEM", {}).values())
    prog = _ItemClassification.progression

    out = []
    for name, ap_code in name_to_id.items():
        is_lock = name.endswith(" Lock")
        if not (is_lock or _is_key(name, key_substrings)):
            continue
        cls = item_class.get(name, 0)
        # a lock always gates; a curated key we keep if progression-ish or a known count good
        stage = copies.get(name, 1) or 1
        out.append({
            "name": name, "ap_code": int(ap_code) if ap_code is not None else None,
            "lock": is_lock, "is_dlc": name in dlc_names,
            "stage": stage, "progression": bool(int(cls) & int(prog)) if cls else is_lock,
        })
    out.sort(key=lambda i: (not i["lock"], i["is_dlc"], i["name"]))
    return out


def _slug(s):
    out = "".join(c.lower() if c.isalnum() else "_" for c in s)
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_")


def read_region_graph(mods, regions, item_code_fn, dlc_root_region="Gravesite"):
    """Greenfield region reachability, expressed in the shape emit_region_graph_lua consumes.

    Adjacency: the hub (Roundtable Hold) reaches every top-level region; the sparse REGION_PARENT
    tree adds the four nested links (Raya Lucaria<-Liurnia, Leyndell<-Altus, Sewer<-Leyndell,
    Scaduview<-Shadow Keep). Lock gates: each of the 31 REGIONS is gated by its "<R> Lock" item when
    region gating is active. Vanilla key gates (Academy Glintstone Key, gaol keys, ...) are the
    logic-layer P2 port and are intentionally left empty here.
    """
    data, region_spine, core = mods["data"], mods["region_spine"], mods["core"]
    parent = dict(region_spine.REGION_PARENT)
    hub = data.HUB
    name_to_id = core.item_name_to_id

    adj = {}
    hub_slug = _slug(hub)
    adj[hub_slug] = []
    for region in regions["ordered_regions"]:
        if region == hub:
            continue
        par = parent.get(region, hub)
        ps = _slug(par)
        adj.setdefault(ps, [])
        if _slug(region) not in adj[ps]:
            adj[ps].append(_slug(region))

    locks = {}
    for region in data.REGIONS:
        lock_name = f"{region} Lock"
        if name_to_id.get(lock_name) is not None:
            locks[_slug(region)] = [item_code_fn(lock_name, True)]

    keys = {}                                   # P2: vanilla key gates
    gate_codes = sorted({c for v in locks.values() for c in v}
                        | {c for v in keys.values() for c in v})
    return {
        "adj": adj, "locks": locks, "keys": keys,
        "root": hub_slug, "dlc_root": _slug(dlc_root_region), "gate_codes": gate_codes,
        "stats": {"edges": sum(len(v) for v in adj.values()),
                  "lock_gated": len(locks), "key_gated": len(keys),
                  "skipped_untracked_gates": 0},
    }
