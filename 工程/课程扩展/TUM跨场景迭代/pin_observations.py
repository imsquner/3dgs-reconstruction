"""Hash unique protocol observations; atomic progress, reuse verified records."""
import argparse,json,time,os
from pathlib import Path
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('scene');a=p.parse_args()
source=B/'协议'/f'{a.scene}.json';protocol=json.loads(source.read_text())
paths=sorted({r[k] for label in ['upstream_original_train','upstream_original_validation','strict_common_train','strict_validation'] for r in protocol[label] for k in ['rgb_path','depth_path']})
out=B/'协议'/f'{a.scene}-observations.json';signature=sha256(source)
old=json.loads(out.read_text()) if out.exists() else {};records=old.get('files',{}) if old.get('protocol_sha256')==signature else {}
start=time.monotonic()
for i,name in enumerate(paths,1):
 path=Path(name);stat=path.stat();prior=records.get(name)
 if prior and prior['bytes']==stat.st_size and prior['mtime_ns']==stat.st_mtime_ns:continue
 records[name]={'bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns,'sha256':sha256(path)}
 if i%100==0:
  atomic_json(out,{'protocol_sha256':signature,'complete':False,'files':records,'pid':os.getpid(),'updated':time.time()});print('PIN',i,'/',len(paths),'seconds',round(time.monotonic()-start,1),flush=True)
assert len(records)==len(paths)
atomic_json(out,{'protocol_sha256':signature,'complete':True,'files':records,'seconds':time.monotonic()-start,'scope':'Content SHA256 at pin time; resumed entries require identical size and mtime; final package must rehash, not trust timestamps'})
print('PIN_COMPLETE',a.scene,len(paths),flush=True)
