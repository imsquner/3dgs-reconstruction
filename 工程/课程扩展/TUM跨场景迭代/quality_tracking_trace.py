"""Read-only actual GICP inputs for small development replay; never alters arrays."""
import hashlib,json
from pathlib import Path
import numpy as np

def digest(array):
 a=np.ascontiguousarray(array)
 return hashlib.sha256(str((a.shape,a.dtype)).encode()+a.tobytes()).hexdigest()

def target(tracker,index,points,rotations,scales,output,initial_filter=None):
 if index>=80:return
 p=Path(output)/'GICP输入';p.mkdir(exist_ok=True)
 data={name:np.asarray(value).copy() for name,value in [('points',points),('rotations',rotations),('scales',scales)]}
 if initial_filter is not None:tracker.quality_trace_initial_target_filter=np.asarray(initial_filter).copy()
 data['initial_target_filter']=tracker.quality_trace_initial_target_filter
 name=f'target-{index:04d}.npz';np.savez(p/name,**data)
 tracker.quality_trace_target=name
 with (p/'targets.jsonl').open('a') as f:f.write(json.dumps(dict(frame=index,file=name,hashes={k:digest(v) for k,v in data.items()},point_count=len(data['points'])))+'\n')

def alignment(tracker,index,points,source_filter,initial_pose,output):
 if index>=80:return
 p=Path(output)/'GICP输入';p.mkdir(exist_ok=True)
 data={name:np.asarray(value).copy() for name,value in [('points',points),('source_filter',source_filter),('initial_pose',initial_pose)]}
 name=f'source-{index:04d}.npz';np.savez(p/name,**data)
 with (p/'alignment.jsonl').open('a') as f:f.write(json.dumps(dict(frame=index,file=name,target_file=tracker.quality_trace_target,hashes={k:digest(v) for k,v in data.items()}))+'\n')
