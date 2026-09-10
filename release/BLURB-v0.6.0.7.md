# v0.6.0.7 — release blurb (draft)

_Draft. Written as the window fills, not at tag time -- the moment a change lands is the
only moment anyone remembers why it mattered._

## Can I update the client during a run?

**Yes.** Versions are V.R.M.F and this is still the 0.6.0 line: a v0.6.0.7 client plays every seed
rolled by any 0.6.0-line apworld, your run included, and the contract hash has not moved since
v0.6.0.3, so a v0.6.0.3, v0.6.0.4, v0.6.0.5 or v0.6.0.6 client also plays every v0.6.0.7 seed.
Your save is not at risk in either direction. The one thing that is not about the contract at all:
if Steam has updated your game to 2.7.1.0, you need a v0.6.0.6 or newer client to attach to it,
and that was already true before this window opened.

## What you need to update

- **Client:** **Optional** — unless your game is on Elden Ring 2.7.1.0, where a v0.6.0.6 or newer
  client is required and clients older than that switch themselves off at the version gate.
- **APWorld:** Host-only — install v0.6.0.7 when generating a new room once it ships.
- **YAML:** **No new YAML required. Existing YAMLs remain valid.**
- **Existing seed/save:** Compatible — a fixpack never strands a running seed.
- **Profile/assets:** No action so far. If an entry below moves the MapForGoblins build or the AP
  Flower package, this line changes with it.

## What is in it so far

- **Uniform starting regions (#1547):** Set `start_region_selection: uniform` for equal odds across eligible kept base-game and DLC regions. Respects the starting-region pool and draws multiple starts without replacement. The default remains `weighted`; existing YAMLs keep their current behavior. New rooms only.
- **Clearer release downloads (#1545):** The six optional HTML tools now share `Optional-Offline-Tools.zip`, with a README explaining each tool. Download the versioned client bundle to play, or `eldenring.apworld` to generate; the optional tools ZIP contains no DLL. Existing releases stay unchanged.

Glintstone Kris, Prosthesis-Wearer Heirloom, Golden Lion Shield and Gourmet Scorpion Stew now respect **Protect Missable Locations**.
The default leaves filler on these quest rewards; progression-only protection excludes required
progression, and off still permits it. Their dialogue's collection checks had hidden the earlier
quest prerequisites from our screening. This fixes placement in newly generated rooms.

## What carried over from v0.6.0.6

**Nothing is owed on the notes**, and that is the unusual part: v0.6.0.6 opened two commits past
its own predecessor's tag and had to move two entries out of an already-shipped section. This one
opens on a clean tag with both v0.6.0.6 release workflows green, so the v0.6.0.6 section says
exactly what v0.6.0.6 shipped and nothing has been carried forward under the wrong heading.

**The research debts are still open**, and they are the same three, unchanged by this window
because this window has not changed anything yet:

- 🛑 **The 2.7.1.0 client's live smoke test.** Its addresses are signature and
  binary-mapper derived and prologue-checked against the shipped executable, not confirmed by a
  running one. `stable` moved to v0.6.0.6 here on the strength of the tag and its green workflows;
  the gate-silent / connect / one-check / one-item log is still owed, and
  `VANILLA_MULTI_SLOT_ROWS` is still unmeasured on a vanilla 2.7.1.0 run.
- 🛑 **The world-side param re-export for the 2.7.1.0 `regulation.bin`.** The committed
  `gen_inputs.db` is still the 2026-08-29 export, so every table ships derived from the 1.17
  corpus. The two regulations compared data-identical across all 239 params, which is why this is
  tidiness rather than correctness — but it is owed, not done.
- **`tools/matt_oracle.py`** still leaves 107 item-identity disagreements and 45 missing slots
  allowlisted by cause, chiefly a DLC upgrade-material tier disagreement spanning 99 event flags;
  on 37 of those checks the curated name no longer names any item the flag's lot grants. Research
  debt against our tables, not a risk to a run.

## For whoever writes the real one

The v0.4.3 blurb is the model: lead with what changed at the table, not with the option
name. Its opening line -- "You can get BK'ed now, and that is the point" -- says what a
player will feel before it says what was built, and that is the right order.

The Academy merchant's bell bearing now follows his stock behind the Academy lock. Three boundary pickups (including both Unseen spells) move from Mt. Gelmir to Altus, with matching sweep ownership. These placement changes apply to newly generated rooms.

An optional [ALttPR repair helper](../docs/ALTTPR-FILL-IDENTITY-2026-09-10.md) addresses a mixed-room generation failure traced to duplicate-item removal in ALttPR 1.5.0. It verifies the affected source and writes a repaired package. Elden Ring itself needs no change for this failure.
