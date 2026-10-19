#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""推算 TUM 世界坐标下的真实上方向与合理观察点。"""
import os

import numpy as np

POSE_TXT = "/mnt/d/桌面/image/4dgs/Flow4DGS_model_all_frames/pose.txt"
rows = [ln.split() for ln in open(POSE_TXT, encoding="utf-8").read().strip().splitlines() if ln.strip()]
rows = [r for r in rows if len(r) == 4]
c2w = np.array(rows, dtype=np.float64).reshape(-1, 4, 4)

centers = c2w[:, :3, 3]
x_axis = c2w[:, :3, 0]   # 相机右
y_axis = c2w[:, :3, 1]   # 相机下（OpenCV）
z_axis = c2w[:, :3, 2]   # 相机前

print("相机中心 均值", centers.mean(0).round(2))
print("相机中心 范围", centers.min(0).round(2), "~", centers.max(0).round(2))
print("相机 y 轴（下）均值", y_axis.mean(0).round(3))
print("相机 z 轴（前）均值", z_axis.mean(0).round(3))
print("=> 世界“上”方向 ≈", (-y_axis.mean(0)).round(3))

# 相机前方 1.5m 处的点集合，作为观察目标（视线焦点）
targets = centers + z_axis * 1.5
print("视线焦点 均值", targets.mean(0).round(2), "中位", np.median(targets, axis=0).round(2))

# 场景包围盒估计（用相机位置 + 焦点）
pts = np.vstack([centers, targets])
print("场景范围 最小", pts.min(0).round(2), "最大", pts.max(0).round(2))
print("相机间距 中位", np.median(np.linalg.norm(np.diff(centers, axis=0), axis=1)).round(3))
