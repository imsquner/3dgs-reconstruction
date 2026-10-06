"""Read live process and map-update telemetry; ETA is an extrapolation only."""
import argparse,json,time
from pathlib import Path
from quality_core import atomic_json
B=Path(__file__).resolve().parent;E=B.parents[1]

def read_events(path):
 if not path.exists():return []
 lines=path.read_text().splitlines();events=[]
 for index,line in enumerate(lines):
  try:events.append(json.loads(line))
  except json.JSONDecodeError:
   if index!=len(lines)-1:raise
 return events

def main():
 p=argparse.ArgumentParser();p.add_argument('--state',default='online-full-v6.json');a=p.parse_args()
 assert Path(a.state).name==a.state
 d=json.loads((B/'状态'/a.state).read_text());result={'batch_state':a.state,'updated':time.time(),'stage':d['stage'],'child_pid':d.get('child_pid')}
 child=Path('/proc')/str(d.get('child_pid',0))/'cmdline'
 result['child_confirmed_live']=child.exists() and str(d.get('script','')).encode() in child.read_bytes()
 if d.get('script','').startswith('run_online_') and result['child_confirmed_live']:
  args=d['args'];value=lambda flag:args[args.index(flag)+1]
  run=value('--run-id');frames=int(value('--frames'));budget=int(value('--steps-per-frame'));R=E/'运行'/run
  tracking=read_events(R/'tracking-timing.jsonl');events=read_events(R/'mapping-timing.jsonl');last=events[-1] if events else None
  recent=events[-50:];rate=(recent[-1]['mapping_iteration']-recent[0]['mapping_iteration'])/(recent[-1]['completion_monotonic']-recent[0]['completion_monotonic']) if len(recent)>1 else None
  done=last['mapping_iteration'] if last else 0;fps=float(value('--input-fps')) if '--input-fps' in args else 0.
  due_remaining=max(0.,tracking[0]['scheduled_arrival_monotonic']+(frames-1)/fps-time.monotonic()) if tracking and fps>0 else None
  result.update(run=run,tracking_completions=len(tracking),frames=frames,mapping_iterations_done=done,mapping_iterations_total=frames*budget,
   gaussians=last['gaussians'] if last else None,recent_mapping_iterations_per_second=rate,
   scheduled_arrival_remaining_seconds=due_remaining,
   extrapolated_mapping_remaining_seconds=(frames*budget-done)/rate if rate else None,
   scope='Actual live child and completed JSONL events. ETA uses last 50 map updates; camera visibility/map growth/host load may change speed. Scheduled arrivals are not completed processing; mapping ETA excludes final PLY saving, worker shutdown and evaluation. No every-frame map-readiness claim.')
 atomic_json(B/'状态'/(Path(a.state).stem+'-progress.json'),result);print('LIVE_PROGRESS',json.dumps(result,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
