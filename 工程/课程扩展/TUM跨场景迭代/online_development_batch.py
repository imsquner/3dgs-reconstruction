"""Seeded online smoke and matched-budget TUM development; one GPU child."""
import os,sys,time,json,subprocess
from pathlib import Path
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent;E=B.parents[1];state=B/'状态/online-development-v5.json'
assert json.loads((B/'状态/pruned-view-audit-batch.json').read_text())['stage']=='complete'
jobs=[('original',40,10,'local-tum-quality-online-original40-v5'),
      ('improved-shape',40,10,'local-tum-quality-online-shape40-v5'),
      ('original',240,10,'local-tum-quality-online-original240-b10-v5'),
      ('original',240,20,'local-tum-quality-online-original240-b20-v5'),
      ('improved-shape',240,20,'local-tum-quality-online-shape240-b20-v5')]
files=['run_online_v5.py','worker_seed.py','online_quality_patch.py','quality_spacing.py',
       'quality_losses.py','quality_losses_v2.py','quality_depth_range.py','evaluate_local_v2.py','common_depth_v2.py']
pin={f:sha256(B/f) for f in files}
atomic_json(B/'协议/online-development-v5-frozen.json',{'jobs':jobs,'scripts':pin,'seed':0,
 'scope':'TUM development only, full fixed selected observation prefix, explicit spawn worker seed, original10/original20/candidate20 per-frame mapping budget. Same upstream insertion/pruning. Asynchronous execution is not bitwise deterministic. Not final transfer freeze.'})
def status(stage,**extra):atomic_json(state,{'pid':os.getpid(),'updated':time.time(),'stage':stage,**extra})
def run(script,args,log):
 assert all(sha256(B/f)==v for f,v in pin.items()),'Pinned development source changed'
 with (B/'日志'/log).open('a',buffering=1) as f:
  child=subprocess.Popen([sys.executable,str(B/script),*args],stdout=f,stderr=subprocess.STDOUT)
  while child.poll() is None:
   status('running',script=script,child_pid=child.pid,args=args,log=log);print('ONLINE_DEVELOPMENT_CHILD',script,child.pid,flush=True);time.sleep(10)
  if child.returncode:status('failed',script=script,returncode=child.returncode,log=log);raise RuntimeError(log)
for variant,frames,budget,name in jobs:
 R=E/'运行'/name
 if R.exists():
  saved=json.loads((R/'state.json').read_text());assert saved['status']=='complete','Interrupted online run cannot resume from PLY; preserve and use a new run ID'
  assert all(sha256(R/f)==h for f,h in saved['artifacts'].items()),'Completed artifact mismatch'
  args=json.loads((R/'manifest.json').read_text())['quality_args']
  assert (args['variant'],args['frames'],args['steps_per_frame'],args['seed'])==(variant,frames,budget,0)
  print('VERIFIED_COMPLETE_ONLINE_REUSED',name,flush=True)
 else:
  run('run_online_v5.py',['--scene','tum-office','--frames',str(frames),'--steps-per-frame',str(budget),
                        '--variant',variant,'--run-id',name],name+'.log')
 if frames==240:
  run('evaluate_local_v2.py',[name],name+'-eval.log')
  if variant=='improved-shape':run('common_depth_v2.py',['local-tum-quality-online-original240-b10-v5',name],name+'-common-depth.log')
status('complete',jobs=jobs);print('ONLINE_DEVELOPMENT_V5_COMPLETE',flush=True)
