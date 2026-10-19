#!/usr/bin/env bash
# 用指定模型重启网页渲染服务：restart_web.sh <模型目录>
set -uo pipefail
MODEL=${1:?usage: restart_web.sh <model_dir>}
for p in $(pgrep -f '[p]ython server.py'); do kill -9 "$p" 2>/dev/null; done
sleep 2
cd /home/ad/flow4dgs-local/web || exit 2
source /home/ad/flow4dgs-local/env/flow4dgs/bin/activate
MODEL_DIR="$MODEL" setsid nohup python server.py > /home/ad/flow4dgs-local/logs/web_server.log 2>&1 &
sleep 20
tail -4 /home/ad/flow4dgs-local/logs/web_server.log
