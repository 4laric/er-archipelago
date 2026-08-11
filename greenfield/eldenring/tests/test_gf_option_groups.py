"""Every player-visible option is filed under a wizard tab. AP-free, so this can gate anywhere.

`core.GFWeb.option_groups` is the ONE grouping of the option surface: Archipelago's player-options
page renders it directly, and `tools/dump_options_metadata.py` projects it into
`wizard/options-metadata.json` as `groups` + `ungrouped`, where the wizard turns each non-collapsed
group into a step of its own.

MOTIVATING CASE (CONTRIBUTING rule 11). `option_groups` was never defined, so the dumper emitted
`"groups": []` and put all 54 keys in `ungrouped` -- and `ungrouped` renders as a single
"Other Options (54)" accordion inside the wizard's Advanced step, under a banner reading
"Everything here is safe to skip -- the defaults are fine." Enemy scaling, the pool builder, the
progression surface and the multiworld knobs were all behind that sentence. Nothing was broken and
no gate had anything to say: the page rendered, the yaml it wrote was correct, and the option was
reachable if you opened the one summary that told you not to. The grouping machinery in the page had
been there the whole time with nothing feeding it.

WHAT THIS TEST IS FOR, THEN: an option added tomorrow and not added to `core._OPTION_GROUPS` lands
in exactly that bucket -- the same failure, one option at a time, and just as quiet. This says so
out loud.

🛑 WHAT IT DOES NOT COVER. It reads the COMMITTED metadata, so it proves the artifact is fully
filed, not that the artifact is current. A grouping edit that was never regenerated passes here and
fails `dump_options_metadata.py --check` (the `tests` job), which is the gate that imports the live
world. The two are not substitutes for one another -- same split as test_gf_wizard_blob_sync.
"""

import json
import os
import sys
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:  # run as a script (the `generators` CI job does exactly this)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = find_repo_root(HERE)

FIX = ("fix: add the key to core._OPTION_GROUPS, then re-run "
       "python tools/dump_options_metadata.py")


@unittest.skipUnless(REPO, REPO_ONLY_REASON)
class TestOptionGroups(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(REPO, "wizard", "options-metadata.json"),
                  "r", encoding="utf-8", newline="") as f:
            cls.meta = json.load(f)
        cls.groups = cls.meta["groups"]
        cls.order = cls.meta["field_order"]

    def test_every_option_is_in_exactly_one_group(self):
        """No visible key may be ungrouped, and none may be claimed twice."""
        # WITNESSES first (test_gf_vacuous_pass's ratchet, and the reason for it). Everything below
        # asserts that some collection is EMPTY, and all three of those assertions pass just as
        # happily against metadata carrying no groups and no options at all -- which is precisely
        # the state this file exists to forbid.
        self.assertTrue(self.order, "field_order is empty -- the metadata describes no options, so "
                                    "every emptiness check below is vacuous. %s" % FIX)
        self.assertTrue(self.groups, "the metadata defines no option groups at all. That was the "
                                     "original defect: `\"groups\": []` put the entire surface in "
                                     "one Advanced accordion. %s" % FIX)

        seen, twice = set(), []
        for g in self.groups:
            for k in g["options"]:
                if k in seen:
                    twice.append(k)
                seen.add(k)

        self.assertFalse(
            twice, "option(s) in more than one group: %s. Archipelago's WebWorldRegister asserts "
                   "against this at import, so a duplicate here means the metadata was generated "
                   "from a different grouping than the world now defines. %s"
                   % (", ".join(sorted(set(twice))), FIX))

        ungrouped = [k for k in self.order if k not in seen]
        self.assertFalse(
            ungrouped, "option(s) in no group: %s.\nAn ungrouped option does not disappear -- it "
                       "lands in the wizard's Advanced step, inside one accordion, under a banner "
                       "telling the player everything there is safe to skip. That is where the "
                       "WHOLE surface used to live. %s" % (", ".join(ungrouped), FIX))

        # And the reported bucket agrees with what we just derived. `ungrouped` is what the page
        # actually reads; deriving the answer and then not checking the field would let the two
        # disagree.
        self.assertEqual([], self.meta["ungrouped"],
                         "metadata `ungrouped` is non-empty while every key is grouped -- the two "
                         "halves of the same emit disagree. %s" % FIX)

    def test_no_key_is_invented_or_lost_by_the_grouping(self):
        """The grouping is a PARTITION of field_order -- it may not add or drop keys."""
        grouped = sorted(k for g in self.groups for k in g["options"])
        self.assertEqual(sorted(self.order), grouped,
                         "the grouped keys are not the same set as field_order. Grouping is "
                         "presentation only: field_order is what the wizard writes into the yaml "
                         "and what presets are ordered by, so these two must stay the same set. %s"
                         % FIX)

    def test_groups_are_named_once_and_never_empty(self):
        names = [g["name"] for g in self.groups]
        self.assertEqual(sorted(names), sorted(set(names)),
                         "duplicate group name(s): %s -- the wizard would render two tabs with the "
                         "same caption." % ", ".join(sorted(n for n in names if names.count(n) > 1)))
        for g in self.groups:
            self.assertTrue(g["options"],
                            "group %r has no options. Archipelago asserts a custom group is "
                            "non-empty, and the wizard would draw a bare '(0)' tab." % g["name"])

    def test_the_surface_is_not_all_behind_advanced(self):
        """At least one group is OPEN -- i.e. the wizard has real steps, not just Advanced.

        This is the original defect stated directly. A grouping where every group is
        `start_collapsed` reproduces it exactly: every group renders inside Advanced, and the
        player is told the whole thing is skippable.
        """
        open_groups = [g for g in self.groups if not g["collapsed"]]
        self.assertTrue(
            open_groups,
            "every option group is collapsed, so the wizard has no option steps at all and the "
            "entire surface renders inside 'Advanced & experimental'. %s" % FIX)
        covered = sum(len(g["options"]) for g in open_groups)
        self.assertGreater(
            covered, len(self.order) // 2,
            "only %d of %d options sit in an open group; the majority of the surface is behind "
            "Advanced. %s" % (covered, len(self.order), FIX))


if __name__ == "__main__":
    unittest.main()
