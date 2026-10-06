"""Native renderer sensitivity to fixed needle flags; no map file modification."""
import sys,json,argparse,time
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
patch_camera()
p=argparse.ArgumentParser();p.add_argument('base');p.add_argument('run');a=p.parse_args();BASE=E/'运行'/a.base;RUN=E/'运行'/a.run;map_hash=sha256(RUN/'scene.ply')
bm=json.loads((BASE/'manifest.json').read_text());protocol=json.loads((B/'协议'/f'{bm["quality_args"]["scene"]}.json').read_text());views=json.loads((BASE/'评价/metrics.json').read_text())['fixed_views'];poses=np.array(json.loads((BASE/'final-poses.json').read_text()))
m=GaussianModel(0);m.load_ply(str(RUN/'scene.ply'));s=m.get_scaling.detach().sort(dim=-1,descending=True).values;flags=(s[:,0]>.2)&(s[:,0]/s[:,1].clamp_min(1e-6)>10)&(m.get_opacity.detach().squeeze()>.5);original=m._opacity.detach().clone()
w,h,fx,fy,cx,cy=protocol['intrinsic'];cam=SharedCam(focal2fov(fx,w),focal2fov(fy,h),np.zeros((h,w,3),np.uint8),np.zeros((h,w),np.float32),cx,cy,fx,fy);pipe=Pipe(False,False,False);bg=torch.zeros(3,device='cuda');OUT=RUN/'评价/固定视角原生审计';OUT.mkdir(exist_ok=True);rows=[];start=time.monotonic()
try:
 for view in views:
  P=poses[view['train_index']].copy();P[:3,3]+=P[:3,0]*view['offset_local_x_m'];T=np.linalg.inv(P);cam.setup_cam(T[:3,:3].T,T[:3,3],np.zeros((h,w,3),np.uint8),np.zeros((h,w),np.float32));cam.on_cuda()
  with torch.no_grad():
   m._opacity.copy_(original);full=render(cam,m,pipe,bg)['render'].clamp(0,1)
   m._opacity[flags]=-80;without=render(cam,m,pipe,bg)['render'].clamp(0,1);m._opacity.copy_(original)
   difference=(full-without).abs().mean(0);mask=(difference>.03).cpu().numpy();effect=float(difference.mean())
  native_name=Path(view['path']).stem+'-native.png';rgb=full.permute(1,2,0).cpu().numpy()
  assert cv2.imwrite(str(OUT/native_name),cv2.cvtColor((rgb*255).astype('uint8'),cv2.COLOR_RGB2BGR))
  name=Path(view['path']).stem+'-effect.png';assert cv2.imwrite(str(OUT/name),mask.astype(np.uint8)*255)
  rows.append({**view,'affected_pixels_rgb_l1_gt0p03':int(mask.sum()),'affected_fraction':float(mask.mean()),'whole_image_mean_effect':effect,'mask':name,'render_rgb':native_name})
  print('VISIBLE_NEEDLE_EFFECT',view['path'],int(mask.sum()),flush=True)
finally:
 with torch.no_grad():m._opacity.copy_(original)
assert torch.equal(m._opacity.detach(),original) and sha256(RUN/'scene.ply')==map_hash
atomic_json(OUT/'影响.json',{'run':a.run,'base':a.base,'map_sha256':map_hash,'script_sha256':sha256(__file__),'flagged':int(flags.sum()),'rows':rows,'seconds':time.monotonic()-start,'scope':'Native full render versus flags opacity disabled in memory, restored. RGB effect is visible sensitivity, not an artifact truth label; legitimate thin structures may be flagged. Pair with all-view table/chair/blur review; do not label all affected pixels as errors. Original files unchanged.'})
