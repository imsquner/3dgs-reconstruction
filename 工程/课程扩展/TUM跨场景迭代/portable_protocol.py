"""Materialize host paths without changing observations, poses or holdouts."""
import argparse,copy,json,hashlib,time
from pathlib import Path,PurePosixPath,PureWindowsPath
from quality_core import atomic_json,sha256

def relative_observation(path,source):
 path_type=PureWindowsPath if PureWindowsPath(source).drive else PurePosixPath
 p=path_type(path);root=path_type(source)
 if '..' in p.parts or not p.is_absolute():raise ValueError('Unsafe observation path')
 return PurePosixPath(p.relative_to(root).as_posix())

def rebase_protocol(protocol,dataset_root):
 result=copy.deepcopy(protocol);new_root=Path(dataset_root).resolve()
 for key,value in result.items():
  if key.endswith('_train') or key.endswith('_validation'):
   for row in value:
    for field in ['rgb_path','depth_path']:
     row[field]=str(new_root/relative_observation(row[field],protocol['source']))
 result['source']=str(new_root)
 return result

def semantic_hash(protocol):
 normalized=copy.deepcopy(protocol)
 for key,rows in normalized.items():
  if key.endswith('_train') or key.endswith('_validation'):
   for row in rows:
    for field in ['rgb_path','depth_path']:
     row[field]=str(PurePosixPath('/__DATASET_ROOT__')/relative_observation(row[field],protocol['source']))
 normalized['source']='/__DATASET_ROOT__'
 return hashlib.sha256(json.dumps(normalized,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def verify_observations(protocol,observations,dataset_root):
 if observations.get('complete') is not True:raise ValueError('Incomplete canonical observations manifest')
 required={row[field] for group,rows in protocol.items() if group.endswith('_train') or group.endswith('_validation') for row in rows for field in ['rgb_path','depth_path']}
 if not required.issubset(observations['files']):raise ValueError('Canonical manifest does not cover every protocol observation')
 root=Path(dataset_root).resolve();verified={};start=time.monotonic();total=len(observations['files'])
 for old,expected in observations['files'].items():
  target=root/relative_observation(old,protocol['source']);target.resolve().relative_to(root)
  stat=target.stat();actual=sha256(target)
  if stat.st_size!=expected['bytes'] or actual!=expected['sha256']:raise ValueError('Observation content mismatch: '+str(target))
  verified[str(target)]={'bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns,'sha256':actual}
  count=len(verified)
  if count%100==0 or count==total:
   elapsed=time.monotonic()-start;print('DATA_CONTENT_VERIFY',count,'/',total,'eta_seconds',round(elapsed/max(1,count)*(total-count),1),flush=True)
 for name,expected in protocol.get('file_hashes',{}).items():
  if PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts:raise ValueError('Unsafe metadata path')
  target=root/name;target.resolve().relative_to(root)
  if sha256(target)!=expected:raise ValueError('Dataset metadata mismatch: '+name)
 return verified

def main():
 p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);p.add_argument('--observations',required=True)
 p.add_argument('--dataset-root',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
 source=Path(a.protocol);obs_path=Path(a.observations);old=json.loads(source.read_text(encoding='utf-8'));observations=json.loads(obs_path.read_text(encoding='utf-8'))
 if observations['protocol_sha256']!=sha256(source):raise ValueError('Canonical observation manifest refers to another protocol')
 out=Path(a.output_dir);scene=old['scene'];paths=[out/f'{scene}.json',out/f'{scene}-observations.json',out/f'{scene}-host-materialization.json']
 if any(path.exists() for path in paths):raise ValueError('Use a new output directory; preserve existing protocols')
 mapped=rebase_protocol(old,a.dataset_root);assert semantic_hash(mapped)==semantic_hash(old)
 verified=verify_observations(old,observations,a.dataset_root)
 atomic_json(paths[0],mapped);atomic_json(paths[1],{'protocol_sha256':sha256(paths[0]),'complete':True,'files':verified,
 'scope':'Every observation rehashed on this host; canonical semantic input/holdout/pose identities unchanged.'})
 atomic_json(paths[2],{'canonical_protocol_sha256':sha256(source),'canonical_observations_sha256':sha256(obs_path),
 'materialized_protocol_sha256':sha256(paths[0]),'semantic_input_sha256':semantic_hash(old),'files':len(verified),
 'scope':'Paths and current file stat metadata change across hosts. Observation bytes, poses, calibration, frame/depth IDs and holdouts are preserved; these JSON byte hashes can differ.'})
 print('HOST_PROTOCOL_MATERIALIZED',scene,len(verified),flush=True)

if __name__=='__main__':main()
