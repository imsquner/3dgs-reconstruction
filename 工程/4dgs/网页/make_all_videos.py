#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为三条序列各生成一份网页用输入视频（298 帧，30 fps）。"""
import os
import shutil
import subprocess

import numpy as np

FFMPEG = "/mnt/d/桌面/image/4dgs/gpt-6/工程/工具/ffmpeg/ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe"
STATIC_DIR = "/home/ad/flow4dgs-local/web/static"
BASE = "/home/ad/flow4dgs-local/data/tum"

SEQS = [
    ("walking_xyz", "full_xyz"),
    ("walking_static", "full_static"),
    ("sitting_static", "full_sitting"),
]


def load_list(root, p):
    rows = []
    for ln in open(os.path.join(root, p), encoding="utf-8"):
        if ln.startswith("#") or not ln.strip():
            continue
        rows.append(ln.split())
    return rows


def build(seq, model_name):
    root = os.path.join(BASE, f"rgbd_dataset_freiburg3_{seq}")
    if not os.path.isdir(root):
        print("跳过（数据不存在）:", seq)
        return
    rgb = load_list(root, "rgb.txt")
    dep = load_list(root, "depth.txt")
    gtt = load_list(root, "groundtruth.txt")
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

    tmp = f"/mnt/d/Temp/frames_{seq}"
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp)
    for n, i in enumerate(sel):
        shutil.copy(os.path.join(root, rgb[i][1]), os.path.join(tmp, f"{n:05d}.png"))

    out_win = rf"D:\Temp\input_{model_name}.mp4"
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-framerate", "30",
           "-i", rf"{tmp.replace('/mnt/d', 'D:')}\%05d.png".replace("/", "\\"),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
           "-movflags", "+faststart", out_win]
    rc = subprocess.call(cmd)
    if rc == 0:
        dst = os.path.join(STATIC_DIR, f"input_{model_name}.mp4")
        shutil.copy(f"/mnt/d/Temp/input_{model_name}.mp4", dst)
        print(f"{seq}: {len(sel)} 帧 -> {dst} ({os.path.getsize(dst)//1024} KB)")
    else:
        print(f"{seq}: ffmpeg 失败 rc={rc}")


for seq, model in SEQS:
    build(seq, model)
