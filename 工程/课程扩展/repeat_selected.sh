set -eu
BASE=/mnt/d/桌面/image/gpt-6/工程
for repeat in 1 2 3;do
 bash "$BASE/课程扩展/run_gsicp.sh" "gsicp-office240-10fps-repeat$repeat" 240 10 1
done
for repeat in 2 3;do
 MONOGS_DATA="$BASE/数据/EndoSLAM/tum-mono-subset240" bash "$BASE/课程扩展/run_experiment_v4.sh" "medical-mono240-5fps-r$repeat" 240 "$BASE/数据/EndoSLAM/tum-mono-subset240/mono.yaml" --preset fast --input-fps 5 --record
done
