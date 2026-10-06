"""All fixed views arranged without changing renders; no quality filtering."""
import argparse,json
from pathlib import Path
from PIL import Image,ImageDraw
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent;E=B.parents[1]
p=argparse.ArgumentParser();p.add_argument('--include-candidate',action='store_true');a=p.parse_args()
names=['local-tum-quality-full-base-v2','local-tum-quality-pruned-original-10000-v5',
       'local-tum-quality-pruned-original-20000-v5']
labels=['Online base','Original +10000','Original +20000']
if a.include_candidate:names+=['local-tum-quality-pruned-improved-20000-v5'];labels+=['Candidate +20000']
metrics=[json.loads((E/'运行'/n/'评价/metrics.json').read_text()) for n in names]
views=metrics[0]['fixed_views'];assert all(m['fixed_views']==views for m in metrics)
out=B/'验证/固定视角对照';out.mkdir(parents=True,exist_ok=True);sources={};outputs=[]
for pose in sorted({v['train_index'] for v in views}):
 rows=[v for v in views if v['train_index']==pose]
 board=Image.new('RGB',(320*len(names),264*len(rows)),(235,235,235));draw=ImageDraw.Draw(board)
 for r,v in enumerate(rows):
  for c,(n,label) in enumerate(zip(names,labels)):
   path=E/'运行'/n/'评价'/v['path'];sources[str(path)]=sha256(path)
   with Image.open(path) as image:
    assert image.size==(640,480),'This board is explicitly for TUM 640x480'
    board.paste(image.resize((320,240),Image.Resampling.LANCZOS),(c*320,r*264+24))
   draw.text((c*320+5,r*264+5),f'{label} | pose {pose} X+{v["offset_local_x_m"]:.1f}m',fill=(10,10,10))
 suffix='four-variants' if a.include_candidate else 'controls'
 target=out/f'pose-{pose:04d}-{suffix}.png';board.save(target);outputs.append(str(target));print('BOARD',target,flush=True)
atomic_json(out/f'{suffix}-manifest.json',{'sources':sources,'outputs':outputs,'script_sha256':sha256(__file__),
 'scope':'All nine fixed views, unchanged native RGB rendered images displayed at half resolution, same estimated base cameras and offsets. No selected views, enhancement, ROI cropping, or new-view ground truth.'})
