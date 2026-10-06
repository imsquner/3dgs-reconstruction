"""Compare read-only membership snapshots; report opacity versus missing prune IDs."""
import json,time
from pathlib import Path
import numpy as np
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent;E=B.parents[1]
def compare(short,long):
 x=E/'运行'/short/'筛选输入';y=E/'运行'/long/'筛选输入';rows=[]
 for p in sorted(x.glob('selection-*.npz')):
  frame=int(p.stem.split('-')[1])
  if frame>=39 or not (y/p.name).exists():continue
  a=np.load(p);b=np.load(y/p.name);sa=set(a['selected_ids'].tolist());sb=set(b['selected_ids'].tolist())
  if sa==sb:continue
  aa={int(i):j for j,i in enumerate(a['all_ids'])};bb={int(i):j for j,i in enumerate(b['all_ids'])};common=set(aa)&set(bb)
  trackable_diff=[i for i in sorted(common) if a['trackable'][aa[i]]!=b['trackable'][bb[i]]]
  details=[]
  for i in sorted(sa^sb):
   details.append(dict(id=i,short_present=i in aa,long_present=i in bb,short_selected=i in sa,long_selected=i in sb,short_opacity=float(a['opacity'][aa[i]]) if i in aa else None,long_opacity=float(b['opacity'][bb[i]]) if i in bb else None,short_trackable=bool(a['trackable'][aa[i]]) if i in aa else None,long_trackable=bool(b['trackable'][bb[i]]) if i in bb else None))
  rows.append(dict(frame=frame,short_selected_count=len(sa),long_selected_count=len(sb),short_all_count=len(aa),long_all_count=len(bb),missing_all_ids_short=sorted(set(bb)-set(aa)),missing_all_ids_long=sorted(set(aa)-set(bb)),trackable_difference_ids=trackable_diff,opacity_only_same_population=set(aa)==set(bb) and not trackable_diff,changed_members=details,short_snapshot_sha256=sha256(p),long_snapshot_sha256=sha256(y/p.name)))
 return dict(short=short,long=long,changed_views=rows,scope='Persistent insertion IDs; first39 target snapshots only, excluding forced final short keyframe. Opacity-only classification requires same surviving IDs and trackable mask. Missing IDs may arise from prune or changed insertion and require prune/source evidence; no automatic sole-cause attribution.')
if __name__=='__main__':
 result={'created':time.time(),'pairs':{}}
 for pair in ['a','b']:
  short=f'local-tum-quality-selection40-{pair}-v14';long=f'local-tum-quality-selection80-{pair}-v14'
  r=E/'运行'/long/'state.json'
  if r.exists() and json.loads(r.read_text())['status']=='complete':result['pairs'][pair]=compare(short,long)
 atomic_json(B/'验证/映射边界/透明度与剪枝分离诊断-v14.json',result)
 print(json.dumps(result,ensure_ascii=False),flush=True)
