# Greenfield features

Each SPEC-PARITY phase (scaling, boss locks, shops, grace rando, ...) is **one file in this
directory**. Dropping a file here is the whole integration -- no other file changes, so phases can
be built in parallel without colliding.

A feature self-registers and overrides only the hooks it needs (see `../registry.py`):

```python
from BaseClasses import ItemClassification
from Options import Range
from ..registry import Feature, register        # NEVER import ..core (circular)

class ScalingFloor(Range):
    """docstring == the option description (required)."""
    display_name = "Completion Scaling Floor"; range_start = 0; range_end = 50; default = 0

@register
class Scaling(Feature):
    name = "scaling"
    OPTIONS = {"completion_scaling_floor": ScalingFloor}   # merged into GFOptions
    ITEMS   = {}                                           # {name: ItemClassification}; core allocates ids
    def generate_early(self, world): ...
    def create_items(self, world):   return []             # extra pool items
    def create_regions(self, world): ...
    def set_rules(self, world):      ...                   # extra access/completion rules
    def slot_data(self, world):      return {"completion_scaling_floor": ...}
```

Rules: (1) import `..registry` / `Options` / `..data` / `..region_spine`, never `..core`.
(2) Option field names, item names, and slot_data keys must be globally unique -- core raises on a
collision. (3) `self.gf_kept` (the kept-region list) is set before any feature hook runs; read it
for region-scoped logic. (4) Add a `tests/test_gf_<phase>.py`. Validate with `bash greenfield/ci-linux.sh`.
