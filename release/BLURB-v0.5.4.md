# v0.5.4 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## What you need to update

- **Client:** Required — use the v0.5.4 client with v0.5.4 seeds.
- **APWorld:** Host-only — the room host or generator must install the matching APWorld.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — keep an active seed on its matching client/APWorld pair;
  there is no save migration.
- **Profile/assets:** No action.

## What is in it so far

**Mt. Gelmir's landmark-grace mode no longer strands Seethewater behind Altus.** The lower basin
cannot be reached from the two landmarks the warp menu originally selected without Altus access,
the Academy abductors, or a particular Patches state. Opening Mt. Gelmir now also grants Seethewater
River, so an Altus Lock placed in the basin cannot sit behind itself (#1136).

**Version-mismatch warnings stop covering the screen once you acknowledge them.** After reading
the full warning in the F6 tracker, you can dismiss its full-width banner for the current
connection. A persistent menu indicator and the full tracker/log details remain, and reconnecting
shows the banner again; acknowledging it never marks an unsafe pairing safe (#1133, clients#480).

**DeathLink can forgive incoming and outgoing deaths at different rates.** Seeds can independently
choose that only every Nth received DeathLink kills you and only every Nth local death is sent.
Both controls default to every death, and their counters restart on reconnect (#1051, clients#487).

**Setup says the important part first.** The current-YAML upgrade advice and the difference between
`ap.me3` save separation and Matt's launcher now take fewer detours while preserving the same
commands, warnings, and verified behavior (#1160).

## What carried over from v0.5.3

Nothing is owed. The v0.5.3 blurb and changelog were completed before its tag, and this window-opening
change promotes `stable` and regenerates `latest.json` so the updater and public wizard follow that
tag. The 0.5.4 version change has its mandatory matching client half in clients#477.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.
