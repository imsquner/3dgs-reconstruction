"""Resumable single-scene download from the existing NICE-SLAM Replica release."""
import io,zipfile,urllib.request,time,json,zlib,os,collections,sys
from pathlib import Path
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent;OUT=B/'数据/Replica';OUT.mkdir(parents=True,exist_ok=True)
(B/'日志').mkdir(exist_ok=True)
LOG=(B/'日志/replica-download.log').open('a',buffering=1)
class Tee:
 def write(self,s):sys.__stdout__.write(s);LOG.write(s)
 def flush(self):sys.__stdout__.flush();LOG.flush()
sys.stdout=Tee()
atomic_json(B/'状态/replica-download-owner.json',{'pid':os.getpid(),'started':time.time(),'status':'running','script_sha256':sha256(__file__)})
URL='https://cvg-data.inf.ethz.ch/nice-slam/data/Replica.zip';BLOCK=4*1024*1024
def request_range(start,end):
 for attempt in range(3):
  try:
   req=urllib.request.Request(URL,headers={'Range':f'bytes={start}-{end}','User-Agent':'3dgs-course-local-quality'})
   with urllib.request.urlopen(req,timeout=45) as r:
    if r.status!=206:raise RuntimeError('Server did not support byte range')
    total=int(r.headers['Content-Range'].split('/')[-1]);data=r.read()
    if len(data)!=end-start+1:raise RuntimeError('Truncated range')
   return data,total
  except Exception as e:
   print('RANGE_RETRY',attempt,str(e),flush=True)
   if attempt==2:raise
   time.sleep(2)
_,SIZE=request_range(0,0);print('ARCHIVE_SIZE',SIZE,flush=True)
class Remote(io.RawIOBase):
 def __init__(self):self.pos=0;self.cache=collections.OrderedDict();self.downloaded=0
 def seekable(self):return True
 def readable(self):return True
 def tell(self):return self.pos
 def seek(self,o,w=0):self.pos=o if w==0 else self.pos+o if w==1 else SIZE+o;return self.pos
 def read(self,n=-1):
  n=min(SIZE-self.pos,n if n>=0 else SIZE-self.pos);out=[]
  while n>0:
   idx=self.pos//BLOCK;off=self.pos%BLOCK
   if idx not in self.cache:
    start=idx*BLOCK;end=min(SIZE-1,start+BLOCK-1);buf,total=request_range(start,end)
    assert total==SIZE;self.cache[idx]=buf;self.downloaded+=len(buf)
    if len(self.cache)>4:self.cache.popitem(last=False)
    print('DOWNLOAD_BLOCK',idx,'network_MiB',round(self.downloaded/1024**2,1),flush=True)
   take=min(n,len(self.cache[idx])-off);assert take>0
   out.append(self.cache[idx][off:off+take]);self.pos+=take;n-=take
  return b''.join(out)
remote=Remote();records=[];start=time.monotonic()
with zipfile.ZipFile(remote) as archive:
 selected=[x for x in archive.infolist() if x.file_size and '/office0/' in '/'+x.filename]
 atomic_json(OUT/'archive-selected-index.json',{'url':URL,'archive_bytes':SIZE,'scene':'office0','entries':[{'name':x.filename,'bytes':x.file_size,'crc32':x.CRC} for x in selected]})
 print('SELECTED',len(selected),'bytes',sum(x.file_size for x in selected),flush=True)
 for count,item in enumerate(selected,1):
  relative=Path(item.filename.split('office0/',1)[1]);dest=OUT/'office0'/relative
  if dest.resolve().is_relative_to((OUT/'office0').resolve()) is False:raise RuntimeError('Unsafe zip path')
  dest.parent.mkdir(parents=True,exist_ok=True)
  skip=False
  if dest.exists() and dest.stat().st_size==item.file_size:
   skip=(zlib.crc32(dest.read_bytes())&0xffffffff)==item.CRC
  if not skip:
   tmp=dest.with_suffix(dest.suffix+'.partial')
   with archive.open(item) as source,tmp.open('wb') as target:
    for block in iter(lambda:source.read(1024*1024),b''):target.write(block)
   assert tmp.stat().st_size==item.file_size
   assert (zlib.crc32(tmp.read_bytes())&0xffffffff)==item.CRC
   os.replace(tmp,dest)
  records.append({'path':str(relative),'bytes':item.file_size,'crc32':item.CRC,'sha256':sha256(dest)})
  if count%20==0 or count==len(selected):
   atomic_json(OUT/'download-checkpoint.json',{'completed':count,'total':len(selected),'seconds':time.monotonic()-start,'last':str(relative),'pid':os.getpid(),'updated':time.time()})
   print('DOWNLOAD_PROGRESS',count,'/',len(selected),'elapsed',round(time.monotonic()-start,1),'reused',skip,flush=True)
paths=OUT/'office0/results';rgb=list(paths.glob('frame*.jpg'));depth=list(paths.glob('depth*.png'))
assert len(rgb)==2000 and len(depth)==2000 and (OUT/'office0/traj.txt').exists()
atomic_json(OUT/'office0/来源核验.json',{'url':URL,'archive_bytes':SIZE,'scene':'office0','rgb':len(rgb),'depth':len(depth),'files':records,'complete':True,'scope':'NICE-SLAM/iMAP-rendered Replica release; CRC checked for every extracted file; not a map result'})
print('DATA_COMPLETE',OUT/'office0',flush=True)
atomic_json(B/'状态/replica-download-owner.json',{'pid':os.getpid(),'finished':time.time(),'status':'complete','manifest_sha256':sha256(OUT/'office0/来源核验.json')})
