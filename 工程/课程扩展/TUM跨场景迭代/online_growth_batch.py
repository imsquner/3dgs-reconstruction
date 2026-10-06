"""TUM development ablation for birth-scale growth; no transfer retuning."""
import json,os,subprocess,sys,time
from pathlib import Path
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent;E=B.parents[1]
state=B/'状态/online-growth-v7.json'
jobs=[(40,.01,'local-tum-quality-growth40-v7'),(240,0.,'local-tum-quality-growth240-zero-v7'),(240,.002,'local-tum-quality-growth240-low-v7'),(240,.01,'local-tum-quality-growth240-high-v7')]
files=['run_online_v7.py','online_quality_patch_v3.py','quality_growth.py','worker_seed.py','quality_spacing.py','quality_losses.py','quality_losses_v2.py','quality_depth_range.py','quality_coverage.py','quality_core.py','evaluate_local_v2.py','common_depth_v2.py','visible_needle_effect_v2.py','report_online.py','quality_gate.py','build_matched_view_boards.py']
pin={f:sha256(B/f) for f in files}
plan={'jobs':jobs,'scripts':pin,'seed':0,'depth_weight':.05,'coverage_weight':.05,'needle_weight':.002,'growth_factor':8.,'protocol_sha256':sha256(B/'协议/tum-office.json'),'scope':'TUM development only, 40 CUDA smoke then matched 240 online ablation. No fewer-observation quality claim; short success cannot freeze transfer. As-fast replay, not real-time measurement. Original normal10/increased20 controls retained.'}
plan_path=B/'协议/online-growth-v7-frozen.json'
if plan_path.exists():assert json.loads(plan_path.read_text())==plan
else:atomic_json(plan_path,plan)
def status(stage,**extra):atomic_json(state,dict(pid=os.getpid(),updated=time.time(),stage=stage,**extra))
def run(script,args,log):
 assert all(sha256(B/f)==h for f,h in pin.items())
 with (B/'日志'/log).open('a',buffering=1) as output:
  child=subprocess.Popen([sys.executable,str(B/script),*args],stdout=output,stderr=subprocess.STDOUT)
  try:
   while child.poll() is None:
    status('running',script=script,args=args,child_pid=child.pid,log=log);print('GROWTH_CHILD',script,child.pid,flush=True);time.sleep(10)
  finally:
   if child.poll() is None:
    child.terminate()
    try:child.wait(timeout=10)
    except subprocess.TimeoutExpired:child.kill();child.wait()
  if child.returncode:status('failed',script=script,args=args,log=log,exit=child.returncode);raise RuntimeError(log)
base='local-tum-quality-online-original240-b10-v5'
for frames,weight,name in jobs:
 r=E/'运行'/name
 if r.exists():
  saved=json.loads((r/'state.json').read_text());assert saved['status']=='complete','Preserve interrupted run; new ID required'
  assert all(sha256(r/f)==h for f,h in saved['artifacts'].items())
  q=json.loads((r/'manifest.json').read_text())['quality_args'];assert (q['frames'],q['growth_weight'],q['depth_weight'],q['coverage_weight'],q['seed'],q['steps_per_frame'])==(frames,weight,.05,.05,0,20)
 else:run('run_online_v7.py',['--scene','tum-office','--frames',str(frames),'--steps-per-frame','20','--variant','improved-shape','--depth-weight','.05','--coverage-weight','.05','--growth-weight',str(weight),'--run-id',name],name+'.log')
 if frames==240:
  run('evaluate_local_v2.py',[name],name+'-eval.log')
  run('common_depth_v2.py',[base,name],name+'-common-depth.log')
  run('visible_needle_effect_v2.py',[base,name],name+'-native-views.log')
  run('quality_gate.py',[base,name],name+'-gate.log')
 run('report_online.py',[name],name+'-report.log')
run('build_matched_view_boards.py',['--base',base,'--runs',base,*[j[2] for j in jobs if j[0]==240],'--tag','online-growth-v7'],'online-growth-v7-boards.log')
status('complete',jobs=jobs);print('GROWTH_V7_SHORT_COMPLETE_FULL_DEVELOPMENT_STILL_REQUIRED',flush=True)

if __name__=='__main__':pass
