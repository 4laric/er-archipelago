#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Cross-compile the Elden Ring Archipelago client (.dll) FROM Linux.
#
# The whole cargo/rustc/clang toolchain runs on a Linux host; the output is a
# Windows x86_64-pc-windows-msvc cdylib (eldenring_archipelago.dll).
# This removes the "every build needs the Windows box" friction. You STILL need
# Windows to RUN / smoke-test the dll (it hooks a live Elden Ring process).
#
# Target hosts: a clean Ubuntu 22.04/24.04 machine, WSL2, or GitHub Actions
# `ubuntu-latest`. Needs root (sudo) for the apt step, ~4-5 GB free disk, and
# outbound network for crates.io + the git deps + the MSVC SDK download.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_ROOT="${1:-$(git rev-parse --show-toplevel)}"
CLIENTS="$REPO_ROOT/from-software-archipelago-clients"
TARGET=x86_64-pc-windows-msvc

# cargo-xwin downloads the Microsoft CRT/SDK; this accepts the EULA non-interactively.
export XWIN_ACCEPT_LICENSE=1

# 1. Rust toolchain + the Windows target's std (no C++ here, small download).
if ! command -v rustup >/dev/null 2>&1; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
  # shellcheck disable=SC1091
  . "$HOME/.cargo/env"
fi
rustup target add "$TARGET"

# 2. C/C++ cross toolchain that cargo-xwin drives. imgui-sys and hudhook each
#    compile C/C++; clang-cl compiles it against the MSVC CRT, lld-link links.
if ! command -v clang-cl >/dev/null 2>&1 || ! command -v lld-link >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y clang lld llvm
fi

# 3. cargo-xwin: transparently downloads + caches the MSVC CRT/SDK headers and
#    import libs (~1 GB, cached under $XWIN_CACHE_DIR / ~/.cache on later runs).
cargo install --locked cargo-xwin

# 4. Pure-logic crates: host-native build + tests. No Windows/clang needed --
#    this is the layer your greenfield/ci-linux.sh already gates. Fast.
( cd "$CLIENTS" && cargo test -p er-codec -p er-semver -p er-logic )

# 5. The real event: cross-compile the client cdylib -> eldenring_archipelago.dll
( cd "$CLIENTS" && cargo xwin build --release \
    -p eldenring-archipelago --target "$TARGET" )

echo
echo "=== artifact ==="
ls -la "$CLIENTS/target/$TARGET/release/eldenring_archipelago.dll"