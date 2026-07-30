"""The two committed wizard artifacts must agree WITH EACH OTHER. AP-free, so this can gate anywhere.

The options wizard surface is stored THREE times: `wizard/options-metadata.json`, the byte-identical
blob inlined into `wizard/wizard.html` inside `<script id="er-options-metadata">`, and the option
keys used by `presets/*.yaml`. All three come out of `tools/dump_options_metadata.py`.

MOTIVATING CASE (CONTRIBUTING rule 11). Until 2026-07-29 that tool's `--inject` and `--presets`
writes were OPT-IN FLAGS, so the obvious command wrote one of the three artifacts and left the other
two behind. Four commits (3381174..9ce2476, 2026-07-28/29) regenerated the JSON without
re-injecting, and the wizard page quietly lost three whole options -- `dungeon_sweep`,
`pool_builder_intensity`, `region_grace_unlock`, 6197 bytes -- while every gate stayed green. It
stayed green because the ONE instrument that would have caught it, the WIZARD step in `run_ci.ps1`,
had been commented out since 2026-07-04 "until the surface stabilizes". Nothing released was
affected: `wizard/` is not staged into the release zip. The tool's default now emits all three.

🛑 WHAT THIS TEST DOES NOT COVER, AND CANNOT. It proves the committed artifacts are consistent with
each other. It CANNOT prove either one matches the live option docstrings -- both could be equally
stale and this would still pass, because comparing two files to each other says nothing about the
world. That is `dump_options_metadata.py --check`'s job, which imports the real `GFOptions` through
a pinned Archipelago and therefore needs Python >= 3.11 and an AP checkout. It runs in the `tests`
CI job and in `run_ci.ps1`. This file is the cheap half that also runs where AP is absent, and the
two are not substitutes for one another.
"""

import json
import os
import re
import sys
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:  # run as a script (`python greenfield/eldenring/tests/test_gf_wizard_blob_sync.py`)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = find_repo_root(HERE)

# The exact pattern tools/dump_options_metadata.py:inject() substitutes on. Kept character-for-
# character identical on purpose: if the injector's tag ever changes, this must fail rather than
# quietly match nothing and report "in sync".
BLOB_RE = re.compile(
    r'<script id="er-options-metadata" type="application/json">\n(.*?)</script>', re.S)

FIX = "fix: python tools/dump_options_metadata.py"


def _read(*parts):
    with open(os.path.join(REPO, *parts), "r", encoding="utf-8", newline="") as f:
        return f.read().replace("\r\n", "\n")


@unittest.skipUnless(REPO, REPO_ONLY_REASON)
class TestWizardBlobSync(unittest.TestCase):

    def test_inlined_blob_equals_the_json_file(self):
        """wizard.html's inlined blob is byte-identical to wizard/options-metadata.json."""
        raw_json = _read("wizard", "options-metadata.json")
        html = _read("wizard", "wizard.html")

        m = BLOB_RE.search(html)
        self.assertIsNotNone(
            m, "wizard/wizard.html has no <script id=\"er-options-metadata\"> block for the injector "
               "to write into. Either the page was restructured or the tag was renamed -- in both "
               "cases dump_options_metadata.py --inject would exit 1 too. %s" % FIX)
        blob = m.group(1)

        if blob == raw_json:
            return

        # Say WHAT is missing, not just "they differ" -- an absence is invisible unless named
        # (CONTRIBUTING rule 6). This diagnostic is the whole value of the test: the 2026-07-28
        # drift was three named options, and "6197 bytes differ" would not have found them.
        def keys_and_hash(text, label):
            try:
                d = json.loads(text)
            except ValueError as exc:
                self.fail("%s is not valid JSON (%s). %s" % (label, exc, FIX))
            return ([o["key"] for o in d.get("options", [])], d.get("source_sha256", "?"))

        blob_keys, blob_sha = keys_and_hash(blob, "the blob inlined in wizard.html")
        file_keys, file_sha = keys_and_hash(raw_json, "wizard/options-metadata.json")

        missing = [k for k in file_keys if k not in blob_keys]
        extra = [k for k in blob_keys if k not in file_keys]

        detail = []
        if missing:
            detail.append("options in the JSON but MISSING from the page: %s" % ", ".join(missing))
        if extra:
            detail.append("options on the page but gone from the JSON: %s" % ", ".join(extra))
        if blob_sha != file_sha:
            detail.append("source_sha256 page=%s json=%s" % (blob_sha[:12], file_sha[:12]))
        if not detail:
            detail.append("same %d option keys, so the difference is in descriptions, defaults or "
                          "formatting (%d bytes vs %d)" % (len(file_keys), len(blob), len(raw_json)))

        self.fail(
            "wizard/wizard.html's inlined metadata does not match wizard/options-metadata.json.\n"
            "  %s\n"
            "The page is what a player actually fills in, so it is the copy that matters. %s"
            % ("\n  ".join(detail), FIX))

    def test_every_preset_option_key_still_exists(self):
        """No presets/*.yaml may set an option the metadata no longer defines."""
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML not installed; the generators CI job installs it for this gate")

        meta = json.loads(_read("wizard", "options-metadata.json"))
        known = {o["key"] for o in meta["options"]}
        self.assertTrue(known, "options-metadata.json defines no options at all")

        presets_dir = os.path.join(REPO, "presets")
        names = sorted(n for n in os.listdir(presets_dir) if n.endswith(".yaml"))
        self.assertTrue(names, "presets/ has no .yaml files -- they are generated output, so an "
                               "empty directory means the emit silently stopped. %s" % FIX)

        bad = {}
        for name in names:
            with open(os.path.join(presets_dir, name), "r", encoding="utf-8") as f:
                doc = yaml.safe_load(f) or {}
            section = doc.get(meta["game"]) or {}
            unknown = sorted(k for k in section if k not in known)
            if unknown:
                bad[name] = unknown

        self.assertFalse(
            bad, "preset(s) set option keys that options-metadata.json does not define: %s.\n"
                 "A preset naming a retired option makes Archipelago refuse the yaml outright, so "
                 "this is a broken download, not a cosmetic drift. %s"
                 % ("; ".join("%s -> %s" % (k, ", ".join(v)) for k, v in sorted(bad.items())), FIX))


if __name__ == "__main__":
    unittest.main()
