"""Fair offline loss comparison retaining the same upstream pruning policy."""
import os,sys,time,json,subprocess
from pathlib import Path
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent;state=B/'状态/pruned-refinement-batch.json';dep=B/'状态/fixed-view-audit-batch.json';base='local-tum-quality-full-base-v2'
jobs=[('original',10000,'local-tum-quality-pruned-original-10000-v5'),('original',20000,'local-tum-quality-pruned-original-20000-v5'),('improved-shape',20000,'local-tum-quality-pruned-improved-20000-v5')]
scripts=['refine_local_v5.py','quality_losses.py','quality_losses_v2.py','quality_depth_range.py','upstream_prune.py','evaluate_local_v2.py','common_depth_v2.py'];pin={f:sha256(B/f) for f in scripts}
atomic_json(B/'协议/pruned-refinement-frozen.json',{'base':base,'jobs':jobs,'scripts':pin,'scope':'Same upstream pruning both groups, same training observations/estimated poses/iteration counts; second render costs reported. Offline stage, online constraint stage still required.'})
def status(stage,**extra):atomic_json(state,{'pid':os.getpid(),'updated':time.time(),'stage':stage,**extra})
start=time.monotonic()
while True:
 d=json.loads(dep.read_text())
 if d['stage']=='complete':break
 if d['stage']=='superseded_invalid_unpruned_dependency':
  prior=json.loads((B/'状态/full-refinement-batch.json').read_text())
  if prior['stage']=='failed' and (B.parents[1]/'运行/local-tum-quality-full-original-20000-v3/stop-reason.json').exists():break
 if d['stage'] in ['failed','dependency_failed','wait_timeout']:status('dependency_failed',details=d);sys.exit(1)
 if time.monotonic()-start>21600:status('wait_timeout');sys.exit(1)
 status('waiting_fixed_audit');print('PRUNED_BATCH_WAIT',round(time.monotonic()-start),flush=True);time.sleep(30)
def run(script,args,log):
 assert all(sha256(B/f)==v for f,v in pin.items()),'Pinned source changed'
 with (B/'日志'/log).open('a',buffering=1) as f:
  child=subprocess.Popen([sys.executable,str(B/script),*args],stdout=f,stderr=subprocess.STDOUT)
  while child.poll() is None:
   status('running',script=script,child_pid=child.pid,args=args,log=log);print('PRUNED_CHILD_LIVE',script,child.pid,flush=True);time.sleep(10)
  if child.returncode:status('failed',script=script,log=log,returncode=child.returncode);raise RuntimeError('Stage failed '+log)
# The first iteration exercises upstream pruning, then checkpoint restore after five steps.
smoke='local-tum-quality-pruned-resume10-v5'
run('refine_local_v5.py',['--base','local-tum-quality-smoke40-v1','--run',smoke,'--variant','improved-shape','--steps','10','--stop-after','5'],'pruned-resume10-first.log')
run('refine_local_v5.py',['--base','local-tum-quality-smoke40-v1','--run',smoke,'--variant','improved-shape','--steps','10'],'pruned-resume10-restored.log')
for variant,steps,name in jobs:
 run('refine_local_v5.py',['--base',base,'--run',name,'--variant',variant,'--steps',str(steps)],name+'.log')
 run('evaluate_local_v2.py',[name],name+'-eval.log')
 run('common_depth_v2.py',[base,name],name+'-common-depth.log')
status('complete',jobs=jobs);print('PRUNED_BATCH_COMPLETE',flush=True)
