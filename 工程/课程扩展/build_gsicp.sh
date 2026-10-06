set -eu
BASE=/mnt/d/桌面/image/gpt-6/工程
SRC="$BASE/源码/GS-ICP-SLAM"
PREFIX=/root/.local/share/monogs/gsicp-native
TARGET=/root/.local/share/monogs/gsicp-packages
export PYTHONUNBUFFERED=1
export PYTHONPATH=/root/.local/share/monogs/speedup-packages
export PATH=/root/.local/share/monogs/speedup-packages/bin:$PATH
export LD_LIBRARY_PATH="$PREFIX/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export CMAKE_PREFIX_PATH="$PREFIX/usr"
export CMAKE_BUILD_PARALLEL_LEVEL=1 MAX_JOBS=1 TORCH_CUDA_ARCH_LIST='8.6+PTX'
export CC=/root/.local/share/monogs/gcc10/usr/bin/gcc-10 CXX=/root/.local/share/monogs/gcc10/usr/bin/g++-10
export CUDA_HOME=/usr
export CPLUS_INCLUDE_PATH="$PREFIX/usr/include:$PREFIX/usr/include/eigen3:$PREFIX/usr/include/pcl-1.12:$PREFIX/usr/include/x86_64-linux-gnu"
PY=/root/.local/share/monogs/env-py310/bin/python
mkdir -p "$BASE/运行/gsicp-env" "$TARGET"
build_job(){
 name=$1;shift
 : > "$BASE/运行/gsicp-env/$name.log"
 "$@" > "$BASE/运行/gsicp-env/$name.log" 2>&1 & job=$!
 start=$(date +%s)
 while kill -0 "$job" 2>/dev/null;do echo "BUILD_HEARTBEAT name=$name pid=$job elapsed=$(( $(date +%s)-start )) $(date -Iseconds)";tail -2 "$BASE/运行/gsicp-env/$name.log" || true;sleep 10;done
 rc=0;wait "$job" || rc=$?;echo "$rc" > "$BASE/运行/gsicp-env/$name.exit";tail -8 "$BASE/运行/gsicp-env/$name.log";test "$rc" -eq 0
}
if [ -f "$BASE/运行/gsicp-env/fast-gicp.exit" ] && [ "$(cat "$BASE/运行/gsicp-env/fast-gicp.exit")" = 0 ];then echo 'REUSE fast-gicp successful build';else
build_job fast-gicp env CC=/usr/bin/gcc CXX=/usr/bin/g++ "$PY" -m pip install -v --upgrade --no-deps --no-build-isolation --target "$TARGET" "$SRC/submodules/fast_gicp"
fi
if [ -f "$BASE/运行/gsicp-env/rasterizer.exit" ] && [ "$(cat "$BASE/运行/gsicp-env/rasterizer.exit")" = 0 ];then echo 'REUSE rasterizer';else
build_job rasterizer "$PY" -m pip install -v --no-deps --no-build-isolation --target "$TARGET" "$SRC/submodules/diff-gaussian-rasterization"
fi
test -d "$TARGET/rerun_sdk" || build_job rerun "$PY" -m pip install --no-deps --target "$TARGET" 'rerun-sdk==0.16.1'
test -d "$TARGET/pyarrow" || build_job pyarrow "$PY" -m pip install --no-deps --target "$TARGET" 'pyarrow==15.0.2'
export PYTHONPATH="$TARGET:$TARGET/rerun_sdk:/root/.local/share/monogs/speedup-packages"
cd "$SRC"
"$PY" -c 'import pygicp,diff_gaussian_rasterization,rerun;from mp_Tracker import Tracker;from mp_Mapper import Mapper;print("GSICP_IMPORTS_OK")'
