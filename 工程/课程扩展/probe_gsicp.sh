set -eu
export PYTHONPATH=/root/.local/share/monogs/gsicp-packages:/root/.local/share/monogs/gsicp-packages/rerun_sdk:/root/.local/share/monogs/speedup-packages
export LD_LIBRARY_PATH=/root/.local/share/monogs/gsicp-native/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
cd /mnt/d/桌面/image/gpt-6/工程/源码/GS-ICP-SLAM
/root/.local/share/monogs/env-py310/bin/python -c 'import torch,pygicp,diff_gaussian_rasterization,rerun;from mp_Tracker import Tracker;from mp_Mapper import Mapper;print("GSICP_IMPORTS_OK",torch.__version__)'
