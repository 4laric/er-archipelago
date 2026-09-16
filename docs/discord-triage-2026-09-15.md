# Discord report triage — 2026-09-15

The dump contains times but no message dates, builds, seed files, logs, or the referenced image.
The date above is the triage date. Player observations are preserved below; proposed causes are
not treated as reproduced defects. No Discord reply has been posted.

| Report | Priority / disposition | Tracking and next action |
| --- | --- | --- |
| Pacificator66: Stormveil start; Margit intro triggers Roundtable ejection | P1, matches an existing report | [world #202](https://github.com/4laric/er-archipelago/issues/202). Added the new evidence. Resolve shared runtime boundary without opening all of Limgrave. |
| kagutsuchi: two purchases/checks not sent, including “swap and marchant” | P1 pending check identities | [client #689](https://github.com/4laric/from-software-archipelago-clients/issues/689). Trace purchase through server acknowledgement; clarify “swap”. |
| kagutsuchi: can goal without all expected bosses | P1 if actual goal bypass; unconfirmed | [world #1569](https://github.com/4laric/er-archipelago/issues/1569). Check configured goal policy and actual AP completion status. Holding locks and completing regions are different policies. |
| Hinaloth: second Sword of Idus +1 despite held +5; later pickup succeeds | P2, violates advertised behavior if enabled and same track | [client #690](https://github.com/4laric/from-software-archipelago-clients/issues/690). Investigate cached/partial inventory census and pickup delivery. No evidence yet that duplicates themselves cause it. |
| Mayo: ER + ER multiworld? | Support answer; no bug ticket | Yes: separate named slots and saves/clients in the same AP room. The repository's `tools/gf_multiworld_smoke.py` already exercises two ER slots. This is AP item sharing, not shared in-game co-op. |
| Infernal: teleport works, Rennala absent | Unconfirmed; missing preceding commands | [client #691](https://github.com/4laric/from-software-archipelago-clients/issues/691). Need destination, phase, commands, prior defeat/randomizer state. |
| Hinaloth: Forbidden Lands + Hero's Grave fails to reach upper Mountaintops | P1, source-supported access gap | [world #1568](https://github.com/4laric/er-archipelago/issues/1568). Preserve Forbidden Lands and Zamor Ruins in limited bundles and attunement. |
| Hinaloth: open turtle/puzzle towers, retain real prerequisites | P3 feature request | [world #1570](https://github.com/4laric/er-archipelago/issues/1570). Default off; source-backed tower eligibility before implementation. |
| colombius07/bobler: DLC OOB, suspected incomplete tree burn | P1 pending location/reproduction | [client #692](https://github.com/4laric/from-software-archipelago-clients/issues/692). Obtain missing image/route; tree-burn cause unverified. Do not classify as harmless or automatically duplicate corridor-ejection #570. |

## Implemented fix and limits

`features/graces.py` previously chose Forbidden Lands (76500) as Mountaintops' sole entrance.
The region-open marker is Giant-Conquering Hero's Grave (73017), explaining why observing two
lit graces does not establish upper outdoor access. The existing landmarks bundle already names
Zamor Ruins (76501). Names and placement are recorded in `grace_names.tsv`, `grace_flags.tsv`,
and `grace_ground.tsv`; the Rold gate is recorded in `key_item_gates.tsv`.

The fix adds lower/upper component entrances and preserves component entrances when attunement
would otherwise reduce a bundle to one grace. It also prevents that reduction from undoing the
existing Ainsel component fix. Random-anchor mode keeps these fixed entrances for the two
component regions. Threshold feasibility is measured after reserving the entrances. Default
all-graces, attunement-off bundles remain unchanged.

This changes newly generated slot data. It does not repair an existing room's stored bundles,
grant the Rold Medallion, or open dungeon doors. In-game traversal remains unverified here.

Validation: 60 focused tests passed, including 24 combinations of grace tier, attunement
threshold, and anchor mode. The portable fill-regression harness generated all 96 cases
(12 configurations, eight fixed seeds each) successfully. A baseline/fixed function comparison
confirmed the old entrance bundle was `[76500]` and the old attunement anchor was `[73017]`;
both fixed paths retain `[76500, 76501]`. Wizard metadata was regenerated and release-note
validation passed. These are automated/source results, not an in-game confirmation.

The other reports do not yet support a specific safe code change. Their tickets record the
available source leads, missing evidence, and acceptance criteria rather than invented fixes.

## Suggested Discord reply

Thanks for the reports — I've split these up so they can be tracked separately.

- **Margit:** this matches the known Stormveil/Stormhill boundary problem. Your Stormveil unlock
  should let you fight its assigned sweeper; the intro followed by a Roundtable kick is a bug.
- **Mountaintops:** you're right: a grace inside Giant-Conquering Hero's Grave doesn't give you
  outdoor access above Rold. A fix is in progress to retain Forbidden Lands and Zamor Ruins,
  including with grace attunement. It affects new seeds; it won't rewrite your current room.
- **Auto-upgrade:** with the option enabled and your +5 copy still held, another copy on the same
  smithing track should arrive at +5. Normal and somber are separate. Needing repeated pickups
  isn't intended; I've filed it.
- **Missing purchases / early goal:** please send your client/apworld versions, YAML and log,
  the two merchant/check names, and which bosses remained when AP marked you complete. Some
  goal settings require holding region locks rather than clearing every boss, so the settings
  matter here. Also, what did “swap” refer to?
- **Rennala:** please include the commands you ran, where you teleported, and whether this was
  before her first defeat or with enemy randomization. That earlier context is missing here.
- **DLC OOB:** please resend the image and nearest grace/route. I've filed it as a traversal bug
  report; the tree-burn explanation still needs checking.
- **ER + ER:** yes — use two differently named Elden Ring slots in the same multiworld, each
  connected with its own client/save. That's AP item sharing rather than in-game co-op.
- **Magic towers:** I've recorded the opt-in puzzle-skip request, with actual item/gesture
  requirements preserved.
