# 4DGS · Flow4DGS-SLAM 动态场景

本目录只保留 **4D 动态重建** 的演示代码与文档，模型权重、全帧渲染和录屏不进入 Git。

## 上游

- 代码：`wangys16/Flow4DGS-SLAM` @ `ecb4e94`
- 论文：Flow4DGS-SLAM: Optical Flow-Guided 4D Gaussian Splatting SLAM（CVPR 2026 Highlight，arXiv 2604.22339）
- 数据：TUM RGB-D `fr3_walking_xyz` / `fr3_walking_static` / `fr3_sitting_static`，各 298 帧

## 目录

```text
网页/     本地回放服务（server.py + static/），8770 端口
方案/     复现、执行、本地重跑交接方案
交付/     成果说明与验收报告
```

## 运行

```powershell
cd 工程/4dgs/网页
python server.py --port 8770
```

打开 `http://127.0.0.1:8770/`。页面读取本地已导出的模型与全帧渲染，不重新训练。

## 边界

- 297/298 帧训练视角重建，不是新视角泛化评测。
- 相机 10 秒内移动不到 1 米，**不能绕场景环绕**；±15°/±10°/±0.2 m 是安全范围。
- 时间轴形变是关键帧线性插值（62 个关键帧），快速运动部位会糊。
- PSNR 有两个口径：官方掩码约 56% 覆盖率，全像素低 3–4 dB。
- 单目未拍到的角度没有数据，任何实现都补不出背面。
