# 演示资产清单

仓库只含代码与 JSON 清单；以下大文件通过 GitHub Release `v0.2.0-demo-assets` 分发。

## 一键下载

```powershell
python tools/download_demo_assets.py           # 下载并校验
python tools/download_demo_assets.py --check   # 只校验
python tools/download_demo_assets.py --dry-run # 只打印计划
```

脚本会断点续传、校验 SHA256，并按上表路径放置。

## 文件表

路径均相对仓库根目录。

| 演示 | 文件 | 大小 |
|---|---|---:|
| 汇报① Replica | `工程/交互演示/assets/replica-web.ply` | 74.4 MB |
| 汇报② TUM GS-ICP | `工程/交互演示/assets/natural/tum-comparison/GSICP10-web.ply` | 31.5 MB |
| 汇报③ OOOSplat | `工程/交互演示/assets/natural/ooosplat-office/balanced/final.ply` | 112.7 MB |
| 演示① C3VD 103 | `工程/交互演示/assets/medical/tsdf/trans_t2_b/open3d_park_v0500/mesh_m.ply` | 5.3 MB |
| 演示② C3VD 276 | `工程/交互演示/assets/medical/tsdf/cecum_t1_a/open3d_park_v1000/mesh_m.ply` | 1.9 MB |

## 观测累计（可选，不发布）

以下文件只用于本地“观测累计”模式，仓库版按钮置灰：

```text
assets/natural/tum-comparison/GSICP10-observations.xyz / .rgb
assets/natural/ooosplat-office/balanced/observations.xyz / .rgb
assets/medical/tsdf/trans_t2_b/open3d_park_v0500/observations.xyz / .rgb
assets/medical/tsdf/trans_t2_b/open3d_park_v0500/input/*.jpg
assets/medical/tsdf/cecum_t1_a/open3d_park_v1000/observations.xyz / .rgb
assets/medical/tsdf/cecum_t1_a/open3d_park_v1000/input/*.jpg
```

## 校验

放置后核对文件大小与 `scene.json` 中的 `vertices` / `triangles`；页面加载失败时先看浏览器 Network 面板的 404 路径。
