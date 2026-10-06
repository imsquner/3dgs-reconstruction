import json
from pathlib import Path
import cv2
B=Path(__file__).resolve().parents[1]/'运行'
rows=[]
for name in ['gsicp-office-full-10fps-finite','gsicp-desk240-10fps-finite']+[f'gsicp-office240-10fps-repeat{i}' for i in (1,2,3)]+['medical-mono240-5fps']+[f'medical-mono240-5fps-r{i}' for i in (2,3)]:
 run=B/name; audit=run/'experiment-audit.json'
 if not audit.exists():continue
 report=json.loads(audit.read_text());rows.append(report)
 for video in run.glob('*.mp4'):
  cap=cv2.VideoCapture(str(video));count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));fps=cap.get(cv2.CAP_PROP_FPS);cap.set(cv2.CAP_PROP_POS_FRAMES,max(0,count-1));ok,frame=cap.read();cap.release()
  if ok:
   out=run/'video-preview';out.mkdir(exist_ok=True);assert cv2.imwrite(str(out/'last-frame.png'),frame)
   (out/'metadata.json').write_text(json.dumps(dict(video=str(video),frame=count-1,encoder_fps=fps,time_seconds=(count-1)/fps,scope='Actual last encoded online video frame'),indent=2))
(B/'selected-results.json').write_text(json.dumps(rows,indent=2));print('SELECTED_REPORTS',len(rows))
