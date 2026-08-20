#!/usr/bin/env python3
"""Exercise the wizard's YAML importer against the YAML that the wizard emits.

The importer deliberately accepts only complete wizard output.  This gate runs the shipped
JavaScript under the same small DOM shim as check_wizard_renders.py and pins both halves of that
contract: a real download round-trips, while partial, weighted, duplicate, and invalid option
values are refused before they can enter wizard state.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIZARD_HTML = os.path.join(ROOT, "wizard", "wizard.html")
SHIM = os.path.join(ROOT, "tools", "wizard_dom_shim.js")


HARNESS = r"""
const fs = require("fs");
const { El, makeDocument } = require(process.argv[2]);
const html = fs.readFileSync(process.argv[3], "utf8");
const head = html.split('<script id="wizard-core">')[0];
const staticIds = [...new Set([...head.matchAll(/\bid="([\w-]+)"/g)].map(m => m[1]))];
const doc = makeDocument(staticIds);

for (const id of ["er-options-metadata", "er-region-census", "er-pool-composition"]){
  const m = html.match(new RegExp('<script id="' + id + '" type="application/json">\\r?\\n([\\s\\S]*?)</script>'));
  const node = doc.getElementById(id);
  if (!m || !node) throw new Error("harness could not load #" + id);
  node.textContent = m[1];
}

let scripts = [...html.matchAll(/<script(?![^>]*type="application\/json")[^>]*>([\s\S]*?)<\/script>/g)]
  .map(m => m[1]);
scripts = scripts.map(src => {
  const i = src.lastIndexOf("})();");
  if (i < 0 || !src.includes("function parseWizardYaml(")) return src;
  return src.slice(0, i) +
    "\n globalThis.__yamlProbe = { meta, state, buildYaml: ERW.buildYaml, parseWizardYaml };\n" +
    src.slice(i);
});

const sandbox = {
  document: doc, window: { scrollTo(){} },
  navigator: { clipboard: { writeText: async () => {} } },
  location: { protocol: "https:", origin: "https://example.invalid", pathname: "/er/wizard.html" },
  URL, Option: function(t, v){ const e = new El("option"); e.textContent = t; e.value = v; return e; },
  console, JSON, Math, Object, Array, Set, Map, Number, String, Boolean, Date, RegExp, Error,
  isNaN, parseInt, parseFloat, encodeURIComponent, decodeURIComponent,
  Blob: function(){}, fetch: () => {}, setTimeout, clearTimeout, module: {},
};
const vm = require("vm");
const ctx = vm.createContext(sandbox);
for (const src of scripts) vm.runInContext(src, ctx, { timeout: 20000 });

const P = sandbox.__yamlProbe;
if (!P || !P.meta || !P.state || !P.buildYaml || !P.parseWizardYaml){
  throw new Error("the importer probe was not exported from the page IIFE");
}

P.state.name = 'A"#x';
const valid = P.buildYaml(P.meta, P.state);
const parsed = P.parseWizardYaml(valid, P.meta);
const expectedKeys = P.meta.field_order.concat(P.meta.apCore.map(o => o.key)).filter(k => P.meta.byKey[k]);

function optionLine(yaml, key){
  const re = new RegExp("^  " + key.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\$&") + ":.*$", "m");
  const hit = yaml.match(re);
  if (!hit) throw new Error("fixture could not find option line " + key);
  return hit[0];
}
function replaceOption(yaml, key, replacement){
  return yaml.replace(optionLine(yaml, key), replacement);
}

const rejected = {};
function mustReject(label, yaml){
  try {
    P.parseWizardYaml(yaml, P.meta);
    rejected[label] = null;
  } catch (e){
    rejected[label] = String(e && e.message ? e.message : e);
  }
}

mustReject("partial", [
  'name: "partial"', 'description: "not wizard output"', 'game: Elden Ring',
  'Elden Ring:', '  num_regions: 6', ''
].join("\n"));
const nr = optionLine(valid, "num_regions");
mustReject("duplicate", valid.replace(nr, nr + "\n" + nr));
mustReject("weighted_range", replaceOption(valid, "num_regions", "  num_regions:\n    zero: 1"));
mustReject("quoted_toggle", replaceOption(valid, "enable_dlc", '  enable_dlc: "false"'));
mustReject("unknown_choice", replaceOption(valid, "ending_condition", "  ending_condition: banana"));
mustReject("range_out_of_bounds", replaceOption(valid, "num_regions", "  num_regions: 9999"));
mustReject("unknown_set_member", replaceOption(valid, "progression_surface", "  progression_surface: [__nope__]"));
mustReject("unknown_dict_key", valid.replace("  curated_filler:", "  curated_filler:\n    __nope__: 1"));
const negativeDictWeight = valid.replace(
  /(  curated_filler:[^\r\n]*\r?\n)    ([^:\r\n]+):[^\r\n]*/,
  "$1    $2: -1"
);
if (negativeDictWeight === valid){
  throw new Error("fixture could not find the first curated_filler weight");
}
mustReject("negative_dict_weight", negativeDictWeight);

console.log(JSON.stringify({
  validName: parsed.name,
  parsedKeys: Object.keys(parsed.values).length,
  expectedKeys: expectedKeys.length,
  rejected,
}));
"""


def main():
    node = shutil.which("node")
    if not node:
        print("[SKIP] node not on PATH -- the wizard YAML importer is NOT gated on this box.")
        return 4

    tmp = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                         encoding="utf-8", newline="\n") as fh:
            fh.write(HARNESS)
            tmp = fh.name
        proc = subprocess.run([node, tmp, SHIM, WIZARD_HTML], capture_output=True, text=True)
    finally:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)

    if proc.returncode:
        print("[FAIL] the wizard YAML importer threw under the DOM shim:")
        print((proc.stderr or proc.stdout)[-4000:])
        return 1

    data = json.loads(proc.stdout)
    problems = []
    if data.get("validName") != 'A"#x':
        problems.append("the wizard could not round-trip an escaped quote followed by # in name")
    if data.get("parsedKeys") != data.get("expectedKeys") or not data.get("parsedKeys"):
        problems.append("the complete wizard YAML did not round-trip every emitted option")
    for label, message in (data.get("rejected") or {}).items():
        if not message:
            problems.append("%s input was accepted" % label)

    if problems:
        print("[FAIL] wizard YAML import contract:")
        for problem in problems:
            print("   ", problem)
        return 1
    print("[ok] complete wizard YAML round-trips %d options and all %d invalid shapes are refused"
          % (data["parsedKeys"], len(data["rejected"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
