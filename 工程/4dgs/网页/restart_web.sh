#!/usr/bin/env bash
# 重启网页渲染服务
set -uo pipefail
for p in $(pgrep -f '[p]ython server.py'); do kill -9 "$p" 2>/dev/null; done
sleep 2
cd /home/ad/flow4dgs-local/web || exit 2
source /home/ad/flow4dgs-local/env/flow4dgs/bin/activate
setsid nohup python server.py > /home/ad/flow4dgs-local/logs/web_server.log 2>&1 &
sleep 18
tail -5 /home/ad/flow4dgs-local/logs/web_server.log
echo "--- 端口 ---"
ss -ltn | grep -E '8770|8771'
