#!/usr/bin/env bash
# greenfield/provision-linux-env.sh -- one-time Linux env for greenfield gen/CI.
#
# Stands up Python 3.11 + a stock Archipelago runtime so the whole greenfield gate runs NATIVELY
# on Linux -- no Windows, no Cowork mount (see SPEC-PARITY.md "dedicated env"). Idempotent: re-run
# freely. Home: WSL2 (recommended -- native ext4, same box as the game), a persistent VM, or a
# sandbox session. Greenfield only uses core AP API, so stock ArchipelagoMW/Archipelago suffices.
#
#   bash greenfield/provision-linux-env.sh          # provision (or refresh) the env
#   GF_CI_HOME=~/gfci bash .../provision-linux-env.sh   # custom location
set -uo pipefail
CACHE="${GF_CI_HOME:-$HOME/.greenfield-ci}"
AP_REPO="${GF_AP_REPO:-https://github.com/ArchipelagoMW/Archipelago.git}"
VENV="$CACHE/.venv"; AP="$CACHE/ap"
mkdir -p "$CACHE"
export PATH="$HOME/.local/bin:$PATH"

if ! command -v uv >/dev/null 2>&1; then
  echo "[provision] installing uv ..."
  curl -LsSf https://astral.sh/uv/install.sh | sh || { echo "uv install failed"; exit 2; }
  export PATH="$HOME/.local/bin:$PATH"
fi

uv python install 3.11 || { echo "python 3.11 install failed"; exit 2; }
[ -d "$VENV" ] || uv venv --python 3.11 "$VENV"
# headless gen + test deps only -- NOT AP's full requirements.txt (no Kivy/GUI git deps)
uv pip install --python "$VENV" -q \
  pyyaml schema jsonschema typing-extensions pathspec platformdirs certifi colorama pytest \
  || { echo "dep install failed"; exit 2; }

if [ ! -d "$AP" ]; then
  echo "[provision] cloning Archipelago (shallow) ..."
  git clone --depth 1 --single-branch "$AP_REPO" "$AP" || { echo "AP clone failed"; exit 2; }
fi
echo "[provision] READY: $("$VENV/bin/python" --version) | AP=$AP | cache=$CACHE"
