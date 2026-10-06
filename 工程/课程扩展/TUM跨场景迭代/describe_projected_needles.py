"""Fixed-view needle projection upper-bound, NOT a visible artifact mask."""
import json,argparse
from pathlib import Path
import numpy as np,cv2
from plyfile import PlyData
from projection_diagnostic import project_covariance,footprint_mask
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent;E=B.parents[1]
p=argparse.ArgumentParser();p.add_argument('base');p.add_argument('run');a=p.parse_args();BASE=E/'运行'/a.base;RUN=E/'运行'/a.run
bm=json.loads((BASE/'manifest.json').read_text());protocol=json.loads((B/'协议'/f'{bm["quality_args"]["scene"]}.json').read_text());views=json.loads((BASE/'评价/metrics.json').read_text())['fixed_views'];poses=np.array(json.loads((BASE/'final-poses.json').read_text()));v=PlyData.read(RUN/'scene.ply')['vertex'].data
xyz=np.stack([v[k] for k in ['x','y','z']],-1);scales=np.exp(np.stack([v[f'scale_{i}'] for i in range(3)],-1));q=np.stack([v[f'rot_{i}'] for i in range(4)],-1);opacity=1/(1+np.exp(-np.clip(v['opacity'],-80,80)));ordered=np.sort(scales,axis=-1)
flags=(ordered[:,2]>.2)&(ordered[:,2]/np.maximum(ordered[:,1],1e-6)>10)&(opacity>.5);assert np.isfinite(scales).all() and (np.linalg.norm(q[flags],axis=1)>1e-10).all()
OUT=RUN/'评价/针状投影描述';OUT.mkdir(exist_ok=True);rows=[];w,h,*_=protocol['intrinsic']
for view in views:
 P=poses[view['train_index']].copy();P[:3,3]+=P[:3,0]*view['offset_local_x_m']
 xy,cov,z=project_covariance(xyz[flags],scales[flags],q[flags],P,protocol['intrinsic']);mask,n=footprint_mask(xy,cov,z,opacity[flags],w,h)
 name=Path(view['path']).stem+'-footprint.png';assert cv2.imwrite(str(OUT/name),mask.astype(np.uint8)*255)
 rows.append({**view,'projected_needles':n,'upper_bound_pixels':int(mask.sum()),'upper_bound_fraction':float(mask.mean()),'mask':name})
report={'run':a.run,'base':a.base,'signature':{'map':sha256(RUN/'scene.ply'),'poses':sha256(BASE/'final-poses.json'),'helper':sha256(B/'projection_diagnostic.py')},'criteria':{'largest_axis_m':.2,'largest_middle_ratio':10,'opacity':.5,'projected_alpha_threshold':.05,'lowpass_pixels2':.3},'flagged':int(flags.sum()),'rows':rows,'scope':'Geometric screen footprint without depth occlusion/actual visibility; includes legitimate thin objects. Descriptive upper bound only; cannot pass the 30-percent visible-artifact gate by itself. Inspect all paired RGB views and object integrity.'}
atomic_json(OUT/'描述.json',report);print('PROJECTED_DESCRIPTOR',a.run,report['flagged'],[r['upper_bound_pixels'] for r in rows],flush=True)
