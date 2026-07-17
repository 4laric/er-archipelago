# NOTES — In-game map overlay (parked / future feature)

Status: PARKED 2026-07-17 (Alaric: "real overlay goes on the future feature pile"). Goal was to draw
the AP randomizer's remaining checks onto Elden Ring's *own* map screen (which already shows
you-are-here), anchored via coordinates — the "anchor around the graces" idea. Feasibility: tractable
but a multi-hour interactive RE project, not a quick win. The tracker map (PopTracker pack) already
delivers "every remaining check on a map"; this was the stretch of putting them on the game's map.

## What the deliverable actually needs

The game already renders you-are-here, so the *only* missing thing is checks-on-the-map. Two hard
parts remain, plus one solved:

1. **Coordinate registration (BLOCKED — needs a differential scan).** We need the player's live world
   position AND the game's absolute coordinate frame, to project check coords onto the map.
2. **Map view state (not yet probed).** The map's pan-centre + zoom, so markers stay correct when you
   drag/zoom. If you never pan, "map opens centred on the player" is a usable first approximation.
3. **Drawing (EASY, was over-worried).** No DirectX hook needed: if ER runs borderless/windowed, a
   plain always-on-top transparent (click-through) overlay window drawing markers at computed screen
   pixels works. Standard game-overlay technique.

## What we CONFIRMED this session (Cheat Engine, game build as of 2026-07)

Probe: `greenfield/probes/ce_player_coords_probe.lua` (evolved v1→v6; final = value-scan hunter).
Reference table: Hexinton v6.1 (`eldenring_allinone_Hexintonv6.1_ce7.5.ct`).

- **WorldChrMan** resolves from the stable AOB `48 8B 05 ?? ?? ?? ?? 48 85 C0 74 0F 48 39 88`
  (`base = [hit + 7 + rel32]`). Confirmed working.
- **Local player** at `[[WorldChrMan] + 0x1E508]` (Hexinton also exposes `LocalPlayerOffset = 0x10EF8`
  via `[[+0x10EF8]+0]`; both reach the player). Confirmed.
- **Local (rebased) coords** = player `->0x190 ->0x68 +0x70` {x,y,z} floats. Reads fine, but this is
  ER's *floating-origin* value: it re-anchors at graces and does NOT track world position (two graces
  137 units apart read ~17 units apart). **Not usable for map projection.**
- **Current overworld tile** = little-endian mapid dword at player `+0x38` (`{sub,YY,XX,area}`,
  overworld area 60/61). Decodes correctly (`m60_42_36` on The First Step) AND updates as you cross
  tiles (Gatefront→`m60_42_37`, Agheel N→`m60_43_37`). **This works and is reusable.**

## What is BLOCKED and why

- Hexinton's **Global Coords** entry (`player + 0x6B0`) and **LastGoodGlobalCoords** (`+0x6C4`) read a
  *pointer*, not floats, on this build — the table's global offset is **stale for our game version**
  (local-coord + tile offsets survived; the global block moved).
- We can't find global by value-scan either: our datamine "global" `gx = tileXX*256 + localX` is *our*
  composition (internally consistent for the tracker map) and may not match the game's **absolute**
  coordinate origin. `ce_player_coords_probe.lua` v6 swept the player's ChrIns + physics windows for
  The First Step's datamine `(10739, 9162)` ±18 and found nothing — consistent with a different
  absolute frame (or the field living off WorldChrMan / a world-block struct).

## Plan when we pick this up

1. **Differential-scan the player world coords** (version-agnostic, no known value needed): CE float
   scan "unknown initial value" → walk north → "increased value" → walk south → "decreased" → repeat
   to isolate Z; repeat for X. Standard; every ER practice tool has these.
2. **Fit our datamine frame to the game frame**: read the found coords at 3-4 known graces, solve the
   affine map (almost certainly a translation, maybe a sign/axis swap) between game-world (gx,gz) and
   our `item_grace_coords.tsv` frame. The tile at `+0x38` composes the coarse position; the fit handles
   the origin.
3. **Map view state**: with the map open, differential-scan for the pan-centre (world x/z that change
   as you drag) + a zoom/scale float. Or approximate with "opens centred on player + fixed default zoom."
4. **Overlay window**: borderless always-on-top transparent window; project each remaining check via the
   fitted transform → screen pixels → draw. Feed "remaining checks" from the AP client / tracker state.

## Cheaper alternative (no memory work)

Generate a static annotated Lands Between map (all checks pinned, from `item_grace_coords.tsv` + the
map calibration) for personal reference on a second monitor — pairs with the game's you-are-here. This
was offered as the quick win; not built yet.
