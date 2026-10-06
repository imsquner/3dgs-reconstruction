# 第三方来源与版本

GS-ICP-SLAM：https://github.com/Lab-of-AI-and-Robotics/GS_ICP_SLAM ，commit `5f996a872a979406b270fe0ee3b0a8f25c5e9ae3`。根 MIT，部分 Inria 文件采用非商业研究许可；请阅读文件头和相关上游完整许可。

原生依赖：

- fast_gicp：https://github.com/Lab-of-AI-and-Robotics/fast_gicp ，`e2954b1aa06a563d1b2ef2ec5d1fddd1e911d8f4`，BSD-3；保留本项目 PCL 兼容修复 patch。
- diff-gaussian-rasterization：https://github.com/Lab-of-AI-and-Robotics/diff-gaussian-rasterization ，`95dbb69d81449ae56783628803198bea2f42e2c9`，Inria 非商业研究许可。
- simple-knn：https://github.com/camenduru/simple-knn ，`44f764299fa305faf6ec5ebd99939e0508331503`，安装前阅读获取版本的许可。

MonoGS：https://github.com/muskie82/MonoGS ，`6c9254c319d8bff5caeef65259e6bb0941a9b9f6`。其专用条款限制复制、转让及第三方访问，本公共仓库不打包源码或本地 speedup 派生副本。队友从上游获取时自行阅读并接受条款。

网站：GaussianSplats3D 0.4.7、Three.js 0.170.0（MIT），Lucide（ISC，含 Feather MIT）；完整许可在 `工程/交互演示/vendor/`。

数据：TUM https://vision.in.tum.de/data/datasets/rgbd-dataset 、Replica https://github.com/facebookresearch/Replica-Dataset 、EndoSLAM https://github.com/CapsuleEndoscope/EndoSLAM 、C3VD https://durrlab.github.io/C3VD/ 。本仓库不重新分发数据或承诺这些来源具有相同许可。

获取脚本仅执行 Git 固定版本获取、源码校验与已记录补丁。不安装依赖、不训练。两个 GS-ICP 目录保持同一固定 commit，runner 使用隔离快照；本机二进制需重建。历史 freeze/audit 脚本仍需原实验资料，不保证无数据的新 checkout 能运行每个历史脚本。
