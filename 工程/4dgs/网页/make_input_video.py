#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 TUM 序列生成网页用的输入视频（298 帧，30 fps）。

帧序与训练完全一致：复刻 TUMParser 的关联与抽帧，取前 298 帧。
"""
import os
import shutil
import subprocess
import sys

import numpy as np

TUM = os.environ.get("TUM_DIR", "/home/ad/flow4dgs-local/data/tum/rgbd_dataset_freiburg3_walking_xyz")
OUT_DIR = "/mnt/d/Temp/input_frames"
FFMPEG = "/mnt/d/桌面/image/4dgs/gpt-6/工程/工具/ffmpeg/ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe"
OUT_MP4_WIN = r"D:\Temp\input.mp4"
OUT_MP4_WSL = "/home/ad/flow4dgs-local/web/static/input.mp4"


def load_list(p):
    rows = []
    for ln in open(os.path.join(TUM, p), encoding="utf-8"):
        if ln.startswith("#") or not ln.strip():
            continue
        rows.append(ln.split())
    return rows


rgb = load_list("rgb.txt")
dep = load_list("depth.txt")
gtt = load_list("groundtruth.txt")
ts_rgb = np.array([float(r[0]) for r in rgb])
ts_dep = np.array([float(r[0]) for r in dep])
ts_gt = np.array([float(r[0]) for r in gtt])

assoc = []
for i, t in enumerate(ts_rgb):
    j = int(np.argmin(np.abs(ts_dep - t)))
    k = int(np.argmin(np.abs(ts_gt - t)))
    if abs(ts_dep[j] - t) < 0.08 and abs(ts_gt[k] - t) < 0.08:
        assoc.append(i)
keep = [0]
for i in range(1, len(assoc)):
    if ts_rgb[assoc[i]] - ts_rgb[assoc[keep[-1]]] > 1.0 / 32:
        keep.append(i)
sel = [assoc[i] for i in keep][:298]
print("frames selected:", len(sel))

if os.path.isdir(OUT_DIR):
    shutil.rmtree(OUT_DIR)
os.makedirs(OUT_DIR, exist_ok=True)
for n, i in enumerate(sel):
    shutil.copy(os.path.join(TUM, rgb[i][1]), os.path.join(OUT_DIR, f"{n:05d}.png"))
print("copied to", OUT_DIR)

cmd = [FFMPEG, "-y", "-loglevel", "error", "-framerate", "30",
       "-i", r"D:\Temp\input_frames\%05d.png",
       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
       "-movflags", "+faststart", OUT_MP4_WIN]
print(" ".join(cmd))
rc = subprocess.call(cmd)
print("ffmpeg rc =", rc)
if rc == 0:
    os.makedirs(os.path.dirname(OUT_MP4_WSL), exist_ok=True)
    shutil.copy("/mnt/d/Temp/input.mp4", OUT_MP4_WSL)
    print("saved", OUT_MP4_WSL, os.path.getsize(OUT_MP4_WSL) // 1024, "KB")
else:
    sys.exit(1)
