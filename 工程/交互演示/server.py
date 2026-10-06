from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
import argparse,json,threading
from urllib.parse import urlsplit,unquote
B=Path(__file__).resolve().parent
PUBLIC_FILES={'index.html','style.css','app.mjs','catalog.mjs','timeline.mjs','ui-state.mjs','loader-bridge.mjs','first-person.mjs','experiment-versions.mjs'}
class Handler(SimpleHTTPRequestHandler):
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
