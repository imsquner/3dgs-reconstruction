"""Local pinned GS-ICP smoke/baseline, fixed optimizer-step budget.

Stage resume only: incomplete online tracking is restarted, never resumed from PLY.
"""
import argparse,os,sys,json,time,hashlib,random,inspect,textwrap
from pathlib import Path
import numpy as np,torch,torch.multiprocessing as mp,cv2
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--growth-weight',type=float,default=0.);p.add_argument('--depth-weight',type=float,default=.01);p.add_argument('--coverage-weight',type=float,default=0.);p.add_argument('--variant',choices=['original','improved-shape'],default='original');p.add_argument('--scene',default='tum-office');p.add_argument('--frames',type=int,default=40);p.add_argument('--steps-per-frame',type=int,default=10);p.add_argument('--association',choices=['original','strict'],default='original');p.add_argument('--run-id',required=True);p.add_argument('--seed',type=int,default=0);p.add_argument('--input-fps',type=float,default=0);a=p.parse_args()
SOURCE=B/'来源/GS-ICP-SLAM';OUT=B.parents[1]/'运行'/a.run_id
os.environ['MPLBACKEND']='Agg';sys.path.insert(0,str(SOURCE));sys.path.insert(0,str(B.parents[1]/'服务器'))
import gs_icp_slam as gs,mp_Tracker as tracking,mp_Mapper as mapping
from projection import patch_camera
patch_camera()
PROTOCOL=json.loads((B/'协议'/f'{a.scene}.json').read_text());selected=PROTOCOL['upstream_original_train' if a.association=='original' else 'strict_common_train'][:a.frames]
assert selected and len(selected)==a.frames
class SelectedTraj(gs.TrajManager):
 def __init__(self,*args,**kwargs):
  self.which_dataset='tum' if a.scene.startswith('tum-') else 'replica';self.dataset_path=PROTOCOL['source']
  self.gt_poses=np.array([r['reference_c2w'] for r in selected]);self.gt_poses_vis=self.gt_poses[:,:3,3]
  self.color_paths=[r['rgb_path'] for r in selected];self.depth_paths=[r['depth_path'] for r in selected]
gs.TrajManager=tracking.TrajManager=mapping.TrajManager=SelectedTraj
OriginalTarget=gs.SharedTargetPoints
class BoundedTarget(OriginalTarget):
 def __init__(self,n):super().__init__(min(n,1000000))
gs.SharedTargetPoints=BoundedTarget
old_input=gs.SharedGaussians.input_values
def finite_input(self,xyz,colors,rots,scales,z_values,trackable_filter):
 if not all(torch.isfinite(x).all() for x in (xyz,colors,rots,scales,z_values)):raise RuntimeError('Nonfinite input')
 if (scales<0).any():raise RuntimeError('Negative scale')
 return old_input(self,xyz,colors,rots,scales.clamp_min(1e-6),z_values,trackable_filter)
gs.SharedGaussians.input_values=finite_input
class LazyImages:
 def __init__(self,paths,color):self.paths=paths;self.index=0;self.color=color;self.start=None
 def __len__(self):return len(self.paths)-self.index
 def pop(self,index):
  assert index==0
  if self.color and a.input_fps>0:
   if self.start is None:self.start=time.monotonic()
   due=self.start+self.index/a.input_fps;time.sleep(max(0,due-time.monotonic()))
  path=self.paths[self.index];self.index+=1;im=cv2.imread(path,cv2.IMREAD_COLOR if self.color else cv2.IMREAD_ANYDEPTH)
  if im is None:raise RuntimeError('Image decode failed '+path)
  return im
def get_images(self,*args):return LazyImages(self.trajmanager.color_paths,True),LazyImages(self.trajmanager.depth_paths,False)
tracking.Tracker.get_images=get_images
# Completion time versus scheduled arrival includes decoding, GICP and mapper waits.
def frame_event(tracker,index):
 now=time.monotonic();due=(tracker.rgb_images.start+index/a.input_fps) if a.input_fps>0 else None
 with (OUT/'tracking-timing.jsonl').open('a') as f:f.write(json.dumps({'frame':index,'completion_monotonic':now,'scheduled_arrival_monotonic':due,'tracking_latency_seconds':now-due if due else None})+'\n')
tracking.frame_event=frame_event
tcode=textwrap.dedent(inspect.getsource(tracking.Tracker.tracking))
assert tcode.count('        self.iteration_images += 1')==1
tcode=tcode.replace('        self.iteration_images += 1','        frame_event(self,ii)\n        self.iteration_images += 1')
exec(tcode,tracking.__dict__);tracking.Tracker.tracking=tracking.__dict__['tracking']
# Spawn workers do not inherit the parent's Python RNG state.
def run_worker(system,role,rank):
 from worker_seed import seed_worker
 seed_worker(a.seed)
 print('WORKER_SEED',role,a.seed,flush=True)
 getattr(system,role)(rank)

def record_map_event(mapper):
 if mapper.train_iter%a.steps_per_frame==0:
  with (OUT/'mapping-timing.jsonl').open('a') as f:
   f.write(json.dumps({'mapping_iteration':mapper.train_iter,'completion_monotonic':time.monotonic(),'latest_tracking_frame':int(mapper.iter_shared[0]),'latest_inserted_keyframe':int(mapper.keyframe_idxs[-1]),'gaussians':len(mapper.gaussians.get_xyz),'gradient_bearing_step_calls':mapper.quality_gradient_step_calls})+'\n')
mapping.record_map_event=record_map_event

# Keep the official mapper and its parameters, constrain its asynchronous polling to a fixed step quota.
code=textwrap.dedent(inspect.getsource(mapping.Mapper.mapping))
assert code.count('    t = torch.zeros((1,1)).float().cuda()')==1
code=code.replace('    t = torch.zeros((1,1)).float().cuda()','    self.quality_gradient_step_calls=0\n    t = torch.zeros((1,1)).float().cuda()')
assert code.count('                self.gaussians.optimizer.step()')==1
code=code.replace('                self.gaussians.optimizer.step()','                self.quality_gradient_step_calls += int(any(g["params"][0].grad is not None for g in self.gaussians.optimizer.param_groups))\n                self.gaussians.optimizer.step()')
assert code.count('            self.train_iter += 1')==1
code=code.replace('            self.train_iter += 1','            self.train_iter += 1\n            record_map_event(self)')

code=code.replace('if self.end_of_dataset[0]:\n            break','if self.end_of_dataset[0] and not self.is_tracking_keyframe_shared[0] and not self.is_mapping_keyframe_shared[0] and self.train_iter >= '+str(a.frames*a.steps_per_frame)+':\n            break')
anchor='        if len(self.mapping_cams)>0:\n'
assert code.count(anchor)==1
replacement=anchor+'            quota = '+str(a.frames*a.steps_per_frame)+' if self.end_of_dataset[0] else (int(self.iter_shared[0])+1)*'+str(a.steps_per_frame)+'\n            if self.train_iter >= quota:\n                time.sleep(0.001)\n                continue\n'
code=code.replace(anchor,replacement)
if a.variant=='improved-shape':
 from online_quality_patch_v3 import patch_candidate_mapping
 code=patch_candidate_mapping(code,mapping,PROTOCOL.get('depth_trunc',3.),a.depth_weight,a.coverage_weight,a.growth_weight)
exec(code,mapping.__dict__);mapping.Mapper.mapping=mapping.__dict__['mapping']
def finish(self):
 if a.variant=='improved-shape':np.save(OUT/'birth-scales.npy',self.gaussians.quality_birth_scales.detach().cpu().numpy())
 assert self.train_iter==a.frames*a.steps_per_frame,(self.train_iter,a.frames*a.steps_per_frame)
 atomic_json(OUT/'mapping-summary.json',dict(gaussians=len(self.gaussians.get_xyz),keyframes=len(self.mapping_cams),mapping_iterations=self.train_iter,keyframe_indices=[int(x) for x in self.keyframe_idxs],gradient_bearing_optimizer_step_calls=self.quality_gradient_step_calls,peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated()))
 print('MAPPING_COMPLETE',self.train_iter,flush=True)
mapping.Mapper.calc_2d_metric=finish

def main():
 assert not OUT.exists(),'Unique run id required; preserve interrupted run'
 OUT.mkdir(parents=True);os.chdir(SOURCE);random.seed(a.seed);np.random.seed(a.seed);torch.manual_seed(a.seed)
 K=PROTOCOL['intrinsic'];config=OUT/'camera.txt';kind='tum' if a.scene.startswith('tum-') else 'replica'
 config.write_text('## camera parameters\nW H fx fy cx cy depth_scale depth_trunc dataset_type\n'+' '.join(str(x) for x in K+[PROTOCOL['depth_scale'],PROTOCOL.get('depth_trunc',3.0),kind])+'\n')
 from types import SimpleNamespace
 args=SimpleNamespace(dataset_path=PROTOCOL['source'],config=str(config),output_path=str(OUT),verbose=False,keyframe_th=.7,knn_maxd=99999.,overlapped_th=.0005,max_correspondence_distance=.02,trackable_opacity_th=.05,overlapped_th2=.00005,downsample_rate=10,test=None,save_results=True,rerun_viewer=False,demo=False)
 atomic_json(OUT/'manifest.json',dict(args=vars(args),quality_args=vars(a),frames=selected,protocol_sha256=sha256(B/'协议'/f'{a.scene}.json'),runner_sha256=sha256(__file__),source_manifest_sha256=sha256(B/'来源/source-manifest.json'),fixed_optimizer_steps=a.frames*a.steps_per_frame,quality_module_hashes={f:sha256(B/f) for f in ['online_quality_patch_v3.py','quality_spacing.py','quality_losses.py','quality_losses_v2.py','quality_depth_range.py','worker_seed.py','quality_coverage.py','quality_growth.py']},torch=torch.__version__,scope='Calibrated GS-ICP online insertion with fixed iteration budget, variant stated in quality_args; timestamps/latency report authoritative, no training-state resume'))
 atomic_json(OUT/'state.json',dict(status='running',pid=os.getpid(),started=time.time()))
 system=gs.GS_ICP_SLAM(args);children=[];start=time.monotonic()
 try:
  for role in ['tracking','mapping']:
   child=mp.Process(target=run_worker,args=(system,role,0));child.start();children.append(child)
  while any(c.is_alive() for c in children):
   for c in children:
    if c.exitcode not in [None,0]:raise RuntimeError('Worker failed '+str(c.exitcode))
   frame=int(system.iter_shared[0]);atomic_json(OUT/'heartbeat.json',dict(pid=os.getpid(),frame=frame,total=a.frames,elapsed=time.monotonic()-start,updated=time.time()))
   print('HEARTBEAT',frame,'/',a.frames,'elapsed',round(time.monotonic()-start,1),flush=True);time.sleep(5)
  for c in children:c.join();assert c.exitcode==0
  poses=system.final_pose.numpy();assert np.isfinite(poses).all() and np.allclose(poses[:,3,3],1)
  atomic_json(OUT/'final-poses.json',poses.tolist());atomic_json(OUT/'summary.json',dict(frames=len(poses),wall_seconds=time.monotonic()-start,worker_exitcodes=[c.exitcode for c in children]))
  artifacts=['scene.ply','final-poses.json','mapping-summary.json','manifest.json']
  if a.variant=='improved-shape':artifacts.append('birth-scales.npy')
  atomic_json(OUT/'state.json',dict(status='complete',pid=os.getpid(),finished=time.time(),artifacts={f:sha256(OUT/f) for f in artifacts}));print('RUN_COMPLETE',OUT,flush=True)
 except Exception as e:
  atomic_json(OUT/'state.json',dict(status='failed',error=str(e),pid=os.getpid()));raise
 finally:
  for c in children:
   if c.is_alive():c.terminate()
   c.join(timeout=5)
if __name__=='__main__':main()
