# The AP flower icon: what may be committed, and what may not

The placeholder good (`8852`) and every repointed shop slot are pointed at **iconId 92** by the
client. Vanilla cell 92 is the **Telescope**. The AP flower is not a separate item -- it is that cell
repainted by a me3 VFS override, so *everything* the client points at 92 renders as the flower.

That is why the icon is not a cosmetic nicety. The client writes the icon id unconditionally
(`check_lots.rs::dress_placeholder`, `shop_icon.rs`); if the override is absent the write still
happens and the player sees a literal telescope on every check and every AP shop slot. A player
reported exactly that on 2026-07-29. **A client that writes an icon id and a bundle that does not
define it are two halves of one feature.**

## Three artifacts, three different answers

| artifact | whose | in git? | why |
|---|---|---|---|
| `tools/build_ap_icon.py` | **ours** | YES | project source. It was referenced by `build.ps1` in four places while living only on one dev box -- which is the whole reason the flower has never shipped from a clean clone. |
| the flower **source artwork** | Archipelago's logo | YES -- **landed 2026-07-29** at `tools/ap_icon_src/` | not game data, so rule 1 does not apply. The only input that is not derivable: without it the tool cannot reproduce the sheet on another machine. |
| `menu\hi\|low\01_common.tpf.dcx` (the built sheet) | **FromSoft's**, repainted | **NO** | the game's SB_Icon sprite sheet with one cell replaced. Game data -- **PROVENANCE.md rule 1**. Gitignored (`/build/`, `/me3/`). Built per machine from the local install. |

The split is the one the rest of this repo already uses: **commit the derivation, never the derived
game data.** `gen_inputs.db` and the params are handled the same way.

## The pipeline

    flower art (ours, committed)
            +
    <game>\menu\hi|low\01_common.tpf.dcx   (the player's own install -- never ours to redistribute)
            |
            v   tools/build_ap_icon.py --icon01 --icon-id 92 --black-to-alpha --bundles hi,low --menu "<game>\menu"
    build\ap_icon01\menu\{hi,low}\01_common.tpf.dcx   (gitignored)
            |
            v   build.ps1
    me3\ap-package\menu\{hi,low}\01_common.tpf.dcx    (gitignored)
            |
            v   package_release.ps1  -- HARD FAILS if the sheet is absent
    the release zip

`build.ps1` now **invokes the tool itself** when the sheet is missing, rather than printing the
command and carrying on. It throws if the tool is absent, if `$GameDir\menu` is absent, or if the
tool exits 0 but produces nothing (an empty result is a failure, not a clean run).

## Why the packager fails rather than warns

It used to log *"cosmetic nicety, not a feature ... the placeholder is NAMED either way"* and ship.
That reasoning is wrong twice over: the naming covers the *placeholder* but not the repointed shop
slots, and "the feature degrades quietly" is exactly the class of failure this project treats as a
defect (CONTRIBUTING, *Runtime visibility* -- tolerance requires telemetry, and a silent
half-feature is indistinguishable from a broken one).

The gate requires the **real** sheet, `01_common.tpf.dcx`. `build.ps1` also stages `00_solo.*` as a
harmless hi-res extra, so an any-file-present check would pass on the cosmetic variant alone and
still ship telescopes.

## Open item

The **source art has landed** (`tools/ap_icon_src/`, 2026-07-29). What is still missing is
`tools/build_ap_icon.py` itself -- it exists only on the dev box. Until it is committed, `build.ps1`
throws with instructions and `package_release.ps1` refuses to package. That is deliberate: the gap
was previously invisible, and a build that quietly skipped the icon is how it stayed invisible.

Two notes for whoever commits the tool, both recorded in `tools/ap_icon_src/README.md`: the art is
not square (2034x2112) while SB_Icon cells are, and the documented `--black-to-alpha` flag looks
wrong for this source, which already carries a real alpha channel.
