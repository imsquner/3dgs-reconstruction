import json,hashlib,cv2,numpy as np
from pathlib import Path
B=Path(__file__).resolve().parents[1]/'数据'/'EndoSLAM'
m=json.loads((B/'subset240-manifest.json').read_text());rows=[]
for r in m['files']:
 p=B/'subset240'/r['kind']/r['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
 image=cv2.imread(str(p),-1);assert image is not None
 if len(rows)<4:rows.append(dict(file=r['file'],shape=image.shape,dtype=str(image.dtype),channel_ranges=[(int(image[:,:,c].min()),int(image[:,:,c].max())) for c in range(image.shape[2])] if image.ndim==3 else []))
for kind in ['rgb','depth']:
 p=sorted((B/'subset240'/kind).glob('*.png'))[0];image=cv2.imread(str(p),-1)
 print(kind,p.name,image.shape,image.dtype,'channel ranges',[(int(image[:,:,c].min()),int(image[:,:,c].max())) for c in range(image.shape[2])],flush=True)
report=dict(status='download_subset_verified',files=len(m['files']),rgb_count=240,depth_count=240,full_archive_hash_verified=False,geometry_ready=False,issue='8bit RGBA AOV depth encoding/metric scale and Unity coordinate convention need source verification',samples=rows)
(B/'subset-audit.json').write_text(json.dumps(report,indent=2));print('SUBSET_HASH_AND_DECODE_OK',len(m['files']))
