# SPEC: port `auto_upgrade` + `flatten_regular_upgrades` into greenfield

Status: scoped, not yet implemented. Author pass 2026-07-07.

## Verdict up front

This is a **gen-side-only** port. **Zero client change.** Both features are already
implemented and wired in the shared runtime client as game-generic edits on live
param/inventory memory; greenfield currently ships them as constant-`0` stubs. Turning
them on for greenfield is the exact `weapon_reqs.py` pattern: declare the option, echo the
real value, no `.rs` touched.

## Why it's zero client change (verified)

Both consumers read the value from the `options` sub-dict of slot_data and act on the live
game — they need no apworld-specific data (no item table, no location set, no flags):

- `auto_upgrade` — `crates/eldenring-archipelago/src/upgrades.rs`. `apply_auto_upgrade(full_id)`
  is called from `detour.rs grant_full_id` on every granted item. It decodes the weapon id,
  reads `EquipParamWeapon`/`ReinforceParamWeapon` for the track + cap, walks live inventory
  for the highest held level, and raises the granted weapon (raise-only). Connect parse:
  `set_auto_upgrade(sd.pointer("/options/auto_upgrade") ... unwrap_or(0))`.
- `flatten_regular_upgrades` — `crates/eldenring-archipelago/src/upgrade_cost.rs`.
  `maybe_apply()` clamps every regular-smithing-stone material count in `EquipMtrlSetParam`
  to 1 on the live param table (lower-only, somber untouched). Connect parse:
  `set_flatten(sd.pointer("/options/flatten_regular_upgrades") ... != 0)`; applied on the
  in-world tick.

Greenfield's `core._options_echo()` already builds the `options` sub-dict (the F1
`gf-contract-options-subdict-gap` fix), so once it emits real values under
`options.auto_upgrade` / `options.flatten_regular_upgrades`, the shared client consumes them
with no change. Both default OFF, so shipping is no-change for existing seeds.

## Changes (all under `greenfield/eldenring_gf/`)

### 1. New feature module `features/upgrades.py`

Mirrors `features/weapon_reqs.py`. `features/__init__.py` pkgutil-auto-imports every module,
so dropping the file self-registers — no import list to touch.

```python
from Options import Toggle
from ..registry import Feature, register

class AutoUpgrade(Toggle):
    """Auto-upgrade any received weapon to your current highest reinforcement on its smithing
    track (normal vs somber). Off by default; the client raises the granted weapon at grant time
    from live inventory + params (raise-only, reconnect-safe)."""
    display_name = "Auto-Upgrade Received Weapons"

class FlattenRegularUpgrades(Toggle):
    """Flatten regular (non-somber) weapon upgrade costs so every smithing-stone step needs only
    one stone. Somber weapons keep their vanilla curve. Off by default; the client clamps the live
    EquipMtrlSetParam counts at runtime (lower-only, reconnect-safe)."""
    display_name = "Flatten Regular Upgrade Costs"

@register
class UpgradesFeature(Feature):
    name = "upgrades"
    OPTIONS = {"auto_upgrade": AutoUpgrade,
               "flatten_regular_upgrades": FlattenRegularUpgrades}
```

No `slot_data()` method: values are emitted centrally by `core._options_echo` (below). The
legacy top-level duplicate that `weapon_reqs`/`scaling` still emit is deliberately skipped — it
is legacy cruft, and the client only reads `options.<key>`.

### 2. `core.py` `_options_echo` — emit real values

Replace the two constant-`0` lines (currently ~393-394):

```python
contract.AUTO_UPGRADE: _opt("auto_upgrade"),
contract.FLATTEN_REGULAR_UPGRADES: _opt("flatten_regular_upgrades"),
```

`_opt(name)` already reads `self.options.<name>.value`, so once the option fields exist on
`GFOptions` (via step 1) this echoes the seed's real choice.

### 3. `contract.py` — refresh the two ContractKey producer/doc strings

Entries at ~213-218 keep shape `INT`, required `True`, profile `GREENFIELD`. Update the
producer/doc from "constant 0" / "feature off" to reflect the live option, e.g.:

```python
ContractKey("auto_upgrade", "INT", True, (GREENFIELD,),
            "core._options_echo (options.auto_upgrade)", "upgrades.rs apply_auto_upgrade",
            "auto weapon-upgrade to highest held reinforcement; 0 off / non-zero on."),
ContractKey("flatten_regular_upgrades", "INT", True, (GREENFIELD,),
            "core._options_echo (options.flatten_regular_upgrades)", "upgrade_cost.rs maybe_apply",
            "flatten regular (non-somber) upgrade-stone counts to 1; 0 off / 1 on."),
```

### 4. Regenerate contract artifacts

```
python greenfield/gen_contract.py    # -> eldenring_gf/contract.json + client contract_gen.rs
python greenfield/gen_handoff.py     # -> handoff/CLIENT_SLOTDATA_CONTRACT.md
```

Shapes are unchanged (INT), so `contract_gen.rs` only gets doc/producer text; the client
validator stays behaviorally identical.

### 5. Tests

- `tests/test_gf_features_smoke.py` — add `"auto_upgrade"`, `"flatten_regular_upgrades"` to the
  `_OPTS` tuple so the smoke test asserts the fields land on `options_dataclass`.
- New round-trip: gen a world with both toggles on, assert
  `sd["options"]["auto_upgrade"] == 1` and `sd["options"]["flatten_regular_upgrades"] == 1`
  (extend `test_gf_slot_data_fixture.py` or add a small WorldTestBase). Guards the
  subdict-gap regression for these keys.
- `tests/test_gf_options.py` OptionsDescriptionGate — satisfied by the docstrings above.
- `test_gf_client_contract_paths.py` — regen keeps the contract-source hash green.

### 6. Deploy sync

Propagate `greenfield/eldenring_gf/` -> `Archipelago/worlds/eldenring_gf/` via the normal
deploy step so both `contract.json` copies match.

## Verification checklist

- pytest greenfield unit suite green (features smoke, options desc gate, contract paths,
  slot_data fixture round-trip).
- `cargo test` in the client green (contract_gen.rs regenerated; no shape change).
- Gen a seed with both on; inspect `slot_data["options"]` shows `1`/`1`.
- In-game (Windows): connect a gf seed with `auto_upgrade` on while holding a higher weapon on
  the same track -> a lower granted weapon arrives upgraded; with `flatten` on, the smithing
  menu shows 1 stone per regular-stone step.

## Risks / open checks

- **Grant path parity.** `auto_upgrade` fires inside `detour.rs grant_full_id`. Greenfield uses
  the same shared client, so its item grants funnel through the same path — but confirm a gf
  grant actually routes through `grant_full_id` (not a divergent grace/flag-only path) before
  claiming auto_upgrade works end-to-end for gf.
- **Defaults.** Both OFF by default => no behavior change for existing greenfield seeds; safe to
  ship dark and enable per-yaml.
- **Playtest yaml.** Optionally flip both on in `greenfield/players/Greenfield.yaml` for the
  flagship playtest, matching how `no_weapon_requirements` is exercised.
