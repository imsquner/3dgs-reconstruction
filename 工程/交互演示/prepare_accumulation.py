"""Actual past RGB-D observations transformed by the recorded estimated poses.
No reference pose, final Gaussian, or future frame contributes to an earlier state.
"""
from pathlib import Path
import json,hashlib,time
import numpy as np
from PIL import Image
B=Path(__file__).resolve().parent;G=B.parents[1];project=G.parent
D=project/'MonoGS/datasets/tum/rgbd_dataset_freiburg3_long_office_household'
R=G/'工程/运行/srv-demo-officefull-5fps';A=B/'assets';images=A/'office-input';images.mkdir(exist_ok=True)
rows=[json.loads(x) for x in (R/'frames.jsonl').read_text().splitlines()]
depth_rows=[x.split() for x in (D/'depth.txt').read_text().splitlines() if x and not x.startswith('#')]
depth_t=np.array([float(x[0]) for x in depth_rows]);seen=set();chunks=[];points=[];colors=[];total=0;started=time.time()
fx,fy,cx,cy=535.4,539.2,320.1,247.6
yy,xx=np.mgrid[0:480:6,0:640:6]
selected=list(range(0,len(rows),5))
if selected[-1]!=len(rows)-1:selected.append(len(rows)-1)
for count,i in enumerate(selected):
 r=rows[i];rgb_rel=Path(r['image_path']).parts[-2:];rgb=D.joinpath(*rgb_rel);t=float(rgb.stem);j=int(np.argmin(np.abs(depth_t-t)));assert abs(depth_t[j]-t)<.08
 depth=D/depth_rows[j][1];assert rgb.exists() and depth.exists()
 color=np.asarray(Image.open(rgb).convert('RGB'));z=np.asarray(Image.open(depth),dtype=np.float32)[::6,::6]/5000
 valid=(z>.1)&(z<3);xyz=np.stack([(xx-cx)*z/fx,(yy-cy)*z/fy,z],axis=-1)[valid]
 pose=np.array(r['estimated_c2w']);world=(xyz@pose[:3,:3].T+pose[:3,3]).astype('<f4');col=color[::6,::6][valid]
 keys=np.floor(world/.015).astype(np.int32);keep=[]
 for k,key in enumerate(map(tuple,keys)):
  if key not in seen:seen.add(key);keep.append(k)
 points.append(world[keep]);colors.append(col[keep]);total+=len(keep)
 preview=images/f'{i:05d}.jpg';im=Image.fromarray(color);im.resize((320,240)).save(preview,quality=88)
 chunks.append(dict(source_frame=i,time_seconds=i/5,point_count=total,added=len(keep),input_image='assets/office-input/'+preview.name,rgb_path='/'.join(rgb_rel),depth_path=depth_rows[j][1],rgb_sha256=hashlib.sha256(rgb.read_bytes()).hexdigest(),depth_sha256=hashlib.sha256(depth.read_bytes()).hexdigest(),depth_time_difference_seconds=float(abs(depth_t[j]-t))))
 if count%25==0:print('ACCUMULATION_HEARTBEAT',count,len(selected),total,'elapsed',round(time.time()-started,1),flush=True)
p=np.concatenate(points);c=np.concatenate(colors);assert len(p)==total and np.isfinite(p).all()
(A/'office-observations.xyz').write_bytes(p.astype('<f4').tobytes());(A/'office-observations.rgb').write_bytes(c.tobytes())
m=dict(run=R.name,input_fps=5,source_frames=len(rows),sampled_frames=len(selected),pixel_stride=6,frame_stride=5,voxel_size_m=.015,depth_scale=5000,depth_range_m=[.1,3],intrinsic=[640,480,fx,fy,cx,cy],points=total,chunks=chunks,scope='Sequential RGB-D observation accumulation with recorded estimated GICP poses. First observation per voxel is retained; no future points in earlier draw ranges. This is point-cloud accumulation, NOT saved historical 3DGS optimizer states. NOT a new measured online throughput experiment.',pose_source_sha256=hashlib.sha256((R/'frames.jsonl').read_bytes()).hexdigest(),position_sha256=hashlib.sha256((A/'office-observations.xyz').read_bytes()).hexdigest(),color_sha256=hashlib.sha256((A/'office-observations.rgb').read_bytes()).hexdigest())
(A/'office-accumulation.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8');print('ACCUMULATION_READY',total,flush=True)
