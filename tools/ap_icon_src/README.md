# AP flower — icon source art

The Archipelago flower, as it should appear on every AP item in game. `build_ap_icon.py` composites
this into the game's SB_Icon sprite sheet at **cell 92** (vanilla: the Telescope), and me3 serves the
result as a VFS override. The client points the placeholder good (`8852`) and every repointed shop
slot at iconId 92, so this one image is what all of them wear.

Provided by Alaric 2026-07-29, which closed half of the gap described in
`docs/AP-ICON-PIPELINE.md` — the other half is `tools/build_ap_icon.py` itself, still untracked.

## Files

| file | role |
|---|---|
| `ap_flower.webp` | **CANONICAL.** The original, byte-for-byte as supplied. 2034x2112, RGBA, transparent background. |
| `ap_flower.png`  | Derived convenience copy for tooling that will not read webp. Regenerate with the one-liner below; verified a lossless round-trip of the webp's pixels. |

    python -c "from PIL import Image; Image.open('tools/ap_icon_src/ap_flower.webp').convert('RGBA').save('tools/ap_icon_src/ap_flower.png','PNG',optimize=True)"

If they ever disagree, the webp wins and the png is stale — regenerate it, do not hand-edit either.

## Two things to check when wiring the tool

1. **The art is NOT square** — 2034x2112, opaque bounding box (5, 7, 2028, 2107). SB_Icon cells are
   square, so something must letterbox or crop it. Whatever the tool does, it should do it
   deliberately rather than by non-uniform scaling.
2. **`--black-to-alpha` is probably wrong for this source.** The documented invocation in
   `build.ps1` is `--icon01 --icon-id 92 --black-to-alpha --bundles hi,low`. That flag keys
   transparency off a black background; this image already ships a real alpha channel (corner alpha
   = 0). Passing it may punch holes in the dark parts of the petals rather than doing nothing.
   Verify against a rendered sheet before trusting it.

## Licensing

This is the Archipelago project's logo, used to mark Archipelago items in an Archipelago world.
It is NOT game data — `PROVENANCE.md` rule 1 does not apply to it, which is why it can live here.
The sprite sheet it gets composited INTO is FromSoft's and must never be committed; see
`docs/AP-ICON-PIPELINE.md` for the three-way split.
