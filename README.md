# 3DGS Reconstruction

RGB-D 场景重建算法与三维网站查看器的团队协作仓库。包含基于 GS-ICP-SLAM 的工程适配、固定预算实验模块和浏览器交互查看器。

## 内容

- `工程/课程扩展/TUM跨场景迭代/`：算法改进、版本化 runner、评价与测试；当前最新已实现 runner 为 `run_online_v18.py`。历史版本是开发记录，不代表每个版本成功。
- `工程/课程扩展/`：运行、评价和环境辅助脚本。
- `工程/服务器/projection.py`：相机投影适配；不包含服务器凭据或远程账号。
- `工程/交互演示/`：网站源码、依赖和场景元数据。
- `docs/`：协作方式、忽略规则、来源与资产清单。

## 网站

需要 Python 3、支持 WebGL2 的浏览器。第三方浏览器依赖已附带许可证并随源码提交。

```sh
python tools/check_assets.py
python 工程/交互演示/server.py --host 127.0.0.1 --port 8765
```

打开 http://127.0.0.1:8765 。大地图与观测缓冲不在 Git 中，首次克隆须向维护者取得资产包，按照 `docs/assets-manifest.json` 放置并验证。无资产时服务与静态页面可启动，但无法加载场景，不表示网站完整运行成功。不要直接双击 HTML。

## 算法

需要 Linux、NVIDIA CUDA 环境和 GS-ICP-SLAM 的原生依赖；Windows 本轮只验证源码及独立测试，未在新 checkout 重新构建 GPU 环境或训练。

```sh
python tools/setup_upstream.py
```

该命令下载固定版本第三方源代码到现有 runner 预期的目录（详见 `docs/UPSTREAM.md`），校验快照，应用已记录的原生补丁；不安装系统软件或启动实验。先阅读各上游许可证及安装说明，再按上游 requirements 编译 `fast_gicp`、rasterizer、simple-knn。复制原生二进制不能替代环境重建。

场景协议中 `/datasets/<scene>` 是公开占位路径，需要改为本机真实路径；可调用 `portable_protocol.rebase_protocol`，并在本机重建和核验观测清单。不要将重新落地的路径或新的运行 hash 误称原冻结实验的字节级复现。原 runner 保留历史路径逻辑，迁移后先做低成本完整链路验证，再决定正式运行。

## 协作

从 `main` 建功能分支；通过 Pull Request 审阅后合并。环境与数据准备见 `docs/UPSTREAM.md`，提交规则见 `CONTRIBUTING.md`。

## 结论边界与许可

已有短段开发结果不能证明完整长序列或医学精度成功；自由视角地图仍可能有毛刺、漂浮与孔洞。本仓库不宣称原创 3DGS 算法或临床可用性。

第三方源码通过固定上游版本获取；GS-ICP-SLAM 及其依赖具有混合许可，不能把本仓库所有内容统一视为 MIT。MonoGS 仅列来源，不再发布其源码和本地派生副本。原创新增内容当前未授予通用开源许可证，公共可见不等于任意商业使用许可；后续由作者明确授权。
