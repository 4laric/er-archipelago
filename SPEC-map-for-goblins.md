# SPEC — Map for Goblins integration

**Next stage (2026-09-05):** [Integrated F6 and MapForGoblins tracker](SPEC-integrated-map-tracker.md)
sets out the source-build path from the public 2.0.6 source and supplied 2.1.3 DLL.
This older document remains the historical companion-mod proposal.

**Status:** SPECCED 2026-08-26, on a verified artifact. Supersedes the K3 recon
(RECON-map-for-goblins, 2026-08-26) whose §1 identified the wrong package — see §2. Every claim
here is labelled VERIFIED (read from the binary/ini/license in the zip bobler linked, md5 below)
or CARRIED (survives from the recon, which measured the other edition) or OPEN.
**Owner:** Alaric rules. Phase A is implementable now behind one acceptance session on his box
(§6); phase C is the endgame and is deliberately not blocked on phase A.

---

## 1. The ask

Alaric, 2026-08-26: integrate Map for Goblins — "there's a couple versions around but bobler
linked me this one as the dll-only one that's matt-rando compatible."

## 2. The artifact, and the identity correction

VERIFIED. The package in hand is **Map For Goblins - DLL Edition v2.1.2** (VirusAlex,
2026-08-06), from the zip "Vanilla or Randomizer - v2.1.2":

| file | size | note |
|---|---|---|
| `MapForGoblins.dll` | 6,801,920 B, md5 `6d14ddc64182fa49e80c5ea5b5825645` | the whole mod |
| `MapForGoblins.ini` | 10,760 B | schema-synced config; the DLL re-writes it on launch |
| `LICENSE.txt` | MIT-style (copy/modify/merge/publish/distribute/sublicense with notice) | |
| `README.txt` | install docs for me3 / ME2 / EML | |

README, verbatim: "~6900 loot & world-map icons. **No regulation.bin changes.** Pure DLL - no
gfx or other extra files."

🛑 **The K3 recon analyzed a different lineage**: Map for Goblins v1.16 (Harmonixer, Nexus 3091,
Oct-2024), the file-based edition that ships `regulation.bin` + `02_120_worldmap.gfx` + msgbnds
+ a talk-script menu, and asserted "the file Alaric has is current [v1.16]". It is not the file
Alaric has. Carry-over of the recon's findings:

| recon section | verdict here |
|---|---|
| §5.1 regulation version skew ("the big one") | **VACATED** — no regulation ships; the DLL reads the loaded one |
| §5.2 matt's-randomizer file conflict + Smithbox merge | **VACATED** — nothing to merge; reading matt's live regulation is WHY it is matt-compatible |
| §5.3 "icons name the vanilla item, confidently wrong" | **REFUTED for this edition** — see `live_loot_*`, §3 |
| §6B port-forward graft tool | **UNNECESSARY** |
| §4 client param census (client never reads `WorldMapPointParam`) | **CARRIED** — still the load-bearing compatibility fact |
| §4 AP-flower iconId-92 disjointness | **CARRIED** |
| §6C native endgame design | **CARRIED**, margin re-priced in §7 |
| EXACT/INDICATIVE method discipline | worth keeping as house style for recon docs |

## 3. Verified mechanism (binary + ini)

- **Markers are `WorldMapPointParam`-driven and game-drawn.** Strings: `02_120_worldmap`,
  `Marker dump: WorldMapPointParam not available - live marker list skipped`, `Marker dump: {}
  row(s) could not be placed on the overworld`. The DLL evidently appends/patches rows at
  runtime; the game's own map renders them. No gfx file needed (README says so; the strings'
  placement-conversion complaints corroborate a runtime pipeline).
- **The randomizer mode is native to it.** Ini keys, all defaulted ON in this package:
  - `live_loot_flags = true` — "Hide loot markers using the pickup flag from the loaded
    regulation, so they disappear correctly under the Item/Enemy Randomizer or other regulation
    mods."
  - `live_loot_labels = true` — "Relabel each loot marker with the item its lot currently gives."
  - `live_loot_icons = true` — icon + category follow the lot's current content.
  - `anonymous_loot = false` — "Spoiler-free: every loot marker shows a gray '?' and a generic
    label ... markers still hide on pickup."
- **The overlay is opt-in and OFF by default.** `menu_render_mode = native` — "the in-game menu
  the game draws itself; **the overlay is not created at all**." The ImGui 1.90.9 / dxgi-shadow
  machinery (imports: d3d12, dxgi, D3DCOMPILER_47; `overlay_dxgi_shadow.cpp` in strings) exists
  only for `menu_render_mode = imgui`, and the ini's own text offers `menu_enabled = false` as
  the escape for "a DX overlay conflict (Steam overlay / RTSS / GeForce Experience)".
- Quality-of-life that matters to us: `require_map_fragments = true` (icons gated on map
  discovery), `location_emphasis` (own-map vs other-map marker separation), F10 / Y+R3 menu,
  per-category `show_*` toggles, schema-synced ini (safe across updates).
- Loader support: me3 `[[natives]]` (README's recommended path — ours), ME2 `external_dlls`,
  EML with `load_delay = 0` (its 5s default loads after map build and the icons never inject —
  see §6 check 2 for why this timing note matters to us).

## 4. Why it composes with the archipelago stack

- **Param disjointness (CARRIED).** Our client reads BonfireWarpParam, ShopLineupParam,
  ItemLotParam_*, EquipParam*, SpEffectParam and never touches `WorldMapPointParam`. MFG's
  entire payload lives in the table we never read. Its reads of ItemLotParam are reads.
- **Our repoint is its truth.** The client repoints ground lots in memory and the lot's
  acquisition flag IS the check flag. Therefore, with `live_loot_flags` on, an MFG marker hides
  exactly when the check sends; with `live_loot_labels`, the marker names the check ware
  (post-#937, our named shop/check wares). ~6,900 world-lot markers become "uncollected check
  sites on the world map" with zero code on either side.
- **matt's stack.** No file collision (no files). MFG reads the loaded regulation — matt's,
  when matt's is in the stack — live. This is bobler's compat claim, and it holds by
  construction. me3 profile order still needs stating, not assuming (§6 check 4), because
  matt's tool ignores our profile.
- **The flower.** Our one file asset repaints iconId 92 only; zero of the file-edition's 6,905
  rows referenced iconId 92 (CARRIED) and there is no reason the DLL edition differs — but §6
  check 1 eyeballs it anyway since the row set is now runtime-generated.

## 5. Phase A — ship it as a companion (the near-term shape)

1. **Distribution:** include the DLL edition in the player bundle as an OPT-IN, with
   LICENSE.txt alongside verbatim (the license permits it). NOT in the bare apworld. The me3
   profile gains a commented-out `[[natives]]` entry (or a second profile variant
   `ap-goblins.me3`) — decide in review; the commented entry is the smaller surface.
2. **AP settings preset:** ship a recommended `MapForGoblins.ini` (or a documented diff):
   `live_loot_flags/labels/icons = true` (already this package's default), and the one
   deliberate choice — **`anonymous_loot = true` as the AP-recommended default**: a map of
   "somewhere here is an unclaimed check" without naming what our repoint put there. Players
   who want labels flip one key. `menu_render_mode = native` stays (no second overlay).
   `require_map_fragments` stays true (it composes with region locks: fragments are checks).
3. **Docs:** SETUP.md section (install, the offline/EAC note is already in their README; ours
   adds "works with the AP client and matt's rando; icons = world pickups only — enemy drops,
   boss/event awards, shops and talk rewards have NO marker" — the §7 corpus honesty).
4. **Support boundary:** their Discord for mod bugs, ours for AP bugs; the SETUP section says
   which is which. We do not fork, patch, or rehost modified builds under this spec.

Non-goals for A: no wizard surface, no contract/option, no client code, no world code. A is a
distribution + docs change gated on §6.

## 6. The acceptance session (Windows, Alaric's box, one sitting)

Run with the AP client + MFG in one me3 profile, a real seed:

1. **Coexistence:** launch, connect, open the map. Expect: markers render, our overlay renders,
   no D3D12 first-chance crash (our known crash class), flower icon intact. Then set
   `menu_render_mode = imgui` and repeat once — that is the risky mode; record, don't rely.
2. **Repoint timing:** with `live_loot_labels` on, note a specific marker's label BEFORE
   connecting, connect (lots repoint), reopen the map. Expect the label to update on map
   reopen (the ini says some options apply "on the next map open"). If it never updates until
   restart, A ships with `anonymous_loot = true` mandatory in the preset and the timing goes to
   §8 opens.
3. **Flag-hide on a check send:** pick up a ground check; the marker must disappear on the next
   map open. This is the load-bearing behavior; one check suffices, two is better (one
   overworld, one dungeon).
4. **matt three-way:** matt's rando + MFG + AP client in the documented stack order. Markers
   should reflect matt's shuffled lots where we did not repoint, ours where we did. Ten minutes
   of spot-checking, screenshot the map.
5. **Tarnished survival (time-boxed, 08-28 is two days out):** after the patch, does the DLL
   load and place markers? A live param reader SHOULD be patch-proof, but it hooks game code we
   have not seen; if it dies on the new exe, A's docs say "wait for upstream" and nothing in
   our stack is affected — which is the point of A's shape.

Record verdicts in this file (the ability-lock spec's probes-ANSWERED pattern).

## 6.5 Phase B — ware-icon signalling (OPEN, probe-gated)

Alaric's ask, 2026-08-26: "any custom coloring of hinted checks? progression_surface?"

MFG has no per-marker API — its only colour knobs are the own/other-map emphasis fade. But with
`live_loot_icons`/`live_loot_labels` the marker's icon, category and label follow the LOT'S
CURRENT WARE'S params, and the client writes those ware rows. So state can be encoded in what
MFG already reads:

- **progression_surface (static, per-seed):** bake surface-eligible check wares with a distinct
  iconId / goodsType class at repoint time. If MFG's classifier keys on goodsType, those markers
  land in their own MFG category and players can isolate them with MFG's OWN category toggles.
- **hinted (dynamic):** when a hint lands, the client rewrites that check ware's iconId in the
  live params (the minibaker write precedent). Works iff MFG re-reads on map open — the same
  question as §6 check 2, one probe answers both.

Probes before any build: (1) flip one check ware's iconId live, reopen the map — does the marker
change? (2) what does MFG's classifier actually key on (goodsType? EquipParam table? icon id
ranges?) — determined empirically, two ware edits and a map open. Costs and limits, stated:
mutually exclusive with `anonymous_loot` (it overrides labels AND icons — spoiler-free or
class-signalling, per player, not both); gaming a third-party classifier, so it can break on any
MFG update (the SETUP note should version-pin the recommendation); icon-as-colour, not true
tinting — in-logic/out-of-logic colouring stays phase C.

## 7. Phase C — the native endgame (CARRIED, re-priced)

The recon's §6C design survives as the roadmap item: the client appends its own
`WorldMapPointParam` rows at runtime (param_guard row access + the minibaker live-write
precedent), keyed to check acquisition flags, from a world-emitted
`checkId -> (map point, icon, flag)` contract table (the region_open_flags emission pattern;
coordinates exist — item_grace_coords + the play-region spine).

What C buys **over a working phase A**, honestly:

- markers for the non-lot corpus (EMEVD awards, enemy drops, shops, talk/gesture awards — the
  same split every audit this week kept hitting; MFG structurally cannot mark these);
- tracker-state coloring (in-logic vs out-of-logic vs hinted — F6 on the map);
- no third-party closed binary in the trust chain, no upstream patch dependency.

What C costs: the icon sheet (flower pipeline is the precedent), a config surface (overlay
panel), placement conversion for interiors (MFG's own "could not be placed on the overworld"
strings show that pain), and maintenance forever. C is worth doing when the non-lot corpus or
logic coloring is the ask; it is not worth doing to replace what A already does.

First probe for C, unchanged from the recon: does the pinned `eldenring` crate bind
`WorldMapPointParam`, and is row-APPEND (not just patch) safe at runtime? Read the pinned
checkout before promising.

## 8. Open questions

- §6 check 2's answer (label refresh cadence) — decides the preset.
- Whether the DLL's own map-fragment gating reads flags we manipulate (region unlock granting
  fragments?) — if a region Lock grants map fragments, icons bloom with the region: pleasant,
  but verify it does not bloom EVERYTHING.
- The DLL edition's provenance vs the Nexus lineage (VirusAlex vs Harmonixer; strings reference
  "Elden Ring Reforged" and an ERR-adjacent build path). Cosmetic for A given the license text
  in the zip, but worth one look at where v2.x is published before we link it in SETUP.md.
- Per-icon state beyond hide (collected vs in-logic coloring) needs upstream cooperation or
  phase C — parked.

## 9. Not verified

- Anything about the file-based editions (v1.16, Expanded) — out of scope; A uses neither.
- The DLL's hook sites (no disassembly beyond imports/strings). The acceptance session is the
  instrument.
- EML path — unsupported by us; me3 only.
