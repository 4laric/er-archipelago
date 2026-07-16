# docs/history — archive

**Not current guidance.** Everything in this directory is a superseded design,
recon, triage, or process document, kept for provenance. It describes work that
has either shipped (and now lives in code) or been replaced by a different
design. Do not follow instructions in these files.

The live sources of truth are:

- **Architecture & setup:** `README.md`, `release-v0.2/SETUP.md`
- **apworld ↔ client contract:** `greenfield/CONTRACT.md` (auto-generated from `greenfield/eldenring/contract.py`)
- **Quality bar / workflow:** `CONTRIBUTING.md`, `AGENTS.md`
- **Current region model:** `SPEC-region-spine-v2.md`, `greenfield/region_groups.py`
- **Pending work:** `docs/specs/` (the work queue) and the kanban `er-archipelago-kanban.html`

---

## Index

### Retired architecture (C#/.NET baker · C++ client · baked seeds)
- `TODO-baker-era.md` — the pre-cutover backlog (regulation.bin patching, ArchipelagoForm.cs, the C++ client). Wholly superseded by the pure-runtime model.
- `SPEC-packaging.md` — baked-seed packaging + SoulsRandomizers licensing. Dissolved by pure-runtime (nothing is baked).
- `SPEC-grace-rando.md` — grace scatter against the C++ client / old apworld. Graces are now bundled per Region Lock (`features/graces.py`).
- `SPEC-gf-configurable-big-ticket-20260708.md` — the retired "big-ticket" concept; replaced by `features/progression_surface.py`.
- `SYNC-RUNBOOK.md` — multiworld join via the old bake workflow. Current: `release-v0.2/SETUP.md`.
- `DLC-AREA-ID-CAPTURE.md` — area-id capture against the retired apworld.
- `RELEASE-CHECKLIST-v0.1.md` — the v0.1 ship checklist (renamed to avoid colliding with the live `RELEASE-CHECKLIST-v0.2.md`).

### Superseded design (matt-free MVP · pre-spine-v2 carve)
- `SPEC-region-capstone-model-20260708.md`, `WIRING-region-capstone-v0.2.md` — folded Leyndell into Altus at 21 regions; overturned by spine v2 (Leyndell goal, 31 regions).
- `SPEC-PARITY-greenfield.md` — the completed MVP→feature-parity roadmap (phases 0–7 all shipped).
- `HANDOFF-greenfield-mvp-20260705.md`, `LESSONS-LEARNED-greenfield.md` — MVP-era snapshots (22 locks / 24 regions / 3,944 checks).
- `DLC-READINESS-AUDIT.md` — pre-spine-v2 DLC audit (21/6 region model).
- `GRACE_GATES_CLIENT_SPEC.md` — work-order for `runeGatedGraces`/`greatRuneItemIds`, retired unbuilt 2026-07-14 (superseded by withholding a gated child's bundle).

### Shipped specs (implemented essentially as written — see the named code)
- `SPEC-client-scaling-20260706.md` → `features/scaling.py` + client `scaling.rs`
- `SPEC-client-tracker-20260706.md` → `er-logic/tracker_regions.rs`
- `SPEC-gen-input-hash-gate-20260710.md` → `tools/gen_manifest.py` + `_gen_stamp.json`
- `SPEC-gf-upgrade-features-port.md` → `features/upgrades.py`
- `SPEC-item-tracker.md` → client `er-logic/tracker.rs` (v0.1)
- `SPEC-runtime-minibake-20260711.md` → `features/check_lots.py` (one placeholder goods row 8852)
- `SPEC-rust-client-port.md` → the `from-software-archipelago-clients` workspace
- `SPEC-semantic-test-tiers-20260706.md` → `*_replay.rs` + region oracles + the contract validator
- `WIRING-boss-locks-v0.2.md` → `bossLockItems` / `boss_felled` / `KickCountdown`

### Contract & architecture recon (superseded by contract.py / CONTRACT.md)
- `CONTRACT-DELTA-20260706.md`, `RECON-contract-keys-20260706.md`, `RECON-tracker-scaling-20260706.md`
- `FABLE-ARCH-REVIEW-FINDINGS-20260706.md`, `FABLE-ARCH-REVIEW-HANDOFF-20260706.md`, `FABLE-FIX-PARALLELIZATION-PLAN-20260706.md`
- `TRIAGE-test-upgrades-20260706.md`

### Game-fact recon (timeless; still-useful provenance)
- `ANALYSIS-dlc-progression-map.md`, `ANALYSIS-legacy-dungeon-chokepoints.md`
