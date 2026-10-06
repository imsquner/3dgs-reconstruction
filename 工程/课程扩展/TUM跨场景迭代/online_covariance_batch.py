"""TUM covariance-source ablation; no transfer data used for selection."""
import json,os,subprocess,sys,time
from pathlib import Path
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent;E=B.parents[1];state=B/'状态/online-covariance-v8.json'
jobs=[(40,'birth-render','local-tum-quality-cov40-birth-v8'),(40,'raw-gicp','local-tum-quality-cov40-raw-v8'),(240,'optimized','local-tum-quality-cov240-optimized-v8'),(240,'birth-render','local-tum-quality-cov240-birth-v8'),(240,'raw-gicp','local-tum-quality-cov240-raw-v8')]
files=['run_online_v8.py','quality_tracking_covariance.py','online_quality_patch_v3.py','quality_growth.py','worker_seed.py','quality_spacing.py','quality_losses.py','quality_losses_v2.py','quality_depth_range.py','quality_coverage.py','quality_core.py','evaluate_local_v2.py','common_depth_v2.py','visible_needle_effect_v2.py','report_online.py','quality_gate.py','build_matched_view_boards_v3.py']
pin={f:sha256(B/f) for f in files};plan={'jobs':jobs,'scripts':pin,'seed':0,'steps_per_frame':20,'depth_weight':.05,'coverage_weight':.05,'needle_weight':.002,'growth_weight':.01,'growth_factor':8.,'protocol_sha256':sha256(B/'协议/tum-office.json'),'scope':'TUM development: covariance optimized/birth-render/raw-GICP, means/opacity/trackable filtering/pruning unchanged. No ground truth feed except initial pose. Short as-fast replay, no real-time claim. Single asynchronous exploration, not transfer freeze.'}
p=B/'协议/online-covariance-v8-frozen.json'
if p.exists():assert json.loads(p.read_text())==plan
else:atomic_json(p,plan)
def status(stage,**extra):atomic_json(state,dict(pid=os.getpid(),updated=time.time(),stage=stage,**extra))
def run(script,args,log):
 assert all(sha256(B/f)==h for f,h in pin.items())
 with (B/'日志'/log).open('a',buffering=1) as output:
  child=subprocess.Popen([sys.executable,str(B/script),*args],stdout=output,stderr=subprocess.STDOUT)
  try:
   while child.poll() is None:
    status('running',script=script,args=args,child_pid=child.pid,log=log);print('COVARIANCE_CHILD',script,child.pid,flush=True);time.sleep(10)
  finally:
   if child.poll() is None:
    child.terminate()
    try:child.wait(timeout=10)
    except subprocess.TimeoutExpired:child.kill();child.wait()
  if child.returncode:status('failed',script=script,args=args,log=log,exit=child.returncode);raise RuntimeError(log)
base='local-tum-quality-online-original240-b10-v5'
for frames,mode,name in jobs:
 r=E/'运行'/name
 if r.exists():
  saved=json.loads((r/'state.json').read_text());assert saved['status']=='complete','Preserve interrupted run; new ID required'
  assert all(sha256(r/f)==h for f,h in saved['artifacts'].items())
  q=json.loads((r/'manifest.json').read_text())['quality_args'];assert (q['frames'],q['tracking_covariance'],q['growth_weight'],q['seed'],q['steps_per_frame'])==(frames,mode,.01,0,20)
 else:run('run_online_v8.py',['--scene','tum-office','--frames',str(frames),'--steps-per-frame','20','--variant','improved-shape','--depth-weight','.05','--coverage-weight','.05','--growth-weight','.01','--tracking-covariance',mode,'--run-id',name],name+'.log')
 if frames==240:
  run('evaluate_local_v2.py',[name],name+'-eval.log')
  run('common_depth_v2.py',[base,name],name+'-common-depth.log')
  run('visible_needle_effect_v2.py',[base,name],name+'-native-views.log')
  run('quality_gate.py',[base,name],name+'-gate.log')
 run('report_online.py',[name],name+'-report.log')
 with (r/'实验记录.md').open('a') as f:f.write('\n跟踪协方差来源='+mode+'，depth .05/coverage .05/needle .002/growth .01/factor8。仅rotation/scales来源改变，XYZ/opacity/trackable mask/pruning保持上游；不是完整解耦地图，参考未馈入跟踪（除首姿态）。\n')
run('build_matched_view_boards_v3.py',['--base',base,'--runs',base,*[j[2] for j in jobs if j[0]==240],'--tag','online-covariance-v8'],'online-covariance-v8-boards.log')
status('complete',jobs=jobs);print('COVARIANCE_V8_SHORT_COMPLETE_PENDING_FULL_DEVELOPMENT',flush=True)
