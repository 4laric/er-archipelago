# ER Archipelago — v0.2 Release Checklist (Greenfield apworld)

*Drafted 2026-07-07. Companion to `RELEASE-CHECKLIST.md` (v0.1) and `greenfield/SPEC-PARITY.md`.*

## Scope / assumption

v0.2 ships the **greenfield** world (`greenfield/eldenring_gf`) as the headline apworld: a
from-scratch, **data-derived, provenance-clean** rebuild with no Bedrock/matt data or code (see
`greenfield/SPEC-PARITY.md` P1–P5 and `PROVENANCE.md`). It rides the **existing MIT Rust client**
via the keyless slot_data path (`locationFlags` + `regionOpenFlags` + `apIdsToItemIds`) — no client
fork. The v0.1 (matt-lineage) apworld is superseded.

**Decision (locked 2026-07-07):** the published game id is **`"Elden Ring"`** (drops `(Greenfield)`;
supersedes the v0.1 game id — not cross-compatible with v0.1 seeds/rooms). The rename spans the world
(`core.py` `GAME`), the template yaml, the greenfield tests, AND the Rust client's Connect string
(`core.rs:213`) — all covered by `patch_gf_rename_and_version.py`.

**Prep automation written this session (all run on Windows):**
- `patch_gf_rename_and_version.py` — game rename ("Elden Ring") across world + yaml + 22 tests +
  client `core.rs`; adds `WORLD_VERSION = "0.2.0"`; quarantines the old `worlds/eldenring` during
  isolated greenfield gen to dodge the duplicate-game collision. Self-verifying, ASCII, idempotent.
- `patch_build_greenfield_apworld.py` — adds `-GreenfieldApworld` to `build.ps1` (regen data +
  install + zip → `eldenring_gf.apworld` + timestamped twin).
- `release-v0.2/` — SETUP, CHANGELOG, ATTRIBUTION (credits nex3 + vswarte; upstream-AP MIT license),
  KNOWN-ISSUES, and the `EldenRing.yaml` flagship template (`game: "Elden Ring"`).
- `.gitignore` — now ignores `gendiag_*` / `generate_*.log` / `gensweep_*` / `genfuzz_*` dumps.

---

## ✅ Already done (verified / landed)

- Greenfield **gens end-to-end**, winnable, AP-recognized; latest run clean (`generate_greenfield_*.log`).
- **Phase 0 boot contract** landed — `apIdsToItemIds` + `regionOpenFlags` emitted (`tests/README.md`).
- **Phase 1 num_regions spine** landed — the marquee mode, on the clean base (`region_spine.py`).
- Feature modules ported onto greenfield: num_regions, scaling, boss_locks, grace_rando,
  important_locations, missable_locations, pool_builder, progressive, shops, weapon_shop_slots,
  local_items, goal_locations, start_grace/start_items, upgrades, varied_filler, deathlink.
- **Semantic test tiers** shipped — replay suites + region gates, CI-gated (`SPEC-semantic-test-tiers-20260706.md`).
- **Contract single-source** (`contract.py` + `validate_slot_data`) and the **options-subdict read gap**
  both landed; client-read-path audit in place.
- map_lot region quarantine, dungeon-grace mis-bundle, boss-gated grace-skip oracle — fixed + test-guarded.

---

## 🔴 Blockers to the v0.2 tag

### A. Packaging + rename (patches written; must run on Windows)
- [x] **Greenfield apworld packaging mode** — `patch_build_greenfield_apworld.py` adds
      `-GreenfieldApworld` (regen + install + zip → `eldenring_gf.apworld`). *Run on Windows.*
- [x] **World version stamp** — `WORLD_VERSION = "0.2.0"` added by `patch_gf_rename_and_version.py`
      (module constant only; slot_data left untouched — `validate_slot_data` rejects undeclared keys).
- [x] **Game rename to "Elden Ring"** (world + yaml + tests + client `core.rs`) — same patch.
- [ ] **Run the patches on Windows** (`--apply`), then `build.ps1 -GreenfieldApworld`.
- [ ] **Rebuild the client `.dll`** — `cargo build` the client on Windows AFTER the rename, so the
      shipped binary connects as "Elden Ring" (the pre-built .dll still embeds the old string).
- [ ] **Retire-vs-quarantine the old `worlds/eldenring`.** Quarantine protects isolated gen/CI, but a
      real multiworld host with both worlds installed would still collide on `game = "Elden Ring"`.
      Decide whether to fully retire the matt-lineage world for v0.2.
- [ ] **Gen-test the shipping yaml once on Windows** (sandbox can't run AP gen) — confirm
      `release-v0.2/EldenRing.yaml` generates clean and the spoiler looks right.
- [ ] **Fuzz clean** — run `greenfield/fuzz_gf.py` / `gen_fuzz_gf_yamls.py`; no crashes, graceful
      rejects only (CONTRIBUTING bar: "any yaml → clean gen or graceful reject").

### B. In-game confirmation of landed-but-unverified fixes
These are wired in code but **not yet confirmed in-game** (save-load / reconnect). Each is a
data-loss risk if it regressed:
- [ ] **Region front-door latch** — Limgrave graces were lost when bloom latched on the open flag;
      fix wired (`region_bloom_settled`, site 1). Confirm graces survive a save-load in-game.
- [ ] **Flag-poll new-save baseline** — reconnect re-snapshot ate earned checks ("Sacred Tear got
      nothing"); baseline-persist landed 2026-07-07. Confirm reconnect keeps earned checks.
- [ ] **Start-item / Torch clobber** and **flask double-grant on tutorial-death reload** — replay
      guards exist; confirm no clobber/double-grant in-game.

### C. Client contract compatibility
- [ ] **Confirm the shipped client `.dll` reads greenfield slot_data.** Greenfield emits the keyless
      path only (no `locationIdsToKeys`/matt tokens). Verify on a live seed: checks register, region
      locks open regions, filler grants a real item (`apIdsToItemIds` → Golden Rune FullID).
- [ ] Confirm the **3 DLC sub-areas** with `REGION_OPEN_PENDING` (Abyssal Woods, Jagged Peak, Scadu
      Altus) behave as "unlocked" and don't strand checks (SPEC-PARITY §14.4).

### D. Docs + provenance (player-facing)
v0.1 shipped a `release-v0.1/` bundle (SETUP, CHANGELOG, template yaml, explainers). Greenfield has
only dev docs (`greenfield/README`, `HANDOFF`, `CONTRACT`, `SPEC-PARITY`). `release-v0.2/` created:
- [x] Flagship **template yaml** — `release-v0.2/EldenRing.yaml` (`game: "Elden Ring"`; option keys
      pulled from real greenfield source; num_regions headline).
- [x] **SETUP.md** — install (client `.dll` + `eldenring_gf.apworld`), connect, play.
- [x] **CHANGELOG.md** — headlines the provenance-clean rebuild + the game-id rename.
- [x] **ATTRIBUTION.md** — credits **nex3** and **vswarte**; adopts upstream-Archipelago (MIT)
      license; cross-refs `PROVENANCE.md` / SPEC-PARITY P1–P5.
- [x] **KNOWN-ISSUES.md** — Spirit Calling Bell, map-on-connect, Shadow Keep church-drain grace, +
      the two wired-but-unconfirmed fixes.
- [ ] **Review pass on the docs** — the docs agent flagged that the sample `Greenfield.yaml` carried
      stale keys (`flatten_smithing_stones`, `auto_upgrade`); the template uses the real
      `flatten_regular_upgrades`. Eyeball `EldenRing.yaml` against a real gen before shipping.

### E. Repo hygiene + CI (public repo)
- [ ] **`run_ci.ps1 -OnlyGreenfield` must be 100% green** before tag (num_regions is the marquee —
      100%-green gate per project standard). Run the full greenfield suite on Windows/Py3.11.
- [x] **`.gitignore` updated** — `gendiag_*`, `generate_*.log`, `gensweep_*`, `genfuzz_*`,
      `preflight_*` now ignored (`*.bak_*` and `patch_*.py` were already ignored).
- [ ] **`git rm` the tracked clutter** on Windows: `greenfield/eldenring_gf/tests/_DELETE_ME_brk.txt`
      and any already-committed `*.bak_*` / dump files (mount blocks unlink; do it on Windows). Never
      `git add -A` blind; check `git diff --cached` before committing.
- [ ] Confirm no game-data / non-free FromSoft content is staged (filter-repo history stays clean).

---

## 🟠 Feature-parity decisions (ship vs gate-off for v0.2)
- [ ] **Upgrade features (`auto_upgrade` / `flatten`)** have **zero replay-test coverage** and are
      blocked on the er-logic extraction. Decide: gate them off in v0.2, or accept as documented
      "experimental." (Default: gate off — keep the 100%-green promise honest.)
- [ ] **Unsound alternate modes** — per project policy, prefer *deleting* an unsound mode over
      shipping it behind a warning. Sweep the option surface for any mode that can't gen-clean and
      cut it from v0.2.

---

## Critical path to the tag
1. ~~Decide the game name~~ → **"Elden Ring"** (locked). ~~Write rename/packaging patches + docs~~ (done).
2. Windows: run `patch_gf_rename_and_version.py --apply` + `patch_build_greenfield_apworld.py --apply`;
   then `cargo build` the client `.dll` (new "Elden Ring" Connect string).
3. Windows: `build.ps1 -GreenfieldApworld` → `eldenring_gf.apworld`.
4. Windows: `run_ci.ps1 -OnlyGreenfield` 100% green; gen-test + fuzz `release-v0.2/EldenRing.yaml`.
5. In-game: confirm B (front-door latch, flag-poll baseline, start-item/flask) and C (renamed client
   connects + reads greenfield slot_data) on one live seed.
6. Decide retire-vs-quarantine for the old `worlds/eldenring`; `git rm` tracked clutter; commit only
   intended files (`git diff --cached`).
7. `git tag v0.2` → GitHub Release: attach `eldenring_gf.apworld` + `release-v0.2/` docs; client
   `.dll` on Nexus.
