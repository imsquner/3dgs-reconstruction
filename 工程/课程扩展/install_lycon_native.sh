set -eu
P=/root/.local/share/monogs/native-headers
mkdir -p "$P/debs"
cd "$P/debs"
cp /mnt/d/桌面/image/gpt-6/工程/依赖/native-debs/libpng-dev.deb "$P/debs/libpng-dev.deb"
for d in *.deb; do dpkg-deb -x "$d" "$P"; done
ln -sfn /usr/lib/x86_64-linux-gnu/libpng16.so.16 "$P/usr/lib/x86_64-linux-gnu/libpng16.so"
ln -sfn /usr/lib/x86_64-linux-gnu/libjpeg.so.8 "$P/usr/lib/x86_64-linux-gnu/libjpeg.so"
export CMAKE_PREFIX_PATH="$P/usr"
export CPLUS_INCLUDE_PATH="$P/usr/include/x86_64-linux-gnu" C_INCLUDE_PATH="$P/usr/include/x86_64-linux-gnu"
export PYTHONPATH=/root/.local/share/monogs/speedup-packages
export PATH=/root/.local/share/monogs/speedup-packages/bin:$PATH
export CC=/root/.local/share/monogs/gcc10/usr/bin/gcc-10 CXX=/root/.local/share/monogs/gcc10/usr/bin/g++-10
OUT=/mnt/d/桌面/image/gpt-6/工程/运行/speedup-env
/root/.local/share/monogs/env-py310/bin/python -m pip install -v --no-deps --no-build-isolation --target /root/.local/share/monogs/speedup-packages lycon==0.2.0 > "$OUT/lycon-native.log" 2>&1 & job=$!
while kill -0 "$job" 2>/dev/null; do echo "HEARTBEAT lycon-native $(date -Iseconds)"; tail -2 "$OUT/lycon-native.log"; sleep 10; done
rc=0;wait "$job" || rc=$?;echo "$rc" > "$OUT/lycon-native.exit"
tail -14 "$OUT/lycon-native.log"
exit "$rc"
