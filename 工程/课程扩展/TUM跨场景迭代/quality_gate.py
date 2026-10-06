"""Independent numeric gate audit. Visual acceptance always remains manual."""
import argparse,json,math
from pathlib import Path
from quality_core import sha256,atomic_json
B=Path(__file__).resolve().parent;E=B.parents[1]

def numeric_gate(base,candidate,base_common_mae,candidate_common_mae,mode):
 assert mode in ('development','transfer')
 for m in (base,candidate):
  assert all(math.isfinite(m[k]) for k in ('psnr_db','ssim','coverage'))
 delta={k:candidate[k]-base[k] for k in ('psnr_db','ssim','coverage')}
 if mode=='development':
  rgb=(delta['psnr_db']>=.5 or delta['ssim']>=.01) and delta['psnr_db']>=0 and delta['ssim']>=0
 else:rgb=delta['psnr_db']>=-.2 and delta['ssim']>=-.005
 geometry=None
 if base_common_mae is not None and candidate_common_mae is not None:
  assert math.isfinite(base_common_mae) and math.isfinite(candidate_common_mae)
  assert base_common_mae>=0 and candidate_common_mae>=0
  geometry=candidate_common_mae<=1.05*base_common_mae
 coverage=delta['coverage']>=-.02
 return dict(mode=mode,deltas=delta,rgb_gate=rgb,coverage_gate=coverage,common_mae_gate=geometry,
             all_numeric_gates=None if geometry is None else bool(rgb and coverage and geometry))

def audit(base_name,candidate_name,mode):
 roots=[E/'运行'/n for n in (base_name,candidate_name)]
 manifests=[json.loads((r/'manifest.json').read_text()) for r in roots]
 metrics=[json.loads((r/'评价/metrics.json').read_text()) for r in roots]
 maps=[sha256(r/'scene.ply') for r in roots]
 assert all(m['signature']['map']==h for m,h in zip(metrics,maps)),'Stale evaluation'
 assert manifests[0]['frames']==manifests[1]['frames'],'Training observations differ'
 assert manifests[0]['protocol_sha256']==manifests[1]['protocol_sha256'],'Protocol differs'
 ids=[[x['source_frame'] for x in m['rows']] for m in metrics]
 assert ids[0]==ids[1] and len(ids[0])>0,'Validation observations differ'
 common=json.loads((roots[1]/'评价/common-depth.json').read_text())
 assert (common['base'],common['candidate'])==(base_name,candidate_name)
 assert (common['signature']['base'],common['signature']['candidate'])==tuple(maps)
 assert [x['source_frame'] for x in common['rows']]==ids[0]
 assert all(x['common_pixels']>0 for x in common['rows']),'Missing common pixels'
 result=numeric_gate(metrics[0]['means'],metrics[1]['means'],common['means']['base']['common_mae_m'],common['means']['candidate']['common_mae_m'],mode)
 result.update(base=base_name,candidate=candidate_name,validation_frames=len(ids[0]),map_sha256=maps,
               common_depth=common['means'],visual_acceptance=None,all_goal_requirements=False,
               scope='Numerical gate only. Development uses nondecreasing second RGB metric. RMSE is reported independently. Fixed-view preservation/artifact truth review, transfer, timing and package remain separate requirements.')
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('base');p.add_argument('candidate');p.add_argument('--mode',choices=['development','transfer'],default='development');a=p.parse_args()
 result=audit(a.base,a.candidate,a.mode)
 out=E/'运行'/a.candidate/'评价'/('numeric-gate-'+a.mode+'.json')
 atomic_json(out,result);print(json.dumps(result,ensure_ascii=False),flush=True)
