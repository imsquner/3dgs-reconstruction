"""Unified diagnostic validation; reference poses used only for evaluation."""
import os,sys,argparse,json,time
from pathlib import Path
import numpy as np,torch,cv2
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent;E=B.parents[1]
sys.path.insert(0,str(B/'来源/GS-ICP-SLAM'));sys.path.insert(0,str(E/'服务器'))
from scene import GaussianModel
from scene.shared_objs import SharedCam
from gs_icp_slam import Pipe
from gaussian_renderer import render
from projection import patch_camera
from utils.graphics_utils import focal2fov
from utils.loss_utils import ssim
patch_camera()
p=argparse.ArgumentParser();p.add_argument('run');a=p.parse_args();RUN=E/'运行'/a.run
m=json.loads((RUN/'manifest.json').read_text());base=m.get('base_run')
bm=json.loads((E/'运行'/base/'manifest.json').read_text()) if base else m
scene=bm['quality_args']['scene'];protocol=json.loads((B/'协议'/f'{scene}.json').read_text());train=bm['frames']
test=[r for r in protocol['upstream_original_validation' if bm['quality_args']['association']=='original' else 'strict_validation'] if r['source_frame']<=max(x['source_frame'] for x in train)]
assert test and not {r['rgb_path'] for r in train}&{r['rgb_path'] for r in test}
assert not {r['depth_id'] for r in train}&{r['depth_id'] for r in test}
OUT=RUN/'评价';OUT.mkdir(exist_ok=True)
signature={'map':sha256(RUN/'scene.ply'),'protocol':sha256(B/'协议'/f'{scene}.json'),'evaluator':sha256(__file__)}
if (OUT/'metrics.json').exists():
 old=json.loads((OUT/'metrics.json').read_text())
 if old['signature']==signature:print('EVALUATION_REUSED',old['means'],flush=True);sys.exit(0)
model=GaussianModel(0);model.load_ply(str(RUN/'scene.ply'));model.active_sh_degree=0
w,h,fx,fy,cx,cy=protocol['intrinsic'];cam=SharedCam(focal2fov(fx,w),focal2fov(fy,h),np.zeros((h,w,3),np.uint8),np.zeros((h,w),np.float32),cx,cy,fx,fy);pipe=Pipe(False,False,False)
def camera(P,offset=0):
 P=np.array(P).copy();P[:3,3]+=P[:3,0]*offset;T=np.linalg.inv(P)
 cam.setup_cam(T[:3,:3].T,T[:3,3],np.zeros((h,w,3),np.uint8),np.zeros((h,w),np.float32));cam.on_cuda()
def rgb_write(path,rgb):assert cv2.imwrite(str(path),cv2.cvtColor((rgb*255).astype('uint8'),cv2.COLOR_RGB2BGR))
rows=[];start=time.monotonic()
for j,row in enumerate(test):
 camera(row['reference_c2w'])
 with torch.no_grad():
  r=render(cam,model,pipe,torch.zeros(3,device='cuda'));white=render(cam,model,pipe,torch.ones(3,device='cuda'))['render']
  trans=(white-r['render']).mean(0).clamp(0,1);alpha=1-trans
  expected=(r['render_depth'].squeeze()-15*trans)/alpha.clamp_min(1e-8)
  pred=expected.cpu().numpy();alpha=alpha.cpu().numpy();rgb=r['render'].permute(1,2,0).cpu().numpy().clip(0,1)
 ref=cv2.cvtColor(cv2.imread(row['rgb_path']),cv2.COLOR_BGR2RGB).astype(np.float32)/255;depth=cv2.imread(row['depth_path'],-1).astype(np.float32)/protocol['depth_scale']
 assert np.isfinite(rgb).all() and np.isfinite(pred).all()
 valid=(depth>.1)&(depth<3);covered=valid&(alpha>.95)&(pred>0)
 error=pred[covered]-depth[covered];score=ssim(torch.from_numpy(rgb).permute(2,0,1)[None],torch.from_numpy(ref).permute(2,0,1)[None])[1].item()
 mse=np.mean((rgb-ref)**2)
 rows.append(dict(source_frame=row['source_frame'],psnr_db=float(-10*np.log10(max(mse,1e-12))),ssim=float(score),coverage=float(covered.sum()/max(1,valid.sum())),depth_mae_m=float(abs(error).mean()) if len(error) else None,depth_rmse_m=float(np.sqrt(np.mean(error**2))) if len(error) else None,valid_depth_pixels=int(valid.sum()),covered_pixels=int(covered.sum())))
 if j%10==0 or j==len(test)-1:
  rgb_write(OUT/f'held-{row["source_frame"]:04d}.png',rgb)
  print('EVAL',j+1,'/',len(test),rows[-1],flush=True)
means={k:float(np.mean([r[k] for r in rows if r[k] is not None])) for k in ['psnr_db','ssim','coverage','depth_mae_m','depth_rmse_m']}
poses=json.loads((E/'运行'/(base or a.run)/'final-poses.json').read_text())
views=[]
for i in sorted(set([0,len(poses)//2,len(poses)-1])):
 for offset in [0.,.2,.4]:
  camera(poses[i],offset)
  with torch.no_grad():rgb=render(cam,model,pipe,torch.zeros(3,device='cuda'))['render'].permute(1,2,0).cpu().numpy().clip(0,1)
  name=f'free-{i:04d}-{offset:.1f}.png';rgb_write(OUT/name,rgb);views.append({'train_index':i,'offset_local_x_m':offset,'path':name})
report={'run':a.run,'signature':signature,'validation_frames':len(rows),'means':means,'rows':rows,'fixed_views':views,'seconds':time.monotonic()-start,'protocol':'No RGB/depth ID overlap; whole-image RGB PSNR/SSIM; depth reference valid 0.1..3m, alpha>0.95 coverage + MAE/RMSE; GT cameras only for evaluation, no fitting. TUM office is development validation. No novel-view truth; free-view images qualitative. Map geometry is sensor-reference consistency, not perfect GT.'}
atomic_json(OUT/'metrics.json',report);print('EVALUATION_COMPLETE',means,flush=True)
