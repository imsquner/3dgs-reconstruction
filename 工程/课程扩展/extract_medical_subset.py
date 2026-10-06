import json,re,struct,zlib,hashlib,time,requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
BASE=Path(__file__).resolve().parents[1]/'数据'/'EndoSLAM'
items=json.loads((BASE/'resolved.json').read_text(encoding='utf-8-sig'))
records=[]
def extract(task):
 item,row=task; filename=Path(row['name']).name; kind='rgb' if item['filename']=='Frames.zip' else 'depth'
 out=BASE/'subset240'/kind/filename;out.parent.mkdir(parents=True,exist_ok=True)
 if out.exists() and out.stat().st_size==row['size']:return dict(kind=kind,file=filename,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),bytes=row['size'],archive_crc=row['crc'])
 offset=row['offset'];end=min(item['size']-1,offset+row['compressed']+4095)
 for attempt in range(3):
  try:
   r=requests.get(item['resolved_url'],headers={'Range':f'bytes={offset}-{end}'},timeout=40);r.raise_for_status()
   assert r.status_code==206
   data=r.content;head=struct.unpack('<4s5H3I2H',data[:30]);assert head[0]==b'PK\x03\x04'
   start=30+head[-2]+head[-1];encoded=data[start:start+row['compressed']]
   payload=zlib.decompress(encoded,-15) if head[3]==8 else encoded
   assert len(payload)==row['size'] and zlib.crc32(payload)&0xffffffff==row['crc']
   tmp=out.with_suffix('.part');tmp.write_bytes(payload);tmp.replace(out)
   return dict(kind=kind,file=filename,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),archive_crc=row['crc'])
  except Exception:
   if attempt==2:raise
   time.sleep(2)
tasks=[]
for item in items:
 rows=json.loads((BASE/(item['filename']+'.index.json')).read_text())
 selected=sorted([r for r in rows if r['size'] and re.search(r'_(\d+)\.png$',r['name'])],key=lambda r:int(re.search(r'_(\d+)\.png$',r['name'])[1]))[:240]
 tasks.extend((item,row) for row in selected)
print('SUBSET_START files',len(tasks),flush=True);begin=time.monotonic()
with ThreadPoolExecutor(max_workers=4) as pool:
 futures=[pool.submit(extract,t) for t in tasks]
 for f in as_completed(futures):
  records.append(f.result())
  if len(records)%10==0:print('PROGRESS',len(records),len(tasks),'elapsed',round(time.monotonic()-begin,1),'eta',round((time.monotonic()-begin)*(len(tasks)/len(records)-1),1),flush=True)
  (BASE/'subset240-manifest.partial.json').write_text(json.dumps(records,indent=2))
manifest=dict(source='https://data.mendeley.com/datasets/cd2rtzm23r/1',doi='10.17632/cd2rtzm23r.1',license='CC BY 4.0',scene='UnityCam synthetic colon',subset='first 240 numeric frame IDs',full_archive_sha256_verified=False,files=records)
(BASE/'subset240-manifest.json').write_text(json.dumps(manifest,indent=2));print('SUBSET_COMPLETE',len(records),flush=True)
