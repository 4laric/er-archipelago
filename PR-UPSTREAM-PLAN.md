# Upstream PR Plan

Grouping our work into logically-scoped, independently-reviewable PRs against the right upstreams.
Drafted 2026-06-16. Routing is driven by **which repo a change physically lives in**, because that
determines both the PR target and the licensing exposure.

## Routing summary

| Repo (local) | Upstream | License posture | Verdict |
|---|---|---|---|
| `Archipelago/worlds/eldenring/` (Python apworld) | ER apworld maintainer (lBedrockl fork / ArchipelagoMW) | Clean — AP world code | **Primary target.** Most upstreamable. |
| `SoulsIds/` | `thefifthmatt/SoulsIds` | Permissive lib, actively merges PRs | **Clean win.** Tiny generic fix. |
| `SoulsFormats/` | `thefifthmatt/SoulsFormats` | Permissive lib, actively merges PRs (#219, #217…) | **Clean,** but isolate our commit from the DSMapStudio re-sync noise. |
| `SoulsRandomizers/` (C# baker/randomizer) | thefifthmatt-derived | **Licensing landmine** (per our notes) | **Park.** Also where the DLC baker logic lives — leave alone per your steer. |
| `Dark-Souls-III-Archipelago-client/` (runtime client) | our fork of the DS3 AP client | Fork track | Separate, later. |

Apworld upstream confirmed (2026-06-16): **`lBedrockl/Archipelago`** — a fork of
`ArchipelagoMW/Archipelago`, ER world under `worlds/eldenring`. Status from the GitHub API:
- **Last code push 2026-02-10** (metadata touched 2026-06-03, but no commits since Feb) — quiet ~4 months.
- **Issues are disabled**, no Discussions. PRs ARE enabled (`pull_request_creation_policy: all`, 0 open).
- License is `NOASSERTION` (inherited custom AP license) — normal for AP world contributions.
- Practical consequences: (1) the local `Archipelago` remote points at `4laric/Archipelago`; add
  `lBedrockl/Archipelago` as the PR-base remote. (2) The region_lock "design-first" step can't be an
  issue — use a **draft PR** or a direct ping (their YouTube/Discord) instead. (3) A 4-month-idle
  personal fork may be slow to review; if it's unresponsive, the fallback is the (much higher-bar)
  ArchipelagoMW world-inclusion process.

---

## Track A — apworld (Python). Primary, no license risk.

These are the changes you flagged: region lock (the feature upstream wanted) plus genuine
plumbing/correctness fixes. All live under `Archipelago/worlds/eldenring/`. Split so a reviewer can
take them one at a time, easiest/most-isolated first.

### PR A1 — Reclassify build-relevant filler as `useful` (junk ammo excluded)
- **Scope (corrected):** `__init__.py` `generate_early()` classification pass (~L373–407), NOT a
  one-liner in `items.py`. The ammo guard is a `continue` *inside* a filler→useful promotion block.
- **Why:** real gear (weapons/armor/talismans/AoW + key GOODS) sits in the undifferentiated filler
  bucket; promoting it to `useful` gives fill the right signal without making it progression. Junk
  ammo is excluded by **er_code range 50.0M–53.6M, not by name** (Bolt of Gransax is a spear).
- **Dependency:** the promotion block is our addition ("AP sync candidate", not yet upstream), so the
  PR ships the whole block unless lBedrockl already reclassifies — diff first, then pick full vs.
  ammo-only scope. See `PR-A1-useful-reclass-ammo-guard.md`.
- **Status:** ready after the upstream-diff decision gate + a stock-yaml gen-test. Mild design
  sensitivity (changes fill behavior) — invite maintainer pushback on the GOODS keep-list.

### ~~PR A2 — filler shortage under forbid_useful~~ → DROPPED (not a PR)
- **Verdict:** configuration, not a code defect. The "not enough filler" abort only occurs when our
  trimmed/lean pools meet the stock `forbid_useful` default; the fix is a YAML change
  (`allow_useful` on both behaviors), not a diff. Stock pools never trip it.
- **Action:** fold the guidance into our own trimmed-mode docs, not upstream. One optional real-code
  improvement (graceful fallback vs. hard abort) is parked as a backlog idea — unbuilt, do not PR.
- See `PR-A2-forbid-useful-NOTE.md`.

### PR A3 — Fix: rune-skip demand-drop to avoid fill deadlock
- **Scope:** `__init__.py` `create_items` (cheapest-first Golden Runes [1]–[5], emitted only when short).
- **Why:** DLC-off pools could overflow and deadlock the fill when region locks consume slots;
  demand-dropping the cheapest runes fits the locks in-world.
- **Caveat:** entangled with region_lock conceptually. If it reads cleaner *after* A4 lands, sequence
  it second. Needs a Windows gen-test before sending (see Gate below).
- **Status:** hold until gen-tested.

### PR A4 — region-lock ENHANCEMENTS (decompose; the base mechanism is likely already upstream)
Reframe: `WorldLogic` already defaults to `region_lock` and `_region_lock()` is fork core — so this
isn't "introduce region lock," it's upstreaming our 2026-06 enhancement layer. Splits by client/baker
coupling. Full breakdown in `PR-A4-region-lock-PLAN.md`. Run the **decision gate** (diff region
machinery vs lBedrockl@main) before opening anything.

- **A4-warp** — `RegionAccessLogic` (geographic|warp), `_region_lock_warp_access()`. Pure logic, no
  client dep. **Cleanest first region PR** → open as a draft for design sign-off (Issues disabled).
- **A4-count** — `region_spine.py` + `RegionCount` capital-run spine. Pure logic/fill, no client dep.
- **A4-grace** — grace bundle (`GracesPerRegion`, `regionGraces`/`startGraces`, `grace_data.py`).
  **Client-coupled:** the option is inert without a client that consumes `regionGraces`. Hold and pair
  with the client PR; do not ship solo.
- **A4-enforce** — `areaLockFlags`/`lockRevealFlags` + `map_region_data.py`. **Excluded:** needs client
  + baker EMEVD fog-walls (SoulsRandomizers / landmine). Park with Track D.
- **Also excluded:** the `dlc_only` Gravesite-start variant (our mode, still failing in-game).

---

## Track B — SoulsIds library. Cleanest single win.

### PR B1 — Events: pad omitted trailing args in ParseAdd
- **Target:** `thefifthmatt/SoulsIds`.
- **Scope:** `SoulsIds/Events.cs` (+ minor `GameEditor.cs` / `ParamDictionary.cs` touch — trim to the
  Events fix only for the PR).
- **Why:** generic event-tooling correctness; nothing AP- or DLC-specific. 14-line, self-contained.
- **Status:** ready. This is the lowest-friction PR of the whole set — good one to land first to open
  a contribution channel with the upstream maintainer.

---

## Track C — SoulsFormats library. Clean, but needs isolation.

### PR C1 — zstd DCX streamed 64KB frames + PARAM read/write fixes
- **Target:** `thefifthmatt/SoulsFormats`.
- **Scope:** our commit `8f63d7b "ER: zstd DCX streamed 64KB frames; PARAM fixes for AP randomizer"`.
- **Why:** library-level format support (zstd DCX streaming) and PARAM correctness — generic, reusable,
  the kind of thing this repo already takes (cf. merged #219, #217).
- **Required prep:** the working tree's diff vs. merge-base spans 83 files / ~17.8k insertions because
  it also carries a DSMapStudio re-sync (TAE.cs, CryptographyUtility, etc.). **Cherry-pick just our ER
  commit onto a fresh branch off `upstream/master`** so the PR is only our changes. Do not PR the raw diff.
- **Status:** ready after the cherry-pick/isolation step.

---

## Track D — SoulsRandomizers (baker/randomizer). PARK.

Per your steer ("if it's easier with the thefifthmatt stuff, leave the DLC stuff alone") and our own
licensing note, **do not open PRs here for now.** For the record, the genuinely-clean fixes stranded
in this repo are:

- **KeepDlcMaps int-toggle bug** (`RandomizerCommon/ArchipelagoForm.cs`) — `enable_dlc` read via
  `BoolOptions()` dropped the int toggle → 871 DLC locations never scraped. Real bug, but DLC-specific
  and inside the landmine repo. Leave alone.
- GetSlotData-at-login timeout fix, acquisition-modal suppression (param edit), bake polish
  (pickup glow / single-grant), region-lock EMEVD enforcement.

If the licensing question is ever resolved, KeepDlcMaps + slotdata-at-login are the two cleanest
candidates to revisit first.

---

## Track E — Runtime client. Separate fork track, later.

Lives in `Dark-Souls-III-Archipelago-client/` (our fork). Generic, non-curation fixes worth eventually
upstreaming to the client effort: Torrent start-grant, companion "obtained" flags, item-source
"X from Y" notify, console PrintJSON ItemSend. Hold until the apworld + library PRs are moving and the
client changes are confirmed built on Windows.

---

## Suggested order

1. **B1** (SoulsIds ParseAdd) — smallest, opens a channel with thefifthmatt.
2. **A1** (useful reclassification + ammo guard) — establishes the apworld relationship; run the
   upstream-diff decision gate first.
3. **C1** (SoulsFormats zstd/PARAM) — after the cherry-pick isolation.
4. **A4** (region_lock) — design-first (draft PR, since lBedrockl Issues are disabled), then code.
5. **A3** (rune-skip) — after A4, once gen-tested.
6. Client (Track E) and anything in Track D — deferred.
- ~~A2~~ dropped (config, not a PR).

## Gate before any PR
- **Don't PR un-built / unconfirmed work.** Anything coded-but-not-Windows-built or marked UNCONFIRMED
  in our notes (e.g. RLA CrashFix.dll) stays out until it actually runs.
- Each apworld PR should pass a clean Windows gen-test on its own branch.
- Strip our project-specific modes (trimmed/lean curation, dlc_only, boss/grace sweep,
  dlc_gear/spell curation, relevance-uplift) from every upstream PR.
