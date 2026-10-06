"""TUM-only mapping schedule diagnosis, with same-schedule budget controls."""
import json,os,subprocess,sys,time
from pathlib import Path
import numpy as np
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent;E=B.parents[1]
jobs=[(40,'original',10,'optimized','optimized','local-tum-quality-barrier40-original-b10-v12'),(40,'improved-shape',20,'birth','raw-gicp','local-tum-quality-barrier40-birthraw-b20-v12'),(80,'improved-shape',20,'birth','raw-gicp','local-tum-quality-barrier80-birthraw-b20-v12'),(240,'original',10,'optimized','optimized','local-tum-quality-barrier240-original-b10-v12'),(240,'original',20,'optimized','optimized','local-tum-quality-barrier240-original-b20-v12'),(240,'improved-shape',20,'birth','raw-gicp','local-tum-quality-barrier240-birthraw-b20-v12')]
files=['online_barrier_batch_v2.py','run_online_v12.py','quality_mapping_barrier_v2.py','quality_tracking_positions.py','quality_tracking_covariance.py','online_quality_patch_v3.py','quality_growth.py','quality_spacing.py','quality_losses.py','quality_losses_v2.py','quality_depth_range.py','quality_coverage.py','worker_seed.py','quality_core.py','evaluate_local_v2.py','common_depth_v2.py','visible_needle_effect_v2.py','quality_gate.py','report_online.py','build_matched_view_boards_v5.py','../../服务器/projection.py']
pin={f:sha256(B/f) for f in files}
plan=dict(jobs=jobs,scripts=pin,input_fps=5.,seed=0,mapping_schedule='observation-barrier',growth_weight=0.,depth_weight=.05,coverage_weight=.05,needle_weight=.002,protocol_sha256=sha256(B/'协议/tum-office.json'),prefix_position_max_tolerance_m=1e-4,prefix_rotation_max_tolerance_degrees=.01,scope='TUM development only. No future observation quota; each submitted frame waits for its exact budget and CUDA completion. Both original budget controls use same schedule. Old asynchronous results retained, not replaced. Slower processing/late delivery reported, no realtime speed claim. Prefix checks do not prove universal bitwise determinism or quality.')
p=B/'协议/online-barrier-v12-frozen.json'
if p.exists():assert json.loads(p.read_text())==plan
else:atomic_json(p,plan)
state=B/'状态/online-barrier-v12.json'
def status(stage,**extra):atomic_json(state,dict(pid=os.getpid(),updated=time.time(),stage=stage,**extra))
def run(script,args,log):
 assert all(sha256(B/f)==h for f,h in pin.items())
 with (B/'日志'/log).open('a',buffering=1) as out:
  child=subprocess.Popen([sys.executable,str(B/script),*args],stdout=out,stderr=subprocess.STDOUT)
  try:
   while child.poll() is None:
    status('running',script=script,args=args,child_pid=child.pid,log=log);print('BARRIER_CHILD',script,child.pid,flush=True);time.sleep(10)
  finally:
   if child.poll() is None:
    child.terminate()
    try:child.wait(timeout=10)
    except subprocess.TimeoutExpired:child.kill();child.wait()
  if child.returncode:status('failed',script=script,args=args,log=log,exit=child.returncode);raise RuntimeError(log)
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
base=jobs[3][5]
for frames,variant,budget,positions,cov,name in jobs:
 r=E/'运行'/name
 if r.exists():
  saved=json.loads((r/'state.json').read_text());assert saved['status']=='complete','Preserve incomplete run; unique ID required'
  assert all(sha256(r/f)==h for f,h in saved['artifacts'].items())
  q=json.loads((r/'manifest.json').read_text())['quality_args']
  assert (q['frames'],q['variant'],q['steps_per_frame'],q['mapping_schedule'],q['tracking_positions'],q['tracking_covariance'],q['seed'],q['input_fps'])==(frames,variant,budget,'observation-barrier',positions,cov,0,5.)
 else:run('run_online_v12.py',['--scene','tum-office','--frames',str(frames),'--variant',variant,'--steps-per-frame',str(budget),'--mapping-schedule','observation-barrier','--tracking-positions',positions,'--tracking-covariance',cov,'--growth-weight','0','--depth-weight','.05','--coverage-weight','.05','--input-fps','5','--seed','0','--run-id',name],name+'.log')
 verify_events(name,frames,budget)
 if frames==80:
  short=E/'运行'/jobs[1][5];x=np.array(json.loads((short/'final-poses.json').read_text()));y=np.array(json.loads((r/'final-poses.json').read_text()))[:40]
  dist=np.linalg.norm(x[:,:3,3]-y[:,:3,3],axis=1);rot=np.einsum('nij,njk->nik',x[:,:3,:3].transpose(0,2,1),y[:,:3,:3]);angles=np.rad2deg(np.arccos(np.clip((np.trace(rot,axis1=1,axis2=2)-1)/2,-1,1)))
  check=dict(position_max_m=float(dist.max()),position_rmse_m=float(np.sqrt(np.mean(dist**2))),rotation_max_degrees=float(angles.max()),position_tolerance_m=1e-4,rotation_tolerance_degrees=.01,scope='Same first40 observed frames, final short-frame forced keyframe may differ after pose estimate; maps are not asserted identical.')
  check['passed']=check['position_max_m']<=1e-4 and check['rotation_max_degrees']<=.01
  atomic_json(B/'验证/映射边界/40与80前缀一致性-v12.json',check)
  assert check['passed'],'Prefix instability remains; do not automatically proceed to larger cases'
 if frames==240:
  run('evaluate_local_v2.py',[name],name+'-eval.log')
  if name!=base:run('common_depth_v2.py',[base,name],name+'-common-depth.log')
  run('visible_needle_effect_v2.py',[base,name],name+'-native-views.log')
  if name!=base:run('quality_gate.py',[base,name],name+'-gate.log')
 run('report_online.py',[name],name+'-report.log')
 with (r/'实验记录.md').open('a') as f:f.write('\n映射时序诊断v11：每观测固定预算和CUDA完成边界；同schedule的原10/原20/候选20对照。5FPS文件输入可能大量迟到，不作重建5FPS声明。\n')
run('build_matched_view_boards_v5.py',['--base',base,'--runs',*[j[5] for j in jobs if j[0]==240],'--tag','online-barrier-v12'],'online-barrier-v12-boards.log')
status('complete',scope='Small-stage execution complete only; all-view quality review and larger TUM prefix stability/full acceptance remain.')
print('BARRIER_V12_COMPLETE_PENDING_REVIEW',flush=True)
