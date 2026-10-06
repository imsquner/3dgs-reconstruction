import tarfile,hashlib,json
from pathlib import Path,PurePosixPath
B=Path(__file__).resolve().parents[1]/'数据'/'TUM'
for seq in ['xyz','desk']:
 archive=B/f'rgbd_dataset_freiburg1_{seq}.tgz';target=B/f'rgbd_dataset_freiburg1_{seq}'
 if not archive.exists():print('NOT_READY',seq,flush=True);continue
 if (target/'data-audit.json').exists():print('VERIFIED_EXISTS',seq,flush=True);continue
 h=hashlib.sha256()
 with archive.open('rb') as f:
  while chunk:=f.read(1024*1024):h.update(chunk)
 expected=(B/(archive.name+'.sha256')).read_text().split()[0];assert h.hexdigest()==expected
 with tarfile.open(archive) as t:
  members=t.getmembers()
  for m in members:
   p=PurePosixPath(m.name)
   assert not p.is_absolute() and '..' not in p.parts and p.parts[0]==target.name
   assert m.isfile() or m.isdir()
  print('EXTRACT_START',seq,len(members),flush=True);t.extractall(B)
 report=dict(sequence=seq,archive_bytes=archive.stat().st_size,archive_sha256=h.hexdigest(),members=len(members),rgb_files=len(list((target/'rgb').glob('*.png'))),depth_files=len(list((target/'depth').glob('*.png'))),indices={n:(target/n).is_file() for n in ['rgb.txt','depth.txt','groundtruth.txt']})
 assert all(report['indices'].values());(target/'data-audit.json').write_text(json.dumps(report,indent=2));print('EXTRACT_VERIFIED',report,flush=True)
