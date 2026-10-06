"""Full TUM online three-budget development after short numeric/visual audit."""
import os,sys,time,json,subprocess
from pathlib import Path
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent;E=B.parents[1];state=B/'状态/online-full-v6.json'
dep=B/'状态/online-geometry-v6.json'
base='local-tum-quality-online-full-original-b10-v6'
jobs=[('original',10,.01,0.,base),('original',20,.01,0.,'local-tum-quality-online-full-original-b20-v6'),
      ('improved-shape',20,.05,.05,'local-tum-quality-online-full-coverage-b20-v6')]
files=['run_online_v6.py','worker_seed.py','online_quality_patch_v2.py','quality_spacing.py',
       'quality_losses.py','quality_losses_v2.py','quality_depth_range.py','quality_coverage.py','quality_core.py',
       'evaluate_local_v2.py','common_depth_v2.py','visible_needle_effect_v2.py','projection_diagnostic.py',
       'describe_projected_needles.py','report_online.py','build_matched_view_boards.py']
pin={f:sha256(B/f) for f in files}
protocol=json.loads((B/'协议/tum-office.json').read_text());frames=len(protocol['upstream_original_train']);assert frames==2253
atomic_json(B/'协议/online-full-v6-frozen.json',{'jobs':jobs,'scripts':pin,'frames':frames,'seed':0,'input_fps':5.,
 'protocol_sha256':sha256(B/'协议/tum-office.json'),'observations_manifest_sha256':sha256(B/'协议/tum-office-observations.json'),
 'scope':'Full TUM development only, all original training observations processed; original10/original20/candidate20 matched-input budgets. Candidate depth .05/coverage .05/needle .002 from short ablation; valid training alpha target .99, evaluator alpha .95 unchanged. Same upstream pruning. Single seed exploratory, async not bitwise deterministic. Not final transfer parameter freeze.'})
def status(stage,**extra):atomic_json(state,{'pid':os.getpid(),'updated':time.time(),'stage':stage,**extra})
start=time.monotonic()
while True:
 d=json.loads(dep.read_text())
 if d['stage']=='complete':break
 if d['stage'] in ['failed','dependency_failed']:status('dependency_failed',details=d);sys.exit(1)
 owner=Path('/proc')/str(d['pid'])/'cmdline'
 if not owner.exists() or b'online_geometry_batch.py' not in owner.read_bytes():status('dependency_owner_missing',details=d);sys.exit(1)
 if time.monotonic()-start>10800:status('wait_timeout');sys.exit(1)
 status('waiting_live_geometry',dependency_pid=d['pid']);print('FULL_WAIT_LIVE_GEOMETRY',d['pid'],flush=True);time.sleep(20)
# Inspect actual short results and map hashes; a status label is not acceptance evidence.
short=E/'运行/local-tum-quality-online-coverage240-v6';control=E/'运行/local-tum-quality-online-original240-b10-v5'
c=json.loads((short/'评价/metrics.json').read_text());r=json.loads((control/'评价/metrics.json').read_text());common=json.loads((short/'评价/common-depth.json').read_text())
assert c['signature']['map']==sha256(short/'scene.ply') and r['signature']['map']==sha256(control/'scene.ply')
assert [x['source_frame'] for x in c['rows']]==[x['source_frame'] for x in r['rows']]
cm,rm=c['means'],r['means'];assert cm['psnr_db']-rm['psnr_db']>=.5 or cm['ssim']-rm['ssim']>=.01
assert cm['psnr_db']>=rm['psnr_db'] and cm['ssim']>=rm['ssim'];assert cm['coverage']>=rm['coverage']-.02
assert common['means']['candidate']['common_mae_m']<=1.05*common['means']['base']['common_mae_m']
source_manifest=json.loads((B/'来源/source-manifest.json').read_text())
assert all(sha256(B/'来源/GS-ICP-SLAM'/f)==h for f,h in source_manifest['files'].items())
def run(script,args,log):
 assert all(sha256(B/f)==h for f,h in pin.items()),'Pinned full development source changed'
 with (B/'日志'/log).open('a',buffering=1) as output:
  child=subprocess.Popen([sys.executable,str(B/script),*args],stdout=output,stderr=subprocess.STDOUT)
  try:
   while child.poll() is None:
    status('running',script=script,child_pid=child.pid,args=args,log=log);print('FULL_ONLINE_CHILD',script,child.pid,flush=True);time.sleep(10)
  finally:
   if child.poll() is None:
    child.terminate()
    try:child.wait(timeout=10)
    except subprocess.TimeoutExpired:child.kill();child.wait()
  if child.returncode:status('failed',script=script,log=log,returncode=child.returncode);raise RuntimeError(log)
for variant,budget,dw,cw,name in jobs:
 R=E/'运行'/name
 if R.exists():
  saved=json.loads((R/'state.json').read_text());assert saved['status']=='complete','Interrupted online run needs a new preserved run ID'
  assert all(sha256(R/f)==h for f,h in saved['artifacts'].items())
  q=json.loads((R/'manifest.json').read_text())['quality_args'];assert (q['variant'],q['frames'],q['steps_per_frame'],q['input_fps'],q['depth_weight'],q['coverage_weight'])==(variant,frames,budget,5.,dw,cw)
  print('FULL_VERIFIED_COMPLETE_REUSED',name,flush=True)
 else:run('run_online_v6.py',['--scene','tum-office','--frames',str(frames),'--steps-per-frame',str(budget),'--input-fps','5',
                            '--variant',variant,'--depth-weight',str(dw),'--coverage-weight',str(cw),'--run-id',name],name+'.log')
 run('evaluate_local_v2.py',[name],name+'-eval.log')
 if name!=base:run('common_depth_v2.py',[base,name],name+'-common-depth.log')
 run('visible_needle_effect_v2.py',[base,name],name+'-native-views.log')
 run('describe_projected_needles.py',[base,name],name+'-projection.log')
 run('report_online.py',[name],name+'-report.log')
run('build_matched_view_boards.py',['--base',base,'--runs',*[j[-1] for j in jobs],'--tag','online-full-v6'],'online-full-v6-boards.log')
status('complete',jobs=jobs);print('ONLINE_FULL_V6_COMPLETE_METRICS_AND_VIEWS_REVIEW_STILL_REQUIRED',flush=True)
