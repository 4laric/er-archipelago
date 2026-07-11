#!/usr/bin/env python3
"""Generate the external integration spec to hand to a third-party apworld author (e.g. Bedrock):
what the runtime client reads from slot_data, so they can tailor their .apworld to it. Provider-
neutral (no greenfield internals). Emits greenfield/handoff/CLIENT_SLOTDATA_CONTRACT.md and copies
contract.json + contract_gen.rs alongside as the machine-readable schema + reference validator.
Run: python greenfield/gen_handoff.py   (after gen_contract.py)
"""
import os, sys, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "eldenring"))
import contract  # noqa: E402

EXAMPLE = {
    "SCALAR_INT_MAP":  '{"7770029": 60290}',
    "LISTVAL_INT_MAP": '{"Limgrave Lock": [73000, 73003, 73005]}',
    "TRIPLE_LIST":     '[[61000, 61000, 73100], [10000, 10000, 200]]',
    "INT_LIST":        '[24000000, 1073741954]',
    "BOOL":            'true',
    "BOOL_OR_INT":     'true   (or 1)',
    "STR":             '"Limgrave"',
    "NESTED_GRANTS":   '{"Flask of Crimson Tears": [{"goods": 1073742018, "flags": []}]}',
    "ANY":             '(client-defined; see the reference validator)',
}

def shape_json(name):
    forms = {
        "SCALAR_INT_MAP":  "object, string key -> **integer** value (NOT a list)",
        "LISTVAL_INT_MAP": "object, string key -> **array of integers**",
        "TRIPLE_LIST":     "array of `[int, int, int]` triples",
        "INT_LIST":        "array of integers",
        "BOOL":            "boolean",
        "BOOL_OR_INT":     "boolean, or integer 0/1 (tolerant)",
        "STR":             "string",
        "NESTED_GRANTS":   "object, name -> array of `{\"goods\": int, \"flags\": [int]}`",
        "ANY":             "client-specific (opaque here)",
    }
    return forms[name]

def main():
    L = []
    A = L.append
    A("# Elden Ring Archipelago — client `slot_data` contract")
    A("")
    A("**What this is.** The runtime client (`eldenring-archipelago`) drives the game entirely from the")
    A("`slot_data` an apworld returns from `fill_slot_data()`. This document is the exact set of keys the")
    A("client reads, their JSON shapes, whether they're required, and what each does. If your `.apworld`")
    A("emits these keys with these shapes, this client will detect location checks, grant received items,")
    A("gate/warp regions, light graces, reveal maps, run shops, and send Goal — no client changes needed.")
    A("")
    A("It is **auto-generated from the client's own contract definition** (`contract.py` / `contract_gen.rs`),")
    A("so it always matches what the client actually validates. Two companion files ship with this spec:")
    A("")
    A("- `contract.json` — the same contract, machine-readable (validate your slot_data against it in CI).")
    A("- `contract_gen.rs` — the client's actual validator (`fn validate(sd) -> Vec<String>`); the client")
    A("  runs it on connect and logs any mismatch as `contract: SHAPE '<key>' expected <Shape>`.")
    A("")
    A("## Conventions")
    A("")
    A("- **FullID** (item id space): `category_nibble | param_id`. `WEAPON = 0x00000000`, `PROTECTOR/armor")
    A("  = 0x10000000`, `ACCESSORY/talisman = 0x20000000`, `GOODS = 0x40000000`, `GEM/ash = 0x80000000`.")
    A("  e.g. Torch (weapon 24000000) = `24000000`; Spectral Steed Whistle (goods 130) = `1073741954`.")
    A("- **Event flags** are ER game event flags (group-allocated; invented ids no-op). Map/grace/region")
    A("  flags are the real vanilla flags.")
    A("- **Detection model** is `own_world`: on a check pickup the client suppresses the vanilla item,")
    A("  reports the location, and grants back whatever the multiworld placed there via `apIdsToItemIds`.")
    A("")
    A("## Shapes")
    A("")
    A("| shape | JSON form | client parser | example |")
    A("|-------|-----------|---------------|---------|")
    for n in contract.SHAPES:
        if n == "ANY":
            continue
        A(f"| `{n}` | {shape_json(n)} | `{contract.SHAPES[n][2]}` | `{EXAMPLE[n]}` |")
    A("")
    A("> The single most common integration bug is emitting a `SCALAR_INT_MAP` key (e.g. `locationFlags`)")
    A("> with **list** values `{\"id\": [flag]}` instead of scalar `{\"id\": flag}`. The client parses it to")
    A("> empty and silently detects nothing. The validator catches exactly this.")
    A("")
    # group keys by profile
    def rows(pred):
        out = []
        for k in contract.CONTRACT:
            if not pred(k):
                continue
            prof = "both" if contract.BOTH in k.profiles else "+".join(k.profiles)
            req = "**required**" if k.required else "optional"
            out.append(f"| `{k.name}` | `{k.shape}` | {req} | {prof} | {k.consumer} | {k.doc} |")
        return out
    HDR = ("| key | shape | | profile | client reads in | meaning |\n"
           "|-----|-------|-----|---------|-----------------|---------|")
    A("## Core keys (read by the client in every profile)")
    A("")
    A(HDR)
    for r in rows(lambda k: contract.BOTH in k.profiles):
        A(r)
    A("")
    A("## Alternate / profile-specific keys")
    A("")
    A("The client supports two ways to wire **location detection**: emit event flags directly")
    A("(`locationFlags`, the greenfield path) **or** emit matt-style location keys (`locationIdsToKeys`,")
    A("the bedrock path — the client resolves `token1` -> flag). Provide one. Keys below are read by the")
    A("client but are specific to one profile:")
    A("")
    A(HDR)
    for r in rows(lambda k: contract.BOTH not in k.profiles):
        A(r)
    A("")
    A("## Minimal viable slot_data")
    A("")
    A("A region-lock seed needs at least: `apIdsToItemIds`, `locationFlags` (or the key path),")
    A("`regionOpenFlags`, `areaLockFlags`, `startRegion`, `goalLocations`. Everything else is optional and")
    A("enables a feature (graces, map reveal, shops, sweeps, deathlink, progressives).")
    A("")
    A("```jsonc")
    A("{")
    A('  "apIdsToItemIds":  {"7770001": 1073750026},         // AP item id -> ER FullID granted on receipt')
    A('  "locationFlags":   {"7770001": 60290},              // AP location id -> its ER acquisition flag')
    A('  "regionOpenFlags": {"Caelid Lock": 73202},          // lock item -> region-open flag set on receipt')
    A('  "areaLockFlags":   [[62000, 62002, 73202]],         // [lo,hi,open_flag] play_region ranges, kicked while unset')
    A('  "startRegion":     "Limgrave",')
    A('  "goalLocations":   [7770875, 7770876, 7770885]      // all-done => client sends Goal')
    A("}")
    A("```")
    A("")
    A("## Questions")
    A("")
    A("The contract lives in one file on the client side; if you need a key the client doesn't yet read,")
    A("or a shape adjusted, that's a one-line change plus a regen of these three artifacts. Happy to add")
    A("`bedrock`-profile keys to the shared contract so both apworlds validate against the same source.")
    return "\n".join(L) + "\n"

out_dir = os.path.join(HERE, "handoff")
os.makedirs(out_dir, exist_ok=True)
with open(os.path.join(out_dir, "CLIENT_SLOTDATA_CONTRACT.md"), "w", encoding="utf-8", newline="\n") as f:
    f.write(main())
for fn, src in [("contract.json", os.path.join(HERE, "eldenring", "contract.json")),
                ("contract_gen.rs", os.path.join(REPO, "from-software-archipelago-clients",
                                                 "crates", "eldenring-archipelago", "src", "contract_gen.rs"))]:
    if os.path.isfile(src):
        shutil.copyfile(src, os.path.join(out_dir, fn))
print("wrote", os.path.relpath(out_dir, REPO), "->", os.listdir(out_dir))
