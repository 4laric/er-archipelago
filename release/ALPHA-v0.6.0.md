# v0.6.0-alpha.1 preparation and smoke checklist

Status: preparation in progress; publication and the bundled-build live smoke are pending.
The APWorld/client version remains `0.6.0`. `v0.6.0-alpha.1` is the proposed release tag,
not a separate wire-protocol version. Keep this release marked prerelease and leave
stable/beta channel pointers unchanged.

## Scope and expectations

The alpha bundles the source-built MapForGoblins engine and matching AP client.
Gathering nodes are hidden by the preset. Check-only is the default while a session map
workflow is active; progression-only and tracker-region in-logic-only remain optional.
The map also has larger progression highlights, and F5 has concise names, AP/UT item colors,
and session `[P]`/`[S]` annotations.

MapForGoblins placements are accepted reference data. The full access audit is incomplete.
Check-only filtering hides unmatched pins, some of which may correspond to real checks;
the map therefore does not replace the complete F6 check list. Region access does not
establish additional quest, key or puzzle readiness.

The alpha is assembled by `tools/pack_release.py` and the `er-release` workflow.
Legacy `build.ps1 -Me3Deploy` and `package_release.ps1` remain local client-only
routes; they do not produce this alpha's bundled map-engine release.

## Package gates

- [ ] World PR records the exact merged client gitlink and map-engine source/build identity.
- [ ] Bundle contains the matching APWorld, client DLL, vanilla-profile map-engine DLL,
      configuration, loader profile, and required license notices.
- [ ] Archived loader profile resolves every bundled file and loads one map engine.
- [ ] Automated release checks and relevant build/CI jobs pass on the final pinned commits.
- [ ] Final archive hashes and build provenance are retained with the release artifacts.
- [ ] Release is prepared as `v0.6.0-alpha.1`, marked prerelease, without moving stable/beta.

## Live smoke on the assembled archive

Record the archive hash, client/engine versions, seed, game version and result for each step.
These boxes deliberately remain open until someone runs the assembled bundle.

- [ ] Launch through the archived profile and connect to a matching v0.6.0 seed; open the
      native map and F5/F6 without a crash or duplicate engine.
- [ ] In F6, expand **Map pin test (optional)** and select **Enable map filters (this session)**. Gathering-node Trina's Lily pins stay hidden, while
      an actual Lily treasure check in the seed remains visible. A neutral check stays visible.
- [ ] A pin outside the connected seed is hidden, including when category focus is selected.
- [ ] Progression-only hides neutral checks; larger halos appear on eligible progression
      pins, including multiple native representations of one lot.
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

## Observations before the assembled-alpha smoke

On September 5, the player confirmed that enabling session sharing in the earlier test bundle
made larger progression rings visible. This verifies that activation path in the test bundle;
it does not complete the assembled-alpha smoke or the in-logic filter check above.
