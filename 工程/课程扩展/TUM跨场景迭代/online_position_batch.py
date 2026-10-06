"""TUM covariance-source ablation; no transfer data used for selection."""
import json,os,subprocess,sys,time
from pathlib import Path
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent;E=B.parents[1];state=B/'状态/online-position-v10.json'
jobs=[(40,'birth','optimized','local-tum-quality-pos40-birth-opt-v10'),(40,'birth','raw-gicp','local-tum-quality-pos40-birth-raw-v10'),(240,'optimized','optimized','local-tum-quality-pos240-opt-opt-v10'),(240,'birth','optimized','local-tum-quality-pos240-birth-opt-v10'),(240,'birth','raw-gicp','local-tum-quality-pos240-birth-raw-v10')]
files=['quality_tracking_positions.py','run_online_v10.py','quality_tracking_covariance.py','online_quality_patch_v3.py','quality_growth.py','worker_seed.py','quality_spacing.py','quality_losses.py','quality_losses_v2.py','quality_depth_range.py','quality_coverage.py','quality_core.py','evaluate_local_v2.py','common_depth_v2.py','visible_needle_effect_v2.py','report_online.py','quality_gate.py','build_matched_view_boards_v5.py']
pin={f:sha256(B/f) for f in files};plan={'jobs':jobs,'scripts':pin,'seed':0,'steps_per_frame':20,'depth_weight':.05,'coverage_weight':.05,'needle_weight':.002,'growth_weight':0.,'growth_factor':8.,'protocol_sha256':sha256(B/'协议/tum-office.json'),'scope':'TUM development: position optimized or stored-birth XYZ, covariance optimized or raw-GICP; original opacity/trackable selection/pruning retained. Growth0, no independent raw-map accumulation. No ground truth feed except initial pose. Short as-fast replay, no real-time claim. Single asynchronous exploration, not transfer freeze.'}
p=B/'协议/online-position-v10-frozen.json'
if p.exists():assert json.loads(p.read_text())==plan
else:atomic_json(p,plan)
def status(stage,**extra):atomic_json(state,dict(pid=os.getpid(),updated=time.time(),stage=stage,**extra))
def run(script,args,log):
 assert all(sha256(B/f)==h for f,h in pin.items())
 with (B/'日志'/log).open('a',buffering=1) as output:
  child=subprocess.Popen([sys.executable,str(B/script),*args],stdout=output,stderr=subprocess.STDOUT)
  try:
   while child.poll() is None:
    status('running',script=script,args=args,child_pid=child.pid,log=log);print('POSITION_CHILD',script,child.pid,flush=True);time.sleep(10)
  finally:
   if child.poll() is None:
    child.terminate()
    try:child.wait(timeout=10)
    except subprocess.TimeoutExpired:child.kill();child.wait()
  if child.returncode:status('failed',script=script,args=args,log=log,exit=child.returncode);raise RuntimeError(log)
base='local-tum-quality-online-original240-b10-v5'
for frames,positions,mode,name in jobs:
 r=E/'运行'/name
 if r.exists():
  saved=json.loads((r/'state.json').read_text());assert saved['status']=='complete','Preserve interrupted run; new ID required'
  assert all(sha256(r/f)==h for f,h in saved['artifacts'].items())
  q=json.loads((r/'manifest.json').read_text())['quality_args'];assert (q['frames'],q['tracking_positions'],q['tracking_covariance'],q['growth_weight'],q['seed'],q['steps_per_frame'])==(frames,positions,mode,0.,0,20)
 else:run('run_online_v10.py',['--scene','tum-office','--frames',str(frames),'--steps-per-frame','20','--variant','improved-shape','--depth-weight','.05','--coverage-weight','.05','--growth-weight','0','--tracking-covariance',mode,'--tracking-positions',positions,'--run-id',name],name+'.log')
 if frames==40:
  import numpy as np
  points=np.load(r/'tracking-birth-positions.npy');n=json.loads((r/'mapping-summary.json').read_text())['gaussians']
  assert points.shape==(n,3) and np.isfinite(points).all()
  atomic_json(B/'验证'/('birth-position40-'+mode+'.json'),dict(run=name,gaussians=n,positions_sha256=sha256(r/'tracking-birth-positions.npy'),scope='CUDA40 insert/prune/export with birth-position references aligned to rendered topology. Not truth or quality gate.'))
 if frames==240:
  run('evaluate_local_v2.py',[name],name+'-eval.log')
  run('common_depth_v2.py',[base,name],name+'-common-depth.log')
  run('visible_needle_effect_v2.py',[base,name],name+'-native-views.log')
  run('quality_gate.py',[base,name],name+'-gate.log')
 run('report_online.py',[name],name+'-report.log')
 with (r/'实验记录.md').open('a') as f:f.write('\ntracking positions='+positions+' / covariance='+mode+'，growth0；opacity/trackable/pruning仍上游。仅开发，首帧外参考未馈入，不称完整改善。\n')
run('build_matched_view_boards_v5.py',['--base',base,'--runs',base,*[j[3] for j in jobs if j[0]==240],'--tag','online-position-v10'],'online-position-v10-boards.log')
status('complete',jobs=jobs);print('POSITION_V10_SHORT_COMPLETE_PENDING_1200_STRESS',flush=True)
