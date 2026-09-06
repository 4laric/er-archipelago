# v0.6.0 stable release handoff and smoke checklist

Status: preparation in progress; publication and the bundled-build live smoke are pending.
The APWorld/client version and proposed stable tag are `0.6.0` and `v0.6.0`.
Prepare an ordinary stable release, not a prerelease. Publication and stable-channel
promotion have not happened; record them only when completed.

## Scope and expectations

The release bundles the source-built MapForGoblins engine and matching AP client.
Gathering nodes are hidden by the preset. Check-only is the default while a session map
workflow is active; progression-only and tracker-region in-logic-only remain optional.
Map progression excludes enabled sweep-member pickups and highlights their granting boss;
F6 stars and F5 `[P]` keep the raw seed-surface meaning. Halos default to 1.5x.
The map also has larger progression highlights, and F5 has concise names, AP/UT item colors,
and session `[P]`/`[S]` annotations.

MapForGoblins placements are accepted reference data. The full access audit is incomplete.
Check-only filtering hides unmatched pins, some of which may correspond to real checks;
the map therefore does not replace the complete F6 check list. Region access does not
establish additional quest, key or puzzle readiness.
A granting boss without a native MapForGoblins pin cannot receive a map highlight;
the associated checks remain available in F6.

The release is assembled by `tools/pack_release.py` and the `er-release` workflow.
Legacy `build.ps1 -Me3Deploy` and `package_release.ps1` remain local client-only
routes; they do not produce this release's bundled map-engine release.

Current candidate builds: client `cf6bb11` (client PR #633), map engine `81613ec`.
Land engine PR #7 and client PR #633 before world PR #1431. After the client merge,
refresh the world gitlink to the resulting client `main` SHA and rerun pairing checks;
the merge may produce a different SHA. Pin complete commits and final hashes in provenance.

Leave `CHANNELS.tsv` on its current stable tag while preparing this release: its gate
rejects a future tag. Promote that ledger only after `v0.6.0` actually exists. These
instructions describe the remaining handoff; no merge or tag is claimed here.

## Package gates

- [ ] World PR records the exact merged client gitlink and map-engine source/build identity.
- [ ] Bundle contains the matching APWorld, client DLL, vanilla-profile map-engine DLL,
      configuration, loader profile, and required license notices.
- [ ] Archived loader profile resolves every bundled file and loads one map engine.
- [ ] Automated release checks and relevant build/CI jobs pass on the final pinned commits.
- [ ] Final archive hashes and build provenance are retained with the release artifacts.
- [ ] Release uses tag `v0.6.0` and is not marked prerelease; stable-channel metadata and
      published update guidance agree with the actual release.

## Live smoke on the assembled archive

Record the archive hash, client/engine versions, seed, game version and result for each step.
These boxes deliberately remain open until someone runs the assembled bundle.

- [ ] Launch through the archived profile and connect to a matching v0.6.0 seed; open the
      native map and F5/F6 without a crash or duplicate engine.
- [ ] In F6, expand **Map pin test (optional)** and select **Enable map filters (this session)**. Gathering-node Trina's Lily pins stay hidden, while
      an actual Lily treasure check in the seed remains visible. A neutral check stays visible.
- [ ] A pin outside the connected seed is hidden, including when category focus is selected.
- [ ] Progression-only hides neutral checks; larger halos appear on eligible progression
      pins, including multiple native representations of one lot. An enabled sweep-member
      pickup has no progression halo and is excluded by progression-only; its granting boss
      is highlighted instead. Its F6 star/F5 `[P]` remains consistent with the seed surface.
- [ ] F10 opens map settings without a stamina probe. A missing live FMG name retains the
      valid original label; changing check states removes obsolete orange highlights.
- [ ] In-logic-only follows the F6 region-access result. Combining it with progression-only
      requires the same candidate check to satisfy both conditions.
- [ ] Change region access, toggle filters, close/reopen the map and warp. Visibility updates
      without stale hidden pins or floating halos; collecting a known pickup still hides it.
- [ ] Disconnect, change seed and disable all session map workflows. Old state is withdrawn;
      an interrupted client update expires rather than applying the old seed indefinitely.
- [ ] F5 shows clean pickup names, the expected classification colors and correct session
      `[P]`/`[S]` markers. A physical pickup is distinguishable from a sweep completion.
- [ ] F6 still lists checks that have no matched map pin. Review links identify the intended
      check and opening a link does not submit a report.

Do not turn passing compile/host tests into checked live-smoke boxes. Record remaining
problems alongside the release notes before publication.

## Observations before the assembled-release smoke

On September 5, the player confirmed in the earlier test bundle that larger progression
rings work and that in-logic filtering works once its toggle is enabled. A 3x halo was too
broad; the default remains 1.5x. The scarab's F6 star correctly represented a seed
progression-surface slot covered by a sweep. The subsequent map-only sweep exclusion,
F10 change and label fallback still require the final assembled-bundle smoke. These
preliminary observations do not check off the final archive's live-smoke boxes above.
