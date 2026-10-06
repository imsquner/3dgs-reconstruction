"""Offline evaluation of images excluded from online tracking and mapping."""
import argparse,json,sys,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('run',type=Path);a=p.parse_args();run=a.run
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'MonoGS'))
import cv2,numpy as np,torch,yaml
from munch import munchify
from gaussian_splatting.utils.loss_utils import ssim
from gaussian_splatting.scene.gaussian_model import GaussianModel
from gaussian_splatting.gaussian_renderer import render
from gaussian_splatting.utils.graphics_utils import focal2fov
from utils.camera_utils import Camera
c=yaml.safe_load((run/'effective-config.yaml').read_text());m=json.loads((run/'manifest.json').read_text());cal=c['Dataset']['Calibration'];factor=m['downsample']
assert c['Dataset']['sensor_type']=='depth', 'Only verified TUM metric RGB-D supported'
held=json.loads((run/'heldout-frames.json').read_text());train=json.loads((run/'all-frame-poses.json').read_text());assert not set(r['image_path'] for r in held)&set(r['image_path'] for r in train)
w,h=cal['width']//factor,cal['height']//factor
K=np.array([[cal['fx'],0,cal['cx']],[0,cal['fy'],cal['cy']],[0,0,1]],dtype=float)
maps=cv2.initUndistortRectifyMap(K,np.array([cal[k] for k in ('k1','k2','p1','p2','k3')]),np.eye(3),K,(cal['width'],cal['height']),cv2.CV_32FC1)
cam=Camera.init_from_gui(0,torch.eye(4,device='cuda'),focal2fov(cal['fx']/factor,w),focal2fov(cal['fy']/factor,h),cal['fx']/factor,cal['fy']/factor,cal['cx']/factor,cal['cy']/factor,h,w)
model=GaussianModel(0,config=c);model.load_ply(str(run/'point_cloud/final/point_cloud.ply'));bg=torch.zeros(3,device='cuda');rows=[]
out=run/'heldout-evaluation';out.mkdir(exist_ok=False)
for row in held:
 image=cv2.cvtColor(cv2.imread(row['image_path']),cv2.COLOR_BGR2RGB);depth=cv2.imread(row['depth_path'],cv2.IMREAD_ANYDEPTH).astype(np.float32)/cal['depth_scale']
 if cal['distorted']:
  image=cv2.remap(image,*maps,cv2.INTER_LINEAR)
  # Reference depth must occupy the same undistorted projection as the renderer.
  depth=cv2.remap(depth,*maps,cv2.INTER_NEAREST)
 image=torch.from_numpy(image.copy()).permute(2,0,1).float()[None]/255
 image=torch.nn.functional.interpolate(image,size=(h,w),mode='bilinear',align_corners=False,antialias=True)[0].permute(1,2,0).numpy()
 depth=cv2.resize(depth,(w,h),interpolation=cv2.INTER_NEAREST)
 T=np.asarray(row['reference_w2c']);cam.update_RT(torch.tensor(T[:3,:3],device='cuda',dtype=torch.float32),torch.tensor(T[:3,3],device='cuda',dtype=torch.float32))
 with torch.no_grad():r=render(cam,model,munchify(c['pipeline_params']),bg)
 rgb=r['render'].clamp(0,1).permute(1,2,0).cpu().numpy();opacity=r['opacity'].squeeze().cpu().numpy();pred=r['depth'].squeeze().cpu().numpy()/np.maximum(opacity,1e-8)
 valid=np.isfinite(depth)&(depth>.1)&(depth<10);mask=valid&np.isfinite(pred)&(pred>0)&(opacity>.95)
 error=pred[mask]-depth[mask];mse=float(np.mean((rgb-image)**2))
 score=ssim(torch.from_numpy(image).permute(2,0,1)[None],torch.from_numpy(rgb).permute(2,0,1)[None]).item()
 result=dict(source_frame=row['source_frame'],psnr_db=float(-10*np.log10(max(mse,1e-12))),ssim=float(score),reference_valid_pixels=int(valid.sum()),covered_pixels=int(mask.sum()),coverage=float(mask.sum()/max(valid.sum(),1)),depth_mae_m=float(np.mean(np.abs(error))) if mask.any() else None,depth_rmse_m=float(np.sqrt(np.mean(error**2))) if mask.any() else None)
 rows.append(result);print('HELDOUT '+json.dumps(result),flush=True)
 if len(rows) in (1,len(held)):
  panel=cv2.cvtColor((np.concatenate([image,rgb],axis=1)*255).astype(np.uint8),cv2.COLOR_RGB2BGR);cv2.imwrite(str(out/f'frame-{row["source_frame"]:04d}.png'),panel)
report=dict(protocol='Excluded every tenth source image before tracking/mapping; final PLY rendered at provided GT pose; no map alignment; no exposure fitting; full-image PSNR/SSIM; alpha-normalized expected depth; depth mask alpha>0.95 and reference 0.1..10m; macro means over frames',input_truth='TUM sensor depth reference, not perfect surface ground truth',training_depth_note='Official loader undistorts RGB but leaves depth unrectified; this inherited mismatch is a limitation when distortion is enabled',evaluator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),heldout_count=len(rows),training_count=len(train),rows=rows)
for key in ('psnr_db','ssim','coverage','depth_mae_m','depth_rmse_m'):report['mean_'+key]=float(np.mean([r[key] for r in rows if r[key] is not None]))
(out/'metrics.json').write_text(json.dumps(report,indent=2));print('EVALUATION_COMPLETE '+json.dumps({k:v for k,v in report.items() if k!='rows'}),flush=True)
