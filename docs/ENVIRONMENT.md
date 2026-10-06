# Windows + WSL2 + NVIDIA 环境

目标复现环境：WSL2 Ubuntu 22.04、Python 3.10、torch 1.12.1+cu116、numpy 1.23.5、CUDA toolkit/nvcc 11.6。历史本机记录为 Python 3.10.12、glibc 2.35、RTX 4060；新机安装和 GPU 两帧测试仍须实际验证。服务器 Ubuntu 20.04 / Python 3.8.10 / torch 2 + cu118 / nvcc 11.8 是另一环境，不能称为同一基线。

Windows PowerShell 先执行 `wsl --status`、`wsl -l -v`、`nvidia-smi`。未安装 WSL 时由用户执行 `wsl --install -d Ubuntu-22.04` 并完成首次用户设置，确认发行版 VERSION 为 2。使用支持 WSL 的 Windows NVIDIA 驱动；安装脚本不会更改驱动或系统服务。

在 WSL 中由用户明确安装系统依赖：

```bash
sudo apt update
sudo apt install python3.10 python3.10-venv python3-dev build-essential cmake git libeigen3-dev libpcl-dev libgl1 libglib2.0-0
```

CUDA 11.6 **toolkit** 需按 NVIDIA WSL 安装文档配置 WSL-Ubuntu 仓库后安装 `cuda-toolkit-11-6`，设置 `PATH=/usr/local/cuda-11.6/bin:$PATH` 与 `CUDA_HOME=/usr/local/cuda-11.6`。不要安装 Linux NVIDIA 驱动；`cuda`、`cuda-11-6`、`cuda-drivers` 元包会引入驱动。`nvidia-smi` 显示的 CUDA 数字代表驱动支持能力，不能代替 `nvcc --version`。

随后在仓库根目录执行：

```bash
bash tools/setup_wsl.sh
source .venv-wsl/bin/activate
python tools/preflight.py --gpu
```

脚本默认拒绝已有环境，安装日志与阶段退出码保存在新环境的 `setup-logs/`；失败时检查日志，结束上一安装进程后执行 `bash tools/setup_wsl.sh .venv-wsl --resume`。只有本安装器创建且配置签名一致的环境允许续跑；已成功阶段跳过，失败阶段重试。配置改变或无关环境仍须选择新目录。脚本使用固定源码及随仓库提供的 native 补丁，不复制历史 `/root` 路径。第一次编译可能较慢，日志每五秒显示心跳，ETA 无可靠依据时标为 unknown。

PyTorch 官方 cu116 索引有 Python 3.10 Linux x86_64 的 1.12.1 wheel；CUDA 扩展仍需要独立 nvcc 编译器。锁定的是复现目标，不表示新机已通过测试。硬件或编译器不兼容时保留错误日志，勿自行切换 torch/CUDA 后仍声称同协议环境。

官方依据（2026-10-06 核对）：[PyTorch previous versions](https://docs.pytorch.org/get-started/previous-versions/)、[cu116 wheel index](https://download.pytorch.org/whl/cu116/torch/)、[NVIDIA CUDA on WSL](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)、[Microsoft WSL 安装](https://learn.microsoft.com/windows/wsl/install)。
