"""Feature registry for the greenfield ER world.

Each SPEC-PARITY phase (scaling, boss locks, shops, grace rando, ...) is ONE self-registered file in
features/. A feature contributes options, items, regions, rules, and slot_data via hooks; core.py
aggregates every registered feature, so adding a phase touches NO shared file. Feature modules may
import registry / Options / data / region_spine, but NEVER core (would cycle). The aggregation
helpers are pure (take an explicit feature list) so they unit-test without Archipelago.
"""
from typing import Any, Dict, List, Tuple

# slot_data keys are gated through the contract (F2). registry.py must ALSO load standalone (the
# pure unit suite spec-loads it by path, no package context), and contract.py itself is stdlib-only,
# so fall back to a by-path load when the relative import has no parent package.
try:
    from . import contract as _contract
except ImportError:
    import importlib.util as _ilu
    import os as _os
    _spec = _ilu.spec_from_file_location(
        "gf_contract_standalone", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "contract.py"))
    _contract = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_contract)


class Feature:
    """Subclass + @register in a features/ module. Override only the hooks you need."""
    name: str = ""
    OPTIONS: Dict[str, Any] = {}   # {yaml_field: Option class}      -> merged into GFOptions
    ITEMS: Dict[str, Any] = {}     # {item_name: ItemClassification} -> ids allocated + classified

    def generate_early(self, world) -> None: ...
    def create_items(self, world) -> List: return []
    def create_regions(self, world) -> None: ...
    def set_rules(self, world) -> None: ...
    def slot_data(self, world) -> Dict[str, Any]: return {}


_REGISTRY: List["Feature"] = []


def register(cls):
    """Class decorator: instantiate + register (idempotent per class, so re-import is safe)."""
    if not any(type(f) is cls for f in _REGISTRY):
        _REGISTRY.append(cls())
    return cls


def features() -> List["Feature"]:
    return list(_REGISTRY)


# ---- pure aggregation helpers (unit-testable with a synthetic feature list) ------------------
def collect_option_fields(core_fields: List[Tuple[str, Any]], feats) -> List[Tuple[str, Any]]:
    fields = list(core_fields)
    seen = {n for n, _ in fields}
    for f in feats:
        for name, opt in f.OPTIONS.items():
            if name in seen:
                raise ValueError(f"option field '{name}' declared by two sources")
            fields.append((name, opt)); seen.add(name)
    return fields


def collect_item_classes(base: Dict[str, Any], feats) -> Dict[str, Any]:
    out = dict(base)
    for f in feats:
        for name, cls in f.ITEMS.items():
            if name in out:
                raise ValueError(f"item '{name}' declared twice")
            out[name] = cls
    return out


def allocate_item_ids(base_ids: Dict[str, int], start: int, feats) -> Dict[str, int]:
    ids = dict(base_ids); nxt = start
    for f in feats:
        for name in f.ITEMS:
            if name not in ids:
                ids[name] = nxt; nxt += 1
    return ids


def merge_slot_data(base: Dict[str, Any], feats, world) -> Dict[str, Any]:
    sd = dict(base)
    for f in feats:
        contrib = f.slot_data(world)
        for k, v in contrib.items():
            if k in sd:
                raise ValueError(f"slot_data key '{k}' emitted by core and feature {f.name or type(f).__name__!r}")
            if k not in _contract.BY_NAME:
                # F2 fix: an UNDECLARED emission is exactly how a feature goes silently dark (the
                # client never reads a key the contract doesn't know). Fail at the merge, at gen.
                raise ValueError(
                    f"slot_data key '{k}' from feature {f.name or type(f).__name__!r} is not "
                    f"declared in contract.py -- add a ContractKey (name/shape/profile/producer) "
                    f"before emitting it")
            sd[k] = v
    return sd
