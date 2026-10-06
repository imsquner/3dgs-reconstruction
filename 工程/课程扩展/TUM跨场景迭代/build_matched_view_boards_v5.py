"""Native matched-camera boards, all views and source hashes retained."""
import argparse,json,re
from pathlib import Path
from PIL import Image,ImageDraw
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent;E=B.parents[1]
p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--runs',nargs='+',required=True);p.add_argument('--tag',required=True);a=p.parse_args()
assert re.fullmatch('[a-zA-Z0-9-]+',a.tag)
views=json.loads((E/'运行'/a.base/'评价/metrics.json').read_text())['fixed_views']
audits=[];labels=[];sources={}
for name in a.runs:
 R=E/'运行'/name;d=json.loads((R/'评价/固定视角原生审计/影响.json').read_text())
 assert d['base']==a.base and d['map_sha256']==sha256(R/'scene.ply')
 assert [(r['train_index'],r['offset_local_x_m']) for r in d['rows']]==[(r['train_index'],r['offset_local_x_m']) for r in views]
 q=json.loads((R/'manifest.json').read_text())['quality_args']
 labels.append(('original' if q.get('variant','original')=='original' else f"candidate d{q.get('depth_weight',.01):g} c{q.get('coverage_weight',0):g}")+f" b{q['steps_per_frame']}")
 if 'growth_weight' in q:labels[-1]+=f" g{q['growth_weight']:g}"
 if 'tracking_covariance' in q:labels[-1]=f"cand b{q['steps_per_frame']} g{q.get('growth_weight',0):g} {q['tracking_covariance']}"
 if 'tracking_positions' in q:labels[-1]=f"b{q['steps_per_frame']} {q['tracking_positions']}-xyz {q['tracking_covariance']}"
 audits.append(d)
out=B/'验证/匹配相机对照'/a.tag;out.mkdir(parents=True,exist_ok=True);outputs=[]
with Image.open(E/'运行'/a.runs[0]/'评价/固定视角原生审计'/audits[0]['rows'][0]['render_rgb']) as first:
 width,height=first.size
thumb_h=round(height*320/width)
for pose in sorted({v['train_index'] for v in views}):
 ids=[i for i,v in enumerate(views) if v['train_index']==pose]
 board=Image.new('RGB',(320*len(a.runs),(thumb_h+24)*len(ids)),(235,235,235));draw=ImageDraw.Draw(board)
 for r,i in enumerate(ids):
  for c,(name,label,d) in enumerate(zip(a.runs,labels,audits)):
   view=d['rows'][i];path=E/'运行'/name/'评价/固定视角原生审计'/view['render_rgb'];sources[str(path)]=sha256(path)
   with Image.open(path) as image:
    assert image.size==(width,height);board.paste(image.resize((320,thumb_h),Image.Resampling.LANCZOS),(c*320,r*(thumb_h+24)+24))
   draw.text((c*320+4,r*(thumb_h+24)+5),f"{label} | {pose} X+{view['offset_local_x_m']:.1f}",fill=(10,10,10))
 target=out/f'pose-{pose:04d}.png';board.save(target);outputs.append(str(target));print('MATCHED_BOARD',target,flush=True)
atomic_json(out/'manifest.json',{'base':a.base,'runs':a.runs,'labels':labels,'sources':sources,'outputs':outputs,'script_sha256':sha256(__file__),
 'scope':'All fixed views rendered with identical estimated base camera poses/intrinsics, original native images retained and SHA pinned. Display resizing only, no enhancement, no cropped views, no novel-view ground truth.'})
