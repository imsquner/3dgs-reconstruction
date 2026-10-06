"""Verify delivered assets against original experiments and raw RGB-D sources."""
from pathlib import Path
import json, hashlib
import numpy as np
B=Path(__file__).resolve().parent
G=B.parents[1]; R=G/'工程/运行'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
report={'scenes':[], 'status':'passed'}
for key in ['replica','office','unity']:
    s=json.loads((B/'assets'/f'{key}.json').read_text(encoding='utf-8'))
    original=R/s['run']/'scene.ply'
    if not original.exists(): original=R/s['run']/'point_cloud/final/point_cloud.ply'
    assert sha(original)==s['source_ply_sha256']
    assert sha(B/s['ply'])==s['ply_sha256']
    assert len(s['indices'])==len(s['poses']) and np.isfinite(s['poses']).all()
    assert all(a<b for a,b in zip(s['indices'],s['indices'][1:]))
    if s['browser_adapter']:
        assert s['browser_adapter']['max_covariance_error']==0
    report['scenes'].append({'scene':key,'original_unchanged':True,'browser_hash_verified':True,'poses':len(s['poses'])})
m=json.loads((B/'assets/office-accumulation.json').read_text())
assert sha(R/m['run']/'frames.jsonl')==m['pose_source_sha256']
for name,field,width in [('office-observations.xyz','position_sha256',12),('office-observations.rgb','color_sha256',3)]:
    p=B/'assets'/name
    assert p.stat().st_size==m['points']*width and sha(p)==m[field]
assert np.isfinite(np.fromfile(B/'assets/office-observations.xyz',dtype='<f4')).all()
total=0; last=-1; max_dt=0
D=G.parent/'MonoGS/datasets/tum/rgbd_dataset_freiburg3_long_office_household'
for chunk in m['chunks']:
    assert chunk['source_frame']>last
    last=chunk['source_frame'];total+=chunk['added'];assert total==chunk['point_count']
    assert (B/chunk['input_image']).exists()
    for kind in ['rgb','depth']: assert sha(D/chunk[kind+'_path'])==chunk[kind+'_sha256']
    max_dt=max(max_dt,chunk['depth_time_difference_seconds'])
assert total==m['points'] and last==m['source_frames']-1 and max_dt<.08
report['accumulation']={'points':total,'sampled_frames':len(m['chunks']),'first_points':m['chunks'][0]['point_count'],'max_rgb_depth_time_difference_s':max_dt,'source_and_output_hashes_verified':True,'prefix_counts_verified':True}
(B/'验证/资产核验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False),flush=True)
