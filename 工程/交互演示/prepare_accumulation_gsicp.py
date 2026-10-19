"""Cumulative RGB-D observation replay for the online GS-ICP full office run.

Same contract as assets/office-accumulation.json: each chunk only contains points that were
actually observed up to that frame, transformed by the online estimated poses recorded at the
time. No reference pose, no final Gaussian map and no future frame contributes to an earlier state.
"""
import hashlib
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image

B = Path(__file__).resolve().parent
G = B.parents[1]
project = G.parent
D = project / 'MonoGS/datasets/tum/rgbd_dataset_freiburg3_long_office_household'
R = G / '工程/运行/gsicp-office-full-10fps-finite'
A = B / 'assets'
OUT = A / 'natural/tum-comparison'
OUT.mkdir(parents=True, exist_ok=True)
thumbs = OUT / 'GSICP10-input'
thumbs.mkdir(exist_ok=True)

SCENE = OUT / 'GSICP10.json'
ARM = 'GSICP10'
INPUT_FPS = 10.0
FRAME_STRIDE = 5
PIXEL_STRIDE = 6
VOXEL = .015
fx, fy, cx, cy = 535.4, 539.2, 320.1, 247.6

rows = [json.loads(x) for x in (R / 'frames.jsonl').read_text().splitlines()]
depth_rows = [x.split() for x in (D / 'depth.txt').read_text().splitlines() if x and not x.startswith('#')]
depth_t = np.array([float(x[0]) for x in depth_rows])

seen = set()
points, colors, chunks = [], [], []
total = 0
skipped = []
started = time.time()
yy, xx = np.mgrid[0:480:PIXEL_STRIDE, 0:640:PIXEL_STRIDE]

selected = list(range(0, len(rows), FRAME_STRIDE))
if selected[-1] != len(rows) - 1:
    selected.append(len(rows) - 1)

for count, i in enumerate(selected):
    r = rows[i]
    rgb = D / 'rgb' / Path(r['image_path']).name
    t = float(rgb.stem)
    j = int(np.argmin(np.abs(depth_t - t)))
    dt = float(abs(depth_t[j] - t))
    chunk = dict(source_frame=i, time_seconds=i / INPUT_FPS, point_count=total, added=0,
                 rgb_path=f'rgb/{rgb.name}', rgb_sha256=hashlib.sha256(rgb.read_bytes()).hexdigest())
    if dt > .08 or not rgb.exists():
        skipped.append(dict(source_frame=i, depth_time_difference_seconds=dt, reason='no depth within 0.08s'))
        chunks.append(chunk)
        continue
    depth = D / depth_rows[j][1]
    color = np.asarray(Image.open(rgb).convert('RGB'))
    z = np.asarray(Image.open(depth), dtype=np.float32)[::PIXEL_STRIDE, ::PIXEL_STRIDE] / 5000
    valid = (z > .1) & (z < 3)
    xyz = np.stack([(xx - cx) * z / fx, (yy - cy) * z / fy, z], axis=-1)[valid]
    pose = np.array(r['estimated_c2w'])
    world = (xyz @ pose[:3, :3].T + pose[:3, 3]).astype('<f4')
    col = color[::PIXEL_STRIDE, ::PIXEL_STRIDE][valid]
    keys = np.floor(world / VOXEL).astype(np.int32)
    keep = []
    for k, key in enumerate(map(tuple, keys)):
        if key not in seen:
            seen.add(key)
            keep.append(k)
    points.append(world[keep])
    colors.append(col[keep])
    total += len(keep)
    preview = thumbs / f'{i:05d}.jpg'
    Image.fromarray(color).resize((320, 240)).save(preview, quality=88)
    chunk.update(added=len(keep), point_count=total,
                 depth_path=depth_rows[j][1], depth_sha256=hashlib.sha256(depth.read_bytes()).hexdigest(),
                 depth_time_difference_seconds=dt,
                 input_image=f'assets/natural/tum-comparison/GSICP10-input/{preview.name}')
    chunks.append(chunk)
    if count % 25 == 0:
        print('ACCUMULATION_HEARTBEAT', count, len(selected), total, 'elapsed', round(time.time() - started, 1), flush=True)

p = np.concatenate(points)
c = np.concatenate(colors)
assert len(p) == total and np.isfinite(p).all()
(OUT / 'GSICP10-observations.xyz').write_bytes(p.astype('<f4').tobytes())
(OUT / 'GSICP10-observations.rgb').write_bytes(c.tobytes())

m = dict(
    run=R.name, input_fps=INPUT_FPS, source_frames=len(rows), sampled_frames=len(selected),
    pixel_stride=PIXEL_STRIDE, frame_stride=FRAME_STRIDE, voxel_size_m=VOXEL, depth_scale=5000,
    depth_range_m=[.1, 3], intrinsic=[640, 480, fx, fy, cx, cy], points=total, chunks=chunks,
    caption='每5帧采样（在线估计位姿）',
    skipped_frames=skipped,
    scope=('Sequential RGB-D observation accumulation using the ONLINE estimated GICP poses recorded '
           'during that run. First observation per 1.5cm voxel is retained, so no future point appears '
           'in an earlier draw range. This is point-cloud accumulation, NOT saved historical 3DGS '
           'optimizer states, and NOT a new throughput measurement.'),
    pose_source_sha256=hashlib.sha256((R / 'frames.jsonl').read_bytes()).hexdigest(),
    position_sha256=hashlib.sha256((OUT / 'GSICP10-observations.xyz').read_bytes()).hexdigest(),
    color_sha256=hashlib.sha256((OUT / 'GSICP10-observations.rgb').read_bytes()).hexdigest(),
)
(OUT / 'GSICP10-accumulation.json').write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')

# Attach the accumulation contract to the already packaged scene JSON (paths only).
scene = json.loads(SCENE.read_text(encoding='utf-8'))
assert scene['key'] == f'natural/tum-comparison/{ARM}'
scene.update(accumulation_path=f'assets/natural/tum-comparison/{ARM}-accumulation.json',
             points_path=f'assets/natural/tum-comparison/{ARM}-observations.xyz',
             colors_path=f'assets/natural/tum-comparison/{ARM}-observations.rgb')
SCENE.write_text(json.dumps(scene, ensure_ascii=False), encoding='utf-8')
print('ACCUMULATION_READY', total, 'skipped', len(skipped), flush=True)
