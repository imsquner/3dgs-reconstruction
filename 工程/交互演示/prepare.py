"""Package original, verified experiment assets without retraining or editing them."""
from pathlib import Path
import json,hashlib,urllib.request,tarfile,io,base64,shutil
import numpy as np
from ply_adapter import adapt_xyzw_to_wxyz

B=Path(__file__).resolve().parent; G=B.parents[1]; R=G/'工程/运行'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
vendor=B/'vendor';vendor.mkdir(exist_ok=True);records=[]
for pkg,ver,files in [('@mkkellogg/gaussian-splats-3d','0.4.7',{'package/build/gaussian-splats-3d.module.js':'gaussian-splats-3d.module.js','package/LICENSE':'LICENSE-GaussianSplats3D'}),('three','0.170.0',{'package/build/three.module.js':'three.module.js','package/examples/jsm/controls/OrbitControls.js':'OrbitControls.js','package/LICENSE':'LICENSE-Three'})]:
 print('DEPENDENCY',pkg,ver,flush=True)
 metadata=json.load(urllib.request.urlopen('https://registry.npmjs.org/'+pkg+'/'+ver,timeout=40))
 data=urllib.request.urlopen(metadata['dist']['tarball'],timeout=90).read()
 assert 'sha512-'+base64.b64encode(hashlib.sha512(data).digest()).decode()==metadata['dist']['integrity']
 with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as t:
  for src,dest in files.items():
   try:b=t.extractfile(src).read()
   except KeyError:
    if 'LICENSE' in src:continue
    raise
   (vendor/dest).write_bytes(b)
 records.append(dict(package=pkg,version=ver,integrity=metadata['dist']['integrity'],source=metadata['dist']['tarball']))
assets=B/'assets';assets.mkdir(exist_ok=True);scenes=[]
for key,run,label,kind,intrinsic in [
 ('replica','srv-final-replicaoffice0-5fps-h10','Replica office0','合成室内 · 最终3DGS',[1200,680,600,600,599.5,339.5]),
 ('office','srv-demo-officefull-5fps','TUM office','真实室内 · 最终3DGS',[640,480,535.4,539.2,320.1,247.6]),
 ('unity','srv-med-unity240','Unity colon','医学合成 · 局部3DGS',[320,320,156.0418,155.7529,178.5604,181.8043])]:
 d=R/run;ply=d/'scene.ply'
 if not ply.exists():ply=d/'point_cloud/final/point_cloud.ply'
 assert ply.exists(),ply
 target=assets/(key+'.ply');shutil.copyfile(ply,target);assert sha(target)==sha(ply)
 original_sha=sha(ply);adapter=None
 if key in ('replica','office'):
  target=assets/(key+'-web.ply');adapter=adapt_xyzw_to_wxyz(ply,target)
 if (d/'final-poses.json').exists():
  poses=json.loads((d/'final-poses.json').read_text());indices=json.loads((d/'input-clock.json').read_text())['source_indices']
 else:
  rows=json.loads((d/'all-frame-poses.json').read_text());poses=[r['estimated_c2w'] for r in rows];indices=[r.get('frame',i) for i,r in enumerate(rows)]
 assert len(poses)==len(indices)
 audit=json.loads((d/'experiment-audit.json').read_text());assert audit['ply_finite']
 scene=dict(id=key,label=label,kind=kind,run=run,ply='assets/'+target.name,ply_sha256=sha(target),gaussians=audit['ply_count'],input_fps=5,indices=indices,poses=poses,intrinsic=intrinsic,duration=indices[-1]/5,measured_tracking_fps=audit['post_first_tracking_fps'],ate_m=audit.get('all_frame_ate_rmse_m'),bounds='最终地图的轨迹回放；不代表历史高斯地图快照。医学仅局部、物理精度未评价。')
 scene['source_ply_sha256']=original_sha;scene['browser_adapter']=adapter
 raw=target.read_bytes();end=raw.index(b'end_header\n')+11;fields=[l for l in raw[:end].decode().splitlines() if l.startswith('property ')];xyz=np.frombuffer(raw[end:],dtype='<f4').reshape(-1,len(fields))[:,:3];scene['map_bounds']=np.quantile(xyz,[.005,.995],axis=0).tolist()
 (assets/(key+'.json')).write_text(json.dumps(scene,separators=(',',':'),ensure_ascii=False),encoding='utf-8')
 scenes.append({k:v for k,v in scene.items() if k not in ('poses','indices')})
 print('SCENE',key,len(poses),audit['ply_count'],target.stat().st_size,flush=True)
(assets/'scenes.json').write_text(json.dumps(scenes,ensure_ascii=False,indent=2),encoding='utf-8')
(B/'dependency-manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('ASSETS_READY',flush=True)
