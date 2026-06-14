# BRIEF: randomizer bake polish — pickup VFX glow (#12) + shop double-grant fix (#6)

Repo: **static randomizer** `SoulsRandomizers` (C#, build config `"Release (Archipelago)"`).
Contract-FREE (this changes regulation/param OUTPUT, not slot_data). Safe to run parallel with the
client + apworld briefs. SAME repo as `BRIEF-randomizer-bake-stability.md` → run that one in a
SEPARATE git worktree or sequence them. See BRIEF-PARALLEL-INDEX.md. TODO #12 and #6.

> LICENSING (do not skip): SoulsRandomizers fork is **PRIVATE ONLY** (thefifthmatt). Reimplement in
> our own C#; never vendor his decompiled source or config forks. Validate against local artifacts
> only.
> Build: `build.ps1 -Randomizer` then `-Bake -Deploy` (Windows). Every bake writes timestamped
> `ap_*_<ts>.txt` diags into `SoulsRandomizers/` — check `ap_diag`'s "items with NO PARAM ROW".

---

## Task A — visual glow on randomized-check pickups (#12)

One sentence: with `location_pool: lean` most world pickups aren't checks, so put a visible aura
(reuse the legendary/notable item VFX) on the pickups that ARE AP checks, so players know what's
worth grabbing.

**Research first (this is the unknown):** find how a world pickup's glow is driven. Candidates,
verify which actually controls the overworld treasure shimmer:
- `ItemLotParam` fields, or an `SpEffectVfxParam` / `SpEffectParam` on the placed asset (the enemy
  randomizer already does exactly this pattern — see `EnemyRandomizer.cs` ~1003–1018:
  `AddRow("SpEffectVfxParam", …, 51508)` + `AddRow("SpEffectParam", …, 13177)`; that's the proven
  "attach a VFX to a thing at bake" recipe to mirror).
- the item rarity field → built-in aura (legendary tier), if the treasure reads rarity.
Use the vanilla param dump `elden_ring_artifacts/vanilla_er/vanilla_er/*.csv` for any field/def
archaeology.

**Then:** at bake, tag each pickup that maps to an AP check with the chosen VFX. The bake already
rewrites these spots (item placement in `ArchipelagoForm.cs` shop/world branches ~454–547), so hook
the tagging where the AP item is written. Verify it shows on **all** check kinds — world treasure,
shop, gift, enemy drop — not just world treasure.

**Test:** bake a `lean` seed; in-game, checks glow and non-checks don't. Cross-check against
`apconfig.json` location list. Confirm no bake regression (ap_diag clean, no new NO-PARAM-ROW items).

**Out of scope:** a bespoke custom VFX asset (reuse an existing aura first); client-side rendering.

---

## Task B — fix own-world shop GOODS double-grant (#6)

One sentence: own-world GOODS sold in shops are granted twice (buy = grant #1 via the functional
synthetic copy; flag-poll echo = grant #2); make it a single grant.

**Root cause (already traced, TODO #6):** `ArchipelagoForm.cs` ELSE branch (~544) places own-world
GOODS via `writer.AddSyntheticCopy(original, replaceWithInArchipalago: original, …)` — a FUNCTIONAL
copy (shops can't suppress-on-pickup; see the comment block ~499–513). Buying it lands the real item
(grant #1); the purchase flag then trips flag-polling (~705) which echoes the own-world item
(items_handling=7) → client gibs it (grant #2). Non-GOOD shop items already use the placeholder
branch (`AddSyntheticItem`, ~454/513) so they don't double; foreign-player items sell a junk token.
It's specifically own-world GOODS.

**Fix (pick per the trade in TODO #6):**
- *Interim, single-repo, recommended to ship first:* drop the GOODS exception so own-world shop
  goods route through the **placeholder branch** (`AddSyntheticItem` … `replaceWithInArchipelago`)
  like non-GOOD items. Result: single grant (purchase → placeholder, echo → real item) + a lingering
  placeholder token UNTIL the client's `removeFromInventory` lands (that's `BRIEF-client-notify-
  cleanup.md` Task B — independent; the token auto-cleans once it ships). Strictly better than a
  double-grant today.
- *Proper (cross-track, no rush):* same placeholder routing here, and the client un-stubs
  `removeFromInventory` so the placeholder is pulled on echo → single grant AND no lingering token.
  This brief only needs the routing change; the client half is owned elsewhere.

**Watch:** the comment at ~499–503 warns the first weapon placed in a shop NPE'd `AddSyntheticCopy`
(Vagrant field lookup) once scope made shops resolvable — i.e. there's a real reason GOODS got the
functional-copy treatment. Confirm routing GOODS through `AddSyntheticItem` doesn't reintroduce that
NPE (test with a shop that sells an own-world good + a weapon).

**Test:** bake a seed with own-world runes/goods in a shop; buy one → it arrives EXACTLY once (watch
the client received-index log + inventory count). Foreign-player shop items and non-GOOD own items
unaffected. ap_diag clean.

**Contract:** none — regulation/param output only. Do NOT touch slot_data/apconfig/version range.
(The optional "tag shop locations in apconfig" variant from TODO #6 IS a contract change — out of
scope here; that would go through `BRIEF-contract-map-reveal`-style serialized handling.)
