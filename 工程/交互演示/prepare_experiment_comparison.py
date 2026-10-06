"""Package existing experiments; no training, pruning, appearance edits or GT cameras."""
import json,hashlib,numpy as np
from pathlib import Path
from ply_adapter import adapt_xyzw_to_wxyz
B=Path(__file__).resolve().parent;R=B.parent/'运行';A=B/'assets';items=[('01','original-b10'),('02','original-b20'),('03','prior-only-b20'),('04','combined-b20')]
runs={n:R/f'local-tum-quality-rgbdpnp240-{suffix}-v18' for n,suffix in items}
base=json.loads((runs['02']/'manifest.json').read_text());poses=json.loads((runs['02']/'final-poses.json').read_text());indices=[x['source_frame'] for x in base['frames']]
for number,run in runs.items():
 state=json.loads((run/'state.json').read_text());assert state['status']=='complete'
 manifest=json.loads((run/'manifest.json').read_text());assert manifest['frames']==base['frames'];source=run/'scene.ply'
 before=hashlib.sha256(source.read_bytes()).hexdigest();assert before==state['artifacts']['scene.ply']
 key=f'office-exp-{number}';target=A/f'{key}-web.ply';assert not target.exists()
 adapter=adapt_xyzw_to_wxyz(source,target);assert hashlib.sha256(source.read_bytes()).hexdigest()==before
 raw=source.read_bytes();end=raw.index(b'end_header\n')+11;lines=raw[:end].decode().splitlines();names=[x.split()[-1] for x in lines if x.startswith('property ')];data=np.frombuffer(raw[end:],dtype='<f4').reshape(adapter['vertices'],len(names));xyz=data[:,[names.index(a) for a in ['x','y','z']]]
 metrics=json.loads((run/'评价/metrics.json').read_text())['means'];audit=json.loads((run/'online-audit.json').read_text());summary=json.loads((run/'summary.json').read_text());own=json.loads((run/'final-poses.json').read_text())
 scene={'key':key,'label':f'{number} · TUM office240','kind':'真实RGB-D · 短段开发实验','ply':f'assets/{key}-web.ply','gaussians':adapter['vertices'],'input_fps':5,'indices':indices,'poses':poses,'estimated_poses':own,'intrinsic':[640,480,535.4,539.2,320.1,247.6],'duration':indices[-1]/5,'measured_tracking_fps':240/summary['wall_seconds'],'ate_m':audit['trajectory']['ate_rigid_aligned_rmse_m'],'bounds':'固定最终高斯地图；时间轴仅回放观察相机，不是在线地图快照。全部240帧观测一致，共用02估计轨迹观察；各版本指标来自各自实验。完整长序列和迁移未验证。','source_ply_sha256':before,'browser_adapter':adapter,'map_bounds':[xyz.min(0).tolist(),xyz.max(0).tolist()],'experiment':{'number':number,'run':run.name,'frames':240,'steps_per_frame':manifest['quality_args']['steps_per_frame'],'wall_seconds':summary['wall_seconds'],'metrics':metrics,'camera_source_run':runs['02'].name,'scope':'本组基于GS-ICP-SLAM的工程优化；短段开发验证，不声称原创算法或完整长序列提升。'}}
 (A/f'{key}.json').write_text(json.dumps(scene,ensure_ascii=False),encoding='utf8');print('PACKAGED',number,adapter['vertices'],flush=True)
