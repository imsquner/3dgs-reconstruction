"""Serial native all-view audits and online CUDA smoke after fair refinement."""
import os,sys,time,json,subprocess
from pathlib import Path
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent
state=B/'状态/pruned-view-audit-batch.json';dep=B/'状态/pruned-refinement-batch.json'
base='local-tum-quality-full-base-v2'
names=[base,'local-tum-quality-pruned-original-10000-v5',
       'local-tum-quality-pruned-original-20000-v5','local-tum-quality-pruned-improved-20000-v5']
files=['describe_projected_needles.py','projection_diagnostic.py','visible_needle_effect.py',
       'run_online_v4.py','online_quality_patch.py','quality_spacing.py',
       'quality_losses.py','quality_losses_v2.py','quality_depth_range.py']
pin={f:sha256(B/f) for f in files}
atomic_json(B/'协议/pruned-view-audit-frozen.json',{'runs':names,'scripts':pin,
 'scope':'All nine fixed views, descriptors plus native sensitivity, not artifact truth. Online40 smoke proves insertion/pruning/loss execution only, not final quality.'})
def status(stage,**extra):atomic_json(state,{'pid':os.getpid(),'updated':time.time(),'stage':stage,**extra})
start=time.monotonic()
while True:
 d=json.loads(dep.read_text())
 if d['stage']=='complete':break
 if d['stage'] in ['failed','dependency_failed','wait_timeout']:status('dependency_failed',details=d);sys.exit(1)
 owner=Path('/proc')/str(d['pid'])/'cmdline'
 if not owner.exists() or b'pruned_refinement_batch.py' not in owner.read_bytes():
  status('dependency_owner_missing',details=d);sys.exit(1)
 if time.monotonic()-start>10800:status('wait_timeout');sys.exit(1)
 status('waiting_live_refinement',dependency_pid=d['pid']);print('AUDIT_WAIT_LIVE',d['pid'],round(time.monotonic()-start),flush=True);time.sleep(30)
def run(script,args,log):
 assert all(sha256(B/f)==v for f,v in pin.items()),'Pinned audit source changed'
 with (B/'日志'/log).open('a',buffering=1) as f:
  child=subprocess.Popen([sys.executable,str(B/script),*args],stdout=f,stderr=subprocess.STDOUT)
  while child.poll() is None:
   status('running',script=script,child_pid=child.pid,args=args,log=log)
   print('AUDIT_CHILD_LIVE',script,child.pid,flush=True);time.sleep(10)
  if child.returncode:
   status('failed',script=script,returncode=child.returncode,log=log);raise RuntimeError(log)
for name in names:
 run('describe_projected_needles.py',[base,name],name+'-projection-v5.log')
 run('visible_needle_effect.py',[base,name],name+'-visible-v5.log')
run('run_online_v4.py',['--scene','tum-office','--frames','40','--steps-per-frame','10',
                       '--variant','improved-shape','--run-id','local-tum-quality-online-shape40-v4'],
    'local-tum-quality-online-shape40-v4.log')
status('complete',runs=names);print('PRUNED_VIEW_AUDIT_AND_ONLINE_SMOKE_COMPLETE',flush=True)
