"""THE AP GAME NAME IS TYPED IN EXACTLY ONE PLACE (#1465).

Archipelago keys the data package, every player yaml, the wizard's emitted yaml, the poptracker
pack and the client's handshake on one string: `greenfield/eldenring/gamename.py`'s `GAME`. Before
this gate it was typed at ~20 Python sites, three Rust sites, the wizard's JSON blob and every
shipped/preset/tester yaml -- so a rename ships half-done by default. That is not a hypothetical:

  * the v0.1 -> v0.2 rename (`EldenRing` -> `Elden Ring`) left `er_yaml_lint.py` matching the OLD
    key, so all fifteen of its rules were no-ops on every yaml anyone played, for months;
  * the same rename left `release/EldenRing.yaml` saying `game: EldenRing`, so the flagship
    template in the release bundle could not generate -- a player's FIRST action failed;
  * and it left the wizard's `buildYaml` emitting the old spelling, so Copy/Download handed people
    a file naming a game Archipelago does not have and "Generate & host" 422'd on every click.

Three of the same bug, in three artifacts, from one rename. This suite is the gate that makes the
next rename a one-line change:

  1. `test_no_stray_literals_*` greps BOTH repos' source for the quoted literal and fails on any
     hit outside the allowlist below.
  2. `test_shipped_yamls_name_the_constant` runs `er_yaml_lint.check_game_name` over every yaml this
     repo ships. Yamls are DATA -- they are checked against the constant rather than generated from
     a template, so a hand-written playtest yaml still gets caught.
  3. `test_the_client_mirrors_the_constant` proves the generated Rust mirror carries the same
     string, and that the client reads the mirror instead of typing its own.

WHAT THE GREP MATCHES, and why that is the right rule. It matches the game name as a QUOTED STRING
LITERAL -- `"Elden Ring"` or `'Elden Ring'`, the exact value and nothing else. Prose is untouched
on purpose: docstrings, `//!` module docs, README and changelog headings say "Elden Ring" as English
and always will, and a gate that made those illegal would be turned off within a week. A longer
string that merely CONTAINS the name (`"Elden Ring Archipelago"`, the window title) is likewise not
the AP key and is not matched. The property this actually enforces is the one that matters: no
second copy of the value AP dispatches on.
"""
import os
import re
import sys
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:  # run as a script by the `generators` job
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = find_repo_root(_HERE)

sys.path.insert(0, os.path.dirname(_HERE))  # .../eldenring -- gamename.py imports nothing
from gamename import GAME, LEGACY_GAME_KEYS  # noqa: E402

CLIENT_DIRNAME = "from-software-archipelago-clients"

# The literal, as a quoted string, in any of the four source languages. `re.escape` keeps this
# honest if the name ever grows a regex metacharacter.
LITERAL = re.compile(r"""(?:"|')%s(?:"|')""" % re.escape(GAME))

# Extensions worth scanning: the languages that can HOLD the constant. Yaml is deliberately absent
# -- those are data, covered by test_shipped_yamls_name_the_constant instead.
SOURCE_EXT = (".py", ".rs", ".js", ".cjs", ".mjs", ".html", ".ps1", ".sh")

# Directories that are build output, vendored, or another tool's working area.
SKIP_DIRS = {".git", ".ap-test", "target", "node_modules", "elden_ring_artifacts", "evidence",
             "__pycache__", ".venv", "venv", "Archipelago", "_ap",
             # TESTS ARE OUT OF SCOPE, and not as a convenience. Archipelago's own WorldTestBase
             # identifies the world under test by a `game = "..."` CLASS ATTRIBUTE -- it is the
             # harness's parameter, not a copy of our constant, and ~100 suites set it. Making
             # those import the world's GAME would couple every test to the thing it is testing:
             # a suite that asserts "this world is registered as GAME" proves nothing if it asks
             # the world what its name is. They are also not shipped, so they cannot rot a
             # player-facing artifact -- which is the harm this gate is about.
             "tests"}

# Same rule for a test that lives outside a tests/ directory (tools/test_*.py, *.test.js).
TEST_FILE = re.compile(r"^test_|_test\.|\.test\.")

# Rust puts its tests INSIDE the production file, in a `#[cfg(test)] mod tests { .. }` block, so a
# by-filename rule cannot see them. Those blocks name games as FIXTURE DATA -- `const OURS: &str =
# "Elden Ring"` opposite a `"Geometry Dash"` sender in archipelago-rs, a shop label rendered "For:
# Alaric (Elden Ring)" in er-logic -- which is the same "it is the harness's parameter, not a copy
# of our constant" case as the Python suites, and pointing them at the apworld's const would make
# them assert against themselves. Cut the blocks out before scanning.
_CFG_TEST = re.compile(r"#\[cfg\(test\)\]")


def strip_rust_test_modules(text):
    out, pos = [], 0
    for m in _CFG_TEST.finditer(text):
        brace = text.find("{", m.end())
        if brace < 0:
            continue
        # Brace-match rather than "cut to EOF": a cfg(test) block is CONVENTIONALLY last, and a
        # convention is not a guarantee. Truncating at the marker would silently stop scanning the
        # real code below it -- a gate that quietly narrows its own input.
        depth, i = 0, brace
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        if i >= len(text):
            continue  # unbalanced: scan it whole rather than swallow the rest of the file
        out.append(text[pos:m.start()])
        # Keep the line count intact so reported line numbers still point at the real line.
        out.append("\n" * text.count("\n", m.start(), i + 1))
        pos = i + 1
    out.append(text[pos:])
    return "".join(out)

# ---------------------------------------------------------------------------------------------
# THE ALLOWLIST. Every entry is a repo-relative posix path, and every entry states WHY the literal
# is allowed to be there. Three kinds only -- if a fourth kind of entry ever seems necessary, that
# is the signal that the site should read the constant instead.
#
#   SOURCE    -- the one definition. Exactly one entry, by construction.
#   MIRROR    -- GENERATED from the source by a committed generator. A mirror is not a second
#                source: regenerate and it follows. Each entry names its generator, because a
#                "generated" file nobody regenerates is just a stale copy with a good excuse.
#   NARRATIVE -- a comment or docstring that QUOTES the string as evidence, in a passage about the
#                rename itself. Removing the quotes would destroy the point the passage is making
#                ("it said `EldenRing` while the world was `Elden Ring`" needs both spellings).
#                Deliberately short: this is the entry type that rots into a hiding place.
# ---------------------------------------------------------------------------------------------
ALLOW = {
    # -- SOURCE --------------------------------------------------------------------------------
    "greenfield/eldenring/gamename.py":
        "SOURCE. The one definition of the AP game name.",

    # -- MIRRORS (world) -----------------------------------------------------------------------
    "greenfield/eldenring/contract.json":
        "MIRROR of contract.py, generated by greenfield/gen_contract.py.",
    "wizard/options-metadata.json":
        "MIRROR of the option surface, generated by tools/dump_options_metadata.py (which imports "
        "GAME). The wizard's JS reads `meta.game` from this blob -- see wizard.html buildYaml.",
    "wizard/wizard.html":
        "MIRROR: the options-metadata blob is INJECTED into this page by tools/"
        "dump_options_metadata.py. The page's own JS reads `meta.game`; it types nothing.",

    # -- MIRRORS (client) ----------------------------------------------------------------------
    CLIENT_DIRNAME + "/crates/eldenring-archipelago/src/contract_gen.rs":
        "MIRROR of the world's contract, generated by greenfield/gen_contract.py "
        "(contract.to_rust). This is where the client's `GAME` const comes from.",

    # -- NARRATIVE -----------------------------------------------------------------------------
    "er_yaml_lint.py":
        "NARRATIVE: the comment recording that this linter matched the retired spelling through "
        "the rename, which is the defect #1465 exists to prevent recurring.",
}

# Client-side files whose literal is prose inside a longer string or a doc comment. They do not
# match LITERAL (it requires the quotes to hug the value), so they need no entry -- this note is
# here so a future reader does not add one "for completeness" and turn the allowlist into a list
# of every file that mentions the game.


def _iter_source(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if TEST_FILE.search(fn):
                continue
            if fn.endswith(SOURCE_EXT) or fn == "contract.json" or fn == "options-metadata.json":
                yield os.path.join(dirpath, fn)


def _hits(root, rel_prefix=""):
    """[(repo-relative posix path, lineno, line)] for every quoted-literal hit under `root`."""
    out = []
    for path in _iter_source(root):
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        if path.endswith(".rs"):
            text = strip_rust_test_modules(text)
        if not LITERAL.search(text):
            continue
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        if rel_prefix:
            rel = rel_prefix + "/" + rel
        for i, line in enumerate(text.splitlines(), 1):
            if LITERAL.search(line):
                out.append((rel, i, line.strip()))
    return out


def _fmt(hits):
    return "\n".join("  %s:%d  %s" % (p, n, l[:110]) for p, n, l in hits)


_FIX = (
    "\n\nEach hit must either read the constant --\n"
    "    from .gamename import GAME                                  # inside the world package\n"
    '    sys.path.insert(0, "<repo>/greenfield/eldenring"); from gamename import GAME  # outside\n'
    "    use crate::contract_gen::GAME;                              # client\n"
    "-- or be added to ALLOW in this file WITH the reason it is a SOURCE, a generated MIRROR, or "
    "NARRATIVE about the rename. Do not add an entry to make a red go away: a second copy of this "
    "string is the defect, and the three shipped bugs in this file's docstring are what it costs."
)


@unittest.skipIf(REPO is None, REPO_ONLY_REASON)
class TestNoStrayLiterals(unittest.TestCase):

    def test_the_source_is_where_we_say_it_is(self):
        """A grep gate whose allowlist has drifted off the tree passes vacuously. Prove the one
        SOURCE entry exists and actually holds the definition."""
        src = os.path.join(REPO, "greenfield", "eldenring", "gamename.py")
        self.assertTrue(os.path.isfile(src), "gamename.py is gone -- the single source with it")
        with open(src, encoding="utf-8") as f:
            self.assertIn('GAME = "%s"' % GAME, f.read(),
                          "gamename.py no longer defines GAME as a plain literal; this gate's "
                          "allowlist would be excusing a file that is not the source.")

    def test_the_gate_can_actually_see_a_stray(self):
        """The regex is the whole gate. A change to GAME (or to the pattern) that stopped it
        matching would turn every assertion below into a green no-op -- the exact failure mode
        er_yaml_lint's rule 0 suffered for months. So exercise it on both spellings, and on the
        prose form it must NOT flag."""
        self.assertTrue(LITERAL.search('game = "%s"' % GAME))
        self.assertTrue(LITERAL.search("game = '%s'" % GAME))
        self.assertIsNone(LITERAL.search('"%s Archipelago"' % GAME),
                          "a longer string that merely contains the name is not the AP key")
        self.assertIsNone(LITERAL.search("/// the %s client does X" % GAME),
                          "prose must stay legal or the gate gets switched off")

    def test_the_rust_test_stripper_keeps_the_real_code(self):
        """The stripper is the one place this gate can go BLIND: cut too much and the client's
        production code stops being scanned while the run stays green. Prove both halves -- the
        fixture inside the block is dropped, the literal after it is not."""
        src = ('fn real() { let a = "%s"; }\n'
               '#[cfg(test)]\nmod tests {\n    const OURS: &str = "%s";\n}\n'
               'fn also_real() { let b = "%s"; }\n' % (GAME, GAME, GAME))
        cut = strip_rust_test_modules(src)
        self.assertEqual(2, len(LITERAL.findall(cut)),
                         "the stripper must remove ONLY the cfg(test) block:\n" + cut)
        self.assertNotIn("OURS", cut)
        self.assertEqual(src.count("\n"), cut.count("\n"),
                         "line numbers in failure messages must still point at the real line")
        # Unbalanced braces must FAIL OPEN (scan everything) rather than swallow the rest.
        self.assertIn("also_real", strip_rust_test_modules("#[cfg(test)]\nmod t {\nfn also_real"))

    def test_no_stray_literals_in_the_world_repo(self):
        found = _hits(REPO)
        # WITNESS (test_gf_vacuous_pass): "no strays" is also what a walk that stopped walking
        # says. The allowlisted sites are the scan's own control group -- gamename.py and the
        # generated mirrors are KNOWN to hold the literal, so seeing them proves the walk reached
        # the tree, opened files and matched. Without this, a bad SKIP_DIRS entry or a moved
        # source directory turns this gate green and silent.
        self.assertTrue([h for h in found if h[0] in ALLOW],
                        "the scan found the literal NOWHERE, not even in gamename.py -- it is not "
                        "reading the tree, so its 'no strays' verdict means nothing.")
        strays = [h for h in found if h[0] not in ALLOW]
        self.assertEqual([], strays,
                         "the AP game name is typed outside gamename.py:\n" + _fmt(strays) + _FIX)

    def test_no_stray_literals_in_the_client_repo(self):
        client = os.path.join(REPO, CLIENT_DIRNAME)
        if not os.path.isdir(os.path.join(client, "crates")):
            self.skipTest("client checkout absent (the submodule dir is empty); the `generators` "
                          "CI job checks it out at the gitlink and runs this live")
        found = _hits(client, CLIENT_DIRNAME)
        # Same witness, same reason: contract_gen.rs is the control group. A client checkout that
        # landed an empty or wrong tree would otherwise read as a clean one.
        self.assertTrue([h for h in found if h[0] in ALLOW],
                        "the scan found the literal nowhere in the client, not even in the "
                        "generated contract_gen.rs -- the checkout is empty or the walk is broken, "
                        "and 'no strays' is measuring nothing.")
        strays = [h for h in found if h[0] not in ALLOW]
        self.assertEqual([], strays,
                         "the AP game name is typed in the client outside the generated mirror:\n"
                         + _fmt(strays) + _FIX)

    def test_the_allowlist_has_no_dead_entries(self):
        """An allowlist entry for a file that no longer holds the literal is an excuse waiting for
        a file to attach itself to. Every entry must still be needed."""
        dead, checked = [], 0
        for rel in ALLOW:
            path = os.path.join(REPO, rel.replace("/", os.sep))
            if not os.path.exists(path):
                if rel.startswith(CLIENT_DIRNAME + "/"):
                    continue  # client not checked out here; covered by the client test's skip
                dead.append(rel + " (missing)")
                continue
            checked += 1
            with open(path, encoding="utf-8", errors="replace") as f:
                if not LITERAL.search(f.read()):
                    dead.append(rel + " (no longer contains the literal)")
        # WITNESS: an empty `dead` is also what "the loop opened nothing" looks like.
        self.assertGreaterEqual(checked, 4,
                                "only %d ALLOW entry(s) were actually opened -- the rest resolved "
                                "to nothing, so this check has no opinion about them." % checked)
        self.assertEqual([], dead,
                         "stale ALLOW entries -- delete them:\n  " + "\n  ".join(dead))


@unittest.skipIf(REPO is None, REPO_ONLY_REASON)
class TestClientMirrorsTheConstant(unittest.TestCase):
    """The client's copy is GENERATED, and the client reads the generated copy."""

    def setUp(self):
        self.client = os.path.join(REPO, CLIENT_DIRNAME)
        if not os.path.isdir(os.path.join(self.client, "crates")):
            self.skipTest("client checkout absent; the `generators` CI job runs this at the gitlink")

    def test_the_generated_mirror_carries_the_name(self):
        gen = os.path.join(self.client, "crates", "eldenring-archipelago", "src", "contract_gen.rs")
        self.assertTrue(os.path.isfile(gen), "contract_gen.rs missing -- regenerate it with "
                                             "python greenfield/gen_contract.py")
        with open(gen, encoding="utf-8") as f:
            src = f.read()
        self.assertIn('pub const GAME: &str = "%s";' % GAME, src,
                      "the client's generated mirror does not carry the world's game name. Run "
                      "python greenfield/gen_contract.py and land the client half.")

    def test_the_client_reads_the_mirror(self):
        """core.rs must OBTAIN the name, not restate it. The grep gate above proves it types no
        literal; this proves it did not solve that by inventing a second const of its own."""
        core = os.path.join(self.client, "crates", "eldenring-archipelago", "src", "core.rs")
        with open(core, encoding="utf-8") as f:
            src = f.read()
        self.assertTrue(
            re.search(r"\bcontract_gen::GAME\b", src) or
            re.search(r"use\s+crate::contract_gen::\{[^}]*\bGAME\b", src),
            "core.rs does not reference contract_gen::GAME -- the handshake name must come from "
            "the generated mirror of the world's constant.")


# The yamls this repo SHIPS. Data, so they are CHECKED rather than generated: a hand-written
# playtest yaml is exactly the artifact a rename forgets, and it is also the one a tester runs.
SHIPPED_YAML_GLOBS = (
    ("release", "EldenRing.yaml"),
    ("presets", "*.yaml"),
    ("greenfield", "presets", "*.yaml"),
    ("testers", "*.yaml"),
    ("greenfield", "playtest-yamls", "*.yaml"),
    ("greenfield", "players", "*.yaml"),
)


@unittest.skipIf(REPO is None, REPO_ONLY_REASON)
class TestShippedYamls(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, REPO)
        try:
            import er_yaml_lint  # noqa: PLC0415
        except ImportError as e:  # PyYAML absent
            raise unittest.SkipTest("er_yaml_lint unavailable (%s)" % e)
        cls.lint = er_yaml_lint

    def _files(self):
        import glob  # noqa: PLC0415
        out = []
        for parts in SHIPPED_YAML_GLOBS:
            out += sorted(glob.glob(os.path.join(REPO, *parts)))
        return out

    def test_the_fleet_is_actually_found(self):
        """Zero files is a green run that checked nothing -- the vacuous pass this whole suite
        exists to prevent. Pin a floor well under the real count so a moved directory is loud."""
        files = self._files()
        self.assertGreaterEqual(len(files), 15,
                                "only %d shipped yaml(s) found under %r -- a directory moved and "
                                "this gate stopped gating." % (len(files), SHIPPED_YAML_GLOBS))

    def test_shipped_yamls_name_the_constant(self):
        bad, checked = [], 0
        files = self._files()
        # WITNESS: zero findings over zero files is the same green as a clean fleet. The floor is
        # asserted here as well as in test_the_fleet_is_actually_found, because this ratchet is
        # per-test -- a sibling's assertion does not keep THIS one honest.
        self.assertGreaterEqual(len(files), 15,
                                "only %d shipped yaml(s) to check -- a directory moved and this "
                                "gate is checking nothing." % len(files))
        for path in files:
            checked += 1
            for f in self.lint.check_game_name(path):
                bad.append("%s: %s" % (os.path.relpath(path, REPO).replace(os.sep, "/"), f.msg))
        self.assertEqual(len(files), checked)
        self.assertEqual([], bad,
                         "shipped yamls disagree with gamename.GAME = %r:\n  %s"
                         % (GAME, "\n  ".join(bad)))

    def test_the_yaml_gate_can_see_a_bad_file(self):
        """Same reason as the regex self-test: a checker that silently accepts everything is
        indistinguishable from a clean fleet. Feed it the exact defect that shipped in v0.2 --
        the retired spelling -- and require both findings."""
        import tempfile  # noqa: PLC0415
        stale = LEGACY_GAME_KEYS[0]
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "stale.yaml")
            with open(p, "w", encoding="utf-8") as f:
                f.write("name: Tester\ngame: %s\n%s:\n  num_regions: 6\n" % (stale, stale))
            msgs = " ".join(f.msg for f in self.lint.check_game_name(p))
        self.assertIn("game:", msgs)
        self.assertIn(stale, msgs)


if __name__ == "__main__":
    unittest.main()
