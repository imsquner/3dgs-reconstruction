"""TUM covariance-source ablation; no transfer data used for selection."""
import json,os,subprocess,sys,time
from pathlib import Path
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent;E=B.parents[1];state=B/'状态/online-geometry-map-v9.json'
jobs=[(40,.01,'local-tum-quality-rawmap40-v9'),(240,0.,'local-tum-quality-rawmap240-g0-v9'),(240,.01,'local-tum-quality-rawmap240-g01-v9')]
files=['quality_tracking_geometry.py','run_online_v9.py','quality_tracking_covariance.py','online_quality_patch_v3.py','quality_growth.py','worker_seed.py','quality_spacing.py','quality_losses.py','quality_losses_v2.py','quality_depth_range.py','quality_coverage.py','quality_core.py','evaluate_local_v2.py','common_depth_v2.py','visible_needle_effect_v2.py','report_online.py','quality_gate.py','build_matched_view_boards_v4.py']
pin={f:sha256(B/f) for f in files};plan={'jobs':jobs,'scripts':pin,'seed':0,'steps_per_frame':20,'depth_weight':.05,'coverage_weight':.05,'needle_weight':.002,'growth_weights':[0.,.01],'growth_factor':8.,'protocol_sha256':sha256(B/'协议/tum-office.json'),'tracking_geometry':'raw-map','tracking_covariance':'raw-gicp','scope':'TUM development only: independent stored observed XYZ/rotation/raw-GICP scales, same upstream trackable indices and overlap selection; render opacity/pruning do not alter registration map. Estimated coordinates, not ground truth. Short fast replay, single asynchronous exploratory run, not transfer freeze.'}
p=B/'协议/online-geometry-map-v9-frozen.json'
if p.exists():assert json.loads(p.read_text())==plan
else:atomic_json(p,plan)
def status(stage,**extra):atomic_json(state,dict(pid=os.getpid(),updated=time.time(),stage=stage,**extra))
def run(script,args,log):
 assert all(sha256(B/f)==h for f,h in pin.items())
 with (B/'日志'/log).open('a',buffering=1) as output:
  child=subprocess.Popen([sys.executable,str(B/script),*args],stdout=output,stderr=subprocess.STDOUT)
  try:
   while child.poll() is None:
    status('running',script=script,args=args,child_pid=child.pid,log=log);print('GEOMETRY_MAP_CHILD',script,child.pid,flush=True);time.sleep(10)
  finally:
   if child.poll() is None:
    child.terminate()
    try:child.wait(timeout=10)
    except subprocess.TimeoutExpired:child.kill();child.wait()
  if child.returncode:status('failed',script=script,args=args,log=log,exit=child.returncode);raise RuntimeError(log)
base='local-tum-quality-online-original240-b10-v5'
for frames,growth,name in jobs:
 r=E/'运行'/name
 if r.exists():
  saved=json.loads((r/'state.json').read_text());assert saved['status']=='complete','Preserve interrupted run; new ID required'
  assert all(sha256(r/f)==h for f,h in saved['artifacts'].items())
  q=json.loads((r/'manifest.json').read_text())['quality_args'];assert (q['frames'],q['tracking_covariance'],q['tracking_geometry'],q['growth_weight'],q['seed'],q['steps_per_frame'])==(frames,'raw-gicp','raw-map',growth,0,20)
 else:run('run_online_v9.py',['--scene','tum-office','--frames',str(frames),'--steps-per-frame','20','--variant','improved-shape','--depth-weight','.05','--coverage-weight','.05','--growth-weight',str(growth),'--tracking-covariance','raw-gicp','--tracking-geometry','raw-map','--run-id',name],name+'.log')
 if frames==40:
  import numpy as np
  refs=np.load(r/'tracking-geometry-reference.npz');summary=json.loads((r/'mapping-summary.json').read_text());n=summary['tracking_geometry_points']
  assert 0<n<=1000000 and refs['points'].shape==(n,3) and refs['scales'].shape==(n,3) and refs['rotations'].shape==(n,4)
  assert all(np.isfinite(refs[k]).all() for k in refs.files) and (refs['scales']>0).all() and np.allclose(np.linalg.norm(refs['rotations'],axis=-1),1,atol=1e-5)
  atomic_json(B/'验证/独立跟踪几何GPU40检查.json',dict(run=name,tracking_points=n,render_gaussians=summary['gaussians'],reference_sha256=sha256(r/'tracking-geometry-reference.npz'),scope='Real CUDA40 insert/optimization/prune/export; raw registration references not GT and need not equal render topology count.'))
 if frames==240:
  run('evaluate_local_v2.py',[name],name+'-eval.log')
  run('common_depth_v2.py',[base,name],name+'-common-depth.log')
  run('visible_needle_effect_v2.py',[base,name],name+'-native-views.log')
  run('quality_gate.py',[base,name],name+'-gate.log')
 run('report_online.py',[name],name+'-report.log')
 with (r/'实验记录.md').open('a') as f:f.write('\n独立原观测跟踪地图 raw-map/raw-gicp，growth '+str(growth)+'；不受渲染位置/旋转/尺度/opacity/pruning直接修改，但观测坐标与关键帧/重叠筛选依赖估计位姿。首帧外参考不馈入。\n')
run('build_matched_view_boards_v4.py',['--base',base,'--runs',base,'local-tum-quality-cov240-raw-v8',*[j[2] for j in jobs if j[0]==240],'--tag','online-geometry-map-v9'],'online-geometry-map-v9-boards.log')
status('complete',jobs=jobs);print('GEOMETRY_MAP_V9_SHORT_COMPLETE_PENDING_FULL',flush=True)
