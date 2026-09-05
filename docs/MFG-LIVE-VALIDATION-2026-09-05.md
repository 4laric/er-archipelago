# Map tracker live validation — 2026-09-05

These are bounded observations from Alaric's test session, not a promotion of
the source-corroboration ledger or proof of every map pin.

## Build and evidence

- Source-built map engine: f505f8c93ef63bb62c224b71880d2a585769c48e
  ([engine PR 1](https://github.com/4laric/ERR-MapForGoblins-DLL/pull/1)).
- Recording client: 23eb0716169f34fa51fa9a6c502d97b6a0ab5f3b
  ([client PR 628](https://github.com/4laric/from-software-archipelago-clients/pull/628)).
- Static resolver/catalog: registry branch 1c03aee334ff2b71219c2092e78f2688f59d8795.
- Session: MFGTest, apworld 0.6.0, contract ffc0f1b5.
- Source evidence: user-provided archipelago-2026-09-05.log and screenshots,
  plus explicit player confirmations in the development conversation.
- The attached log is append-only across launches. The locally retained snapshot
  SHA-256 is 9e52b3979924ca1444877a8d7b6c5597d2d7ac926bdd60a73da4b5118ca5c24b. Times below are literal log times; no timezone conversion
  is inferred. Full logs remain local; only relevant observations are reproduced.

## Confirmed witnesses

| Witness | Observation | What it establishes |
| --- | --- | --- |
| Gatefront Lordsworn's Greatsword | Player collected it and confirmed its map pin disappeared. No successful hover capture for this pickup was supplied. | Pickup hiding worked for this one pickup; no bridge identity claim. |
| Limgrave Tunnels Glintstone Scrap | Capture at 11:23:17: map lot 32010040, generation 23, handle 4015, source age 13 ms. Resolver returns only AP 7772256, original catalog flag 32017040. Player explicitly confirmed that was the hovered pickup. | Live native hover -> copied original lot -> matching catalog candidate, confirmed by player. No collection event claimed. |
| Gatefront Flail | Capture at 11:26:43: map lot 942370060, generation 29, handle 1269, source age 12 ms. Resolver returns only AP 7772821, original catalog flag 1042377060. At 11:27:01 AP reported finding that Flail check, and player reported hovering and collecting it. | Live hover -> matching catalog candidate -> AP collection report for this pickup. Pin disappearance after Flail collection was not separately confirmed. |

Both hover records have original-flag=0: the bridge deliberately leaves that
identity unknown. The nonzero flags above come from the catalog resolver, not a
flag read by the native interface. Runtime handles are transient and are not native
generated row IDs. The 300 ms freshness limit was not relaxed to obtain these results.

Relevant log excerpts:

    11:23:17 [INFO] [APC] Recorded map pin at client +160107 ms, 10528 ms after starting (source age 13 ms): generation=23 handle=4015 original-flag=0 lot-table=1 lot-row=32010040. Historical observation, not a live hover; AP binding not established.
    11:26:43 [INFO] [APC] Recorded map pin at client +365228 ms, 5251 ms after starting (source age 12 ms): generation=29 handle=1269 original-flag=0 lot-table=1 lot-row=942370060. Historical observation, not a live hover; AP binding not established.
    11:27:01 [INFO] [APS] MFGTest found their Flail (Limgrave :: Flail - near Agheel Lake North, may be sweep-granted by Ulcerated Tree Spirit (m18_00) [f1042377060])

Reproduce the static part from this registry revision:

    python3 tools/resolve_mfg_hover.py --lot-table map --lot-row 32010040
    python3 tools/resolve_mfg_hover.py --lot-table map --lot-row 942370060

## Remaining limits and observations

- The two successful captures do not validate every shared-flag mapping, pin position,
  map layer, seed configuration, lifecycle transition, or player review submission.
- Collection is distinct from physical visitation: sweeps can report checks. For
  the Flail, the player also explicitly reported physical collection.
- Slow map performance was reported. The supplied engine log confirms fast-map
  setup failed and all 7,031 marker rows were added. It also records 53 missing
  enemy-lot rows. These do not establish which work caused the slowdown.
- A supplied community screenshot suggests disabling gathering nodes. In this
  build that setting is show_material_nodes = false, separate from
  show_crafting_materials; performance improvement has not been measured.
- The same screenshot reports Coffin Fissure visibility depending on Miquella's
  fog gate. This is an unverified report for this build, not a confirmed defect
  or a proven game-condition relationship.

## Next implementation gate

Show captured check candidates in F6 using the connected seed's location set,
retain ambiguities and unknowns, show current AP completion separately from the
historical hover, and offer explicit player review actions. These witnesses
justify proceeding to that presentation; they do not authorize automatic
corroboration or marking a check as physically visited.
