# ER Archipelago — v0.2 Release Checklist

**Rewritten 2026-07-12.** The previous version was drafted 07-07 and had gone stale in *both* directions:
it listed blockers that were long since fixed, and marked "done" things that were broken (the shipped
yaml named a game that does not exist). It was read, not run.

> **The rule for this file: RUN the gate, don't read it.** Every ✅ below has a command next to it that
> was actually executed. If you can't run it, it isn't checked.

---

## Where v0.2 stands

**The last hard blocker is cleared.** The runtime param-rewrite suite — the riskiest thing in the repo,
3744 live lot rows rewritten on the assumption a suppressed placeholder still fires its acquisition flag —
**has now been played** (2026-07-12, client `e40f74e`), and it works:

```
check-lots: configured 3536 MAP + 208 ENEMY check lot(s); placeholder goods 8852
check-lots: blanked 3744 check goods slot(s) -> placeholder 8852   (0 missing from the named table)
shop-stock:  rerolled 455 infinite-stock slot(s) to consumables
enemy-drops: rerolled 2812 farmable goods slot(s)
flag-poll:   173 checks registered across the session
```

What remains is a short list of decisions, not unknowns.

---

## ✅ Verified (command shown; each was run)

| Gate | Evidence |
|---|---|
| Apworld unit tests | `pytest worlds/eldenring/tests` — **550 passed, 0 failed** |
| Fuzz clean | `python greenfield/fuzz_gf.py --count 6 --pass-pct 100` — **6/6, 0 FILLERROR / CRASH / HANG** |
| Shipping yaml generates | `Generate.py` on `release-v0.2/EldenRing.yaml`, **unmodified** → seed produced |
| Client builds + tests | client CI (Windows) — `cargo build` ✅, `cargo test` ✅ (304) |
| Apworld CI | `.github/workflows/tests.yaml` — `tests` ✅ + `generators` ✅ |
| Generated tables not stale | `generators` job fails on a non-empty `git diff` after regen — clean |
| No tracked clutter | `git ls-files` — no `_DELETE_ME`, `.orig`, `.rej`, `gendiag_*`, `genfuzz_*` |
| Old matt-lineage world retired | `git ls-files worlds/eldenring` — **0 files** |
| No game data / non-free content | `git ls-files` — no `.dcx`, `regulation.bin`, `.msb`, `elden_ring_artifacts/` |
| check_lots sound in-game | playtest log 2026-07-12 — 3744 blanked, 0 missing, 173 checks fired |
| Version handshake quiet | rebuilt client: **0** "version mismatch" errors (was 3/session) |

---

## 🔴 Blockers to the tag

### 1. The public repo is not cloneable by anyone but Alaric
`archipelago_rs` was a committed gitlink with no `.gitmodules` entry — **removed**, that one is done.
Still broken:

- [ ] **Every submodule url is SSH** (`git@github.com:…`). An anonymous `git clone --recurse-submodules`
      of a *public* repo cannot fetch any of them. → switch to `https://`.
- [ ] **`Paramdex`'s url is `.\Paramdex\`** — a literal Windows path, meaningless to git anywhere.

This is the one thing that makes v0.2 un-shippable *as a public repo*, independent of whether the game
works. A stranger following the README cannot get the source.

### 2. Decide: clippy debt
- [ ] ~45 style lints in `eldenring-archipelago` (`map_or`, `collapsible_if`, doc lists,
      `type_complexity`). **No correctness bugs.** Clippy is `continue-on-error: true` in client CI until
      they're cleared. Either clear them and re-arm the gate, or consciously ship with it advisory.

### 3. Windows-only gates (cannot be run from Linux/CI)
- [ ] `run_ci.ps1 -OnlyGreenfield` **100% green** — `num_regions` is the marquee mode; it does not get to
      be 99%.
- [ ] Final `build.ps1` producing the shipped `eldenring.apworld` + the client `.dll` from a clean tree.

---

## 🟠 Known, contained, shipping anyway

- **Vanilla-drop class** (ItemLotParam via the regular mob-drop channel). Fix is in; not yet
  playtest-verified. **No softlock risk by construction — it does not touch `progression_surface`.**
  Ship with it in KNOWN-ISSUES if the playtest doesn't land first.
- `KNOWN-ISSUES.md` needs a pass: **map-piece items, Spirit Calling Bell, flask double-grant and
  Torrent-mountless are FIXED** (playtested 2026-07-12) and should come off the active list.

---

## The one-line answer

Everything that can be verified without a human at a keyboard **is** verified. What's left is:
fix the submodule URLs, make a call on clippy, and run the two Windows gates.
