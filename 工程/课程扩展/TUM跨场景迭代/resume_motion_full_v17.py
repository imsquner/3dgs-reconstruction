"""Guarded stage recovery; does not resume interrupted optimizer state."""
import argparse,json,sys
from pathlib import Path
from frozen_plan_semantics import assert_same_plan
from quality_core import sha256,atomic_json
B=Path(__file__).resolve().parent;E=B.parents[1]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');a=parser.parse_args()
 script=B/'online_motion_prior_full_batch.py';text=script.read_text();marker="p=B/'协议/online-motion-prior-full-v17-frozen.json'"
 assert text.count(marker)==1
 ns={'__file__':str(script),'__name__':'frozen_preflight'};exec(compile(text[:text.index(marker)],str(script),'exec'),ns)
 saved=json.loads((B/'协议/online-motion-prior-full-v17-frozen.json').read_text());assert_same_plan(saved,ns['plan'])
 state=json.loads((B/'状态/online-motion-prior-full-v17.json').read_text())
 cmd=Path('/proc')/str(state['pid'])/'cmdline'
 live=cmd.exists() and ('online_motion_prior_full_batch.py' in cmd.read_bytes().replace(b'\0',b' ').decode() or 'resume_motion_full_v17.py' in cmd.read_bytes().replace(b'\0',b' ').decode())
 if a.check:print('FROZEN_PLAN_CHECK_OK', 'coordinator_live',live,flush=True);return
 assert not live,'Existing coordinator still live; do not duplicate GPU jobs'
 if state['stage']=='complete':print('BATCH_ALREADY_COMPLETE_NO_ACTION',flush=True);return
 for j in ns['jobs']:
  run=E/'运行'/j[7]
  if run.exists():
   completed=json.loads((run/'state.json').read_text());assert completed['status']=='complete','Interrupted training is preserved; new ID/plan required'
   assert all(sha256(run/f)==h for f,h in completed['artifacts'].items())
 old='assert json.loads(p.read_text())==plan';assert text.count(old)==1
 patched=text.replace(old,'assert assert_same_plan(json.loads(p.read_text()),plan)')
 atomic_json(B/'验证/v17恢复执行审计.json',{'original_script_sha256':sha256(script),'recovery_entry_sha256':sha256(__file__),'protocol_sha256':sha256(B/'协议/online-motion-prior-full-v17-frozen.json'),'change':'Only JSON tuple/list comparison normalized in memory. Original file and frozen protocol unchanged. Completed artifacts checked; no interrupted optimizer resume.'})
 exec(compile(patched,str(script),'exec'),{'__file__':str(script),'__name__':'__main__','assert_same_plan':assert_same_plan})
if __name__=='__main__':main()
