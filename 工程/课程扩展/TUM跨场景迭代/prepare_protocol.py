"""Pin source and source-observation splits before quality experiments."""
from pathlib import Path
import json,sys,shutil,subprocess
import numpy as np
from scipy.spatial.transform import Rotation
from quality_core import paired_frames,split_depth_groups,atomic_json,sha256
B=Path(__file__).resolve().parent;E=B.parents[1];ROOT=E.parents[1]
SOURCE=E/'源码/GS-ICP-SLAM';SNAP=B/'来源/GS-ICP-SLAM'
commit=subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip()
assert commit=='5f996a872a979406b270fe0ee3b0a8f25c5e9ae3'
files=list(SOURCE.glob('*.py'))
for folder in ['arguments','utils','scene','gaussian_renderer','configs']:
 files.extend(p for p in (SOURCE/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in ['.py','.txt','.json','.yaml'])
hashes={}
for src in files:
 rel=src.relative_to(SOURCE);dst=SNAP/rel;dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists():assert sha256(dst)==sha256(src),'Source changed; new protocol version required'
 else:shutil.copy2(src,dst)
 hashes[str(rel)]=sha256(dst)
atomic_json(B/'来源/source-manifest.json',{'upstream_commit':commit,'files':hashes,'scope':'Isolated runtime Python/config snapshot; installed native binaries reused and separately hashed in each run'})
for scene,data in [('tum-office',ROOT/'MonoGS/datasets/tum/rgbd_dataset_freiburg3_long_office_household'),('tum-desk',E/'数据/TUM/rgbd_dataset_freiburg1_desk')]:
 def load(name):return np.loadtxt(data/name,dtype=str)
 rgb,dep,gt=load('rgb.txt'),load('depth.txt'),load('groundtruth.txt');tr,td,tg=[a[:,0].astype(float) for a in [rgb,dep,gt]]
 # Recreate original source indices first; strict sync is a tagged common-subset alternative.
 assoc=[]
 for i,t in enumerate(tr):
  j=int(np.argmin(abs(td-t)));k=int(np.argmin(abs(tg-t)))
  if abs(td[j]-t)<.08 and abs(tg[k]-t)<.08:assoc.append((i,j,k))
 selected=[0]
 for a in range(1,len(assoc)):
  if tr[assoc[a][0]]-tr[assoc[selected[-1]][0]]>1/32:selected.append(a)
 rows=[]
 for source_frame,a in enumerate(selected):
  i,j,k=assoc[a];P=np.eye(4);P[:3,:3]=Rotation.from_quat(gt[k,4:8].astype(float)).as_matrix();P[:3,3]=gt[k,1:4].astype(float)
  rows.append(dict(source_frame=source_frame,rgb_index=i,rgb_path=str(data/rgb[i,1]),depth_path=str(data/dep[j,1]),depth_id=str(dep[j,1]),rgb_timestamp=float(tr[i]),depth_timestamp=float(td[j]),reference_c2w=P.tolist()))
 held={r['source_frame'] for r in rows if r['source_frame']>0 and r['source_frame']%10==0}
 train,test=split_depth_groups(rows,held)
 # Development validation only; TUM office already examined, desk is future frozen-parameter verification.
 pairs=dict(paired_frames(tr.tolist(),td.tolist(),.02));strict=[]
 for r in rows:
  j=pairs.get(r['rgb_index'])
  if j is not None:
   r=dict(r);r['depth_path']=str(data/dep[j,1]);r['depth_id']=str(dep[j,1]);r['depth_timestamp']=float(td[j]);strict.append(r)
 strict_train,strict_test=split_depth_groups(strict,held)
 assert strict_train and strict_train[0]['source_frame'] not in held
 manifest={'scene':scene,'source':str(data),'source_frames':len(rows),'intrinsic':[640,480,535.4,539.2,320.1,247.6] if scene=='tum-office' else [640,480,517.3,516.5,318.6,255.3],'depth_scale':5000,'upstream_original_train':train,'upstream_original_validation':test,'strict_common_train':strict_train,'strict_validation':strict_test,'holdout_source_ids':sorted(held),'file_hashes':{name:sha256(data/name) for name in ['rgb.txt','depth.txt','groundtruth.txt']},'protocol':'Reference poses for first-frame initialization/evaluation only. Paired frame IDs and depth-group exclusion frozen. Strict association offline preprocessing; no live-buffer claim. Original and strict variants have separate matching controls. office validation is development, desk is frozen-parameter verification; histories not unseen.'}
 for label,training,testing in [('original',train,test),('strict',strict_train,strict_test)]:
  assert not {r['rgb_path'] for r in training}&{r['rgb_path'] for r in testing}
  assert not {r['depth_id'] for r in training}&{r['depth_id'] for r in testing}
 atomic_json(B/'协议'/f'{scene}.json',manifest)
 print('PROTOCOL_FROZEN',scene,'source',len(rows),'original_train',len(train),'validation',len(test),'strict_train',len(strict_train),'strict_validation',len(strict_test),flush=True)
print('SOURCE_SNAPSHOT',len(hashes),'files',flush=True)
