from pathlib import Path
import json,hashlib,sys
root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'docs/assets-manifest.json').read_text(encoding='utf-8'))
failed=0
for item in manifest['files']:
    p=root/item['path']
    status='MISSING' if not p.is_file() else ('OK' if p.stat().st_size==item['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'] else 'MISMATCH')
    print(status,item['path'],flush=True)
    failed+=status!='OK'
sys.exit(1 if failed else 0)
