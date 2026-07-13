# ER Archipelago — Release Checklist

*Refreshed 2026-07-04. Supersedes the 2026-06-17 snapshot. Decision: **v0.1 is GO.***

The June-17 version of this doc listed the SoulsRandomizers/baker licensing
problem as the top release blocker. **That blocker is gone:** the July 1 baker
retirement moved the project to a pure-runtime model, so v0.1 ships **no baked /
non-freely-licensed FromSoftware content** — just the MIT client + apworld + a
static detection table. The remaining work is packaging and a git tag.

---

## ✅ Decisions locked (Alaric, 2026-07-04)

- **Spirit Calling Bell** — **NOT a blocker.** Ships as a documented known issue.
- **Map pieces granted on connect** — **NOT a blocker.** Accepted behavior (a few
  free checks at run start).
- **Dragon Communion softlock** — **RESOLVED.** Fix applied and gen-tested.
- **Scope** — v0.1 headlines the **Shattering** mode (`num_regions`) with a
  verified-green base-game config; other modes present as variants.
- **Tracker** — the **in-client tracker window is implemented and working**
  (F6 / overlay **Tracker** menu; region-grouped checks, hint marking,
  locked-region dimming, reachable-only + big-ticket filters) and ships in v0.1.
  The **PopTracker pack** (`poptracker/`) also ships as an optional external tracker.

---

## ✅ Verified green — shipping

- Pure-runtime loop: pickup → check → item grant, confirmed in-game
- Region locks — **warp-enforced** (client, not honor-system); grace bundles on receipt
- Native-style item send/receive notifications
- DeathLink — validated both directions in-game
- Custom AP item icons via the ModEngine3 `ap-package`
- In-client tracker window (F6 / overlay menu) — region-grouped checks, hint
  marking, locked-region dimming, filters
- Progressive tiers / bells, start-item dedup, quick_start, early_leveling
- Pool builder, curation, trimmed pool
- The Shattering (`num_regions`) — Capital/Morgott run, gen-tested

---

## 📦 Packaging — the actual remaining work

- [x] Flagship template yaml — `release-v0.1/EldenRing-Shattering.yaml`
- [x] Player setup guide — `release-v0.1/SETUP.md`
- [x] v0.1 changelog / release notes — `release-v0.1/CHANGELOG.md`
- [x] Flagship explainer — `release-v0.1/HOW-THE-SHATTERING-WORKS.md`
- [x] Checks/progression explainer — `release-v0.1/CHECKS-AND-PROGRESSION.md`
- [x] matt's-randomizer compatibility guide — `release-v0.1/USING-WITH-MATTS-RANDOMIZER.md`
- [x] Version-stamp patch — `patch_apworld_version_v01.py` (run on Windows)
- [ ] **Build a fresh `eldenring.apworld`** (`build.ps1 -Apworld`) — the checked-in
      one is stale. Windows.
- [ ] **Gen-test the shipping yaml once** on Windows (sandbox can't run AP gen) —
      confirm `EldenRing-Shattering.yaml` generates clean.
- **AP flower icon — DESCOPED from v0.1** (Alaric, 2026-07-04): the generator
  `build_ap_icon.py` is **lost**, and the icon is polish, not a functional blocker.
  v0.1 ships AP items with the vanilla **Telescope** icon (the working fallback).
  Rebuilding the flower is a point-release task (see Post-v0.1). So the empty
  `me3\ap-package\menu` and `package_release.ps1`'s icon warning are **expected**
  for v0.1 — not something to fix before the tag.
- [ ] **Assemble the release bundle** — run `.\package_release.ps1` (wraps the
      `eldenring.apworld`, the `me3/` runtime incl. the `ap-package` AP-icon
      override, the yaml, SETUP.md and CHANGELOG.md into
      `dist\ER-Archipelago-v0.1-*.zip`; ships a generic apconfig; PopTracker stays
      in the repo, not bundled; **warns if the
      AP-icon textures under `me3\ap-package\menu` are missing** — confirm they're
      staged on Windows, they read empty in the sandbox).
- [ ] **Repo hygiene before tagging** (public repo): add `genfuzz*` to
      `.gitignore`; confirm no `gensweep_*` / `ER_SPHERE_TIERS_*` / dump files are
      staged. Never `git add -A` blind.
- [ ] **Tag & release**: `git tag v0.1 && git push origin v0.1`, attach the bundle
      as a GitHub Release, paste CHANGELOG.

---

## 🟢 Post-v0.1 — not blockers

- Spirit Calling Bell fix (point release)
- Map-on-connect: switch to reveal-flags instead of item grants (cosmetic)
- Per-item AP descriptions; outgoing "Sent X to Y" banner
- Broaden playtest coverage of the newer options / longer `num_regions` seeds
- Tracker follow-ups (`SPEC-item-tracker.md` Phase 2+): screen-space panel pinned
  over the in-game map, robust hints via DataStorage, true world-map pins
- **Rebuild the AP flower icon**: recreate the lost `build_ap_icon.py` (ER
  `01_common` SB_Icon atlas edit for iconId 92), then `build.ps1 -Me3Deploy`.
  `regen_ap_icon.ps1` is parked and ready to drive it once the generator exists.

---

## Critical path to the tag

1. Windows: run `patch_apworld_version_v01.py`, then `build.ps1 -Apworld`.
2. Windows: gen-test `EldenRing-Shattering.yaml` once; eyeball the spoiler.
3. Repo hygiene pass; commit only the intended files.
4. Assemble bundle → `git tag v0.1` → GitHub Release.

Everything upstream of the tag that can be done off-Windows is done.
