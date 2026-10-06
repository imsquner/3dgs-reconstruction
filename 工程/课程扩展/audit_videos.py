import json,hashlib
from pathlib import Path
import cv2
base=Path(__file__).resolve().parents[1]/'运行';reports=[]
for path in sorted(base.glob('*/realtime-record.mp4')):
 cap=cv2.VideoCapture(str(path));fps=cap.get(cv2.CAP_PROP_FPS);declared=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));count=0;shape=None
 while True:
  ok,frame=cap.read()
  if not ok:break
  count+=1;shape=list(frame.shape)
 cap.release();summary=json.loads((path.parent/'summary.json').read_text());record=summary['recording']
 report=dict(run=path.parent.name,decoded_frames=count,metadata_frames=declared,fps=fps,duration_seconds=count/fps,shape=shape,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),matches_summary=count==record['frames'],initialization_excluded=record['excludes_initialization'],policy=record['policy'],scope='Input and currently available reconstruction render; recording ends at last tracking display and excludes shutdown/evaluation')
 (path.parent/'video-audit.json').write_text(json.dumps(report,indent=2));reports.append(report);print(json.dumps(report),flush=True)
(base/'视频审计.json').write_text(json.dumps(reports,indent=2))
