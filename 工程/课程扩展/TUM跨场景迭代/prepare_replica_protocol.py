"""Freeze rendered Replica IDs before frozen-rule transfer; no training."""
import json
from pathlib import Path
import numpy as np,cv2
from quality_core import atomic_json,sha256,split_depth_groups
B=Path(__file__).resolve().parent;data=B/'数据/Replica/office0';provenance=json.loads((data/'来源核验.json').read_text())
assert provenance['complete'] and provenance['rgb']==2000 and provenance['depth']==2000
poses=np.loadtxt(data/'traj.txt').reshape(-1,4,4);assert poses.shape==(2000,4,4) and np.isfinite(poses).all()
assert np.allclose(poses[:,3,:],np.array([0,0,0,1]),atol=1e-5)
assert np.allclose(np.linalg.det(poses[:,:3,:3]),1,atol=1e-3)
rows=[]
for i in range(2000):
 rgb=data/'results'/f'frame{i:06d}.jpg';dep=data/'results'/f'depth{i:06d}.png';assert rgb.is_file() and dep.is_file()
 rows.append({'source_frame':i,'rgb_index':i,'rgb_path':str(rgb),'depth_path':str(dep),'depth_id':dep.name,'rgb_timestamp':None,'depth_timestamp':None,'reference_c2w':poses[i].tolist()})
checks=[]
for i in [0,999,1999]:
 rgb=cv2.imread(rows[i]['rgb_path']);dep=cv2.imread(rows[i]['depth_path'],-1)
 assert rgb.shape==(680,1200,3) and dep.shape==(680,1200) and dep.dtype==np.uint16
 checks.append({'frame':i,'depth_m_p10_p50_p90':np.quantile(dep[dep>0].astype(float)/6553.5,[.1,.5,.9]).tolist(),'missing_fraction':float((dep==0).mean())})
held={i for i in range(10,2000,10)};train,test=split_depth_groups(rows,held);assert len(train)==1801 and len(test)==199
manifest={'scene':'replica-office0','source':str(data),'source_frames':2000,'intrinsic':[1200,680,600.,600.,599.5,339.5],'depth_scale':6553.5,'depth_trunc':12.,'upstream_original_train':train,'upstream_original_validation':test,'strict_common_train':train,'strict_validation':test,'holdout_source_ids':sorted(held),'file_hashes':{'traj.txt':sha256(data/'traj.txt'),'来源核验.json':sha256(data/'来源核验.json')},'input_checks':checks,'protocol':'NICE-SLAM/iMAP-rendered Replica office0. RGB/depth paired by shared integer frame ID; no measured physical timestamps. Pose only first-frame initialization and evaluation. Synthetic rendered depth scale 6553.5, original GS-ICP config truncation12m. Frozen-parameter transfer, no test tuning.'}
out=B/'协议/replica-office0.json'
if out.exists():assert json.loads(out.read_text())==manifest
else:atomic_json(out,manifest)
print('REPLICA_PROTOCOL_FROZEN',len(train),len(test),checks,flush=True)
