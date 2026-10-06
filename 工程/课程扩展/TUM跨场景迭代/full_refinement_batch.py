"""Serial local continuation after complete full-map evaluation."""
import json,time,subprocess,os,sys
from pathlib import Path
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent;E=B.parents[1];base='local-tum-quality-full-base-v2';R=E/'运行'/base;state=B/'状态/full-refinement-batch.json'
jobs=[('original',10000,'local-tum-quality-full-original-10000-v3'),('original',20000,'local-tum-quality-full-original-20000-v3'),('improved-shape',20000,'local-tum-quality-full-improved-shape-20000-v3')]
plan={'base':base,'jobs':jobs,'runner':sha256(B/'refine_local.py'),'losses':sha256(B/'quality_losses.py'),'sparse_losses':sha256(B/'quality_losses_v2.py'),'evaluation':sha256(B/'evaluate_local.py'),'geometry_evaluation':sha256(B/'common_depth.py'),'scope':'Fixed budget before full metrics. Offline, original topology retained, 8-image LRU. Failed stage stops batch; exact offline resume supported.'}
atomic_json(B/'协议/full-refinement-frozen.json',plan)
def status(stage,**extra):atomic_json(state,{'pid':os.getpid(),'updated':time.time(),'stage':stage,**extra})
start=time.monotonic()
while True:
 if (R/'state.json').exists():
  s=json.loads((R/'state.json').read_text())
  if s['status']=='failed':status('failed',error=s);raise RuntimeError('Online baseline failed')
  if s['status']=='complete' and (R/'评价/metrics.json').exists():
   m=json.loads((R/'评价/metrics.json').read_text());assert m['signature']['map']==sha256(R/'scene.ply');break
 if time.monotonic()-start>1800:status('wait_timeout');raise RuntimeError('Baseline/evaluation not complete after 30 minutes; inspect before retry')
 status('waiting_baseline');print('BATCH_WAIT_BASELINE',round(time.monotonic()-start),flush=True);time.sleep(15)
def run(script,args,log):
 assert sha256(B/'refine_local.py')==plan['runner'],'Runner changed while queued'
 with (B/'日志'/log).open('a',buffering=1) as f:
  child=subprocess.Popen([sys.executable,str(B/script),*args],stdout=f,stderr=subprocess.STDOUT,env=os.environ)
  while child.poll() is None:
   status('running',script=script,child_pid=child.pid,args=args,log=log);print('BATCH_CHILD_LIVE',script,child.pid,log,flush=True);time.sleep(15)
  if child.returncode:status('failed',script=script,returncode=child.returncode,log=log);raise RuntimeError('Child failure '+log)
for variant,steps,name in jobs:
 run('refine_local.py',['--base',base,'--run',name,'--variant',variant,'--steps',str(steps)],name+'.log')
 run('evaluate_local.py',[name],name+'-eval.log')
 run('common_depth.py',[base,name],name+'-common-depth.log')
 status('job_complete',run=name)
status('complete',jobs=jobs);print('FULL_BATCH_COMPLETE',flush=True)
