"""Resumable release download and safe installation (standard library only)."""
import argparse, hashlib, http.client, json, os, re, shutil, tarfile, tempfile, time, urllib.request, zipfile
from pathlib import Path, PurePosixPath

def digest(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()

def safe_path(root,name):
    if not isinstance(name,str) or not name or '\\' in name or ':' in name: raise ValueError('Unsafe path: '+repr(name))
    p=PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts: raise ValueError('Unsafe path: '+name)
    reserved={'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}
    if any(part.endswith((' ','.')) or part.split('.')[0].upper() in reserved or any(ord(c)<32 for c in part) for part in p.parts): raise ValueError('Unsafe Windows path: '+name)
    dest=root.joinpath(*p.parts)
    if not dest.resolve().is_relative_to(root.resolve()): raise ValueError('Path escapes root')
    return dest

def matches(p,item):
    return p.is_file() and not p.is_symlink() and p.stat().st_size==item['bytes'] and digest(p)==item['sha256']

def download(item,cache,offline=False,retries=4):
    cache.mkdir(parents=True,exist_ok=True)
    final=safe_path(cache,item['name'])
    if final.parent!=cache or item['bytes']<0 or not re.fullmatch('[0-9a-f]{64}',item['sha256']): raise ValueError('Invalid asset metadata')
    if final.exists():
        if matches(final,item): return final
        raise ValueError('Existing cache checksum mismatch')
    if offline: raise FileNotFoundError('Offline asset missing: '+str(final))
    partial=final.with_name(final.name+'.partial'); checkpoint=final.with_name(final.name+'.checkpoint.json')
    identity={k:item[k] for k in ('name','bytes','sha256','url')}
    if partial.exists() and (not checkpoint.exists() or json.loads(checkpoint.read_text(encoding='utf-8'))!=identity): raise ValueError('Partial identity mismatch')
    if partial.is_symlink() or checkpoint.is_symlink(): raise ValueError('Unsafe download checkpoint')
    checkpoint.write_text(json.dumps(identity),encoding='utf-8')
    for attempt in range(retries):
        start=partial.stat().st_size if partial.exists() else 0
        if start == item['bytes'] and matches(partial,item):
            os.replace(partial,final); checkpoint.unlink(missing_ok=True); return final
        try:
            req=urllib.request.Request(item['url'],headers={'Range':f'bytes={start}-'} if start else {})
            began=time.monotonic(); last=0
            with urllib.request.urlopen(req,timeout=30) as response:
                if start and response.status==206:
                    if not response.headers.get('Content-Range','').startswith(f'bytes {start}-'): raise ValueError('Invalid Content-Range')
                    mode='ab'
                else: start=0; mode='wb'
                total=start
                with open(partial,mode) as out:
                    while True:
                        chunk=response.read(1048576)
                        if not chunk: break
                        out.write(chunk); total+=len(chunk)
                        if total>item['bytes']: raise ValueError('Download exceeds declared size')
                        elapsed=time.monotonic()-began
                        if elapsed-last>=2:
                            rate=(total-start)/max(elapsed,.001)
                            print(f"{item['id']}: {total}/{item['bytes']} bytes ETA {(item['bytes']-total)/max(rate,1):.0f}s",flush=True); last=elapsed
            if not matches(partial,item): raise ValueError('Checksum or size mismatch')
            os.replace(partial,final); checkpoint.unlink(missing_ok=True)
            print('Verified: '+item['id'],flush=True); return final
        except ValueError:
            partial.unlink(missing_ok=True); checkpoint.unlink(missing_ok=True); raise
        except (OSError,EOFError,http.client.IncompleteRead) as exc:
            if attempt+1==retries: raise
            print(f'Retry {attempt+1}: {exc}',flush=True); time.sleep(min(2**attempt,8))

def extract(archive,item,stage):
    seen=set()
    began=time.monotonic();last=began;count=0
    def progress():
        nonlocal last,count
        count+=1;now=time.monotonic()
        if now-last>=5:
            print(f"EXTRACT_HEARTBEAT package={item['id']} members={count} elapsed={now-began:.1f}s ETA=unknown",flush=True);last=now
    def destination(name):
        p=safe_path(stage,name.rstrip('/')); key=str(p).casefold()
        if key in seen: raise ValueError('Duplicate archive path')
        seen.add(key); return p
    if item['format']=='zip':
        with zipfile.ZipFile(archive) as z:
            for m in z.infolist():
                p=destination(m.filename); mode=m.external_attr>>16
                if (mode & 0o170000) not in (0,0o100000,0o040000): raise ValueError('Special archive file')
                if m.is_dir(): p.mkdir(parents=True,exist_ok=True)
                else:
                    p.parent.mkdir(parents=True,exist_ok=True)
                    with z.open(m) as source,open(p,'xb') as out: shutil.copyfileobj(source,out)
                progress()
    elif item['format']=='tar.gz':
        with tarfile.open(archive,'r:gz') as t:
            for m in t:
                p=destination(m.name)
                if m.isdir(): p.mkdir(parents=True,exist_ok=True)
                elif m.isfile():
                    p.parent.mkdir(parents=True,exist_ok=True)
                    with t.extractfile(m) as source,open(p,'xb') as out: shutil.copyfileobj(source,out)
                else: raise ValueError('Archive link or special file')
                progress()
    else: raise ValueError('Unsupported archive format')
    if item.get('archive_root'):
        expected=safe_path(stage,item['archive_root'])
        if not expected.is_dir() or any(p!=expected for p in stage.iterdir()): raise ValueError('Unexpected archive root')

def install(archive,item,root,files):
    if item['target'] not in ('.','data'): raise ValueError('Invalid target')
    root.mkdir(parents=True,exist_ok=True); target=root if item['target']=='.' else safe_path(root,'data')
    with tempfile.TemporaryDirectory(prefix='.asset-stage-',dir=root) as temp:
        stage=Path(temp); extract(archive,item,stage)
        for record in files:
            if record.get('package')==item['id']:
                rel=PurePosixPath(record['path'])
                if item['target']=='data': rel=rel.relative_to('data')
                if not matches(safe_path(stage,str(rel)),record): raise ValueError('Staged manifest mismatch')
        entries=[(p,safe_path(target,p.relative_to(stage).as_posix())) for p in stage.rglob('*') if p.is_file()]
        for source,dest in entries:
            if dest.exists() and (not dest.is_file() or dest.is_symlink() or digest(dest)!=digest(source)): raise ValueError('Existing destination mismatch: '+str(dest))
            parent=dest.parent
            while parent!=root:
                if parent.exists() and (not parent.is_dir() or parent.is_symlink()): raise ValueError('Invalid destination parent')
                parent=parent.parent
        installed=[]
        try:
            for source,dest in entries:
                if not dest.exists():
                    dest.parent.mkdir(parents=True,exist_ok=True); os.replace(source,dest); installed.append(dest)
        except BaseException:
            for dest in reversed(installed): dest.unlink(missing_ok=True)
            raise

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]); p.add_argument('--manifest',type=Path); p.add_argument('--cache-dir',type=Path)
    p.add_argument('--package',action='append',nargs='+',default=[]); p.add_argument('--dataset',action='append',choices=['tum-office','tum-desk','tum-xyz'],default=[])
    p.add_argument('--website',action='store_true'); p.add_argument('--accept-replica-terms',action='store_true'); p.add_argument('--offline',action='store_true')
    a=p.parse_args(argv); root=a.root.resolve()
    manifest=json.loads((a.manifest or Path(__file__).resolve().parents[1]/'docs/release-assets.json').read_text(encoding='utf-8'))
    selected=set(sum(a.package,[])+a.dataset)
    if a.website or not selected:
        selected.add('website-core')
        if a.accept_replica_terms: selected.add('replica-research')
    assets={x['id']:x for x in manifest['assets']}
    if selected-assets.keys(): raise ValueError('Unknown package')
    for name in selected:
        if assets[name].get('requires_acceptance') and not a.accept_replica_terms: raise ValueError('Replica requires --accept-replica-terms')
    for name in sorted(selected):
        item=assets[name]; archive=download(item,(a.cache_dir or root/'.downloads').resolve(),a.offline)
        if item['format']!='file': install(archive,item,root,manifest.get('files',[]))
        print('Ready: '+name,flush=True)
    return 0

if __name__=='__main__':
    try: raise SystemExit(main())
    except (OSError,ValueError,KeyError,zipfile.BadZipFile,tarfile.TarError) as e:
        print('ERROR: '+str(e),flush=True); raise SystemExit(1)
