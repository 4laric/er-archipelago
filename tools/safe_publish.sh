#!/usr/bin/env bash
# safe_publish.sh -- corruption-proof publish of a file onto the (truncating) mount.
#
# The sandbox mount silently truncates / null-pads large Write/Edit/redirect
# writes. This publishes SRC -> DST so a truncated result can never land silently:
#   1. guard SRC is non-empty and itself passes check_integrity
#   2. stage onto the SAME filesystem as DST (rename is only atomic same-FS)
#   3. cmp the staged bytes against SRC -- a corrupt copy fails here, loudly
#   4. atomic `mv` over DST: rename makes a NEW inode, defeating the
#      shrinking null-pad, and rename is one op the mount actually allows
#   5. re-verify DST size + sha256 == SRC and print a receipt
#
# Usage:   tools/safe_publish.sh SRC DST
# Example: tools/safe_publish.sh /tmp/core.py greenfield/eldenring_gf/core.py
#
# Exit 0 = published + verified; non-zero = nothing published (or publish
# aborted before the rename). ALWAYS also confirm DST with the harness Read
# tool -- bash can serve a stale mount view even of a just-written file.
set -euo pipefail

die() { echo "safe_publish: ERROR: $*" >&2; exit 1; }

[ $# -eq 2 ] || die "usage: safe_publish.sh SRC DST"
SRC=$1; DST=$2
HERE=$(cd "$(dirname "$0")" && pwd)

[ -f "$SRC" ] || die "SRC does not exist: $SRC"
[ -s "$SRC" ] || die "SRC is EMPTY: $SRC (refusing to publish 0 bytes)"

# 1. verify the source itself before it goes anywhere
if [ -f "$HERE/check_integrity.py" ]; then
  python3 "$HERE/check_integrity.py" "$SRC" || die "SRC failed integrity check: $SRC"
fi

DSTDIR=$(dirname "$DST")
mkdir -p "$DSTDIR"
STAGE="$DSTDIR/.safe_publish.$(basename "$DST").$$"

cleanup() { [ -e "$STAGE" ] && mv -f "$STAGE" "$STAGE.orphan" 2>/dev/null || true; }
trap cleanup EXIT

# 2 + 3. stage same-FS, then prove the staged bytes match SRC exactly
cp "$SRC" "$STAGE"
if ! cmp -s "$SRC" "$STAGE"; then
  die "staged copy differs from SRC (mount corrupted the write): $STAGE"
fi

SRC_SHA=$(sha256sum "$SRC" | cut -d' ' -f1)
SRC_LEN=$(wc -c < "$SRC" | tr -d ' ')

# 4. atomic rename over the destination (new inode; no null-pad possible)
mv -f "$STAGE" "$DST"
trap - EXIT

# 5. re-verify the destination on disk
DST_SHA=$(sha256sum "$DST" | cut -d' ' -f1)
DST_LEN=$(wc -c < "$DST" | tr -d ' ')
[ "$DST_SHA" = "$SRC_SHA" ] || die "post-publish sha MISMATCH ($DST): got $DST_SHA want $SRC_SHA"
[ "$DST_LEN" = "$SRC_LEN" ] || die "post-publish size MISMATCH ($DST): got $DST_LEN want $SRC_LEN"

echo "safe_publish: OK $DST"
echo "  bytes : $DST_LEN"
echo "  sha256: $DST_SHA"
echo "  head  : $(head -n1 "$DST")"
echo "  tail  : $(tail -n1 "$DST")"
echo "  NOTE  : also confirm with the harness Read tool (bash mount can lie on read-back)."
