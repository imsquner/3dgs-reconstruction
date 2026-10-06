import subprocess,json
from pathlib import Path
packages=['libpcl-dev','libeigen3-dev','libflann-dev','libflann1.9','liblz4-dev']+['libpcl-'+x+'1.12' for x in ['common','registration','filters','features','kdtree','search','octree','sample-consensus']]+['libboost1.74-dev']+['libboost-'+x+'1.74.0' for x in ['system','filesystem','thread','date-time','iostreams','serialization','chrono','atomic','regex']]+['libboost-'+x+'1.74-dev' for x in ['system','filesystem','thread','date-time','iostreams','serialization','chrono','atomic','regex']]
rows=[]
for name in packages:
 raw=subprocess.check_output(['apt-cache','show',name],text=True)
 blocks=[]
 for stanza in raw.strip().split('\n\n'):
  d=dict(line.split(': ',1) for line in stanza.splitlines() if ': ' in line and not line.startswith(' '))
  if 'Filename' in d:blocks.append(d)
 d=blocks[-1] # oldest indexed jammy base package, stable archive URL
 rows.append(dict(package=name,version=d['Version'],url='https://archive.ubuntu.com/ubuntu/'+d['Filename'],sha256=d['SHA256'],size=int(d['Size']),filename=Path(d['Filename']).name))
out=Path(__file__).resolve().parents[1]/'数据'/'GS-ICP';out.mkdir(exist_ok=True)
(out/'deb-manifest.json').write_text(json.dumps(rows,indent=2));print('PACKAGES',len(rows),'BYTES',sum(r['size'] for r in rows))
