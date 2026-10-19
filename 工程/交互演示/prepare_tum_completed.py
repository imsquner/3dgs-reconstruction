"""Expose completed TUM maps without training or editing source geometry."""
import hashlib
import json
from pathlib import Path
import numpy as np
from ply_adapter import adapt_xyzw_to_wxyz

B = Path(__file__).resolve().parent
R = B.parent / '运行'
A = B / 'assets/natural/tum-comparison'
A.mkdir(parents=True, exist_ok=True)
names = {
    'B5': 'local-tum-v20-office-B5-2253-observation-barrier-s0-1791656820053729305',
    'B10': 'local-tum-v20-office-B10-2253-observation-barrier-s0-1791658108937718734',
}
def read(p):
    return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
base = read(R / names['B5'] / 'manifest.json')
common_poses = read(R / names['B5'] / 'final-poses.json')
reports = []
protected = {p: sha(p) for p in (B/'assets').glob('replica*') if p.is_file()}
for arm, name in names.items():
    run = R / name
    state, manifest = read(run/'state.json'), read(run/'manifest.json')
    assert state['status'] == 'complete'
    assert manifest['frames'] == base['frames']
    source = run/'scene.ply'
    before = sha(source)
    assert before == state['artifacts']['scene.ply']
    target = A / f'{arm}-web.ply'
    assert not target.exists(), 'Preserve existing derived assets'
    adapter = adapt_xyzw_to_wxyz(source, target)
    assert sha(source) == before
    raw = source.read_bytes()
    end = raw.index(b'end_header\n') + 11
    fields = [x.split()[-1] for x in raw[:end].decode().splitlines() if x.startswith('property ')]
    data = np.frombuffer(raw[end:], dtype='<f4').reshape(adapter['vertices'], len(fields))
    xyz = data[:, [fields.index(x) for x in ('x','y','z')]]
    summary = read(run/'summary.json')
    trajectory = read(run/'评价/trajectory-v20.json')
    frames = manifest['frames']
    seconds = [f['rgb_timestamp']-frames[0]['rgb_timestamp'] for f in frames]
    scene = dict(key=f'natural/tum-comparison/{arm}', label=f'TUM office · {arm}完整2253帧',
        kind='真实RGB-D · 完整序列实验', ply=f'assets/natural/tum-comparison/{arm}-web.ply',
        gaussians=adapter['vertices'], input_fps=manifest['quality_args']['input_fps'],
        indices=[f['source_frame'] for f in frames], poses=common_poses,
        estimated_poses=read(run/'final-poses.json'), intrinsic=[640,480,535.4,539.2,320.1,247.6],
        duration=seconds[-1], frame_times=seconds,
        measured_tracking_fps=2253/summary['wall_seconds'], ate_m=trajectory['ate_common_se3_rmse_m'], ate_label='本组轨迹ATE（共同S5帧）',
        bounds=f'{arm}：2253帧、每帧20步优化、估计G-ICP位姿。5/10 FPS只改变送帧节奏，输入相同且逐帧等待；不是实时采集帧率。两组共用B5估计相机观察，固定最终地图；时间轴不是历史地图。完整图像/深度质量门尚未验收，不标课堂可用。',
        source_ply_sha256=before, browser_adapter=adapter,
        map_bounds=[xyz.min(0).tolist(), xyz.max(0).tolist()],
        experiment=dict(run=name,frames=2253,steps_per_frame=20,wall_seconds=summary['wall_seconds'],
            camera_source_run=names['B5'],pose_source='estimated G-ICP; reference pose only at initialization/evaluation',
            quality_status='pending_full_evaluation',scope='Single-seed complete reconstruction, visual inspection only'))
    (A/f'{arm}.json').write_text(json.dumps(scene,ensure_ascii=False),encoding='utf-8')
    reports.append(dict(arm=arm,source_hash=before,derived_hash=sha(target),vertices=adapter['vertices']))
for p, h in protected.items():
    assert sha(p)==h, 'Replica asset changed'
(A/'packaging-audit.json').write_text(json.dumps(dict(maps=reports,replica_unchanged=True,scope='rotation-order adapter only'),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(reports),flush=True)
