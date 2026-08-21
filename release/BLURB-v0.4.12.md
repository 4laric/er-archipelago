# v0.4.12 — release blurb (draft)

_Draft. Written as the window fills, not at tag time — the moment a change lands is the
only moment anyone remembers why it mattered._

## What you need to update

- **Client:** Required — use the v0.4.12 client with v0.4.12 seeds.
- **APWorld:** Host-only — the room host or generator must install v0.4.12; joining players only
  need the matching client.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — keep an active v0.4.11 seed on its matched v0.4.11 pair.
  There is no save migration; just do not mix client and APWorld versions.
- **Profile/assets:** No action — no profile or packaged asset changed when the window opened.

## What is in it so far

**One command really is one command now.** The matt's-rando installer used to refuse fresh
installs with an instruction — "open Add dll mod once, close it, the app writes the file" — that
turned out to be false: the app writes nothing on open-and-close. The installer now creates the
config itself when it is genuinely missing (only the one line it owns, in the app's own style),
appends its line to a config without a dll list, and if the config lives one folder up or down
from where you pointed it, refuses and names the right folder instead of planting a twin.

**Packaging housekeeping.** The release bundle is now built by a script that stages the updater
and the matt's-rando installer beside the dll as required entries — the v0.4.11 zip already
shipped with them, this makes that mechanical — and the packager derives its version from
`contract.py` instead of a stale default.

## What carried over from v0.4.11

The two entries above were found during v0.4.11's own packaging acceptance and landed just past
its tag; nothing else is carried. The stable channel promotes to the already-published v0.4.11
tag in the window-open commit while beta remains on `main`.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. The v0.4.11 blurb's "the shelf finally tells you what it's selling" is the same shape —
say what a player will feel before what was built.
