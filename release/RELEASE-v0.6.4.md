# v0.6.4 release handoff

Alaric explicitly requested exact version 0.6.4 and a release cut after ending the
manual playtest. This handoff prepares that request; it does not claim publication.
The untagged 0.6.1.8 draft window is superseded, with its historical ledger preserved.

## Package and publication checklist

- [ ] World and client version sites agree on 0.6.4, with the generated contract mirror and exact client gitlink committed together.
- [ ] Final pinned world/client/Mario Windows CI and relevant generation/release checks pass.
- [ ] Release archive contains the matching APWorld/client, loader configuration, documentation and license notices; retained provenance identifies exact source commits and hashes.
- [ ] Mario remains explicitly optional and experimental. No private ROM, game data or generated icon atlas is included.
- [ ] Attach the optional ROM-free ER-Mario-AP-v0.6.4.zip companion with Mario DLL a39033e, profiles, setup docs, license notices and local atlas-composition helper; it uses the matched standard AP client and leaves ordinary profiles unchanged.
- [ ] Tag v0.6.4 and publish the authorized release after the final checks; record actual artifact links and hashes.
- [ ] Promote stable only after the tag exists, then regenerate channel metadata and verify the published wizard/download guidance.

## Live evidence and limitations

The human passed all nine move families, randomized pickups, visible overlays,
keyboard capture, reconnect preservation, ordinary fast travel, death/respawn
recovery and initial new-seed relocking. Further slot/history replay, region
kicks, healing, combined icons, the statue/Goldmask route, required special bosses
and ending completion remain untested live. These are disclosed limitations of
the authorized experimental release, not requests for another manual session.

Old Mario seeds cannot gain the reserved Law of Regression retroactively. Generate
a new seed for the native statue interaction. Ordinary item delivery after a room
switch still requires restart with the proper save/room identity; this release
does not bypass that protection.
