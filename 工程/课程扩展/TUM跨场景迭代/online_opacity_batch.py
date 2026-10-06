"""TUM-only opacity source ablation; render pruning and observations unchanged."""
import json,os,subprocess,sys,time
from pathlib import Path
import numpy as np
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent;E=B.parents[1]
assert json.loads((B/'状态/online-barrier-v14.json').read_text())['stage']=='complete'
jobs=[(40,'birth','local-tum-quality-opacity40-birth-v15'),(240,'learned','local-tum-quality-opacity240-learned-v15'),(240,'birth','local-tum-quality-opacity240-birth-v15')]
files=['online_opacity_batch.py','run_online_v15.py','quality_tracking_opacity.py','quality_tracking_positions.py','quality_tracking_covariance.py','quality_mapping_barrier_v2.py','online_quality_patch_v3.py','quality_growth.py','quality_spacing.py','quality_losses.py','quality_losses_v2.py','quality_depth_range.py','quality_coverage.py','worker_seed.py','quality_core.py','evaluate_local_v2.py','common_depth_v2.py','visible_needle_effect_v2.py','quality_gate.py','report_online.py','build_matched_view_boards_v6.py','../../服务器/projection.py']
pin={f:sha256(B/f) for f in files};base='local-tum-quality-barrier240-original-b10-v14'
plan=dict(jobs=jobs,scripts=pin,frames_source='tum-office',mapping_schedule='observation-barrier',input_fps=5.,seed=0,steps_per_frame=20,tracking_positions='birth',tracking_covariance='raw-gicp',depth_weight=.05,coverage_weight=.05,needle_weight=.002,growth_weight=0.,protocol_sha256=sha256(B/'协议/tum-office.json'),base_map_sha256=sha256(E/'运行'/base/'scene.ply'),scope='TUM development: learned or stored-birth opacity target selection only. Birth opacity does not bypass upstream trackable mask or render pruning; not independent raw-map. Both new candidates use same runner, schedule and budget; reference original controls fromv14 are functional original/identical inputs and timing policy, read-only trace differences reported. No bitwise determinism or full/transfer claim.')
p=B/'协议/online-opacity-v15-frozen.json'
if p.exists():assert json.loads(p.read_text())==plan
else:atomic_json(p,plan)
state=B/'状态/online-opacity-v15.json'
def status(stage,**extra):atomic_json(state,dict(pid=os.getpid(),updated=time.time(),stage=stage,**extra))
def run(script,args,log):
 assert all(sha256(B/f)==h for f,h in pin.items())
 with (B/'日志'/log).open('a',buffering=1) as out:
  child=subprocess.Popen([sys.executable,str(B/script),*args],stdout=out,stderr=subprocess.STDOUT)
  try:
   while child.poll() is None:
    status('running',script=script,args=args,child_pid=child.pid,log=log);print('OPACITY_CHILD',script,child.pid,flush=True);time.sleep(10)
  finally:
   if child.poll() is None:
    child.terminate()
    try:child.wait(timeout=10)
    except subprocess.TimeoutExpired:child.kill();child.wait()
  if child.returncode:status('failed',script=script,args=args,log=log,exit=child.returncode);raise RuntimeError(log)
for frames,opacity,name in jobs:
 r=E/'运行'/name
 if r.exists():
  saved=json.loads((r/'state.json').read_text());assert saved['status']=='complete','Preserve incomplete run; uniqueID required'
  assert all(sha256(r/f)==h for f,h in saved['artifacts'].items())
  q=json.loads((r/'manifest.json').read_text())['quality_args'];assert (q['frames'],q['steps_per_frame'],q['tracking_opacity'],q['tracking_positions'],q['tracking_covariance'],q['mapping_schedule'])==(frames,20,opacity,'birth','raw-gicp','observation-barrier')
 else:run('run_online_v15.py',['--scene','tum-office','--frames',str(frames),'--steps-per-frame','20','--variant','improved-shape','--tracking-positions','birth','--tracking-covariance','raw-gicp','--tracking-opacity',opacity,'--mapping-schedule','observation-barrier','--depth-weight','.05','--coverage-weight','.05','--growth-weight','0','--input-fps','5','--seed','0','--run-id',name],name+'.log')
 if opacity=='birth':
  values=np.load(r/'tracking-birth-opacity.npy');n=json.loads((r/'mapping-summary.json').read_text())['gaussians'];assert values.shape==(n,) and np.isfinite(values).all() and np.allclose(values,.1)
  atomic_json(B/'验证/映射边界'/f'{name}-birth-opacity.json',dict(count=n,opacity_sha256=sha256(r/'tracking-birth-opacity.npy'),scope='Stored birthopacity .1 aligned to actual final render topology after insert/prune; opacity not truth confidence.'))
 if frames==240:
  for script,args,tag in [('evaluate_local_v2.py',[name],'eval'),('common_depth_v2.py',[base,name],'common-depth'),('visible_needle_effect_v2.py',[base,name],'native-views'),('quality_gate.py',[base,name],'gate')]:run(script,args,name+'-'+tag+'.log')
 run('report_online.py',[name],name+'-report.log')
 with (r/'实验记录.md').open('a') as f:f.write('\nTracking opacity source='+opacity+'；birth XYZ/raw covariance，原prune/trackable仍保留。同期runner15 learned/birth对照，旧v14原控制读写诊断差异单列，不称位确定。\n')
runs=[base,'local-tum-quality-barrier240-original-b20-v14',*[j[2] for j in jobs if j[0]==240]]
run('build_matched_view_boards_v6.py',['--base',base,'--runs',*runs,'--tag','online-opacity-v15'],'online-opacity-v15-boards.log')
status('complete',scope='Short-stage execution only; full TUM and transfer still required, all-view/geometry review pending.')
print('OPACITY_V15_COMPLETE_PENDING_REVIEW',flush=True)
