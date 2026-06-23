# Memory index

> Live project board (kanban, prioritized) at C:\Users\alari\Documents\er-archipelago\er-archipelago-kanban.html — rebuilt weekly from this index. Keep statuses here current so the rebuild stays accurate.

## Working style & environment (durable)
- [Builds solo, undershoots outreach](alaric-builds-solo-undershoots-outreach.md) — does deep solo build brilliantly but stops short of community/upstream outreach; surface that angle EARLY
- [Don't use AskUserQuestion](dont-use-askuserquestion.md) — slow, has killed long sessions; ask clarifying Qs inline as prose
- [Verify files before naming](verify-files-before-naming.md) — confirm files/commands exist; always give full paths
- [Don't assert patch-state from mount](dont-assert-patch-state-from-mount.md) — verify on Windows; trust only POSITIVE finds
- [Local gen from source not apworld](er-local-gen-from-source-not-apworld.md) — gen runs from worlds/eldenring/ SOURCE; verify patch-state from source, not zip/mount
- [ER patches run on Windows](er-patches-run-on-windows.md) — ⛔ NEVER edit __init__.py/apworld directly; write patch_*.py for Alaric to run on Windows; verify via Read
- [CRLF edit truncation](crlf-edit-truncation.md) — Edit tool truncates CRLF source; patch via Python + verify on disk
- [Bash read truncation](bash-read-truncation.md) — sandbox bash can silently truncate large-file reads; verify length/braces
- [ER mount write truncation](er-mount-write-truncation.md) — Write/Edit truncates/null-bytes larger mount files; build in /tmp, cp, verify bytes
- [Mount error → hand off patch](mount-error-hand-off-patch.md) — mount error on a patch → stop, hand to Alaric; don't re-write to "fix"
- [Sandbox mount no-unlink](sandbox-mount-no-unlink.md) — mount blocks rm/unlink (rename+overwrite OK); drive git via /tmp index, commit on Windows
- [ER sandbox git sync](er-sandbox-git-sync.md) — sync repos via GitHub HTTPS+PAT (SSH blocked); re-paste token each session
- [Parallel shared-doc clobber](parallel-shared-doc-clobber.md) — don't co-edit shared docs in parallel; per-track files, reconcile serially
- [Always timestamp dump files](always-timestamp-dump-files.md) — every dump gets a timestamp-in-filename version, even one-offs
- [Don't trust un-timestamped files](dont-trust-untimestamped-files.md) — ground truth = generated spoiler; gendiag dumps resolved options
- [AP zip seedname≠seed](er-ap-zip-seedname-vs-seed.md) — AP_<name>.zip filename ≠ spoiler's internal Seed:; match runs by reading inside the zip
- [build loop UX fixes](er-build-loop-ux-fixes.md) — -Generate hangs on gen error (AP_NONINTERACTIVE); baker headless arg
- [Repo cleanup tool](er-repo-cleanup-tool.md) — cleanup_repo.ps1 (dry-run default) purges cruft + archives finished one-offs

## Project structure, build & infra (reference)
- [ER project structure](er-archipelago-project-structure.md) — THREE repos (apworld, randomizer, runtime client)
- [ER dev environment](er-dev-environment.md) — gen/test/build commands; sandbox can't run AP (needs Python 3.11+)
- [ER -Clean -All convention](er-build-clean-all-convention.md) — default full clean build on real change; kill stale :38281 first
- [ER randomizer build recipe](er-randomizer-build-recipe.md) — deps/pins/patches to build SoulsRandomizers Release
- [ER client build speed](er-client-build-speed.md) — slow client build = Core.h→apclient header soup; /MP + LTCG-off + -NoClient
- [ER apworld packaging](er-apworld-packaging.md) — build.ps1 -Apworld zips worlds/eldenring→eldenring.apworld
- [ER ecosystem upstreams](er-ecosystem-upstreams.md) — upstream=lBedrockl (DLC-complete); thefifthmatt licensing landmine on rando forks
- [ER thefifthmatt upstream path](er-thefifthmatt-upstream-path.md) — distribution blocked by forked diste (DLC-ported derivative of his configs); clean path = rebase ~3k-line AP overlay onto his DLC source; outreach plan
- [ER FromSoft AP ecosystem](er-fromsoft-ap-ecosystem.md) — fswap consolidated client repo lists ER as PLANNED; contacts (nex3 Mastodon/GitHub, fswap); DS3 forks LukeYui not thefifthmatt, Sekiro is the real precedent
- [Nightreign AP = Hades pattern](nightreign-ap-hades-pattern.md) — de-escalating-scaling-as-checks idea = port of Polycosmos "Reverse Heat"; distilled location/goal/winnability template + Nightreign mapping
- [ER yaml overrides -Enemies flag](er-yaml-overrides-enemies-flag.md) — yaml enemy_rando overrides build.ps1 -Enemies
- [ER deploy hygiene gap](er-deploy-hygiene-gap.md) — build.ps1 deploy overlays w/o purge; stale MSBs leak; fix=tools\deploy_hygiene.ps1
- [ER event flag validity](er-event-flag-validity.md) — flags GROUP-allocated; invented ids no-op; probe set→readback; 62xxx/71-76xxx valid
- [ER ?EventTextForMap? failsafe](er-eventtextformap-failsafe.md) — in-game ?Tag? = regulation.bin vs deployed msg mismatch; fix=full restart + clean redeploy
- [ER sphere dump tooling](er-sphere-dump-tooling.md) — reachable-checks-per-sphere via ER_DUMP_SPHERES; ER emits spoilers
- [ER location id map](er-location-id-map.md) — canonical AP location id↔name via exec'ing locations.py w/ stubbed imports
- [ER filldiag tool](er-filldiag-tool.md) — ER_DUMP_FILL dumps adv/priority/slack/per-region; gen_sweep -Seeds reproduces
- [ER apworld key mismatch](er-apworld-key-mismatch.md) — MASTER LOG: bake pipeline debugging; dev-loop tools + ap_* diags
- [ER seed-archive convention](er-seed-archive-convention.md) — park/resume a playable seed across rebakes; seeds-archive/ + .ps1
- [ER baker reads slotdata live](er-baker-reads-slotdata-live.md) — baker pulls options from :38281 slot_data, not yaml/zip; stale binary silently applies old
- [ER fill-regression suite](er-fill-regression-suite.md) — gen-test fill-regression-yamls + run_fill_regression.ps1 gate

## 🔴 Broken in-game (active)
- [ER AP icon override](er-ap-icon-override.md) — InjectApItemIcon telescope swap BROKEN per playtest (P1)
- [ER spirit bell flag](er-spirit-bell-flag.md) — Spirit Calling Bell still unusable in-game despite obtained flag 60110 (P1)
- [ER DLC lock notifications](er-dlc-lock-notifications.md) — notifs don't fire for DLC region locks; likely b/c many DLC locks share one map piece (m61) (P2, NEW 2026-06-23)

## 🟠 Next up — ready to build/bake (patch written)
- [ER kick kill-keep-runes](er-kick-kill-keep-runes.md) — ONLY outstanding region-lock bug: break-lock kills player but STILL loses runes; patch flips Should Receive Runes→TRUE, baker rebuild+rebake only (P1)
- [ER bake slotdata timeout](er-bake-slotdata-timeout.md) — sync GetSlotData times out; fix=request at login; NOT done, rebuild+rebake (P1)
- [ER natural-key triggers impl](er-natural-key-triggers-impl.md) — 4 patches (Mountaintops/Snowfield/Altus blooms + Spelunker torches + Rold 400001); apply+build pending
- [ER Mountaintops lock design](er-mountaintops-lock-design.md) — DECISION Option B (keep Rold, gate bloom on Rold+Morgott dead 11000800); ships with triggers
- [ER Snowfield lock split](er-snowfield-lock-split.md) — opt-in snowfield lock (101/130 checks); patch written, needs run+gen-test
- [ER chokepoint locks impl](er-chokepoint-locks-impl.md) — gate legacy back-half on choke-boss drop (Godskin Duo+Loretta); needs build+gen-test
- [ER DLC catacombs lock](er-dlc-catacombs-lock.md) — opt-in dlc_catacombs bundles Fog Rift+Belurat Gaol (41 checks); needs gen-test
- [ER dlc_only chain](er-dlc-only-chain.md) — Phase 1 (messmer) generates; Phase 2 full-tree patch written
- [ER hint full region names](er-hint-full-region.md) — extend_hint_information spells out parent_region.name; NOT implemented yet, needs run+gen-test
- [ER furnace pot injection](er-furnace-pot-injection.md) — furnace_pot_count seeds Hefty Furnace Pots into DLC seeds; written, needs run
- [ER furnace golem scaling](er-furnace-golem-scaling.md) — c5170 golems opt out of tier-1 fallback; patch needs Windows build+bake+walkup
- [ER Messmer kindling cap](er-messmer-kindling-cap.md) — baker raises goods 2008021 maxNum to 99; uncommitted
- [ER soft-consumable cleanup](er-soft-consumables.md) — soft_consumable_shop + derandomize_gurranq; patch+spec, shop side needs baker
- [ER dlc_gear_curation](er-dlc-gear-curation.md) — swap worst base gear 1:1 for best S/A DLC gear; needs gen-test
- [ER trimmed curation impl](er-trimmed-curation-impl.md) — curation.py cut lists + _in_location_pool; needs gen-test
- [ER trimmed forbid_useful shortage](er-trimmed-forbid-useful-shortage.md) — trimmed+forbid_useful fails 'not enough filler'; fix=both allow_useful
- [ER trimmed lock-spill](er-trimmed-lock-spill.md) — trimmed dlc_only spills all region locks to start; location_pool=all fixes it

## 🔵 In progress (partial)
- [ER completion scaling](er-completion-scaling.md) — geographic pass PLAYTEST-VALIDATED; sphere-basis bridge wired but resolver coverage partial, not bake-validated (P1)
- [ER boss scaling tiers](er-boss-scaling-tiers.md) — 23 DLC bosses model-keyed; gen-tested + scaling-diag validated; only remaining = playtest for feel (P2)
- [ER random start region](er-random-start-region.md) — apworld+baker+client done & bake-confirmed (lands Caelid); in-game latch pending
- [ER random-start Roundtable hub](er-random-start-roundtable-hub.md) — re-root hub to Roundtable; apworld re-root pending (graph Limgrave-rooted)
- [ER notify item source](er-notify-item-source.md) — 'X from Y': data threaded through queue; pending build
- [ER auto_equip spec](er-auto-equip-spec.md) — apworld half done; gap=client equipItem stub (RE ChrAsm equip fn)
- [ER yaml comprehension layer](er-yaml-comprehension-layer.md) — annotated ref + er_yaml_lint.py built; pregen wiring + docstring discrepancy open
- [ER poptracker dlc_only](er-poptracker-dlc-only.md) — auto-clears non-DLC + Land of Shadow map; map needs DLC re-dump
- [ER DLC area_ids](er-dlc-area-ids.md) — 4 interior DLC regions wired; overworld m61 tiles need in-game place-name capture
- [ER enemy-drop tagging](er-enemy-drop-tagging.md) — tag enemy-dropped checks via `enemy cXXXX_YYYY`; pure enemy-lot vs event-enemy

## 🟣 Backlog — specs / ideas
- [ER trap items](er-trap-items.md) — AP traps (summon bears/warp/freeze); mine Crowd Control mod; not started
- [ER control randomizer](er-control-randomizer.md) — Skumnut special: start gimped, unlock controls (look-left/roll/double-jump) as AP items; client input-mask subsystem; spec-only, lowest pri
- [ER boss-kill grace + fog audit](er-grace-bundle-boss-arena.md) — follow-up to boss-arena fix: sweep EMEVDs/MSBs for graces that appear on boss kill + for fog walls
- [ER run trimmed mode](er-trimmed-audit.md) — operational todo: haven't run trimmed mode in a while; do a regression run (trimmed measured 2498, DLC 573)
- [ER num_regions chain spec](er-num-regions-chain-spec.md) — breadcrumb locks into 1..N chain for sphere gradient; stubs only
- [ER Oops All Legacy Dungeons](er-oops-all-legacy-dungeons.md) — chain legacy dungeons by grace-warp, delete open world; SPEC
- [ER global scadutree blessing spec](er-global-scadutree-blessing-spec.md) — DRAFT: fragments as game-wide power curve; crux=persist stored level
- [ER pool builder](er-pool-builder.md) — compose pool to a target size from a ranked ladder; junk_retention knob; SPEC
- [ER check-trim spec](er-check-trim-spec.md) — drop checks both bad-tier AND remote; somber far-cut wired; grace-proximity needs coords
- [ER relevance-uplift spec](er-relevance-uplift-spec.md) — dlc_only: swap DLC filler for base-game juice; mirror of dlc_gear_curation; SPEC
- [ER progressive consumables spec](er-progressive-consumables-spec.md) — progressive Tear/Seed/Scadutree/Revered Ash + glovewort bells; Roderika flags need extraction
- [ER map-grant region tracker](er-map-grant-region-tracker.md) — region MAP item=unlock token + tracker; long-term
- [ER in-game check indicators spec](er-ingame-check-indicators-spec.md) — enemy ghost-glow SpEffect + scarab audio cue; SPEC
- [ER snowfast QoL](er-snowfast-feature.md) — port thefifthmatt Mountaintops shortcuts; impl decision pending
- [ER merchant bell-bearing logic](er-merchant-bell-bearing-logic.md) — gate merchant shop checks behind their Bell Bearing; idea
- [ER Moore shop rando idea](er-moore-shop-rando-idea.md) — already randomized in gen; in-game access issue (Bell Bearing 2008900 skip=True kills route)
- [ER QoL Patches shop + refresh](er-qol-patches-shop.md) — Patches Murkwater shop needs reload; general shop-refresh-on-unlock
- [ER natural-key locks](er-natural-key-locks.md) — use vanilla keys as region locks (Academy/Dectus/Rold/Haligtree/Irina); broad SPEC
- [ER great_runes_present](er-great-runes-present.md) — force extra great runes into num_regions pool; default 0=no change
- [ER Stormveil Rusty Key follow-ups](er-stormveil-rusty-key-falsegate.md) — over-gate removed; Margit Shackle + Liurnia/Caelid Rusty Key rules pending
- [ER bake warnings audit](er-todo-bake-warnings-audit.md) — triage all warnings in a full bake; backlog
- [ER next deliverable: DLC enemy rando](er-next-deliverable-dlc-enemy-rando.md) — unstrip DLC maps for enemies only; check fork config first
- [ER ruins sweep PARKED](er-ruins-sweep-parked.md) — overworld ruins not discrete objects; revive via hand-curated list; DLC ruins ship
- [ER lean-check curation wishlist](er-start-items-randomize-request.md) — force-keep start fingers/early stones/chest weapons as lean checks; `chest` tag is the lever
- [ER FogMod region-lock direction](er-fogmod-region-lock-direction.md) — replace play-region KICK w/ baked flag-gated fog WALL; +Liurnia Caves=1 lock over 8 dungeons
- [ER region-lock physical enforcement](er-region-lock-physical-enforcement.md) — fog-wall enforcement belongs in BAKER (EMEVD gated on region_open flag), not client
- [ER boss attribution spec](er-boss-attribution-spec.md) — SPEC for the (now-shipped) boss attribution; every check→one boss DefeatFlag

## Open bug notes / gotchas (reference)
- [num_regions chain host reach](er-numregions-chain-host-reach.md) — chain breadcrumb host parks locks in gated interiors → FillError; fix=reachability-filter cands
- [num_regions pool strands Leyndell](er-numregions-pool-strands-leyndell.md) — rune_source=pool seals Altus→Leyndell; unblock=rune_source:regions
- [num_regions pool+chain Limgrave](er-numregions-pool-chain-limgrave.md) — pool+chain rolled Limgrave → 2 start locks; fix excludes Limgrave from the chain roll (patch written, needs Windows run)
- [_can_go_to warp / Radahn festival](er-cango-warp-radahn-festival.md) — _can_go_to checks geographic entrance not region-reach; fix=setflag festival in baker (flag UNCONFIRMED)
- [ER key-item obtained flags](er-keyitem-obtained-flags.md) — client grants goods but skips vanilla obtained-flag; Rold Medallion=400001; full 4000xx table
- [ER DLC-only spec](er-dlc-only-spec.md) — SPEC-dlc-only.md; DLC check count 1207; access crux A transit vs B DLC-start
- [ER rune-skip injectable room](er-rune-skip-injectable-room.md) — create_items demand-drops small Golden Runes to fit region locks; fixes DLC-off overflow deadlock
- [ER Ashes of War tiers](er-ashofwar-tiers.md) — PvE tiers for all 105 transferable AoW in item_tiers; feeds injection

## ✅ Done / shipped (2026-06-23 status)
- [ER runtime client port](er-runtime-client-port-status.md) — pickup→grant→location check working end-to-end
- [ER Godrick goal](er-godrick-goal.md) — ending_condition=godrick verified in-game
- [ER num_regions](er-num-regions.md) — randomized region count for ~3-4hr runs; TESTED GREEN
- [ER DLC mini-campaign](er-dlc-mini-campaign-spec.md) — ending=messmer, 24 kept/20 sealed; rigorously tested green; Alaric's main DLC mode
- [ER DLC auto-entry](er-dlc-autoentry.md) — Chapel latch→baked warp + Roundtable grace; worked completely smoothly first try
- [ER region fusion](er-region-fusion.md) — region_lock + grace bundle DONE & playtested (dlc_only Gravesite-grace-at-start was the m61 layer FAIL)
- [ER slotdata areaLockFlags](er-slotdata-arealockflags-drop.md) — fixed; region lock LIVE & confirmed working in-game
- [ER grace rando](er-grace-rando.md) — WORKING in-game; residual UX: empty check spots + reuse for boss sweep (see board k21/k22)
- [ER dlc_only region-lock](er-dlc-only-region-lock.md) — gen-test passed
- [ER bundle-lock graces](er-bundle-lock-graces.md) — bundle locks now grant warp grace; closed out
- [ER grace bundle boss-arena warp](er-grace-bundle-boss-arena.md) — grace_arena_exclude; closed (follow-up audit in backlog)
- [ER shackle dlc_only inject](er-shackle-spiritspring-lock.md) — Margit's/Mohg's Shackle into UPLIFT_UNIQUE_CAPS; playtest-validated
- [ER boss attribution impl](er-boss-attribution-impl.md) — BossAttribution.cs + sweep emit; verified in-game
- [ER auto_upgrade](er-auto-upgrade-noop.md) — implemented (live highest, normal/somber separate); verified in-game
- [ER progressive stone bells](er-progressive-stone-bells.md) — fully implemented apworld+client behind default-OFF
- [ER progressive physick](er-progressive-physick-spec.md) — validated; residual = duplicate tears in pool (low-sev, dedupe in create_items)
- [ER physick grant crash](er-physick-goodslist-grant-crash.md) — FIXED (client rebuilt); was killing ALL grants
- [ER bell overflow rune](er-bell-overflow-rune.md) — extra bell copies past max→Lord's Rune
- [ER Torrent start grant](er-torrent-start-grant.md) — startItems goods 130 + flag 60100; tested green
- [ER quick_start option](er-quick-start-option.md) — dlc_only grants 71 Lord's Runes at start; validated
- [ER early leveling](er-leveling-enable-flag.md) — skip-Melina flags 4680+951 shipped
- [ER options consolidation](er-options-consolidation.md) — 84 fields→12 groups (presentation-only); done
- [ER priority locations](er-priority-locations.md) — important_locations priority-fill; done
- [ER important_locations scope](er-important-locations-scope.md) — num_regions/Enia-aware + per-region headroom; gen passed
- [ER questline de-randomization](er-questline-derando.md) — locks optional NPC quests at vanilla; tested green
- [ER spell trim keep](er-spell-trim-keep.md) — 57 S/A spell tiers + HIGH_TIER_SPELLS keep; validated
- [ER ammo filler guard](er-ammo-filler-guard.md) — arrows/bolts excluded from filler→useful promotion
- [ER filler_replacement option](er-filler-replacement.md) — swap filler for runes or stones+runes; count-neutral
- [num_regions priority reach-prune](er-numregions-priority-reach-prune.md) — pre_fill max-state prune; 40/40 green
- [num_regions fill overflow](er-num-regions-fill-overflow.md) — 4 demotion patches for spine-seal "No more spots"
- [soft_progression × bell gate](er-softprog-bellgate-contradiction.md) — fix shipped
- [base-hub start graces](er-base-hub-startgraces.md) — grants Roundtable always + First Step if Limgrave free
- [ER bake polish glow + double-grant](er-bake-polish-glow-doublegrant.md) — AP-check pickup glow + shop single-grant; fixed
- [ER fix #7 volcano loop](er-fix-7-volcano-loop.md) — fixpoint hardening of findLoops; fixed
- [ER KeepDlcMaps bug](er-keepdlcmaps-bug.md) — read enable_dlc raw not via BoolOptions; fix verified
- [?NpcName? deploy](nr-npcname-deploy-not-structure.md) — always a build/deploy problem; L4396 precedence fix shipped
- [ER DLC map flag](er-dlc-map-flag.md) — pieces 1000-1004 openEventFlagId 62080-84 are real per-area flags
- [ER client save/load crash](er-client-load-crash-poll-gate.md) — auto_upgrade race + start-item timing; fixed via SEH wrap + settle-gate
- [ER grace flag flush](er-grace-flag-flush-too-early.md) — gated flush on InventoryInstance()!=0
- [ER start-items grant loop](er-startitems-grant-loop.md) — fixed via pendingStartItems queue + persist once-per-save
- [ER progressive tier persist](er-progressive-tier-persist.md) — persist counter + highIndex
- [ER client inventory removal](er-client-inventory-removal.md) — toasts are native popups (paced); removeFromInventory=direct edit
- [ER superrepo merge](er-superrepo-merge-2026-06-15.md) — keep-ours + LF renorm + merge -s ours; runbook in repo
- [ER notify outgoing sent](er-notify-outgoing-sent.md) — 'Sent X to Y' console line done; on-screen banner parked
- [ER notify banner Task B](er-notify-banner-task-b.md) — incoming banner abandoned (native ticker is UX); modal suppression confirmed
- [ER AP-notify banner size](er-ap-notify-banner-size.md) — reuse ER native bottom-center event banner; Alaric likes its size
- [ER Twin Maiden shop dlc_only](er-twin-maiden-shop-dlconly.md) — correctly VANILLA in dlc_only; not a bug
- [ER defer grants in boss fight](er-defer-grants-in-boss-fight.md) — built then removed (obsoleted by modal suppression); AOB/RVA preserved
- [ER trimmed-pool audit](er-trimmed-audit.md) — measured trimmed=2498 (DLC 573); stones=586
- [ER playtest status 2026-06-17](er-playtest-status-2026-06-17.md) — old verification matrix; SUPERSEDED by the live board
- [ER RLA crash + CrashFix.dll](er-rla-crash-crashfix-dll.md) — PARKED; CrashFix.dll wired into deploy, wait for recurrence