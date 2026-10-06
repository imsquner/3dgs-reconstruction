"""Seeded online smoke and matched-budget TUM development; one GPU child."""
import os,sys,time,json,subprocess
from pathlib import Path
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent;E=B.parents[1];state=B/'状态/online-geometry-v6.json'
assert json.loads((B/'状态/online-development-v5.json').read_text())['stage']=='complete'
jobs=[('improved-shape',40,10,.05,.05,'local-tum-quality-online-coverage40-v6'),
      ('improved-shape',240,20,.05,0.,'local-tum-quality-online-depth240-v6'),
      ('improved-shape',240,20,.05,.05,'local-tum-quality-online-coverage240-v6')]
files=['run_online_v6.py','worker_seed.py','online_quality_patch_v2.py','quality_spacing.py',
       'quality_losses.py','quality_losses_v2.py','quality_depth_range.py','evaluate_local_v2.py','common_depth_v2.py','quality_coverage.py','visible_needle_effect_v2.py','report_online.py','quality_core.py']
pin={f:sha256(B/f) for f in files}
atomic_json(B/'协议/online-geometry-v6-frozen.json',{'jobs':jobs,'scripts':pin,'seed':0,
 'scope':'TUM development only. Prior online v5 candidate failed coverage/common MAE despite RGB gain. V6 fixed depth weight .05, coverage ablation0/.05, target alpha .99 on valid training depth only. Same heldout evaluator/observations and budget20; original controls v5 retained. Explicit spawn seeds, no bitwise determinism claim. No transfer tuning or final freeze.'})
def status(stage,**extra):atomic_json(state,{'pid':os.getpid(),'updated':time.time(),'stage':stage,**extra})
def run(script,args,log):
 assert all(sha256(B/f)==v for f,v in pin.items()),'Pinned development source changed'
 with (B/'日志'/log).open('a',buffering=1) as f:
  child=subprocess.Popen([sys.executable,str(B/script),*args],stdout=f,stderr=subprocess.STDOUT)
  try:
   while child.poll() is None:
    status('running',script=script,child_pid=child.pid,args=args,log=log);print('ONLINE_DEVELOPMENT_CHILD',script,child.pid,flush=True);time.sleep(10)
  finally:
   if child.poll() is None:
    child.terminate()
    try:child.wait(timeout=10)
    except subprocess.TimeoutExpired:child.kill();child.wait()
  if child.returncode:status('failed',script=script,returncode=child.returncode,log=log);raise RuntimeError(log)
for variant,frames,budget,dw,cw,name in jobs:
 R=E/'运行'/name
 if R.exists():
  saved=json.loads((R/'state.json').read_text());assert saved['status']=='complete','Interrupted online run cannot resume from PLY; preserve and use a new run ID'
  assert all(sha256(R/f)==h for f,h in saved['artifacts'].items()),'Completed artifact mismatch'
  args=json.loads((R/'manifest.json').read_text())['quality_args']
  assert (args['variant'],args['frames'],args['steps_per_frame'],args['seed'],args['depth_weight'],args['coverage_weight'])==(variant,frames,budget,0,dw,cw)
  print('VERIFIED_COMPLETE_ONLINE_REUSED',name,flush=True)
 else:
  run('run_online_v6.py',['--scene','tum-office','--frames',str(frames),'--steps-per-frame',str(budget),
                        '--variant',variant,'--depth-weight',str(dw),'--coverage-weight',str(cw),'--run-id',name],name+'.log')
 if frames==240:
  run('evaluate_local_v2.py',[name],name+'-eval.log')
  run('common_depth_v2.py',['local-tum-quality-online-original240-b10-v5',name],name+'-common-depth.log')
  run('visible_needle_effect_v2.py',['local-tum-quality-online-original240-b10-v5',name],name+'-native-views.log')
for name in ['local-tum-quality-online-original240-b10-v5','local-tum-quality-online-original240-b20-v5']:
 run('visible_needle_effect_v2.py',['local-tum-quality-online-original240-b10-v5',name],name+'-native-views.log')
for variant,frames,budget,dw,cw,name in jobs:
 run('report_online.py',[name],name+'-report.log')
status('complete',jobs=jobs);print('ONLINE_GEOMETRY_V6_COMPLETE',flush=True)
