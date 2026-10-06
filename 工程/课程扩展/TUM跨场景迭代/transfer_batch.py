"""Frozen-parameter transfer queue; refuses to run without full development evidence."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
from quality_core import atomic_json,sha256
from quality_gate import audit
from portable_protocol import verify_observations
B=Path(__file__).resolve().parent;E=B.parents[1]

def validate_visual(visual,maps,expected_views):
 assert visual['map_sha256']==maps
 assert len(visual['views'])==9
 actual=[(r['train_index'],r['offset_local_x_m']) for r in visual['views']]
 expected=[(r['train_index'],r['offset_local_x_m']) for r in expected_views]
 assert actual==expected and len(set(actual))==9,'Review must cover every fixed view in protocol order'
 assert all(r['fewer_visible_artifacts'] is True and r['table_chair_preserved'] is True for r in visual['views'])

def validate_freeze(frozen):
 assert frozen['status']=='accepted_for_transfer'
 assert frozen['quality_parameters']=={'depth_weight':.05,'coverage_weight':.05,'needle_weight':.002}
 assert frozen['seed']==0 and frozen['input_fps']==5.
 assert all(sha256(B/name)==digest for name,digest in frozen['scripts'].items())
 source=json.loads((B/'来源/source-manifest.json').read_text())
 assert sha256(B/'来源/source-manifest.json')==frozen['source_manifest_sha256']
 assert all(sha256(B/'来源/GS-ICP-SLAM'/name)==digest for name,digest in source['files'].items())
 development=frozen['development'];result=audit(development['base'],development['candidate'],'development')
 assert result['all_numeric_gates'] is True and result['map_sha256']==development['map_sha256']
 visual_path=B/development['visual_review'];assert sha256(visual_path)==development['visual_review_sha256']
 visual=json.loads(visual_path.read_text())
 expected_views=json.loads((E/'运行'/development['base']/'评价/metrics.json').read_text())['fixed_views']
 validate_visual(visual,result['map_sha256'],expected_views)
 for scene in ['tum-desk','replica-office0']:
  assert sha256(B/'协议'/f'{scene}.json')==frozen['protocols'][scene]['protocol_sha256']
  assert sha256(B/'协议'/f'{scene}-observations.json')==frozen['protocols'][scene]['observations_sha256']

def main():
 p=argparse.ArgumentParser();p.add_argument('--freeze',required=True);a=p.parse_args()
 freeze_path=Path(a.freeze);frozen=json.loads(freeze_path.read_text());validate_freeze(frozen)
 state=B/'状态/transfer-v6.json'
 def status(stage,**extra):atomic_json(state,dict(pid=os.getpid(),updated=time.time(),freeze_sha256=sha256(freeze_path),stage=stage,**extra))
 def run(script,args,log):
  validate_freeze(frozen)
  with (B/'日志'/log).open('a',buffering=1) as out:
   child=subprocess.Popen([sys.executable,str(B/script),*args],stdout=out,stderr=subprocess.STDOUT)
   try:
    while child.poll() is None:
     status('running',script=script,args=args,child_pid=child.pid,log=log)
     print('TRANSFER_CHILD',script,child.pid,flush=True);time.sleep(10)
   finally:
    if child.poll() is None:
     child.terminate()
     try:child.wait(timeout=10)
     except subprocess.TimeoutExpired:child.kill();child.wait()
   if child.returncode:status('failed',script=script,args=args,log=log,returncode=child.returncode);raise RuntimeError(log)
 def training(scene,frames,variant,budget,name):
  r=E/'运行'/name
  if r.exists():
   saved=json.loads((r/'state.json').read_text());assert saved['status']=='complete','Preserve interrupted run; use a new run ID'
   assert all(sha256(r/f)==h for f,h in saved['artifacts'].items())
   actual=json.loads((r/'manifest.json').read_text())['quality_args']
   expected=dict(scene=scene,frames=frames,variant=variant,steps_per_frame=budget,input_fps=5.,seed=0,depth_weight=.05,coverage_weight=.05)
   assert all(actual[k]==v for k,v in expected.items())
   print('TRANSFER_VERIFIED_COMPLETE_REUSED',name,flush=True)
  else:run('run_online_v6.py',['--scene',scene,'--frames',str(frames),'--variant',variant,'--steps-per-frame',str(budget),'--input-fps','5','--seed','0','--depth-weight','.05','--coverage-weight','.05','--run-id',name],name+'.log')
 # Content hashes, not prior mtime/complete labels, prove transfer inputs unchanged.
 for scene in ['tum-desk','replica-office0']:
  status('verifying_data',scene=scene)
  protocol=json.loads((B/'协议'/f'{scene}.json').read_text());obs=json.loads((B/'协议'/f'{scene}-observations.json').read_text())
  assert obs['protocol_sha256']==sha256(B/'协议'/f'{scene}.json')
  verified=verify_observations(protocol,obs,protocol['source'])
  atomic_json(B/'验证/冻结迁移'/f'{scene}-input-content.json',dict(files=len(verified),protocol_sha256=obs['protocol_sha256'],freeze_sha256=sha256(freeze_path),verified=time.time()))
 # Replica 12m range and local GPU memory smoke; these are preflight, not transfer quality evidence.
 for variant,tag in [('original','original'),('improved-shape','coverage')]:
  training('replica-office0',40,variant,20,'local-transfer-replica40-'+tag+'-v6')
 for scene,count in [('tum-desk',527),('replica-office0',1801)]:
  protocol=json.loads((B/'协议'/f'{scene}.json').read_text());assert len(protocol['upstream_original_train'])==count
  prefix='local-transfer-'+scene
  jobs=[('original',10,prefix+'-original-b10-v6'),('original',20,prefix+'-original-b20-v6'),('improved-shape',20,prefix+'-coverage-b20-v6')]
  base=jobs[0][2]
  for variant,budget,name in jobs:
   training(scene,count,variant,budget,name)
   run('evaluate_local_v2.py',[name],name+'-eval.log')
   if name!=base:run('common_depth_v2.py',[base,name],name+'-common-depth.log')
   run('visible_needle_effect_v2.py',[base,name],name+'-native-views.log')
   run('describe_projected_needles.py',[base,name],name+'-projection.log')
   run('report_online.py',[name],name+'-report.log')
   if name!=base:run('quality_gate.py',[base,name,'--mode','transfer'],name+'-gate.log')
  run('build_matched_view_boards.py',['--base',base,'--runs',*[j[2] for j in jobs],'--tag','transfer-'+scene+'-v6'],scene+'-boards.log')
 status('complete',scope='Queue stages complete; final numeric/visual/time/memory audit remains. No test-set retuning.')

if __name__=='__main__':main()
