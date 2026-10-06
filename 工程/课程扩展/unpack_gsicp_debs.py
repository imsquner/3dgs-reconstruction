import json,subprocess,hashlib
from pathlib import Path
b=Path(__file__).resolve().parents[1]/'数据/GS-ICP';dst=Path('/root/.local/share/monogs/gsicp-native');dst.mkdir(exist_ok=True)
rows=json.loads((b/'deb-manifest.json').read_text())
for row in rows:
 p=b/row['filename'];assert p.stat().st_size==row['size'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
 subprocess.run(['dpkg-deb','-x',str(p),str(dst)],check=True);print('UNPACKED '+row['package'],flush=True)
print('PREFIX_READY '+str(dst),flush=True)
