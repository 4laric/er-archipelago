"""Typed questline-model gate: game-derived flags plus revision-pinned CC-wiki evidence.

The original DAG remains the machine oracle and intentionally contains flags only. This suite
guards the wider evidence model, especially the id-space boundary introduced by item prerequisites.
It is AP-free and runs from the generators job.
"""
import csv
import importlib.util
import os
import sys
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = find_repo_root(HERE)
RUNNING_FROM_REPO = REPO is not None
REPO = REPO or os.path.dirname(os.path.dirname(HERE))
GF = os.path.join(REPO, "greenfield")
TOOL = os.path.join(REPO, "tools", "build_questline_model.py")
TABLE = os.path.join(GF, "questline_model.tsv")


def _load_tool():
    spec = importlib.util.spec_from_file_location("_build_questline_model", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _rows(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(
            (line for line in fh if not line.lstrip().startswith("#")), delimiter="\t"))


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class QuestlineModelGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = _load_tool()
        cls.rows = _rows(TABLE)
        cls.cc = [row for row in cls.rows if row["evidence_kind"] == "cc_wiki"]

    def test_committed_model_is_fresh_and_deterministic(self):
        first = self.tool.render()
        self.assertEqual(first, self.tool.render())
        with open(TABLE, encoding="utf-8", newline="") as fh:
            self.assertEqual(fh.read(), first,
                             "questline_model.tsv is stale; run tools/build_questline_model.py")

    def test_cc_rows_are_revision_pinned_and_share_alike(self):
        self.assertGreaterEqual(len(self.cc), 10, "CC evidence layer unexpectedly shrank")
        for row in self.cc:
            self.assertEqual(row["license"], "CC-BY-SA-4.0")
            self.assertIn("eldenring.wiki.gg/", row["source_url"])
            self.assertIn("oldid=" + row["source_revision"], row["source_url"])
            self.assertTrue(row["source_page_id"].isdigit())
            self.assertTrue(row["source_timestamp"].endswith("Z"))
            self.assertTrue(row["id_evidence"], "numeric ids need independent game-data provenance")
            self.assertNotIn("fextra", " ".join(row.values()).lower())

    def test_item_prerequisite_cannot_masquerade_as_an_event_flag(self):
        rows = [r for r in self.cc if r["source_node"] == "item:Hole-Laden Necklace"]
        self.assertEqual({r["target_node"] for r in rows},
                         {"flag:2053467600", "flag:2050407000"})
        self.assertEqual({r["source_game_ref"] for r in rows}, {"goods:2008008"})
        self.assertFalse(any(r["source_node"] == "flag:2008008" for r in self.rows),
                         "goods id 2008008 was laundered into the event-flag namespace")

    def test_validator_rejects_wrong_id_space_and_unpinned_attribution(self):
        """Break both new guards directly; a green output fixture alone cannot prove they fire."""
        rows, world = self.tool.build()
        wrong_space = [dict(row) for row in rows]
        item = next(row for row in wrong_space
                    if row["source_node"] == "item:Hole-Laden Necklace")
        item["source_node"] = "flag:2008008"
        with self.assertRaises(SystemExit):
            self.tool.validate(wrong_space, world)

        unpinned = [dict(row) for row in rows]
        wiki = next(row for row in unpinned if row["evidence_kind"] == "cc_wiki")
        wiki["source_url"] = "https://eldenring.wiki.gg/wiki/" + wiki["source_page"]
        with self.assertRaises(SystemExit):
            self.tool.validate(unpinned, world)

    def test_fortissax_arena_hole_is_now_visible_but_not_laundered_into_the_machine_dag(self):
        cc_pair = [r for r in self.cc
                   if r["source_node"] == "flag:400392" and r["target_node"] == "flag:510110"]
        self.assertEqual(len(cc_pair), 1)
        self.assertEqual(cc_pair[0]["relation"], "requires")
        machine = [r for r in self.rows
                   if r["target_node"] == "flag:510110" and r["evidence_kind"] == "game_data"]
        self.assertEqual(machine, [], "the award-site corpus still cannot prove arena existence; "
                                     "do not relabel CC evidence as game-derived")

    def test_metyr_requires_both_bell_states_in_one_all_group(self):
        rows = [r for r in self.cc if r["target_node"] == "flag:510550"]
        self.assertEqual({r["source_node"] for r in rows},
                         {"flag:2053460600", "flag:2050400600"})
        self.assertEqual({r["group_id"] for r in rows}, {"ccwiki:ymir:metyr"})
        self.assertEqual({r["group_semantics"] for r in rows}, {"all"})
        self.assertEqual({r["relation"] for r in rows}, {"requires"})

    def test_wiki_can_corroborate_without_replacing_game_evidence(self):
        witnesses = {(r["source_node"], r["target_node"], r["relation"])
                     for r in self.rows if r["evidence_kind"] == "game_data"}
        overlap = [r for r in self.cc
                   if (r["source_node"], r["target_node"], r["relation"]) in witnesses]
        self.assertTrue(any(r["quest"] == "Patches" for r in overlap),
                        "the CC layer no longer independently corroborates the Patches exclusion")

    def test_world_behavior_does_not_import_the_evidence_model(self):
        package = os.path.join(GF, "eldenring")
        offenders = []
        scanned = 0
        for root, dirs, files in os.walk(package):
            dirs[:] = [d for d in dirs if d not in {"tests", "__pycache__"}]
            for name in files:
                if not name.endswith(".py"):
                    continue
                scanned += 1
                path = os.path.join(root, name)
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
                if "questline_model" in text:
                    offenders.append(os.path.relpath(path, REPO))
        self.assertGreater(scanned, 50, "runtime-consumer scan went blind")
        self.assertEqual(offenders, [], "evidence-only model acquired a world consumer: %s"
                         % offenders)


if __name__ == "__main__":
    unittest.main()
