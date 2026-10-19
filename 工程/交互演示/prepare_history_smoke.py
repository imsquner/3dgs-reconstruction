from pathlib import Path
import json,hashlib,sys
import cv2,numpy as np
WEB=Path('/mnt/d/桌面/image/gpt-6/工程/交互演示'); TASK=WEB.parent/'GSICP历史快照'
sys.path.insert(0,str(WEB.parent/'源码/GS-ICP-SLAM'))
from utils.traj_utils import TrajManager
for key,run in [('tum','tum-smoke30-a3'),('replica','replica-smoke30-a1')]:
 root=TASK/'运行'/run; src=json.loads((root/'snapshot-index.json').read_text()); clock=json.loads((root/'input-clock.json').read_text()); frames=[json.loads(x) for x in (root/'frames.jsonl').read_text().splitlines()]; out=WEB/'assets'/'history-smoke'/key;out.mkdir(parents=True,exist_ok=True)
 if key=='tum':
  traj=TrajManager('tum',src['snapshots'][0]['dataset']); depths=traj.depth_paths
 else: depths=sorted(str(p) for p in (TASK/'数据/Replica/office0/results').glob('depth*.png'))
 rows=[]
 for v in src['snapshots']:
  n=v['source_frame']; f=frames[v['training_frame']]; rgb=Path(f['image_path']); rgb=rgb if rgb.exists() else TASK/'数据/Replica/office0/results'/rgb.name
  depth=Path(depths[n]); image=cv2.imread(str(depth),cv2.IMREAD_UNCHANGED); scale=5000 if key=='tum' else 6553.5
  heat=cv2.applyColorMap(np.uint8(np.clip(image.astype(float)/scale/6,0,1)*255),cv2.COLORMAP_TURBO);heat[image==0]=80
  cv2.imwrite(str(out/f'{n}-rgb.jpg'),cv2.imread(str(rgb)),[cv2.IMWRITE_JPEG_QUALITY,92]);cv2.imwrite(str(out/f'{n}-depth.png'),heat)
  v={**v,'ply':f'/history/{key}/{v["ply"]}','rgb':f'assets/history-smoke/{key}/{n}-rgb.jpg','depth':f'assets/history-smoke/{key}/{n}-depth.png','input_rgb_sha256':hashlib.sha256(rgb.read_bytes()).hexdigest(),'input_depth_sha256':hashlib.sha256(depth.read_bytes()).hexdigest()}; rows.append(v)
 meta=json.loads((WEB/'assets'/('replica.json' if key=='replica' else 'natural/tum-comparison/GSICP10.json')).read_text()); meta.update(snapshots=rows,run_id=run,scope='初测30帧',input_fps=5 if key=='replica' else 10,indices=clock['source_indices'],duration=clock['source_indices'][-1]/(5 if key=='replica' else 10),poses=[f['estimated_c2w'] for f in frames],gaussians=rows[-1]['gaussians'],kind='GS-ICP SLAM · 初测30帧',bounds='',display_info='初测30帧',tracking_text='初测',ate_text='—',show_rgb_preview=False)
 (out/'index.json').write_text(json.dumps(meta,ensure_ascii=False),encoding='utf-8')
 print(key,len(rows),flush=True)
