from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
import argparse,json,threading
from functools import lru_cache
from urllib.parse import urlsplit,unquote
B=Path(__file__).resolve().parent
PUBLIC_FILES={'index.html','style.css','app.mjs','catalog.mjs','timeline.mjs','ui-state.mjs','loader-bridge.mjs','first-person.mjs','experiment-versions.mjs','history-map.mjs'}
HISTORY_ROOT=B.parent/'GSICP历史快照'/'运行'
HISTORY_RUNS={'tum':'tum-smoke30-a3','replica':'replica-smoke30-a1'}
@lru_cache(maxsize=8)
def cached_history_allowed(path,mtime_ns,size):
 return frozenset(row['ply'] for row in json.loads(Path(path).read_text(encoding='utf-8'))['snapshots'])
def history_allowed(root):
 path=root/'snapshot-index.json';stat=path.stat()
 return cached_history_allowed(str(path),stat.st_mtime_ns,stat.st_size)
class Handler(SimpleHTTPRequestHandler):
 def translate_path(self,path):
  requested=unquote(urlsplit(path).path)
  if requested.startswith('/history/'):
   parts=requested.strip('/').split('/')
   registry_path=B/'assets/history-publications.json'
   registry=json.loads(registry_path.read_text(encoding='utf-8')) if registry_path.exists() else {}
   if len(parts)==3 and parts[1] in HISTORY_RUNS and parts[2]=='index.json':
    item=registry.get(parts[1]);target=(B/item['index']).resolve() if item else B/'assets/history-smoke'/parts[1]/'index.json'
    try:target.relative_to(B/'assets')
    except ValueError:return str(B/'__not_public__')
    return str(target)
   if len(parts)==4 and parts[1] in HISTORY_RUNS and parts[2]=='snapshots':
    run=registry.get(parts[1],{}).get('run_id',HISTORY_RUNS[parts[1]])
    root=(HISTORY_ROOT/run).resolve()
    try:root.relative_to(HISTORY_ROOT.resolve())
    except ValueError:return str(B/'__not_public__')
    allowed=history_allowed(root)

    relative='/'.join(parts[2:])
    if relative in allowed:return str(root/relative)
   return str(B/'__not_public__')
  return super().translate_path(path)
 def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(B),**kwargs)
 def end_headers(self):
  self.send_header('Cross-Origin-Opener-Policy','same-origin');self.send_header('Cross-Origin-Embedder-Policy','require-corp');self.send_header('Cache-Control','no-cache');super().end_headers()
 def do_GET(self):
  if self.path=='/health':
   b=json.dumps({'app':'3dgs-course-interactive','status':'ready'}).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
  else:
   if not self.public_path():self.send_error(404);return
   super().do_GET()
 def public_path(self):
  requested=unquote(urlsplit(self.path).path).lstrip('/') or 'index.html'
  if requested.startswith('history/'):
   return Path(self.translate_path(self.path)).is_file()
  target=(B/requested).resolve()
  try:relative=target.relative_to(B)
  except ValueError:return False
  return target.is_file() and (relative.as_posix() in PUBLIC_FILES or relative.parts[0] in ('assets','vendor'))
 def do_HEAD(self):
  if not self.public_path():self.send_error(404);return
  super().do_HEAD()
 def list_directory(self,path):self.send_error(404);return None
 def do_POST(self):
  if self.client_address[0]=='127.0.0.1' and self.path=='/shutdown' and self.headers.get('Origin') in (None,'http://127.0.0.1:'+str(self.server.server_port)):
   self.send_response(200);self.end_headers();self.wfile.write(b'shutting down');threading.Thread(target=self.server.shutdown).start()
  else:self.send_error(403)
 def log_message(self,fmt,*args):print(self.log_date_time_string(),fmt%args,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8765);p.add_argument('--host',default='127.0.0.1');args=p.parse_args();s=ThreadingHTTPServer((args.host,args.port),Handler);print('DEMO_READY http://'+args.host+':'+str(args.port),flush=True)
 try:s.serve_forever()
 except KeyboardInterrupt:pass
 finally:s.server_close();print('DEMO_STOPPED',flush=True)
