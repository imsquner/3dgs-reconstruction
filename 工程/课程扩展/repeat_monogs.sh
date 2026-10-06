set -eu
BASE=/mnt/d/桌面/image/gpt-6/工程
for repeat in 2 3;do
 MONOGS_DATA=/root/.local/share/monogs/gpt-6/data/tum-office bash "$BASE/课程扩展/run_experiment_v4.sh" "speedup-rgbd-balanced30-half240-native-5fps-r$repeat" 240 configs/rgbd/tum/fr3_office.yaml --preset balanced30 --downsample 2 --input-fps 5 --record
done
for repeat in 2 3;do
 MONOGS_DATA="$BASE/数据/EndoSLAM/tum-mono-subset240" bash "$BASE/课程扩展/run_experiment_v4.sh" "medical-mono240-5fps-r$repeat" 240 "$BASE/数据/EndoSLAM/tum-mono-subset240/mono.yaml" --preset fast --input-fps 5 --record
done
