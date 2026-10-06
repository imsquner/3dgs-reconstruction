set -eu
ps -p 204 --ppid 204 -o pid,ppid,rss,pcpu,etime,args
free -m
nvidia-smi --query-gpu=memory.used,utilization.gpu,temperature.gpu,power.draw,clocks.sm --format=csv
tail -3 /mnt/d/桌面/image/gpt-6/工程/运行/speedup-office-balanced30-half-full-5fps.log
