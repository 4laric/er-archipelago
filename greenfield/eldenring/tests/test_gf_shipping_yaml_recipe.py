"""The shipped yaml's `curated_filler` must equal the code's default -- or it silently pins an old one.

THE BUG THIS EXISTS FOR, and it shipped. `release-v0.2/EldenRing.yaml` carried a literal recipe of
`juice: 44 / stones: 27`. The default in `features/filler_curation.py` had moved to `juice: 42 /
stones: 29` -- a MEASURED change: at stones 27, three of nine seeds fell under the 24-stone +3
affordability floor, and 29 "clears with a point of margin, which is what ships".

An explicit yaml value OVERRIDES the default. So every player generating from the shipped template
was getting the economy that had just been measured broken, while the code, the tests and the wizard
metadata all agreed on the fixed one. Nothing compared the two, because they are the same numbers in
two files and that is exactly the kind of duplication nobody thinks needs a test.

WHY NOT JUST DELETE THE BLOCK. It was deleted, briefly. But the recipe is the single most useful
thing a player can edit, and a template that does not show it hides the game's main dial. So it is
shown AND pinned: this gate is what makes showing it safe.

WHAT IT DOES NOT ASSERT: that the numbers are GOOD. Retuning is expected -- change the default,
re-run this, update the yaml. It only asserts the two copies agree.
"""
import os
import sys
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
_FOUND = find_repo_root(HERE)
REPO = _FOUND or os.path.dirname(os.path.dirname(HERE))
GF = os.path.join(REPO, "greenfield") if _FOUND else os.path.dirname(os.path.dirname(HERE))
YAML = os.path.join(REPO, "release-v0.2", "EldenRing.yaml")


@unittest.skipUnless(_FOUND is not None, REPO_ONLY_REASON)
class ShippingYamlRecipe(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            import yaml  # noqa: PLC0415
        except ImportError:
            raise unittest.SkipTest("PyYAML absent; the shipping-yaml gates need it")
        if not os.path.isfile(YAML):
            raise unittest.SkipTest("release-v0.2/EldenRing.yaml not present")
        with open(YAML, encoding="utf-8") as fh:
            doc = yaml.safe_load(fh)
        # 🛑 ASSERT the game key, do not fall back to the whole document. `doc.get("Elden Ring", doc)`
        # looks defensive and is the opposite: rename or typo that key and every lookup below returns
        # None, `curated_filler` is absent, and the equality test DISARMS ITSELF into a skip -- a
        # green run that checked nothing. The fallback has to be an error, because the thing it would
        # be tolerating (no Elden Ring section in the Elden Ring template) is never acceptable.
        assert "Elden Ring" in doc, (
            "release-v0.2/EldenRing.yaml has no 'Elden Ring' section -- either the game key was "
            "renamed or the template is malformed. Refusing to fall back to the whole document, "
            "because that turns every assertion below into a vacuous pass.")
        cls.opts = doc["Elden Ring"]

        # Read the default WITHOUT importing: filler_curation uses package-relative imports and
        # needs the AP env, and this gate is a two-numbers-in-two-files check that should not depend
        # on either. `ast` gets the literal exactly, and cannot execute anything.
        import ast
        path = os.path.join(GF, "eldenring", "features", "filler_curation.py")
        tree = ast.parse(open(path, encoding="utf-8").read())
        found = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "CuratedFiller":
                for stmt in node.body:
                    if (isinstance(stmt, ast.Assign) and stmt.targets
                            and getattr(stmt.targets[0], "id", None) == "default"):
                        found = ast.literal_eval(stmt.value)
        if found is None:
            raise AssertionError(
                "could not read CuratedFiller.default out of %s -- the gate cannot compare against "
                "a default it cannot find, and a skipped comparison is how the yaml drifted in the "
                "first place." % path)
        cls.default = dict(found)

    def test_the_yaml_recipe_equals_the_code_default(self):
        shipped = self.opts.get("curated_filler")
        if shipped is None:
            self.skipTest("the template does not pin a recipe, so it follows the default -- also fine")
        self.assertEqual(
            dict(shipped), self.default,
            "release-v0.2/EldenRing.yaml pins a curated_filler recipe that is NOT the code's default. "
            "An explicit yaml value OVERRIDES the default, so every player generating from this "
            "template gets the pinned one -- which is how the stones-27 economy kept shipping after "
            "it was measured below the +3 affordability floor and fixed. Update the yaml block to "
            "match filler_curation.CuratedFiller.default, or delete it to follow the default.")

    def test_the_economy_weights_are_present_and_non_zero(self):
        """A recipe that ships with no upgrade economy is a different bug with the same shape."""
        shipped = self.opts.get("curated_filler") or self.default
        for cat in ("juice", "stones", "somber_stones", "runes"):
            self.assertIn(cat, shipped, "the shipped recipe has no %r weight" % cat)
            self.assertGreater(int(shipped[cat]), 0,
                               "the shipped recipe zeroes %r; that is a real setting but not a "
                               "shippable default" % cat)

    def test_no_retired_pool_builder_option_is_named(self):
        """A retired option in the template would RAISE for every player who generates from it."""
        retired = ("pool_builder", "pool_builder_scope", "pool_builder_juice_cap",
                   "pool_builder_juice_pct")
        named = [k for k in retired if k in self.opts]
        self.assertFalse(
            named, "the shipped template names retired option(s) %s. They are Options.Removed stubs, "
                   "so Archipelago raises 'Option removed, please update your options file' -- the "
                   "template itself would fail to generate." % named)


if __name__ == "__main__":
    unittest.main()
