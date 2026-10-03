"""The player reference must describe real live groups, never an invented payout."""
import json
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import tempfile
import unittest

from tools.build_sweep_reference import build_payload, constants, render
from tools.gen_manifest import BUILDER_INPUTS

ROOT = Path(__file__).resolve().parents[1]


class SweepReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = build_payload(ROOT)
        cls.sweeps = constants(ROOT / "greenfield/eldenring/tables/boss_sweeps.py")
        cls.contract = runpy.run_path(str(ROOT / "greenfield/eldenring/contract.py"))

    def test_complete_live_groups_and_members_match_authoritative_tables(self):
        actual = {group["flag"]: group for group in self.payload["groups"]}
        expected = set(self.sweeps["DUNGEON_SWEEPS"]) - set(self.contract["runtime_sweep_skips"]())
        self.assertEqual(set(actual), expected)
        for flag, group in actual.items():
            self.assertEqual(group["checks"], sorted(set(self.sweeps["DUNGEON_SWEEPS"][flag])))
            for ap in group["checks"]:
                self.assertIn(str(ap), self.payload["checks"])
            self.assertNotIn("none", group["rungs"])

    def test_capital_sewer_and_dragon_groups_remain_distinct(self):
        groups = {group["boss"]: group for group in self.payload["groups"]}
        capital = groups["Morgott, the Omen King"]
        sewer = groups["Mohg, the Omen"]
        self.assertEqual((capital["region"], sewer["region"]), ("Leyndell", "Leyndell"))
        self.assertEqual(capital["map"], "m11_00")
        self.assertEqual(sewer["map"], "m35_00")
        self.assertFalse(set(capital["checks"]) & set(sewer["checks"]))
        loretta = groups["Royal Knight Loretta"]
        smarag = groups["Glintstone Dragon Smarag"]
        self.assertFalse(set(loretta["checks"]) & set(smarag["checks"]))
        self.assertTrue(sewer["checks"])
        self.assertTrue(loretta["checks"])

    def test_setting_filter_uses_contract_classes(self):
        for group in self.payload["groups"]:
            for rung, kinds in self.contract["SWEEP_RUNGS"].items():
                expected = group["kind"] in kinds or (group["kind"] == "unknown" and rung == "bosses")
                self.assertEqual(rung in group["rungs"], expected)

    def test_missing_member_or_input_refuses_instead_of_omitting_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            for relative in BUILDER_INPUTS["sweep_reference"]:
                destination = repo / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, destination)
            sweep_path = repo / "greenfield/eldenring/tables/boss_sweeps.py"
            sweep = constants(sweep_path)
            sweep["DUNGEON_SWEEPS"][11000800].append(-1)
            sweep_path.write_text("\n".join(f"{key} = {value!r}" for key, value in sweep.items()),
                                  encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing checks"):
                build_payload(repo)
            sweep_path.unlink()
            with self.assertRaisesRegex(ValueError, "Missing sweep reference inputs"):
                build_payload(repo)

    def test_windows_and_ci_template_newlines_produce_the_same_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            for relative in BUILDER_INPUTS["sweep_reference"]:
                destination = repo / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, destination)
            template = repo / "tools/sweep_reference_template.html"
            template.write_bytes(template.read_bytes().replace(b"\r\n", b"\n"))
            before = render(repo, build_payload(repo))
            template.write_bytes(template.read_bytes().replace(b"\n", b"\r\n"))
            self.assertEqual(before, render(repo, build_payload(repo)))

    def test_offline_payload_is_deterministic_and_script_safe(self):
        first = render(ROOT, self.payload)
        self.assertEqual(first, render(ROOT, build_payload(ROOT)))
        injected = json.loads(json.dumps(self.payload))
        next(iter(injected["checks"].values()))["name"] = '</script><script>alert("x")</script>'
        html = render(ROOT, injected)
        embedded = re.search(r'<script id="sweep-payload" type="application/json">(.*?)</script>',
                             html, re.S).group(1)
        self.assertNotIn("</script>", embedded)
        self.assertEqual(json.loads(embedded), injected)
        self.assertIn("candidate", html)
        self.assertIn("F6 tracker is authoritative", html)

    @unittest.skipUnless(shutil.which("node"), "Node is required for page interaction checks")
    def test_actual_page_script_search_filter_and_link_behaviour(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "sweeps.html"
            page.write_text(render(ROOT, self.payload), encoding="utf-8")
            result = subprocess.run([shutil.which("node"),
                                     str(ROOT / "tools/check_sweep_reference_ui.js"), str(page)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
