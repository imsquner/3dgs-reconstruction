#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Flow4DGS 4D 高斯实时渲染服务。

- WebSocket 接收 {t, yaw, pitch, dist, mode}，返回 JPEG 帧
- HTTP 提供静态页面
- 模型常驻 GPU，单帧渲染约 10-25 ms（640x480 / 960x720）
"""
import asyncio
import io
import json
import math
import os
import sys
import threading
import time
from urllib.parse import urlparse, parse_qs
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

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

import cv2
import websockets

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.environ.get("MODEL_DIR", "/home/ad/flow4dgs-local/models/full298")
DATA_DIR = os.environ.get("DATA_DIR", "/home/ad/flow4dgs-local/data/tum/rgbd_dataset_freiburg3_walking_xyz")
_default_pose = os.path.join(MODEL_DIR, "pose.txt")
POSE_TXT = os.environ.get(
    "POSE_TXT",
    _default_pose if os.path.isfile(_default_pose)
    else "/mnt/d/桌面/image/4dgs/Flow4DGS_model_all_frames/pose.txt",
)
HTTP_PORT = int(os.environ.get("HTTP_PORT", 8770))
WS_PORT = int(os.environ.get("WS_PORT", 8771))


# ---------------------------------------------------------------- 模型
class Scene:
    def __init__(self, model_dir=None, pose_txt=None):
        model_dir = model_dir or MODEL_DIR
        pose_txt = pose_txt or POSE_TXT
        cfg_raw = yaml.safe_load(open(os.path.join(model_dir, "config.yml"), encoding="utf-8"))
        cfg_raw.pop("inherit_from", None)
        cfg = munchify(cfg_raw)
        original_data = cfg["Dataset"]["dataset_path"]
        if not os.path.isdir(original_data):
            local_data = os.path.join('/home/ad/flow4dgs-local/data/tum', os.path.basename(original_data.rstrip('/')))
            if not os.path.isdir(local_data):
                raise FileNotFoundError(f'Missing matching dataset: {original_data}; expected {local_data}')
            cfg["Dataset"]["dataset_path"] = local_data
        self.cfg = cfg

        self.ds = load_dataset(None, None, cfg)
        self.n_frames = len(self.ds)

        g = GaussianModel(cfg["model_params"]["sh_degree"], config=cfg, args=None,
                          init_deform=cfg["model_params"]["dynamic_model"], nframes=self.n_frames)
        ply = os.path.join(model_dir, "point_cloud.ply")
        if not os.path.isfile(ply):
            ply = os.path.join(model_dir, "point_cloud", "final", "point_cloud.ply")
        off = os.path.join(model_dir, "offsets.pth")
        if not os.path.isfile(off):
            off = os.path.join(model_dir, "offsets", "iteration_81500", "offsets.pth")
        print(f"[scene] ply={ply}", flush=True)
        print(f"[scene] offsets={off}", flush=True)
        g.load_ply(ply)
        g.load_offsets(off)
        self.g = g
        self.kf = list(g.kf_list)

        # 渐进建图：如果 offsets 里存了每个高斯的出生帧，就保留一份基准不透明度
        self.birth = None
        self.opacity_base = None
        try:
            ck = torch.load(off, map_location="cpu")
            if isinstance(ck, dict) and "unique_kfIDs" in ck:
                b = ck["unique_kfIDs"].reshape(-1).to(torch.int64)
                if b.numel() == g.get_xyz.shape[0]:
                    self.birth = b
                    self.opacity_base = g._opacity.detach().clone()
                    print(f"[scene] birth info ok: min={int(b.min())} max={int(b.max())} "
                          f"unique={int(b.unique().numel())}", flush=True)
                else:
                    print(f"[scene] birth 长度不匹配 {b.numel()} vs {g.get_xyz.shape[0]}", flush=True)
        except Exception as e:
            print("[scene] 无出生信息:", repr(e), flush=True)
        self._grow_applied = None
        # 演示动画用的显式顺序：先按真实出生帧，再按索引；便于"从少到多"铺开
        self.reveal_order = None
        if self.birth is not None:
            n = self.birth.numel()
            key = self.birth.to(torch.float64) * (n + 1) + torch.arange(n, dtype=torch.float64)
            self.reveal_order = torch.argsort(key)
        self.name = os.path.basename(model_dir.rstrip("/"))

        rows = [ln.split() for ln in open(pose_txt, encoding="utf-8").read().strip().splitlines() if ln.strip()]
        rows = [r for r in rows if len(r) == 4]
        self.c2w = np.array(rows, dtype=np.float64).reshape(-1, 4, 4)

        xyz = g.get_xyz.detach().cpu().numpy()
        self.center = np.median(xyz, axis=0)
        self.radius = float(np.percentile(np.linalg.norm(xyz - self.center, axis=1), 90))
        # 默认观察距离：用轨迹相机到场景中心的中位距离，避免一上来就在场景外
        cam_centers = self.c2w[:, :3, 3]
        self.dist0 = float(np.median(np.linalg.norm(cam_centers - self.center, axis=1)))
        self.bg = torch.tensor([1.0, 1.0, 1.0], dtype=torch.float32, device="cuda")
        print(f"[scene] frames={self.n_frames} gaussians={xyz.shape[0]} kf={len(self.kf)} "
              f"center={self.center.round(2)} radius={self.radius:.2f} dist0={self.dist0:.2f}", flush=True)

    # 关键帧插值
    def dxyz(self, idx):
        kf = self.kf
        if idx <= kf[0]:
            return self.g.get_delta_xyz(0)
        if idx >= kf[-1]:
            return self.g.get_delta_xyz(len(kf) - 1)
        lo = max(i for i, k in enumerate(kf) if k <= idx)
        hi = min(i for i, k in enumerate(kf) if k >= idx)
        if lo == hi:
            return self.g.get_delta_xyz(lo)
        w = (idx - kf[lo]) / float(kf[hi] - kf[lo])
        return (1.0 - w) * self.g.get_delta_xyz(lo) + w * self.g.get_delta_xyz(hi)

    def frame_of_time(self, t):
        return int(round(min(max(t, 0.0), 1.0) * (self.n_frames - 1)))

    def make_cam(self, W, H, R, T, idx):
        ds = self.ds
        sx, sy = W / ds.width, H / ds.height
        fx, fy, cx, cy = ds.fx * sx, ds.fy * sy, ds.cx * sx, ds.cy * sy
        fovx = 2 * math.atan(W / (2 * fx))
        fovy = 2 * math.atan(H / (2 * fy))
        proj = getProjectionMatrix2(0.01, 100.0, cx, cy, fx, fy, W, H).transpose(0, 1).cuda()
        dummy_color = torch.zeros(3, H, W, device="cuda")
        dummy_depth = np.zeros((H, W), dtype=np.float64)
        dummy_pose = torch.eye(4)
        dummy_mask = torch.zeros(H, W, device="cuda", dtype=torch.bool)
        cam = Camera(idx, dummy_color, dummy_depth, dummy_pose, proj,
                     fx, fy, cx, cy, fovx, fovy, H, W,
                     time=idx / max(1, self.n_frames - 1), motion_mask=dummy_mask, device="cuda")
        cam.update_RT(torch.as_tensor(R, dtype=torch.float32, device="cuda"),
                      torch.as_tensor(T, dtype=torch.float32, device="cuda"))
        return cam

    def growth_count(self, idx):
        """当前帧之前已"出生"的高斯数。"""
        if self.birth is None:
            return None
        return int((self.birth <= idx).sum())

    def apply_growth(self, idx):
        """把尚未出生的高斯不透明度压到 0（可逆，用基准值恢复）。"""
        if self.birth is None or self.opacity_base is None:
            return
        if self._grow_applied == ("birth", idx):
            return
        born = (self.birth <= idx).cuda()
        with torch.no_grad():
            self.g._opacity.data.copy_(self.opacity_base)
            self.g._opacity.data[~born] = -20.0
        self._grow_applied = ("birth", idx)

    def apply_anim(self, t):
        """演示动画：按真实出生顺序 + 时间比例铺开，视觉上从稀疏到完整。"""
        if self.reveal_order is None or self.opacity_base is None:
            return
        frac = min(1.0, max(0.015, t / 0.45))
        key = ("anim", round(frac, 4))
        if self._grow_applied == key:
            return
        n = self.reveal_order.numel()
        k = max(1, int(round(n * frac)))
        mask = torch.zeros(n, dtype=torch.bool)
        mask[self.reveal_order[:k]] = True
        with torch.no_grad():
            self.g._opacity.data.copy_(self.opacity_base)
            self.g._opacity.data[~mask.cuda()] = -20.0
        self._grow_applied = key

    def restore_full(self):
        if self.opacity_base is not None and self._grow_applied is not None:
            with torch.no_grad():
                self.g._opacity.data.copy_(self.opacity_base)
            self._grow_applied = None

    def render(self, t, yaw, pitch, dolly, W, H, mode="free", quality=85, grow=False, anim=False):
        idx = self.frame_of_time(t)
        dxyz = self.dxyz(idx)
        if anim:
            self.apply_anim(t)
        elif grow:
            self.apply_growth(idx)
        else:
            self.restore_full()
        born = self.growth_count(idx) if (grow or anim) else None
        if anim:
            frac = min(1.0, max(0.015, t / 0.45))
            born = int(round(self.birth.numel() * frac)) if self.birth is not None else None

        # 以该时刻的估计位姿为基准（重建就是围绕这条轨迹建立的）
        w2c = np.linalg.inv(self.c2w[idx])
        R = w2c[:3, :3].astype(np.float64).copy()
        T = w2c[:3, 3].astype(np.float64).copy()

        if mode == "free":
            # 在相机自身坐标系里左右看/上下看（R 右乘 = 绕光心旋转，位置不变）
            cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
            cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
            Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]], dtype=np.float64)
            Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]], dtype=np.float64)
            R = R @ Ry @ Rx
            # 沿光轴推拉：T' = T - [0,0,dolly]
            T = T - np.array([0.0, 0.0, float(dolly)])

        cam = self.make_cam(W, H, R, T, idx)
        t0 = time.perf_counter()
        with torch.no_grad():
            pkg = render(cam, self.g, self.cfg["pipeline_params"], self.bg,
                         dynamic=False, dx=dxyz, ds=0, dr=0)
        torch.cuda.synchronize()
        ms = (time.perf_counter() - t0) * 1000.0
        img = pkg["render"].clamp(0, 1).permute(1, 2, 0).cpu().numpy()
        img8 = (img * 255).astype(np.uint8)[:, :, ::-1]  # BGR for cv2
        ok, buf = cv2.imencode(".jpg", img8, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)])
        return buf.tobytes(), ms, idx, born


SCENE = None
SCENES = {}
CURRENT = None
MODELS_ROOT = os.environ.get("MODELS_ROOT", "/home/ad/flow4dgs-local/models")


def list_models():
    """扫描可用模型目录：需要 ply + offsets + pose.txt + config.yml。"""
    out = []
    if not os.path.isdir(MODELS_ROOT):
        return out
    for name in sorted(os.listdir(MODELS_ROOT)):
        d = os.path.join(MODELS_ROOT, name)
        if not os.path.isdir(d):
            continue
        has_ply = os.path.isfile(os.path.join(d, "point_cloud.ply")) or \
            os.path.isfile(os.path.join(d, "point_cloud", "final", "point_cloud.ply"))
        has_off = os.path.isfile(os.path.join(d, "offsets.pth")) or \
            os.path.isfile(os.path.join(d, "offsets", "iteration_81500", "offsets.pth"))
        has_cfg = os.path.isfile(os.path.join(d, "config.yml"))
        has_pose = os.path.isfile(os.path.join(d, "pose.txt"))
        if has_ply and has_off and has_cfg and has_pose:
            out.append(name)
    return out


def get_scene(name):
    global SCENE, CURRENT
    if name not in SCENES:
        d = os.path.join(MODELS_ROOT, name)
        print(f"[scene] loading {name} ...", flush=True)
        SCENES[name] = Scene(model_dir=d, pose_txt=os.path.join(d, "pose.txt"))
    SCENE = SCENES[name]
    CURRENT = name
    return SCENE


def asset_handler_factory(directory):
    class H(SimpleHTTPRequestHandler):
        def do_GET(self):
            u = urlparse(self.path)
            if u.path == '/input-frame':
                try:
                    q = parse_qs(u.query)
                    name = q.get('model', [''])[0]
                    scene = SCENES.get(name)
                    if scene is None:
                        self.send_error(404, 'Model not loaded'); return
                    idx = int(q.get('i', ['0'])[0])
                    if not 0 <= idx < scene.n_frames:
                        self.send_error(400, 'Invalid frame'); return
                    kind = q.get('kind', ['rgb'])[0]
                    if kind == 'rgb':
                        img = cv2.imread(scene.ds.color_paths[idx])
                    elif kind == 'depth':
                        raw = cv2.imread(scene.ds.depth_paths[idx], cv2.IMREAD_UNCHANGED)
                        depth = raw.astype(np.float32) / float(scene.cfg['Dataset']['Calibration']['depth_scale'])
                        img = cv2.applyColorMap((np.clip(depth / 6.0, 0, 1) * 255).astype(np.uint8), cv2.COLORMAP_TURBO)
                        img[raw == 0] = (65, 65, 65)
                    else:
                        self.send_error(400, 'Invalid kind'); return
                    if img is None:
                        raise ValueError('Missing input image')
                    ok, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 88])
                    if not ok: raise ValueError('Encode failed')
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', str(len(buf)))
                    self.end_headers(); self.wfile.write(buf.tobytes())
                except Exception as exc:
                    self.send_error(500, str(exc))
                return
            super().do_GET()

        def __init__(self, *a, **kw):
            super().__init__(*a, directory=directory, **kw)

        def log_message(self, *a):
            pass

    return H


def start_http():
    srv = ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), asset_handler_factory(os.path.join(HERE, "static")))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"[http] http://127.0.0.1:{HTTP_PORT}", flush=True)


async def ws_handler(ws):
    print("[ws] client connected", flush=True)
    try:
        async for msg in ws:
            req = json.loads(msg)
            if req.get("type") == "hello":
                models = list_models()
                if CURRENT is None and models:
                    get_scene(models[0])
                await ws.send(json.dumps({
                    "type": "scene",
                    "name": CURRENT,
                    "models": models,
                    "frames": SCENE.n_frames,
                    "gaussians": int(SCENE.g.get_xyz.shape[0]),
                    "keyframes": len(SCENE.kf),
                    "center": SCENE.center.tolist(),
                    "radius": SCENE.radius,
                    "dist0": SCENE.dist0,
                }))
                continue
            if req.get("type") == "use":
                name = req.get("name")
                try:
                    sc = get_scene(name)
                except Exception as e:
                    await ws.send(json.dumps({"type": "error", "message": repr(e)}))
                    continue
                await ws.send(json.dumps({
                    "type": "scene",
                    "name": CURRENT,
                    "models": list_models(),
                    "frames": sc.n_frames,
                    "gaussians": int(sc.g.get_xyz.shape[0]),
                    "keyframes": len(sc.kf),
                    "center": sc.center.tolist(),
                    "radius": sc.radius,
                    "dist0": sc.dist0,
                }))
                continue
            t = float(req.get("t", 0.0))
            yaw = float(req.get("yaw", 0.0))
            pitch = float(req.get("pitch", 0.0))
            dolly = float(req.get("dolly", 0.0))
            W = int(req.get("w", 640))
            H = int(req.get("h", 480))
            mode = req.get("mode", "free")
            q = int(req.get("q", 85))
            grow = bool(req.get("grow", False))
            anim = bool(req.get("anim", False))
            jpg, ms, idx, born = SCENE.render(t, yaw, pitch, dolly, W, H, mode, q, grow, anim)
            await ws.send(json.dumps({"type": "frame", "t": t, "idx": idx,
                                      "w": W, "h": H, "ms": round(ms, 2), "mode": mode,
                                      "born": born, "total": int(SCENE.g.get_xyz.shape[0])}))
            await ws.send(jpg)
    except websockets.ConnectionClosed:
        pass
    except Exception as e:
        print("[ws] error", repr(e), flush=True)
    finally:
        print("[ws] client gone", flush=True)


async def main():
    global SCENE, CURRENT
    print("[init] 扫描模型 ...", flush=True)
    models = list_models()
    print("[init] 可用模型:", models, flush=True)
    default = os.path.basename(MODEL_DIR.rstrip("/"))
    if default in models:
        get_scene(default)
    elif models:
        get_scene(models[0])
    else:
        SCENE = None
    start_http()
    async with websockets.serve(ws_handler, "0.0.0.0", WS_PORT, max_size=8 * 1024 * 1024):
        print(f"[ws] ws://127.0.0.1:{WS_PORT}", flush=True)
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
