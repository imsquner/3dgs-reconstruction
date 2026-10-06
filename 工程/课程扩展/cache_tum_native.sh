set -eu
SRC=/mnt/d/桌面/image/MonoGS/datasets/tum/rgbd_dataset_freiburg3_long_office_household
DST=/root/.local/share/monogs/gpt-6/data/tum-office
mkdir -p "$DST"
cp -au "$SRC/." "$DST/" & job=$!
while kill -0 "$job" 2>/dev/null; do echo "CACHE_HEARTBEAT pid=$job bytes=$(du -sb "$DST" | cut -f1) $(date -Iseconds)"; sleep 10; done
rc=0; wait "$job" || rc=$?
if [ "$rc" -eq 0 ]; then echo 'CACHE_COPY_COMPLETE'; find "$DST/rgb" -name '*.png' | wc -l; find "$DST/depth" -name '*.png' | wc -l; fi
exit "$rc"
