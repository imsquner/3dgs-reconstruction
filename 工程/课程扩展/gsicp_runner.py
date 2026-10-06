"""Pinned GS-ICP: lazy sequential input, observations and managed workers."""
import os,sys,time,json,hashlib,random,subprocess
from pathlib import Path
ROOT=Path(os.environ['GSICP_SOURCE']);sys.path.insert(0,str(ROOT))
import numpy as np,cv2,torch,torch.multiprocessing as mp
import gs_icp_slam as gs,mp_Tracker as tracking,mp_Mapper as mapping
random.seed(0);np.random.seed(0);torch.manual_seed(0)
OUT=Path(os.environ['GSICP_OUTPUT']);LIMIT=int(os.environ['GSICP_FRAMES']);FPS=float(os.environ.get('GSICP_INPUT_FPS','0'))
OriginalTraj=gs.TrajManager
class LimitedTraj(OriginalTraj):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.gt_poses=self.gt_poses[:LIMIT];self.gt_poses_vis=self.gt_poses_vis[:LIMIT];self.color_paths=self.color_paths[:LIMIT];self.depth_paths=self.depth_paths[:LIMIT]
  self.source_indices=list(range(len(self.color_paths)));stride=int(os.environ.get('GSICP_HOLDOUT','0'))
  if stride:
   assert stride>=2
   held=[i for i in self.source_indices if i>0 and i%stride==0]
   rows=[dict(source_frame=i,image_path=self.color_paths[i],depth_path=self.depth_paths[i],reference_c2w=self.gt_poses[i].tolist()) for i in held]
   if not (OUT/'heldout-frames.json').exists():(OUT/'heldout-frames.json').write_text(json.dumps(rows,indent=2))
   self.source_indices=[i for i in self.source_indices if i not in held]
   self.gt_poses=self.gt_poses[self.source_indices];self.gt_poses_vis=self.gt_poses_vis[self.source_indices];self.color_paths=[self.color_paths[i] for i in self.source_indices];self.depth_paths=[self.depth_paths[i] for i in self.source_indices]
gs.TrajManager=tracking.TrajManager=mapping.TrajManager=LimitedTraj
OriginalTarget=gs.SharedTargetPoints
class BoundedTarget(OriginalTarget):
 def __init__(self,num_points):super().__init__(min(num_points,1000000))
gs.SharedTargetPoints=BoundedTarget
OriginalInput=gs.SharedGaussians.input_values
def finite_input(self,xyz,colors,rots,scales,z_values,trackable_filter):
 if not all(torch.isfinite(x).all() for x in (xyz,colors,rots,scales,z_values)) or (scales<0).any():
  raise RuntimeError('Nonfinite or negative incoming Gaussian parameters')
 count=int((scales<1e-6).sum())
 if count:
  with (OUT/'numerical-guards.jsonl').open('a') as f:f.write(json.dumps(dict(scale_components_floored=count,min_incoming_scale=float(scales.min()),floor=1e-6,reason='Prevent log(0) for degenerate covariance'))+'\n')
 return OriginalInput(self,xyz,colors,rots,scales.clamp_min(1e-6),z_values,trackable_filter)
gs.SharedGaussians.input_values=finite_input
TRACKER=None;CLOCK={'origin':None,'arrival':None,'start':None}
class LazyImages:
 def __init__(self,paths,color,indices):self.paths=list(paths);self.color=color;self.index=0;self.indices=indices
 def __len__(self):return len(self.paths)-self.index
 def pop(self,index):
  assert index==0
  if self.color:
   if CLOCK['origin'] is None:
    CLOCK['origin']=time.monotonic();(OUT/'input-clock.json').write_text(json.dumps(dict(origin_monotonic=CLOCK['origin'],input_fps=FPS,source_indices=self.indices)))
   CLOCK['arrival']=CLOCK['origin']+self.indices[self.index]/FPS if FPS else time.monotonic()
   if FPS:time.sleep(max(0,CLOCK['arrival']-time.monotonic()))
   CLOCK['start']=time.monotonic()
  path=self.paths[self.index];self.index+=1;image=cv2.imread(path,cv2.IMREAD_COLOR if self.color else cv2.IMREAD_ANYDEPTH)
  if image is None:raise RuntimeError('Image decode failed '+path)
  return image
def get_images(self,*args):
 global TRACKER
 TRACKER=self
 return LazyImages(self.trajmanager.color_paths,True,self.trajmanager.source_indices),LazyImages(self.trajmanager.depth_paths,False,self.trajmanager.source_indices)
tracking.Tracker.get_images=get_images
OriginalBar=tracking.tqdm
class ObservedBar(OriginalBar):
 def update(self,n=1):
  result=super().update(n)
  if TRACKER is not None and CLOCK['start'] is not None:
   torch.cuda.synchronize();idx=TRACKER.iteration_images
   row=dict(frame=idx,wall_seconds=time.monotonic()-CLOCK['origin'],input_fps=FPS,arrival_to_tracking_complete_seconds=time.monotonic()-CLOCK['arrival'],processing_seconds=time.monotonic()-CLOCK['start'],estimated_c2w=np.asarray(TRACKER.poses[-1]).tolist(),reference_c2w=TRACKER.trajmanager.gt_poses[idx].tolist(),image_path=TRACKER.trajmanager.color_paths[idx])
   with (OUT/'frames.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
   if idx%20==0:print('GSICP_FRAME '+json.dumps({k:v for k,v in row.items() if not k.endswith('c2w')}),flush=True)
  return result
tracking.tqdm=ObservedBar
record={'video':None,'origin':None,'last':None,'frames':0,'source_frame':-1}
MAP_LAST=-1
OPTIMIZER_STEPS=0
OriginalStep=torch.optim.Adam.step
def observed_step(self,*args,**kwargs):
 global OPTIMIZER_STEPS
 result=OriginalStep(self,*args,**kwargs);OPTIMIZER_STEPS+=1
 if OPTIMIZER_STEPS==1 or OPTIMIZER_STEPS%10==0:
  torch.cuda.synchronize()
  with (OUT/'mapping-updates.jsonl').open('a') as f:f.write(json.dumps(dict(step=OPTIMIZER_STEPS,monotonic=time.monotonic()))+'\n')
 return result
torch.optim.Adam.step=observed_step
OriginalRender=mapping.render_3
def recorded_render(cam,model,*args,**kwargs):
 global MAP_LAST
 result=OriginalRender(cam,model,*args,**kwargs)
 idx=int(cam.cam_idx[0])
 if idx>MAP_LAST:
  torch.cuda.synchronize();now=time.monotonic();clock=json.loads((OUT/'input-clock.json').read_text())
  source_index=clock['source_indices'][idx]
  obs=dict(training_frame=idx,source_frame=source_index,monotonic=now,elapsed_from_input=now-clock['origin_monotonic'],gaussians=int(model.get_xyz.shape[0]),map_render_ready_age_seconds=now-clock['origin_monotonic']-source_index/FPS if FPS else None)
  with (OUT/'map-frames.jsonl').open('a') as f:f.write(json.dumps(obs)+'\n')
  MAP_LAST=idx
 if os.environ.get('GSICP_RECORD')=='1' and idx>record['source_frame']:
  rgb=result['render'].detach().clamp(0,1).permute(1,2,0).cpu().numpy();image=cam.original_image.detach().clamp(0,1).permute(1,2,0).cpu().numpy()
  image=cv2.resize(image,(rgb.shape[1],rgb.shape[0]));panel=cv2.cvtColor((np.concatenate([image,rgb],axis=1)*255).astype(np.uint8),cv2.COLOR_RGB2BGR)
  now=time.monotonic()
  if record['video'] is None:
   record['origin']=now;record['video']=cv2.VideoWriter(str(OUT/'online-map.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),10,(panel.shape[1],panel.shape[0]));assert record['video'].isOpened()
  elapsed=now-record['origin'];desired=int(elapsed*10)
  while record['last'] is not None and record['frames']<desired:record['video'].write(record['last']);record['frames']+=1
  cv2.putText(panel,f'Input keyframe {idx} | Online GS-ICP map | {elapsed:.1f}s',(8,24),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,255,0),1)
  if record['frames']<=desired:record['video'].write(panel);record['frames']+=1
  record['last']=panel;record['source_frame']=idx
  if idx==0 or idx%40==0:cv2.imwrite(str(OUT/f'map-frame-{idx:04d}.png'),panel)
 return result
mapping.render_3=recorded_render
def finish_mapping(self):
 if record['video'] is not None:record['video'].release()
 rows=dict(gaussians=int(self.gaussians.get_xyz.shape[0]),keyframes=len(self.mapping_cams),mapping_iterations=self.train_iter,recorded_frames=record['frames'],encoder_fps=10,recording_scope='Existing online training render at increasing keyframes, hold frames to retain wall time; not every tracked input frame',internal_image_evaluation='Skipped; requires separate held-out evaluation')
 (OUT/'mapping-summary.json').write_text(json.dumps(rows,indent=2));print('MAPPING_COMPLETE '+json.dumps(rows),flush=True)
mapping.Mapper.calc_2d_metric=finish_mapping
def main():
 OUT.mkdir(exist_ok=False);random.seed(0);np.random.seed(0);torch.manual_seed(0);os.chdir(ROOT)
 from types import SimpleNamespace
 config=os.environ['GSICP_CONFIG'];args=SimpleNamespace(dataset_path=os.environ['GSICP_DATA'],config=config,output_path=str(OUT),verbose=False,keyframe_th=.7,knn_maxd=99999.,overlapped_th=5e-4,max_correspondence_distance=.02,trackable_opacity_th=.05,overlapped_th2=5e-5,downsample_rate=10,test=None,save_results=True,rerun_viewer=False,demo=False)
 manifest=dict(source_commit=os.environ['GSICP_COMMIT'],wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),config_sha256=hashlib.sha256(Path(config).read_bytes()).hexdigest(),frames=LIMIT,input_fps=FPS,seed=0,gt_usage='First pose initialization and evaluation only; subsequent poses estimated with GICP',input_policy='Lazy sequential PNG reads; optional fixed arrivals; late frames retained',target_capacity=1000000,environment='Torch1.12.1+cu116 compatibility experiment; different from official Torch2.0 env',args=vars(args))
 manifest['native_patch_sources_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'submodules/fast_gicp/CMakeLists.txt',ROOT/'submodules/fast_gicp/setup.py',ROOT/'submodules/fast_gicp/include/fast_gicp/gicp/impl/fast_gicp_impl.hpp']}
 manifest['numerical_scale_floor_m']=1e-6
 manifest['holdout_stride']=int(os.environ.get('GSICP_HOLDOUT','0'))
 import pygicp,diff_gaussian_rasterization
 manifest['native_binaries_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(pygicp.__file__),Path(pygicp.__file__).parent/'libfast_gicp.so',Path(diff_gaussian_rasterization._C.__file__)]}
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));start=time.monotonic();system=gs.GS_ICP_SLAM(args);processes=[]
 try:
  for fn in (system.tracking,system.mapping):
   child=mp.Process(target=fn,args=(0,));child.start();processes.append(child)
  while any(p.is_alive() for p in processes):
   for child in processes:
    if child.exitcode not in (None,0):raise RuntimeError('Worker failed '+str(child.exitcode))
   print('GSICP_HEARTBEAT frame='+str(int(system.iter_shared[0]))+' elapsed='+str(round(time.monotonic()-start,1)),flush=True);time.sleep(10)
  for child in processes:child.join();assert child.exitcode==0
  poses=system.final_pose.numpy();assert np.isfinite(poses).all() and np.allclose(poses[:,3,3],1)
  (OUT/'final-poses.json').write_text(json.dumps(poses.tolist()));summary=dict(frames=len(poses),wall_seconds=time.monotonic()-start,worker_exitcodes=[p.exitcode for p in processes]);(OUT/'summary.json').write_text(json.dumps(summary,indent=2));print('COMPLETE '+json.dumps(summary),flush=True)
 finally:
  for child in processes:
   if child.is_alive():child.terminate()
   child.join(timeout=5)
if __name__=='__main__':main()
