"""Greenfield Elden Ring apworld -- data-derived, matt-free (../LESSONS-LEARNED.md, SPEC-PARITY.md).

Modular: core.py owns region scope + hub/locks/goal + the client contract; each SPEC-PARITY phase is
one self-registered file in features/. This module just re-exports what Archipelago needs to find.
"""
from .core import (
    GreenfieldEldenRingWorld,
    GFOptions,
    GFItem,
    GFLocation,
    GFWeb,
    GAME,
    FILLER,
    item_name_to_id,
    location_name_to_id,
)

__all__ = [
    "GreenfieldEldenRingWorld", "GFOptions", "GFItem", "GFLocation", "GFWeb",
    "GAME", "FILLER", "item_name_to_id", "location_name_to_id",
]
