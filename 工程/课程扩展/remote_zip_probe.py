import io,json,zipfile,requests
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]/'数据'/'EndoSLAM'
class Remote(io.RawIOBase):
 def __init__(self,url,size): self.url=url;self.size=size;self.pos=0;self.session=requests.Session();self.session.headers.update({"User-Agent":"Mozilla/5.0","Referer":"https://data.mendeley.com/datasets/cd2rtzm23r/1"})
 def seekable(self): return True
 def readable(self): return True
 def tell(self):return self.pos
 def seek(self,off,whence=0):self.pos=off if whence==0 else self.pos+off if whence==1 else self.size+off;return self.pos
 def read(self,n=-1):
  if n<0:n=self.size-self.pos
  n=min(n,self.size-self.pos)
  if n<=0:return b''
  start=self.pos
  with self.session.get(self.url,headers={'Range':f'bytes={start}-{start+n-1}'},stream=True,timeout=40) as r:
   r.raise_for_status()
   if r.status_code!=206:raise RuntimeError(f'Range unavailable {r.status_code}')
   data=r.content
   if len(data)!=n:raise RuntimeError(f'Range length {len(data)} != {n}')
  self.pos+=n;return data
items=json.loads((BASE/'resolved.json').read_text(encoding='utf-8-sig'))
for item in items:
 print('ZIP_INDEX_START',item['filename'],flush=True)
 d=item['content_details']; remote=Remote(item['resolved_url'],d['size'])
 with zipfile.ZipFile(remote) as z:
  rows=[dict(name=i.filename,size=i.file_size,compressed=i.compress_size,offset=i.header_offset,crc=i.CRC) for i in z.infolist()]
  (BASE/(item['filename']+'.index.json')).write_text(json.dumps(rows,indent=2))
  print('INDEX',len(rows),rows[:6],flush=True)
