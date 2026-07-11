"""Tier-B CROSS-SIDE contract gate: every slot_data PATH the CLIENT reads has a gen-side PRODUCER.

The existing contract test (`test_gf_contract.py`) validates an assembled slot_data dict against
`contract.py` -- it proves the emitted dict MATCHES the declarations. But it inherits contract.py's
blind spots: if the client reads a path that contract.py never declares, a feature is silently DARK
("slot_data OK" while the client's `.get(...)`/`.pointer(...)` returns None and falls back to a
default). That is exactly the gf-contract-options-subdict-gap bug class:

    client:   sd.pointer("/options/auto_upgrade")        # reads a nested path
    gen:      contract validated only the top-level key NAMES

so `auto_upgrade` (and death_link / enable_dlc / no_weapon_requirements / the scaling knobs) were
emitted TOP-LEVEL, the client read them under `/options/...`, and every one was inert while gen
reported a clean contract.

This gate is INDEPENDENT of contract.py's shape checks. It re-derives the truth from the OTHER side:
it parses the CLIENT Rust source for every slot_data read-path and asserts each one is DECLARED by
contract.py (as a top-level ContractKey, or -- for `/options/<sub>` -- an OPTIONS_SUBKEYS entry, or
via the option-parser helpers `parse_bool_option`/`parse_dlc`/`parse_death_link`). A client read with
no declaration is an orphan == a dark feature waiting to happen -> FAIL, listing the orphan paths and
their source locations. It would have caught the options-subdict gap before the subdict landed.

Note on PROFILES: some declared keys are tagged `bedrock` (the swap-target keys the client reads with
`.unwrap_or` defaults but greenfield does not emit -- fogWalls, itemCounts, randomStart*, ...). Those
are DECLARED, so they are not orphans; the gate reports them separately as "declared, greenfield-inert"
so a real orphan is never hidden among them.

Extraction (see `_extract_client_paths`): from each real `*.rs` under the two client crates' `src/`
(EXCLUDING `*.bak*` snapshots and the generated `contract_gen.rs` mirror), after stripping comments
and `#[cfg(test)]` modules, capture receiver-anchored reads on the slot_data root only --
`sd|slot_data . get|pointer ("...")` and `sd|slot_data ["..."]` -- plus the option-helper calls
`parse_bool_option(sd, "KEY")`, `parse_dlc(..)`, `parse_death_link(..)`. Anchoring on the `sd`/
`slot_data` receiver is what keeps nested reads on sub-objects (e.g. a shop entry's `.get("goods")`,
a fog-wall's `.get("x")`, a JSON *file's* `v.get("location_flags")`) out of the set -- they are not
slot_data reads.

Run:  python -m pytest greenfield/eldenring/tests/test_gf_client_contract_paths.py
  or: python greenfield/eldenring/tests/test_gf_client_contract_paths.py   (unittest fallback)
"""
import importlib.util
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)                    # .../greenfield/eldenring
GREENFIELD = os.path.dirname(GF_PKG)              # .../greenfield
REPO_ROOT = os.path.dirname(GREENFIELD)           # repo root
CONTRACT_PY = os.path.join(GF_PKG, "contract.py")
CRATES = os.path.join(REPO_ROOT, "from-software-archipelago-clients", "crates")
CLIENT_SRC_DIRS = [
    os.path.join(CRATES, "eldenring-archipelago", "src"),
    os.path.join(CRATES, "er-logic", "src"),
]

# Generated mirror of contract.py (its only slot_data reads are the validator loop that re-implements
# contract.py itself -- not feature reads). Excluded; noted in the module docstring.
EXCLUDE_FILES = {"contract_gen.rs"}

# ALLOW: client read-paths that are legitimately WITHOUT a contract.py declaration yet known-safe.
# EMPTY today -- contract.py already declares every path the client reads (bedrock swap-target keys
# included, under the bedrock profile). Add an entry ONLY with a one-line justification, e.g. a
# diagnostic-only key never meant to ship. Format: top-level key name, or "/options/<sub>".
ALLOW = set()

_SLOT = r"(?:sd|slot_data)"
_RE_GETPTR = re.compile(_SLOT + r"\s*\.\s*(?:get|pointer)\s*\(\s*\"([^\"]+)\"")
_RE_INDEX = re.compile(_SLOT + r"\s*\[\s*\"([^\"]+)\"\s*\]")
_RE_BOOLOPT = re.compile(r"parse_bool_option\s*\(\s*" + _SLOT + r"\s*,\s*\"([^\"]+)\"")
# named option wrappers -> their fixed options sub-key (defined in er-logic/options.rs)
_NAMED_WRAPPERS = {"parse_dlc": "enable_dlc", "parse_death_link": "death_link"}
_RE_NAMED = re.compile(r"\b(parse_dlc|parse_death_link)\s*\(")


def _load_contract():
    spec = importlib.util.spec_from_file_location("gf_contract_pathaudit", CONTRACT_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _strip(text):
    """Remove block comments, line comments, and #[cfg(test)] modules (conventionally file-tail).

    Cutting from the first `#[cfg(test)]` to EOF drops unit-test fixtures whose `json!({...})` and
    replay harnesses would otherwise inject phantom keys (e.g. options.rs' `parse_bool_option(&json!
    (..), "x")`). Production slot_data reads always precede the test module, so nothing real is lost.
    """
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)   # block comments
    text = re.sub(r"//[^\n]*", " ", text)                     # line comments
    cut = text.find("#[cfg(test)]")
    if cut != -1:
        text = text[:cut]
    return text


def _norm(path):
    """Normalize a captured argument to ('top', key) or ('opt', subkey)."""
    if path.startswith("/options/"):
        return ("opt", path[len("/options/"):].split("/", 1)[0])
    if path.startswith("/"):
        seg = path.strip("/").split("/", 1)[0]
        return ("top", seg)
    return ("top", path)


def _extract_client_paths(sources):
    """sources: {label: rust_text} -> (top_paths, opt_paths) each = {name: sorted[label]}.

    top_paths -> top-level slot_data keys the client reads.
    opt_paths -> `options.<sub>` sub-keys the client reads (pointers + option-parser helpers).
    """
    top, opt = {}, {}

    def add(bucket, name, label):
        bucket.setdefault(name, set()).add(label)

    for label, raw in sources.items():
        text = _strip(raw)
        for m in _RE_GETPTR.finditer(text):
            kind, name = _norm(m.group(1))
            add(top if kind == "top" else opt, name, label)
        for m in _RE_INDEX.finditer(text):
            kind, name = _norm(m.group(1))
            add(top if kind == "top" else opt, name, label)
        for m in _RE_BOOLOPT.finditer(text):
            add(opt, m.group(1), label)
        for m in _RE_NAMED.finditer(text):
            add(opt, _NAMED_WRAPPERS[m.group(1)], label)
    top = {k: sorted(v) for k, v in top.items()}
    opt = {k: sorted(v) for k, v in opt.items()}
    return top, opt


def _audit(top_paths, opt_paths, top_names, opt_names):
    """Return list of orphan strings (client path with no contract.py declaration)."""
    orphans = []
    for k, labels in sorted(top_paths.items()):
        if k not in top_names and k not in ALLOW:
            orphans.append("top-level slot_data['%s']  <- %s" % (k, ", ".join(labels)))
    for k, labels in sorted(opt_paths.items()):
        if k not in opt_names and ("/options/%s" % k) not in ALLOW:
            orphans.append("options['%s']  <- %s" % (k, ", ".join(labels)))
    return orphans


def _read_client_sources():
    sources = {}
    for d in CLIENT_SRC_DIRS:
        if not os.path.isdir(d):
            continue
        crate = os.path.basename(os.path.dirname(d))
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".rs"):
                continue
            if fn in EXCLUDE_FILES or ".bak" in fn:
                continue
            with open(os.path.join(d, fn), encoding="utf-8", errors="replace") as f:
                sources["%s/%s" % (crate, fn)] = f.read()
    return sources


class ClientContractPaths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(CONTRACT_PY):
            raise unittest.SkipTest("contract.py absent (installed-world copy / fresh clone).")
        if not any(os.path.isdir(d) for d in CLIENT_SRC_DIRS):
            raise unittest.SkipTest(
                "client crates absent (%s) -- this cross-side gate needs the in-repo client source."
                % CRATES
            )
        cls.c = _load_contract()
        cls.top_names = {k.name for k in cls.c.CONTRACT}
        cls.opt_names = {k.name for k in cls.c.OPTIONS_SUBKEYS}
        cls.gf_top = {k.name for k in cls.c.CONTRACT
                      if cls.c.GREENFIELD in k.profiles or cls.c.BOTH in k.profiles}
        cls.sources = _read_client_sources()
        cls.top_paths, cls.opt_paths = _extract_client_paths(cls.sources)

    def test_extractor_found_paths(self):
        # Guard against a silently-vacuous pass: if the regexes matched nothing, the gate is useless.
        # The client is known to read dozens of top-level keys and the full 8-key options sub-dict.
        self.assertGreaterEqual(len(self.top_paths), 20,
                                "extractor found too few top-level reads -- regex/anchor broke")
        self.assertGreaterEqual(len(self.opt_paths), 6,
                                "extractor found too few options reads -- regex/anchor broke")

    def test_every_client_path_has_a_producer(self):
        orphans = _audit(self.top_paths, self.opt_paths, self.top_names, self.opt_names)
        self.assertEqual(orphans, [], "\n\nCLIENT reads slot_data paths that contract.py does NOT "
                         "declare (dark-feature risk -- add a ContractKey, or an ALLOW entry with "
                         "justification):\n  " + "\n  ".join(orphans) + "\n")

    def test_report_greenfield_inert_paths(self):
        # Informational (never fails): top-level paths the client reads that are DECLARED but only
        # under the bedrock profile -- greenfield does not emit them, client reads inert defaults.
        inert = sorted(k for k in self.top_paths
                       if k in self.top_names and k not in self.gf_top)
        # These must still be declared (the assertion that matters lives in the test above); here we
        # only surface them so an orphan is never mistaken for an intentional swap-target key.
        for k in inert:
            self.assertIn(k, self.top_names)
        print("\n[client-contract-paths] declared-but-greenfield-inert (bedrock swap targets): %s"
              % (inert or "(none)"))

    def test_injection_catches_a_dark_path(self):
        # PROOF the gate bites: feed a synthetic client source that reads an undeclared path and a
        # phantom option, and confirm both are reported as orphans.
        fake = {
            "synthetic/scratch.rs": (
                'fn f(sd: &Value) {\n'
                '    let a = sd.get("totally_fake_dark_feature");\n'
                '    let b = sd.pointer("/options/phantom_knob");\n'
                '    let c = er_logic::options::parse_bool_option(sd, "phantom_bool_opt");\n'
                '}\n'
            )
        }
        top, opt = _extract_client_paths(fake)
        orphans = _audit(top, opt, self.top_names, self.opt_names)
        joined = "\n".join(orphans)
        self.assertIn("totally_fake_dark_feature", joined)
        self.assertIn("phantom_knob", joined)
        self.assertIn("phantom_bool_opt", joined)
        # ...and a real declared path in the same synthetic batch is NOT flagged.
        top2, opt2 = _extract_client_paths({"synthetic/ok.rs": 'sd.get("startRegion");'})
        self.assertEqual(_audit(top2, opt2, self.top_names, self.opt_names), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
