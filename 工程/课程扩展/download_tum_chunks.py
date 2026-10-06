import requests,os,hashlib,json,time,threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
BASE=Path(__file__).resolve().parents[1]/'数据'/'TUM'
lock=threading.Lock(); donebytes=0
for name,total in [('xyz',448204271),('desk',0)]:
 url=f'https://vision.in.tum.de/rgbd/dataset/freiburg1/rgbd_dataset_freiburg1_{name}.tgz'
 final=BASE/f'rgbd_dataset_freiburg1_{name}.tgz';prefix=final.with_suffix('.tgz.part')
 if final.exists(): print('EXISTS',name,flush=True);continue
 probe=requests.get(url,headers={'Range':'bytes=0-0'},timeout=40);probe.raise_for_status();assert probe.status_code==206
 total=int(probe.headers['Content-Range'].split('/')[-1]);base=prefix.stat().st_size if prefix.exists() else 0
 chunkdir=BASE/'chunks'/name;chunkdir.mkdir(parents=True,exist_ok=True);tasks=[];donebytes=base;started=time.monotonic()
 for offset in range(base,total,16*1024*1024):tasks.append((offset,min(total,offset+16*1024*1024)))
 print('DOWNLOAD_START',name,'total',total,'prefix',base,flush=True)
 def getchunk(task):
  global donebytes
  a,b=task;p=chunkdir/f'{a}-{b}.bin'
  if p.exists() and p.stat().st_size==b-a:
   with lock:donebytes+=b-a
   return p
  for attempt in range(3):
   try:
    with requests.get(url,headers={'Range':f'bytes={a}-{b-1}'},stream=True,timeout=40) as r:
     r.raise_for_status();assert r.status_code==206 and r.headers['Content-Range'].startswith(f'bytes {a}-{b-1}/')
     temp=p.with_suffix('.part')
     with temp.open('wb') as f:
      for buf in r.iter_content(1024*1024):f.write(buf)
    assert temp.stat().st_size==b-a;temp.replace(p)
    with lock:donebytes+=b-a
    return p
   except Exception:
    if attempt==2:raise
    time.sleep(2)
 with ThreadPoolExecutor(max_workers=4) as pool:
  pending={pool.submit(getchunk,t) for t in tasks}
  while pending:
   completed,pending=wait(pending,timeout=10,return_when=FIRST_COMPLETED)
   for f in completed:f.result()
   elapsed=time.monotonic()-started;speed=(donebytes-base)/max(elapsed,1)
   print('HEARTBEAT',name,'bytes',donebytes,'total',total,'elapsed',round(elapsed),'eta',round((total-donebytes)/speed) if speed else 'pending',flush=True)
 temp=final.with_suffix('.assembling');h=hashlib.sha256()
 with temp.open('wb') as out:
  sources=([prefix] if base else [])+[chunkdir/f'{a}-{b}.bin' for a,b in tasks]
  for p in sources:
   with p.open('rb') as f:
    while buf:=f.read(1024*1024):out.write(buf);h.update(buf)
 assert temp.stat().st_size==total;temp.replace(final)
 (BASE/(final.name+'.sha256')).write_text(h.hexdigest()+'  '+final.name+'\n')
 print('DOWNLOAD_COMPLETE',name,total,h.hexdigest(),flush=True)
