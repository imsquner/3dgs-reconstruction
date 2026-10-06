"""40/240-frame TUM tracking-position feedback test; final acceptance still needs full2253."""
import json,os,subprocess,sys,time
from pathlib import Path
from quality_core import atomic_json,sha256
from quality_gate import audit
B=Path(__file__).resolve().parent;E=B.parents[1]
assert json.loads((B/'状态/online-opacity-stress-v15.json').read_text())['stage']=='complete'
files=['online_position_feedback_batch.py','run_online_v16.py','quality_tracking_opacity_v2.py','quality_mapping_barrier_v2.py','quality_tracking_positions.py','quality_tracking_covariance.py','online_quality_patch_v3.py','quality_growth.py','quality_spacing.py','quality_losses.py','quality_losses_v2.py','quality_depth_range.py','quality_coverage.py','worker_seed.py','quality_core.py','evaluate_local_v2.py','common_depth_v2.py','visible_needle_effect_v2.py','describe_projected_needles.py','quality_gate.py','report_online.py','build_matched_view_boards_v6.py','../../服务器/projection.py']
pin={n:sha256(B/n) for n in files}
jobs=[(40,'improved-shape',20,'optimized','raw-gicp','birth','local-tum-quality-feedback40-v16'),(240,'original',10,'optimized','optimized','learned','local-tum-quality-feedback240-original-b10-v16'),(240,'original',20,'optimized','optimized','learned','local-tum-quality-feedback240-original-b20-v16'),(240,'improved-shape',20,'optimized','raw-gicp','birth','local-tum-quality-feedback240-optimizedxyz-b20-v16')]
plan=dict(jobs=jobs,frames=[40,240],seed=0,input_fps=5.,growth_weight=0.,depth_weight=.05,coverage_weight=.05,needle_weight=.002,scripts=pin,protocol_sha256=sha256(B/'协议/tum-office.json'),mapping_schedule='observation-barrier',tracking_positions='optimized',opacity_sources=['learned','birth'],scope='TUM development40 GPU smoke and same240 inputs/budget controls. Test optimized tracking XYZ with raw covariance and birth opacity, preserving original render pruning. All three240 controls use runner16, no full/transfer acceptance, no5FPS reconstruction claim.')
p=B/'协议/online-position-feedback-v16-frozen.json'
if p.exists():assert json.loads(p.read_text())==plan
else:atomic_json(p,plan)
state=B/'状态/online-position-feedback-v16.json'
def status(stage,**kw):atomic_json(state,dict(pid=os.getpid(),updated=time.time(),stage=stage,**kw))
def run(script,args,log):
 assert all(sha256(B/n)==h for n,h in pin.items())
 with (B/'日志'/log).open('a',buffering=1) as output:
  child=subprocess.Popen([sys.executable,str(B/script),*args],stdout=output,stderr=subprocess.STDOUT)
  try:
   while child.poll() is None:
    status('running',script=script,args=args,child_pid=child.pid,log=log)
    print('POSITION_FEEDBACK_CHILD',script,child.pid,flush=True);time.sleep(10)
  finally:
   if child.poll() is None:
    child.terminate()
    try:child.wait(timeout=10)
    except subprocess.TimeoutExpired:child.kill();child.wait()
  if child.returncode:
   status('failed',script=script,args=args,log=log,exit=child.returncode);raise RuntimeError(log)
def verify_events(name,frames,budget):
 r=E/'运行'/name
 tracking=[json.loads(x) for x in (r/'tracking-timing.jsonl').read_text().splitlines()]
 mapping=[json.loads(x) for x in (r/'mapping-timing.jsonl').read_text().splitlines()]
 assert len(tracking)==len(mapping)==frames
 for i,(t,m) in enumerate(zip(tracking,mapping)):
  expected=(i+1)*budget
  assert t['frame']==i and t['mapping_completed_steps']==expected
  assert m['mapping_iteration']==expected and m['submitted_observations']==i+1 and m['latest_tracking_frame']==i
  assert t['completion_monotonic']>=m['completion_monotonic']
 atomic_json(B/'验证/映射边界'/f'{name}.json',dict(frames=frames,budget=budget,tracking_timing_sha256=sha256(r/'tracking-timing.jsonl'),mapping_timing_sha256=sha256(r/'mapping-timing.jsonl'),verified=True,scope='Actual ordered per-observation submitted budget, CUDA-completion event then tracker release. Not guaranteed each non-keyframe inserted.'))
base=jobs[1][6]
for frames,variant,budget,positions,covariance,opacity,name in jobs:
 r=E/'运行'/name
 if r.exists():
  saved=json.loads((r/'state.json').read_text());assert saved['status']=='complete','Preserve interrupted run; new ID required'
  assert all(sha256(r/f)==h for f,h in saved['artifacts'].items())
  q=json.loads((r/'manifest.json').read_text())['quality_args']
  assert (q['frames'],q['variant'],q['steps_per_frame'],q['tracking_positions'],q['tracking_covariance'],q['seed'],q['input_fps'],q['growth_weight'],q['depth_weight'],q['coverage_weight'],q['tracking_opacity'],q['mapping_schedule'])==(frames,variant,budget,positions,covariance,0,5.,0.,.05,.05,opacity,'observation-barrier')
 else:
  run('run_online_v16.py',['--scene','tum-office','--frames',str(frames),'--steps-per-frame',str(budget),'--variant',variant,'--tracking-positions',positions,'--tracking-covariance',covariance,'--tracking-opacity',opacity,'--mapping-schedule','observation-barrier','--growth-weight','0','--depth-weight','.05','--coverage-weight','.05','--input-fps','5','--seed','0','--run-id',name],name+'.log')
 verify_events(name,frames,budget)
 if frames==240:
  run('evaluate_local_v2.py',[name],name+'-eval.log')
  if name!=base:run('common_depth_v2.py',[base,name],name+'-common-depth.log')
  run('visible_needle_effect_v2.py',[base,name],name+'-native-views.log')
  run('describe_projected_needles.py',[base,name],name+'-projection.log')
  if name!=base:run('quality_gate.py',[base,name],name+'-gate.log')
 run('report_online.py',[name],name+'-report.log')
 with (r/'实验记录.md').open('a') as f:f.write('\n40/240位置反馈消融，最终仍须完整2253。tracking XYZ='+positions+'，cov='+covariance+'；跟踪opacity='+opacity+'，growth0、原渲染opacity/prune保留，每观测预算边界。5FPS输入不等于每帧map-ready。\n')
run('build_matched_view_boards_v6.py',['--base',base,'--runs',*[j[6] for j in jobs if j[0]==240],'--tag','online-position-feedback-v16'],'online-position-feedback-v16-boards.log')
status('complete',jobs=jobs,scope='Short development completed only; numeric/all9 review precedes1200, full2253 and eventual transfer freeze.')
print('POSITION_FEEDBACK_COMPLETE_PENDING_REVIEW',flush=True)
