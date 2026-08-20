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



class TestAutoUpgradeUnfreeze(unittest.TestCase):
    """2026-08-20: auto_upgrade unfroze (frozen at 1 since v0.2). While frozen, the class default
    was unreachable and had rotted to Toggle's 0 -- so the unfreeze moved the default to the
    frozen value in the same commit, and this pin keeps a default seed's behaviour identical to
    every seed since the freeze (the PoolBuilderIntensity lesson, one option over)."""

    def test_the_default_is_the_ex_frozen_value(self):
        import importlib.util as ilu
        spec = ilu.spec_from_file_location(
            "_upg", os.path.join(REPO, "greenfield", "eldenring", "features", "upgrades.py"))
        # AP-free: read the class body textually rather than import a module that wants Options.
        with open(os.path.join(REPO, "greenfield", "eldenring", "features", "upgrades.py"),
                  encoding="utf-8") as f:
            src = f.read()
        body = src.split("class AutoUpgrade", 1)[1].split("class ", 1)[0]
        self.assertIn("default = 1", body,
                      "AutoUpgrade.default is not 1 -- a yaml that does not name auto_upgrade "
                      "would silently turn OFF behaviour every seed has had since v0.2")
        with open(os.path.join(REPO, "greenfield", "eldenring", "defaults.py"),
                  encoding="utf-8") as f:
            self.assertNotIn('"auto_upgrade": (', f.read(),
                             "auto_upgrade is frozen AND defaulted -- pick one")


class TestEssentialsTier(unittest.TestCase):
    """The essentials tier (core._ESSENTIAL_OPTIONS -> metadata `essential`) stays honest.

    2026-08-20, the "too many options" follow-up to the five-step rail: each section renders its
    essential options expanded and the rest behind a More fold. These assertions keep the tier
    from decaying the way ungrouped options used to: a section with no essentials renders as a
    single closed fold, which is the pre-#554 accordion one group at a time."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(REPO, "wizard", "options-metadata.json"),
                  "r", encoding="utf-8", newline="") as f:
            cls.meta = json.load(f)
        cls.ess = {o["key"] for o in cls.meta["options"] if o.get("essential")}

    def test_the_tier_exists_and_is_a_tier(self):
        # WITNESS both directions: no essentials = the fold hides everything; all essentials = the
        # fold is scenery. Either way the tier stopped meaning anything.
        total = len(self.meta["options"])
        self.assertTrue(self.ess, "no option is marked essential -- the wizard renders every "
                                  "section as one closed More fold")
        self.assertLess(len(self.ess), total * 0.5,
                        "%d of %d options are 'essential' -- the tier no longer distinguishes "
                        "anything; demote some or delete the concept" % (len(self.ess), total))

    # A group RULED to have no essentials renders every row directly under its own section fold
    # (the page skips the inner More when nothing is promoted) -- one fold, not two. Any OTHER
    # bare group is an accident and fails below.
    RULED_BARE_GROUPS = {
        # Alaric 2026-08-20: keep_out_of_shops was a bobler request, usage unknown; nothing in
        # the section is a first-session decision.
        "Shops & Merchants",
    }

    def test_every_open_group_keeps_at_least_one_essential(self):
        # WITNESSES: an empty groups list or an empty tier makes `bare == []` true for free.
        self.assertTrue(self.meta["groups"], "no groups -- this assertion is over nothing")
        self.assertTrue(self.ess, "no essentials -- this assertion is over nothing")
        bare = {g["name"] for g in self.meta["groups"]
                if not g.get("collapsed") and not any(k in self.ess for k in g["options"])}
        self.assertEqual(bare - self.RULED_BARE_GROUPS, set(),
                         "open group(s) with NO essential option and no ruling: %r -- promote a "
                         "key in core._ESSENTIAL_OPTIONS, or record the ruling in "
                         "RULED_BARE_GROUPS with who made it." % sorted(bare - self.RULED_BARE_GROUPS))
        self.assertEqual(self.RULED_BARE_GROUPS - bare, set(),
                         "stale RULED_BARE_GROUPS entr(ies): %r now carry an essential -- drop "
                         "them so the waiver does not outlive its subject."
                         % sorted(self.RULED_BARE_GROUPS - bare))

    def test_every_essential_is_grouped_and_visible(self):
        grouped = {k for g in self.meta["groups"] for k in g["options"]}
        # WITNESSES: both sides must be nonempty for the disjointness below to mean anything.
        self.assertTrue(grouped, "no grouped keys -- the subtraction below is vacuous")
        self.assertTrue(self.ess, "no essentials -- the subtraction below is vacuous")
        stray = sorted(self.ess - grouped)
        self.assertEqual(stray, [], "essential option(s) outside every group: %r -- core.py "
                                    "validates this at import, so the metadata is stale; rerun "
                                    "tools/dump_options_metadata.py" % stray)

if __name__ == "__main__":
    unittest.main()
