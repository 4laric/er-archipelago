# ER Archipelago — Release Checklist

*Snapshot 2026-06-17. Status reflects the in-game verification pass on the stacked-patch batch.*

---

## ✅ Verified green — no action needed

The scary "compiles but untested" pile is mostly gone. Confirmed working in-game:

- Crash-on-save-load fix (SEH-wrapped auto_upgrade race)
- auto_upgrade (correct ER reinforce model)
- Progressive tier persist (bell double-grant fix)
- Start-items dedup (Torrent/flask re-grant loop fix)
- Grace-flag flush in-world (leveling + First Step/Roundtable in warp menu)
- quick_start (Lord's Runes at start)
- Bell overflow → Lord's Rune + `progressive_bell_count`
- Progressive stone bells (client)
- DLC auto-entry (Chapel latch → Gravesite)
- Pool builder
- `dlc_gear_curation`
- `filler_replacement`
- `trimmed` location_pool
- Region locks — **warp-enforced** (not honor-system); core loop; native-style notifications; grace bundles on receipt

---

## 🔴 Blocks v1 — must fix or finish

- [ ] **Summoning / companion bell bug.** Spirit Calling Bell still unusable in-game — the one true *functional* blocker (gates summoning). Chase and fix.
- [ ] **Finish Godrick + Messmer goal playthroughs.** Both in progress — confirm the goals actually complete end-to-end.
- [ ] **Implement map-flag rule** (decision made): grant-on-obtain when `region_lock` is ON (region map = unlock token), grant-all otherwise.
- [ ] **Confirm grace arena-exclude.** "So far so good" — needs a final pass to call it green.
- [ ] **Capture the last few region IDs.** Small chore; write down the full set so all intended regions are lockable.

---

## 🟡 Decide: ship in v1 *or* flag experimental

These work in principle but aren't playtested. Quick playtest → include; otherwise gate behind an "experimental" label so v1 stays trustworthy.

- [ ] Progressive consumables (flasks / seeds / tears / scadutree)
- [ ] `lean` location_pool (note: `trimmed` is verified, `lean` is not)
- [ ] Liurnia Caves bundle lock

---

## 🟢 Post-v1 polish — not blockers

- [ ] AP item icon override (verified broken — rework, or ship with the default icon)
- [ ] Per-item descriptions on AP items (not implemented)
- [ ] Outgoing "Sent X to Y" on-screen banner (console line exists; banner doesn't)

---

## ⛔ Non-code gates — the real release blockers

The code is basically not what's standing between you and a public release. These are:

- [ ] **Licensing.** The forked C# randomizer/baker (thefifthmatt's SoulsRandomizers) is **source-available but explicitly not freely licensed** — its README says *"Do not distribute the randomizer, forks of the randomizer programs, or forks of config files."* This gates any public distribution that includes the baker fork. (Good news: the **client is MIT**, **SoulsIds is Apache-2.0**, **Archipelago is MIT** — those are freely redistributable.) See the licensing notes below / discuss before any public drop.
- [ ] **Confirm the apworld's own license** with its upstream author (lBedrock lineage) — likely permissive (AP ecosystem), but verify before shipping it as a download.
- [ ] **Packaging / distribution.** A real release needs: a fresh `eldenring.apworld` build (the checked-in one is stale), the client, **one known-good template yaml**, and a short setup guide. Right now `build.ps1` is a dev pipeline, not an installer.
- [ ] **Pick the v1 scope cut.** Ship the verified-green subset; park the rest behind "experimental."

---

## Critical path

1. Fix the summoning-bell bug.
2. Land the Godrick/Messmer playthrough confirmations + the map-flag rule.
3. Resolve the licensing question (this decides *whether* a public release is even the move vs. a private build).
4. Package: fresh apworld + client + one config + setup guide.

Everything else is polish or a quick yes/no scope decision.
