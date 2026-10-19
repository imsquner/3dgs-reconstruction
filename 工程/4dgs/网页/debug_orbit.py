#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断轨道相机的坐标系约定：试几种 up / 朝向组合，看哪种能渲染出内容。"""
import math
import os
import sys

import numpy as np
import torch
import yaml

REPO = "/home/ad/flow4dgs-local/src/Flow4DGS-SLAM"
sys.path.insert(0, REPO)
os.chdir(REPO)

from munch import munchify
from gaussian_splatting.gaussian_renderer import render
from gaussian_splatting.scene.gaussian_model import GaussianModel
from gaussian_splatting.utils.graphics_utils import getProjectionMatrix2
from utils.camera_utils import Camera
from utils.dataset import load_dataset

MODEL_DIR = "/home/ad/flow4dgs-local/models/full298"
DATA = "/home/ad/flow4dgs-local/data/tum/rgbd_dataset_freiburg3_walking_xyz"
POSE_TXT = "/mnt/d/桌面/image/4dgs/Flow4DGS_model_all_frames/pose.txt"

cfg_raw = yaml.safe_load(open(os.path.join(MODEL_DIR, "config.yml"), encoding="utf-8"))
cfg_raw.pop("inherit_from", None)
cfg = munchify(cfg_raw)
cfg["Dataset"]["dataset_path"] = DATA
ds = load_dataset(None, None, cfg)
g = GaussianModel(cfg["model_params"]["sh_degree"], config=cfg, args=None,
                  init_deform="offset", nframes=len(ds))
g.load_ply(os.path.join(MODEL_DIR, "point_cloud.ply"))
g.load_offsets(os.path.join(MODEL_DIR, "offsets.pth"))
kf = list(g.kf_list)
xyz = g.get_xyz.detach().cpu().numpy()
center = np.median(xyz, axis=0)

rows = [ln.split() for ln in open(POSE_TXT, encoding="utf-8").read().strip().splitlines() if ln.strip()]
rows = [r for r in rows if len(r) == 4]
c2w = np.array(rows, dtype=np.float64).reshape(-1, 4, 4)
cam_centers = c2w[:, :3, 3]
print("scene center", center.round(2))
print("camera centers: median", np.median(cam_centers, axis=0).round(2),
      "dist to center median", np.median(np.linalg.norm(cam_centers - center, axis=1)).round(2))

W, H = 320, 240
proj = getProjectionMatrix2(0.01, 100.0, ds.cx * W / 640, ds.cy * H / 480,
                            ds.fx * W / 640, ds.fy * H / 480, W, H).transpose(0, 1).cuda()
bg = torch.tensor([1.0, 1.0, 1.0], device="cuda")


def make_cam(R, T, idx=0):
    cam = Camera(idx, torch.zeros(3, H, W, device="cuda"), np.zeros((H, W)), torch.eye(4), proj,
                 ds.fx * W / 640, ds.fy * H / 480, ds.cx * W / 640, ds.cy * H / 480,
                 2 * math.atan(W / (2 * ds.fx * W / 640)), 2 * math.atan(H / (2 * ds.fy * H / 480)),
                 H, W, time=0.0, motion_mask=torch.zeros(H, W, device="cuda", dtype=torch.bool),
                 device="cuda")
    cam.update_RT(torch.as_tensor(R, dtype=torch.float32, device="cuda"),
                  torch.as_tensor(T, dtype=torch.float32, device="cuda"))
    return cam


def dxyz(idx):
    if idx <= kf[0]:
        return g.get_delta_xyz(0)
    if idx >= kf[-1]:
        return g.get_delta_xyz(len(kf) - 1)
    lo = max(i for i, k in enumerate(kf) if k <= idx)
    hi = min(i for i, k in enumerate(kf) if k >= idx)
    if lo == hi:
        return g.get_delta_xyz(lo)
    w = (idx - kf[lo]) / float(kf[hi] - kf[lo])
    return (1 - w) * g.get_delta_xyz(lo) + w * g.get_delta_xyz(hi)


def look_at(pos, target, up):
    z = target - pos
    z = z / (np.linalg.norm(z) + 1e-9)     # 相机 +z 指向场景（OpenCV 前向）
    x = np.cross(up, z)
    x = x / (np.linalg.norm(x) + 1e-9)
    y = np.cross(z, x)
    R = np.stack([x, y, z], axis=0)
    T = -R @ pos
    return R, T


def stat(img):
    a = img.clamp(0, 1).permute(1, 2, 0).cpu().numpy()
    dark = float((a.sum(axis=2) < 2.7).mean())
    return f"mean={a.mean():.3f} std={a.std():.3f} 非白像素={1 - dark:.3f}"


for name, up, dist in [
    ("up=+y, d=3", np.array([0.0, 1.0, 0.0]), 3.0),
    ("up=-y, d=3", np.array([0.0, -1.0, 0.0]), 3.0),
    ("up=-z, d=3", np.array([0.0, 0.0, -1.0]), 3.0),
    ("up=+y, d=1.5", np.array([0.0, 1.0, 0.0]), 1.5),
]:
    pos = center + dist * np.array([0.0, 0.3, 1.0]) / np.linalg.norm([0.0, 0.3, 1.0])
    R, T = look_at(pos, center, up)
    cam = make_cam(R, T)
    with torch.no_grad():
        pkg = render(cam, g, cfg["pipeline_params"], bg, dynamic=False, dx=dxyz(0), ds=0, dr=0)
    print(f"{name:14s} {stat(pkg['render'])}")
