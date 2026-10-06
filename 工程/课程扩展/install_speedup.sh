set -eu
export PYTHONUNBUFFERED=1 MAX_JOBS=2 TORCH_CUDA_ARCH_LIST='8.6+PTX' CUDA_HOME=/usr
export CC=/root/.local/share/monogs/gcc10/usr/bin/gcc-10 CXX=/root/.local/share/monogs/gcc10/usr/bin/g++-10
PY=/root/.local/share/monogs/env-py310/bin/python
OUT=/mnt/d/桌面/image/gpt-6/工程/运行/speedup-env
TARGET=/root/.local/share/monogs/speedup-packages
mkdir -p "$OUT" "$TARGET"
export PYTHONPATH="$TARGET"
stage() {
 name=$1; shift
 "$@" > "$OUT/$name.log" 2>&1 & job=$!
 echo "START stage=$name pid=$job"
 while kill -0 "$job" 2>/dev/null; do echo "HEARTBEAT stage=$name logbytes=$(stat -c %s "$OUT/$name.log") $(date -Iseconds)"; tail -2 "$OUT/$name.log"; sleep 10; done
 rc=0; wait "$job" || rc=$?
 echo "$rc" > "$OUT/$name.exit"
 tail -12 "$OUT/$name.log"
 return "$rc"
}
stage lietorch "$PY" -m pip install -v --no-deps --no-build-isolation --target "$TARGET" /mnt/d/桌面/image/gpt-6/工程/源码/lietorch
stage lycon "$PY" -m pip install -v --no-deps --no-build-isolation --target "$TARGET" lycon==0.2.0
stage probe "$PY" -c 'import torch, lietorch, lycon; x=torch.zeros(1,6,device="cuda",requires_grad=True); y=lietorch.SE3.exp(x).matrix(); y.sum().backward(); torch.cuda.synchronize(); assert torch.isfinite(x.grad).all(); print("LIE_CUDA_FORWARD_BACKWARD_OK",y.detach().cpu())'
