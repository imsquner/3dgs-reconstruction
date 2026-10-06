"""Offline fixed-topology refinement; resumable optimizer/RNG checkpoints."""
import os,sys,json,time,argparse,random
from pathlib import Path
import numpy as np,torch,cv2
from quality_core import atomic_json,sha256
from quality_losses import normalized_depth,valid_depth_loss,needle_regularizer
B=Path(__file__).resolve().parent;E=B.parents[1]
sys.path.insert(0,str(B/'来源/GS-ICP-SLAM'));sys.path.insert(0,str(E/'服务器'))
from scene import GaussianModel
from scene.shared_objs import SharedCam
from gs_icp_slam import Pipe
from arguments import SLAMParameters
from gaussian_renderer import render
from projection import patch_camera
from utils.graphics_utils import focal2fov
from utils.loss_utils import ssim,l1_loss
patch_camera()
p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--run',required=True);p.add_argument('--variant',choices=['original','improved'],required=True);p.add_argument('--steps',type=int,required=True);p.add_argument('--stop-after',type=int);a=p.parse_args()
BASE=E/'运行'/a.base;RUN=E/'运行'/a.run;RUN.mkdir(exist_ok=True)
bm=json.loads((BASE/'manifest.json').read_text());protocol=json.loads((B/'协议'/f'{bm["quality_args"]["scene"]}.json').read_text());rows=bm['frames'];poses=json.loads((BASE/'final-poses.json').read_text())
assert len(rows)==len(poses)
indices=json.loads((BASE/'mapping-summary.json').read_text())['keyframe_indices']
manifest={'base_run':a.base,'variant':a.variant,'steps':a.steps,'seed':0,'base_map':sha256(BASE/'scene.ply'),'base_manifest':sha256(BASE/'manifest.json'),'poses':sha256(BASE/'final-poses.json'),'runner':sha256(__file__),'losses':sha256(B/'quality_losses.py'),'keyframes':indices,'scope':'offline fixed topology, estimated training poses only; no pruning/densification; original means original losses without online growth/pruning','weights':{'depth':.01,'needle':.002,'ratio':10,'growth':8}}
if (RUN/'manifest.json').exists():assert json.loads((RUN/'manifest.json').read_text())==manifest,'Protocol changed; use a new run ID'
else:atomic_json(RUN/'manifest.json',manifest)
if (RUN/'state.json').exists():
 old=json.loads((RUN/'state.json').read_text())
 if old['status']=='complete' and old['map_sha256']==sha256(RUN/'scene.ply'):print('REFINEMENT_REUSED',flush=True);sys.exit(0)
torch.manual_seed(0);np.random.seed(0);random.seed(0)
model=GaussianModel(0);args=SLAMParameters();start_step=0;elapsed_before=0
checkpoint=RUN/'checkpoint.pt'
if checkpoint.exists():
 c=torch.load(checkpoint);assert c['manifest']==manifest
 model.restore(c['model'],args);spacing=c['spacing'];start_step=c['step'];elapsed_before=c['elapsed']
 torch.set_rng_state(c['rng']);torch.cuda.set_rng_state_all(c['cuda_rng']);random.setstate(c['python_rng'])
 print('RESUME',start_step,flush=True)
else:
 model.load_ply(str(BASE/'scene.ply'));model.spatial_lr_scale=2.5;model.training_setup(args)
 spacing=model.get_scaling.detach().sort(dim=-1,descending=True).values[:,1].clone()
w,h,fx,fy,cx,cy=protocol['intrinsic'];cam=SharedCam(focal2fov(fx,w),focal2fov(fy,h),np.zeros((h,w,3),np.uint8),np.zeros((h,w),np.float32),cx,cy,fx,fy);pipe=Pipe(False,False,False);black=torch.zeros(3,device='cuda');white=torch.ones(3,device='cuda')
# Keep only keyframe observations in bounded CPU cache; one GPU camera at a time.
cache={}
for i in indices:
 rgb=cv2.imread(rows[i]['rgb_path']);dep=cv2.imread(rows[i]['depth_path'],-1)
 assert rgb is not None and dep is not None
 cache[i]=(cv2.cvtColor(rgb,cv2.COLOR_BGR2RGB),dep.astype(np.float32)/protocol['depth_scale'])
start=time.monotonic();last=0
def save(step,status):
 elapsed=elapsed_before+time.monotonic()-start
 c={'manifest':manifest,'model':model.capture(),'spacing':spacing,'step':step,'elapsed':elapsed,'rng':torch.get_rng_state(),'cuda_rng':torch.cuda.get_rng_state_all(),'python_rng':random.getstate()}
 temp=RUN/'checkpoint.pt.partial';torch.save(c,temp);os.replace(temp,checkpoint)
 atomic_json(RUN/'state.json',{'status':status,'step':step,'total':a.steps,'pid':os.getpid(),'updated':time.time(),'elapsed_seconds':elapsed,'checkpoint_sha256':sha256(checkpoint)})
for step in range(start_step,a.steps):
 i=random.choice(indices);rgb,dep=cache[i];T=np.linalg.inv(np.array(poses[i]));cam.setup_cam(T[:3,:3].T,T[:3,3],rgb,dep);cam.on_cuda()
 gt=torch.from_numpy(rgb).permute(2,0,1).float().cuda()/255;depth=torch.from_numpy(dep).cuda()
 pkg=render(cam,model,pipe,black);image=pkg['render'];raw=pkg['render_depth'].squeeze()
 if a.variant=='original':
  target=gt*(depth>0);loss=.8*l1_loss(image,target)[1]+.2*(1-ssim(image,target)[1])+.1*l1_loss(raw/10,depth/10)[1]
 else:
  trans=(render(cam,model,pipe,white)['render']-image).mean(0).clamp(0,1);alpha=1-trans
  loss=.8*(image-gt).abs().mean()+.2*(1-ssim(image,gt)[1])+.01*valid_depth_loss(normalized_depth(raw,alpha),depth,alpha)+.002*needle_regularizer(model.get_scaling,spacing)
 assert torch.isfinite(loss),'Nonfinite loss'
 loss.backward();model.optimizer.step();model.optimizer.zero_grad(set_to_none=True)
 if step%20==0:
  assert all(torch.isfinite(x).all() for x in [model._xyz,model._scaling,model._opacity]),'Nonfinite parameters'
 if time.monotonic()-last>5 or step+1==a.steps:
  elapsed=elapsed_before+time.monotonic()-start;print('REFINE',step+1,'/',a.steps,'loss',float(loss.detach()),'seconds',round(elapsed,2),flush=True)
  atomic_json(RUN/'heartbeat.json',{'step':step+1,'total':a.steps,'pid':os.getpid(),'updated':time.time(),'loss':float(loss.detach())});last=time.monotonic()
 if (step+1)%100==0 or step+1==a.steps:save(step+1,'running')
 if a.stop_after and step+1>=a.stop_after:
  save(step+1,'paused_for_resume_test');print('CONTROLLED_STOP',step+1,flush=True);sys.exit(0)
model.save_ply(str(RUN/'scene.ply'));save(a.steps,'complete')
state=json.loads((RUN/'state.json').read_text());state['map_sha256']=sha256(RUN/'scene.ply');state['peak_cuda_allocated_bytes']=torch.cuda.max_memory_allocated();atomic_json(RUN/'state.json',state)
print('REFINEMENT_COMPLETE',state,flush=True)
