#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用实测轴（up=+z, 焦点=视线交点）构造轨道相机，对比两种朝向约定。"""
import math
import os
import sys

import numpy as np
import torch
import yaml
from PIL import Image

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
OUT = "/mnt/d/Temp/orbit_test2"

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

rows = [ln.split() for ln in open(POSE_TXT, encoding="utf-8").read().strip().splitlines() if ln.strip()]
rows = [r for r in rows if len(r) == 4]
c2w = np.array(rows, dtype=np.float64).reshape(-1, 4, 4)
centers = c2w[:, :3, 3]
z_axis = c2w[:, :3, 2]
UP = (-c2w[:, :3, 1]).mean(0)          # 相机 y 向下 => 世界上 = -y_cam
UP = UP / np.linalg.norm(UP)
TARGET = np.median(centers + z_axis * 1.5, axis=0)   # 视线交点
D0 = float(np.median(np.linalg.norm(centers - TARGET, axis=1)))
print("UP", UP.round(3), "TARGET", TARGET.round(2), "D0", round(D0, 2))

os.makedirs(OUT, exist_ok=True)
W, H = 640, 480
proj = getProjectionMatrix2(0.01, 100.0, ds.cx, ds.cy, ds.fx, ds.fy, W, H).transpose(0, 1).cuda()
bg = torch.tensor([1.0, 1.0, 1.0], device="cuda")


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


def make(R, T):
    cam = Camera(0, torch.zeros(3, H, W, device="cuda"), np.zeros((H, W)), torch.eye(4), proj,
                 ds.fx, ds.fy, ds.cx, ds.cy, ds.fovx, ds.fovy, H, W, time=0.0,
                 motion_mask=torch.zeros(H, W, device="cuda", dtype=torch.bool), device="cuda")
    cam.update_RT(torch.as_tensor(R, dtype=torch.float32, device="cuda"),
                  torch.as_tensor(T, dtype=torch.float32, device="cuda"))
    with torch.no_grad():
        return render(cam, g, cfg["pipeline_params"], bg, dynamic=False, dx=dxyz(148), ds=0, dr=0)


def orbit(yaw_deg, pitch_deg, dist, flip, name):
    yr, pr = math.radians(yaw_deg), math.radians(pitch_deg)
    # 以 UP 为极轴的球面坐标
    e1 = np.array([1.0, 0.0, 0.0])
    e1 = e1 - UP * (e1 @ UP)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(UP, e1)
    pos = TARGET + dist * (math.cos(pr) * (math.cos(yr) * e1 + math.sin(yr) * e2) + math.sin(pr) * UP)
    f = TARGET - pos
    f /= np.linalg.norm(f)
    x = np.cross(UP, f)
    x /= np.linalg.norm(x)
    y = np.cross(f, x)
    if flip:
        y = -y
    R = np.stack([x, y, f], axis=0)
    T = -R @ pos
    pkg = make(R, T)
    img = (pkg["render"].clamp(0, 1).permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)
    Image.fromarray(img).save(os.path.join(OUT, f"{name}.png"))
    print(name, "mean", round(float(img.mean()), 1))


for flip in (False, True):
    tag = "flip" if flip else "noflip"
    orbit(0, 5, D0 * 1.2, flip, f"a_{tag}_yaw0")
    orbit(35, 15, D0 * 1.3, flip, f"b_{tag}_yaw35")
