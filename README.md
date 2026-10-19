# 3DGS Reconstruction · 演示版

课程演示仓库：**3 条自然场景 + 2 条医学 C3VD 网格 + 1 组 4D 动态**。只保留演示所需代码、场景清单与文档；模型、点云、视频和数据集不进入 Git。

## 演示清单

| 编号 | 演示 | 路线 | 输入 | 结果 |
|---|---|---|---|---|
| 汇报① | Replica office0 | GS-ICP 在线 RGB-D SLAM | 1801 帧 RGB-D | 1,146,721 高斯 |
| 汇报② | TUM office | GS-ICP 在线 RGB-D SLAM | 2515 帧 RGB-D | 484,990 高斯 |
| 汇报③ | TUM office | COLMAP + OOOBrush 离线 | 2585 张 RGB | 500,544 高斯 |
| 演示① | C3VD `trans_t2_b` | Open3D Park 里程计 + TSDF | 103 帧 RGB-D | 53,850 顶点网格 |
| 演示② | C3VD `cecum_t1_a` | Open3D Park 里程计 + TSDF | 276 帧 RGB-D | 20,356 顶点网格 |

4D 动态（Flow4DGS-SLAM，TUM fr3 三条序列）在 [`工程/4dgs/`](工程/4dgs/README.md)。

## 快速开始

需要 Python 3.10+ 和支持 WebGL2 的浏览器。**仓库不含大文件**，请先按 [`docs/ASSETS.md`](docs/ASSETS.md) 把 PLY 放到对应目录，再启动：

```powershell
python 工程/交互演示/server.py --host 127.0.0.1 --port 8765
```

打开 <http://127.0.0.1:8765/>。请用 HTTP 服务访问，不要双击 HTML。

4D 回放：

```powershell
python 工程/4dgs/网页/server.py --port 8770
```

## 目录

```text
工程/交互演示/     网页源码、catalog、场景 JSON、构建/适配脚本
工程/4dgs/         4D 回放服务、方案与验收文档
工程/课程扩展/     数据准备与 GS-ICP 运行脚本
docs/              来源、资产清单、展示边界、运行说明
tools/             资产下载与校验脚本
```

## 边界

- 汇报①② 无回环、无全局 BA，轨迹会漂移；ATE 只能与同口径比较。
- 汇报③ 是离线 SfM + 训练，**无实时性、无绝对尺度**。
- 演示①② 只用 RGB + 注册参考深度估计位姿，GT 位姿仅用于评价。
- 观测累计（点云回放）资产不随仓库发布，仓库版按钮置灰。
- 4DGS 是训练视角重建，不能环绕；±15°/±10°/±0.2 m 是安全范围。

## 上游与许可

见 [`docs/UPSTREAM.md`](docs/UPSTREAM.md)。本仓库不打包第三方源码，复现按其中 commit 拉取；C3VD 等数据不重新分发。
