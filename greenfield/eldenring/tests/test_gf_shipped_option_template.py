"""Every live wizard option must be discoverable in the shipped player template.

The wizard metadata is the committed, AP-free projection of ``GFOptions`` and its option groups.
Using it as the live-surface oracle deliberately excludes frozen options: those remain named in
``core._OPTION_GROUPS`` so they return to the right tab when unfrozen, but players cannot set them.

This gate was added after 14 live grouped options were found missing from ``release/EldenRing.yaml``.
The omissions were filled before the gate landed, so this test starts from a clean baseline instead
of preserving an allow-list that would teach the next omission to pass.
"""
import json
import os
import sys
import unittest

import yaml

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = find_repo_root(HERE)


@unittest.skipUnless(REPO, REPO_ONLY_REASON)
class TestShippedOptionTemplate(unittest.TestCase):

    def test_every_live_grouped_option_is_in_the_shipped_template(self):
        with open(os.path.join(REPO, "wizard", "options-metadata.json"), encoding="utf-8") as fh:
            metadata = json.load(fh)
        with open(os.path.join(REPO, "release", "EldenRing.yaml"), encoding="utf-8") as fh:
            template = yaml.safe_load(fh)["Elden Ring"]

        live = set(metadata["field_order"])
        grouped = {key for group in metadata["groups"] for key in group["options"]}
        self.assertTrue(live, "wizard metadata has no live options; coverage would be vacuous")
        self.assertEqual(live, grouped,
                         "wizard metadata must partition the live surface before it can serve as "
                         "the shipped-template coverage oracle")

        missing = sorted(live - set(template))
        self.assertFalse(
            missing,
            "live grouped option(s) absent from release/EldenRing.yaml: %s. A player editing the "
            "shipped template cannot discover these settings; add each key with its default and "
            "player-facing explanation." % ", ".join(missing))


if __name__ == "__main__":
    unittest.main()
