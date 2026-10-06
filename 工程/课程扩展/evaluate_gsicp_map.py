import os,sys,argparse,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('--heldout',action='store_true');a=p.parse_args();run=a.run
ROOT=Path(__file__).resolve().parents[1]/'源码/GS-ICP-SLAM';sys.path.insert(0,str(ROOT))
import cv2,numpy as np,torch
from scene import GaussianModel
from gaussian_renderer import render
from scene.shared_objs import SharedCam
from gs_icp_slam import Pipe
from utils.graphics_utils import focal2fov
from utils.loss_utils import ssim
m=json.loads((run/'manifest.json').read_text());params=Path(m['args']['config']).read_text().splitlines()[2].split();w,h=int(params[0]),int(params[1]);fx,fy,cx,cy,depth_scale=[float(x) for x in params[2:7]]
from plyfile import PlyData
fields=PlyData.read(str(run/'scene.ply'))['vertex'].data.dtype.names
rest=sum(name.startswith('f_rest_') for name in fields);degree=int(round(np.sqrt(rest/3+1)-1));assert rest==3*((degree+1)**2-1)
model=GaussianModel(degree);model.load_ply(str(run/'scene.ply'));model.active_sh_degree=degree;pipe=Pipe(False,False,False);bg=torch.zeros(3,device='cuda')
cam=SharedCam(focal2fov(fx,w),focal2fov(fy,h),np.zeros((h,w,3),np.uint8),np.zeros((h,w),np.float32),cx,cy,fx,fy)
def camera(pose,offset=0):
 T=np.linalg.inv(np.asarray(pose));T[0,3]+=offset;cam.setup_cam(T[:3,:3].T,T[:3,3],np.zeros((h,w,3),np.uint8),np.zeros((h,w),np.float32));cam.on_cuda()
def output():
 with torch.no_grad():return render(cam,model,pipe,bg)
out=run/('heldout-evaluation' if a.heldout else 'map-replay');out.mkdir(exist_ok=False)
if not a.heldout:
 poses=json.loads((run/'final-poses.json').read_text());rows=[]
 for offset in (0,.03,-.03):
  camera(poses[-1],offset);r=output();rgb=r['render'].clamp(0,1).permute(1,2,0).cpu().numpy();assert np.isfinite(rgb).all();path=out/f'view-{offset:+.2f}.png';assert cv2.imwrite(str(path),cv2.cvtColor((rgb*255).astype(np.uint8),cv2.COLOR_RGB2BGR));rows.append(dict(offset_x_m=offset,path=str(path),finite=True))
 (out/'replay-audit.json').write_text(json.dumps(dict(gaussians=int(model.get_xyz.shape[0]),views=rows,scope='Offline exported PLY reloaded; shifted camera views, not online FPS evidence'),indent=2));print('REPLAY_OK',flush=True)
else:
 held=json.loads((run/'heldout-frames.json').read_text());train=[json.loads(x) for x in (run/'frames.jsonl').read_text().splitlines()];assert not set(r['image_path'] for r in held)&set(r['image_path'] for r in train);rows=[]
 for row in held:
  camera(row['reference_c2w']);r=output();raw_rgb=r['render'].permute(1,2,0).cpu().numpy();rgb=np.clip(raw_rgb,0,1);gt=cv2.cvtColor(cv2.imread(row['image_path']),cv2.COLOR_BGR2RGB).astype(np.float32)/255;depth=cv2.imread(row['depth_path'],cv2.IMREAD_ANYDEPTH).astype(np.float32)/depth_scale
  with torch.no_grad():white=render(cam,model,pipe,torch.ones(3,device='cuda'))['render'].permute(1,2,0).cpu().numpy()
  delta=white-raw_rgb;assert np.max(np.ptp(delta,axis=2))<1e-4
  transmittance=np.clip(delta.mean(axis=2),0,1);alpha=1-transmittance;pred=(r['render_depth'].squeeze().cpu().numpy()-15*transmittance)/np.maximum(alpha,1e-8)
  valid=(depth>.1)&(depth<10)&np.isfinite(depth);mask=valid&np.isfinite(pred)&(pred>0)&(alpha>.95);error=pred[mask]-depth[mask];mse=float(np.mean((rgb-gt)**2));score=ssim(torch.from_numpy(rgb).permute(2,0,1)[None],torch.from_numpy(gt).permute(2,0,1)[None])[1].item()
  result=dict(source_frame=row['source_frame'],psnr_db=float(-10*np.log10(max(mse,1e-12))),ssim=float(score),coverage=float(mask.sum()/max(valid.sum(),1)),depth_mae_m=float(np.mean(np.abs(error))) if mask.any() else None,depth_rmse_m=float(np.sqrt(np.mean(error**2))) if mask.any() else None);rows.append(result);print('HELDOUT '+json.dumps(result),flush=True)
  if len(rows) in (1,len(held)):cv2.imwrite(str(out/f'frame-{row["source_frame"]:04d}.png'),cv2.cvtColor((np.concatenate([gt,rgb],axis=1)*255).astype(np.uint8),cv2.COLOR_RGB2BGR))
 report=dict(protocol='Every tenth source frame excluded from tracking/mapping; GT pose render; no alignment; no exposure fitting; raw TUM RGB/depth per official GSICP projection; sensor depth not perfect mesh truth; macro frame means',depth_protocol='Renderer depth is D+15*T_depth. In forward.cu RGB/depth transmittance follow identical alpha updates; infer T from white-background minus black-background RGB, check channel agreement, remove 15m background and normalize by alpha. Mask alpha>0.95 and reference0.1..10m',projection_note='Official GSICP SharedCam uses centered FoV projection; supplied cx/cy are used for ICP unprojection. No calibration correction applied to mapping',heldout_count=len(rows),training_count=len(train),rows=rows,evaluator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 for key in ('psnr_db','ssim','coverage','depth_mae_m','depth_rmse_m'):report['mean_'+key]=float(np.mean([r[key] for r in rows if r[key] is not None]))
 (out/'metrics.json').write_text(json.dumps(report,indent=2));print('EVALUATION_COMPLETE '+json.dumps({k:v for k,v in report.items() if k!='rows'}),flush=True)
