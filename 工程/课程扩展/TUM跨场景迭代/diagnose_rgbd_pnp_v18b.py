"""All TUM train pairs; no reconstruction or heldout parameter selection."""
import json,os,time,hashlib,numpy as np,cv2
from pathlib import Path
from scipy.spatial.transform import Rotation
from quality_core import atomic_json,sha256
from quality_rgbd_pnp import CONFIG,features,measure,world_from_relative
B=Path(__file__).resolve().parent;E=B.parents[1];O=B/'验证/v18-RGBD-PnP-r2';O.mkdir(exist_ok=True)
protocol=B/'协议/tum-office.json';d=json.loads(protocol.read_text());rows=d['upstream_original_train'];assert len(rows)==2253
W,H,fx,fy,cx,cy=d['intrinsic'];K=np.array([[fx,0,cx],[0,fy,cy],[0,0,1.]])
plan={'protocol_sha256':sha256(protocol),'module_sha256':sha256(B/'quality_rgbd_pnp.py'),'script_sha256':sha256(__file__),'config':CONFIG,'rows':len(rows),'scope':'Previous train RGB/depth and current train RGB only. GT evaluation after all measurements, no heldout or tuning. Decode content hashes recorded. Fallback hold previous in diagnostic trajectory only; no Gaussian map or training.'}
f=O/'manifest.json'
if f.exists():assert json.loads(f.read_text())==plan
else:atomic_json(f,plan)
cv2.setNumThreads(2)
eventfile=O/'pairs.jsonl';events=[json.loads(x) for x in eventfile.read_text().splitlines()] if eventfile.exists() else []
assert all(e['frame']==i for i,e in enumerate(events,1))
start=time.monotonic();first=len(events)+1
atomic_json(O/'state.json',{'stage':'running','pid':os.getpid(),'completed_pairs':len(events)})
def decode(path,mode):
 raw=Path(path).read_bytes();im=cv2.imdecode(np.frombuffer(raw,dtype=np.uint8),mode);assert im is not None
 return im,hashlib.sha256(raw).hexdigest()
try:
 if first<len(rows):
  previous,prevhash=decode(rows[first-1]['rgb_path'],cv2.IMREAD_COLOR);previous_features=features(previous)
  with eventfile.open('a',buffering=1) as output:
   for i in range(first,len(rows)):
    current,curhash=decode(rows[i]['rgb_path'],cv2.IMREAD_COLOR);current_features=features(current)
    depth,depthhash=decode(rows[i-1]['depth_path'],cv2.IMREAD_ANYDEPTH)
    result=measure(previous_features,current_features,depth.astype(np.float64)/d['depth_scale'],K,d.get('depth_trunc',3.))
    if result['accepted']:result['current_from_previous']=result['current_from_previous'].tolist()
    result.update(frame=i,source_frame=rows[i]['source_frame'],previous_source_frame=rows[i-1]['source_frame'],input_sha256={'previous_rgb':prevhash,'current_rgb':curhash,'previous_depth':depthhash})
    output.write(json.dumps(result)+'\n');events.append(result);previous_features=current_features;prevhash=curhash
    if i%50==0 or i==len(rows)-1:
     elapsed=time.monotonic()-start;eta=elapsed/(i-first+1)*(len(rows)-1-i)
     atomic_json(O/'state.json',{'stage':'running','pid':os.getpid(),'completed_pairs':i,'total_pairs':len(rows)-1,'elapsed_this_session_seconds':elapsed,'eta_seconds':eta})
     print('PNP_PROGRESS',i,'/',len(rows)-1,'accepted',sum(x['accepted'] for x in events),'elapsed',round(elapsed,1),'eta',round(eta,1),flush=True)
 assert len(events)==2252
 # Reference read only after all image-derived measurements finished.
 gt=np.array([x['reference_c2w'] for x in rows]);estimated=[gt[0].copy()];comparisons=[]
 baselines={name:np.array(json.loads((E/'运行'/name/'final-poses.json').read_text())) for name in ['local-tum-quality-motionfull-original-b10-v17','local-tum-quality-motionfull-combined-b20-v17']}
 for i,e in enumerate(events,1):
  if not e['accepted']:estimated.append(estimated[-1].copy());continue
  T=np.array(e['current_from_previous']);estimated.append(world_from_relative(estimated[-1],T));truth=np.linalg.inv(gt[i])@gt[i-1]
  def error(T):return {'translation_m':float(np.linalg.norm(T[:3,3]-truth[:3,3])),'rotation_deg':float(Rotation.from_matrix(T[:3,:3]@truth[:3,:3].T).magnitude()*180/np.pi)}
  comparisons.append({'frame':i,'pnp':error(T),**{name:error(np.linalg.inv(p[i])@p[i-1]) for name,p in baselines.items()}})
 def describe(v):return {'rmse':float(np.sqrt(np.mean(np.array(v)**2))),'p50':float(np.percentile(v,50)),'p95':float(np.percentile(v,95)),'max':float(max(v))}
 metrics={'total_pairs':2252,'accepted':len(comparisons),'rejected':2252-len(comparisons),'paired_relative_errors_on_all_accepted':{name:{axis:describe([x[name][axis] for x in comparisons]) for axis in ['translation_m','rotation_deg']} for name in ['pnp',*baselines]},'segments':[{'start_frame':a,'end_exclusive':z,'accepted':sum(a<=x['frame']<z for x in comparisons)} for a,z in [(1,600),(600,1200),(1200,1800),(1800,2253)]],'scope':'Pairwise diagnostic using GT only after measurement; accepted subset compared identically, rejection explicitly reported; no full map quality proof. No test or transfer tuning.'}
 pp=np.array(estimated);metrics['diagnostic_cumulative_raw_translation_rmse_m']=float(np.sqrt(np.mean(np.sum((pp[:,:3,3]-gt[:,:3,3])**2,axis=1))))
 atomic_json(O/'metrics.json',metrics);atomic_json(O/'pair-evaluation.json',comparisons);atomic_json(O/'diagnostic-poses.json',pp.tolist());atomic_json(O/'state.json',{'stage':'complete','pid':os.getpid(),'pairs':2252,'accepted':len(comparisons),'pair_log_sha256':sha256(eventfile)});print('PNP_DIAGNOSTIC_COMPLETE',json.dumps(metrics),flush=True)
except Exception as ex:
 atomic_json(O/'state.json',{'stage':'failed','pid':os.getpid(),'error':str(ex),'completed_pairs':len(events)});raise
