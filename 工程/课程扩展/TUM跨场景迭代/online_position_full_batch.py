"""Full TUM development check of the selected birth-growth prior."""
import json,os,subprocess,sys,time
from pathlib import Path
from quality_core import atomic_json,sha256
from quality_gate import audit
B=Path(__file__).resolve().parent;E=B.parents[1]
name='local-tum-quality-online-full-birthraw-b20-v10';base='local-tum-quality-online-full-original-b10-v6'
state=B/'状态/online-position-full-v10.json'
assert json.loads((B/'状态/online-position-stress-v10.json').read_text())['stage']=='complete'
assert audit('local-tum-quality-online-original240-b10-v5','local-tum-quality-pos240-birth-raw-v10','development')['all_numeric_gates'] is True
assert audit('local-tum-quality-stress1200-original-b10-v10','local-tum-quality-stress1200-birthraw-b20-v10','development')['all_numeric_gates'] is True
old=json.loads((B/'协议/online-full-v6-frozen.json').read_text());assert all(sha256(B/f)==h for f,h in old['scripts'].items())
files=['online_position_full_batch.py','quality_tracking_positions.py','run_online_v10.py','online_quality_patch_v3.py','quality_growth.py','quality_tracking_covariance.py','quality_spacing.py','quality_losses.py','quality_losses_v2.py','quality_depth_range.py','quality_coverage.py','worker_seed.py','quality_core.py','evaluate_local_v2.py','common_depth_v2.py','visible_needle_effect_v2.py','describe_projected_needles.py','projection_diagnostic.py','report_online.py','quality_gate.py','build_matched_view_boards_v5.py']
pin={f:sha256(B/f) for f in files}
plan={'run':name,'scripts':pin,'frames':2253,'steps_per_frame':20,'input_fps':5.,'seed':0,'depth_weight':.05,'coverage_weight':.05,'needle_weight':.002,'growth_weight':0.,'growth_factor':8.,'tracking_covariance':'raw-gicp','tracking_positions':'birth','protocol_sha256':sha256(B/'协议/tum-office.json'),'base_map_sha256':sha256(E/'运行'/base/'scene.ply'),'scope':'Full TUM development; unchanged input/holdout/budget vs existing v6 controls. Birth tracking positions and raw GICP covariance, retaining upstream opacity/trackable/pruning. Estimated coordinates and upstream keyframe/overlap selection remain. Growth weight0 selected on development only. Single seeded asynchronous run, not isolated causal proof or final transfer freeze.'}
p=B/'协议/online-position-full-v10-frozen.json'
if p.exists():assert json.loads(p.read_text())==plan
else:atomic_json(p,plan)
def status(stage,**extra):atomic_json(state,dict(pid=os.getpid(),updated=time.time(),stage=stage,**extra))
def run(script,args,log):
 assert all(sha256(B/f)==h for f,h in pin.items())
 with (B/'日志'/log).open('a',buffering=1) as output:
  child=subprocess.Popen([sys.executable,str(B/script),*args],stdout=output,stderr=subprocess.STDOUT)
  try:
   while child.poll() is None:
    status('running',script=script,args=args,child_pid=child.pid,log=log);print('FULL_POSITION_CHILD',script,child.pid,flush=True);time.sleep(10)
  finally:
   if child.poll() is None:
    child.terminate()
    try:child.wait(timeout=10)
    except subprocess.TimeoutExpired:child.kill();child.wait()
  if child.returncode:status('failed',script=script,log=log,exit=child.returncode);raise RuntimeError(log)
r=E/'运行'/name
if r.exists():
 saved=json.loads((r/'state.json').read_text());assert saved['status']=='complete','Preserve incomplete run; use a new ID'
 assert all(sha256(r/f)==h for f,h in saved['artifacts'].items())
 q=json.loads((r/'manifest.json').read_text())['quality_args'];assert (q['frames'],q['steps_per_frame'],q['growth_weight'],q['depth_weight'],q['coverage_weight'],q['seed'],q['input_fps'])==(2253,20,0.,.05,.05,0,5.) and q['tracking_covariance']=='raw-gicp' and q['tracking_positions']=='birth'
else:run('run_online_v10.py',['--scene','tum-office','--frames','2253','--steps-per-frame','20','--input-fps','5','--variant','improved-shape','--depth-weight','.05','--coverage-weight','.05','--growth-weight','0','--tracking-covariance','raw-gicp','--tracking-positions','birth','--run-id',name],name+'.log')
for script,args,tag in [('evaluate_local_v2.py',[name],'eval'),('common_depth_v2.py',[base,name],'common-depth'),('visible_needle_effect_v2.py',[base,name],'native-views'),('describe_projected_needles.py',[base,name],'projection'),('quality_gate.py',[base,name],'gate'),('report_online.py',[name],'report')]:run(script,args,name+'-'+tag+'.log')
runs=[base,'local-tum-quality-online-full-original-b20-v6','local-tum-quality-online-full-coverage-b20-v6','local-tum-quality-online-full-growth-b20-v7','local-tum-quality-online-full-rawcov-b20-v8',name]
run('build_matched_view_boards_v5.py',['--base',base,'--runs',*runs,'--tag','online-full-position-v10'],'online-full-position-v10-boards.log')
status('complete',run=name,scope='Full stage completion only; numeric and all-view acceptance required before transfer.')
print('FULL_POSITION_V10_COMPLETE_PENDING_REVIEW',flush=True)
