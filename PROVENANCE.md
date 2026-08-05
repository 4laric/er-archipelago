# Provenance

Where this project's data comes from, what it deliberately does **not** contain, and the rule for
working alongside other Elden Ring randomizers.

This file exists because the derivation is the asset. Everything below is checkable from the tree;
where a claim has a command that proves it, the command is given.

---

**Two documents, two audiences.** This file is the *repo* rule: what a contributor may and may not
put in the tree, and which gate enforces it. `release/ATTRIBUTION.md` is the *release* document
that ships to players — licence, credits, and the link to thefifthmatt's randomizer we point at
rather than redistribute. They cross-reference; neither replaces the other.

---

## The five non-negotiables, and the gate that enforces each

Referenced from `release/ATTRIBUTION.md`. Each is a machine check, not an intention — the
point of the list is that none of them relies on anyone remembering.

| # | Non-negotiable | Enforced by |
|---|---|---|
| 1 | **No game assets or licensed game data in the tree.** No `regulation.bin`, no `.dcx`, no MSB/FMG/EMEVD, no `elden_ring_artifacts/`. | `.gitignore` (`/elden_ring_artifacts/`, `game-files/`, `/applied_patches/`); `tools/check_integrity.py` as the pre-commit hook |
| 2 | **No data or code from another randomizer.** Reading to cross-check is fine; committing it — or copying flags out of it — is not. | `check_integrity.py`'s foreign-list signatures + `test_gf_provenance_gate.py` (13 tests); `tools/diff_foreign_list.py` cannot print a foreign id |
| 3 | **Every table is DERIVED, never typed.** Each generated module carries a `_GEN_STAMP` naming the `inputs_hash` it came from. | CI `generators` job: regenerates and fails on a non-empty `git diff`; `test_gf_gen_stamp.py` |
| 4 | **A hand list only where the derivation genuinely cannot reach**, and it must say why. | `CONTRIBUTING.md` review bar; the coverage gate (`coverage.py`) fails generation on an unclassified location |
| 5 | **Generated output is reproducible.** A regen on Windows and a regen in Linux CI produce identical bytes. | determinism tests (sorted sets, `sort_keys`, `newline="\n"`, `eol=lf` in `.gitattributes`), proven by the same CI diff as #3 |

If you are adding something and cannot point at the row that covers it, that is the interesting
case — raise it rather than guessing.

---

## What ships here

| | |
|---|---|
| Code in this repo | MIT (`LICENSE`) |
| Runtime client (`from-software-archipelago-clients`) | MIT |
| Game assets | **none** — `git ls-files` has no `.dcx`, no `regulation.bin`, no FMG, no MSB |
| Game files modified at runtime | **none** — no `regulation.bin` patch, nothing baked per seed |
| Data or code from another randomizer | **none** — see *The foreign-list rule* below |

Elden Ring and Shadow of the Erdtree are property of FromSoftware / Bandai Namco. This is an
unaffiliated fan project.

---

## How the world data is derived

Every table under `greenfield/` is generated from **vanilla game data**, by tools in this repo,
against files that never enter this repo.

`greenfield/gen_data.py` reads exactly (enumerated from its read sites, and pinned by
`tools/gen_inputs.py`):

- **13 param CSVs** (the bundle carries every `*.csv` in the params dir; these 13 are the ones
  `gen_data` reads, and a missing one refuses the build) — `BonfireWarpParam`, `EquipMtrlSetParam`,
  `EquipParamAccessory`,
  `EquipParamGoods`, `EquipParamProtector`, `EquipParamWeapon`, `GestureParam`,
  `ItemLotParam_enemy`, `ItemLotParam_map`, `NpcParam`, `PlayRegionParam`, `ShopLineupParam`,
  `ShopLineupParam_Recipe`
- **15 FMG XMLs** — `{Weapon,Protector,Accessory,Goods,Gem}Name` × `{base, dlc01, dlc02}`
- **the decompiled EMEVD** (`event/*.emevd.dcx.js`)
- **the decompiled talk ESD** (optional; feeds the `esd_*` datamines)

The Tier-2 spatial datamines additionally read witchy'd MSBs. Those are the unwieldy half and stay
on the build box.

**The licensed game data is Windows-only and stays there.** It is never copied, never symlinked,
never committed — `/elden_ring_artifacts/` and `game-files/` are `.gitignore`d, and
`tools/check_integrity.py` runs as the pre-commit hook.

Every generated file carries a `_GEN_STAMP` naming the `inputs_hash` it was derived from, and CI
regenerates the AP-free generators and fails on a non-empty diff. So "this table was derived, not
typed" is a property the build checks, not a claim in a README.

### Derivation over hand entry

`CONTRIBUTING.md` is the bar: **derive the datum, don't pin the symptom.** A hand-maintained list is
permitted *only* where the derivation genuinely cannot reach, and it must say why. This is a quality
rule first, but it is also what keeps the provenance story simple: there is no large hand table in
this repo for anyone to wonder about the origin of.

---

## The foreign-list rule

Other Elden Ring randomizers exist, and theirs are good work. The relevant one here is
thefifthmatt's randomizer, whose location list circulates both in source and as a plain list inside
his Nexus binary release, and whose terms forbid redistributing a modified fork of his randomizer.
Downstream Archipelago worlds in that lineage key their locations off that list.

**This tree contains none of it.** The old matt-lineage world was retired wholesale — prove it with:

```
git ls-files worlds/            # 0 files
```

The working rule, which applies to any foreign randomizer's data:

> **Reading it to cross-check is fine. Ingesting it is not.**

Concretely:

- ✅ Compare our corpus against theirs **locally**, to find out where *our* derivation is short.
- ✅ Read their repo to understand a mechanism, then go derive the mechanism ourselves.
- ✅ Interoperate at runtime — our client can parse a foreign apworld's keys at connect time,
  because that is the *user's* copy on the *user's* machine.
- ❌ Commit their list, or any subset of it, into this repo.
- ❌ Redistribute their apworld or their binary's data files.
- ❌ Copy flags out of their list into ours — even flags we are missing. That is the same act as
  committing the list, done slowly.

The last one is the one that feels harmless and is not. It was proposed once here and retracted.

### Why a diff is still allowed, and what shape it has to take

`tools/diff_foreign_list.py` compares a foreign list you supply **from your own disk** against our
corpus. It is built so that the interesting output is *where our derivation is short*, never *what
to paste*:

- it takes the foreign file as a runtime argument and writes nothing back;
- it reports **aggregates** — how many entries we already have, how many we lack, and for the ones
  we lack, which of *our own* tables can already place them, bucketed by region;
- it **cannot print foreign identifiers**. There is no flag for it. If our tables can place a
  missing entry, that entry is a gap in *our* derivation, and the fix is to re-run *our* datamine
  scoped to the named region — which produces a datum we derived, from vanilla data, with a stamp.

That distinction is not only legal caution. A flag copied from a foreign list is a hand entry we
cannot regenerate, cannot stamp, and cannot defend — it fails `CONTRIBUTING.md` on its own terms,
independently of anyone's licence. **Let the other project be the bug report; keep our datamine as
the source.**

`tools/check_integrity.py --staged` (the pre-commit hook) refuses to commit a file carrying a
foreign location-list signature, so this is a gate rather than a habit.

Legitimate uses of the *grammar* exist — the foreign-apworld degrade test encodes one synthetic key
so our client's vanilla fallback can be tested. Such a file declares itself with a
`PROVENANCE-OK:` comment stating that its keys are synthetic. That is deliberately an in-file
declaration and not a filename allowlist in the tool: the claim then appears in the diff, where a
reviewer sees it being made. `PROVENANCE-OK:` (grep it) should stay a very short list.

---

## Credits

- **thefifthmatt** — the Elden Ring randomizer and the tooling around it (ESDLang, Yabber-lineage
  format work) that the wider modding community, including this project's *understanding* of the
  formats, is downstream of. No data or code from those projects is in this tree.
- **The Archipelago project** — the multiworld protocol and server this world plugs into.
- **The `soulsmods` / `fswap` ecosystem** — `soulstruct`, `witchy`, ModEngine3, and the
  `from-software-archipelago-clients` lineage our Rust client belongs to.
- **FromSoftware / Bandai Namco** — the game. Not affiliated, not endorsed.

If you believe something here is misattributed, open an issue — provenance corrections take
priority over features.
