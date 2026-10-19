"""Build web observation-accumulation assets for a medical TSDF scene.

Reads the per-frame RGB-D + the estimated camera trajectory already stored in the
scene JSON, back-projects every sampled depth pixel to world space, keeps the first
observation per voxel, and writes the three files the viewer expects:

    observations.xyz    float32 little-endian xyz (world metres, first-seen order)
    observations.rgb    uint8 sRGB triplets, same order
    accumulation.json   per-frame cumulative point_count + preview image
    input/*.jpg         downscaled RGB frames for the preview pane

The scene JSON is patched in place with points_path / colors_path /
accumulation_path / point_size / accumulation_description.

Pose convention: scene.json "poses" are 4x4 camera-to-world (row-major); the viewer
takes translation from column 3, forward from column 2, up from -column 1.
"""

import argparse
import json
import math
import zipfile
from pathlib import Path

import matplotlib
import numpy as np
from PIL import Image

TURBO = matplotlib.colormaps["turbo"]

OFFSET = 1 << 20
BITS = 21
MASK = (1 << BITS) - 1


class DirSource:
    def __init__(self, rgb_dir: Path, depth_dir: Path):
        self.rgb_dir = Path(rgb_dir)
        self.depth_dir = Path(depth_dir)

    def rgb(self, i):
        return self.rgb_dir / f"{i:04d}.png"

    def depth(self, i):
        for ext in (".tiff", ".tif", ".npy", ".png"):
            p = self.depth_dir / f"{i:04d}{ext}"
            if p.exists():
                return p
        raise FileNotFoundError(f"depth {i:04d} not found under {self.depth_dir}")


class ZipSource:
    def __init__(self, zip_path: Path, prefix: str):
        self.zip = zipfile.ZipFile(zip_path)
        self.prefix = prefix.rstrip("/")
        self.names = set(self.zip.namelist())

    def _name(self, kind, i):
        return f"{self.prefix}/{kind}/{i:04d}.{'png' if kind == 'rgb' else 'npy'}"

    def rgb(self, i):
        return self._read(self._name("rgb", i))

    def depth(self, i):
        return self._read(self._name("depth_m", i))

    def _read(self, name):
        with self.zip.open(name) as f:
            return f.read()


def load_depth(payload):
    """Return (metres, invalid_mask)."""
    if isinstance(payload, bytes):
        import io
        if payload[:6] == b"\x93NUMPY":
            arr = np.load(io.BytesIO(payload)).astype(np.float32)
            return np.nan_to_num(arr, nan=0.0), ~np.isfinite(arr) | (arr <= 0)
        raw = np.array(Image.open(io.BytesIO(payload))).astype(np.float32)
    else:
        path = Path(payload)
        if path.suffix.lower() == ".npy":
            arr = np.load(path).astype(np.float32)
            return np.nan_to_num(arr, nan=0.0), ~np.isfinite(arr) | (arr <= 0)
        raw = np.array(Image.open(path)).astype(np.float32)
    invalid = (raw <= 0) | (raw >= 65535)
    return raw / 655350.0, invalid


def load_rgb(payload):
    import io
    if isinstance(payload, bytes):
        return Image.open(io.BytesIO(payload)).convert("RGB")
    return Image.open(payload).convert("RGB")


def transform(pts, pose):
    r = np.asarray(pose, dtype=np.float64)[:3, :3]
    t = np.asarray(pose, dtype=np.float64)[:3, 3]
    return pts @ r.T + t


def load_ply_vertices(path: Path):
    """Minimal ASCII PLY vertex reader (x y z ...)."""
    with open(path, "rb") as f:
        if f.readline().strip() != b"ply":
            raise ValueError(f"{path} is not a PLY file")
        count = None
        f.readline()
        while True:
            line = f.readline()
            if not line:
                raise ValueError("unexpected EOF in PLY header")
            parts = line.split()
            if parts[:1] == [b"element"] and parts[1:2] == [b"vertex"]:
                count = int(parts[2])
            if line.strip() == b"end_header":
                break
        if count is None:
            raise ValueError("PLY has no vertex element")
        verts = np.empty((count, 3), dtype=np.float64)
        for i in range(count):
            parts = f.readline().split()
            verts[i] = (float(parts[0]), float(parts[1]), float(parts[2]))
    return verts


def depth_colour(depth, invalid, vmax_m=0.1):
    t = np.clip(depth / vmax_m, 0, 1)
    rgb = (TURBO(t)[..., :3] * 255).astype(np.uint8)
    rgb[invalid] = (35, 35, 35)
    return rgb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene-json", required=True)
    ap.add_argument("--rgb-dir")
    ap.add_argument("--depth-dir")
    ap.add_argument("--zip")
    ap.add_argument("--zip-prefix", default="cecum276_675")
    ap.add_argument("--pixel-stride", type=int, default=4)
    ap.add_argument("--voxel-mm", type=float, default=0.5)
    ap.add_argument("--min-depth-mm", type=float, default=5.0)
    ap.add_argument("--max-depth-mm", type=float, default=110.0)
    ap.add_argument("--input-width", type=int, default=480)
    ap.add_argument("--point-size", type=float, default=0.0005)
    ap.add_argument("--limit", type=int, default=0, help="debug: only first N frames")
    ap.add_argument("--no-clip", action="store_true", help="keep points outside map_bounds")
    ap.add_argument("--clip-pad-mm", type=float, default=5.0)
    ap.add_argument("--mesh-filter-mm", type=float, default=0.0,
                    help="keep only points within this distance of the final mesh")
    ap.add_argument("--description", default="")
    args = ap.parse_args()

    scene_path = Path(args.scene_json)
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    out = scene_path.parent
    site_root = out
    while site_root.name != "assets":
        site_root = site_root.parent
    site_root = site_root.parent

    w, h, fx, fy, cx, cy = scene["intrinsic"]
    poses = scene["poses"]
    indices = scene["indices"]
    n = len(indices) if not args.limit else min(args.limit, len(indices))

    clip_lo = clip_hi = None
    if not args.no_clip and scene.get("map_bounds"):
        pad = args.clip_pad_mm / 1000.0
        clip_lo = np.asarray(scene["map_bounds"][0], dtype=np.float64) - pad
        clip_hi = np.asarray(scene["map_bounds"][1], dtype=np.float64) + pad

    mesh_tree = None
    if args.mesh_filter_mm > 0:
        from scipy.spatial import cKDTree
        mesh_tree = cKDTree(load_ply_vertices(site_root / scene["ply"]))
        print(f"mesh vertices={mesh_tree.n}  filter={args.mesh_filter_mm} mm", flush=True)

    if args.zip:
        src = ZipSource(Path(args.zip), args.zip_prefix)
    else:
        src = DirSource(Path(args.rgb_dir), Path(args.depth_dir))

    voxel = args.voxel_mm / 1000.0
    zmin, zmax = args.min_depth_mm / 1000.0, args.max_depth_mm / 1000.0
    step = args.pixel_stride
    us = np.arange(step // 2, w, step, dtype=np.int32)
    vs = np.arange(step // 2, h, step, dtype=np.int32)
    uu, vv = np.meshgrid(us, vs)
    uu = uu.reshape(-1)
    vv = vv.reshape(-1)

    seen = set()
    xyz_chunks, rgb_chunks, records = [], [], []
    frame_times = []
    total = 0

    input_dir = out / "input"
    input_dir.mkdir(exist_ok=True)

    for k in range(n):
        fidx = int(indices[k])
        depth, invalid = load_depth(src.depth(fidx))
        if depth.shape != (h, w):
            raise SystemExit(f"frame {fidx}: depth {depth.shape} != ({h}, {w})")
        img = load_rgb(src.rgb(fidx))
        if img.size != (w, h):
            img = img.resize((w, h), Image.BILINEAR)
        rgb = np.asarray(img, dtype=np.uint8)

        fname = f"input/{fidx:04d}.jpg"
        thumb = img.resize((args.input_width,
                            max(1, round(h * args.input_width / w))), Image.LANCZOS)
        thumb.save(out / fname, quality=82, optimize=True)

        dname = f"input/depth_{fidx:04d}.jpg"
        dimg = Image.fromarray(depth_colour(depth, invalid))
        dimg = dimg.resize((args.input_width,
                            max(1, round(h * args.input_width / w))), Image.LANCZOS)
        dimg.save(out / dname, quality=82, optimize=True)
        img_rel = (out / fname).relative_to(site_root).as_posix()
        dep_rel = (out / dname).relative_to(site_root).as_posix()

        z = depth[vv, uu]
        valid = (~invalid[vv, uu]) & (z > zmin) & (z < zmax)
        if valid.sum() == 0:
            records.append({"source_frame": fidx, "time_seconds": k / 5.0,
                            "point_count": total, "added": 0,
                            "input_image": img_rel, "depth_image": dep_rel})
            frame_times.append(k / 5.0)
            continue

        uu_v = uu[valid]
        vv_v = vv[valid]
        zz = z[valid].astype(np.float64)
        x = (uu_v - cx) / fx * zz
        y = (vv_v - cy) / fy * zz
        pts = transform(np.stack([x, y, zz], axis=1), poses[k])

        if clip_lo is not None:
            inside = ((pts >= clip_lo) & (pts <= clip_hi)).all(axis=1)
            pts = pts[inside]
            uu_v = uu_v[inside]
            vv_v = vv_v[inside]

        if mesh_tree is not None and len(pts):
            dist, _ = mesh_tree.query(pts, workers=-1)
            near = dist <= args.mesh_filter_mm / 1000.0
            pts = pts[near]
            uu_v = uu_v[near]
            vv_v = vv_v[near]

        if len(pts) == 0:
            records.append({"source_frame": fidx, "time_seconds": k / 5.0,
                            "point_count": total, "added": 0,
                            "input_image": img_rel, "depth_image": dep_rel})
            frame_times.append(k / 5.0)
            continue

        q = np.floor(pts / voxel).astype(np.int64) + OFFSET
        if (q < 0).any() or (q > MASK).any():
            raise SystemExit(f"frame {fidx}: voxel grid overflow")
        keys = (q[:, 0] << (2 * BITS)) | (q[:, 1] << BITS) | q[:, 2]

        uniq, first = np.unique(keys, return_index=True)
        new_mask = np.asarray([int(v) not in seen for v in uniq.tolist()], dtype=bool)
        added = 0
        if new_mask.any():
            idx = first[new_mask]
            seen.update(int(v) for v in uniq[new_mask].tolist())
            xyz_chunks.append(pts[idx].astype(np.float32))
            rgb_chunks.append(rgb[vv_v[idx], uu_v[idx]].astype(np.uint8))
            added = int(len(idx))
            total += added

        records.append({
            "source_frame": fidx,
            "time_seconds": k / 5.0,
            "point_count": total,
            "added": added,
            "input_image": img_rel,
            "depth_image": dep_rel,
        })
        frame_times.append(k / 5.0)
        if k % 25 == 0 or k == n - 1:
            print(f"frame {k + 1}/{n}  points={total}", flush=True)

    xyz = np.concatenate(xyz_chunks, axis=0) if xyz_chunks else np.zeros((0, 3), np.float32)
    rgb = np.concatenate(rgb_chunks, axis=0) if rgb_chunks else np.zeros((0, 3), np.uint8)
    (out / "observations.xyz").write_bytes(np.ascontiguousarray(xyz, dtype="<f4").tobytes())
    (out / "observations.rgb").write_bytes(np.ascontiguousarray(rgb, dtype="u1").tobytes())

    acc = {
        "points": int(len(xyz)),
        "source_frames": n,
        "sampled_frames": len(records),
        "frame_stride": 1,
        "pixel_stride": step,
        "voxel_m": voxel,
        "depth_range_m": [zmin, zmax],
        "chunks": records,
        "frame_times": frame_times,
        "caption": "逐帧RGB-D观测（估计位姿）",
        "scope": (args.description or
                  "按记录的估计位姿把每帧深度反投影累积；每 {} 像素采样，{} mm 体素保留首次观测；"
                  "不是历史高斯状态，也不是真值位姿。").format(step, args.voxel_mm),
    }
    (out / "accumulation.json").write_text(
        json.dumps(acc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    rel = lambda p: p.relative_to(site_root).as_posix()
    scene.update({
        "points_path": rel(out / "observations.xyz"),
        "colors_path": rel(out / "observations.rgb"),
        "accumulation_path": rel(out / "accumulation.json"),
        "point_size": args.point_size,
        "accumulation_description": acc["scope"],
    })
    scene_path.write_text(json.dumps(scene, ensure_ascii=False, separators=(",", ":")),
                          encoding="utf-8")
    print(json.dumps({"points": len(xyz), "frames": n,
                      "xyz_mb": round(len(xyz) * 12 / 1e6, 2),
                      "rgb_mb": round(len(rgb) * 3 / 1e6, 2)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
