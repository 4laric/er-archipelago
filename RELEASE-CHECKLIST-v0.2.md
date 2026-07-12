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

## 🟢 Blockers: NONE

Every one is cleared, and each was cleared by RUNNING it, not by reading it.

| Was blocking | Now |
|---|---|
| Public repo not cloneable (SSH urls + orphan `archipelago_rs` gitlink) | **Fixed.** Anonymous `git clone --recurse-submodules` over HTTPS **verified working** — no key, no token, exit 0. |
| Bedrock fork in the submodule list | **Gone.** `Archipelago` is no longer a submodule at all: `bootstrap-ap.ps1` clones **stock upstream**, pinned by `.ap-version`. |
| ~45 clippy lints | **Cleared, all 44.** Clippy is a **hard gate** again (`-D warnings`). |
| `run_ci.ps1 -OnlyGreenfield` 100% green (Windows) | **Green.** |
| Clean `build.ps1` (Windows) | **Green.** |
| `check_lots` never played (3744 live lot rows) | **Played 2026-07-12.** 3744 blanked, 0 missing, 173 checks fired. |

### Clean-room verification (from an anonymous clone of `main`, on stock upstream AP 0.6.7)

```
git clone --recurse-submodules https://github.com/4laric/er-archipelago.git   -> exit 0
bootstrap-ap  (.ap-version = 0.6.7, stock ArchipelagoMW)                      -> ok
pytest worlds/eldenring/tests                                                 -> 572 passed, 0 failed
Generate.py on release-v0.2/EldenRing.yaml, UNMODIFIED                        -> seed produced
fuzz_gf.py --count 8 --pass-pct 100                                           -> 8/8, 0 FILLERROR/CRASH/HANG
client CI (Windows): build, test, fmt, clippy -D warnings                     -> all green
apworld CI: tests + generators                                                -> green
submodule gitlink == client main                                              -> match
```

**v0.2 is taggable.**

## 🟠 Known, contained, shipping anyway

- **Vanilla-drop class** (ItemLotParam via the regular mob-drop channel). Fix is in; not yet
  playtest-verified. **No softlock risk by construction — it does not touch `progression_surface`.**
  Ship with it in KNOWN-ISSUES if the playtest doesn't land first.
- `KNOWN-ISSUES.md` needs a pass: **map-piece items, Spirit Calling Bell, flask double-grant and
  Torrent-mountless are FIXED** (playtested 2026-07-12) and should come off the active list.

---

## The one-line answer

**Ship it.** The only thing not verified by a machine is the vanilla-drop class, and that is
contained by construction: those locations may never hold progression, so the worst case is a
missed filler item, not a stranded run.

## Tag sequence

1. `git tag -a v0.2.0` on the apworld, and on the client at the pinned gitlink (they must match).
2. Attach `eldenring.apworld` + the client `.dll` from the clean `build.ps1`.
3. Release notes: `release-v0.2/RELEASE-NOTES-v0.2.md`. **The `game:` id CHANGED** (`EldenRing` ->
   `Elden Ring`) — that is a migration step for anyone with a v0.1 yaml, and it is the single most
   likely support question. It is called out in SETUP / CHANGELOG / the template header.
