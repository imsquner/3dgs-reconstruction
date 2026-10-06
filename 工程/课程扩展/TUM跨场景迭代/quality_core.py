"""Protocol helpers. Offline association; no claim of causal live matching."""
import bisect,json,os,time,hashlib,sys
from pathlib import Path

def paired_frames(rgb_times,depth_times,max_dt=.02):
 if max_dt<0:raise ValueError('negative max_dt')
 if list(rgb_times)!=sorted(rgb_times) or list(depth_times)!=sorted(depth_times):raise ValueError('timestamps must be sorted')
 candidates=[]
 for i,t in enumerate(rgb_times):
  lo=bisect.bisect_left(depth_times,t-max_dt);hi=bisect.bisect_right(depth_times,t+max_dt)
  candidates.extend((abs(depth_times[j]-t),i,j) for j in range(lo,hi))
 used_i=set();used_j=set();pairs=[]
 for dt,i,j in sorted(candidates):
  if i not in used_i and j not in used_j:
   used_i.add(i);used_j.add(j);pairs.append((i,j))
 return sorted(pairs)

def split_depth_groups(rows,held_source_ids):
 test=[r for r in rows if r['source_frame'] in held_source_ids]
 ids={r['depth_id'] for r in test}
 train=[r for r in rows if r['source_frame'] not in held_source_ids and r['depth_id'] not in ids]
 return train,test

def sha256(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 return h.hexdigest()

def atomic_json(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.partial')
 with tmp.open('w',encoding='utf8') as f:
  json.dump(value,f,indent=2,ensure_ascii=False);f.flush();os.fsync(f.fileno())
 for attempt in range(8):
  try:
   os.replace(tmp,path);return
  except PermissionError:
   if attempt==7:raise
   delay=min(.05*2**attempt,.5)
   print('ATOMIC_JSON_RETRY',path.name,attempt+1,'delay',delay,file=sys.stderr,flush=True)
   time.sleep(delay)

class StageLedger:
 def __init__(self,path,protocol_hash):
  self.path=Path(path);self.state=json.loads(self.path.read_text()) if self.path.exists() else {'protocol_hash':protocol_hash,'stages':{}}
  if self.state['protocol_hash']!=protocol_hash:raise ValueError('Protocol mismatch: start separate run')
 def done(self,name):
  row=self.state['stages'].get(name,{})
  return row.get('status')=='complete' and all(Path(p).exists() and sha256(p)==h for p,h in row.get('artifacts',{}).items())
 def _put(self,name,status,evidence):
  self.state['stages'][name]=dict(status=status,updated=time.time(),**evidence);atomic_json(self.path,self.state)
 def finish(self,name,evidence):
  if evidence.get('exit',0)!=0:raise ValueError('Failed exit cannot be complete')
  self._put(name,'complete',evidence)
 def fail(self,name,error):self._put(name,'failed',{'error':str(error)})
