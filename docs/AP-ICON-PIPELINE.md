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
            +
    <game>\oo2core_6_win64.dll   (the player's codec; discovered, never copied or packaged)
            |
            v   tools/build_ap_icon.py --icon01 --icon-id 92 --bundles hi,low --menu "<game>\menu"
    build\ap_icon01\menu\{hi,low}\01_common.tpf.dcx   (gitignored)
            |
            v   build.ps1
    me3\ap-package\menu\{hi,low}\01_common.tpf.dcx    (gitignored)
            |
            v   package_release.ps1  -- HARD FAILS if the sheet is absent
    the release zip

`build.ps1` now **invokes the tool on every me3 deploy**. The output is a complete atlas, so a cached
copy from an older game version would erase icons added by a later patch even though the AP flower
cell still looked correct. It throws if the tool is absent, if `$GameDir\menu` is absent, or if the
tool does not produce both the hi and low sheets.

This rebuild is deliberately not timestamp-based. Steam and copied game directories do not provide
a trustworthy cross-machine timestamp relationship, while rebuilding from the installed source is
the only direct proof that every non-92 cell belongs to the game version being packaged.

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

The old KRAK/runtime-splice fork is resolved. A 2026-08-17 live experiment proved that Elden Ring
loads both `menu\hi\01_common.tpf.dcx` and `menu\low\01_common.tpf.dcx` when repacked as
`DCX_DFLT`; the flower rendered without the AP client DLL or any KRAK override. The game atlas has
one mip, so there is no hidden lower-mip splice to reconstruct.

`build_ap_icon.py` therefore performs an installer-side derivation:

1. read the hi and low KRAK source atlases from the player's installation;
2. expose the player's own `oo2core_6_win64.dll` to Witchy for decompression;
3. replace only icon 92 with the committed AP artwork;
4. change Witchy's container manifest to `DCX_DFLT`, repack, and verify the output header says DFLT;
5. stage the generated full atlases only under ignored build/package paths.

Neither Oodle nor a generated atlas is copied into git or a release. Re-running starts from the
installed source again and clears the intermediate extraction, so the result does not accumulate
edits from an earlier build. Missing game files, Oodle, Witchy, the expected layout geometry, or a
DFLT output are hard failures with actionable messages. The player does not need Pillow or texconv: the
committed 25,600-byte BC7 payload is project-owned art, and the installer copies its aligned blocks
directly into the one-mip BC7 surface.
