"""Wait for serial training batch, then compute all fixed-view descriptors."""
import os,sys,json,time,subprocess
from pathlib import Path
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent;state=B/'状态/fixed-view-audit-batch.json';owner=B/'状态/full-refinement-batch.json';plan=json.loads((B/'协议/full-refinement-frozen.json').read_text());names=[plan['base']]+[j[2] for j in plan['jobs']]
pin={name:sha256(B/name) for name in ['visible_needle_effect.py','describe_projected_needles.py','projection_diagnostic.py']};atomic_json(B/'协议/fixed-view-audit-frozen.json',{'runs':names,'scripts':pin,'scope':'All existing 9 fixed views, no view selection. Screen footprint upper bound and native sensitivity, neither equals artifact truth.'})
def status(stage,**extra):atomic_json(state,{'pid':os.getpid(),'updated':time.time(),'stage':stage,**extra})
start=time.monotonic()
while True:
 s=json.loads(owner.read_text())
 if s['stage']=='complete':break
 if s['stage'] in ['failed','wait_timeout']:status('dependency_failed',details=s);sys.exit(1)
 if time.monotonic()-start>10800:status('wait_timeout');sys.exit(1)
 status('waiting_full_batch',dependency=s);print('AUDIT_WAIT_FULL_BATCH',round(time.monotonic()-start),flush=True);time.sleep(30)
for name in names:
 for script in ['describe_projected_needles.py','visible_needle_effect.py']:
  assert all(sha256(B/f)==v for f,v in pin.items()),'Audit script changed while queued'
  log=B/'日志'/f'{name}-{script}.log'
  with log.open('a',buffering=1) as f:
   child=subprocess.Popen([sys.executable,str(B/script),plan['base'],name],stdout=f,stderr=subprocess.STDOUT)
   while child.poll() is None:
    status('running',run=name,script=script,child_pid=child.pid,log=str(log));print('AUDIT_CHILD_LIVE',name,script,child.pid,flush=True);time.sleep(5)
   if child.returncode:status('failed',run=name,script=script,returncode=child.returncode);sys.exit(1)
status('complete',runs=names);print('FIXED_VIEW_AUDIT_COMPLETE',flush=True)
