set -eu
export PYTHONPATH=/root/.local/share/monogs/gsicp-packages:/root/.local/share/monogs/gsicp-packages/rerun_sdk:/root/.local/share/monogs/speedup-packages
export LD_LIBRARY_PATH=/root/.local/share/monogs/gsicp-native/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 PYTHONUNBUFFERED=1
BASE=/mnt/d/桌面/image/gpt-6/工程
gdb --batch -ex run -ex 'thread apply all bt 15' --args /root/.local/share/monogs/env-py310/bin/python "$BASE/课程扩展/repro_gicp.py" > "$BASE/运行/gsicp-env/gicp-native-debug.log" 2>&1 & job=$!
while kill -0 "$job" 2>/dev/null;do echo "DEBUG_HEARTBEAT pid=$job $(date -Iseconds)";tail -4 "$BASE/运行/gsicp-env/gicp-native-debug.log" || true;sleep 10;done
rc=0;wait "$job" || rc=$?;tail -30 "$BASE/运行/gsicp-env/gicp-native-debug.log";exit "$rc"
