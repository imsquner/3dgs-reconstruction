#!/usr/bin/env bash
# Explicit user invocation installs into a NEW isolated environment only.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
ENV_DIR=${1:-"$ROOT/.venv-wsl"}
RESUME=${2:-}
if [[ $(uname -s) != Linux ]]; then echo 'Linux/WSL required' >&2; exit 1; fi
if [[ -e "$ENV_DIR" && "$RESUME" != --resume ]]; then echo 'Existing environment preserved; use --resume only for this installer or choose a NEW path' >&2; exit 1; fi
python3.10 -c 'import sys; assert sys.version_info[:2] == (3,10)'
command -v nvcc >/dev/null || { echo 'Install CUDA toolkit 11.6 first; see docs/ENVIRONMENT.md' >&2; exit 1; }
nvcc --version | grep -q 'release 11.6' || { echo 'CUDA toolkit 11.6 required' >&2; exit 1; }
for command in cmake gcc g++; do command -v "$command" >/dev/null || { echo "Missing system dependency: $command" >&2; exit 1; }; done
SETUP_SIGNATURE=$(sha256sum "$ROOT/requirements-wsl.txt" "$ROOT/tools/setup_upstream.py" "$ROOT/tools/setup_wsl.sh" | sha256sum | cut -d ' ' -f1)
if [[ -e "$ENV_DIR" ]]; then
  [[ -f "$ENV_DIR/.3dgs-setup-signature" && $(cat "$ENV_DIR/.3dgs-setup-signature") == "$SETUP_SIGNATURE" ]] || { echo 'Installer configuration changed or environment is unrelated; choose a NEW path' >&2; exit 1; }
  [[ -x "$ENV_DIR/bin/python" ]] || { echo 'Incomplete venv; choose a NEW path' >&2; exit 1; }
else
  python3.10 -m venv "$ENV_DIR"
  printf '%s\n' "$SETUP_SIGNATURE" >"$ENV_DIR/.3dgs-setup-signature"
fi
PY="$ENV_DIR/bin/python"
export PYTHONUNBUFFERED=1 MAX_JOBS=1 CMAKE_BUILD_PARALLEL_LEVEL=1
# 8.6+PTX matches the historical local build and supports forward JIT on RTX 4060.
export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.6+PTX}
export CUDA_HOME=${CUDA_HOME:-$(cd -- "$(dirname -- "$(command -v nvcc)")/.." && pwd)}
LOG_DIR="$ENV_DIR/setup-logs"
mkdir -p "$LOG_DIR"
job=''
trap 'if [[ -n "$job" ]]; then kill "$job" 2>/dev/null || true; wait "$job" 2>/dev/null || true; fi' EXIT INT TERM
stage() {
  local name=$1; shift
  if [[ "$name" != preflight && -f "$LOG_DIR/$name.exit" && $(cat "$LOG_DIR/$name.exit") == 0 ]]; then
    echo "SETUP_CHECKPOINT_SKIP stage=$name"
    return 0
  fi
  local start=$SECONDS rc=0
  "$@" >"$LOG_DIR/$name.log" 2>&1 & job=$!
  while kill -0 "$job" 2>/dev/null; do
    echo "SETUP_HEARTBEAT stage=$name pid=$job elapsed=$((SECONDS-start)) eta=unknown"
    tail -n 2 "$LOG_DIR/$name.log" || true
    sleep 5
  done
  wait "$job" || rc=$?; job=''
  echo "$rc" >"$LOG_DIR/$name.exit"
  tail -n 8 "$LOG_DIR/$name.log"
  return "$rc"
}
stage packaging "$PY" -m pip install 'pip==24.0' 'setuptools==68.2.2' 'wheel==0.41.3'
stage torch "$PY" -m pip install 'torch==1.12.1+cu116' 'torchvision==0.13.1+cu116' --extra-index-url https://download.pytorch.org/whl/cu116
stage python-deps "$PY" -m pip install -r "$ROOT/requirements-wsl.txt"
stage sources "$PY" "$ROOT/tools/setup_upstream.py"
SRC="$ROOT/工程/源码/GS-ICP-SLAM/submodules"
for name in fast_gicp simple-knn diff-gaussian-rasterization; do
  stage "$name" "$PY" -m pip install -v --no-deps --no-build-isolation "$SRC/$name"
done
stage preflight "$PY" "$ROOT/tools/preflight.py" --gpu
echo "ENV_READY: source '$ENV_DIR/bin/activate' (no reconstruction started)"
