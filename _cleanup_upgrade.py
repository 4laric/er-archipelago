#!/usr/bin/env python3
"""One-shot: teach cleanup_repo.ps1 + .gitignore about newer generated file types.
Idempotent (skips if markers already present). CRLF-preserving. Verifies after."""
import sys

ROOT = "/sessions/hopeful-great-cannon/mnt/er-archipelago"
PS = ROOT + "/cleanup_repo.ps1"
GI = ROOT + "/.gitignore"


def eol_of(s):
    return "\r\n" if "\r\n" in s else "\n"


def read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write(path, s):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def insert_after(s, anchor, block, eol):
    needle = anchor + eol
    i = s.find(needle)
    if i < 0:
        sys.exit("ANCHOR NOT FOUND in ps1: %r" % anchor[:70])
    body = eol.join(block.strip("\n").split("\n")) + eol
    pos = i + len(needle)
    return s[:pos] + body + s[pos:]


# ---- cleanup_repo.ps1 edits -------------------------------------------------
ps = read(PS)
ps_eol = eol_of(ps)
if "timestamped apworld builds" in ps:
    print("SKIP cleanup_repo.ps1 (already upgraded)")
else:
    anchor_gendiag = "Remove-List (Old-Sets 'gendiag_*.txt')  \"gendiag dumps (keep newest $KeepRecentGenSets)\""
    block_a = (
        "# timestamped apworld builds + detection-table regen artifacts -- keep newest N of each\n"
        "# (git-ignored & regenerable: apworld via build.ps1 -Apworld; tables via regenerate_detection_table.py)\n"
        "Remove-List (Old-Sets 'eldenring_*.apworld') \"timestamped apworld builds (keep newest $KeepRecentGenSets)\"\n"
        "Remove-List (Old-Sets 'er_static_detection_table_augmented_*.json') \"augmented detection tables (keep newest $KeepRecentGenSets)\"\n"
        "Remove-List (Old-Sets 'detection_table_added_*.txt') \"detection-table add dumps (keep newest $KeepRecentGenSets)\"\n"
        "Remove-List (Old-Sets 'er_detection_table_missing_*.txt') \"detection-table missing dumps (keep newest $KeepRecentGenSets)\"\n"
        "# one-off slot_data verification baselines (regenerate by re-running the fixture double-run)\n"
        "Remove-List (Get-ChildItem -File 'slot_data_baseline_*.json' -ErrorAction SilentlyContinue) 'slot_data verification baselines'\n"
    )
    ps = insert_after(ps, anchor_gendiag, block_a, ps_eol)

    anchor_bak = "Remove-List ($walkFiles | Where-Object { $_.Name -match '\\.bak_' }) 'tagged editor backups (*.bak_<tag>)'"
    block_b = (
        "# truncation backups left by patch scripts / mount-truncation recovery (*.truncbak)\n"
        "Remove-List ($walkFiles | Where-Object { $_.Name -like '*.truncbak' }) 'truncation backups (*.truncbak)'\n"
    )
    ps = insert_after(ps, anchor_bak, block_b, ps_eol)

    # keep the .DESCRIPTION accurate
    ps = ps.replace(
        "probe tmp files, loose *.bak). All of these are",
        "probe tmp files, loose *.bak/*.truncbak, timestamped apworlds, "
        "detection-table regen artifacts, slot_data baselines). All of these are",
        1,
    )
    write(PS, ps)
    print("patched cleanup_repo.ps1")

# ---- .gitignore edits -------------------------------------------------------
gi = read(GI)
gi_eol = eol_of(gi)
if "detection-table regen artifacts" in gi:
    print("SKIP .gitignore (already upgraded)")
else:
    add = (
        "# --- detection-table regen artifacts (regenerate via regenerate_detection_table.py; canonical = Archipelago/worlds/eldenring/) ---\n"
        "er_static_detection_table_augmented_*.json\n"
        "detection_table_added_*.txt\n"
        "er_detection_table_missing_*.txt\n"
        "# --- truncation backups + one-off slot_data verification baselines ---\n"
        "*.truncbak\n"
        "slot_data_baseline_*.json\n"
    )
    if not gi.endswith(gi_eol):
        gi += gi_eol
    gi += gi_eol + gi_eol.join(add.strip("\n").split("\n")) + gi_eol
    write(GI, gi)
    print("patched .gitignore")

# ---- verify -----------------------------------------------------------------
for path, needle in ((PS, "timestamped apworld builds"), (PS, "*.truncbak"), (GI, "*.truncbak"),
                     (GI, "er_static_detection_table_augmented_*.json")):
    b = open(path, "rb").read()
    ok = (b"\x00" not in b) and (needle.encode() in b)
    print("VERIFY %-18s %-42s %s" % (path.split("/")[-1], needle, "OK" if ok else "FAIL"))
