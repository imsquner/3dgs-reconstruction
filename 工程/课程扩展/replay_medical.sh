set -eu
export PYTHONPATH=/root/.local/share/monogs/speedup-packages
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
BASE=/mnt/d/桌面/image/gpt-6/工程
RUN="$BASE/运行/medical-mono240-5fps"
mkdir -p "$RUN/map-replay"
/root/.local/share/monogs/env-py310/bin/python "$BASE/view_map.py" "$RUN" --screenshot "$RUN/map-replay/shifted-view.png" --offset-x .01
