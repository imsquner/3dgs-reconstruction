"""1200-frame TUM development stress; final acceptance still needs full2253."""
import json,os,subprocess,sys,time
from pathlib import Path
from quality_core import atomic_json,sha256
from quality_gate import audit
B=Path(__file__).resolve().parent;E=B.parents[1]
assert json.loads((B/'状态/online-position-v10.json').read_text())['stage']=='complete'
short='local-tum-quality-pos240-birth-raw-v10'
assert audit('local-tum-quality-online-original240-b10-v5',short,'development')['all_numeric_gates'] is True
files=['online_position_stress_batch.py','run_online_v10.py','quality_tracking_positions.py','quality_tracking_covariance.py','online_quality_patch_v3.py','quality_growth.py','quality_spacing.py','quality_losses.py','quality_losses_v2.py','quality_depth_range.py','quality_coverage.py','worker_seed.py','quality_core.py','evaluate_local_v2.py','common_depth_v2.py','visible_needle_effect_v2.py','describe_projected_needles.py','quality_gate.py','report_online.py','build_matched_view_boards_v5.py']
pin={n:sha256(B/n) for n in files}
jobs=[('original',10,'optimized','optimized','local-tum-quality-stress1200-original-b10-v10'),('original',20,'optimized','optimized','local-tum-quality-stress1200-original-b20-v10'),('improved-shape',20,'birth','raw-gicp','local-tum-quality-stress1200-birthraw-b20-v10')]
plan=dict(jobs=jobs,frames=1200,seed=0,input_fps=5.,growth_weight=0.,depth_weight=.05,coverage_weight=.05,needle_weight=.002,scripts=pin,protocol_sha256=sha256(B/'协议/tum-office.json'),short_map_sha256=sha256(E/'运行'/short/'scene.ply'),scope='Development stress only. Same1200 observed rows/heldout IDs/normal and increased budget; no transfer data or final2253 quality claim. Original opacity/trackable/pruning retained.')
p=B/'协议/online-position-stress-v10-frozen.json'
if p.exists():assert json.loads(p.read_text())==plan
else:atomic_json(p,plan)
state=B/'状态/online-position-stress-v10.json'
def status(stage,**kw):atomic_json(state,dict(pid=os.getpid(),updated=time.time(),stage=stage,**kw))
def run(script,args,log):
 assert all(sha256(B/n)==h for n,h in pin.items())
 with (B/'日志'/log).open('a',buffering=1) as output:
  child=subprocess.Popen([sys.executable,str(B/script),*args],stdout=output,stderr=subprocess.STDOUT)
  try:
   while child.poll() is None:
    status('running',script=script,args=args,child_pid=child.pid,log=log)
    print('POSITION_STRESS_CHILD',script,child.pid,flush=True);time.sleep(10)
  finally:
   if child.poll() is None:
    child.terminate()
    try:child.wait(timeout=10)
    except subprocess.TimeoutExpired:child.kill();child.wait()
  if child.returncode:
   status('failed',script=script,args=args,log=log,exit=child.returncode);raise RuntimeError(log)
base=jobs[0][4]
for variant,budget,positions,covariance,name in jobs:
 r=E/'运行'/name
 if r.exists():
  saved=json.loads((r/'state.json').read_text());assert saved['status']=='complete','Preserve interrupted run; new ID required'
  assert all(sha256(r/f)==h for f,h in saved['artifacts'].items())
  q=json.loads((r/'manifest.json').read_text())['quality_args']
  assert (q['frames'],q['variant'],q['steps_per_frame'],q['tracking_positions'],q['tracking_covariance'],q['seed'],q['input_fps'],q['growth_weight'],q['depth_weight'],q['coverage_weight'])==(1200,variant,budget,positions,covariance,0,5.,0.,.05,.05)
 else:
  run('run_online_v10.py',['--scene','tum-office','--frames','1200','--steps-per-frame',str(budget),'--variant',variant,'--tracking-positions',positions,'--tracking-covariance',covariance,'--growth-weight','0','--depth-weight','.05','--coverage-weight','.05','--input-fps','5','--seed','0','--run-id',name],name+'.log')
 run('evaluate_local_v2.py',[name],name+'-eval.log')
 if name!=base:run('common_depth_v2.py',[base,name],name+'-common-depth.log')
 run('visible_needle_effect_v2.py',[base,name],name+'-native-views.log')
 run('describe_projected_needles.py',[base,name],name+'-projection.log')
 if name!=base:run('quality_gate.py',[base,name],name+'-gate.log')
 run('report_online.py',[name],name+'-report.log')
 with (r/'实验记录.md').open('a') as f:f.write('\n1200开发压力检查，最终仍须2253完整。tracking XYZ='+positions+'，cov='+covariance+'；growth0、原opacity/prune保留。5FPS输入不等于每帧map-ready。\n')
run('build_matched_view_boards_v5.py',['--base',base,'--runs',*[j[4] for j in jobs],'--tag','online-position-stress-v10'],'online-position-stress-v10-boards.log')
status('complete',jobs=jobs,scope='All1200 development stages complete only; numeric/all9/trajectory review precedes full2253 run and eventual transfer freeze.')
print('POSITION_STRESS_COMPLETE_PENDING_REVIEW',flush=True)
