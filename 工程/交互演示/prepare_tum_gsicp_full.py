"""Expose the best online TUM office run (GS-ICP, full 2515 frames, 10 FPS) to the website.

Rotation-order adapter + timestamp/pose packaging only: no retraining, no geometry edits.
Source run: 工程/运行/gsicp-office-full-10fps-finite (484990 gaussians, ATE 3.11 cm, 10 FPS).
"""
import hashlib
import json
from pathlib import Path

import numpy as np

from ply_adapter import adapt_xyzw_to_wxyz

B = Path(__file__).resolve().parent
R = B.parent / '运行'
A = B / 'assets/natural/tum-comparison'
A.mkdir(parents=True, exist_ok=True)

RUN = 'gsicp-office-full-10fps-finite'
ARM = 'GSICP10'


def read(p):
    return json.loads(p.read_text(encoding='utf-8'))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


run = R / RUN
assert run.is_dir(), run
source = run / 'scene.ply'
audit = read(run / 'experiment-audit.json')
summary = read(run / 'summary.json')
assert audit['ply_finite'] is True, 'PLY must be finite'
assert source.exists(), source
before = sha(source)

# Preserve every already-published derived asset.
protected = {p: sha(p) for p in A.glob('*') if p.is_file()}
protected.update({p: sha(p) for p in (B / 'assets').glob('*') if p.is_file()})

target = A / f'{ARM}-web.ply'
assert not target.exists(), 'Preserve existing derived assets'
adapter = adapt_xyzw_to_wxyz(source, target)
assert sha(source) == before, 'source PLY must stay untouched'

raw = source.read_bytes()
end = raw.index(b'end_header\n') + 11
fields = [x.split()[-1] for x in raw[:end].decode().splitlines() if x.startswith('property ')]
data = np.frombuffer(raw[end:], dtype='<f4').reshape(adapter['vertices'], len(fields))
xyz = data[:, [fields.index(x) for x in ('x', 'y', 'z')]]

poses = read(run / 'final-poses.json')
clock = read(run / 'input-clock.json')
indices = clock['source_indices']
input_fps = float(clock['input_fps'])
assert len(poses) == len(indices) == audit['frames'], (len(poses), len(indices), audit['frames'])
assert audit['ply_count'] == adapter['vertices'], (audit['ply_count'], adapter['vertices'])

scene = dict(
    key=f'natural/tum-comparison/{ARM}',
    label='TUM office · 在线GS-ICP 完整2515帧 · 10FPS',
    kind='真实RGB-D · 在线跟踪（无回环／无全局BA）',
    ply=f'assets/natural/tum-comparison/{ARM}-web.ply',
    gaussians=adapter['vertices'],
    input_fps=input_fps,
    indices=indices,
    poses=poses,
    intrinsic=[640, 480, 535.4, 539.2, 320.1, 247.6],
    duration=indices[-1] / input_fps,
    measured_tracking_fps=audit['post_first_tracking_fps'],
    ate_m=audit['all_frame_ate_rmse_m'],
    ate_label='全序列 SE(3) ATE（独立审计，仅首帧用参考位姿初始化）',
    bounds=(
        '在线 GS-ICP 完整2515帧、10FPS送帧时钟：位姿由GICP里程计在线估计，'
        '无回环检测、无全局BA。时间轴是送帧时钟回放，不是历史高斯快照，也不是采集原始时长。'
        '最终地图视觉质量未验收，画面存在模糊与空洞；浏览帧率不是重建吞吐。'
    ),
    source_ply_sha256=before,
    browser_adapter=adapter,
    accumulation_path=f'assets/natural/tum-comparison/{ARM}-accumulation.json',
    points_path=f'assets/natural/tum-comparison/{ARM}-observations.xyz',
    colors_path=f'assets/natural/tum-comparison/{ARM}-observations.rgb',
    map_bounds=np.quantile(xyz, [.005, .995], axis=0).tolist(),
    experiment=dict(
        run=RUN,
        frames=audit['frames'],
        input_fps=input_fps,
        seed=read(run / 'manifest.json')['seed'],
        pose_source='estimated GICP odometry; reference pose only for first-frame init and evaluation',
        loop_closure=False,
        global_ba=False,
        wall_seconds=summary['wall_seconds'],
        official_tracking_fps=audit['official_tracking_fps'],
        latency_p50_p95_ms=audit['processing_ms_p50_p95'],
        latency_pass_200ms=audit['latency_pass_200ms'],
        final_backlog_seconds=audit['final_backlog_seconds'],
        quality_status='pending_full_evaluation',
        scope='Online tracking + incremental mapping, single seed; separate from the offline OOOSplat run',
    ),
)
(A / f'{ARM}.json').write_text(json.dumps(scene, ensure_ascii=False), encoding='utf-8')

for p, h in protected.items():
    assert sha(p) == h, f'existing asset changed: {p}'

(A / f'{ARM}-packaging.json').write_text(json.dumps(dict(
    run=RUN,
    source_ply=str(source.relative_to(B.parent.parent)),
    source_sha256=before,
    derived_ply=f'assets/natural/tum-comparison/{ARM}-web.ply',
    derived_sha256=sha(target),
    vertices=adapter['vertices'],
    frames=len(poses),
    input_fps=input_fps,
    ate_m=audit['all_frame_ate_rmse_m'],
    adapter=adapter,
    protected_assets_unchanged=True,
    scope='rotation-order adapter + packaging only; no retraining, no geometry edit',
), ensure_ascii=False, indent=2), encoding='utf-8')

print(json.dumps(dict(arm=ARM, vertices=adapter['vertices'], target_bytes=target.stat().st_size,
                      derived_sha256=sha(target), frames=len(poses)), ensure_ascii=False), flush=True)
