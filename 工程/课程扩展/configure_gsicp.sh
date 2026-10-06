set -eu
export PYTHONPATH=/root/.local/share/monogs/speedup-packages
export CMAKE_PREFIX_PATH=/root/.local/share/monogs/gsicp-native/usr
/root/.local/share/monogs/speedup-packages/bin/cmake -S /mnt/d/桌面/image/gpt-6/工程/源码/GS-ICP-SLAM/submodules/fast_gicp -B /root/.local/share/monogs/gsicp-configure2 -DBUILD_PYTHON_BINDINGS=ON -DBUILD_apps=OFF -DBoost_NO_BOOST_CMAKE=ON -DPYTHON_EXECUTABLE=/root/.local/share/monogs/env-py310/bin/python
