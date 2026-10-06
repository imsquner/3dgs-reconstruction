set -eu
export PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 WANDB_MODE=disabled MPLBACKEND=Agg
BASE=/mnt/d/桌面/image/gpt-6/工程
export MONOGS_SOURCE="${MONOGS_SOURCE:-$BASE/源码/MonoGS-speedup}"
export PYTHONPATH=/root/.local/share/monogs/speedup-packages${PYTHONPATH:+:$PYTHONPATH}
export MONOGS_COMMIT="${MONOGS_COMMIT:-6fdcfd8f9507958d7bbc3451d8c586211db81a85}"
export MONOGS_DATA="${MONOGS_DATA:-/mnt/d/桌面/image/MonoGS/datasets/tum/rgbd_dataset_freiburg3_long_office_household}"
export MONOGS_CONFIG="$3"
NAME=$1
FRAMES=$2
shift 3
if [ -e "$BASE/运行/$NAME.log" ]; then echo 'Existing run; choose a new ID'; exit 2; fi
mkdir -p "$BASE/运行/源码快照"
cp "$BASE/课程扩展/experiment_runner_v2.py" "$BASE/运行/源码快照/$NAME.py"
/root/.local/share/monogs/env-py310/bin/python "$BASE/运行/源码快照/$NAME.py" --frames "$FRAMES" --output "$BASE/运行/$NAME" "$@" > "$BASE/运行/$NAME.log" 2>&1 & job=$!
echo "$job" > "$BASE/运行/$NAME.pid"
echo "START name=$NAME pid=$job frames=$FRAMES config=$MONOGS_CONFIG"
start_time=$(date +%s)
while kill -0 "$job" 2>/dev/null; do
 count=0
 if [ -f "$BASE/运行/$NAME/frames.jsonl" ]; then count=$(wc -l < "$BASE/运行/$NAME/frames.jsonl"); fi
 elapsed=$(( $(date +%s) - start_time )); eta=unknown
 if [ "$count" -gt 0 ]; then eta=$(( elapsed * (FRAMES-count) / count )); fi
 echo "HEARTBEAT $(date -Iseconds) pid=$job completed=$count/$FRAMES elapsed=$elapsed eta_seconds=$eta"
 printf '%s,' "$(date -Iseconds)" >> "$BASE/运行/$NAME.resources.csv"
 nvidia-smi --query-gpu=memory.used,utilization.gpu,temperature.gpu,power.draw --format=csv,noheader,nounits >> "$BASE/运行/$NAME.resources.csv"
 tail -2 "$BASE/运行/$NAME.log"
 sleep 10
done
rc=0; wait "$job" || rc=$?
echo "$rc" > "$BASE/运行/$NAME.exit"
tail -20 "$BASE/运行/$NAME.log"
echo "END name=$NAME exit=$rc"
exit "$rc"
