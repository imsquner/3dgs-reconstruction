"""Verify installed website files with streaming SHA-256."""
import argparse,json
from pathlib import Path
from download_assets import matches,safe_path

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]); p.add_argument('--manifest',type=Path)
    p.add_argument('--package',action='append',nargs='+',choices=['website-core','replica-research'])
    a=p.parse_args(argv); selected=set(sum(a.package,[]) if a.package else ['website-core'])
    manifest=json.loads((a.manifest or Path(__file__).resolve().parents[1]/'docs/release-assets.json').read_text(encoding='utf-8'))
    records=[r for r in manifest['files'] if r.get('package') in selected]
    if any(not any(r.get('package')==x for r in records) for x in selected): raise ValueError('No verification records for selected package')
    failed=0
    for item in records:
        path=safe_path(a.root.resolve(),item['path']); status='OK' if matches(path,item) else ('MISMATCH' if path.exists() else 'MISSING')
        print(status,item['path'],flush=True); failed+=status!='OK'
    return int(bool(failed))
if __name__=='__main__':
    try: raise SystemExit(main())
    except (OSError,ValueError,KeyError) as e:
        print('ERROR:',e,flush=True); raise SystemExit(1)
