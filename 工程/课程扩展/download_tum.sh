set -eu
OUT=/mnt/d/桌面/image/gpt-6/工程/数据/TUM
mkdir -p "$OUT"
for seq in xyz desk; do
 file="rgbd_dataset_freiburg1_${seq}.tgz"
 if [ -f "$OUT/$file" ]; then echo "EXISTS $file"; continue; fi
 url="https://vision.in.tum.de/rgbd/dataset/freiburg1/$file"
 echo "DOWNLOAD $url"
 curl --fail --location --retry 2 --connect-timeout 20 --continue-at - --output "$OUT/$file.part" "$url" > "$OUT/$seq-download.log" 2>&1 & job=$!
 while kill -0 "$job" 2>/dev/null; do echo "HEARTBEAT dataset=$seq bytes=$(stat -c %s "$OUT/$file.part" 2>/dev/null || echo 0) $(date -Iseconds)"; sleep 10; done
 rc=0; wait "$job" || rc=$?
 echo "$rc" > "$OUT/$seq-download.exit"
 if [ "$rc" -ne 0 ]; then tail -5 "$OUT/$seq-download.log"; exit "$rc"; fi
 mv "$OUT/$file.part" "$OUT/$file"
 sha256sum "$OUT/$file" > "$OUT/$file.sha256"
 echo "DOWNLOADED $seq"
done
