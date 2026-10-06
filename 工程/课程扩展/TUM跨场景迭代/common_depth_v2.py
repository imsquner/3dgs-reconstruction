"""Paired geometry comparison on identical valid pixels, no pose fitting."""
import sys,json,argparse,time
from pathlib import Path
import torch,numpy as np,cv2
from quality_core import atomic_json,sha256
from quality_losses import normalized_depth
B=Path(__file__).resolve().parent;E=B.parents[1]
sys.path.insert(0,str(B/'来源/GS-ICP-SLAM'));sys.path.insert(0,str(E/'服务器'))
from scene import GaussianModel
from scene.shared_objs import SharedCam
from gs_icp_slam import Pipe
from gaussian_renderer import render
from projection import patch_camera
from utils.graphics_utils import focal2fov
patch_camera()
p=argparse.ArgumentParser();p.add_argument('base');p.add_argument('candidate');a=p.parse_args()
base=E/'运行'/a.base;candidate=E/'运行'/a.candidate;manifest=json.loads((base/'manifest.json').read_text());scene=manifest['quality_args']['scene'];protocol=json.loads((B/'协议'/f'{scene}.json').read_text())
train=manifest['frames'];test=[r for r in protocol['upstream_original_validation' if manifest['quality_args']['association']=='original' else 'strict_validation'] if r['source_frame']<=max(x['source_frame'] for x in train)]
assert not {r['depth_id'] for r in train}&{r['depth_id'] for r in test}
models=[]
for R in [base,candidate]:
 m=GaussianModel(0);m.load_ply(str(R/'scene.ply'));models.append(m)
w,h,fx,fy,cx,cy=protocol['intrinsic'];cam=SharedCam(focal2fov(fx,w),focal2fov(fy,h),np.zeros((h,w,3),np.uint8),np.zeros((h,w),np.float32),cx,cy,fx,fy);pipe=Pipe(False,False,False);black=torch.zeros(3,device='cuda');white=torch.ones(3,device='cuda');rows=[];start=time.monotonic()
for j,row in enumerate(test):
 T=np.linalg.inv(np.array(row['reference_c2w']));cam.setup_cam(T[:3,:3].T,T[:3,3],np.zeros((h,w,3),np.uint8),np.zeros((h,w),np.float32));cam.on_cuda()
 depth=torch.from_numpy(cv2.imread(row['depth_path'],-1).astype(np.float32)/protocol['depth_scale']).cuda();valid=(depth>.1)&(depth<protocol.get('depth_trunc',3.))
 predictions=[];covers=[]
 with torch.no_grad():
  for m in models:
   r=render(cam,m,pipe,black);alpha=1-(render(cam,m,pipe,white)['render']-r['render']).mean(0).clamp(0,1);pred=normalized_depth(r['render_depth'].squeeze(),alpha)
   cover=valid&(alpha>.95)&torch.isfinite(pred)&(pred>0);predictions.append(pred);covers.append(cover)
  common=covers[0]&covers[1];scores=[]
  for pred,cover in zip(predictions,covers):
   error=abs(pred-depth);scores.append({'common_mae_m':float(error[common].mean()) if common.any() else None,'common_rmse_m':float(error[common].square().mean().sqrt()) if common.any() else None,'full_valid_penalized_mae_m':float(torch.where(cover,error,torch.full_like(error,protocol.get('depth_trunc',3.)))[valid].mean()),'coverage':float(cover.sum()/valid.sum())})
  rows.append({'source_frame':row['source_frame'],'common_pixels':int(common.sum()),'valid_pixels':int(valid.sum()),'base':scores[0],'candidate':scores[1]})
 if j%20==0 or j+1==len(test):print('COMMON_DEPTH',j+1,'/',len(test),flush=True)
means={version:{k:float(np.mean([r[version][k] for r in rows if r[version][k] is not None])) for k in rows[0][version]} for version in ['base','candidate']}
out={'base':a.base,'candidate':a.candidate,'signature':{'base':sha256(base/'scene.ply'),'candidate':sha256(candidate/'scene.ply'),'evaluator':sha256(__file__)},'means':means,'rows':rows,'seconds':time.monotonic()-start,'scope':'Same sensor-valid pixels and intersection coverage for both versions. Full-valid penalty 3m for uncovered; diagnostic only, not altered acceptance metric. No depth groundtruth perfection claim.'}
out['depth_valid_range_m']=[.1,protocol.get('depth_trunc',3.)];out['uncovered_penalty_m']=protocol.get('depth_trunc',3.)
out['scope']=out['scope'].replace('penalty 3m','penalty from dataset maximum depth '+str(out['uncovered_penalty_m'])+'m')
atomic_json(candidate/'评价/common-depth.json',out);print('COMMON_DEPTH_COMPLETE',means,flush=True)
