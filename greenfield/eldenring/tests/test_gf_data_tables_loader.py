"""The layering gate for the generated data tables (#1464).

Three properties, none of which any other test asserts:

  1. `core.py` imports NO generated data module by name. It calls `table_loader.load()` once and
     reads the returned `Tables`. This is the property the one-apworld design needs: our tables are
     a module that can be present or absent at build time, so the World may not be wired to them by
     import.
  2. The id bases live in the table definition (`table_loader`), not beside the orchestration code,
     and still carry the FROZEN values the shipped seeds and the client contract are keyed on.
  3. A tree with no `tables/` package refuses to register with a message NAMING the missing
     tables -- not an ImportError from the middle of `core.py`.

SCOPE, stated plainly: the gate covers `core.py` only. `features/*.py` still import generated
modules directly (`from ..tables.X import Y`); moving 40-odd features onto `world.tables` is a
second cut, and doing it inside the layering change would have buried it. The allowlist below is
that debt, written down and counted -- a NEW feature import shows up as a count change.

Run:  python -m pytest greenfield/eldenring/tests/test_gf_data_tables_loader.py
"""
import ast
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)
CORE_PY = os.path.join(GF_PKG, "core.py")
FEATURES_DIR = os.path.join(GF_PKG, "features")


def _load_by_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_LOADER = _load_by_path("_gf_table_loader_under_test", os.path.join(GF_PKG, "table_loader.py"))
GENERATED = set(_LOADER.GENERATED_MODULES)

# Features that still import a generated table directly (the documented debt above). A file may
# only be REMOVED from this list, never added: an entry here is a feature that would break if the
# tables package were absent.
FEATURE_ALLOWLIST = frozenset({
    "area_locks.py", "armor_bundles.py", "boss_locks.py", "capital.py", "check_item_flags.py",
    "check_lots.py", "enemy_drops.py", "evidence_progression_hosts.py", "filler_budget.py",
    "filler_curation.py", "filler_foreign.py", "finale.py", "goal_locations.py", "graces.py",
    "keep_out_of_shops.py", "legacy_key_gates.py", "leyndell_gate.py", "local_items.py",
    "lot_stacks.py", "mine_materials.py", "missable_locations.py", "natural_progression.py",
    "no_runes_in_shops.py", "pool_builder.py", "pool_compaction.py", "presence_floor.py",
    "progression_surface.py", "progressive.py", "quest_prerequisite_rules.py", "rune_pricing.py",
    "scadu_supply.py", "scaling.py", "shop_stock.py", "shops.py", "start_grace.py",
    "start_items.py", "traps.py", "vanilla_placement.py",
})


def _imported_table_modules(path):
    """Every generated table module imported BY NAME in `path`, from its AST (so a mention in a
    comment or a docstring is not a hit and a nested/function-level import is)."""
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)
    hits = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            tail = mod.rsplit(".", 1)[-1]
            if tail in GENERATED and ("tables" in mod.split(".") or mod == tail):
                hits.add(tail)
            if mod.endswith("tables") or mod == "tables":
                for alias in node.names:
                    if alias.name in GENERATED:
                        hits.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                tail = alias.name.rsplit(".", 1)[-1]
                if tail in GENERATED:
                    hits.add(tail)
    return hits


class CoreImportsNoDataModule(unittest.TestCase):
    def test_core_imports_no_generated_table(self):
        # WITNESS (test_gf_vacuous_pass ratchet): "core.py imports none" is only a claim if the
        # scanner can still SEE an import. Point it at a file that definitely has one first -- if
        # the AST walk or GENERATED went stale, this fails here instead of passing an empty core.
        self.assertTrue(GENERATED, "GENERATED_MODULES is empty -- the scan matches nothing")
        witness = _imported_table_modules(os.path.join(FEATURES_DIR, "traps.py"))
        self.assertTrue(witness, "the scanner no longer sees features/traps.py's table imports, "
                                 "so a clean core.py below would prove nothing")
        hits = sorted(_imported_table_modules(CORE_PY))
        self.assertEqual(hits, [], "core.py imports generated data modules directly: %s. "
                                   "Read them off table_loader.load() / world.tables instead "
                                   "(#1464)." % hits)

    def test_core_calls_the_loader(self):
        with open(CORE_PY, encoding="utf-8") as fh:
            src = fh.read()
        self.assertRegex(src, r"table_loader\.load\(",
                         "core.py no longer calls table_loader.load() -- the World would have no "
                         "tables, or would be importing them by name again")

    def test_feature_debt_is_exactly_the_allowlist(self):
        """Every feature that still imports a table by name is on the allowlist, and every entry on
        the allowlist still does -- so the list cannot rot in either direction."""
        actual = set()
        for fn in sorted(os.listdir(FEATURES_DIR)):
            if fn.endswith(".py") and _imported_table_modules(os.path.join(FEATURES_DIR, fn)):
                actual.add(fn)
        # WITNESS (test_gf_vacuous_pass ratchet): an `actual` that collapsed to nothing -- a moved
        # features dir, a scanner that stopped matching -- would satisfy "no unlisted feature"
        # vacuously, and would then blame the allowlist in the second assertion rather than itself.
        self.assertTrue(actual, "the scan found NO feature importing a table; features/ is at %s"
                                % FEATURES_DIR)
        self.assertEqual(sorted(actual - FEATURE_ALLOWLIST), [],
                         "new feature importing a generated table directly -- use world.tables")
        self.assertEqual(sorted(FEATURE_ALLOWLIST - actual), [],
                         "allowlist entry no longer imports a table: delete it from the list")


class IdBasesLiveInTheTableDefinition(unittest.TestCase):
    def test_bases_are_the_frozen_values(self):
        self.assertEqual(_LOADER.LOCATION_ID_BASE, 7770000)
        self.assertEqual(_LOADER.LOCK_ITEM_ID_BASE, 7780000)
        self.assertEqual(_LOADER.REAL_ITEM_ID_BASE, 7790000)
        self.assertEqual(_LOADER.ABILITY_UNLOCK_ITEM_BASE, 7900000)

    def test_contract_agrees_on_the_ability_unlock_base(self):
        contract = _load_by_path("_gf_contract_base_check", os.path.join(GF_PKG, "contract.py"))
        self.assertEqual(contract.ABILITY_UNLOCK_ITEM_BASE, _LOADER.ABILITY_UNLOCK_ITEM_BASE)

    def test_core_does_not_spell_the_bases_itself(self):
        """The numbers moved; a literal creeping back into core.py is how they end up in two places
        and drift."""
        with open(CORE_PY, encoding="utf-8") as fh:
            body = "\n".join(ln.split("#")[0] for ln in fh.read().split("\n"))
        for base in ("7770000", "7780000", "7790000"):
            self.assertNotIn(base, body,
                             "id base %s is spelled in core.py -- it belongs to table_loader" % base)


class MissingTablesRefusesToRegister(unittest.TestCase):
    def test_load_names_the_missing_tables(self):
        """A fresh copy of the loader whose importer finds nothing -- the deleted-package state.

        The message must NAME the tables: the whole point of #1464's acceptance criterion is that a
        tables-less build says what is missing instead of raising ImportError from the middle of
        core.py."""
        loader = _load_by_path("_gf_loader_no_tables", os.path.join(GF_PKG, "table_loader.py"))
        loader._import = lambda name: None
        loader._CACHE.clear()
        with self.assertRaises(loader.MissingTablesError) as caught:
            loader.load()
        msg = str(caught.exception)
        self.assertIn("tables.data", msg, "the message must name the missing table")
        self.assertIn("gen_data.py", msg, "the message must say how to get the tables back")
        self.assertTrue(issubclass(loader.MissingTablesError, ImportError))

    def test_unknown_mode_is_refused(self):
        loader = _load_by_path("_gf_loader_mode", os.path.join(GF_PKG, "table_loader.py"))
        with self.assertRaises(loader.MissingTablesError):
            loader.load(mode="not-a-mode")

    def test_loaded_tables_carry_the_real_data(self):
        tables = _LOADER.load()
        self.assertTrue(tables.regions, "REGIONS empty -- the loader is not reading tables/data.py")
        self.assertIn(tables.hub, tables.locations)
        self.assertEqual(tables.mode, _LOADER.DEFAULT_MODE)
        self.assertIs(tables.module("data"), _LOADER.load().modules["data"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
