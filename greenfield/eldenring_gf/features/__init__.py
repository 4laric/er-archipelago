"""Feature phases. Each module here self-registers via @registry.register; importing this package
auto-imports every module so registration happens before core builds its aggregates. Drop a new
phase in as a single file -- no other file changes. Modules starting with '_' are skipped.
"""
import importlib
import pkgutil

for _finder, _name, _ispkg in pkgutil.iter_modules(__path__):
    if not _name.startswith("_"):
        importlib.import_module(f"{__name__}.{_name}")
