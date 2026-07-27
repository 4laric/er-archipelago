# HANDOFF — `progression_surface: all` (every non-missable location)

**Written 2026-07-27, end of the enemy-scaling session. Nothing below is built.** This is scoping
plus the measurements, so a fresh session does not have to re-derive them.

**The ask (Alaric, relaying a player):** let progression land on **every non-missable location**, not
just the tagged classes.

---

## 1. Read this first: the request is NOT "list every class"

`progression_surface` is an `OptionSet` whose `valid_keys` are the 14 classes in
`contract.IMPORTANT_LOCATION_TYPES`. Setting all 14 is **already possible today** and I verified it
generates clean (seed 4242, 2 slots): first rung, `placed 29/29; 0 SPILLED`, and a check breakdown
essentially identical to the default seed.

But it does not do what the player wants, and this is the whole point of the handoff:

| | checks | share of world |
|---|---:|---:|
| total checks (`sum(len(v) for v in data.LOCATIONS.values())`) | **4879** | 100% |
| carry ANY class tag — the ceiling for *any* `progression_surface` value today | **883** | 18.1% |
| today's default surface | 184 | 3.8% |
| all 14 classes | 869 | 17.8% |
| **the ask: every non-missable, progression-safe check** | **3927** | **80%** |

**The other ~4000 checks carry no class tag at all**, so no combination of existing `valid_keys`
reaches them. The ask is ~4.5x the widest thing currently expressible. It is a new capability, not a
new option value.

> ⚠️ I got this wrong first: I measured `len(lt.LOCATION_TAGS)` = 883 and called it "98.4% of all
> checks". `LOCATION_TAGS` is the TAGGED SUBSET, not the corpus. `data.LOCATIONS` is a
> **region → list** dict (32 regions), so `len()` on it is 32, not the check count. Use
> `sum(len(v) for v in data.LOCATIONS.values())`.

---

## 2. What "non-missable and safe" already means in code

The exclusion set exists and is well-defined. Measured against the 4879:

| set | count | where | why it bars progression |
|---|---:|---|---|
| `MISSABLE_LOCATIONS` | 179 | `missable_locations.py` | can be permanently lost; `protect_missable_locations` is frozen ON |
| `DEFAULTED_REGION_APS` | 506 | `location_tags.py` | region is a GUESS — may sit in a sealed region |
| `ERDTREE_BURN_APS` | 145 | `location_tags.py` | m11_00 is destroyed when Maliketh dies |
| `SHOP_RELEASE_GATED_APS` | 185 | `location_tags.py` | merchant does not stock the row until an unlock fires |
| **union barred** | **952** | `core._NO_PROGRESSION_APS` ∪ missable | |

`core.py` already unions the last three into `_NO_PROGRESSION_APS` and enforces it. So
**4879 − 952 = 3927** is the honest answer to "everything that can safely hold progression".

Also relevant and NOT yet in that union: the **28 two-region checks** made un-requirable in
`7983db8` this same day (a check obtainable in two regions, order-dependent, so a required item on
one strands a player routed the other way). Confirm whether they are already folded into one of the
sets above or need adding — I did not check, and the count above may therefore be ~28 optimistic.

---

## 3. Design shape

`progression_surface` is an `OptionSet` of class names. The two candidate shapes:

**(a) A sentinel member** — accept `All` as a `valid_keys` entry meaning "everything safe".
Cheap, keeps one option, reads well in yaml (`progression_surface: [All]`). Ugly in that one member
is not a class and would need special-casing wherever the set is consumed.

**(b) A separate mode** — `progression_surface_mode` already exists (`off` / `soft` / `strict`,
frozen at `strict`). A fourth value, or a distinct boolean, that bypasses class filtering entirely.
Cleaner semantically; costs a second knob and the two interact.

I lean **(a)**, but it is a design call and the consumers matter — see §4.

Whichever: **the default must not move.** Today's default is 184 locations and a fresh yaml must
generate identically.

---

## 4. Consumers you must not miss

`progression_surface` is NOT only a fill input. `contract.SURFACE_DEFAULT_CLASSES` is single-sourced
because **the AP-free tracker generator needs the same selection and cannot import an AP OptionSet**
(`tools/gen_location_regions.py` bakes `er_logic::tracker_regions` `LOCATION_META.on_surface`).

So a surface that is no longer expressible as a set of class names has to be representable for:

1. `features/progression_surface.py` — the fill-time confinement + feasibility ladder;
2. `contract.py` — the shared definition;
3. `tools/gen_location_regions.py` → client `tracker_regions.rs` — the F6 tracker's starring;
4. `confine_foreign_progression` — the same surface is used to confine OTHER players' progression;
5. `wizard/options-metadata.json` + `release-v0.2/EldenRing.yaml` + the SHIPPED player guide
   (`Elden-Ring-Archipelago-Player-Guide.md` at the repo ROOT — **not** `release-v0.2/PLAYER-GUIDE.md`,
   which ships to nobody; `test_gf_player_guide.py` gates the right one).

(3) is the one that will bite: "star every non-missable check" makes the tracker's surface highlight
meaningless. Decide what the tracker should do before building the fill side.

---

## 5. Hazards, with the specific gate each one trips

- **Sphere shape (CONTRIBUTING, "not a billion checks in sphere 0").** A 3927-location surface means
  progression can hide anywhere, which is *fine for the gradient* but must be measured, not assumed.
  Use `ER_DUMP_SPHERES=1` and compare sphere-0 share against a default seed across a sweep. A
  widened surface is exactly the change that could balloon sphere 0 while still generating clean.
- **`accessibility: minimal`.** The shipped yaml uses it, and region_lock seeds need it. Widening the
  surface interacts with what "reachable" has to mean — check `test_gf_gated_children` and the
  defaulted-region guard still hold.
- **The feasibility ladder widens, never fails.** With the widest possible surface the ladder has
  nowhere to widen TO, so a genuinely infeasible seed changes failure mode. Make sure it still
  rejects loudly rather than FillError-ing.
- **`confine_foreign_progression: true` (default).** At 80% surface this is close to a no-op. That
  may be fine, but the option's docstring currently promises meaningful confinement — a docstring
  that lies is a bug (CONTRIBUTING).
- **Item-pool count-neutrality** is unaffected (this changes placement, not counts) — but say so in
  the PR rather than leaving it unstated.

---

## 6. Acceptance test (rule 11 — the motivating case IS the test)

The case that motivated this is "a player wants progression on ordinary world drops". So assert, end
to end on a generated world, that with the new setting **a check carrying NO class tag actually
receives this world's progression** — not merely that the option parses and the seed gens. A test
that only checks the option is accepted would pass on a build where the widening silently did
nothing, which is this project's signature failure.

Plus: default seed byte-identical; `gen_sweep` + `run_fill_regression`; sphere-0 share vs baseline.

---

## 7. Environment (saves ~30 min)

Everything needed is standing in the sandbox — see memory `er-sandbox-ap-env-works` and AGENTS §5b.

```
O=/sessions/<session>/mnt/outputs
$O/py311/python/bin/python3.11          # 3.11 (3.10 dies on typing.Self)
$O/ap2                                  # sparse AP 0.6.7, real git, gf_test-compatible
$O/er, $O/cl                            # world + client clones
python tools/gf_test.py --install-only --ap-dir $O/ap2
TMPDIR=/dev/shm HOME=/tmp/gfhome3 PYTHONDONTWRITEBYTECODE=1 AP_NONINTERACTIVE=1 \
  SKIP_REQUIREMENTS_UPDATE=1 python -m pytest -q -p no:cacheprovider worlds/eldenring/tests/
```

🛑 `/dev/shm` is **wiped between bash calls** — create player yamls and run `Generate.py` in ONE
call. `/tmp` and `/sessions` run 100% full; use the outputs mount. Suite needs ~4 chunks under the
45s cap.

---

## 8. State at handoff

World `main` at `4d42d8f`, client at `1f27f20`, **all CI green on both**. v0.2.12 versioned across
apworld / `archipelago.json` / client crate, with lockstep tests both ends.

Nothing in this document is started. No branch, no stub.
