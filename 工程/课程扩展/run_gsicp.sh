set -eu
BASE=/mnt/d/桌面/image/gpt-6/工程
NAME=$1
export GSICP_FRAMES=$2 GSICP_INPUT_FPS=$3 GSICP_RECORD=${4:-0}
export GSICP_SOURCE="$BASE/源码/GS-ICP-SLAM" GSICP_COMMIT=5f996a872a979406b270fe0ee3b0a8f25c5e9ae3
export GSICP_DATA=${GSICP_DATA:-/root/.local/share/monogs/gpt-6/data/tum-office}
export GSICP_CONFIG=${GSICP_CONFIG:-$GSICP_SOURCE/configs/TUM/rgbd_dataset_freiburg3_long_office_household.txt}
export GSICP_OUTPUT="$BASE/运行/$NAME"
export PYTHONPATH=/root/.local/share/monogs/gsicp-packages:/root/.local/share/monogs/gsicp-packages/rerun_sdk:/root/.local/share/monogs/speedup-packages
export LD_LIBRARY_PATH=/root/.local/share/monogs/gsicp-native/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 PYTHONUNBUFFERED=1 MPLBACKEND=Agg
test ! -e "$BASE/运行/$NAME.log"
cp "$BASE/课程扩展/gsicp_runner.py" "$BASE/运行/源码快照/$NAME.py"
/root/.local/share/monogs/env-py310/bin/python "$BASE/运行/源码快照/$NAME.py" > "$BASE/运行/$NAME.log" 2>&1 & job=$!
echo "$job" > "$BASE/运行/$NAME.pid";start=$(date +%s)
while kill -0 "$job" 2>/dev/null;do
 count=0;test ! -e "$GSICP_OUTPUT/frames.jsonl" || count=$(wc -l < "$GSICP_OUTPUT/frames.jsonl")
 elapsed=$(( $(date +%s)-start ));eta=unknown;test "$count" -eq 0 || eta=$((elapsed*(GSICP_FRAMES-count)/count))
 echo "RUN_HEARTBEAT name=$NAME completed=$count/$GSICP_FRAMES elapsed=$elapsed eta=$eta";tail -2 "$BASE/运行/$NAME.log"
 printf '%s,' "$(date -Iseconds)" >> "$BASE/运行/$NAME.resources.csv"
 nvidia-smi --query-gpu=memory.used,utilization.gpu,temperature.gpu,power.draw --format=csv,noheader,nounits >> "$BASE/运行/$NAME.resources.csv"
 sleep 10
done
rc=0;wait "$job" || rc=$?
echo "$rc" > "$BASE/运行/$NAME.exit";tail -15 "$BASE/运行/$NAME.log";exit "$rc"
