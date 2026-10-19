#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比几种轨道相机设置，输出图片供人眼判断。"""
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
OUT = "/mnt/d/Temp/orbit_test"

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
cam_centers = c2w[:, :3, 3]
target = np.median(cam_centers, axis=0)
print("target (camera median)", target.round(2))

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


def render_orbit(yaw, pitch, dist, up, name):
    yr, pr = math.radians(yaw), math.radians(pitch)
    pos = target + dist * np.array([math.cos(pr) * math.sin(yr), math.sin(pr), math.cos(pr) * math.cos(yr)])
    z = target - pos
    z = z / (np.linalg.norm(z) + 1e-9)
    x = np.cross(up, z)
    x = x / (np.linalg.norm(x) + 1e-9)
    y = np.cross(z, x)
    R = np.stack([x, y, z], axis=0)
    T = -R @ pos
    cam = Camera(0, torch.zeros(3, H, W, device="cuda"), np.zeros((H, W)), torch.eye(4), proj,
                 ds.fx, ds.fy, ds.cx, ds.cy, ds.fovx, ds.fovy, H, W, time=0.0,
                 motion_mask=torch.zeros(H, W, device="cuda", dtype=torch.bool), device="cuda")
    cam.update_RT(torch.as_tensor(R, dtype=torch.float32, device="cuda"),
                  torch.as_tensor(T, dtype=torch.float32, device="cuda"))
    with torch.no_grad():
        pkg = render(cam, g, cfg["pipeline_params"], bg, dynamic=False, dx=dxyz(148), ds=0, dr=0)
    img = (pkg["render"].clamp(0, 1).permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)
    Image.fromarray(img).save(os.path.join(OUT, f"{name}.png"))
    print(name, "saved, mean", round(float(img.mean()), 1))


render_orbit(0, 10, 2.5, np.array([0.0, -1.0, 0.0]), "a_down_up")
render_orbit(0, 10, 2.5, np.array([0.0, 1.0, 0.0]), "b_up_up")
render_orbit(30, 20, 3.0, np.array([0.0, -1.0, 0.0]), "c_yaw30")
render_orbit(0, 0, 2.5, np.array([0.0, -1.0, 0.0]), "d_level")
